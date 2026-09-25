"""Metadata-only exclusions and sensitivity classification (T-P2-05).

This S5 stage runs after file classification and uses only :class:`BlobRecord`
and :class:`PathObservation` metadata.  It never opens source files or reads raw
bytes.  Version 1 deliberately has no content-based signals (for example,
tables containing names and grades) because text extraction does not exist yet.

Automatic path rules classify grade-list names as ``third_party_personal`` and
identity/application-document names as ``restricted``.  ``personal`` is not
assigned automatically: it remains available through owner curation overrides
only because the current policy has no crisp automatic rule for it.

Owner exclusions are additive: the curation schema can add an exclusion but has
no include/unexclude action, so it cannot reverse a default exclusion.  Owner
sensitivity overrides do replace automatic sensitivity, including with
``normal`` or ``personal``.  When several sensitivity overrides match, the last
matching ledger entry wins.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from typing import Final

from sbr import __version__
from sbr.config import SbrConfig
from sbr.curation import (
    Exclusion,
    ExclusionScope,
    SensitivityOverride,
    load_exclusions,
    load_sensitivity_overrides,
)
from sbr.db import registry as reg
from sbr.db.connection import transaction
from sbr.db.registry import RegistryDB
from sbr.provenance import ProvenanceStore
from sbr.schemas import BlobRecord, PathObservation
from sbr.schemas.registry import BlobStatus, KnowledgeClass, ObservationState, Sensitivity

SENSITIVITY_PRODUCER: Final = "sbr.registry.sensitivity"
SENSITIVITY_STAGE: Final = "sensitivity"
SENSITIVITY_RULES_VERSION: Final = "1"
DEFAULT_EXCLUSIONS_NAME: Final = "exclusions.yaml"
DEFAULT_OVERRIDES_NAME: Final = "sensitivity_overrides.yaml"

_DEFAULT_EXCLUDED_CLASSES: Final = frozenset(
    {
        KnowledgeClass.JUNK,
        KnowledgeClass.TOOL_ARTIFACT,
        KnowledgeClass.EXECUTABLE,
        KnowledgeClass.THIRD_PARTY_REFERENCE,
    }
)


@dataclass(frozen=True, slots=True)
class PathSensitivityRule:
    label: str
    sensitivity: Sensitivity
    pattern: re.Pattern[str]


# Restricted rules intentionally precede grade-list rules: if aliases or one
# path match both groups, the safer class wins.  The negative lookbehind makes
# Noten match as a word or substring (including Labornoten), but never in Knoten.
PATH_SENSITIVITY_RULES: Final = (
    PathSensitivityRule("Vertrag", Sensitivity.RESTRICTED, re.compile("vertrag", re.IGNORECASE)),
    PathSensitivityRule("Bewerbung", Sensitivity.RESTRICTED, re.compile("bewerbung", re.IGNORECASE)),
    PathSensitivityRule("Lebenslauf", Sensitivity.RESTRICTED, re.compile("lebenslauf", re.IGNORECASE)),
    PathSensitivityRule("Zeugnis", Sensitivity.RESTRICTED, re.compile("zeugnis", re.IGNORECASE)),
    PathSensitivityRule("Ausweis", Sensitivity.RESTRICTED, re.compile("ausweis", re.IGNORECASE)),
    PathSensitivityRule("Immatrikulation", Sensitivity.RESTRICTED, re.compile("immatrikulation", re.IGNORECASE)),
    PathSensitivityRule("Noten", Sensitivity.THIRD_PARTY_PERSONAL, re.compile(r"(?<!k)noten", re.IGNORECASE)),
    PathSensitivityRule(
        "Ergebnisliste", Sensitivity.THIRD_PARTY_PERSONAL, re.compile(r"ergebnislisten?", re.IGNORECASE)
    ),
)


@dataclass(frozen=True, slots=True)
class SensitivityDecision:
    sensitivity: Sensitivity
    rule: str
    owner_override: bool = False


@dataclass(frozen=True, slots=True)
class BlobDecision:
    status: BlobStatus
    sensitivity: Sensitivity
    sensitivity_rule: str
    exclusion_rule: str | None


@dataclass(frozen=True, slots=True)
class SensitivityRunResult:
    activity_id: str
    considered: int
    updated: int
    excluded: int
    sensitivity_counts: dict[str, int]


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _glob_matches(relpath: str, pattern: str) -> bool:
    """Match a curation relpath glob with Windows path and case semantics."""
    path = PureWindowsPath(relpath)
    normalized = pattern.replace("/", "\\")
    if path.match(normalized):
        return True
    # pathlib treats ``**/name`` as requiring a parent; glob users generally
    # expect it to match the same name at the source-root top level as well.
    return normalized.startswith("**\\") and path.match(normalized[3:])


def _curation_matches(
    scope: ExclusionScope,
    pattern: str,
    blob_id: str,
    observations: Sequence[PathObservation],
) -> bool:
    if scope is ExclusionScope.BLOB:
        return pattern == blob_id
    return any(_glob_matches(observation.relpath, pattern) for observation in observations)


def automatic_sensitivity(relpath: str) -> SensitivityDecision:
    """Return the first automatic path/name rule matching ``relpath``."""
    for rule in PATH_SENSITIVITY_RULES:
        if rule.pattern.search(relpath) is not None:
            return SensitivityDecision(rule.sensitivity, rule.label)
    return SensitivityDecision(Sensitivity.NORMAL, "Normal")


def decide_sensitivity(
    blob_id: str,
    observations: Sequence[PathObservation],
    overrides: Sequence[SensitivityOverride],
) -> SensitivityDecision:
    """Classify all current aliases, then apply owner overrides in ledger order."""
    automatic = [automatic_sensitivity(observation.relpath) for observation in observations]
    decision = next((item for item in automatic if item.sensitivity is Sensitivity.RESTRICTED), None)
    if decision is None:
        decision = next((item for item in automatic if item.sensitivity is Sensitivity.THIRD_PARTY_PERSONAL), None)
    if decision is None:
        decision = SensitivityDecision(Sensitivity.NORMAL, "Normal")

    for override in overrides:
        if _curation_matches(override.scope, override.pattern, blob_id, observations):
            decision = SensitivityDecision(Sensitivity(override.sensitivity), "Owner override", owner_override=True)
    return decision


def decide_blob(
    blob: BlobRecord,
    observations: Sequence[PathObservation],
    exclusions: Sequence[Exclusion],
    overrides: Sequence[SensitivityOverride],
) -> BlobDecision:
    """Compute one blob's status and sensitivity without touching source data."""
    exclusion_rule: str | None = None
    if blob.knowledge_class in _DEFAULT_EXCLUDED_CLASSES:
        exclusion_rule = f"knowledge_class:{blob.knowledge_class.value}"
    elif blob.encrypted:
        exclusion_rule = "encrypted"
    elif any(_curation_matches(item.scope, item.pattern, blob.blob_id, observations) for item in exclusions):
        exclusion_rule = "owner_exclusion"

    status = BlobStatus.EXCLUDED if exclusion_rule is not None else blob.status
    if exclusion_rule is None and blob.status is BlobStatus.EXCLUDED:
        # Recompute exclusions on every run so removing an owner-added rule takes
        # effect.  ORPHANED is preserved because it is lifecycle state, not a
        # sensitivity-stage decision.
        status = BlobStatus.ACTIVE

    sensitivity = decide_sensitivity(blob.blob_id, observations, overrides)
    return BlobDecision(status, sensitivity.sensitivity, sensitivity.rule, exclusion_rule)


