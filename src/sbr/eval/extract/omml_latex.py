"""Native OMML -> LaTeX conversion prototype (T-P3-07 SPIKE-OMML, ADR-009 evidence only).

pandoc drops every PowerPoint equation (eval/reports/spike_omml.md) and is not installed on every host. This module
converts an OMML tree (``m:oMath``/``m:oMathPara``, as found in DOCX ``word/document.xml`` and PPTX
``ppt/slides/slideN.xml`` alike) straight to LaTeX with the standard library, so DOCX and PPTX math go through one
code path and the equation's structure (fractions, scripts, n-ary operators, delimiters, matrices) is kept.

It is a **prototype for the ADR-009 decision, not the chosen architecture**: it is scored against pandoc and the
owner's review in ``tools/spike_omml.py --native-latex``. Elements it does not know are never dropped silently:
their text content is kept and their tag is recorded in :attr:`OmmlLatex.unsupported`, so a caller can mark the
equation uncertain (HC: uncertain extraction stays marked uncertain).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from xml.etree import ElementTree

from sbr.eval.extract.omml import OMML_NAMESPACE

__all__ = ["OmmlLatex", "latex_compare_key", "latex_text_signature", "omml_to_latex", "omml_xml_to_latex"]

_M = f"{{{OMML_NAMESPACE}}}"

# Unicode math characters -> LaTeX commands. Letters and digits pass through unchanged.
_SYMBOLS: dict[str, str] = {
    # Greek
    "α": r"\alpha",
    "β": r"\beta",
    "γ": r"\gamma",
    "δ": r"\delta",
    "ε": r"\varepsilon",
    "ϵ": r"\epsilon",
    "ζ": r"\zeta",
    "η": r"\eta",
    "θ": r"\theta",
    "ϑ": r"\vartheta",
    "ι": r"\iota",
    "κ": r"\kappa",
    "λ": r"\lambda",
    "μ": r"\mu",
    "ν": r"\nu",
    "ξ": r"\xi",
    "π": r"\pi",
    "ϖ": r"\varpi",
    "ρ": r"\rho",
    "ϱ": r"\varrho",
    "σ": r"\sigma",
    "ς": r"\varsigma",
    "τ": r"\tau",
    "υ": r"\upsilon",
    "φ": r"\varphi",
    "ϕ": r"\phi",
    "χ": r"\chi",
    "ψ": r"\psi",
    "ω": r"\omega",
    "Γ": r"\Gamma",
    "Δ": r"\Delta",
    "∆": r"\Delta",  # U+2206 INCREMENT, what Word inserts for "Delta" in many fonts
    "Θ": r"\Theta",
    "Λ": r"\Lambda",
    "Ξ": r"\Xi",
    "Π": r"\Pi",
    "Σ": r"\Sigma",
    "Υ": r"\Upsilon",
    "Φ": r"\Phi",
    "Ψ": r"\Psi",
    "Ω": r"\Omega",
    # operators and relations
    "±": r"\pm",
    "∓": r"\mp",
    "×": r"\times",
    "·": r"\cdot",
    "⋅": r"\cdot",
    "∙": r"\cdot",
    "÷": r"\div",
    "∗": "*",
    "−": "-",
    "≤": r"\leq",
    "≥": r"\geq",
    "≠": r"\neq",
    "≈": r"\approx",
    "≡": r"\equiv",
    "∼": r"\sim",
    "≃": r"\simeq",
    "≅": r"\cong",
    "∝": r"\propto",
    "≪": r"\ll",
    "≫": r"\gg",
    "→": r"\rightarrow",
    "←": r"\leftarrow",
    "↔": r"\leftrightarrow",
    "⇒": r"\Rightarrow",
    "⇐": r"\Leftarrow",
    "⇔": r"\Leftrightarrow",
    "↦": r"\mapsto",
    "∞": r"\infty",
    "∂": r"\partial",
    "∇": r"\nabla",
    "∈": r"\in",
    "∉": r"\notin",
    "⊂": r"\subset",
    "⊆": r"\subseteq",
    "∪": r"\cup",
    "∩": r"\cap",
    "∅": r"\emptyset",
    "∀": r"\forall",
    "∃": r"\exists",
    "¬": r"\neg",
    "∧": r"\wedge",
    "∨": r"\vee",
    "∘": r"\circ",
    "°": r"^{\circ}",
    "′": "'",
    "″": "''",
    "…": r"\ldots",
    "⋯": r"\cdots",
    "⋮": r"\vdots",
    "⋱": r"\ddots",
    "ℏ": r"\hbar",
    "ℓ": r"\ell",
    "ℝ": r"\mathbb{R}",
    "ℕ": r"\mathbb{N}",
    "ℤ": r"\mathbb{Z}",
    "ℂ": r"\mathbb{C}",
    "⊥": r"\perp",
    "∥": r"\parallel",
    "∠": r"\angle",
    "√": r"\surd",
    "⊗": r"\otimes",
    "⊕": r"\oplus",
    "∑": r"\sum",
    "∏": r"\prod",
    "∫": r"\int",
    "\N{FUNCTION APPLICATION}": "",
    "\N{INVISIBLE TIMES}": "",
    "\N{ZERO WIDTH SPACE}": "",
    "\N{NO-BREAK SPACE}": "~",  # not "\\ ": whitespace collapsing would strand the backslash
    "\N{THIN SPACE}": r"\,",
    "\N{FOUR-PER-EM SPACE}": r"\;",
    "{": r"\{",
    "}": r"\}",
    "%": r"\%",
    "#": r"\#",
    "&": r"\&",
    "_": r"\_",
    "$": r"\$",
}

_NARY: dict[str, str] = {
    "∑": r"\sum",
    "∏": r"\prod",
    "∐": r"\coprod",
    "∫": r"\int",
    "∬": r"\iint",
    "∭": r"\iiint",
    "∮": r"\oint",
    "⋃": r"\bigcup",
    "⋂": r"\bigcap",
    "⋁": r"\bigvee",
    "⋀": r"\bigwedge",
}

_ACCENTS: dict[str, str] = {
    "̂": r"\hat",
    "̃": r"\tilde",
    "̄": r"\bar",
    "̅": r"\overline",
    "̇": r"\dot",
    "̈": r"\ddot",
    "⃛": r"\dddot",
    "⃗": r"\vec",
    "⃖": r"\overleftarrow",
    "⃡": r"\overleftrightarrow",
    "̆": r"\breve",
    "̌": r"\check",
    "́": r"\acute",
    "̀": r"\grave",
    "→": r"\vec",
    "^": r"\hat",
    "~": r"\tilde",
    "¯": r"\bar",
}

_FUNCTION_NAMES = (
    "sin cos tan cot sec csc arcsin arccos arctan sinh cosh tanh coth exp log ln lg lim liminf limsup "
    "max min sup inf det dim ker deg arg gcd Pr"
)
_FUNCTIONS = frozenset(_FUNCTION_NAMES.split(" "))

_DELIMITERS: dict[str, str] = {
    "(": "(",
    ")": ")",
    "[": "[",
    "]": "]",
    "{": r"\{",
    "}": r"\}",
    "|": "|",
    "‖": r"\|",
    "⟨": r"\langle",
    "⟩": r"\rangle",
    "〈": r"\langle",
    "〉": r"\rangle",
    "⌊": r"\lfloor",
    "⌋": r"\rfloor",
    "⌈": r"\lceil",
    "⌉": r"\rceil",
    "": ".",
}

_STRUCTURAL_PROPERTIES = frozenset(
    _M + tag
    for tag in (
        "rPr",
        "ctrlPr",
        "fPr",
        "sSubPr",
        "sSupPr",
        "sSubSupPr",
        "sPrePr",
        "radPr",
        "naryPr",
        "dPr",
        "funcPr",
        "accPr",
        "barPr",
        "groupChrPr",
        "limLowPr",
        "limUppPr",
        "mPr",
        "mrPr",
        "eqArrPr",
        "boxPr",
        "borderBoxPr",
        "phantPr",
        "oMathParaPr",
        "argPr",
    )
)


@dataclass(slots=True)
class OmmlLatex:
    """A converted equation. ``unsupported`` lists OMML tags whose structure was not translated."""

    latex: str
    unsupported: list[str] = field(default_factory=list)

    @property
    def exact(self) -> bool:
        return not self.unsupported


_COMMAND_WORD = re.compile(r"\\[A-Za-z]+$")


def _join(pieces: Iterable[str]) -> str:
    """Concatenate converted siblings, keeping a trailing command word (``\\Delta``) apart from a following
    letter in the next run (``\\Delta x``, not ``\\Deltax``)."""
    out: list[str] = []
    for piece in pieces:
        if out and piece[:1].isalpha() and _COMMAND_WORD.search(out[-1]):
            out.append(" ")
        out.append(piece)
    return "".join(out)


def _symbols(text: str) -> str:
    """Map Unicode math characters to LaTeX, keeping a command word (``\\psi``) apart from a following letter."""
    out: list[str] = []
    for ch in text:
        if "\U0001d400" <= ch <= "\U0001d7ff":  # Mathematical Alphanumeric Symbols (pasted math italic 𝑏 -> b)
            ch = unicodedata.normalize("NFKC", ch)
        piece = _SYMBOLS.get(ch, ch)
        if out and _COMMAND_WORD.search(out[-1]) and piece[:1].isalpha():
            out.append(" ")
        out.append(piece)
    return "".join(out)


def _val(node: ElementTree.Element | None, prop: str, default: str | None = None) -> str | None:
    """``m:<prop> m:val`` inside a property element; a present element without ``m:val`` means "on" (OMML)."""
    if node is None:
        return default
    child = node.find(_M + prop)
    if child is None:
        return default
    return child.get(_M + "val", "on")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class _Converter:
    def __init__(self) -> None:
        self.unsupported: list[str] = []

    def children(self, node: ElementTree.Element) -> str:
        return _join(self.convert(child) for child in node if child.tag not in _STRUCTURAL_PROPERTIES)

    def arg(self, node: ElementTree.Element, name: str) -> str:
        child = node.find(_M + name)
        return self.children(child) if child is not None else ""

    def convert(self, node: ElementTree.Element) -> str:
        tag = node.tag
        if not tag.startswith(_M):
            # Host-document wrappers (w:, a:, mc:) carry no math of their own; keep any math inside them.
            return self.children(node)
        handler = getattr(self, "_" + _local(tag), None)
        if handler is None:
            self.unsupported.append(_local(tag))
            return self.children(node)
        result: str = handler(node)
        return result

    # --- containers -------------------------------------------------------------------------------------------
    def _oMathPara(self, node: ElementTree.Element) -> str:  # noqa: N802 - OMML element name
        rows = [self.convert(child) for child in node if child.tag == _M + "oMath"]
        return r" \\ ".join(rows)

    def _oMath(self, node: ElementTree.Element) -> str:  # noqa: N802
        return self.children(node)

    def _e(self, node: ElementTree.Element) -> str:
        return self.children(node)

    _num = _den = _sub = _sup = _deg = _lim = _fName = _e  # noqa: N815

    # --- text runs --------------------------------------------------------------------------------------------
    def _r(self, node: ElementTree.Element) -> str:
        text = "".join(t.text or "" for t in node.iter(_M + "t"))
        props = node.find(_M + "rPr")
        style = _val(props, "sty")
        script = _val(props, "scr")
        normal_text = _val(props, "nor") is not None
        if not text:
            return ""
        if text.strip() in _FUNCTIONS and style in (None, "p"):
            return "\\" + text.strip() + " "
        body = _symbols(text)
        if normal_text:
            return r"\text{" + text.replace("\\", r"\textbackslash{}") + "}"
        if script == "double-struck":
            return r"\mathbb{" + body + "}"
        if script == "script":
            return r"\mathcal{" + body + "}"
        if script == "fraktur":
            return r"\mathfrak{" + body + "}"
        if style == "b":
            return r"\mathbf{" + body + "}"
        if style == "bi":
            return r"\boldsymbol{" + body + "}"
        if style == "p" and any(ch.isalpha() for ch in text) and len(text.strip()) > 1:
            return r"\mathrm{" + body + "}"
        return body

    # --- structures -------------------------------------------------------------------------------------------
    def _f(self, node: ElementTree.Element) -> str:
        kind = _val(node.find(_M + "fPr"), "type", "bar")
        num, den = self.arg(node, "num"), self.arg(node, "den")
        if kind == "lin":
            return f"{{{num}}}/{{{den}}}"
        if kind == "noBar":
            return rf"\genfrac{{}}{{}}{{0pt}}{{}}{{{num}}}{{{den}}}"
        if kind == "skw":
            return rf"{{}}^{{{num}}}\!/\!{{}}_{{{den}}}"
        return rf"\frac{{{num}}}{{{den}}}"

    def _sSup(self, node: ElementTree.Element) -> str:  # noqa: N802
        return f"{{{self.arg(node, 'e')}}}^{{{self.arg(node, 'sup')}}}"

    def _sSub(self, node: ElementTree.Element) -> str:  # noqa: N802
        return f"{{{self.arg(node, 'e')}}}_{{{self.arg(node, 'sub')}}}"

    def _sSubSup(self, node: ElementTree.Element) -> str:  # noqa: N802
        return f"{{{self.arg(node, 'e')}}}_{{{self.arg(node, 'sub')}}}^{{{self.arg(node, 'sup')}}}"

    def _sPre(self, node: ElementTree.Element) -> str:  # noqa: N802
        return f"{{}}_{{{self.arg(node, 'sub')}}}^{{{self.arg(node, 'sup')}}}{{{self.arg(node, 'e')}}}"

    def _rad(self, node: ElementTree.Element) -> str:
        hide = _val(node.find(_M + "radPr"), "degHide", "off") in ("on", "1", "true")
        degree = "" if hide else self.arg(node, "deg")
        body = self.arg(node, "e")
        return rf"\sqrt[{degree}]{{{body}}}" if degree else rf"\sqrt{{{body}}}"

    def _nary(self, node: ElementTree.Element) -> str:
        props = node.find(_M + "naryPr")
        char = _val(props, "chr", "∫") or "∫"
        operator = _NARY.get(char, _SYMBOLS.get(char, char))
        sub_hidden = _val(props, "subHide", "off") in ("on", "1", "true")
        sup_hidden = _val(props, "supHide", "off") in ("on", "1", "true")
        lower, upper = self.arg(node, "sub"), self.arg(node, "sup")
        limits = "" if sub_hidden or not lower else f"_{{{lower}}}"
        limits += "" if sup_hidden or not upper else f"^{{{upper}}}"
        return f"{operator}{limits}{{{self.arg(node, 'e')}}}"

    def _d(self, node: ElementTree.Element) -> str:
        props = node.find(_M + "dPr")
        begin = _val(props, "begChr", "(")
        end = _val(props, "endChr", ")")
        separator = _val(props, "sepChr", "|") or "|"
        parts = [self.children(e) for e in node.findall(_M + "e")]
        sep = _SYMBOLS.get(separator, separator)
        inner = f" {sep} ".join(parts) if separator != "|" else r" \mid ".join(parts)
        left = _DELIMITERS.get(begin or "", begin or ".")
        right = _DELIMITERS.get(end or "", end or ".")
        return rf"\left{left} {inner} \right{right}"

    def _func(self, node: ElementTree.Element) -> str:
        name = self.arg(node, "fName").strip()
        return f"{name}{{{self.arg(node, 'e')}}}"

    def _acc(self, node: ElementTree.Element) -> str:
        char = _val(node.find(_M + "accPr"), "chr", "̂") or "̂"
        command = _ACCENTS.get(char)
        body = self.arg(node, "e")
        if command is None:
            self.unsupported.append(f"acc:U+{ord(char[0]):04X}")
            return rf"\overset{{{char}}}{{{body}}}"
        return f"{command}{{{body}}}"

    def _bar(self, node: ElementTree.Element) -> str:
        position = _val(node.find(_M + "barPr"), "pos", "bot")
        command = r"\overline" if position == "top" else r"\underline"
        return f"{command}{{{self.arg(node, 'e')}}}"

    def _groupChr(self, node: ElementTree.Element) -> str:  # noqa: N802
        props = node.find(_M + "groupChrPr")
        char = _val(props, "chr", "⏟") or "⏟"
        position = _val(props, "pos", "bot")
        body = self.arg(node, "e")
        if char == "⏟":
            return rf"\underbrace{{{body}}}"
        if char == "⏞":
            return rf"\overbrace{{{body}}}"
        symbol = _SYMBOLS.get(char, char)
        return rf"\overset{{{symbol}}}{{{body}}}" if position == "top" else rf"\underset{{{symbol}}}{{{body}}}"

    def _limLow(self, node: ElementTree.Element) -> str:  # noqa: N802
        base, limit = self.arg(node, "e"), self.arg(node, "lim")
        if base.strip().startswith("\\") and base.strip().rstrip("{} ").lstrip("\\") in _FUNCTIONS:
            return f"{base.strip()}_{{{limit}}}"
        return rf"\underset{{{limit}}}{{{base}}}"

    def _limUpp(self, node: ElementTree.Element) -> str:  # noqa: N802
        return rf"\overset{{{self.arg(node, 'lim')}}}{{{self.arg(node, 'e')}}}"

    def _m(self, node: ElementTree.Element) -> str:
        rows = [" & ".join(self.children(e) for e in row.findall(_M + "e")) for row in node.findall(_M + "mr")]
        return r"\begin{matrix} " + r" \\ ".join(rows) + r" \end{matrix}"

    def _eqArr(self, node: ElementTree.Element) -> str:  # noqa: N802
        rows = [self.children(e) for e in node.findall(_M + "e")]
        return r"\begin{aligned} " + r" \\ ".join(rows) + r" \end{aligned}"

    def _box(self, node: ElementTree.Element) -> str:
        return self.arg(node, "e")

    def _borderBox(self, node: ElementTree.Element) -> str:  # noqa: N802
        return rf"\boxed{{{self.arg(node, 'e')}}}"

    def _phant(self, node: ElementTree.Element) -> str:
        shown = _val(node.find(_M + "phantPr"), "show", "on") in ("on", "1", "true")
        body = self.arg(node, "e")
        return body if shown else rf"\phantom{{{body}}}"


def omml_to_latex(element: ElementTree.Element) -> OmmlLatex:
    """Convert one ``m:oMath`` or ``m:oMathPara`` element (or any element containing one) to LaTeX."""
    converter = _Converter()
    latex = " ".join(converter.convert(element).split())
    return OmmlLatex(latex=latex, unsupported=converter.unsupported)


def omml_xml_to_latex(xml_bytes: bytes) -> list[OmmlLatex] | None:
    """Convert every outermost ``m:oMath`` in one Office XML part, in document order. ``None`` if unparseable.

    Equations inside an ``m:oMathPara`` are returned one by one, as
    :func:`~sbr.eval.extract.omml.count_omml_equations` counts them, so the two stay comparable.
    """
    try:
        # Same expat protections and pinned test as count_omml_equations (entity amplification, external entities).
        root = ElementTree.fromstring(xml_bytes)  # noqa: S314
    except ElementTree.ParseError:
        return None
    found: list[OmmlLatex] = []

    def walk(node: ElementTree.Element) -> None:
        if node.tag == _M + "oMath":
            found.append(omml_to_latex(node))
            return
        for child in node:
            walk(child)

    walk(root)
    return found


_KEY_COMMAND_ALIASES = (
    (re.compile(r"\\(?:left|right|mathrm|mathit|operatorname|text)\b"), ""),
    (re.compile(r"\\(?:boldsymbol|bm)\b"), r"\\mathbf"),
    (re.compile(r"\\overrightarrow\b"), r"\\vec"),
    (re.compile(r"\\widetilde\b"), r"\\tilde"),
    (re.compile(r"\\widehat\b"), r"\\hat"),
    (re.compile(r"\\[ ,;:!]|\\q?quad\b"), ""),
)
_KEY_LITERALS = (
    ("\\lbrack", "["),
    ("\\rbrack", "]"),
    ("\\{", "{"),
    ("\\}", "}"),
    ("\\mid", "|"),
    ("\\cdot", "*"),
    ("\\ast", "*"),
    ("\\leq", "\\le"),
    ("\\geq", "\\ge"),
    ("\\to", "\\rightarrow"),
    ("\\ldots", "..."),
    ("\\cdots", "..."),
    ("\\surd", "\\sqrt"),
)


def latex_compare_key(latex: str) -> str:
    """A lenient comparison key: two LaTeX strings with the same key render the same equation up to notation.

    It drops grouping braces, whitespace, spacing commands and ``\\left``/``\\right``, and folds notational
    synonyms (``\\boldsymbol``/``\\mathbf``, ``\\overrightarrow``/``\\vec``, ``\\cdot``/``*`` ...). It is for
    *scoring converters against each other*, never for storing an equation.
    """
    key = latex
    for pattern, replacement in _KEY_COMMAND_ALIASES:
        key = pattern.sub(replacement, key)
    for old, new in _KEY_LITERALS:
        key = key.replace(old, new)
    key = re.sub(r"[{}\s]", "", key).replace("_^", "").replace("^_", "")
    return re.sub(r"(\\mathbf)(?:\\mathbf)+", r"\1", key)


def latex_text_signature(latex: str) -> str:
    """The sorted letters and digits of an equation, LaTeX commands removed: equal signatures mean the same
    *content*, whatever the structure. Used to catch two LaTeX strings that were paired with the wrong equation."""
    # Function names (\\min, \\sin ...) are content: "\\min" and a plain "min" must agree.
    text = re.sub(r"\\([A-Za-z]+)", lambda m: m.group(1) if m.group(1) in _FUNCTIONS else "", latex)
    return "".join(sorted(ch for ch in text if ch.isalnum()))
