"""Curation ledger (T-P1-12, ADR-029, HC-12): human decisions that must survive ``var/`` rebuilds.

Each ``curation/*.yaml`` file is parsed with ruamel.yaml in round-trip mode (comments, key order and quoting style
survive being re-saved) and every record is validated against a pydantic schema. A file that is not valid YAML, or
whose shape does not match its schema, is rejected as a :class:`CurationError` naming the file and, wherever ruamel
or the record itself carries one, the exact line number — never a bare traceback.

``approvals.yaml`` is the one append-only file (HC-12, ADR-029): :func:`append_approval` is the only way this module
writes it, and it can only add a new entry, never rewrite or drop an existing one.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq
from ruamel.yaml.error import YAMLError

from sbr.schemas.base import AgentRef, BlobId, Slug

__all__ = [
    "Approval",
    "ApprovalDecision",
    "CanonicalOverride",
    "CanonicalPathOverride",
    "ConceptCurationAction",
    "ConceptCurationEntry",
    "CourseMapEntry",
    "CurationError",
    "CurationFile",
    "Exclusion",
    "ExclusionScope",
    "SensitivityOverride",
    "TaxonomyConcept",
    "append_approval",
    "load_approvals",
    "load_canonical_overrides",
    "load_canonical_path_overrides",
    "load_concept_curation",
    "load_course_map",
    "load_exclusions",
    "load_sensitivity_overrides",
    "load_taxonomy",
]

# Curation ids are hand-authored and include the owner's own folder abbreviations (Reg1, RGT, MSR2, GrdInf, BS1,
# KONleh, …), which are not lowercase-slug-shaped, so this is deliberately looser than schemas.base.Slug.
CurationId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")]


class CurationModel(BaseModel):
    """Closed-world record for a hand-edited YAML file. Unlike StrictModel, values may be coerced (YAML is not JSON)."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class CurationError(Exception):
    """A curation/*.yaml file is malformed or fails schema validation."""


# -- schemas: one per curation/*.yaml file ---------------------------------------------------------------------


class TaxonomyConcept(CurationModel):
    """One node of the bilingual, poly-hierarchical SKOS-like taxonomy (docs/12 §1, curation/taxonomy.yaml)."""

    concept_id: CurationId
    label_en: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    label_de: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    broader: list[CurationId] = Field(default_factory=list)
    narrower: list[CurationId] = Field(default_factory=list)
    related: list[CurationId] = Field(default_factory=list)


class CourseMapEntry(CurationModel):
    """One course, its owner-known folder abbreviations and matching patterns (curation/course_map.yaml)."""

    course_id: CurationId
    name: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    aliases: list[str] = Field(default_factory=list)
    folder_patterns: list[str] = Field(default_factory=list)
    domains: list[CurationId] = Field(default_factory=list)


class CanonicalOverride(CurationModel):
    """Owner override of the auto-selected canonical among a set of duplicate/twin blobs (ADR-031)."""

    canonical: BlobId
    aliases: Annotated[list[BlobId], Field(min_length=1)]
    reason: str | None = None


class CanonicalPathOverride(CurationModel):
    """Owner selection of one path observation within an exact-duplicate blob (ADR-031)."""

    blob_id: BlobId
    root_id: Slug
    relpath: Annotated[str, StringConstraints(min_length=1)]
    reason: str | None = None


class ExclusionScope(StrEnum):
    PATH = "path"
    BLOB = "blob"


class Exclusion(CurationModel):
    """An owner-added ingestion exclusion, on top of the default excludes (docs/08 §7)."""

    scope: ExclusionScope
    pattern: Annotated[str, StringConstraints(min_length=1)]
    reason: str | None = None


class SensitivityOverride(CurationModel):
    """Owner override of the automatic sensitivity classification (docs/22 §3)."""

    scope: ExclusionScope
    pattern: Annotated[str, StringConstraints(min_length=1)]
    sensitivity: Annotated[str, StringConstraints(pattern=r"^(normal|personal|third_party_personal|restricted)$")]
    reason: str | None = None


class ConceptCurationAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    RENAME = "rename"
    MERGE = "merge"


class ConceptCurationEntry(CurationModel):
    """A human correction to an AI-proposed concept (curation/concept_curation.yaml)."""

    concept_id: CurationId
    action: ConceptCurationAction
    renamed_to: CurationId | None = None
    merged_into: CurationId | None = None
    note: str | None = None


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class Approval(CurationModel):
    """One owner decision, permanently recorded (curation/approvals.yaml, HC-12). Only ever appended, never edited."""

    approval_id: CurationId
    kind: Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]
    subject: Annotated[str, StringConstraints(min_length=1)]
    decision: ApprovalDecision
    decided_by: AgentRef
    decided_at: datetime
    note: str | None = None


