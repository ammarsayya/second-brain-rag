"""T-P4-01: DocIR models validate fixture documents, are versioned, and reject invalid records."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from sbr.docir import (
    DOCIR_VERSION,
    Annotation,
    Block,
    BlockKind,
    DocIR,
    DocumentInfo,
    Equation,
    EquationReading,
    EquationSourceKind,
    ExtractorRef,
    Figure,
    FigureKind,
    Page,
    Reference,
    Section,
    Table,
    ValidationStatus,
)
from sbr.ids import hash_bytes, new_id

BLOB = hash_bytes(b"a fixture document")


def _minimal_docir() -> DocIR:
    return DocIR(
        blob_id=BLOB,
        document=DocumentInfo(title="Maschinendynamik 1", genre="lecture_script", lang=["de"], pages=1),
        extractors=[ExtractorRef(name="pymupdf", version="1.28.2")],
        pages=[Page(index=0, label="1", width=595.0, height=842.0)],
    )


def test_minimal_docir_validates() -> None:
    doc = _minimal_docir()
    assert doc.docir_version == DOCIR_VERSION


def test_docir_round_trips_through_json() -> None:
    doc = _minimal_docir()
    text = doc.model_dump_json()
    again = DocIR.model_validate_json(text)
    assert again == doc


def test_docir_is_immutable() -> None:
    doc = _minimal_docir()
    with pytest.raises(ValidationError):
        doc.docir_version = "2.0"  # type: ignore[misc]


def test_fixture_matching_docs_09_s2_own_example_validates() -> None:
    """docs/09 §2's own worked example: a dynamics equation block, referencing a real Equation record with
    an OMML-exact twin reading (docs/10 §3's own priority-1 source kind)."""
    equation_id = new_id("eq")
    figure_id = new_id("fig")
    block_id = new_id("blk")
    section_id = new_id("sec")

    doc = DocIR(
        blob_id=BLOB,
        document=DocumentInfo(title="Skript Maschinendynamik 1", genre="lecture_script", lang=["de"], pages=130),
        extractors=[
            ExtractorRef(name="pymupdf", version="1.28.2"),
            ExtractorRef(name="omml-twin-fusion", version="0.1.0", params_hash="deadbeef"),
        ],
        pages=[Page(index=46, label="40", width=595.0, height=842.0, blocks=[block_id])],
        blocks=[
            Block(
                id=block_id,
                type=BlockKind.EQUATION,
                page=46,
                bbox=(72.0, 300.0, 400.0, 340.0),
                order=12,
                text="F_k = M q̈ + c(q, q̇) + g(q)",
                lang="de",
                confidence=1.0,
                source="office",
                equation_ref=equation_id,
            )
        ],
        equations=[
            Equation(
                id=equation_id,
                blob_id=BLOB,
                page_index=46,
                bbox=(72.0, 300.0, 400.0, 340.0),
                display=True,
                label="(42)",
                readings=[
                    EquationReading(
                        latex=r"\boldsymbol{F}_k = \boldsymbol{M}\ddot{\boldsymbol{q}} + "
                        r"\boldsymbol{c}(\boldsymbol{q},\dot{\boldsymbol{q}}) + \boldsymbol{g}(\boldsymbol{q})",
                        source_kind=EquationSourceKind.OMML_EXACT,
                        engine="pandoc@3.11",
                        confidence=1.0,
                        validations={"V4": True},
                    )
                ],
                preferred_reading=0,
                latex_normalized=r"F_k = M \ddot{q} + c(q, \dot{q}) + g(q)",
                validation_status=ValidationStatus.VERIFIED,
                crop_ref="var/artifacts/b3.../eq_.../crop.png",
            )
        ],
        figures=[
            Figure(
                id=figure_id,
                page_index=33,
                bbox=(50.0, 100.0, 500.0, 400.0),
                kind=FigureKind.PLOT,
                caption="Zerlegung einer unstetigen Übertragungsfunktion",
                label="Bild 2.17",
                crop_ref="var/artifacts/b3.../fig_.../crop.png",
                is_knowledge_bearing=True,
                confidence=0.93,
            )
        ],
        sections=[
            Section(
                id=section_id,
                number="3.2",
                title="Innere Kräfte und Momente",
                level=2,
                page_span=(21, 24),
                blocks=[block_id],
            )
        ],
        annotations=[Annotation(id=new_id("ann"), kind="ink_detected", page_index=46, bbox=(0.0, 0.0, 50.0, 50.0))],
        references=[Reference(id=new_id("ref"), raw_text="Pahl, G.; Beitz, W.: Konstruktionslehre, Springer")],
    )
    # a real JSON round trip through the exact shape docs/09 §2 describes
    text = doc.model_dump_json()
    payload = json.loads(text)
    assert payload["docir_version"] == "1.0"
    assert payload["equations"][0]["readings"][0]["source_kind"] == "omml_exact"
    assert DocIR.model_validate_json(text) == doc


def test_block_rejects_unbalanced_bbox() -> None:
    with pytest.raises(ValidationError, match="x0 <= x1"):
        Block(
            id=new_id("blk"),
            type=BlockKind.PARAGRAPH,
            page=0,
            order=0,
            text="x",
            source="text_layer",
            bbox=(10.0, 10.0, 5.0, 20.0),
        )


def test_equation_preferred_reading_must_index_into_readings() -> None:
    with pytest.raises(ValidationError, match="preferred_reading"):
        Equation(
            id=new_id("eq"),
            blob_id=BLOB,
            page_index=0,
            bbox=(0.0, 0.0, 1.0, 1.0),
            display=False,
            readings=[EquationReading(latex="x", source_kind=EquationSourceKind.LATEX_SOURCE, confidence=0.9)],
            preferred_reading=1,
            latex_normalized="x",
            validation_status=ValidationStatus.PLAUSIBLE,
        )


def test_figure_ai_description_requires_a_crop_ref() -> None:
    with pytest.raises(ValidationError, match="crop_ref"):
        Figure(
            id=new_id("fig"),
            page_index=0,
            bbox=(0.0, 0.0, 1.0, 1.0),
            kind=FigureKind.PLOT,
            is_knowledge_bearing=True,
            confidence=0.9,
            ai_description="a plot of something",
        )


def test_table_rejects_ragged_rows() -> None:
    with pytest.raises(ValidationError, match="same number of columns"):
        Table(id=new_id("tbl"), page_index=0, rows=(("a", "b"), ("c",)), confidence=0.9)


def test_section_rejects_backwards_page_span() -> None:
    with pytest.raises(ValidationError, match="page_span"):
        Section(id=new_id("sec"), title="x", level=0, page_span=(5, 2))


def test_docir_rejects_a_block_referencing_an_unknown_page() -> None:
    with pytest.raises(ValidationError, match="unknown page"):
        DocIR(
            blob_id=BLOB,
            document=DocumentInfo(pages=1),
            extractors=[ExtractorRef(name="x", version="1")],
            pages=[Page(index=0, width=1.0, height=1.0)],
            blocks=[Block(id=new_id("blk"), type=BlockKind.PARAGRAPH, page=99, order=0, text="x", source="ocr")],
        )


def test_docir_rejects_a_block_referencing_an_unknown_equation() -> None:
    with pytest.raises(ValidationError, match="unknown equation"):
        DocIR(
            blob_id=BLOB,
            document=DocumentInfo(pages=1),
            extractors=[ExtractorRef(name="x", version="1")],
            pages=[Page(index=0, width=1.0, height=1.0)],
            blocks=[
                Block(
                    id=new_id("blk"),
                    type=BlockKind.EQUATION,
                    page=0,
                    order=0,
                    text="x",
                    source="vision",
                    equation_ref=new_id("eq"),
                )
            ],
        )


def test_docir_rejects_a_page_referencing_an_unknown_block() -> None:
    with pytest.raises(ValidationError, match="unknown block"):
        DocIR(
            blob_id=BLOB,
            document=DocumentInfo(pages=1),
            extractors=[ExtractorRef(name="x", version="1")],
            pages=[Page(index=0, width=1.0, height=1.0, blocks=[new_id("blk")])],
        )


def test_docir_rejects_a_section_child_referencing_an_unknown_section() -> None:
    with pytest.raises(ValidationError, match="unknown child section"):
        DocIR(
            blob_id=BLOB,
            document=DocumentInfo(pages=1),
            extractors=[ExtractorRef(name="x", version="1")],
            pages=[Page(index=0, width=1.0, height=1.0)],
            sections=[Section(id=new_id("sec"), title="x", level=0, page_span=(0, 0), children=[new_id("sec")])],
        )


def test_docir_requires_at_least_one_extractor() -> None:
    with pytest.raises(ValidationError):
        DocIR(blob_id=BLOB, document=DocumentInfo(pages=1), extractors=[], pages=[])
