"""T-P3-04: extraction evaluation harness - dummy extractor end-to-end, plus scoring edge cases."""

from __future__ import annotations

from pathlib import Path

from sbr.eval.extract.contracts import (
    ExtractedBlock,
    ExtractedEquation,
    GoldBlock,
    GoldEquation,
    PageExtraction,
    PageGold,
)
from sbr.eval.extract.dummy import DummyTextExtractor
from sbr.eval.extract.harness import run_harness, score_page

FIXTURE_PDF = Path(__file__).parent / "fixtures" / "corpus" / "Regelungstechnik" / "skript.pdf"


class _StubExtractor:
    name = "stub"

    def __init__(self, prediction: PageExtraction) -> None:
        self._prediction = prediction

    def extract_page(self, pdf_bytes: bytes, page_number: int) -> PageExtraction:
        return self._prediction


class _CrashingExtractor:
    name = "crashing"

    def extract_page(self, pdf_bytes: bytes, page_number: int) -> PageExtraction:
        raise RuntimeError("boom")


def _perfect_page(text: str) -> tuple[PageExtraction, PageGold]:
    blocks = (ExtractedBlock(kind="paragraph", reading_order=0, text=text),)
    gold_blocks = (GoldBlock(kind="paragraph", reading_order=0, text=text),)
    prediction = PageExtraction(
        page=1, blocks=blocks, equations=(), tables=(), figures=(), elapsed_seconds=0.01, ram_delta_gb=0.0
    )
    gold = PageGold(page=1, blocks=gold_blocks, equations=(), tables=(), figures=())
    return prediction, gold


def test_score_page_perfect_prediction_scores_zero_error() -> None:
    prediction, gold = _perfect_page("the quick brown fox")
    score = score_page(prediction, gold)
    assert score.text_cer == 0.0
    assert score.text_wer == 0.0
    assert score.reading_order_edit_distance == 0
    assert score.error is None


def test_score_page_records_the_extractor_own_error() -> None:
    prediction = PageExtraction(
        page=1,
        blocks=(),
        equations=(),
        tables=(),
        figures=(),
        elapsed_seconds=0.0,
        ram_delta_gb=0.0,
        error="PdfReadError: corrupt",
    )
    gold = PageGold(page=1, blocks=(), equations=(), tables=(), figures=())
    score = score_page(prediction, gold)
    assert score.error == "PdfReadError: corrupt"
    assert score.text_cer is None


def test_score_page_false_confidence_on_a_wrong_but_verified_equation() -> None:
    prediction = PageExtraction(
        page=1,
        blocks=(),
        equations=(ExtractedEquation(latex="x^3", confidence=0.99, validation_status="verified"),),
        tables=(),
        figures=(),
        elapsed_seconds=0.0,
        ram_delta_gb=0.0,
    )
    gold = PageGold(
        page=1,
        blocks=(),
        equations=(GoldEquation(latex_normalized="x^2", source_kind="latex_source"),),
        tables=(),
        figures=(),
    )
    score = score_page(prediction, gold)
    assert score.equation_exact_match_rate == 0.0
    assert score.false_confidence_rate == 1.0  # marked verified, but wrong
    assert score.equation_coverage == 1.0  # one gold equation, one prediction matched to it


def test_run_harness_on_a_stub_extractor_across_multiple_pages() -> None:
    prediction, gold = _perfect_page("hello world")
    samples = [(b"unused", 1, gold), (b"unused", 1, gold)]
    report = run_harness(_StubExtractor(prediction), samples)
    assert report.extractor_name == "stub"
    assert report.pages_scored == 2
    assert report.pages_errored == 0
    assert report.mean_text_cer == 0.0


def test_run_harness_records_a_crashing_extractor_as_an_error_not_an_exception() -> None:
    _prediction, gold = _perfect_page("text")
    samples = [(b"unused", 1, gold)]
    report = run_harness(_CrashingExtractor(), samples)
    assert report.pages_scored == 0
    assert report.pages_errored == 1
    assert report.pages[0].error is not None
    assert "boom" in report.pages[0].error


def test_dummy_text_extractor_runs_on_a_real_pdf_fixture_and_produces_a_report() -> None:
    """T-P3-04's own acceptance criterion: 'harness runs on a dummy extractor and produces a report'."""
    pdf_bytes = FIXTURE_PDF.read_bytes()
    prediction = DummyTextExtractor().extract_page(pdf_bytes, 1)
    assert prediction.error is None
    assert len(prediction.blocks) > 0
    assert prediction.elapsed_seconds >= 0.0

    gold = PageGold(
        page=1,
        blocks=(GoldBlock(kind="paragraph", reading_order=0, text="placeholder"),),
        equations=(),
        tables=(),
        figures=(),
    )
    report = run_harness(DummyTextExtractor(), [(pdf_bytes, 1, gold)])
    assert report.extractor_name == "dummy_text_layer"
    assert report.pages_scored == 1
    assert report.mean_text_cer is not None


def test_dummy_text_extractor_records_an_error_for_bytes_that_are_not_a_pdf() -> None:
    prediction = DummyTextExtractor().extract_page(b"not a pdf at all", 1)
    assert prediction.error is not None
    assert prediction.blocks == ()
