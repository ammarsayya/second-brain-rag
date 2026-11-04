"""Archive container inventory (T-P2-08, docs/08 §6, FR-05).

Streams zip/7z/tar member entries without ever writing into a source root.
Each member's content is hashed (BLAKE3, same identity as S2) to check
whether it matches an already-known blob (``already_present``) or is new
content. New *document*-class members are extracted into
``<var>/archive_extract/<container_blob>/<safe_name>`` — never back into the
source tree — and registered as ordinary blobs. Non-document new members are
still recorded (member path, size, hash) but not physically extracted, per
docs/08 §6 ("extract new document members ... with limits").

Safety, all enforced before any extraction happens for a given container:

* **Traversal guard** — a member path containing ``..``, an absolute path, or
  a drive letter is refused (``EXCLUDED``); it is never opened.
* **Zip-bomb guard** — an archive whose members' total declared uncompressed
  size exceeds :data:`MAX_TOTAL_UNCOMPRESSED_BYTES`, or whose declared
  compression ratio exceeds :data:`MAX_COMPRESSION_RATIO`, is not processed
  further; every member is recorded ``skipped_limit``.
* **No execution, ever.** Extracted bytes are only ever hashed or written to
  ``var/archive_extract``; nothing here opens, imports, or executes anything.

v1 does not recurse into nested archives (an archive found as a member of
another archive): a nested archive is recorded as a member like any other
(hashed, and extracted if it matches the document-extension heuristic — it
generally won't, since archive extensions aren't in that list, so a nested
archive member is typically recorded but not extracted). Its own contents are
not inventoried. :data:`MAX_NESTING_DEPTH` documents the intended future
limit for when recursive inventorying is added; it is not yet enforced
because there is no recursion to bound. This is a deliberate v1 scope
limitation, not an oversight — flag it if the real-corpus reconciliation
shows a material count of archives-within-archives that this misses.

Formats: ``zip`` (stdlib ``zipfile``, streamed straight off the SourceFS file
handle), ``7z`` (``py7zr``, which has no member-streaming API — each targeted
member is extracted into a private temporary directory, hashed there, then
either copied into ``archive_extract`` or discarded), ``tar``/``tar.gz``/
``tar.bz2``/``tar.xz`` (stdlib ``tarfile``, streamed), ``rar`` (``rarfile``,
which shells out to an external ``unrar``-compatible tool for both listing
and extraction — the container is copied to a private temporary file first,
same as ``7z``). RAR requires that external tool to actually be installed and
on PATH; when it is not, RAR containers are recorded as
``unsupported_archive`` (the archive itself stays a known, classified blob —
only its member inventory is unavailable) rather than silently skipped or
crashing the run. Read failures for any format (corrupt/truncated archives
that pass magic-byte classification but fail to actually parse) are recorded
as ``read_failure`` and counted in :attr:`ArchiveRunResult.containers_read_failure`
— never silently dropped from the run's totals.

CP437 mojibake in member names (common for old, non-UTF-8-flagged zips, docs/08
§7) is repaired for *display only* (``ArchiveMember.member_name_display``);
the ``member_path`` used for extraction and hashing is never altered by that
repair. ``member_path`` is the archive library's decoded member name; for zip
it uses ``/`` separators on every OS (see ``_zip_member_path``), matching what
CPython's ``zipfile`` already produced on Windows.
"""

from __future__ import annotations

import logging
import re
import shutil
import tarfile
import tempfile
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Final

import py7zr
import rarfile

from sbr import __version__
from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.connection import transaction
from sbr.db.registry import RegistryDB
from sbr.ids import hash_stream
from sbr.obs.logging import get_logger
from sbr.provenance import ProvenanceStore
from sbr.registry.names import repair_mojibake
from sbr.safety import assert_writable
from sbr.schemas import ArchiveMember, BlobRecord, PathObservation
from sbr.schemas.registry import ArchiveMemberStatus, KnowledgeClass, ObservationState
from sbr.sourcefs import SourceFS

ARCHIVE_PRODUCER: Final = "sbr.registry.archives"
ARCHIVE_STAGE: Final = "archives"

