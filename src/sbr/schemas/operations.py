"""Operational records (docs/21 §1): the run ledger. Work items follow in T-P1-09."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, StringConstraints, model_validator

from sbr.schemas.base import RunId, StrictModel, UtcDatetime


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
