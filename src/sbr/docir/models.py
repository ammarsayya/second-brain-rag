"""DocIR (T-P4-01, docs/09 §2, ADR-011): the parser-independent, machine representation every extractor emits.

One DocIR document is keyed by ``(blob_id, extractor_set_version)`` — the source blob is authoritative
evidence and is never replaced; DocIR is a derived, versioned, re-computable artifact stored under
``var/artifacts`` (T-P4-02). Normalized Markdown (T-P4-12) is a *rendering* of DocIR, not a second
extraction, so nothing downstream may depend on any parser's own native output format (ADR-011) — every
engine adapts into these models, and only these models, before anything else in the system sees its output.

Equation fields follow docs/10 §3's priority-ordered ``source_kind`` and V1-V5 validation naming exactly, and
Figure's ``kind`` enum follows docs/11 §1's own list, so cross-referencing those docs and this schema never
needs a translation table.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, StringConstraints, model_validator

from sbr.schemas.base import (
    AnnotationId,
    BlobId,
    BlockId,
    Confidence,
    DocumentId,
    EquationId,
    FigureId,
    NonNeg,
    ReferenceId,
    SectionId,
    StrictModel,
    TableId,
)

DOCIR_VERSION = "1.0"


class BlockKind(StrEnum):
    """docs/04 §2's own Block kind list."""

    PARAGRAPH = "paragraph"
    HEADING = "heading"
    LIST = "list"
    EQUATION = "equation"
    FIGURE = "figure"
    TABLE = "table"
    CAPTION = "caption"
    CODE = "code"
    FOOTNOTE = "footnote"
    HEADER = "header"
    FOOTER = "footer"
    ANNOTATION = "annotation"


class EquationSourceKind(StrEnum):
    """docs/10 §1's priority-ordered math source kinds."""

    OMML_EXACT = "omml_exact"
    OFFICE_OLE_EQUATION = "office_ole_equation"
    LATEX_SOURCE = "latex_source"
    VISION_RECOGNIZED = "vision_recognized"
    TEXT_LAYER_LINEAR = "text_layer_linear"
    NONE = "none"


class ValidationStatus(StrEnum):
    """docs/10 §2's equation validation-status outcomes."""

    VERIFIED = "verified"
    PLAUSIBLE = "plausible"
    UNCERTAIN = "uncertain"
    FAILED = "failed"


class FigureKind(StrEnum):
    """docs/04 §2 / docs/11 §1's own Figure kind list."""

    BLOCK_DIAGRAM = "block_diagram"
    PLOT = "plot"
    SCHEMATIC = "schematic"
    TECHNICAL_DRAWING = "technical_drawing"
    FEM_RESULT = "fem_result"
    ROBOT_DIAGRAM = "robot_diagram"
    SETUP_PHOTO = "setup_photo"
    MATH_FIGURE = "math_figure"
    TABLE_IMAGE = "table_image"
    DECORATIVE = "decorative"


BBox = tuple[float, float, float, float]


def _check_bbox(bbox: BBox | None) -> None:
    if bbox is None:
        return
    x0, y0, x1, y1 = bbox
    if x1 < x0 or y1 < y0:
        raise ValueError("bbox must be [x0, y0, x1, y1] with x0 <= x1 and y0 <= y1")


class ExtractorRef(StrictModel):
    """One entry in a DocIR's ``extractors`` list: which engine (and exact config) produced part of it."""

    name: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    version: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    params_hash: str | None = None


class DocumentInfo(StrictModel):
    title: str | None = None
    genre: str | None = None
    lang: list[Annotated[str, StringConstraints(pattern=r"^[a-z]{2}$")]] = Field(default_factory=list)
    pages: NonNeg


class Page(StrictModel):
    """``index`` is the PDF page index (0-based); slides use one Page per slide (docs/09 §3)."""

    index: NonNeg
    label: str | None = None
    width: Annotated[float, Field(gt=0)]
    height: Annotated[float, Field(gt=0)]
    triage: dict[str, str | float | bool | int] = Field(default_factory=dict)
    blocks: list[BlockId] = Field(default_factory=list)


class Block(StrictModel):
    """Atomic layout element (docs/04 §2, docs/09 §2). ``order`` is reading order within its page."""

    id: BlockId
    type: BlockKind
    page: NonNeg
    bbox: BBox | None = None
    order: NonNeg
    text: str
    lang: str | None = None
    confidence: Confidence | None = None
    source: Annotated[str, StringConstraints(pattern=r"^(text_layer|ocr|office|vision)$")]
    equation_ref: EquationId | None = None
    figure_ref: FigureId | None = None
    table_ref: TableId | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        _check_bbox(self.bbox)
        return self


class EquationReading(StrictModel):
    """One candidate LaTeX reading of an equation (docs/10 §1/§3) — several may coexist; see ``preferred_reading``."""

    latex: str
    source_kind: EquationSourceKind
    engine: str | None = None  # "<engine>@<version>"
    confidence: Confidence
    validations: dict[Annotated[str, StringConstraints(pattern=r"^V[1-5]$")], bool] = Field(default_factory=dict)