def classify_sensitivity(
    config: SbrConfig,
    db: RegistryDB,
    *,
    exclusions_path: Path | None = None,
    overrides_path: Path | None = None,
    owner: str = "system:sensitivity",
    clock: Callable[[], datetime] = _utcnow,
) -> SensitivityRunResult:
    """Apply default exclusions and sensitivity metadata to every known blob."""
    curation_root = Path(config.roots.curation)
    exclusion_file = exclusions_path or curation_root / DEFAULT_EXCLUSIONS_NAME
    override_file = overrides_path or curation_root / DEFAULT_OVERRIDES_NAME
    exclusions = load_exclusions(exclusion_file).records
    overrides = load_sensitivity_overrides(override_file).records

    blobs = db.repo(reg.BLOB)
    observations_by_blob: dict[str, list[PathObservation]] = {}
    for observation in db.repo(reg.PATH_OBSERVATION).find({"state": ObservationState.PRESENT}):
        if observation.blob_id is not None:
            observations_by_blob.setdefault(observation.blob_id, []).append(observation)
    for rows in observations_by_blob.values():
        rows.sort(key=lambda row: (row.root_id, row.relpath))

    candidates = sorted(blobs.find(), key=lambda blob: blob.blob_id)
    updated = 0
    excluded = 0
    counts: Counter[str] = Counter()
    provenance = ProvenanceStore(db.conn, clock=clock)
    with provenance.activity(
        kind=SENSITIVITY_STAGE,
        producer=SENSITIVITY_PRODUCER,
        producer_version=__version__,
        agent=owner,
        params={
            "rules_version": SENSITIVITY_RULES_VERSION,
            "exclusions_file": exclusion_file.name,
            "overrides_file": override_file.name,
        },
    ) as activity:
        for blob in candidates:
            decision = decide_blob(blob, observations_by_blob.get(blob.blob_id, ()), exclusions, overrides)
            counts[decision.sensitivity.value] += 1
            excluded += decision.status is BlobStatus.EXCLUDED
            if blob.status is decision.status and blob.sensitivity is decision.sensitivity:
                continue
            classified = blob.model_copy(
                update={
                    "status": decision.status,
                    "sensitivity": decision.sensitivity,
                    "activity_id": activity.activity_id,
                }
            )
            with transaction(db.conn):
                blobs.upsert(classified)
            activity.outputs.append(blob.blob_id)
            updated += 1

    return SensitivityRunResult(
        activity_id=activity.activity_id,
        considered=len(candidates),
        updated=updated,
        excluded=excluded,
        sensitivity_counts={item.value: counts[item.value] for item in Sensitivity},
    )


__all__ = [
    "DEFAULT_EXCLUSIONS_NAME",
    "DEFAULT_OVERRIDES_NAME",
    "PATH_SENSITIVITY_RULES",
    "SENSITIVITY_PRODUCER",
    "SENSITIVITY_RULES_VERSION",
    "SENSITIVITY_STAGE",
    "BlobDecision",
    "PathSensitivityRule",
    "SensitivityDecision",
    "SensitivityRunResult",
    "automatic_sensitivity",
    "classify_sensitivity",
    "decide_blob",
    "decide_sensitivity",
]