MAX_TOTAL_UNCOMPRESSED_BYTES: Final = 5 * 1024 * 1024 * 1024  # 5 GiB per container
MAX_COMPRESSION_RATIO: Final = 300.0  # declared uncompressed / container blob size
MAX_NESTING_DEPTH: Final = 3
MAX_MEMBER_BYTES: Final = 2 * 1024 * 1024 * 1024  # a single member above this is skipped_limit

_DOCUMENT_MEMBER_EXTENSIONS: Final = frozenset(
    {
        ".pdf",
        ".doc",
        ".docx",
        ".ppt",
        ".pptx",
        ".ppsx",
        ".xls",
        ".xlsx",
        ".txt",
        ".md",
        ".tex",
        ".rtf",
        ".csv",
    }
)

_ARCHIVE_EXTRACT_DIRNAME: Final = "archive_extract"
_TRAVERSAL_PATTERN: Final = re.compile(r"(^|[\\/])\.\.([\\/]|$)")
_LOG = get_logger(__name__)


class ArchiveSafetyError(ValueError):
    """A member or container violates a hard-coded archive safety limit."""


@dataclass(frozen=True, slots=True)
class ArchiveRunResult:
    activity_id: str
    containers_considered: int
    containers_processed: int
    containers_unsupported: int
    containers_over_limit: int
    containers_read_failure: int
    members_total: int
    members_already_present: int
    members_extracted_new: int
    members_skipped_limit: int
    members_excluded: int


@dataclass(slots=True)
class _MemberPlan:
    """One member queued for hashing, with its declared (untrusted) metadata."""

    path: str
    display_name: str
    declared_size: int


_cp437_repair = repair_mojibake  # T-P2-13 promoted this to sbr.registry.names as the shared implementation


def _is_traversal(member_path: str) -> bool:
    normalized = member_path.replace("\\", "/")
    if normalized.startswith("/") or _TRAVERSAL_PATTERN.search(normalized) is not None:
        return True
    return bool(PurePosixPath(normalized).drive) or (len(normalized) > 1 and normalized[1] == ":")


def _is_document_member(path: str) -> bool:
    suffix = PurePosixPath(path.replace("\\", "/")).suffix.casefold()
    return suffix in _DOCUMENT_MEMBER_EXTENSIONS


def _safe_extract_name(member_path: str) -> str:
    """A filesystem-safe on-disk name derived from (not equal to) the member path."""
    normalized = member_path.replace("\\", "/").lstrip("/")
    parts = [part for part in normalized.split("/") if part not in ("", ".", "..")]
    return "__".join(parts) or "member"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _within_limits(members: Sequence[_MemberPlan], container_size: int) -> bool:
    total = sum(max(0, m.declared_size) for m in members)
    if total > MAX_TOTAL_UNCOMPRESSED_BYTES:
        return False
    return not (container_size > 0 and total / container_size > MAX_COMPRESSION_RATIO)


# -- format-specific member iteration --------------------------------------------------------------------------


def _zip_member_path(info: zipfile.ZipInfo) -> str:
    """The canonical member path of a zip entry: ``zipfile``'s decoded name with ``/`` separators on every OS.

    CPython's ``zipfile`` rewrites ``\\`` to ``/`` only when ``os.sep == "\\"`` (Windows), so ``info.filename`` for
    archives written by legacy DOS/Windows tools differs between hosts. Applying the same rewrite everywhere keeps the
    persisted ``member_path`` identical to what Windows produced (APPNOTE 4.4.17 mandates ``/`` anyway).
    """
    return info.filename.replace("\\", "/")


def _zip_members(stream: BinaryIO) -> tuple[list[_MemberPlan], Callable[[str], BinaryIO]]:
    zf = zipfile.ZipFile(stream)
    by_path: dict[str, zipfile.ZipInfo] = {}
    plans: list[_MemberPlan] = []
    for info in zf.infolist():
        path = _zip_member_path(info)
        if path.endswith("/"):  # directory entry (also catches "\\"-terminated legacy entries on POSIX)
            continue
        by_path[path] = info  # last entry wins, like zipfile's own name lookup
        plans.append(_MemberPlan(path, _cp437_repair(path), info.file_size))

    def opener(path: str) -> BinaryIO:
        return zf.open(by_path[path])  # type: ignore[return-value]

    return plans, opener


