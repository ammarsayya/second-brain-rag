"""T-P3-07 SPIKE-OMML: pure LaTeX-equation extraction and syntax-plausibility checks."""

from __future__ import annotations

from sbr.eval.extract.omml import extract_latex_equations, is_syntactically_plausible_latex


def test_extracts_display_and_inline_equations_in_pandocs_own_latex_convention() -> None:
    """Real convention found running pandoc -t latex against a real corpus thesis DOCX: display math is
    \\[...\\], inline math is \\(...\\) - not $...$ (that's the markdown writer's convention)."""
    text = r"Some prose \(x^2 + y^2\) more prose. \[\mathbf{\tau} = \mathbf{M}\ddot{\mathbf{q}}\] end."
    equations = extract_latex_equations(text)
    assert r"\mathbf{\tau} = \mathbf{M}\ddot{\mathbf{q}}" in equations
    assert "x^2 + y^2" in equations


def test_extracts_dollar_math_as_a_fallback() -> None:
    assert extract_latex_equations(r"prose $a+b$ prose") == ["a+b"]


def test_extract_handles_multiple_equations_in_order() -> None:
    text = r"\(a\) then \(b\) then \[c\]"
    assert extract_latex_equations(text) == ["c", "a", "b"]


def test_extract_returns_empty_list_for_prose_with_no_math() -> None:
    assert extract_latex_equations("just plain prose, no math at all") == []


def test_is_syntactically_plausible_accepts_real_extracted_equations() -> None:
    real_examples = [
        r"\mathbf{p}_{LS} = {(\mathbf{A}^{T}\mathbf{A})}^{- 1}\mathbf{A}^{T}\check{\psi}",
        r"c_{\phi}",
        r"\cos \phi",
    ]
    for latex in real_examples:
        assert is_syntactically_plausible_latex(latex) is True


def test_is_syntactically_plausible_rejects_unbalanced_braces() -> None:
    assert is_syntactically_plausible_latex(r"\mathbf{x") is False
    assert is_syntactically_plausible_latex(r"x}") is False


def test_is_syntactically_plausible_rejects_empty_or_error_markers() -> None:
    assert is_syntactically_plausible_latex("") is False
    assert is_syntactically_plausible_latex("   ") is False
    assert is_syntactically_plausible_latex("[ERROR converting formula]") is False
    assert is_syntactically_plausible_latex("pandoc: could not read file") is False
