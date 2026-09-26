"""Registry records (docs/31 §1). Paths are observations of content-addressed blobs (ADR-003).

Every derived record carries the ``activity_id`` of the activity that produced it (docs/32 conventions, PV-1).
"""

from __future__ import annotations

import unicodedata
from enum import StrEnum
from typing import Annotated, Any, Self

from pydantic import Field, StringConstraints, field_validator, model_validator

from sbr.schemas.base import ActivityId, BlobId, Confidence, NonNeg, ObsId, ScanId, Slug, StrictModel, UtcDatetime


class RootKind(StrEnum):
    UNIVERSITY = "university"
    EXTERNAL_ACCEPTED = "external_accepted"
    PERSONAL = "personal"
    QUARANTINE = "quarantine"  # research quarantine only (docs/16); the duplicate quarantine is never registered


class KnowledgeClass(StrEnum):
    DOCUMENT = "document"
    OFFICE = "office"
    SPREADSHEET = "spreadsheet"
    CODE = "code"
    DATA = "data"
    MEDIA = "media"
    ARCHIVE = "archive"
    IMAGE = "image"
    TOOL_ARTIFACT = "tool_artifact"
    JUNK = "junk"
    EXECUTABLE = "executable"
    THIRD_PARTY_REFERENCE = "third_party_reference"
    UNKNOWN = "unknown"


class Sensitivity(StrEnum):
    NORMAL = "normal"
    PERSONAL = "personal"
    THIRD_PARTY_PERSONAL = "third_party_personal"
    RESTRICTED = "restricted"


class BlobStatus(StrEnum):
    ACTIVE = "active"
    ORPHANED = "orphaned"
    EXCLUDED = "excluded"


class HashMode(StrEnum):
    FULL = "full"
    FULL_LOWPRIO_PENDING = "full_lowprio_pending"


class ScanStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class ObservationState(StrEnum):
    PRESENT = "present"
    MOVED = "moved"
    DELETED = "deleted"


class ArchiveMemberStatus(StrEnum):
    ALREADY_PRESENT = "already_present"
    EXTRACTED_NEW = "extracted_new"
    SKIPPED_LIMIT = "skipped_limit"
    EXCLUDED = "excluded"


class RelationType(StrEnum):
    TWIN_CANDIDATE = "twin_candidate"
    TWIN_OF = "twin_of"
    VERSION_OF = "version_of"
    NEAR_DUPLICATE_OF = "near_duplicate_of"
    CONTAINS_TEXT_OF = "contains_text_of"
    ANNOTATED_VARIANT_OF = "annotated_variant_of"
    SOLUTION_OF = "solution_of"


class RelationStatus(StrEnum):
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class ChangeType(StrEnum):
    """docs/08 §3 change semantics."""

    NEW = "new"  # new path, new blob
    ALIAS = "alias"  # new path, known blob
    MOVED = "moved"
    MODIFIED = "modified"
    DELETED = "deleted"


class SourceRootRecord(StrictModel):
    root_id: Slug
    path: str
    kind: RootKind
    read_only: bool
    added_at: UtcDatetime

    @model_validator(mode="after")
    def _read_only(self) -> Self:
        if self.kind is not RootKind.QUARANTINE and not self.read_only:
            raise ValueError("read_only must be true for all non-quarantine roots (HC-01)")
        return self


class ScanRecord(StrictModel):
    scan_id: ScanId
    root_id: Slug
    started_at: UtcDatetime
    finished_at: UtcDatetime | None = None
    status: ScanStatus = ScanStatus.RUNNING
    files_seen: NonNeg = 0
    bytes_seen: NonNeg = 0
    errors: NonNeg = 0
    code_version: str
    activity_id: ActivityId


class BlobRecord(StrictModel):
    blob_id: BlobId
    size: NonNeg
    magic_type: str | None = None
    format: str | None = None
    knowledge_class: KnowledgeClass = KnowledgeClass.UNKNOWN
    encrypted: bool = False
    sensitivity: Sensitivity = Sensitivity.NORMAL
    status: BlobStatus = BlobStatus.ACTIVE
    first_seen_scan: ScanId
    last_seen_scan: ScanId
    hash_mode: HashMode = HashMode.FULL
    canonical_obs_id: ObsId | None = None
    activity_id: ActivityId


class PathObservation(StrictModel):
    """One path seen in one root. ``relpath`` is NFC-normalized; ``relpath_raw`` is the exact OS string."""

    obs_id: ObsId
    root_id: Slug
    relpath: Annotated[str, StringConstraints(min_length=1)]
    relpath_raw: Annotated[str, StringConstraints(min_length=1)]
    display_name: str
    blob_id: BlobId | None = None  # None until hashed
    size: NonNeg
    mtime_ns: NonNeg
    first_seen_scan: ScanId
    last_seen_scan: ScanId
    state: ObservationState = ObservationState.PRESENT
    in_archive: ObsId | None = None
    folder_tokens: list[str] = Field(default_factory=list)
    is_mirror_candidate: bool = False
    activity_id: ActivityId

    @model_validator(mode="after")
    def _nfc(self) -> Self:
        if unicodedata.normalize("NFC", self.relpath) != self.relpath:
            raise ValueError("relpath must be NFC-normalized (the original goes to relpath_raw)")
        if unicodedata.normalize("NFC", self.relpath_raw) != self.relpath:
            raise ValueError("relpath must equal NFC(relpath_raw)")
        return self


class ArchiveMember(StrictModel):
    container_blob: BlobId
    member_path: str
    member_name_display: str
    member_size: NonNeg
    member_blob: BlobId | None = None
    status: ArchiveMemberStatus
    extracted_path: str | None = None  # always under var/archive_extract, never the source tree
    activity_id: ActivityId


class BlobClassification(StrictModel):
    blob_id: BlobId
    genre: str | None = None
    genre_confidence: Confidence | None = None
    course_id: str | None = None
    course_confidence: Confidence | None = None
    language_guess: str | None = None
    semester: str | None = None
    institution: str | None = None
    isbn: str | None = None
    rules_version: str
    activity_id: ActivityId


class BlobRelation(StrictModel):
    src_blob: BlobId
    dst_blob: BlobId
    type: RelationType
    confidence: Confidence
    evidence: dict[str, Any] = Field(default_factory=dict)
    status: RelationStatus = RelationStatus.CANDIDATE
    activity_id: ActivityId

    @model_validator(mode="after")
    def _distinct(self) -> Self:
        if self.src_blob == self.dst_blob:
            raise ValueError("a blob relation needs two distinct blobs")
        return self


class ChangeEvent(StrictModel):
    scan_id: ScanId
    type: ChangeType
    obs_id: ObsId
    blob_id: BlobId | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    activity_id: ActivityId

    @field_validator("details")
    @classmethod
    def _small(cls, v: dict[str, Any]) -> dict[str, Any]:
        if len(v) > 32:
            raise ValueError("details is a small annotation map, not a payload")
        return v