def _tar_members(stream: BinaryIO) -> tuple[list[_MemberPlan], Callable[[str], BinaryIO]]:
    tf = tarfile.open(fileobj=stream, mode="r:*")  # noqa: SIM115 - kept open for the returned lazy opener
    members = {m.name: m for m in tf.getmembers() if m.isfile()}
    plans = [_MemberPlan(name, _cp437_repair(name), m.size) for name, m in members.items()]

    def opener(path: str) -> BinaryIO:
        extracted = tf.extractfile(members[path])
        if extracted is None:
            raise ArchiveSafetyError(f"tar member is not a regular file: {path!r}")
        return extracted  # type: ignore[return-value]

    return plans, opener


def _rar_members(archive_path: Path) -> tuple[list[_MemberPlan], Callable[[str], BinaryIO]]:
    """List and stream RAR members via the external unrar-compatible tool (rarfile shells out to it)."""
    rf = rarfile.RarFile(archive_path)
    plans = [
        _MemberPlan(info.filename, _cp437_repair(info.filename), info.file_size)
        for info in rf.infolist()
        if not info.is_dir()
    ]

    def opener(path: str) -> BinaryIO:
        # rarfile is an untyped import (mypy override); .open() is typed Any as a result.
        return rf.open(path)  # type: ignore[no-any-return]

    return plans, opener


def _7z_members(archive_path: Path, work_dir: Path) -> tuple[list[_MemberPlan], Callable[[str], BinaryIO]]:
    with py7zr.SevenZipFile(archive_path, "r") as probe:
        entries = [entry for entry in probe.list() if not entry.is_directory]
    plans = [_MemberPlan(entry.filename, _cp437_repair(entry.filename), entry.uncompressed or 0) for entry in entries]

    def opener(path: str) -> BinaryIO:
        target = work_dir / "7z"
        target.mkdir(parents=True, exist_ok=True)
        with py7zr.SevenZipFile(archive_path, "r") as zf:
            zf.extract(path=target, targets=[path])
        extracted_path = target / path
        return extracted_path.open("rb")

    return plans, opener


# -- one container -----------------------------------------------------------------------------------------------


def _process_container(
    blob: BlobRecord,
    observation: PathObservation,
    fs: SourceFS,
    extract_root: Path,
    known_blob_ids: set[str],
    activity_id: str,
    clock: Callable[[], datetime],
    logger: logging.Logger,
) -> tuple[list[ArchiveMember], list[BlobRecord], str]:
    """Return (member rows, newly-extracted blob rows, outcome label)."""
    rar_available = True
    if blob.format == "rar":
        try:
            rarfile.tool_setup()
        except rarfile.Error:
            rar_available = False

    is_tar = blob.format in ("tar", "gz", "bz2", "xz") and observation.relpath.lower().endswith(
        (".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")
    )
    is_rar = blob.format == "rar" and rar_available
    if blob.format not in ("zip", "7z") and not is_tar and not is_rar:
        return [], [], "unsupported"

    with tempfile.TemporaryDirectory(prefix="sbr-archive-") as raw_work:
        work_dir = Path(raw_work)
        try:
            if blob.format == "zip":
                with fs.open_binary(observation.root_id, observation.relpath_raw) as stream:
                    plans, opener_factory = _zip_members(stream)
                    rows, new_blobs, outcome = _emit_members(
                        blob, plans, opener_factory, known_blob_ids, extract_root, work_dir, activity_id, clock
                    )
            elif is_tar:
                with fs.open_binary(observation.root_id, observation.relpath_raw) as stream:
                    plans, opener_factory = _tar_members(stream)
                    rows, new_blobs, outcome = _emit_members(
                        blob, plans, opener_factory, known_blob_ids, extract_root, work_dir, activity_id, clock
                    )
            elif is_rar:
                local_copy = work_dir / "container.rar"
                with (
                    fs.open_binary(observation.root_id, observation.relpath_raw) as stream,
                    local_copy.open("wb") as out,
                ):
                    shutil.copyfileobj(stream, out)
                plans, opener_factory = _rar_members(local_copy)
                rows, new_blobs, outcome = _emit_members(
                    blob, plans, opener_factory, known_blob_ids, extract_root, work_dir, activity_id, clock
                )
            else:
                local_copy = work_dir / "container.7z"
                with (
                    fs.open_binary(observation.root_id, observation.relpath_raw) as stream,
                    local_copy.open("wb") as out,
                ):
                    shutil.copyfileobj(stream, out)
                plans, opener_factory = _7z_members(local_copy, work_dir)
                rows, new_blobs, outcome = _emit_members(
                    blob, plans, opener_factory, known_blob_ids, extract_root, work_dir, activity_id, clock
                )
        except (zipfile.BadZipFile, tarfile.TarError, py7zr.exceptions.ArchiveError, rarfile.Error, OSError) as exc:
            logger.warning(
                "archive could not be inventoried",
                extra={"sbr": {"stage": ARCHIVE_STAGE, "subject_id": blob.blob_id, "error": type(exc).__name__}},
            )
            return [], [], "read_failure"
        else:
            return rows, new_blobs, outcome


