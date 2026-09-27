"""Portable backup and fail-closed restore for the local durability layer (T-P13-02).

Database snapshots are always produced by :meth:`sbr.db.migrations.Migrator.backup`, which uses SQLite's online
backup API.  The completed snapshots are then packaged with a full-history Git bundle of the independent vault
repository and byte-for-byte copies of the validated, Git-tracked curation ledger.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import shutil
import sqlite3
import stat
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Final, NoReturn, Self

from sbr.config import SbrConfig, is_within, path_key
from sbr.curation import (
    CurationFile,
    load_approvals,
    load_canonical_overrides,
    load_canonical_path_overrides,
    load_concept_curation,
    load_course_map,
    load_exclusions,
    load_sensitivity_overrides,
    load_taxonomy,
)
from sbr.db.registry import RegistryDB
from sbr.obs.trace import TraceDB
from sbr.safety import assert_outside, assert_writable, protected_roots

BACKUP_FORMAT_VERSION: Final = 1
MANIFEST_NAME: Final = "manifest.json"
_STAMP_FORMAT: Final = "%Y%m%dT%H%M%S%fZ"
_SNAPSHOT_NAME_RE: Final = re.compile(r"^(registry|traces)-p13-\d{8}T\d{12}Z\.sqlite$")

type CurationLoader = Callable[[Path], CurationFile[Any]]

CURATION_LOADERS: Final[Mapping[str, CurationLoader]] = {
    "approvals.yaml": load_approvals,
    "canonical_overrides.yaml": load_canonical_overrides,
    "canonical_path_overrides.yaml": load_canonical_path_overrides,
    "concept_curation.yaml": load_concept_curation,
    "course_map.yaml": load_course_map,
    "exclusions.yaml": load_exclusions,
    "sensitivity_overrides.yaml": load_sensitivity_overrides,
    "taxonomy.yaml": load_taxonomy,
}


class BackupError(RuntimeError):
    """Backup creation or restoration failed without publishing a complete result."""


def _fail(message: str) -> NoReturn:
    raise BackupError(message)


@dataclass(frozen=True, slots=True)
class BackupFile:
    """One checksummed file in a backup package."""

    purpose: str
    relative_path: PurePosixPath
    size: int
    sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "purpose": self.purpose,
            "relative_path": self.relative_path.as_posix(),
            "size": self.size,
            "sha256": self.sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        if not isinstance(value, dict) or set(value) != {"purpose", "relative_path", "size", "sha256"}:
            raise BackupError("backup manifest has an invalid file entry")
        purpose = value["purpose"]
        relative = value["relative_path"]
        size = value["size"]
        digest = value["sha256"]
        if not isinstance(purpose, str) or not purpose:
            raise BackupError("backup manifest file purpose must be a non-empty string")
        if not isinstance(relative, str):
            raise BackupError("backup manifest relative_path must be a string")
        path = PurePosixPath(relative)
        if path.is_absolute() or path.as_posix() != relative or any(part in {"", ".", ".."} for part in path.parts):
            raise BackupError(f"unsafe backup manifest path: {relative!r}")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise BackupError("backup manifest file size must be a non-negative integer")
        if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise BackupError("backup manifest file sha256 is invalid")
        return cls(purpose=purpose, relative_path=path, size=size, sha256=digest)


@dataclass(frozen=True, slots=True)
class BackupManifest:
    """Self-contained inventory and restore contract for one backup package."""

    backup_id: str
    created_at: str
    registry_schema_version: int
    traces_schema_version: int
    vault_head: str
    files: tuple[BackupFile, ...]
    format_version: int = BACKUP_FORMAT_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "backup_id": self.backup_id,
            "created_at": self.created_at,
            "registry_schema_version": self.registry_schema_version,
            "traces_schema_version": self.traces_schema_version,
            "vault_head": self.vault_head,
            "files": [entry.to_dict() for entry in self.files],
        }

    def to_json_bytes(self) -> bytes:
        return (json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n").encode()

    @classmethod
    def from_json_bytes(cls, raw: bytes) -> Self:
        try:
            value: Any = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise BackupError("backup manifest is not valid UTF-8 JSON") from exc
        expected = {
            "format_version",
            "backup_id",
            "created_at",
            "registry_schema_version",
            "traces_schema_version",
            "vault_head",
            "files",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise BackupError("backup manifest has unexpected fields")
        if value["format_version"] != BACKUP_FORMAT_VERSION:
            raise BackupError(f"unsupported backup format version {value['format_version']!r}")
        strings = (value["backup_id"], value["created_at"], value["vault_head"])
        if not all(isinstance(item, str) and item for item in strings):
            raise BackupError("backup manifest identity fields are invalid")
        versions = (value["registry_schema_version"], value["traces_schema_version"])
        if not all(isinstance(item, int) and not isinstance(item, bool) and item >= 0 for item in versions):
            raise BackupError("backup manifest schema versions are invalid")
        file_values = value["files"]
        if not isinstance(file_values, list):
            raise BackupError("backup manifest files must be a list")
        files = tuple(BackupFile.from_dict(item) for item in file_values)
        purposes = [entry.purpose for entry in files]
        paths = [entry.relative_path for entry in files]
        if len(set(purposes)) != len(purposes) or len(set(paths)) != len(paths):
            raise BackupError("backup manifest contains duplicate purposes or paths")
        required = {"registry", "traces", "vault", *(f"curation:{name}" for name in CURATION_LOADERS)}
        if set(purposes) != required:
            raise BackupError("backup manifest does not contain exactly the required durability files")
        by_purpose = {entry.purpose: entry.relative_path for entry in files}
        if by_purpose["vault"] != PurePosixPath("vault.bundle"):
            raise BackupError("backup manifest vault path is invalid")
        for name in CURATION_LOADERS:
            if by_purpose[f"curation:{name}"] != PurePosixPath("curation", name):
                raise BackupError(f"backup manifest curation path is invalid: {name}")
        for purpose in ("registry", "traces"):
            path = by_purpose[purpose]
            if path.parent != PurePosixPath("databases") or not _SNAPSHOT_NAME_RE.fullmatch(path.name):
                raise BackupError(f"backup manifest database path is invalid: {purpose}")
        return cls(
            backup_id=value["backup_id"],
            created_at=value["created_at"],
            registry_schema_version=value["registry_schema_version"],
            traces_schema_version=value["traces_schema_version"],
            vault_head=value["vault_head"],
            files=files,
        )

    @classmethod
    def read(cls, path: Path) -> Self:
        try:
            return cls.from_json_bytes(path.read_bytes())
        except FileNotFoundError:
            raise BackupError(f"backup manifest not found: {path}") from None


@dataclass(frozen=True, slots=True)
class BackupResult:
    backup_dir: Path
    manifest_path: Path
    manifest: BackupManifest


@dataclass(frozen=True, slots=True)
class RestoreResult:
    target_dir: Path
    registry_path: Path
    traces_path: Path
    vault_path: Path
    curation_path: Path
    registry_schema_version: int
    traces_schema_version: int
    vault_head: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _remove_readonly(function: Callable[..., object], path: str, _exc: BaseException) -> None:
    """Let rollback remove read-only Git object files on Windows."""
    Path(path).chmod(stat.S_IWRITE)
    function(path)


def _remove_tree(path: Path) -> None:
    shutil.rmtree(path, onexc=_remove_readonly)


def _entry(root: Path, purpose: str, path: Path) -> BackupFile:
    return BackupFile(
        purpose=purpose,
        relative_path=PurePosixPath(path.relative_to(root).as_posix()),
        size=path.stat().st_size,
        sha256=_sha256(path),
    )


def _git_executable() -> str:
    git = shutil.which("git")
    if git is None:
        raise BackupError("git executable is required for vault backup and restore")
    return git


def _run_git(git: str, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(  # noqa: S603 - fixed executable and argv, cwd is explicit
            [git, *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BackupError(f"git command failed: git {args[0]}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise BackupError(f"git command failed ({completed.returncode}): git {args[0]}: {detail}")
    return completed


def _create_vault_bundle(config: SbrConfig, target: Path) -> str:
    root = config.vault_path
    if not (root / ".git").is_dir():
        raise BackupError(f"configured vault is not an independent Git repository: {root}")
    git = _git_executable()
    actual = _run_git(git, root, "rev-parse", "--show-toplevel").stdout.strip()
    if path_key(actual) != path_key(root.resolve()):
        raise BackupError("configured vault path is not the root of its own Git repository")
    if _run_git(git, root, "status", "--porcelain", "--untracked-files=all").stdout.strip():
        raise BackupError("vault Git working tree is dirty; commit owner changes before backup")
    head = _run_git(git, root, "rev-parse", "HEAD").stdout.strip()
    _run_git(git, root, "bundle", "create", str(target), "--all")
    _run_git(git, root, "bundle", "verify", str(target))
    return head


def _database_state(path: Path, required_table: str) -> int:
    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise BackupError(f"cannot open SQLite snapshot: {path.name}") from exc
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()
        if result != ("ok",):
            raise BackupError(f"SQLite integrity check failed for {path.name}: {result!r}")
        table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (required_table,)
        ).fetchone()
        if table is None:
            raise BackupError(f"SQLite snapshot {path.name} is missing required table {required_table}")
        row = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()
        return int(row[0])
    except sqlite3.Error as exc:
        raise BackupError(f"cannot validate SQLite snapshot: {path.name}") from exc
    finally:
        conn.close()


def _copy_snapshot(snapshot: Path, target_dir: Path, expected_stem: str) -> Path:
    if (
        not snapshot.is_file()
        or not _SNAPSHOT_NAME_RE.fullmatch(snapshot.name)
        or not snapshot.name.startswith(expected_stem + "-")
    ):
        raise BackupError(f"Migrator.backup returned an unexpected snapshot path: {snapshot}")
    target = target_dir / snapshot.name
    shutil.copy2(snapshot, target)
    return target


def _reject_backup_overlap(config: SbrConfig, destination: Path) -> None:
    roots = (config.var_path, config.vault_path, Path(config.roots.curation))
    # A backup below var/ is intentional; nesting it below the vault or ledger would modify authoritative state.
    for root in roots[1:]:
        if is_within(destination, root) or is_within(root, destination):
            raise BackupError(f"backup destination overlaps authoritative state: {root}")


def create_backup(
    config: SbrConfig,
    destination: Path | None = None,
    *,
    registry_db: RegistryDB | None = None,
) -> BackupResult:
    """Create and atomically publish one complete durability backup.

    ``destination`` is a parent directory.  The default is ``var/backups/system``.  Supplying the CLI runtime's
    already-open ``registry_db`` avoids an unnecessary second connection; direct callers may omit it.
    """
    destination = (destination or config.var_path / "backups" / "system").resolve()
    assert_writable(destination, config)
    _reject_backup_overlap(config, destination)
    destination.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime(_STAMP_FORMAT)
    backup_id = f"sbr-backup-{stamp}"
    final = destination / backup_id
    stage = destination / f".{backup_id}-{secrets.token_hex(8)}.tmp"
    if final.exists():
        raise BackupError(f"backup destination already exists: {final}")
    stage.mkdir()

    owned_registry = registry_db is None
    registry = registry_db
    trace: TraceDB | None = None
    try:
        registry_path = config.db_dir / "registry.sqlite"
        traces_path = config.traces_dir / "traces.sqlite"
        if not registry_path.is_file():
            _fail(f"registry database not found: {registry_path}")
        if not traces_path.is_file():
            _fail(f"trace database not found: {traces_path}")
        if registry is None:
            registry = RegistryDB.open(config)
            registry.migrate()
        trace = TraceDB.open(config)
        trace.migrate()

        database_dir = stage / "databases"
        database_dir.mkdir()
        registry_snapshot = _copy_snapshot(registry.migrator.backup("p13"), database_dir, "registry")
        traces_snapshot = _copy_snapshot(trace.migrator.backup("p13"), database_dir, "traces")
        registry_version = _database_state(registry_snapshot, "source_root")
        traces_version = _database_state(traces_snapshot, "span")

        bundle = stage / "vault.bundle"
        vault_head = _create_vault_bundle(config, bundle)

        curation_dir = stage / "curation"
        curation_dir.mkdir()
        source_curation = Path(config.roots.curation)
        for name, loader in CURATION_LOADERS.items():
            source = source_curation / name
            if source.is_symlink() or not source.is_file():
                _fail(f"curation ledger file is missing or not a regular file: {source}")
            target = curation_dir / name
            shutil.copy2(source, target)
            loader(target)

        files = (
            _entry(stage, "registry", registry_snapshot),
            _entry(stage, "traces", traces_snapshot),
            _entry(stage, "vault", bundle),
            *(_entry(stage, f"curation:{name}", curation_dir / name) for name in CURATION_LOADERS),
        )
        manifest = BackupManifest(
            backup_id=backup_id,
            created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            registry_schema_version=registry_version,
            traces_schema_version=traces_version,
            vault_head=vault_head,
            files=files,
        )
        (stage / MANIFEST_NAME).write_bytes(manifest.to_json_bytes())
        stage.replace(final)
        return BackupResult(final, final / MANIFEST_NAME, manifest)
    except BackupError:
        raise
    except Exception as exc:
        raise BackupError(f"backup creation failed: {type(exc).__name__}: {exc}") from exc
    finally:
        if trace is not None:
            trace.close()
        if owned_registry and registry is not None:
            registry.close()
        if stage.exists():
            _remove_tree(stage)


def _verified_files(backup_dir: Path, manifest: BackupManifest) -> dict[str, Path]:
    resolved_root = backup_dir.resolve()
    found: dict[str, Path] = {}
    for entry in manifest.files:
        path = backup_dir.joinpath(*entry.relative_path.parts)
        try:
            resolved = path.resolve(strict=True)
        except FileNotFoundError:
            raise BackupError(f"backup file is missing: {entry.relative_path}") from None
        if resolved.parent != resolved_root and resolved_root not in resolved.parents:
            raise BackupError(f"backup file escapes package root: {entry.relative_path}")
        if path.is_symlink() or not resolved.is_file():
            raise BackupError(f"backup entry is not a regular file: {entry.relative_path}")
        if resolved.stat().st_size != entry.size or _sha256(resolved) != entry.sha256:
            raise BackupError(f"backup file failed integrity verification: {entry.relative_path}")
        found[entry.purpose] = resolved
    return found


def _reject_restore_overlap(config: SbrConfig, backup_dir: Path, target: Path) -> None:
    if is_within(target, backup_dir) or is_within(backup_dir, target):
        raise BackupError("restore target must not overlap the backup package")
    for root in (config.var_path, config.vault_path, Path(config.roots.curation)):
        if is_within(target, root) or is_within(root, target):
            raise BackupError(f"restore target overlaps configured live state: {root}")


def restore_backup(config: SbrConfig, backup: Path, target: Path) -> RestoreResult:
    """Restore a verified backup into a non-existent target, then functionally validate every restored store."""
    backup_dir = backup.parent if backup.name == MANIFEST_NAME else backup
    manifest_path = backup if backup.name == MANIFEST_NAME else backup / MANIFEST_NAME
    assert_outside(backup_dir.resolve(), protected_roots(config))
    target = target.resolve()
    assert_writable(target, config)
    _reject_restore_overlap(config, backup_dir.resolve(), target)
    if target.exists():
        raise BackupError(f"restore target must not exist: {target}")

    manifest = BackupManifest.read(manifest_path)
    files = _verified_files(backup_dir, manifest)
    git = _git_executable()
    # ``bundle verify`` itself requires a repository.  ``list-heads`` validates readability on a truly clean
    # machine path; after cloning below, the stronger verify runs inside the restored repository.
    _run_git(git, backup_dir, "bundle", "list-heads", str(files["vault"]))

    target.parent.mkdir(parents=True, exist_ok=True)
    stage = target.parent / f".{target.name}-restore-{secrets.token_hex(8)}.tmp"
    stage.mkdir()
    try:
        registry_path = stage / "var" / "db" / "registry.sqlite"
        traces_path = stage / "var" / "traces" / "traces.sqlite"
        registry_path.parent.mkdir(parents=True)
        traces_path.parent.mkdir(parents=True)
        shutil.copy2(files["registry"], registry_path)
        shutil.copy2(files["traces"], traces_path)
        registry_version = _database_state(registry_path, "source_root")
        traces_version = _database_state(traces_path, "span")
        if registry_version != manifest.registry_schema_version or traces_version != manifest.traces_schema_version:
            _fail("restored database schema version does not match the manifest")

        vault_path = stage / "vault"
        _run_git(git, stage, "clone", str(files["vault"]), str(vault_path))
        _run_git(git, vault_path, "bundle", "verify", str(files["vault"]))
        vault_head = _run_git(git, vault_path, "rev-parse", "HEAD").stdout.strip()
        if vault_head != manifest.vault_head:
            _fail("restored vault HEAD does not match the manifest")
        if _run_git(git, vault_path, "status", "--porcelain", "--untracked-files=all").stdout.strip():
            _fail("restored vault working tree is not clean")

        curation_path = stage / "curation"
        curation_path.mkdir()
        for name, loader in CURATION_LOADERS.items():
            restored = curation_path / name
            shutil.copy2(files[f"curation:{name}"], restored)
            loader(restored)

        stage.replace(target)
        return RestoreResult(
            target_dir=target,
            registry_path=target / "var" / "db" / "registry.sqlite",
            traces_path=target / "var" / "traces" / "traces.sqlite",
            vault_path=target / "vault",
            curation_path=target / "curation",
            registry_schema_version=registry_version,
            traces_schema_version=traces_version,
            vault_head=vault_head,
        )
    except BackupError:
        raise
    except Exception as exc:
        raise BackupError(f"restore failed: {type(exc).__name__}: {exc}") from exc
    finally:
        if stage.exists():
            _remove_tree(stage)


__all__ = [
    "BACKUP_FORMAT_VERSION",
    "CURATION_LOADERS",
    "MANIFEST_NAME",
    "BackupError",
    "BackupFile",
    "BackupManifest",
    "BackupResult",
    "RestoreResult",
    "create_backup",
    "restore_backup",
]
