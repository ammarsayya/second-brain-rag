"""T-P3-07: native OMML -> LaTeX prototype (structure kept, unknown elements recorded, never dropped)."""

from __future__ import annotations

from xml.etree import ElementTree

import pytest

from sbr.eval.extract.omml_latex import latex_compare_key, latex_text_signature, omml_to_latex, omml_xml_to_latex

M = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def convert(body: str) -> tuple[str, list[str]]:
    element = ElementTree.fromstring(f'<m:oMath xmlns:m="{M}">{body}</m:oMath>')  # noqa: S314 - test literal
    result = omml_to_latex(element)
    return result.latex, result.unsupported


def r(text: str, sty: str | None = None) -> str:
    props = f'<m:rPr><m:sty m:val="{sty}"/></m:rPr>' if sty else ""
    return f"<m:r>{props}<m:t>{text}</m:t></m:r>"


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (f"<m:f><m:num>{r('a')}</m:num><m:den>{r('b')}</m:den></m:f>", r"\frac{a}{b}"),
        (
            f'<m:f><m:fPr><m:type m:val="lin"/></m:fPr><m:num>{r("a")}</m:num><m:den>{r("b")}</m:den></m:f>',
            "{a}/{b}",
        ),
        (f"<m:sSub><m:e>{r('M')}</m:e><m:sub>{r('z')}</m:sub></m:sSub>", "{M}_{z}"),
        (f"<m:sSup><m:e>{r('x')}</m:e><m:sup>{r('2')}</m:sup></m:sSup>", "{x}^{2}"),
        (
            f"<m:sSubSup><m:e>{r('x')}</m:e><m:sub>{r('i')}</m:sub><m:sup>{r('2')}</m:sup></m:sSubSup>",
            "{x}_{i}^{2}",
        ),
        (f"<m:sPre><m:sub>{r('0')}</m:sub><m:sup/><m:e>{r('T', 'b')}</m:e></m:sPre>", r"{}_{0}^{}{\mathbf{T}}"),
        (
            f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{r("3")}</m:e></m:rad>',
            r"\sqrt{3}",
        ),
        (f"<m:rad><m:deg>{r('3')}</m:deg><m:e>{r('x')}</m:e></m:rad>", r"\sqrt[3]{x}"),
        (
            f'<m:nary><m:naryPr><m:chr m:val="∑"/></m:naryPr><m:sub>{r("i=1")}</m:sub><m:sup>{r("n")}</m:sup>'
            f"<m:e>{r('i')}</m:e></m:nary>",
            r"\sum_{i=1}^{n}{i}",
        ),
        (f"<m:nary><m:sub>{r('0')}</m:sub><m:sup>{r('1')}</m:sup><m:e>{r('x')}</m:e></m:nary>", r"\int_{0}^{1}{x}"),
        (f"<m:d><m:e>{r('a')}</m:e><m:e>{r('b')}</m:e></m:d>", r"\left( a \mid b \right)"),
        (
            f'<m:d><m:dPr><m:begChr m:val="["/><m:endChr m:val="]"/><m:sepChr m:val=","/></m:dPr>'
            f"<m:e>{r('q')}</m:e><m:e>{r('n')}</m:e></m:d>",
            r"\left[ q , n \right]",
        ),
        (f"<m:func><m:fName>{r('sin', 'p')}</m:fName><m:e>{r('x')}</m:e></m:func>", r"\sin{x}"),
        (f'<m:acc><m:accPr><m:chr m:val="̇"/></m:accPr><m:e>{r("q")}</m:e></m:acc>', r"\dot{q}"),
        (f'<m:acc><m:accPr><m:chr m:val="⃗"/></m:accPr><m:e>{r("v")}</m:e></m:acc>', r"\vec{v}"),
        (f"<m:acc><m:e>{r('x')}</m:e></m:acc>", r"\hat{x}"),  # OMML default accent is the circumflex
        (f'<m:bar><m:barPr><m:pos m:val="top"/></m:barPr><m:e>{r("x")}</m:e></m:bar>', r"\overline{x}"),
        (f"<m:bar><m:e>{r('x')}</m:e></m:bar>", r"\underline{x}"),  # OMML default bar position is bottom
        (
            f"<m:m><m:mr><m:e>{r('a')}</m:e><m:e>{r('b')}</m:e></m:mr><m:mr><m:e>{r('c')}</m:e>"
            f"<m:e>{r('d')}</m:e></m:mr></m:m>",
            r"\begin{matrix} a & b \\ c & d \end{matrix}",
        ),
        (
            f"<m:limLow><m:e>{r('lim', 'p')}</m:e><m:lim>{r('x→0')}</m:lim></m:limLow>",
            r"\lim_{x\rightarrow0}",
        ),
        (r("α≤β·γ"), r"\alpha\leq\beta\cdot\gamma"),
        (r("ψp+η"), r"\psi p+\eta"),  # a command word must not swallow the next letter (\psip)
        (r("Hz", "p"), r"\mathrm{Hz}"),
        (r("{x}"), r"\{x\}"),
    ],
)
def test_structures_convert_with_their_shape_kept(body: str, expected: str) -> None:
    latex, unsupported = convert(body)
    assert latex == expected
    assert unsupported == []


