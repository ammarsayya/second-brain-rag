"""Typed contracts shared across components (T-P1-05, docs/32). JSON Schemas are exported to ``schemas/``.

Regenerate the exported schemas with ``uv run python tools/export_schemas.py``; a snapshot test fails when they drift.
"""

from sbr.schemas.base import SCHEMA_VERSION, StrictModel
from sbr.schemas.operations import RunRecord, RunStatus, WorkItem, WorkItemState, WorkOutput
from sbr.schemas.provenance import Activity, ActivityStatus, DerivationRole, DerivedFrom, Locator, ProvenanceClass
from sbr.schemas.registry import (
    ArchiveMember,
    BlobClassification,
    BlobRecord,
    BlobRelation,
    ChangeEvent,
    PathObservation,
    ScanRecord,
    SourceRootRecord,
)
from sbr.schemas.trace import RedactedValue, Span, SpanKind, SpanStatus, TraceToolCall

EXPORTED_MODELS: tuple[type[StrictModel], ...] = (
    Activity,
    DerivedFrom,
    Locator,
    SourceRootRecord,
    ScanRecord,
    BlobRecord,
    PathObservation,
    ArchiveMember,
    BlobClassification,
    BlobRelation,
    ChangeEvent,
    RunRecord,
    Span,
    WorkItem,
    WorkOutput,
)

__all__ = [
    "EXPORTED_MODELS",
    "SCHEMA_VERSION",
    "Activity",
    "ActivityStatus",
    "ArchiveMember",
    "BlobClassification",
    "BlobRecord",
    "BlobRelation",
    "ChangeEvent",
    "DerivationRole",
    "DerivedFrom",
    "Locator",
    "PathObservation",
    "ProvenanceClass",
    "RedactedValue",
    "RunRecord",
    "RunStatus",
    "ScanRecord",
    "SourceRootRecord",
    "Span",
    "SpanKind",
    "SpanStatus",
    "StrictModel",
    "TraceToolCall",
    "WorkItem",
    "WorkItemState",
    "WorkOutput",
]
