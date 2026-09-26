"""A minimal, real (not a mock) baseline extractor: pypdf's own text layer, split into paragraph blocks by
blank lines, in the order pypdf returns it. No equation/table/figure detection at all - this is deliberately
the floor every real candidate in T-P3-05 (PyMuPDF/pypdfium2 baseline, Docling, MinerU, PaddleOCR-VL, Marker)
must beat, and it is what T-P3-04's own acceptance criterion means by "runs on a dummy extractor".
"""

from __future__ import annotations

import io
import time

import pypdf

from sbr.eval.extract.contracts import ExtractedBlock, PageExtraction
from sbr.jobs.governor import real_metrics


class DummyTextExtractor:
    """Text-layer-only, no structure. Any real extractor should score at least as well as this on CER."""

    name = "dummy_text_layer"

    def extract_page(self, pdf_bytes: bytes, page_number: int) -> PageExtraction:
        start = time.perf_counter()
        before = real_metrics().ram_used_gb
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            index = max(0, min(page_number - 1, len(reader.pages) - 1))
            text = reader.pages[index].extract_text() or ""
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            blocks = tuple(
                ExtractedBlock(kind="paragraph", reading_order=i, text=paragraph)
                for i, paragraph in enumerate(paragraphs)
            )
            return PageExtraction(
                page=page_number,
                blocks=blocks,
                equations=(),
                tables=(),
                figures=(),
                elapsed_seconds=time.perf_counter() - start,
                ram_delta_gb=max(0.0, real_metrics().ram_used_gb - before),
            )
        except Exception as exc:  # noqa: BLE001 - a single bad PDF must not abort the whole benchmark run
            return PageExtraction(
                page=page_number,
                blocks=(),
                equations=(),
                tables=(),
                figures=(),
                elapsed_seconds=time.perf_counter() - start,
                ram_delta_gb=max(0.0, real_metrics().ram_used_gb - before),
                error=f"{type(exc).__name__}: {exc}",
            )


__all__ = ["DummyTextExtractor"]
