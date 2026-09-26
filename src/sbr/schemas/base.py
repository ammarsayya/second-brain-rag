"""Shared schema building blocks: strict base model, typed ids and UTC timestamps (docs/32 conventions)."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Annotated, Final

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

SCHEMA_VERSION: Final = "1.0.0"

_ULID = r"[0-7][0-9A-HJKMNP-TV-Z]{25}"

NonNeg = Annotated[int, Field(ge=0)]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


class StrictModel(BaseModel):
    """Immutable, closed-world record: unknown fields are rejected and values are never coerced across types."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, validate_default=True)


def _utc(value: datetime) -> datetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError("timestamps must be UTC (offset +00:00)")
    return value.astimezone(UTC)


UtcDatetime = Annotated[AwareDatetime, AfterValidator(_utc)]
BlobId = Annotated[str, StringConstraints(pattern=r"^b3:[0-9a-f]{64}$")]
Sha256Ref = Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_-]{0,31}$")]
AgentRef = Annotated[str, StringConstraints(pattern=r"^(system:[a-z0-9_.-]+|model:[^/\s]+/[^@\s]+@\S+|user:owner)$")]


def prefixed(prefix: str) -> StringConstraints:
    """Constraint for ``<prefix>_<ULID>`` object ids: use as ``Annotated[str, prefixed("act")]``."""
    return StringConstraints(pattern=rf"^{re.escape(prefix)}_{_ULID}$")


ActivityId = Annotated[str, prefixed("act")]
RunId = Annotated[str, prefixed("run")]
ScanId = Annotated[str, prefixed("scan")]
ObsId = Annotated[str, prefixed("obs")]
BlockId = Annotated[str, prefixed("blk")]
JobId = Annotated[str, prefixed("job")]
ManifestId = Annotated[str, prefixed("man")]
DocumentId = Annotated[str, prefixed("doc")]
SectionId = Annotated[str, prefixed("sec")]
EquationId = Annotated[str, prefixed("eq")]
FigureId = Annotated[str, prefixed("fig")]
TableId = Annotated[str, prefixed("tbl")]
AnnotationId = Annotated[str, prefixed("ann")]
ReferenceId = Annotated[str, prefixed("ref")]
AnyEntityId = Annotated[str, StringConstraints(pattern=rf"^(b3:[0-9a-f]{{64}}|[a-z]+_{_ULID})$")]
