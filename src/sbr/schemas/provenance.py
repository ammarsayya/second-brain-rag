"""Provenance core (docs/05, docs/32 §1, ADR-013). W3C-PROV-inspired: entities, activities, agents."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, StringConstraints, model_validator

from sbr.schemas.base import (
    ActivityId,
    AgentRef,
    AnyEntityId,
    BlobId,
    BlockId,
    RunId,
    StrictModel,
    UtcDatetime,
)

Kind = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$", max_length=64)]


class ProvenanceClass(StrEnum):
    """Knowledge-layer classes; they stay distinct end to end (HC-09/10/11)."""

    SOURCE_DERIVED = "SOURCE_DERIVED"
    USER_AUTHORED = "USER_AUTHORED"
    USER_ANNOTATION = "USER_ANNOTATION"
    AI_GENERATED = "AI_GENERATED"
    EXTERNAL_PENDING = "EXTERNAL_PENDING"
    EXTERNAL_RESEARCH = "EXTERNAL_RESEARCH"
    MODEL_KNOWLEDGE = "MODEL_KNOWLEDGE"


class ActivityStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DerivationRole(StrEnum):
    PRIMARY = "primary"
    CONTEXT = "context"
    TWIN = "twin"
    EVIDENCE = "evidence"


class Activity(StrictModel):
    """One run of a producer (scan, hash, extract, approve …)."""

    activity_id: ActivityId
    kind: Kind
    producer: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    producer_version: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    params_hash: str | None = None
    agent: AgentRef
    run_id: RunId | None = None
    started_at: UtcDatetime
    ended_at: UtcDatetime | None = None
    status: ActivityStatus = ActivityStatus.RUNNING
    inputs: list[AnyEntityId] = Field(default_factory=list)
    outputs: list[AnyEntityId] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def _check_times(self) -> Self:
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValueError("ended_at precedes started_at")
        if self.status is ActivityStatus.RUNNING and self.ended_at is not None:
            raise ValueError("a running activity has no ended_at")
        if self.status is not ActivityStatus.RUNNING and self.ended_at is None:
            raise ValueError("a finished activity needs ended_at")
        return self


class Locator(StrictModel):
    """Points evidence into exact source bytes (docs/05 §3). All positions are optional refinements of the blob."""

    blob_id: BlobId
    representation: Annotated[str, StringConstraints(pattern=r"^[a-z0-9]{1,16}$")]
    page_index: Annotated[int, Field(ge=0)] | None = None
    page_label: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    block_id: BlockId | None = None
    char_span: tuple[Annotated[int, Field(ge=0)], Annotated[int, Field(ge=0)]] | None = None
    equation_label: str | None = None
    figure_label: str | None = None
    timestamp_s: Annotated[float, Field(ge=0)] | None = None

    @model_validator(mode="after")
    def _check_geometry(self) -> Self:
        if self.bbox is not None:
            x0, y0, x1, y1 = self.bbox
            if x1 < x0 or y1 < y0:
                raise ValueError("bbox must be [x0, y0, x1, y1] with x0 <= x1 and y0 <= y1")
            if self.page_index is None:
                raise ValueError("bbox requires page_index")
        if self.char_span is not None:
            if self.char_span[1] < self.char_span[0]:
                raise ValueError("char_span end precedes start")
            if self.block_id is None:
                raise ValueError("char_span is relative to a block and requires block_id")
        return self


class DerivedFrom(StrictModel):
    """Link from a derived entity to what it was derived from (PV-1)."""

    entity_id: AnyEntityId
    source_entity_id: AnyEntityId
    locator: Locator | None = None
    role: DerivationRole = DerivationRole.PRIMARY

    @model_validator(mode="after")
    def _no_self_link(self) -> Self:
        if self.entity_id == self.source_entity_id:
            raise ValueError("an entity cannot be derived from itself")
        return self
