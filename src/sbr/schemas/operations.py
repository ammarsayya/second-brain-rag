"""Operational records (docs/21 §1): the run ledger and job queue (T-P1-09, docs/08 §2)."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, StringConstraints, model_validator

from sbr.schemas.base import AgentRef, JobId, ManifestId, RunId, StrictModel, UtcDatetime

Stage = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$", max_length=64)]
StageVersion = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:+-]{0,127}$")]
Wave = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_-]{0,31}$")]
NonNegInt = Annotated[int, Field(ge=0)]


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class RunRecord(StrictModel):
    """One stateful CLI or worker invocation. ``command`` is the command path only; arguments are not stored."""

    run_id: RunId
    command: Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9 _.-]{0,79}$")]
    config_hash: str | None = None
    code_version: str
    git_sha: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{7,40}(\+dirty)?$")] | None = None
    pid: Annotated[int, Field(ge=0)]
    started_at: UtcDatetime
    ended_at: UtcDatetime | None = None
    status: RunStatus = RunStatus.RUNNING
    exit_code: int | None = None
    error_class: str | None = None
    counts: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self) -> Self:
        if (self.status is RunStatus.RUNNING) != (self.ended_at is None):
            raise ValueError("ended_at is set exactly when the run is finished")
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValueError("ended_at precedes started_at")
        return self


class WorkItemState(StrEnum):
    PENDING = "pending"
    LEASED = "leased"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"
    STALE = "stale"


class WorkItem(StrictModel):
    """One ``(subject_id, stage, stage_version)`` unit of pipeline work (docs/08 §2).

    A stage is "done" for a subject only at a specific ``stage_version``; bumping the version is a new row, so it
    re-enqueues exactly the affected subjects without disturbing history. A lease is identified by ``lease_token``:
    only its holder may complete or fail the item, so a re-leased item (after an expired lease) can never be
    completed twice.
    """

    job_id: JobId
    subject_id: Annotated[str, StringConstraints(min_length=1, max_length=256)]
    stage: Stage
    stage_version: StageVersion
    state: WorkItemState = WorkItemState.PENDING
    priority: int = 0
    wave: Wave | None = None
    attempts: NonNegInt = 0
    max_attempts: Annotated[int, Field(ge=1)]
    not_before_ms: NonNegInt = 0
    lease_owner: AgentRef | None = None
    lease_token: Annotated[str, StringConstraints(min_length=1, max_length=64)] | None = None
    lease_expires_ms: NonNegInt | None = None
    last_error: str | None = None
    output_manifest_id: ManifestId | None = None
    created_at: UtcDatetime
    updated_at: UtcDatetime

    @model_validator(mode="after")
    def _check(self) -> Self:
        leased_fields = (self.lease_owner, self.lease_token, self.lease_expires_ms)
        if self.state is WorkItemState.LEASED:
            if any(f is None for f in leased_fields):
                raise ValueError("a leased item needs lease_owner, lease_token and lease_expires_ms")
        elif any(f is not None for f in leased_fields):
            raise ValueError("lease fields are set only while state is leased")
        if self.attempts > self.max_attempts:
            raise ValueError("attempts may not exceed max_attempts")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at precedes created_at")
        return self


class WorkOutput(StrictModel):
    """Artifact manifest of one completed :class:`WorkItem`, written atomically with its completion."""

    manifest_id: ManifestId
    job_id: JobId
    artifacts: dict[str, str] = Field(default_factory=dict)
    created_at: UtcDatetime
