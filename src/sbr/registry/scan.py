"""Deterministic, read-only source scanner (T-P2-01, ingestion stage S1).

Only :class:`sbr.sourcefs.SourceFS` touches source roots.  The walk is iterative and
keeps at most one directory listing plus the directory stack in memory.  Resume is
at root granularity: an interrupted scan remains recorded as ``interrupted`` and a
later run walks that root again, reusing present observations by ``(root, relpath)``.
Each observation update and its idempotent hash enqueue are one transaction, so a
restart cannot leave a newly observed or changed path without its S2 job.
"""

from __future__ import annotations

import logging
import unicodedata
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Final

from sbr import __version__
from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.connection import transaction
from sbr.db.registry import RegistryDB
from sbr.ids import new_id
from sbr.jobs import JobQueue
from sbr.obs.logging import get_logger
from sbr.provenance import ProvenanceStore
from sbr.schemas import ActivityStatus, PathObservation, ScanRecord, SourceRootRecord
from sbr.schemas.registry import ObservationState, RootKind, ScanStatus
from sbr.sourcefs import SourceAccessError, SourceEntry, SourceFS, split_relpath

HASH_STAGE: Final = "hash"
HASH_STAGE_VERSION: Final = "1"
SCAN_PRODUCER: Final = "sbr.registry.scan"
_LOG = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _folder_tokens(relpath: str) -> list[str]:
    return [unicodedata.normalize("NFC", part).casefold() for part in split_relpath(relpath)[:-1]]


def _walk(source_fs: SourceFS, root_id: str, on_error: Callable[[str], None]) -> Iterator[SourceEntry]:
    """Yield regular-file entries in deterministic depth-first order."""
    pending: list[str | SourceEntry] = [""]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            try:
                entries = sorted(source_fs.iter_dir(root_id, item), key=lambda entry: entry.name)
            except (OSError, SourceAccessError) as exc:
                on_error(type(exc).__name__)
                continue
            pending.extend(reversed(entries))
            continue
        if item.error is not None:
            on_error(item.error)
        elif item.is_link:
            continue
        elif item.is_dir:
            pending.append(item.relpath)
        elif item.is_file:
            yield item


