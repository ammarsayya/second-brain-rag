"""Answer segments with validator-enforced knowledge-layer basis (T-P7-03, ADR-034, HC-11)."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, StringConstraints, model_validator

from sbr.schemas.base import Confidence, StrictModel, prefixed
from sbr.schemas.provenance import Locator

KnowledgeUnitId = Annotated[str, prefixed("ku")]
ExternalSourceId = Annotated[str, prefixed("ext")]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AnswerBasis(StrEnum):
    """ADR-034's complete, closed set of answer knowledge layers."""

    CORPUS = "CORPUS"
    USER = "USER"
    AI_NOTE = "AI_NOTE"
    EXTERNAL_APPROVED = "EXTERNAL_APPROVED"
    EXTERNAL_PENDING = "EXTERNAL_PENDING"
    MODEL = "MODEL"


class AnswerCitation(StrictModel):
    """One resolvable KU or external-source citation with an exact locator."""

    ku_id: KnowledgeUnitId | None = None
    external_id: ExternalSourceId | None = None
    locator: Locator
    quote: NonEmptyText | None = None

    @model_validator(mode="after")
    def _exactly_one_target(self) -> Self:
        if (self.ku_id is None) == (self.external_id is None):
            raise ValueError("a citation must set exactly one of ku_id or external_id")
        return self


class AnswerSegment(StrictModel):
    """A contiguous answer claim whose provenance layer and citations are unambiguous."""

    text: NonEmptyText
    basis: AnswerBasis
    citations: list[AnswerCitation] = Field(default_factory=list)
    confidence: Confidence

    @model_validator(mode="after")
    def _citation_policy(self) -> Self:
        if self.basis in {AnswerBasis.USER, AnswerBasis.MODEL}:
            if self.citations:
                raise ValueError(f"{self.basis.value} segments must not carry source citations; split mixed claims")
            return self
        if not self.citations:
            raise ValueError(f"{self.basis.value} segments require at least one citation")
        if self.basis is AnswerBasis.CORPUS and any(c.ku_id is None for c in self.citations):
            raise ValueError("CORPUS segments may cite only knowledge units")
        if self.basis in {AnswerBasis.EXTERNAL_APPROVED, AnswerBasis.EXTERNAL_PENDING} and any(
            c.external_id is None for c in self.citations
        ):
            raise ValueError(f"{self.basis.value} segments may cite only external sources")
        # AI_NOTE is never a terminal evidence layer: its citations resolve to KU or external evidence here.
        return self


__all__ = [
    "AnswerBasis",
    "AnswerCitation",
    "AnswerSegment",
    "ExternalSourceId",
    "KnowledgeUnitId",
]
