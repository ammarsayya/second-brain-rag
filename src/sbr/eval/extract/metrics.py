"""Objective extraction-quality metrics (T-P3-04, docs/20 §2). Every function here is pure: given a prediction
and a gold reference, it returns a number — no file I/O, no engine-specific knowledge.

Two metrics docs/20 §2 lists are deliberately **not** implemented here, as stubs rather than fakes:

* **Render-compare similarity** (render predicted LaTeX to an image, compare to the source crop) needs a
  LaTeX rendering engine (KaTeX/MathJax via Node, or similar) — choosing and standing one up is SPIKE-MATH's
  own job (T-P3-06, ADR-009), not this harness's to pre-empt.
* **TEDS** (the published tree-edit-distance table metric) is a specific, nontrivial algorithm.
  :func:`table_structure_similarity` here is a documented, simpler grid-shape-and-cell-text proxy — useful for
  making the harness runnable and for a first-pass comparison now, but it is **not** TEDS and must not be
  reported as such once real table gold data (T-P3-03, gated on owner approval) makes the difference matter.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache


def levenshtein(a: Sequence[object], b: Sequence[object]) -> int:
    """Classic edit distance over any two sequences (characters, words, block-ids, ...). O(len(a)*len(b))."""
    if a == b:
        return 0
    if len(a) == 0:
        return len(b)
    if len(b) == 0:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ai in enumerate(a, start=1):
        current = [i] + [0] * len(b)
        for j, bj in enumerate(b, start=1):
            cost = 0 if ai == bj else 1
            current[j] = min(
                previous[j] + 1,  # deletion
                current[j - 1] + 1,  # insertion
                previous[j - 1] + cost,  # substitution
            )
        previous = current
    return previous[-1]


def character_error_rate(predicted: str, gold: str) -> float:
    """Levenshtein distance over characters, normalized by gold length. 0.0 = perfect; can exceed 1.0 on a
    wildly over-long wrong prediction (this is the standard CER convention, not a bug)."""
    if not gold:
        return 0.0 if not predicted else 1.0
    return levenshtein(predicted, gold) / len(gold)


def word_error_rate(predicted: str, gold: str) -> float:
    predicted_words = predicted.split()
    gold_words = gold.split()
    if not gold_words:
        return 0.0 if not predicted_words else 1.0
    return levenshtein(predicted_words, gold_words) / len(gold_words)


def reading_order_edit_distance(predicted_order: Sequence[str], gold_order: Sequence[str]) -> int:
    """Edit distance between two block-id orderings - 0 means the predicted reading order exactly matches gold."""
    return levenshtein(list(predicted_order), list(gold_order))


def heading_f1(predicted_headings: set[str], gold_headings: set[str]) -> tuple[float, float, float]:
    """(precision, recall, f1) over a set of heading identifiers (e.g. block ids gold marks as headings)."""
    if not gold_headings and not predicted_headings:
        return 1.0, 1.0, 1.0
    if not predicted_headings:
        return 0.0, 0.0, 0.0
    if not gold_headings:
        return 0.0, 0.0, 0.0
    true_positives = len(predicted_headings & gold_headings)
    precision = true_positives / len(predicted_headings)
    recall = true_positives / len(gold_headings)
    f1 = 0.0 if (precision + recall) == 0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1


@lru_cache(maxsize=4096)
def normalize_latex(latex: str) -> str:
    """A light, documented normalization - NOT a full LaTeX-semantics-aware normalizer: collapses whitespace
    and drops \\left/\\right sizing commands (which don't change meaning), for exact-match comparison that
    isn't defeated by purely cosmetic differences a recognizer might introduce."""
    collapsed = " ".join(latex.split())
    collapsed = collapsed.replace("\\left", "").replace("\\right", "")
    return collapsed.strip()


def equation_exact_match(predicted_latex: str, gold_latex_normalized: str) -> bool:
    return normalize_latex(predicted_latex) == normalize_latex(gold_latex_normalized)


def equation_token_edit_distance(predicted_latex: str, gold_latex_normalized: str) -> int:
    """Edit distance over whitespace-split LaTeX tokens, after the same normalization as exact-match."""
    predicted_tokens = normalize_latex(predicted_latex).split()
    gold_tokens = normalize_latex(gold_latex_normalized).split()
    return levenshtein(predicted_tokens, gold_tokens)


def false_confidence_rate(predictions: Sequence[tuple[bool, bool]]) -> float:
    """The single most important equation metric (docs/20 §2, R-01): of everything an extractor marked
    "verified", what fraction was actually WRONG? Each item is (is_correct, is_marked_verified). An extractor
    with nothing marked verified scores 0.0 here - not because it's good, but because false confidence can
    only be measured on claims it actually made; pair this with the coverage metric, never read alone."""
    verified = [is_correct for is_correct, is_marked_verified in predictions if is_marked_verified]
    if not verified:
        return 0.0
    return sum(1 for is_correct in verified if not is_correct) / len(verified)


def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    inter_x0, inter_y0 = max(ax0, bx0), max(ay0, by0)
    inter_x1, inter_y1 = min(ax1, bx1), min(ay1, by1)
    inter_area = max(0.0, inter_x1 - inter_x0) * max(0.0, inter_y1 - inter_y0)
    if inter_area == 0.0:
        return 0.0
    area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    union = area_a + area_b - inter_area
    return inter_area / union if union > 0 else 0.0


def figure_detection_f1(
    predicted_boxes: Sequence[tuple[float, float, float, float]],
    gold_boxes: Sequence[tuple[float, float, float, float]],
    *,
    iou_threshold: float = 0.5,
) -> tuple[float, float, float]:
    """Greedy IoU matching (highest-IoU pairs first), then standard detection precision/recall/f1."""
    if not gold_boxes and not predicted_boxes:
        return 1.0, 1.0, 1.0
    if not predicted_boxes:
        return 0.0, 0.0, 0.0
    if not gold_boxes:
        return 0.0, 0.0, 0.0

    pairs = sorted(
        (
            (_iou(p, g), pi, gi)
            for pi, p in enumerate(predicted_boxes)
            for gi, g in enumerate(gold_boxes)
            if _iou(p, g) >= iou_threshold
        ),
        key=lambda item: -item[0],
    )
    matched_pred: set[int] = set()
    matched_gold: set[int] = set()
    for _iou_value, pi, gi in pairs:
        if pi in matched_pred or gi in matched_gold:
            continue
        matched_pred.add(pi)
        matched_gold.add(gi)

    true_positives = len(matched_pred)
    precision = true_positives / len(predicted_boxes)
    recall = true_positives / len(gold_boxes)
    f1 = 0.0 if (precision + recall) == 0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def table_structure_similarity(
    predicted_rows: tuple[tuple[str, ...], ...], gold_rows: tuple[tuple[str, ...], ...]
) -> float:
    """Simplified TEDS-lite proxy (see module docstring - NOT the published TEDS algorithm): the average of a
    grid-shape match (do row/column counts agree) and per-cell text similarity (1 - CER, averaged over the
    overlapping grid), giving 1.0 for an identical table and degrading smoothly for shape or content drift."""
    if not gold_rows:
        return 1.0 if not predicted_rows else 0.0
    if not predicted_rows:
        return 0.0

    shape_match = 1.0 if (len(predicted_rows), len(predicted_rows[0])) == (len(gold_rows), len(gold_rows[0])) else 0.0
    overlap_rows = min(len(predicted_rows), len(gold_rows))
    overlap_cols = min(len(predicted_rows[0]), len(gold_rows[0])) if overlap_rows > 0 else 0
    if overlap_rows == 0 or overlap_cols == 0:
        return shape_match * 0.5
    cell_scores = [
        1.0 - min(1.0, character_error_rate(predicted_rows[r][c], gold_rows[r][c]))
        for r in range(overlap_rows)
        for c in range(overlap_cols)
    ]
    content_score = sum(cell_scores) / len(cell_scores)
    return round(0.5 * shape_match + 0.5 * content_score, 4)


__all__ = [
    "character_error_rate",
    "equation_exact_match",
    "equation_token_edit_distance",
    "false_confidence_rate",
    "figure_detection_f1",
    "heading_f1",
    "levenshtein",
    "normalize_latex",
    "reading_order_edit_distance",
    "table_structure_similarity",
    "word_error_rate",
]
