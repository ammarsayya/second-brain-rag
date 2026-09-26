"""Pure document-shape signal classifiers for gold-set stratification (T-P3-01).

Every function here takes already-extracted, cheap metadata (a producer string, a page's text, a page's
media-box, a chunk of Office XML) and returns a classification — none of them open a file or touch the
registry, so they are trivially unit-testable and reusable by whichever later task needs the same signals
(T-P3-04's evaluation harness in particular).

These are deliberately lightweight v1 heuristics, not the final word on any of these questions — e.g.
distinguishing a knowledge-bearing figure from decoration is T-P3-10's own dedicated spike, not solved here.
"""

from __future__ import annotations

import re

_LATEX_PRODUCER: re.Pattern[str] = re.compile(r"tex", re.IGNORECASE)
_WORD_PRODUCER: re.Pattern[str] = re.compile(r"\bword\b", re.IGNORECASE)
_POWERPOINT_PRODUCER: re.Pattern[str] = re.compile(r"powerpoint", re.IGNORECASE)
_LIBREOFFICE_PRODUCER: re.Pattern[str] = re.compile(r"libreoffice|openoffice", re.IGNORECASE)

# A page with fewer non-whitespace characters than this is treated as textless ("scanned-like") - matches
# docs/03 §5.1's own framing of a page with no usable text layer, at the single-page granularity a gold-set
# pick needs (that document-level census used an 80%-of-sampled-pages rule; a gold pick is one specific page).
SCANNED_TEXT_THRESHOLD = 20

_OMATH_TAG: re.Pattern[bytes] = re.compile(rb"<m:oMath[ >]")


def classify_producer(producer: str | None) -> str:
    """Bucket a PDF's ``/Producer`` metadata string into a coarse producer class (docs/03 §5.1's own classes)."""
    if not producer:
        return "no_metadata"
    if _LATEX_PRODUCER.search(producer):
        return "latex"
    if _WORD_PRODUCER.search(producer):
        return "word"
    if _POWERPOINT_PRODUCER.search(producer):
        return "powerpoint"
    if _LIBREOFFICE_PRODUCER.search(producer):
        return "libreoffice"
    return "other"


def is_scanned_page(page_text: str) -> bool:
    """A page with (near-)no extractable text is "scanned-like" - no usable text layer for this page."""
    return len(page_text.strip()) < SCANNED_TEXT_THRESHOLD


def is_landscape_page(width: float, height: float) -> bool:
    """Landscape orientation is this corpus's own proxy for "slide-like" content (docs/03 §5.1: 29.8%)."""
    return width > height


def has_omml_equations(xml_bytes: bytes) -> bool:
    """Whether a chunk of Office Open XML (a DOCX/PPTX part) contains a native OMML equation (``<m:oMath>``).

    Native OMML is this corpus's best available math ground truth for the owner's own authored documents
    (HC-05, docs/03 §6) - exact, not a recognizer's guess - so gold-set stratification needs to know which
    Office documents actually carry one.
    """
    return _OMATH_TAG.search(xml_bytes) is not None


__all__ = [
    "SCANNED_TEXT_THRESHOLD",
    "classify_producer",
    "has_omml_equations",
    "is_landscape_page",
    "is_scanned_page",
]
