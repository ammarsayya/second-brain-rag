"""Deterministic, visibly labeled rendering for answer segments (T-P7-03)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

from sbr.answer.schema import AnswerBasis, AnswerCitation, AnswerSegment

BASIS_LABELS: Final[dict[AnswerBasis, str]] = {
    AnswerBasis.CORPUS: "Corpus",
    AnswerBasis.USER: "User-provided",
    AnswerBasis.AI_NOTE: "AI note (resolved to evidence)",
    AnswerBasis.EXTERNAL_APPROVED: "Approved external",
    AnswerBasis.EXTERNAL_PENDING: "Unapproved external (opt-in)",
    AnswerBasis.MODEL: "Model knowledge (not from corpus)",
}


def _render_citation(citation: AnswerCitation, number: int) -> str:
    target = citation.ku_id or citation.external_id
    locator = citation.locator
    positions: list[str] = []
    if locator.page_label is not None:
        positions.append(locator.page_label)
    elif locator.page_index is not None:
        positions.append(f"page {locator.page_index + 1}")
    if locator.equation_label is not None:
        positions.append(f"eq. {locator.equation_label}")
    if locator.figure_label is not None:
        positions.append(locator.figure_label)
    location = f" — {', '.join(positions)}" if positions else ""
    quote = f" — “{citation.quote}”" if citation.quote is not None else ""
    return f"[{number}] {target}{location}{quote}"


def render_segment(segment: AnswerSegment, *, allow_external_pending: bool = False) -> str:
    """Render one visibly labeled segment; pending external content is opt-in and fail-closed."""
    if segment.basis is AnswerBasis.EXTERNAL_PENDING and not allow_external_pending:
        raise ValueError("EXTERNAL_PENDING segments require explicit opt-in")
    markers = "" if not segment.citations else " " + "".join(f"[{i}]" for i in range(1, len(segment.citations) + 1))
    rendered = f"**[{BASIS_LABELS[segment.basis]}]** {segment.text}{markers}"
    if segment.citations:
        rendered += "\n" + "\n".join(_render_citation(citation, i) for i, citation in enumerate(segment.citations, 1))
    return rendered


def render_answer(segments: Iterable[AnswerSegment], *, allow_external_pending: bool = False) -> str:
    """Render answer segments as separated Markdown blocks without merging provenance layers."""
    return "\n\n".join(render_segment(segment, allow_external_pending=allow_external_pending) for segment in segments)


__all__ = ["BASIS_LABELS", "render_answer", "render_segment"]