def test_unknown_elements_keep_their_text_and_are_recorded() -> None:
    latex, unsupported = convert(f"<m:futureThing>{r('x')}</m:futureThing>")
    assert latex == "x"
    assert unsupported == ["futureThing"]


def test_unknown_accent_is_recorded_not_guessed() -> None:
    latex, unsupported = convert(f'<m:acc><m:accPr><m:chr m:val="☃"/></m:accPr><m:e>{r("x")}</m:e></m:acc>')
    assert latex == r"\overset{☃}{x}"
    assert unsupported == ["acc:U+2603"]


def test_a_math_paragraph_yields_one_equation_per_omath_in_document_order() -> None:
    xml = (
        f'<w:document xmlns:w="urn:w" xmlns:m="{M}"><w:p><m:oMathPara><m:oMath>{r("a")}</m:oMath>'
        f"<m:oMath>{r('b')}</m:oMath></m:oMathPara></w:p><w:p><m:oMath>{r('c')}</m:oMath></w:p></w:document>"
    ).encode()
    result = omml_xml_to_latex(xml)
    assert result is not None
    assert [eq.latex for eq in result] == ["a", "b", "c"]


def test_pptx_alternate_content_equation_is_converted_once() -> None:
    xml = (
        '<p:sld xmlns:p="urn:p" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
        f'xmlns:a14="urn:a14" xmlns:m="{M}"><mc:AlternateContent><mc:Choice Requires="a14"><a14:m>'
        f"<m:oMathPara><m:oMath>{r('E')}</m:oMath></m:oMathPara></a14:m></mc:Choice>"
        "<mc:Fallback><p:pic/></mc:Fallback></mc:AlternateContent></p:sld>"
    ).encode()
    result = omml_xml_to_latex(xml)
    assert result is not None
    assert [eq.latex for eq in result] == ["E"]


def test_unparseable_and_entity_expanding_xml_is_refused() -> None:
    assert omml_xml_to_latex(b"<m:oMath") is None
    bomb = (
        b'<?xml version="1.0"?><!DOCTYPE l [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
        b'<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;"><!ENTITY d "&c;&c;&c;&c;&c;&c;&c;&c;&c;&c;">'
        b'<!ENTITY e "&d;&d;&d;&d;&d;&d;&d;&d;&d;&d;"><!ENTITY f "&e;&e;&e;&e;&e;&e;&e;&e;&e;&e;">'
        b'<!ENTITY g "&f;&f;&f;&f;&f;&f;&f;&f;&f;&f;"><!ENTITY h "&g;&g;&g;&g;&g;&g;&g;&g;&g;&g;">]><l>&h;</l>'
    )
    assert omml_xml_to_latex(bomb) is None
    external = b'<?xml version="1.0"?><!DOCTYPE l [<!ENTITY x SYSTEM "file:///etc/passwd">]><l>&x;</l>'
    assert omml_xml_to_latex(external) is None


def test_compare_key_folds_notation_but_not_content() -> None:
    pandoc = r"c\left( \overrightarrow{q}(t),\dot{\overrightarrow{q}(t)} \right)"
    native = r"c\left( \vec{q}\left( t \right),\dot{\vec{q}(t)} \right)"
    assert latex_compare_key(pandoc) == latex_compare_key(native)
    assert latex_compare_key(r"\mathbf{J}_{A}") == latex_compare_key(r"{\boldsymbol{J}}_{A}")
    assert latex_compare_key(r"\frac{a}{b}") != latex_compare_key(r"\frac{b}{a}")


def test_text_signature_catches_a_latex_string_paired_with_the_wrong_equation() -> None:
    # Real T-P3-02 case: the OMML crop says U_min, the ordinal-paired pandoc LaTeX says L_max.
    assert latex_text_signature(r"{U}_{\min }") != latex_text_signature(r"L_{\max}")
    assert latex_text_signature(r"{\Delta\rho}_{w}") == latex_text_signature(r"{\mathrm{\Delta}\rho}_{w}")


def test_increment_sign_is_delta() -> None:
    assert convert(r("∆h"))[0] == r"\Delta h"


def test_pasted_math_italic_letters_become_plain_letters() -> None:
    assert convert(r("𝑏+𝑐₀"))[0] == "b+c₀"


def test_a_command_word_does_not_swallow_the_next_runs_letter() -> None:
    assert convert(r("∆") + r("x"))[0] == r"\Delta x"


def test_no_break_space_survives_whitespace_collapsing() -> None:
    latex = convert(r("A\N{NO-BREAK SPACE}"))[0]
    assert latex == "A~"