class Equation(StrictModel):
    id: EquationId
    blob_id: BlobId
    page_index: NonNeg
    bbox: BBox
    display: bool  # display math (block) vs inline
    label: str | None = None  # e.g. "(3-114)"
    readings: Annotated[list[EquationReading], Field(min_length=1)]
    preferred_reading: NonNeg  # index into readings
    latex_normalized: str
    validation_status: ValidationStatus
    crop_ref: str | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        _check_bbox(self.bbox)
        if self.preferred_reading >= len(self.readings):
            raise ValueError("preferred_reading must index into readings")
        return self


class Figure(StrictModel):
    id: FigureId
    page_index: NonNeg
    bbox: BBox
    kind: FigureKind
    caption: str | None = None
    label: str | None = None  # e.g. "Bild 2.17"
    crop_ref: str | None = None
    is_knowledge_bearing: bool
    confidence: Confidence
    ai_description: str | None = None  # AI_GENERATED (docs/11 §3 tier F3); cited to crop_ref, never uncited

    @model_validator(mode="after")
    def _check(self) -> Self:
        _check_bbox(self.bbox)
        if self.ai_description is not None and self.crop_ref is None:
            raise ValueError("an AI-generated description must cite a crop_ref")
        return self


class Table(StrictModel):
    id: TableId
    page_index: NonNeg
    bbox: BBox | None = None
    caption: str | None = None
    label: str | None = None
    rows: tuple[tuple[str, ...], ...]
    confidence: Confidence

    @model_validator(mode="after")
    def _check(self) -> Self:
        _check_bbox(self.bbox)
        if self.rows and len({len(row) for row in self.rows}) > 1:
            raise ValueError("all table rows must have the same number of columns")
        return self


class Section(StrictModel):
    id: SectionId
    number: str | None = None  # e.g. "3.2"
    title: str
    level: NonNeg
    page_span: tuple[NonNeg, NonNeg]
    children: list[SectionId] = Field(default_factory=list)
    blocks: list[BlockId] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.page_span[1] < self.page_span[0]:
            raise ValueError("page_span end precedes start")
        return self


class Annotation(StrictModel):
    """Owner's marks on a source (docs/09 §2, docs/11 §7). Always USER_ANNOTATION (ADR-013) - never collapsed
    into the surrounding text, and never dropped by dedup (ADR-032)."""

    id: AnnotationId
    kind: Annotated[str, StringConstraints(pattern=r"^(pdf_annot|ink_detected|highlight)$")]
    page_index: NonNeg
    bbox: BBox
    text: str | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        _check_bbox(self.bbox)
        return self


class Reference(StrictModel):
    """A bibliography entry or in-text citation; may resolve to another Document in the corpus (docs/04 §2)."""

    id: ReferenceId
    raw_text: str
    resolved_document_id: DocumentId | None = None


class Quality(StrictModel):
    text_coverage: Confidence | None = None
    math_status_counts: dict[Annotated[str, StringConstraints(pattern=r"^V[1-5]$|^[a-z_]+$")], int] = Field(
        default_factory=dict
    )
    warnings: list[str] = Field(default_factory=list)


class DocIR(StrictModel):
    """The full per-``(blob_id, extractor_set_version)`` document, per docs/09 §2's own JSON shape."""

    docir_version: str = DOCIR_VERSION
    blob_id: BlobId
    document: DocumentInfo
    extractors: Annotated[list[ExtractorRef], Field(min_length=1)]
    pages: list[Page]
    blocks: list[Block] = Field(default_factory=list)
    equations: list[Equation] = Field(default_factory=list)
    figures: list[Figure] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    annotations: list[Annotation] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    quality: Quality = Field(default_factory=Quality)

    @model_validator(mode="after")
    def _check_referential_integrity(self) -> Self:
        page_indices = {p.index for p in self.pages}
        block_ids = {b.id for b in self.blocks}
        equation_ids = {e.id for e in self.equations}
        figure_ids = {f.id for f in self.figures}
        table_ids = {t.id for t in self.tables}

        for block in self.blocks:
            if block.page not in page_indices:
                raise ValueError(f"block {block.id} references unknown page {block.page}")
            if block.equation_ref is not None and block.equation_ref not in equation_ids:
                raise ValueError(f"block {block.id} references unknown equation {block.equation_ref}")
            if block.figure_ref is not None and block.figure_ref not in figure_ids:
                raise ValueError(f"block {block.id} references unknown figure {block.figure_ref}")
            if block.table_ref is not None and block.table_ref not in table_ids:
                raise ValueError(f"block {block.id} references unknown table {block.table_ref}")
        for page in self.pages:
            for block_id in page.blocks:
                if block_id not in block_ids:
                    raise ValueError(f"page {page.index} references unknown block {block_id}")
        for section in self.sections:
            for block_id in section.blocks:
                if block_id not in block_ids:
                    raise ValueError(f"section {section.id} references unknown block {block_id}")
        section_ids = {s.id for s in self.sections}
        for section in self.sections:
            for child_id in section.children:
                if child_id not in section_ids:
                    raise ValueError(f"section {section.id} references unknown child section {child_id}")
        return self


__all__ = [
    "DOCIR_VERSION",
    "Annotation",
    "BBox",
    "Block",
    "BlockKind",
    "DocIR",
    "DocumentInfo",
    "Equation",
    "EquationReading",
    "EquationSourceKind",
    "ExtractorRef",
    "Figure",
    "FigureKind",
    "Page",
    "Quality",
    "Reference",
    "Section",
    "Table",
    "ValidationStatus",
]