def _emit_members(
    blob: BlobRecord,
    plans: list[_MemberPlan],
    opener: Callable[[str], BinaryIO],
    known_blob_ids: set[str],
    extract_root: Path,
    work_dir: Path,
    activity_id: str,
    clock: Callable[[], datetime],
) -> tuple[list[ArchiveMember], list[BlobRecord], str]:
    rows: list[ArchiveMember] = []
    new_blobs: list[BlobRecord] = []

    if not _within_limits(plans, blob.size):
        for plan in plans:
            rows.append(
                ArchiveMember(
                    container_blob=blob.blob_id,
                    member_path=plan.path,
                    member_name_display=plan.display_name,
                    member_size=max(0, plan.declared_size),
                    status=ArchiveMemberStatus.SKIPPED_LIMIT,
                    activity_id=activity_id,
                )
            )
        return rows, new_blobs, "over_limit"

    for plan in plans:
        if _is_traversal(plan.path):
            rows.append(
                ArchiveMember(
                    container_blob=blob.blob_id,
                    member_path=plan.path,
                    member_name_display=plan.display_name,
                    member_size=max(0, plan.declared_size),
                    status=ArchiveMemberStatus.EXCLUDED,
                    activity_id=activity_id,
                )
            )
            continue
        if plan.declared_size > MAX_MEMBER_BYTES:
            rows.append(
                ArchiveMember(
                    container_blob=blob.blob_id,
                    member_path=plan.path,
                    member_name_display=plan.display_name,
                    member_size=max(0, plan.declared_size),
                    status=ArchiveMemberStatus.SKIPPED_LIMIT,
                    activity_id=activity_id,
                )
            )
            continue

        with opener(plan.path) as member_stream:
            content = hash_stream(member_stream)

        if content.blob_id in known_blob_ids:
            rows.append(
                ArchiveMember(
                    container_blob=blob.blob_id,
                    member_path=plan.path,
                    member_name_display=plan.display_name,
                    member_size=content.size,
                    member_blob=content.blob_id,
                    status=ArchiveMemberStatus.ALREADY_PRESENT,
                    activity_id=activity_id,
                )
            )
            continue

        if not _is_document_member(plan.path):
            rows.append(
                ArchiveMember(
                    container_blob=blob.blob_id,
                    member_path=plan.path,
                    member_name_display=plan.display_name,
                    member_size=content.size,
                    member_blob=content.blob_id,
                    status=ArchiveMemberStatus.SKIPPED_LIMIT,
                    activity_id=activity_id,
                )
            )
            continue

        container_dir = extract_root / blob.blob_id.replace(":", "_")
        container_dir.mkdir(parents=True, exist_ok=True)
        target = container_dir / _safe_extract_name(plan.path)
        with opener(plan.path) as member_stream, target.open("wb") as out:
            shutil.copyfileobj(member_stream, out)
        known_blob_ids.add(content.blob_id)
        new_blobs.append(
            BlobRecord(
                blob_id=content.blob_id,
                size=content.size,
                first_seen_scan=blob.first_seen_scan,
                last_seen_scan=blob.last_seen_scan,
                activity_id=activity_id,
            )
        )
        rows.append(
            ArchiveMember(
                container_blob=blob.blob_id,
                member_path=plan.path,
                member_name_display=plan.display_name,
                member_size=content.size,
                member_blob=content.blob_id,
                status=ArchiveMemberStatus.EXTRACTED_NEW,
                extracted_path=str(target),
                activity_id=activity_id,
            )
        )

    return rows, new_blobs, "processed"


