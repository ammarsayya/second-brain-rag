"""Durable, privacy-bounded execution trace records (T-P9-02, HC-23)."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Final, Self

from pydantic import Field, StringConstraints, model_validator

from sbr.schemas.base import BlobId, RunId, SpanId, StrictModel, UtcDatetime

TRACE_PREVIEW_MAX_CHARS: Final = 160
TraceName = Annotated[str, StringConstraints(min_length=1, max_length=128)]
TraceLabel = Annotated[str, StringConstraints(min_length=1, max_length=128)]
NonNegInt = Annotated[int, Field(ge=0)]


class SpanKind(StrEnum):
    """The three event families required by docs/07 section 8."""

    NODE = "node"
    TOOL_CALL = "tool_call"
    MODEL_CALL = "model_call"


class SpanStatus(StrEnum):
    RUNNING = "running"
    OK = "ok"
    ERROR = "error"
    INTERRUPTED = "interrupted"


class RedactedValue(StrictModel):
    """A content fingerprint plus a bounded, credential-scrubbed preview."""

    content_hash: BlobId
    preview: Annotated[str, StringConstraints(max_length=TRACE_PREVIEW_MAX_CHARS)]
    char_count: NonNegInt
    truncated: bool


class TraceToolCall(StrictModel):
    """Structured summary of a tool selected by a node/model span."""

    name: TraceName
    inputs: RedactedValue | None = None


class Span(StrictModel):
    """One reconstructable node, tool-call, or model-call event."""

    span_id: SpanId
    run_id: RunId
    parent_span_id: SpanId | None = None
    sequence: NonNegInt
    kind: SpanKind
    name: TraceName
    started_at: UtcDatetime
    ended_at: UtcDatetime | None = None
    duration_ms: Annotated[float, Field(ge=0)] | None = None
    status: SpanStatus = SpanStatus.RUNNING
    error_class: TraceLabel | None = None
    inputs: RedactedValue | None = None
    prompt_version: TraceLabel | None = None
    model: TraceLabel | None = None
    raw_output: RedactedValue | None = None
    parsed_output: RedactedValue | None = None
    decision: RedactedValue | None = None
    tool_calls: list[TraceToolCall] = Field(default_factory=list)
    cost_usd: Annotated[float, Field(ge=0)] | None = None
    input_tokens: NonNegInt | None = None
    output_tokens: NonNegInt | None = None

    @model_validator(mode="after")
    def _check_lifecycle(self) -> Self:
        running = self.status is SpanStatus.RUNNING
        if running != (self.ended_at is None and self.duration_ms is None):
            raise ValueError("ended_at and duration_ms are set exactly when the span is finished")
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValueError("ended_at precedes started_at")
        if self.status in (SpanStatus.RUNNING, SpanStatus.OK) and self.error_class is not None:
            raise ValueError("error_class is set only for error or interrupted spans")
        return self


__all__ = [
    "TRACE_PREVIEW_MAX_CHARS",
    "RedactedValue",
    "Span",
    "SpanKind",
    "SpanStatus",
    "TraceToolCall",
]
