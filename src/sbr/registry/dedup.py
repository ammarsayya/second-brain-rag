"""Exact-duplicate grouping and canonical-path selection (T-P2-06, ADR-031).

Exact duplicates are already represented by multiple PRESENT
:class:`~sbr.schemas.registry.PathObservation` rows sharing one ``blob_id``.
This metadata-only stage chooses one of those observations and stores its
``obs_id`` on :class:`~sbr.schemas.registry.BlobRecord`; it never changes or
deletes an observation.

``curation/canonical_overrides.yaml`` cannot express this choice: its
``CanonicalOverride`` relates distinct blob ids and is reserved for later
twin/near-duplicate curation.  Exact-duplicate owner choices therefore live in
the additive ``canonical_path_overrides.yaml`` ledger.  Each record anchors the
group by blob id and selects one PRESENT observation by its owner-readable
``(root_id, relpath)`` identity; selection must resolve exactly once.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from typing import Final

from sbr import __version__
from sbr.config import SbrConfig
from sbr.curation import CanonicalPathOverride, load_canonical_path_overrides
from sbr.db import registry as reg
from sbr.db.connection import transaction
from sbr.db.registry import RegistryDB
from sbr.provenance import ProvenanceStore
from sbr.schemas import PathObservation
from sbr.schemas.registry import ObservationState

DEDUP_PRODUCER: Final = "sbr.registry.dedup"
DEDUP_STAGE: Final = "dedup"
DEDUP_HEURISTIC_VERSION: Final = "1"
DEFAULT_OVERRIDES_NAME: Final = "canonical_path_overrides.yaml"

_DUPLICATE_DOWNLOAD_MARKER: Final = re.compile(r"(?:\(\d+\)|kopie)", re.IGNORECASE)


class DedupError(ValueError):
    """A canonical-path override is ambiguous, stale, or inconsistent."""


@dataclass(frozen=True, slots=True)
class DedupRunResult:
    activity_id: str
    considered: int
    duplicate_groups: int
    singletons: int
    without_present_observation: int
    updated: int
    overrides_applied: int


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _path_identity(relpath: str) -> str:
    """Normalize separators and case for owner-authored Windows relpaths."""
    return str(PureWindowsPath(relpath.replace("/", "\\"))).casefold()


def _has_duplicate_download_marker(observation: PathObservation) -> bool:
    return _DUPLICATE_DOWNLOAD_MARKER.search(PureWindowsPath(observation.relpath).name) is not None


def canonical_sort_key(observation: PathObservation) -> tuple[bool, int, int, bool, str, str, str, str]:
    """Return the documented automatic canonical ranking, best value first.

    Path depth precedes character length because an otherwise short filename in
    a deeply redundant directory tree is less meaningful than a top-level path.
    Root and observation ids only disambiguate equal relpaths deterministically.
    """
    path = PureWindowsPath(observation.relpath)
    return (
        observation.is_mirror_candidate,
        len(path.parts),
        len(observation.relpath),
        _has_duplicate_download_marker(observation),
        observation.relpath.casefold(),
        observation.relpath,
        observation.root_id,
        observation.obs_id,
    )


def choose_canonical(observations: Sequence[PathObservation]) -> PathObservation:
    """Choose one PRESENT observation using the deterministic automatic heuristic."""
    if not observations:
        raise ValueError("canonical selection needs at least one observation")
    if any(observation.state is not ObservationState.PRESENT for observation in observations):
        raise ValueError("canonical selection accepts PRESENT observations only")
    return min(observations, key=canonical_sort_key)


def _resolve_overrides(
    overrides: Sequence[CanonicalPathOverride],
    observations_by_blob: dict[str, list[PathObservation]],
) -> dict[str, PathObservation]:
    resolved: dict[str, PathObservation] = {}
    for override in overrides:
        if override.blob_id in resolved:
            raise DedupError(f"more than one canonical-path override exists for blob {override.blob_id}")
        matches = [
            observation
            for observation in observations_by_blob.get(override.blob_id, ())
            if observation.root_id == override.root_id
            and _path_identity(observation.relpath) == _path_identity(override.relpath)
        ]
        if len(matches) != 1:
            raise DedupError(
                f"canonical-path override for blob {override.blob_id} resolved to {len(matches)} PRESENT observations"
            )
        resolved[override.blob_id] = matches[0]
    return resolved


def select_canonical_paths(
    config: SbrConfig,
    db: RegistryDB,
    *,
    overrides_path: Path | None = None,
    owner: str = "system:deduplicator",
    clock: Callable[[], datetime] = _utcnow,
) -> DedupRunResult:
    """Set every blob's canonical PRESENT observation without touching sources or deleting rows."""
    override_file = overrides_path or Path(config.roots.curation) / DEFAULT_OVERRIDES_NAME
    overrides = load_canonical_path_overrides(override_file).records

    observations_by_blob: dict[str, list[PathObservation]] = defaultdict(list)
    for observation in db.repo(reg.PATH_OBSERVATION).find({"state": ObservationState.PRESENT}):
        if observation.blob_id is not None:
            observations_by_blob[observation.blob_id].append(observation)
    for rows in observations_by_blob.values():
        rows.sort(key=canonical_sort_key)
    selected_overrides = _resolve_overrides(overrides, observations_by_blob)

    blobs = db.repo(reg.BLOB)
    candidates = sorted(blobs.find(), key=lambda blob: blob.blob_id)
    duplicate_groups = sum(len(observations_by_blob.get(blob.blob_id, ())) > 1 for blob in candidates)
    singletons = sum(len(observations_by_blob.get(blob.blob_id, ())) == 1 for blob in candidates)
    without_present = sum(not observations_by_blob.get(blob.blob_id) for blob in candidates)
    updated = 0
    overrides_applied = 0

    provenance = ProvenanceStore(db.conn, clock=clock)
    with (
        provenance.activity(
            kind=DEDUP_STAGE,
            producer=DEDUP_PRODUCER,
            producer_version=__version__,
            agent=owner,
            params={
                "heuristic_version": DEDUP_HEURISTIC_VERSION,
                "overrides_file": override_file.name,
            },
        ) as activity,
        transaction(db.conn),
    ):
        for blob in candidates:
            present = observations_by_blob.get(blob.blob_id, ())
            override = selected_overrides.get(blob.blob_id)
            canonical_obs_id = (
                override.obs_id if override is not None else choose_canonical(present).obs_id if present else None
            )
            overrides_applied += override is not None
            if blob.canonical_obs_id == canonical_obs_id:
                continue
            blobs.upsert(
                blob.model_copy(update={"canonical_obs_id": canonical_obs_id, "activity_id": activity.activity_id})
            )
            activity.outputs.append(blob.blob_id)
            updated += 1

    return DedupRunResult(
        activity_id=activity.activity_id,
        considered=len(candidates),
        duplicate_groups=duplicate_groups,
        singletons=singletons,
        without_present_observation=without_present,
        updated=updated,
        overrides_applied=overrides_applied,
    )


__all__ = [
    "DEDUP_HEURISTIC_VERSION",
    "DEDUP_PRODUCER",
    "DEDUP_STAGE",
    "DEFAULT_OVERRIDES_NAME",
    "DedupError",
    "DedupRunResult",
    "canonical_sort_key",
    "choose_canonical",
    "select_canonical_paths",
]