def inventory_archives(
    config: SbrConfig,
    db: RegistryDB,
    *,
    source_fs: SourceFS | None = None,
    extract_root: Path | None = None,
    owner: str = "system:archivist",
    clock: Callable[[], datetime] = _utcnow,
    logger: logging.Logger = _LOG,
) -> ArchiveRunResult:
    """Inventory every classified archive blob's members without touching source roots."""
    fs = source_fs or SourceFS(config)
    root = extract_root or (config.var_path / _ARCHIVE_EXTRACT_DIRNAME)
    assert_writable(root, config)  # refuses a root inside a source or protected path before anything is written

    blobs = db.repo(reg.BLOB)
    members_repo = db.repo(reg.ARCHIVE_MEMBER)
    observations = db.repo(reg.PATH_OBSERVATION)
    known_blob_ids = {b.blob_id for b in blobs.find()}

    current_by_blob: dict[str, list[PathObservation]] = {}
    for observation in observations.find({"state": ObservationState.PRESENT}):
        if observation.blob_id is not None:
            current_by_blob.setdefault(observation.blob_id, []).append(observation)
    for rows in current_by_blob.values():
        rows.sort(key=lambda row: (row.root_id, row.relpath))

    candidates = sorted(
        (b for b in blobs.find() if b.knowledge_class is KnowledgeClass.ARCHIVE), key=lambda b: b.blob_id
    )
    already_inventoried = {row.container_blob for row in members_repo.find()}

    counts = dict.fromkeys(
        (
            "processed",
            "unsupported",
            "over_limit",
            "read_failure",
            "no_current_observation",
            "already_present",
            "extracted_new",
            "skipped_limit",
            "excluded",
        ),
        0,
    )

    provenance = ProvenanceStore(db.conn, clock=clock)
    with provenance.activity(
        kind=ARCHIVE_STAGE,
        producer=ARCHIVE_PRODUCER,
        producer_version=__version__,
        agent=owner,
        params={"max_total_bytes": MAX_TOTAL_UNCOMPRESSED_BYTES, "max_ratio": MAX_COMPRESSION_RATIO},
    ) as activity:
        for blob in candidates:
            if blob.blob_id in already_inventoried:
                continue
            present = current_by_blob.get(blob.blob_id)
            if not present:
                counts["no_current_observation"] += 1
                continue
            observation = present[0]
            member_rows, new_blobs, outcome = _process_container(
                blob, observation, fs, root, known_blob_ids, activity.activity_id, clock, logger
            )
            if outcome in counts:
                counts[outcome] += 1
            if not member_rows and not new_blobs:
                continue
            with transaction(db.conn):
                for new_blob in new_blobs:
                    blobs.upsert(new_blob)
                for row in member_rows:
                    members_repo.upsert(row)
            for row in member_rows:
                counts[row.status.value] += 1
            activity.outputs.extend(row.member_blob for row in member_rows if row.member_blob is not None)

    return ArchiveRunResult(
        activity_id=activity.activity_id,
        containers_considered=len(candidates),
        containers_processed=counts["processed"],
        containers_unsupported=counts["unsupported"],
        containers_over_limit=counts["over_limit"],
        containers_read_failure=counts["read_failure"],
        members_total=(
            counts["already_present"] + counts["extracted_new"] + counts["skipped_limit"] + counts["excluded"]
        ),
        members_already_present=counts["already_present"],
        members_extracted_new=counts["extracted_new"],
        members_skipped_limit=counts["skipped_limit"],
        members_excluded=counts["excluded"],
    )


__all__ = [
    "ARCHIVE_PRODUCER",
    "ARCHIVE_STAGE",
    "MAX_COMPRESSION_RATIO",
    "MAX_MEMBER_BYTES",
    "MAX_NESTING_DEPTH",
    "MAX_TOTAL_UNCOMPRESSED_BYTES",
    "ArchiveRunResult",
    "ArchiveSafetyError",
    "inventory_archives",
]
