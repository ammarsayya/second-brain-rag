"""OCR engine evidence-gathering helpers (T-P3-08, SPIKE-OCR, ADR-010). Pure parsing only - the actual
Tesseract subprocess call lives in ``tools/spike_ocr.py``, which is real-corpus I/O.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class OcrWordConfidence:
    text: str
    confidence: float  # tesseract's own 0-100 scale; -1 means "no confidence" (e.g. a non-text block)


def parse_tesseract_tsv(tsv_output: str) -> list[OcrWordConfidence]:
    """Parse ``tesseract ... tsv`` output (``-c tessedit_create_tsv=1`` / the ``tsv`` output base) into one
    :class:`OcrWordConfidence` per recognized word, skipping structural rows (page/block/para/line levels,
    which carry no text) and blank/whitespace-only words."""
    reader = csv.DictReader(io.StringIO(tsv_output), delimiter="\t", quoting=csv.QUOTE_NONE)  # TSV is unquoted
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


def confident_word_count(words: list[OcrWordConfidence], threshold: float = 80.0) -> int:
    """Words Tesseract scored at ``threshold`` or above: the readability score of one OCR pass.

    Mean confidence alone rewards a pass that reads three words well; counting confident words also rewards
    reading *more* of the page, which is what distinguishes the right orientation from a wrong one.
    """
    return sum(1 for w in words if w.confidence >= threshold)


@dataclass(frozen=True, slots=True)
class RotationVerdict:
    """Which clockwise rotation (0/90/180/270) of a page image reads best, by :func:`confident_word_count`.

    This is an *oracle by readability*, a proxy for ground truth, not ground truth: ``rotate`` is ``None`` when no
    rotation reads at all, and ``ambiguous`` marks a near tie the evidence cannot separate.
    """

    rotate: int | None
    ambiguous: bool
    best_score: int
    runner_up_score: int


def pick_rotation(scores: Mapping[int, int], *, min_words: int = 5, margin: float = 0.15) -> RotationVerdict:
    """Pick the best-reading rotation from ``{rotation: confident_word_count}``.

    Exact ties break toward the smaller rotation (so toward "no rotation"). A leader within ``margin`` (relative)
    of the runner-up is flagged ambiguous. Fewer than ``min_words`` confident words in every rotation yields
    ``rotate=None``: an unreadable page gives no orientation evidence, so none is invented.
    """
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    (best_rotation, best), runner_up = ranked[0], (ranked[1][1] if len(ranked) > 1 else 0)
    if best < min_words:
        return RotationVerdict(None, False, best, runner_up)
    ambiguous = runner_up >= best * (1 - margin)
    return RotationVerdict(best_rotation, ambiguous, best, runner_up)


def orientation_agreement(pairs: list[tuple[int | None, int | None]]) -> dict[str, Any]:
    """Compare ``(osd_rotate, oracle_rotate)`` pairs. ``None`` on either side is an abstention, not a miss."""
    by_osd: dict[str, dict[str, int]] = {str(r): {"agree": 0, "disagree": 0} for r in sorted(_VALID_ROTATIONS)}
    result: dict[str, Any] = {"compared": 0, "agree": 0, "osd_abstained": 0, "oracle_abstained": 0}
    for osd, oracle in pairs:
        if osd is None:
            result["osd_abstained"] += 1
            continue
        if oracle is None:
            result["oracle_abstained"] += 1
            continue
        result["compared"] += 1
        hit = osd == oracle
        result["agree"] += int(hit)
        by_osd[str(osd)]["agree" if hit else "disagree"] += 1
    result["by_osd"] = by_osd
    return result


__all__ = [
    "OcrWordConfidence",
    "OsdResult",
    "RotationVerdict",
    "confident_word_count",
    "mean_word_confidence",
    "orientation_agreement",
    "parse_tesseract_osd",
    "parse_tesseract_tsv",
    "pick_rotation",
    "summarize_rotations",
]
