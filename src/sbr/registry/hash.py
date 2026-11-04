"""BLAKE3 content hashing worker (T-P2-02, ingestion stage S2).

One provenance activity covers one worker invocation, including every batch it
leases.  Source content is streamed only through :meth:`SourceFS.open_binary`
into :func:`sbr.ids.hash_stream`; source metadata is checked through SourceFS
before and after the read so a concurrently changed file is retried instead of
being associated with stale observation metadata.

Hash-job priority is assigned by S1 through
:func:`sbr.registry.priority.hash_priority`.  That helper is intentionally a
small extension allow-list, not the magic-byte detection or classification
owned by T-P2-04.  Consequently this stage leaves ``magic_type`` and ``format``
unset for new blobs and preserves them on existing blobs.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from sbr import __version__
from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.connection import transaction
from sbr.db.registry import RegistryDB
from sbr.db.repository import Repository
from sbr.ids import ContentHash, hash_stream
from sbr.jobs import DEFAULT_LEASE_MS, JobQueue
from sbr.obs.logging import get_logger
from sbr.provenance import ProvenanceStore
from sbr.registry.scan import HASH_STAGE, HASH_STAGE_VERSION
from sbr.schemas import ActivityStatus, BlobRecord, PathObservation, WorkItem
from sbr.schemas.registry import ScanRecord
from sbr.sourcefs import SourceFS, SourceStat

HASH_PRODUCER: Final = "sbr.registry.hash"
DEFAULT_BATCH_SIZE: Final = 16
_LOG = get_logger(__name__)


class SourceChangedError(OSError):
    """The source no longer matches the metadata captured by S1."""


@dataclass(frozen=True, slots=True)
class HashRunResult:
    """Summary of one S2 worker invocation."""

    activity_id: str
    leased: int
    hashed: int
    bytes_hashed: int
    failed: int
    elapsed_seconds: float


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _matches_observation(stat: SourceStat, observation: PathObservation) -> bool:
    return stat.is_file and not stat.is_link and stat.size == observation.size and stat.mtime_ns == observation.mtime_ns


def _error_label(exc: Exception) -> str:
    """Return a useful queue error without leaking a source path."""
    if isinstance(exc, OSError):
        return f"{type(exc).__name__}: errno={exc.errno} winerror={getattr(exc, 'winerror', None)}"
    return type(exc).__name__


def _latest_scan(existing: BlobRecord, observation: PathObservation, scans: Repository[ScanRecord]) -> str:
    """Choose the later last-seen scan without relying on processing order."""
    left = scans.get(existing.last_seen_scan)
    right = scans.get(observation.last_seen_scan)
    if left is None or right is None:
        raise LookupError("referenced scan record is unavailable")
    return left.scan_id if left.started_at >= right.started_at else right.scan_id


def _require_observation(observations: Repository[PathObservation], subject_id: str) -> PathObservation:
    observation = observations.get(subject_id)
    if observation is None:
        raise LookupError("hash subject observation is unavailable")
    return observation


def _hash_observation(fs: SourceFS, observation: PathObservation, progress: Callable[[int], None]) -> ContentHash:
    before = fs.stat(observation.root_id, observation.relpath_raw)
    if not _matches_observation(before, observation):
        raise SourceChangedError("source metadata changed before hashing")
    with fs.open_binary(observation.root_id, observation.relpath_raw) as stream:
        content = hash_stream(stream, progress=progress)
    after = fs.stat(observation.root_id, observation.relpath_raw)
    if not _matches_observation(after, observation) or content.size != observation.size:
        raise SourceChangedError("source metadata changed while hashing")
    return content


def _blob_record(
    existing: BlobRecord | None,
    content: ContentHash,
    observation: PathObservation,
    scans: Repository[ScanRecord],
    activity_id: str,
) -> BlobRecord:
    if existing is None:
        return BlobRecord(
            blob_id=content.blob_id,
            size=content.size,
            # A path may predate this content (modified in place); blob birth is
            # the scan whose snapshot S2 is hashing, not path birth.
            first_seen_scan=observation.last_seen_scan,
            last_seen_scan=observation.last_seen_scan,
            activity_id=activity_id,
        )
    if existing.size != content.size:
        raise ValueError("existing blob size does not match its content hash")
    return existing.model_copy(
        update={"last_seen_scan": _latest_scan(existing, observation, scans), "activity_id": activity_id}
    )


def _heartbeat(
    jobs: JobQueue,
    items: Sequence[WorkItem],
    lease_ms: int,
    monotonic: Callable[[], float],
) -> Callable[[int], None]:
    next_heartbeat = monotonic() + max(1.0, lease_ms / 2_000)

    def extend_if_due(_: int) -> None:
        nonlocal next_heartbeat
        now = monotonic()
        if now < next_heartbeat:
            return
        for pending in items:
            assert pending.lease_token is not None  # noqa: S101 - leased batch invariant
            jobs.extend(pending.job_id, pending.lease_token, lease_ms=lease_ms)
        next_heartbeat = now + max(1.0, lease_ms / 2_000)

    return extend_if_due


def hash_pending(
    config: SbrConfig,
    db: RegistryDB,
    *,
    source_fs: SourceFS | None = None,
    queue: JobQueue | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    lease_ms: int = DEFAULT_LEASE_MS,
    owner: str = "system:hasher",
    clock: Callable[[], datetime] = _utcnow,
    monotonic: Callable[[], float] = time.monotonic,
    logger: logging.Logger = _LOG,
) -> HashRunResult:
    """Lease and process all currently-ready S2 work, isolating per-item errors."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    if lease_ms <= 0:
        raise ValueError("lease_ms must be positive")

    fs = source_fs or SourceFS(config)
    jobs = queue or JobQueue(db.conn, owner=owner)
    provenance = ProvenanceStore(db.conn, clock=clock)
    observations = db.repo(reg.PATH_OBSERVATION)
    blobs = db.repo(reg.BLOB)
    scans = db.repo(reg.SCAN)
    activity = provenance.start_activity(
        kind=HASH_STAGE,
        producer=HASH_PRODUCER,
        producer_version=__version__,
        agent=owner,
        params={"stage_version": HASH_STAGE_VERSION, "batch_size": batch_size, "lease_ms": lease_ms},
    )
    started = monotonic()
    leased_count = hashed_count = bytes_hashed = failed_count = 0
    outputs: list[str] = []
    terminal_error: BaseException | None = None

    try:
        while batch := jobs.lease(HASH_STAGE, owner=owner, count=batch_size, lease_ms=lease_ms):
            leased_count += len(batch)
            for index, item in enumerate(batch):
                assert item.lease_token is not None  # noqa: S101 - WorkItem validates leased fields
                remaining = batch[index:]
                for pending in remaining:
                    assert pending.lease_token is not None  # noqa: S101 - leased batch invariant
                    jobs.extend(pending.job_id, pending.lease_token, lease_ms=lease_ms)

                try:
                    observation = _require_observation(observations, item.subject_id)
                    content = _hash_observation(fs, observation, _heartbeat(jobs, remaining, lease_ms, monotonic))

                    with transaction(db.conn):
                        existing = blobs.get(content.blob_id)
                        blob = _blob_record(existing, content, observation, scans, activity.activity_id)
                        blobs.upsert(blob)
                        observations.upsert(
                            observation.model_copy(
                                update={"blob_id": content.blob_id, "activity_id": activity.activity_id}
                            )
                        )
                        jobs.complete(
                            item.job_id,
                            item.lease_token,
                            artifacts={
                                "blob_id": content.blob_id,
                                "observation_id": observation.obs_id,
                                "previous_blob_id": observation.blob_id or "",
                                "scan_id": observation.last_seen_scan,
                            },
                        )
                    hashed_count += 1
                    bytes_hashed += content.size
                    outputs.extend((content.blob_id, observation.obs_id))
                except Exception as exc:  # noqa: BLE001 - one poison source must not stop its batch
                    failed_count += 1
                    jobs.fail(item.job_id, item.lease_token, error=_error_label(exc))
                    logger.warning(
                        "source content could not be hashed",
                        extra={
                            "sbr": {
                                "stage": HASH_STAGE,
                                "subject_id": item.subject_id,
                                "error": _error_label(exc),
                            }
                        },
                    )
    except BaseException as exc:  # noqa: BLE001 - terminal state must persist for interrupts and fatal errors
        terminal_error = exc

    elapsed = max(0.0, monotonic() - started)
    provenance.finish_activity(
        activity.activity_id,
        ActivityStatus.CANCELLED
        if isinstance(terminal_error, KeyboardInterrupt)
        else ActivityStatus.FAILED
        if terminal_error is not None
        else ActivityStatus.SUCCEEDED,
        outputs=list(dict.fromkeys(outputs)),
        notes=None if terminal_error is None else f"error:{type(terminal_error).__name__}",
    )
    if terminal_error is not None:
        raise terminal_error

    logger.info(
        "content hashing completed",
        extra={
            "sbr": {
                "stage": HASH_STAGE,
                "activity_id": activity.activity_id,
                "leased": leased_count,
                "hashed": hashed_count,
                "bytes_hashed": bytes_hashed,
                "failed": failed_count,
                "elapsed_seconds": elapsed,
                "bytes_per_second": bytes_hashed / elapsed if elapsed > 0 else 0.0,
            }
        },
    )
    return HashRunResult(
        activity_id=activity.activity_id,
        leased=leased_count,
        hashed=hashed_count,
        bytes_hashed=bytes_hashed,
        failed=failed_count,
        elapsed_seconds=elapsed,
    )


__all__ = ["DEFAULT_BATCH_SIZE", "HASH_PRODUCER", "HashRunResult", "SourceChangedError", "hash_pending"]
