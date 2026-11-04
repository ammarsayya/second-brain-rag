"""T-P3-07 SPIKE-OMML: pure LaTeX-equation extraction and syntax-plausibility checks."""

from __future__ import annotations

import zipfile
from pathlib import Path

from sbr.eval.extract.omml import (
    OmmlCount,
    count_omml_equations,
    extract_latex_equations,
    is_syntactically_plausible_latex,
)


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


_PPTX_FIXTURE = Path(__file__).parent / "fixtures" / "corpus" / "Regelungstechnik" / "Übung" / "folien.pptx"
_M = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'


def test_counts_the_pptx_fixtures_native_equation_once_despite_its_fallback() -> None:
    """The synthetic PPTX (T-P1-13) wraps its equation in mc:AlternateContent with a text fallback."""
    with zipfile.ZipFile(_PPTX_FIXTURE) as archive:
        slide = archive.read("ppt/slides/slide1.xml")
        layout = archive.read("ppt/slideLayouts/slideLayout1.xml")
    assert count_omml_equations(slide) == OmmlCount(total=1, display=0)
    assert count_omml_equations(layout) == OmmlCount(total=0, display=0)


def test_separates_display_from_inline_and_never_counts_inside_an_equation() -> None:
    xml = (
        f"<w:body xmlns:w='urn:w' {_M}><m:oMathPara><m:oMath><m:r><m:t>a</m:t></m:r></m:oMath>"
        "<m:oMath><m:r><m:t>b</m:t></m:r></m:oMath></m:oMathPara>"
        "<m:oMath><m:e><m:oMath><m:r><m:t>nested</m:t></m:r></m:oMath></m:e></m:oMath></w:body>"
    ).encode()
    count = count_omml_equations(xml)
    assert count == OmmlCount(total=3, display=2)
    assert count is not None and count.inline == 1


def test_matches_by_namespace_uri_not_by_prefix() -> None:
    xml = b"<root xmlns:q='http://schemas.openxmlformats.org/officeDocument/2006/math'><q:oMath/></root>"
    assert count_omml_equations(xml) == OmmlCount(total=1, display=0)
    assert count_omml_equations(b"<root xmlns:m='urn:not-omml'><m:oMath/></root>") == OmmlCount(0, 0)


def test_malformed_xml_is_unreadable_not_zero() -> None:
    assert count_omml_equations(b"<m:oMath") is None


def test_refuses_entity_expansion_and_external_entities() -> None:
    """Security boundary: Office parts are untrusted bytes. The stdlib parser must refuse both attacks."""
    laughs = "".join(f'<!ENTITY e{i} "{f"&e{i - 1};" * 10}">' for i in range(1, 9))
    bomb = f'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY e0 "aaaaaaaaaa">{laughs}]><r>&e8;</r>'.encode()
    xxe = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><r>&x;</r>'
    assert count_omml_equations(bomb) is None
    assert count_omml_equations(xxe) is None


def test_is_syntactically_plausible_treats_escaped_braces_as_literals() -> None:
    assert is_syntactically_plausible_latex(r"\left\{ \begin{aligned} a \\ b \end{aligned} \right.") is True
    assert is_syntactically_plausible_latex(r"\{x\}") is True
    assert is_syntactically_plausible_latex(r"a \\{b}") is True  # a line break, then a real group
    assert is_syntactically_plausible_latex(r"a \\{b") is False
