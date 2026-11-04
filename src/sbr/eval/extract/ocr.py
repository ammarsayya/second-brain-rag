"""OCR engine evidence-gathering helpers (T-P3-08, SPIKE-OCR, ADR-010). Pure parsing only - the actual
Tesseract subprocess call lives in ``tools/spike_ocr.py``, which is real-corpus I/O.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OcrWordConfidence:
    text: str
    confidence: float  # tesseract's own 0-100 scale; -1 means "no confidence" (e.g. a non-text block)


def parse_tesseract_tsv(tsv_output: str) -> list[OcrWordConfidence]:
    """Parse ``tesseract ... tsv`` output (``-c tessedit_create_tsv=1`` / the ``tsv`` output base) into one
    :class:`OcrWordConfidence` per recognized word, skipping structural rows (page/block/para/line levels,
    which carry no text) and blank/whitespace-only words."""
    reader = csv.DictReader(io.StringIO(tsv_output), delimiter="\t")
    words: list[OcrWordConfidence] = []
    for row in reader:
        text = (row.get("text") or "").strip()
        if not text:
            continue
        try:
            confidence = float(row["conf"])
        except (KeyError, ValueError):
            continue
        words.append(OcrWordConfidence(text=text, confidence=confidence))
    return words


def mean_word_confidence(words: list[OcrWordConfidence]) -> float | None:
    """Mean confidence over words tesseract actually scored (conf >= 0; -1 rows are structural, not text)."""
    scored = [w.confidence for w in words if w.confidence >= 0]
    return sum(scored) / len(scored) if scored else None


@dataclass(frozen=True, slots=True)
class OsdResult:
    """Tesseract orientation and script detection (``--psm 0``) for one page image.

    ``rotate`` is the clockwise rotation in degrees (0/90/180/270) Tesseract says the image needs to read
    upright; ``orientation_degrees`` is the detected orientation itself. Confidences are Tesseract's own unbounded
    scores, not probabilities - this module reports them and never turns them into a verdict by itself.
    """

    orientation_degrees: int
    rotate: int
    orientation_confidence: float
    script: str | None
    script_confidence: float | None


_VALID_ROTATIONS = frozenset({0, 90, 180, 270})


def parse_tesseract_osd(osd_output: str) -> OsdResult | None:
    """Parse ``tesseract IMAGE stdout --psm 0`` output. Returns ``None`` (fail closed, never a guessed 0) when the
    orientation lines are missing or malformed - e.g. "Too few characters" on a near-empty scan."""
    fields: dict[str, str] = {}
    for line in osd_output.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    try:
        orientation = int(fields["Orientation in degrees"])
        rotate = int(fields["Rotate"])
        orientation_confidence = float(fields["Orientation confidence"])
    except (KeyError, ValueError):
        return None
    if orientation not in _VALID_ROTATIONS or rotate not in _VALID_ROTATIONS:
        return None
    script = fields.get("Script") or None
    try:
        script_confidence: float | None = float(fields["Script confidence"])
    except (KeyError, ValueError):
        script_confidence = None
    return OsdResult(orientation, rotate, orientation_confidence, script, script_confidence)


def summarize_rotations(results: list[OsdResult | None], *, min_confidence: float) -> dict[str, int]:
    """Count pages per required rotation. Pages without a parseable OSD result count as ``undetected``; pages whose
    orientation confidence is below ``min_confidence`` count as ``low_confidence`` instead of a rotation bucket."""
    counts = {"0": 0, "90": 0, "180": 0, "270": 0, "low_confidence": 0, "undetected": 0}
    for result in results:
        if result is None:
            counts["undetected"] += 1
        elif result.orientation_confidence < min_confidence:
            counts["low_confidence"] += 1
        else:
            counts[str(result.rotate)] += 1
    return counts


__all__ = [
    "OcrWordConfidence",
    "OsdResult",
    "mean_word_confidence",
    "parse_tesseract_osd",
    "parse_tesseract_tsv",
    "summarize_rotations",
]
