"""T-P3-07: synthetic PPTX-math benchmark (option A scored without LibreOffice or pandoc)."""

from __future__ import annotations

import zipfile
from pathlib import Path

from tools import spike_pptx_math as spike


def test_benchmark_deck_stores_math_like_powerpoint_and_option_a_recovers_every_equation(tmp_path: Path) -> None:
    deck = tmp_path / "bench.pptx"
    cases = spike.build_deck(deck)
    assert len(cases) == len(spike.CASES)
    with zipfile.ZipFile(deck) as zf:
        slide = zf.read("ppt/slides/slide1.xml").decode("utf-8")
        assert "mc:AlternateContent" in slide and "a14:m" in slide and "FALLBACK-01" in slide
        assert any(name.startswith("ppt/notesSlides/") for name in zf.namelist())
    result = spike.option_a(deck, cases)
    assert result["equations_found"] == len(cases)
    assert result["correct"] == len(cases), [row for row in result["rows"] if not row["ok"]]


def test_report_states_it_is_synthetic_evidence_not_a_decision(tmp_path: Path) -> None:
    deck = tmp_path / "bench.pptx"
    cases = spike.build_deck(deck)
    a = spike.option_a(deck, cases)
    text = spike.render(a, {"available": False}, {"available": False}, len(cases))
    assert "No corpus content" in text and "Not a decision" in text
    assert "not installed on this host" in text