@dataclass(frozen=True, slots=True)
class CurationFile[M: CurationModel]:
    """One curation/*.yaml file: its validated records, in file order."""

    path: Path
    records: tuple[M, ...]


def _yaml() -> YAML:
    y = YAML(typ="rt")  # round-trip: preserves comments, key order and quoting style
    y.preserve_quotes = True
    return y


def _item_line(item: Any) -> int | None:
    """The 1-based source line of a ruamel-loaded mapping, if it tracked one."""
    lc = getattr(item, "lc", None)
    line = getattr(lc, "line", None)
    return None if line is None else line + 1


def load_curation_file[M: CurationModel](path: Path, model: type[M], *, list_key: str | None = None) -> CurationFile[M]:
    """Parse ``path`` and validate every record against ``model``.

    ``list_key`` names the top-level mapping key holding the list of records (e.g. ``"concepts"``); leave it unset
    for a file that is itself a bare list at the top level (``approvals.yaml``).
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise CurationError(f"{path}: file not found") from None
    try:
        doc = _yaml().load(raw)
    except YAMLError as exc:
        # ruamel's own message already names the line and column of the syntax problem.
        raise CurationError(f"{path}: invalid YAML: {exc}") from exc

    if list_key is None:
        items: Any = doc if doc is not None else []
        where = str(path)
    else:
        items = {} if doc is None else doc
        if not isinstance(items, Mapping):
            raise CurationError(f"{path}: expected a mapping with key {list_key!r}, got {type(items).__name__}")
        items = items.get(list_key) or []
        where = f"{path} ({list_key})"
    if not isinstance(items, list):
        raise CurationError(f"{where}: expected a list, got {type(items).__name__}")

    records: list[M] = []
    for i, item in enumerate(items):
        try:
            records.append(model.model_validate(dict(item)))
        except (ValidationError, TypeError) as exc:
            line = _item_line(item)
            loc = f"{path}:{line}" if line is not None else str(path)
            raise CurationError(f"{loc}: entry {i}: {exc}") from exc
    return CurationFile(path=path, records=tuple(records))


def load_taxonomy(path: Path) -> CurationFile[TaxonomyConcept]:
    return load_curation_file(path, TaxonomyConcept, list_key="concepts")


def load_course_map(path: Path) -> CurationFile[CourseMapEntry]:
    return load_curation_file(path, CourseMapEntry, list_key="courses")


def load_canonical_overrides(path: Path) -> CurationFile[CanonicalOverride]:
    return load_curation_file(path, CanonicalOverride, list_key="overrides")


def load_canonical_path_overrides(path: Path) -> CurationFile[CanonicalPathOverride]:
    return load_curation_file(path, CanonicalPathOverride, list_key="overrides")


def load_exclusions(path: Path) -> CurationFile[Exclusion]:
    return load_curation_file(path, Exclusion, list_key="exclusions")


def load_sensitivity_overrides(path: Path) -> CurationFile[SensitivityOverride]:
    return load_curation_file(path, SensitivityOverride, list_key="overrides")


def load_concept_curation(path: Path) -> CurationFile[ConceptCurationEntry]:
    return load_curation_file(path, ConceptCurationEntry, list_key="entries")


def load_approvals(path: Path) -> CurationFile[Approval]:
    return load_curation_file(path, Approval, list_key=None)


def append_approval(path: Path, approval: Approval) -> None:
    """Append one approval to ``approvals.yaml``, preserving every existing entry and its comments (append-only).

    Raises :class:`CurationError` if ``approval_id`` already exists (an approval is recorded once, permanently) or
    if the file does not hold the bare list of entries it is defined as.
    """
    yaml = _yaml()
    doc: Any = yaml.load(path.read_text(encoding="utf-8")) if path.exists() else None
    if doc is None:
        doc = CommentedSeq()
    if not isinstance(doc, list):
        raise CurationError(f"{path}: approvals.yaml must be a bare list of entries")

    existing_ids = {item.get("approval_id") for item in doc if isinstance(item, Mapping)}
    if approval.approval_id in existing_ids:
        raise CurationError(f"{path}: approval {approval.approval_id!r} is already recorded")

    before = list(doc)
    payload = json.loads(approval.model_dump_json())
    doc.append(payload)
    if list(doc)[: len(before)] != before:
        raise CurationError(f"{path}: append would have disturbed an existing entry; refusing to write")

    with path.open("w", encoding="utf-8") as f:
        yaml.dump(doc, f)