def scan_root(
    config: SbrConfig,
    db: RegistryDB,
    root_id: str,
    *,
    source_fs: SourceFS | None = None,
    queue: JobQueue | None = None,
    clock: Callable[[], datetime] = _utcnow,
    logger: logging.Logger = _LOG,
    hash_stage_version: str = HASH_STAGE_VERSION,
) -> ScanRecord:
    """Scan one configured root, persist observations, and enqueue S2 for new/changed files.

    Files are never opened: S1 uses only metadata returned by ``SourceFS.iter_dir``.
    Expected per-entry and per-directory access failures are counted and scanning
    continues.  Unexpected failures mark the scan failed and are re-raised.
    """
    root = config.source_root(root_id)
    fs = source_fs or SourceFS(config)
    jobs = queue or JobQueue(db.conn)
    provenance = ProvenanceStore(db.conn, clock=clock)
    roots = db.repo(reg.SOURCE_ROOT)
    scans = db.repo(reg.SCAN)
    observations = db.repo(reg.PATH_OBSERVATION)
    now = clock()
    existing_root = roots.get(root.id)
    roots.upsert(
        SourceRootRecord(
            root_id=root.id,
            path=root.path,
            kind=RootKind(root.kind.value),
            read_only=True,
            added_at=existing_root.added_at if existing_root is not None else now,
        )
    )

    activity = provenance.start_activity(
        kind="scan",
        producer=SCAN_PRODUCER,
        producer_version=__version__,
        agent="system:scanner",
        params={"root_id": root.id, "hash_stage_version": hash_stage_version},
    )
    scan = ScanRecord(
        scan_id=new_id("scan"),
        root_id=root.id,
        started_at=now,
        code_version=__version__,
        activity_id=activity.activity_id,
    )
    scans.insert(scan)
    files_seen = bytes_seen = errors = 0

    def record_error(error: str) -> None:
        nonlocal errors
        errors += 1
        logger.warning(
            "source entry could not be observed",
            extra={"sbr": {"stage": "scan", "subject_id": root.id, "error": error}},
        )

    status = ScanStatus.RUNNING
    terminal_error: BaseException | None = None
    try:
        for entry in _walk(fs, root.id, record_error):
            if entry.size is None or entry.mtime_ns is None:
                record_error(entry.error or "metadata unavailable")
                continue
            raw = entry.relpath
            normalized = unicodedata.normalize("NFC", raw)
            current_rows = observations.find(
                {"root_id": root.id, "relpath": normalized, "state": ObservationState.PRESENT}, limit=1
            )
            current = current_rows[0] if current_rows else None
            changed = current is None or current.size != entry.size or current.mtime_ns != entry.mtime_ns
            current_blob = current.blob_id if current is not None else None
            observation = PathObservation(
                obs_id=current.obs_id if current is not None else new_id("obs"),
                root_id=root.id,
                relpath=normalized,
                relpath_raw=raw,
                display_name=entry.name,
                blob_id=None if changed else current_blob,
                size=entry.size,
                mtime_ns=entry.mtime_ns,
                first_seen_scan=current.first_seen_scan if current is not None else scan.scan_id,
                last_seen_scan=scan.scan_id,
                state=ObservationState.PRESENT,
                in_archive=current.in_archive if current is not None else None,
                folder_tokens=_folder_tokens(raw),
                is_mirror_candidate=current.is_mirror_candidate if current is not None else False,
                activity_id=activity.activity_id,
            )
            with transaction(db.conn):
                observations.upsert(observation)
                if changed:
                    jobs.enqueue(observation.obs_id, HASH_STAGE, hash_stage_version)
            files_seen += 1
            bytes_seen += entry.size
        status = ScanStatus.COMPLETED
    except KeyboardInterrupt as exc:
        status = ScanStatus.INTERRUPTED
        terminal_error = exc
    except Exception as exc:  # noqa: BLE001 - every unexpected failure must persist terminal scan/activity state
        status = ScanStatus.FAILED
        terminal_error = exc

    finished = scan.model_copy(
        update={
            "finished_at": max(clock(), scan.started_at),
            "status": status,
            "files_seen": files_seen,
            "bytes_seen": bytes_seen,
            "errors": errors,
        }
    )
    ScanRecord.model_validate(finished.model_dump(mode="json"), strict=False)
    scans.upsert(finished)
    provenance.finish_activity(
        activity.activity_id,
        ActivityStatus.CANCELLED
        if status is ScanStatus.INTERRUPTED
        else ActivityStatus.FAILED
        if status is ScanStatus.FAILED
        else ActivityStatus.SUCCEEDED,
        outputs=[scan.scan_id],
        notes=None if terminal_error is None else f"error:{type(terminal_error).__name__}",
    )
    if terminal_error is not None:
        raise terminal_error
    logger.info(
        "source scan completed",
        extra={
            "sbr": {
                "stage": "scan",
                "subject_id": root.id,
                "scan_id": scan.scan_id,
                "files_seen": files_seen,
                "bytes_seen": bytes_seen,
                "errors": errors,
            }
        },
    )
    return finished


def scan_sources(
    config: SbrConfig,
    db: RegistryDB,
    *,
    root_ids: tuple[str, ...] | None = None,
    source_fs: SourceFS | None = None,
) -> list[ScanRecord]:
    """Scan selected roots, or every configured root in configuration order."""
    selected = root_ids if root_ids is not None else tuple(root.id for root in config.roots.sources)
    return [scan_root(config, db, root_id, source_fs=source_fs) for root_id in selected]


__all__ = ["HASH_STAGE", "HASH_STAGE_VERSION", "scan_root", "scan_sources"]
