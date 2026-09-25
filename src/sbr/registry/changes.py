"""Change detection for registry scans (T-P2-03, ingestion stage after S2).

Call :func:`detect_changes` only after S1 has completed the requested scan and
S2 has fully drained that scan's hash jobs.  Move detection needs the new path's
blob identity, and modified detection needs S2's durable ``previous_blob_id``
manifest artifact.  The function refuses incomplete, failed, or error-bearing
scans so an unreadable subtree cannot be mistaken for deletion.

``VERSION_OF`` is directed from the new blob to the previous blob: the source
blob *is a version of* the destination blob.  No registry row is ever deleted.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from sbr import __version__
from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.connection import transaction
from sbr.db.registry import RegistryDB
from sbr.provenance import ProvenanceStore
from sbr.registry.scan import HASH_STAGE, HASH_STAGE_VERSION, hash_job_version
from sbr.schemas import BlobRelation, ChangeEvent, PathObservation
from sbr.schemas.operations import WorkItemState
from sbr.schemas.provenance import ActivityStatus
from sbr.schemas.registry import (
    BlobStatus,
    ChangeType,
    ObservationState,
    RelationStatus,
    RelationType,
    ScanStatus,
)

CHANGE_PRODUCER: Final = "sbr.registry.changes"


@dataclass(frozen=True, slots=True)
class ChangeRunResult:
    """Summary of one completed (or already-completed) change-detection pass."""

    activity_id: str
    events: tuple[ChangeEvent, ...]

    @property
    def counts(self) -> dict[str, int]:
        return {kind.value: sum(event.type is kind for event in self.events) for kind in ChangeType}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _blob_id(observation: PathObservation) -> str:
    if observation.blob_id is None:
        raise ValueError("change detection requires every relevant observation to be hashed")
    return observation.blob_id


def _prior_result(db: RegistryDB, scan_id: str) -> ChangeRunResult | None:
    activities = db.repo(reg.ACTIVITY).find({"kind": "change_detection"})
    completed = [
        activity
        for activity in activities
        if activity.producer == CHANGE_PRODUCER
        and activity.status is ActivityStatus.SUCCEEDED
        and scan_id in activity.inputs
    ]
    if not completed:
        return None
    activity = completed[-1]
    events = tuple(db.repo(reg.CHANGE_EVENT).find({"scan_id": scan_id}))
    return ChangeRunResult(activity.activity_id, events)


def detect_changes(
    config: SbrConfig,
    db: RegistryDB,
    root_id: str,
    scan_id: str,
    *,
    hash_stage_version: str = HASH_STAGE_VERSION,
) -> ChangeRunResult:
    """Classify one fully-hashed scan and persist its append-only changes."""
    config.source_root(root_id)
    scan = db.repo(reg.SCAN).get(scan_id)
    if scan is None or scan.root_id != root_id:
        raise ValueError("scan does not belong to the requested source root")
    if scan.status is not ScanStatus.COMPLETED:
        raise ValueError("change detection requires a completed scan")
    if scan.errors:
        raise ValueError("change detection refuses a scan with source observation errors")

    prior = _prior_result(db, scan_id)
    if prior is not None:
        return prior

    observations = db.repo(reg.PATH_OBSERVATION)
    blobs = db.repo(reg.BLOB)
    jobs = db.repo(reg.WORK_ITEM)
    outputs = db.repo(reg.WORK_OUTPUT)
    events_repo = db.repo(reg.CHANGE_EVENT)
    relations = db.repo(reg.BLOB_RELATION)

    snapshot_version = hash_job_version(scan_id, hash_stage_version)
    scan_jobs = jobs.find({"stage": HASH_STAGE, "stage_version": snapshot_version})
    if any(job.state is not WorkItemState.DONE for job in scan_jobs):
        raise ValueError("change detection requires all hash jobs for the scan to be done")

    previous_by_obs: dict[str, str] = {}
    for job in scan_jobs:
        if job.output_manifest_id is None:
            raise ValueError("completed hash job has no output manifest")
        output = outputs.get(job.output_manifest_id)
        if output is None or output.artifacts.get("scan_id") != scan_id:
            raise ValueError("hash output manifest does not match the requested scan")
        previous_by_obs[job.subject_id] = output.artifacts.get("previous_blob_id", "")

    root_observations = observations.find({"root_id": root_id})
    current = sorted(
        (obs for obs in root_observations if obs.state is ObservationState.PRESENT and obs.last_seen_scan == scan_id),
        key=lambda obs: obs.relpath,
    )
    if any(obs.blob_id is None for obs in current):
        raise ValueError("change detection requires every current observation to be hashed")
    new_observations = [obs for obs in current if obs.first_seen_scan == scan_id]
    vanished = sorted(
        (obs for obs in root_observations if obs.state is ObservationState.PRESENT and obs.last_seen_scan != scan_id),
        key=lambda obs: obs.relpath,
    )

    new_by_blob: dict[str, list[PathObservation]] = defaultdict(list)
    vanished_by_blob: dict[str, list[PathObservation]] = defaultdict(list)
    for obs in new_observations:
        new_by_blob[_blob_id(obs)].append(obs)
    for obs in vanished:
        if obs.blob_id is not None:
            vanished_by_blob[obs.blob_id].append(obs)

    moves: list[tuple[PathObservation, PathObservation]] = []
    move_destinations: set[str] = set()
    moved_sources: set[str] = set()
    for blob_id in sorted(set(new_by_blob) & set(vanished_by_blob)):
        for old, new in zip(vanished_by_blob[blob_id], new_by_blob[blob_id], strict=False):
            moves.append((old, new))
            moved_sources.add(old.obs_id)
            move_destinations.add(new.obs_id)

    provenance = ProvenanceStore(db.conn, clock=_utcnow)
    created: list[ChangeEvent] = []
    with (
        provenance.activity(
            kind="change_detection",
            producer=CHANGE_PRODUCER,
            producer_version=__version__,
            agent="system:change-detector",
            params={"root_id": root_id, "scan_id": scan_id, "hash_stage_version": hash_stage_version},
            inputs=[scan_id],
        ) as activity,
        transaction(db.conn),
    ):
        active_blob_ids = {obs.blob_id for obs in current if obs.blob_id is not None}
        for blob_id in sorted(active_blob_ids):
            blob = blobs.get(blob_id)
            if blob is not None and blob.status is BlobStatus.ORPHANED:
                blobs.upsert(blob.model_copy(update={"status": BlobStatus.ACTIVE, "activity_id": activity.activity_id}))

        for obs in new_observations:
            if obs.obs_id in move_destinations:
                continue
            blob_id = _blob_id(obs)
            blob = blobs.get(blob_id)
            if blob is None:
                raise LookupError("current observation references an unavailable blob")
            event = ChangeEvent(
                scan_id=scan_id,
                type=ChangeType.NEW if blob.first_seen_scan == scan_id else ChangeType.ALIAS,
                obs_id=obs.obs_id,
                blob_id=blob_id,
                activity_id=activity.activity_id,
            )
            events_repo.insert(event)
            created.append(event)

        for obs in current:
            if obs.first_seen_scan == scan_id:
                continue
            previous_blob_id = previous_by_obs.get(obs.obs_id, "")
            if not previous_blob_id or previous_blob_id == obs.blob_id:
                continue
            blob_id = _blob_id(obs)
            relation = BlobRelation(
                src_blob=blob_id,
                dst_blob=previous_blob_id,
                type=RelationType.VERSION_OF,
                confidence=1.0,
                status=RelationStatus.CONFIRMED,
                evidence={"obs_id": obs.obs_id, "scan_id": scan_id},
                activity_id=activity.activity_id,
            )
            relations.upsert(relation)
            event = ChangeEvent(
                scan_id=scan_id,
                type=ChangeType.MODIFIED,
                obs_id=obs.obs_id,
                blob_id=blob_id,
                details={"previous_blob_id": previous_blob_id},
                activity_id=activity.activity_id,
            )
            events_repo.insert(event)
            created.append(event)

        for old, new in moves:
            updated = old.model_copy(update={"state": ObservationState.MOVED, "activity_id": activity.activity_id})
            observations.upsert(updated)
            event = ChangeEvent(
                scan_id=scan_id,
                type=ChangeType.MOVED,
                obs_id=old.obs_id,
                blob_id=old.blob_id,
                details={"new_obs_id": new.obs_id, "new_relpath": new.relpath},
                activity_id=activity.activity_id,
            )
            events_repo.insert(event)
            created.append(event)

        deleted = [obs for obs in vanished if obs.obs_id not in moved_sources]
        for obs in deleted:
            observations.upsert(
                obs.model_copy(update={"state": ObservationState.DELETED, "activity_id": activity.activity_id})
            )
            event = ChangeEvent(
                scan_id=scan_id,
                type=ChangeType.DELETED,
                obs_id=obs.obs_id,
                blob_id=obs.blob_id,
                activity_id=activity.activity_id,
            )
            events_repo.insert(event)
            created.append(event)

        remaining_present_blob_ids = {
            obs.blob_id
            for obs in root_observations
            if obs.state is ObservationState.PRESENT and obs.obs_id not in {item.obs_id for item in vanished}
        }
        for blob_id in sorted({obs.blob_id for obs in deleted if obs.blob_id is not None}):
            if blob_id in remaining_present_blob_ids:
                continue
            blob = blobs.get(blob_id)
            if blob is not None and blob.status is not BlobStatus.ORPHANED:
                blobs.upsert(
                    blob.model_copy(update={"status": BlobStatus.ORPHANED, "activity_id": activity.activity_id})
                )

        activity.outputs.extend(
            dict.fromkeys(
                [event.obs_id for event in created] + [event.blob_id for event in created if event.blob_id is not None]
            )
        )

    return ChangeRunResult(activity.activity_id, tuple(created))


__all__ = ["CHANGE_PRODUCER", "ChangeRunResult", "detect_changes"]
