"""Extraction evaluation harness runner (T-P3-04): score one :class:`~sbr.eval.extract.contracts.Extractor`
against a set of (bytes, page, gold) triples and produce one report — the same scoring path for every
candidate engine (T-P3-05 onward), so results are comparable rather than each engine grading its own homework.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from sbr.eval.extract.contracts import Extractor, GoldEquation, PageExtraction, PageGold
from sbr.eval.extract.metrics import (
    character_error_rate,
    equation_exact_match,
    equation_token_edit_distance,
    false_confidence_rate,
    figure_detection_f1,
    heading_f1,
    reading_order_edit_distance,
    table_structure_similarity,
    word_error_rate,
)
from sbr.jobs.governor import real_metrics


@dataclass(frozen=True, slots=True)
class PageScore:
    page: int
    error: str | None
    elapsed_seconds: float
    ram_delta_gb: float
    text_cer: float | None
    text_wer: float | None
    reading_order_edit_distance: int | None
    heading_precision: float | None
    heading_recall: float | None
    heading_f1: float | None
    equation_coverage: float | None  # detected / total gold equations
    equation_exact_match_rate: float | None
    equation_mean_token_edit_distance: float | None
    false_confidence_rate: float | None
    figure_precision: float | None
    figure_recall: float | None
    figure_f1: float | None
    table_structure_similarity_mean: float | None


@dataclass(frozen=True, slots=True)
class HarnessReport:
    extractor_name: str
    pages_scored: int
    pages_errored: int
    mean_text_cer: float | None
    mean_text_wer: float | None
    mean_false_confidence_rate: float | None
    total_elapsed_seconds: float
    pages: tuple[PageScore, ...]


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _block_text(blocks: tuple[object, ...]) -> str:
    return " ".join(getattr(b, "text", "") for b in blocks)


def _match_equation_to_gold(predicted_latex: str, gold_equations: tuple[GoldEquation, ...]) -> GoldEquation | None:
    """Best-effort pairing: the gold equation with the smallest normalized token-edit distance to the
    prediction. Real spikes with bbox-aware extractors can pair by position instead; this harness's contract
    doesn't require bbox on every equation, so text similarity is the only signal guaranteed to exist."""
    if not gold_equations:
        return None
    return min(
        gold_equations,
        key=lambda g: equation_token_edit_distance(predicted_latex, g.latex_normalized),
    )


