"""T-P7-03: answer basis, citation validation, schema export, and label rendering."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sbr.answer.render import BASIS_LABELS, render_answer, render_segment
from sbr.answer.schema import AnswerBasis, AnswerCitation, AnswerSegment
from sbr.ids import hash_bytes, new_id
from sbr.schemas import Locator


def citation(*, external: bool = False) -> AnswerCitation:
    target = {"external_id": new_id("ext")} if external else {"ku_id": new_id("ku")}
    return AnswerCitation(
        **target,
        locator=Locator(blob_id=hash_bytes(b"source"), representation="pdf", page_index=2, page_label="S. 2"),
        quote="Beleg",
    )


def segment(basis: AnswerBasis, *, citations: list[AnswerCitation] | None = None) -> AnswerSegment:
    return AnswerSegment(text="Eine klar abgegrenzte Aussage.", basis=basis, citations=citations or [], confidence=0.9)


def test_answer_segment_round_trips_strict_json() -> None:
    original = segment(AnswerBasis.CORPUS, citations=[citation()])
    assert AnswerSegment.model_validate_json(original.model_dump_json()) == original
    with pytest.raises(ValidationError):
        AnswerSegment.model_validate({**original.model_dump(), "unexpected": True})


def test_citation_requires_exactly_one_resolvable_target() -> None:
    locator = Locator(blob_id=hash_bytes(b"source"), representation="pdf", page_index=0)
    with pytest.raises(ValidationError, match="exactly one"):
        AnswerCitation(locator=locator)
    with pytest.raises(ValidationError, match="exactly one"):
        AnswerCitation(ku_id=new_id("ku"), external_id=new_id("ext"), locator=locator)


@pytest.mark.parametrize("basis", [AnswerBasis.CORPUS, AnswerBasis.AI_NOTE, AnswerBasis.EXTERNAL_APPROVED])
def test_evidence_bases_require_citations(basis: AnswerBasis) -> None:
    with pytest.raises(ValidationError, match="require at least one citation"):
        segment(basis)


def test_basis_controls_the_allowed_citation_target_type() -> None:
    with pytest.raises(ValidationError, match="knowledge units"):
        segment(AnswerBasis.CORPUS, citations=[citation(external=True)])
    with pytest.raises(ValidationError, match="external sources"):
        segment(AnswerBasis.EXTERNAL_APPROVED, citations=[citation()])
    assert segment(AnswerBasis.AI_NOTE, citations=[citation(), citation(external=True)])


@pytest.mark.parametrize("basis", [AnswerBasis.USER, AnswerBasis.MODEL])
def test_uncited_bases_reject_mixed_source_claims(basis: AnswerBasis) -> None:
    assert segment(basis).citations == []
    with pytest.raises(ValidationError, match="split mixed claims"):
        segment(basis, citations=[citation()])


def test_renderer_labels_every_basis_and_keeps_citation_locators_visible() -> None:
    corpus = segment(AnswerBasis.CORPUS, citations=[citation()])
    rendered = render_segment(corpus)
    assert rendered.startswith("**[Corpus]**")
    assert "[1] ku_" in rendered
    assert "S. 2" in rendered
    assert "Beleg" in rendered

    for basis in (AnswerBasis.USER, AnswerBasis.MODEL):
        assert f"**[{BASIS_LABELS[basis]}]**" in render_segment(segment(basis))


def test_external_pending_is_fail_closed_until_explicitly_enabled() -> None:
    pending = segment(AnswerBasis.EXTERNAL_PENDING, citations=[citation(external=True)])
    with pytest.raises(ValueError, match="explicit opt-in"):
        render_segment(pending)
    assert "Unapproved external (opt-in)" in render_segment(pending, allow_external_pending=True)


def test_answer_renderer_never_merges_adjacent_knowledge_layers() -> None:
    rendered = render_answer([segment(AnswerBasis.CORPUS, citations=[citation()]), segment(AnswerBasis.MODEL)])
    assert rendered.count("**[") == 2
    assert "\n\n**[Model knowledge (not from corpus)]**" in rendered


def test_schema_has_the_closed_basis_enum() -> None:
    schema = AnswerSegment.model_json_schema()
    assert schema["$defs"]["AnswerBasis"]["enum"] == [basis.value for basis in AnswerBasis]
