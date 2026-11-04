"""T-P3-02: the math selector must not pair an OMML crop with another equation's pandoc LaTeX."""

from __future__ import annotations

from tools import select_gold_math_sample

M = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def _crop(base: str) -> str:
    """``base`` subscripted with an upright "min", as Word stores U_min."""
    sub = '<m:sub><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>min</m:t></m:r></m:sub>'
    return f'<m:oMath xmlns:m="{M}"><m:sSub><m:e><m:r><m:t>{base}</m:t></m:r></m:e>{sub}</m:sSub></m:oMath>'


def test_a_correct_pair_is_kept_whatever_the_notation() -> None:
    assert select_gold_math_sample.paired_text_agrees(_crop("U"), r"U_{\min}")
    assert select_gold_math_sample.paired_text_agrees(_crop("U"), r"{U}_{min}")


def test_a_drifted_ordinal_pair_is_rejected() -> None:
    # The real case behind 42 bad T-P3-02 candidates: the crop says U_min, the paired LaTeX says L_max.
    assert not select_gold_math_sample.paired_text_agrees(_crop("U"), r"L_{\max}")
