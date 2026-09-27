"""The sole ownership-safe write path into the Obsidian vault (T-P4-13).

One call to :meth:`VaultWriter.write_batch` is one safety unit: the vault Git
tree is checked once before any note mutation, all output is staged before it
is published with ``os.replace``, and all changes are committed together.
Publication or commit failures restore the exact pre-batch bytes.

User sections use symmetric, explicit delimiters::

    %% user-section %%
    text controlled by the owner
    %% end-user-section %%

The interiors of matched pairs are excluded from edit-detection hashes.  On
an update, blocks from the existing file are spliced into the corresponding
markers in generated content before publication.  Thus editing only a user
section neither causes a fork nor gets overwritten, while every byte outside
those sections remains protected by ``content_hash``.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from io import StringIO
from pathlib import Path, PurePosixPath
from typing import Any, Final, Self

from ruamel.yaml import YAML

from sbr import __version__
from sbr.config import SbrConfig, path_key
from sbr.db.registry import RegistryDB
from sbr.ids import hash_bytes
from sbr.provenance import ProvenanceStore
from sbr.safety import assert_writable
from sbr.schemas.provenance import ProvenanceClass

START_USER_SECTION: Final = "%% user-section %%"
END_USER_SECTION: Final = "%% end-user-section %%"
VAULT_STAGE_PREFIX: Final = ".sbr-stage-"
VAULT_PRODUCER: Final = "sbr.vault.writer"
VAULT_STAGE: Final = "vault_write"

_FRONTMATTER_RE: Final = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", re.DOTALL)
_USER_SECTION_RE: Final = re.compile(
    rf"(?P<start>{re.escape(START_USER_SECTION)})(?P<body>.*?)(?P<end>{re.escape(END_USER_SECTION)})",
    re.DOTALL,
)


class VaultWriteError(RuntimeError):
    """Base class for vault-write failures."""


class VaultPathError(VaultWriteError):
    """A vault-relative path is unsafe or outside the owned folder matrix."""


class VaultOwnershipError(VaultWriteError):
    """An operation or provenance class violates a folder ownership rule."""


class VaultDirtyError(VaultWriteError):
    """The vault has changes not committed by a completed writer batch."""


class VaultGitError(VaultWriteError):
    """The vault Git repository could not be initialized or committed."""


class VaultFrontmatterError(VaultWriteError):
    """A system-owned note has missing or invalid frontmatter."""


class VaultFolder(StrEnum):
    NOTES = "notes"
    SOURCES = "sources"
    CONCEPTS = "concepts"
    AI = "ai"
    MAPS = "maps"
    RESEARCH = "research"
    INBOX = "inbox"


class VaultOperation(StrEnum):
    WRITE = "write"
    DELETE = "delete"
    ORPHAN = "orphan"


@dataclass(frozen=True, slots=True)
class VaultMutation:
    """One requested mutation in a vault batch."""

    operation: VaultOperation
    relpath: PurePosixPath
    content: str | None = None
    provenance_class: ProvenanceClass | None = None
    reason: str | None = None

    @classmethod
    def write(cls, relpath: str | PurePosixPath, content: str, provenance_class: ProvenanceClass) -> VaultMutation:
        return cls(VaultOperation.WRITE, PurePosixPath(relpath), content, provenance_class)

    @classmethod
    def delete(cls, relpath: str | PurePosixPath) -> VaultMutation:
        return cls(VaultOperation.DELETE, PurePosixPath(relpath))

    @classmethod
    def orphan(cls, relpath: str | PurePosixPath, *, reason: str) -> VaultMutation:
        return cls(VaultOperation.ORPHAN, PurePosixPath(relpath), reason=reason)


@dataclass(frozen=True, slots=True)
class VaultWriteResult:
    activity_id: str
    commit_sha: str
    written: tuple[PurePosixPath, ...]
    deleted: tuple[PurePosixPath, ...]
    forked: tuple[PurePosixPath, ...]
    orphaned: tuple[PurePosixPath, ...]


@dataclass(frozen=True, slots=True)
class _PreparedChange:
    target: Path
    content: bytes | None
    relpath: PurePosixPath


@dataclass(frozen=True, slots=True)
class _Backup:
    target: Path
    existed: bool
    content: bytes | None


_ALLOWED_PROVENANCE: Final[dict[VaultFolder, frozenset[ProvenanceClass]]] = {
    VaultFolder.NOTES: frozenset(),
    VaultFolder.SOURCES: frozenset({ProvenanceClass.SOURCE_DERIVED}),
    VaultFolder.CONCEPTS: frozenset({ProvenanceClass.AI_GENERATED}),
    VaultFolder.AI: frozenset({ProvenanceClass.AI_GENERATED}),
    VaultFolder.MAPS: frozenset({ProvenanceClass.AI_GENERATED}),
    VaultFolder.RESEARCH: frozenset({ProvenanceClass.EXTERNAL_RESEARCH}),
    VaultFolder.INBOX: frozenset(
        {
            ProvenanceClass.SOURCE_DERIVED,
            ProvenanceClass.AI_GENERATED,
            ProvenanceClass.EXTERNAL_PENDING,
            ProvenanceClass.EXTERNAL_RESEARCH,
        }
    ),
}


class VaultWriter:
    """Ownership-aware, atomic, Git-versioned writer for one configured vault."""

    def __init__(self, config: SbrConfig, db: RegistryDB, git: str) -> None:
        self.config = config
        self.root = config.vault_path
        self.db = db
        self._git = git

    @classmethod
    def open(cls, config: SbrConfig) -> Self:
        """Open the registry and initialize the vault's independent Git repository."""
        root = config.vault_path
        assert_writable(root, config)
        root.mkdir(parents=True, exist_ok=True)
        git = shutil.which("git")
        if git is None:
            raise VaultGitError("git executable is required for vault writes")
        writer = cls(config, RegistryDB.open(config), git)
        try:
            writer.db.migrate()
            if not (root / ".git").is_dir():
                writer._run_git("init")
            writer._verify_repository_root()
        except BaseException:
            writer.close()
            raise
        return writer

    def _verify_repository_root(self) -> None:
        actual = self._run_git("rev-parse", "--show-toplevel").stdout.strip()
        if path_key(actual) != path_key(self.root.resolve()):
            raise VaultGitError("vault path is not the root of its own Git repository")

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def write_batch(
        self,
        mutations: Sequence[VaultMutation],
        *,
        message: str,
        owner: str = "system:vault-writer",
        before_publish: Callable[[], None] | None = None,
    ) -> VaultWriteResult:
        """Validate, atomically publish and commit one non-empty mutation batch.

        ``before_publish`` is a narrow test seam for crash simulation.  It runs
        after every output has been durably staged but before any final path is
        changed.
        """
        if not mutations:
            raise ValueError("a vault write batch must not be empty")
        if not message.strip():
            raise ValueError("a vault commit message must not be empty")
        self._validate_policy(mutations)
        # Sweep stage debris from a real process kill *before* the dirty check: a stage file is
        # never committed, so it always shows up as untracked. Checking cleanliness first would
        # make that debris look like an owner edit and permanently refuse every future batch.
        self._remove_stale_stages()
        self._require_clean()
        prepared, written, deleted, forked, orphaned = self._prepare(mutations)
        provenance = ProvenanceStore(self.db.conn)
        with provenance.activity(
            kind=VAULT_STAGE,
            producer=VAULT_PRODUCER,
            producer_version=__version__,
            agent=owner,
            params={"mutations": len(mutations)},
        ) as activity:
            backups = self._publish(prepared, before_publish=before_publish)
            try:
                self._run_git("add", "--all", "--", ".")
                commit = self._run_git(
                    "-c",
                    "user.name=Second Brain RAG",
                    "-c",
                    "user.email=sbr@localhost",
                    "commit",
                    "--no-gpg-sign",
                    "--allow-empty",
                    "-m",
                    message,
                )
                del commit
                commit_sha = self._run_git("rev-parse", "HEAD").stdout.strip()
            except BaseException:
                self._restore(backups)
                self._unstage_after_rollback()
                raise
            activity.notes = (
                f"written={len(written)};deleted={len(deleted)};"
                f"forked={len(forked)};orphaned={len(orphaned)};commit={commit_sha}"
            )
        return VaultWriteResult(
            activity_id=activity.activity_id,
            commit_sha=commit_sha,
            written=tuple(written),
            deleted=tuple(deleted),
            forked=tuple(forked),
            orphaned=tuple(orphaned),
        )

    def _validate_policy(self, mutations: Sequence[VaultMutation]) -> None:
        """Reject ownership violations before consulting or mutating filesystem state."""
        for mutation in mutations:
            _, folder, _ = self._resolve(mutation.relpath)
            if mutation.operation is VaultOperation.WRITE:
                if mutation.content is None or mutation.provenance_class is None:
                    raise VaultOwnershipError("write mutations require content and provenance_class")
                if mutation.provenance_class not in _ALLOWED_PROVENANCE[folder]:
                    raise VaultOwnershipError(
                        f"{mutation.provenance_class.value} may not be written in {folder.value}/"
                    )
            elif mutation.operation is VaultOperation.DELETE and folder is not VaultFolder.INBOX:
                raise VaultOwnershipError(f"delete is allowed only in inbox/, not {folder.value}/")
            elif mutation.operation is VaultOperation.ORPHAN and folder is not VaultFolder.SOURCES:
                raise VaultOwnershipError("orphan moves are allowed only for sources/")

    def _prepare(
        self, mutations: Sequence[VaultMutation]
    ) -> tuple[
        list[_PreparedChange],
        list[PurePosixPath],
        list[PurePosixPath],
        list[PurePosixPath],
        list[PurePosixPath],
    ]:
        changes: list[_PreparedChange] = []
        written: list[PurePosixPath] = []
        deleted: list[PurePosixPath] = []
        forked: list[PurePosixPath] = []
        orphaned: list[PurePosixPath] = []
        targets: set[Path] = set()

        for mutation in mutations:
            relpath, folder, target = self._resolve(mutation.relpath)
            if target in targets:
                raise VaultPathError(f"duplicate batch target: {relpath}")
            if mutation.operation is VaultOperation.WRITE:
                change, actual_relpath, did_fork = self._prepare_write(mutation, relpath, folder, target)
                if change.target in targets:
                    raise VaultPathError(f"duplicate batch target: {actual_relpath}")
                changes.append(change)
                targets.add(change.target)
                written.append(actual_relpath)
                if did_fork:
                    forked.append(actual_relpath)
                    # Reclassify only metadata; owner body bytes remain verbatim.
                    original = self._reclassify_as_user(target, relpath)
                    if original is not None:
                        changes.append(original)
                        targets.add(original.target)
            elif mutation.operation is VaultOperation.DELETE:
                if folder is not VaultFolder.INBOX:
                    raise VaultOwnershipError(f"delete is allowed only in inbox/, not {folder.value}/")
                changes.append(_PreparedChange(target, None, relpath))
                targets.add(target)
                deleted.append(relpath)
            elif mutation.operation is VaultOperation.ORPHAN:
                if folder is not VaultFolder.SOURCES:
                    raise VaultOwnershipError("orphan moves are allowed only for sources/")
                if not target.is_file():
                    raise VaultPathError(f"source note does not exist: {relpath}")
                orphan_rel = PurePosixPath("_system", "orphaned", *relpath.parts[1:])
                orphan_target = self.root.joinpath(*orphan_rel.parts)
                if orphan_target.exists() or orphan_target in targets:
                    raise VaultPathError(f"orphan destination already exists: {orphan_rel}")
                note = f"\n\n> [!warning] Orphaned source note. Reason: {mutation.reason or 'unspecified'}\n"
                changes.append(_PreparedChange(orphan_target, target.read_bytes() + note.encode(), orphan_rel))
                changes.append(_PreparedChange(target, None, relpath))
                targets.update({target, orphan_target})
                orphaned.append(orphan_rel)
            else:  # pragma: no cover - enum exhaustiveness
                raise VaultOwnershipError(f"unsupported vault operation {mutation.operation}")
        return changes, written, deleted, forked, orphaned

    def _prepare_write(
        self, mutation: VaultMutation, relpath: PurePosixPath, folder: VaultFolder, target: Path
    ) -> tuple[_PreparedChange, PurePosixPath, bool]:
        if mutation.content is None or mutation.provenance_class is None:
            raise VaultOwnershipError("write mutations require content and provenance_class")
        if mutation.provenance_class not in _ALLOWED_PROVENANCE[folder]:
            raise VaultOwnershipError(f"{mutation.provenance_class.value} may not be written in {folder.value}/")
        metadata, generated_body = _parse_note(mutation.content)
        _validate_required_frontmatter(metadata, mutation.provenance_class)

        if not target.exists():
            rendered = _render_note(metadata, generated_body, mutation.provenance_class)
            return _PreparedChange(target, rendered, relpath), relpath, False
        if not target.is_file():
            raise VaultPathError(f"vault target is not a regular file: {relpath}")

        old_raw = target.read_text(encoding="utf-8")
        try:
            old_metadata, old_body = _parse_note(old_raw)
        except VaultFrontmatterError:
            fork_rel = self._fork_relpath(relpath)
            fork_target = self.root.joinpath(*fork_rel.parts)
            rendered = _render_note(metadata, generated_body, mutation.provenance_class)
            return _PreparedChange(fork_target, rendered, fork_rel), fork_rel, True
        if (
            not old_metadata.get("sbr_id")
            or old_metadata.get("provenance_class") == ProvenanceClass.USER_AUTHORED.value
        ):
            fork_rel = self._fork_relpath(relpath)
            fork_target = self.root.joinpath(*fork_rel.parts)
            rendered = _render_note(metadata, generated_body, mutation.provenance_class)
            return _PreparedChange(fork_target, rendered, fork_rel), fork_rel, True
        if folder is VaultFolder.INBOX:
            merged = _splice_user_sections(old_body, generated_body)
            return (
                _PreparedChange(target, _render_note(metadata, merged, mutation.provenance_class), relpath),
                relpath,
                False,
            )

        stored_hash = old_metadata.get("content_hash")
        current_hash = _body_hash(old_body)
        if not isinstance(stored_hash, str) or stored_hash != current_hash:
            fork_rel = self._fork_relpath(relpath)
            fork_target = self.root.joinpath(*fork_rel.parts)
            rendered = _render_note(metadata, generated_body, mutation.provenance_class)
            return _PreparedChange(fork_target, rendered, fork_rel), fork_rel, True

        merged = _splice_user_sections(old_body, generated_body)
        if folder is VaultFolder.RESEARCH and not _masked_body(merged).startswith(_masked_body(old_body)):
            raise VaultOwnershipError("research/ updates must append to the existing body")
        rendered = _render_note(metadata, merged, mutation.provenance_class)
        return _PreparedChange(target, rendered, relpath), relpath, False

    def _resolve(self, raw: PurePosixPath) -> tuple[PurePosixPath, VaultFolder, Path]:
        text = str(raw)
        if "\\" in text or raw.is_absolute() or len(raw.parts) < 2 or any(p in {"", ".", ".."} for p in raw.parts):
            raise VaultPathError(f"unsafe vault-relative path: {text!r}")
        try:
            folder = VaultFolder(raw.parts[0])
        except ValueError as exc:
            raise VaultPathError(f"unmanaged vault folder: {raw.parts[0]!r}") from exc
        if folder is VaultFolder.NOTES:
            raise VaultOwnershipError("the system may never create, update, or delete notes/")
        if raw.suffix.lower() != ".md":
            raise VaultPathError("VaultWriter v1 accepts Markdown files only")
        target = self.root.joinpath(*raw.parts)
        assert_writable(target, self.config)
        return raw, folder, target

    def _fork_relpath(self, relpath: PurePosixPath) -> PurePosixPath:
        base = relpath.with_name(f"{relpath.stem}.sbr-update{relpath.suffix}")
        candidate = base
        index = 2
        while self.root.joinpath(*candidate.parts).exists():
            candidate = relpath.with_name(f"{relpath.stem}.sbr-update-{index}{relpath.suffix}")
            index += 1
        return candidate

    def _reclassify_as_user(self, target: Path, relpath: PurePosixPath) -> _PreparedChange | None:
        try:
            metadata, body = _parse_note(target.read_text(encoding="utf-8"))
        except VaultFrontmatterError:
            return None
        if not metadata.get("sbr_id") or metadata.get("provenance_class") == ProvenanceClass.USER_AUTHORED.value:
            return None
        metadata["provenance_class"] = ProvenanceClass.USER_AUTHORED.value
        # Preserve the old hash: the file is now owner-controlled and no longer updateable by this writer.
        return _PreparedChange(target, _serialize_note(metadata, body), relpath)

    def _publish(
        self, prepared: Sequence[_PreparedChange], *, before_publish: Callable[[], None] | None
    ) -> list[_Backup]:
        backups: list[_Backup] = []
        staged: list[tuple[Path, Path]] = []
        try:
            for change in prepared:
                assert_writable(change.target, self.config)
                backups.append(
                    _Backup(
                        change.target,
                        change.target.exists(),
                        change.target.read_bytes() if change.target.exists() else None,
                    )
                )
                if change.content is None:
                    continue
                change.target.parent.mkdir(parents=True, exist_ok=True)
                stage = change.target.with_name(f"{VAULT_STAGE_PREFIX}{change.target.name}-{os.urandom(8).hex()}")
                with stage.open("xb") as stream:
                    stream.write(change.content)
                    stream.flush()
                    os.fsync(stream.fileno())
                staged.append((stage, change.target))
            if before_publish is not None:
                before_publish()
            for change in prepared:
                if change.content is None:
                    if change.target.exists():
                        change.target.unlink()
                else:
                    stage = next(path for path, target in staged if target == change.target)
                    stage.replace(change.target)
        except BaseException:
            for stage, _ in staged:
                stage.unlink(missing_ok=True)
            self._restore(backups)
            raise
        else:
            return backups

    def _restore(self, backups: Sequence[_Backup]) -> None:
        for backup in reversed(backups):
            if backup.existed:
                if backup.content is None:  # pragma: no cover - _publish constructs this invariant
                    raise VaultWriteError("missing rollback content")
                backup.target.parent.mkdir(parents=True, exist_ok=True)
                stage = backup.target.with_name(f"{VAULT_STAGE_PREFIX}rollback-{os.urandom(8).hex()}")
                with stage.open("xb") as stream:
                    stream.write(backup.content)
                    stream.flush()
                    os.fsync(stream.fileno())
                stage.replace(backup.target)
            else:
                backup.target.unlink(missing_ok=True)
        self._remove_stale_stages()

    def _remove_stale_stages(self) -> None:
        for path in self.root.rglob(f"{VAULT_STAGE_PREFIX}*"):
            if path.is_file():
                path.unlink()

    def _require_clean(self) -> None:
        status = self._run_git("status", "--porcelain", "--untracked-files=all").stdout
        if status.strip():
            raise VaultDirtyError("vault Git working tree is dirty; commit or discard owner changes first")

    def _unstage_after_rollback(self) -> None:
        head = self._run_git("rev-parse", "--verify", "HEAD", check=False)
        if head.returncode == 0:
            self._run_git("reset", "--mixed", "HEAD")
        else:
            self._run_git("rm", "--cached", "-r", "--ignore-unmatch", ".", check=False)

    def _run_git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        try:
            completed = subprocess.run(  # noqa: S603 - fixed executable and argv, vault cwd is pinned
                [self._git, *args],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise VaultGitError(f"vault git command failed: git {args[0]}") from exc
        if check and completed.returncode != 0:
            raise VaultGitError(
                f"vault git command failed ({completed.returncode}): git {args[0]}: {completed.stderr.strip()}"
            )
        return completed


def _parse_note(content: str) -> tuple[dict[str, Any], str]:
    match = _FRONTMATTER_RE.match(content)
    if match is None:
        raise VaultFrontmatterError("system-written notes require YAML frontmatter")
    yaml = YAML(typ="safe")
    try:
        loaded = yaml.load(match.group(1))
    except Exception as exc:  # ruamel exposes several parser exception subclasses
        raise VaultFrontmatterError("invalid YAML frontmatter") from exc
    if not isinstance(loaded, dict):
        raise VaultFrontmatterError("frontmatter must be a YAML mapping")
    return dict(loaded), content[match.end() :]


def _validate_required_frontmatter(metadata: dict[str, Any], provenance_class: ProvenanceClass) -> None:
    if not isinstance(metadata.get("sbr_id"), str) or not metadata["sbr_id"].strip():
        raise VaultFrontmatterError("frontmatter requires a non-empty sbr_id")
    declared = metadata.get("provenance_class")
    if declared != provenance_class.value:
        raise VaultFrontmatterError(f"frontmatter provenance_class must be {provenance_class.value}, got {declared!r}")
    if not isinstance(metadata.get("generated_by"), str) or not metadata["generated_by"].strip():
        raise VaultFrontmatterError("frontmatter requires a non-empty generated_by")


def _render_note(metadata: dict[str, Any], body: str, provenance_class: ProvenanceClass) -> bytes:
    metadata = dict(metadata)
    metadata["provenance_class"] = provenance_class.value
    metadata["content_hash"] = _body_hash(body)
    return _serialize_note(metadata, body)


def _serialize_note(metadata: dict[str, Any], body: str) -> bytes:
    yaml = YAML(typ="safe")
    stream = StringIO()
    yaml.dump(metadata, stream)
    return f"---\n{stream.getvalue()}---\n{body}".encode()


def _sections(body: str) -> list[str]:
    starts = body.count(START_USER_SECTION)
    ends = body.count(END_USER_SECTION)
    matches = list(_USER_SECTION_RE.finditer(body))
    if starts != ends or len(matches) != starts:
        raise VaultFrontmatterError("user-section markers must be balanced and non-nested")
    return [match.group("body") for match in matches]


def _splice_user_sections(old_body: str, new_body: str) -> str:
    old_sections = _sections(old_body)
    new_sections = _sections(new_body)
    if len(old_sections) != len(new_sections):
        raise VaultFrontmatterError("an update must retain the same number of user-section marker pairs")
    sections = iter(old_sections)
    return _USER_SECTION_RE.sub(lambda match: f"{match.group('start')}{next(sections)}{match.group('end')}", new_body)


def _masked_body(body: str) -> str:
    _sections(body)
    return _USER_SECTION_RE.sub(lambda match: f"{match.group('start')}{match.group('end')}", body)


def _body_hash(body: str) -> str:
    return hash_bytes(_masked_body(body).encode("utf-8"))


__all__ = [
    "END_USER_SECTION",
    "START_USER_SECTION",
    "VaultDirtyError",
    "VaultFolder",
    "VaultFrontmatterError",
    "VaultGitError",
    "VaultMutation",
    "VaultOperation",
    "VaultOwnershipError",
    "VaultPathError",
    "VaultWriteError",
    "VaultWriteResult",
    "VaultWriter",
]