def score_page(prediction: PageExtraction, gold: PageGold) -> PageScore:
    if prediction.error is not None:
        return PageScore(
            page=prediction.page,
            error=prediction.error,
            elapsed_seconds=prediction.elapsed_seconds,
            ram_delta_gb=prediction.ram_delta_gb,
            text_cer=None,
            text_wer=None,
            reading_order_edit_distance=None,
            heading_precision=None,
            heading_recall=None,
            heading_f1=None,
            equation_coverage=None,
            equation_exact_match_rate=None,
            equation_mean_token_edit_distance=None,
            false_confidence_rate=None,
            figure_precision=None,
            figure_recall=None,
            figure_f1=None,
            table_structure_similarity_mean=None,
        )

    predicted_text = _block_text(prediction.blocks)
    gold_text = _block_text(gold.blocks)
    predicted_order = [str(i) for i in range(len(prediction.blocks))]
    gold_order = [str(i) for i in range(len(gold.blocks))]
    predicted_headings = {str(i) for i, b in enumerate(prediction.blocks) if b.kind == "heading"}
    gold_headings = {str(i) for i, b in enumerate(gold.blocks) if b.kind == "heading"}
    heading_precision, heading_recall, heading_f1_score = heading_f1(predicted_headings, gold_headings)

    equation_matches = [
        (equation_exact_match(eq.latex, matched.latex_normalized), eq.validation_status == "verified", matched)
        for eq in prediction.equations
        if (matched := _match_equation_to_gold(eq.latex, gold.equations)) is not None
    ]
    equation_coverage = (len(equation_matches) / len(gold.equations)) if gold.equations else None
    exact_matches = [is_exact for is_exact, _verified, _matched in equation_matches]
    token_edit_distances = [
        equation_token_edit_distance(eq.latex, matched.latex_normalized)
        for eq in prediction.equations
        if (matched := _match_equation_to_gold(eq.latex, gold.equations)) is not None
    ]
    confidence_pairs = [(is_exact, verified) for is_exact, verified, _matched in equation_matches]

    predicted_boxes = [f.bbox for f in prediction.figures]
    gold_boxes = [f.bbox for f in gold.figures]
    figure_precision, figure_recall, figure_f1_score = figure_detection_f1(predicted_boxes, gold_boxes)

    table_scores = [
        table_structure_similarity(predicted_table.rows, gold_table)
        for predicted_table, gold_table in zip(prediction.tables, gold.tables, strict=False)
    ]

    return PageScore(
        page=prediction.page,
        error=None,
        elapsed_seconds=prediction.elapsed_seconds,
        ram_delta_gb=prediction.ram_delta_gb,
        text_cer=character_error_rate(predicted_text, gold_text),
        text_wer=word_error_rate(predicted_text, gold_text),
        reading_order_edit_distance=reading_order_edit_distance(predicted_order, gold_order),
        heading_precision=heading_precision,
        heading_recall=heading_recall,
        heading_f1=heading_f1_score,
        equation_coverage=equation_coverage,
        equation_exact_match_rate=_mean([1.0 if m else 0.0 for m in exact_matches]),
        equation_mean_token_edit_distance=_mean([float(d) for d in token_edit_distances]),
        false_confidence_rate=false_confidence_rate(confidence_pairs) if confidence_pairs else None,
        figure_precision=figure_precision,
        figure_recall=figure_recall,
        figure_f1=figure_f1_score,
        table_structure_similarity_mean=_mean(table_scores),
    )


def run_harness(extractor: Extractor, samples: list[tuple[bytes, int, PageGold]]) -> HarnessReport:
    """Run ``extractor`` over every ``(pdf_bytes, page_number, gold)`` sample and score each page.

    A single page's extraction failure is recorded (:attr:`PageExtraction.error`) and scored as an error, not
    raised - one bad page must never abort a whole-benchmark run (docs/28's own framing for archive/registry
    stages applies just as much here: a real corpus will contain a genuinely unopenable document).
    """
    start = time.perf_counter()
    scores: list[PageScore] = []
    for pdf_bytes, page_number, gold in samples:
        before = real_metrics().ram_used_gb
        page_start = time.perf_counter()
        try:
            prediction = extractor.extract_page(pdf_bytes, page_number)
        except Exception as exc:  # noqa: BLE001 - a candidate engine crashing on one page must not abort the benchmark
            prediction = PageExtraction(
                page=page_number,
                blocks=(),
                equations=(),
                tables=(),
                figures=(),
                elapsed_seconds=time.perf_counter() - page_start,
                ram_delta_gb=max(0.0, real_metrics().ram_used_gb - before),
                error=f"{type(exc).__name__}: {exc}",
            )
        scores.append(score_page(prediction, gold))

    cer_values = [s.text_cer for s in scores if s.text_cer is not None]
    wer_values = [s.text_wer for s in scores if s.text_wer is not None]
    fcr_values = [s.false_confidence_rate for s in scores if s.false_confidence_rate is not None]
    return HarnessReport(
        extractor_name=extractor.name,
        pages_scored=sum(1 for s in scores if s.error is None),
        pages_errored=sum(1 for s in scores if s.error is not None),
        mean_text_cer=_mean(cer_values),
        mean_text_wer=_mean(wer_values),
        mean_false_confidence_rate=_mean(fcr_values),
        total_elapsed_seconds=time.perf_counter() - start,
        pages=tuple(scores),
    )


__all__ = ["HarnessReport", "PageScore", "run_harness", "score_page"]
