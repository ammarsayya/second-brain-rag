"""Extraction/gold contracts for T-P3-04's harness — a deliberately small subset of docs/04 §2's full DocIR
(Document/Section/Block/Equation/Figure/Table), just enough shape for objective scoring. Every extractor
candidate (T-P3-05 onward) adapts its own vendor-specific output into these, so the harness scores every
engine the same way and vendor output never leaks past this boundary (docs/24's own "maintain adapters" line).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

BBox = tuple[float, float, float, float]  # (x0, y0, x1, y1)

# docs/04 §2's own Block kind list.
BLOCK_KINDS = frozenset(
    {
        "paragraph",
        "heading",
        "list",
        "equation",
        "figure",
        "table",
        "caption",
        "code",
        "footnote",
        "header_footer",
        "annotation",
    }
)
VALIDATION_STATUSES = frozenset({"verified", "plausible", "uncertain", "failed"})


@dataclass(frozen=True, slots=True)
class ExtractedBlock:
    kind: str
    reading_order: int
    text: str
    bbox: BBox | None = None


@dataclass(frozen=True, slots=True)
class ExtractedEquation:
    latex: str
    confidence: float
    validation_status: str  # one of VALIDATION_STATUSES; the extractor's own claim, checked against gold by
    # false_confidence_rate() rather than trusted at face value.
    bbox: BBox | None = None


@dataclass(frozen=True, slots=True)
class ExtractedTable:
    rows: tuple[tuple[str, ...], ...]
    bbox: BBox | None = None


@dataclass(frozen=True, slots=True)
class ExtractedFigure:
    bbox: BBox
    caption: str | None
    is_knowledge_bearing: bool
    confidence: float


@dataclass(frozen=True, slots=True)
class PageExtraction:
    page: int
    blocks: tuple[ExtractedBlock, ...]
    equations: tuple[ExtractedEquation, ...]
    tables: tuple[ExtractedTable, ...]
    figures: tuple[ExtractedFigure, ...]
    elapsed_seconds: float
    ram_delta_gb: float
    error: str | None = None  # set instead of raising - one page's failure must not abort a whole benchmark run


@dataclass(frozen=True, slots=True)
class GoldBlock:
    kind: str
    reading_order: int
    text: str


@dataclass(frozen=True, slots=True)
class GoldEquation:
    latex_normalized: str
    source_kind: str  # docs/04 §2: omml_exact, latex_source, vision_recognized, text_layer_linear


@dataclass(frozen=True, slots=True)
class GoldFigure:
    bbox: BBox
    caption: str | None
    is_knowledge_bearing: bool


@dataclass(frozen=True, slots=True)
class PageGold:
    page: int
    blocks: tuple[GoldBlock, ...]
    equations: tuple[GoldEquation, ...]
    tables: tuple[tuple[tuple[str, ...], ...], ...]
    figures: tuple[GoldFigure, ...]


class Extractor(Protocol):
    """One candidate parser (T-P3-05's PyMuPDF/pypdfium2/Docling/MinerU/PaddleOCR-VL/Marker, or a stub)."""

    name: str

    def extract_page(self, pdf_bytes: bytes, page_number: int) -> PageExtraction: ...


__all__ = [
    "BLOCK_KINDS",
    "VALIDATION_STATUSES",
    "BBox",
    "ExtractedBlock",
    "ExtractedEquation",
    "ExtractedFigure",
    "ExtractedTable",
    "Extractor",
    "GoldBlock",
    "GoldEquation",
    "GoldFigure",
    "PageExtraction",
    "PageGold",
]
