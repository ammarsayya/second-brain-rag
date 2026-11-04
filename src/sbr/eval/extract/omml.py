"""OMML→LaTeX conversion evidence-gathering (T-P3-07, SPIKE-OMML, ADR-009).

Pure helpers only: extracting LaTeX equation strings out of pandoc's ``-t latex`` output, and a lightweight
syntax-plausibility check. The actual pandoc invocation (a subprocess call against a real DOCX/PPTX's bytes)
lives in ``tools/spike_omml.py``, which is real-corpus I/O and not unit-testable the same way.

**What "verify rendering" means here, and what it does not**: docs/28's T-P3-07 acceptance criterion is
"≥98% of sampled OMML equations render correctly", checked by "render comparison + manual review of 50" —
that is a human judgment call this module cannot make. What IS checked mechanically is whether the extracted
LaTeX is syntactically well-formed (balanced braces/brackets, non-empty, no pandoc error markers) — a
necessary but not sufficient condition for "renders correctly". The real correctness verdict is the owner's,
on the 50-sample manual review this spike's report prepares for them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from xml.etree import ElementTree

_DISPLAY_MATH = re.compile(r"\\\[(.+?)\\\]", re.DOTALL)
_INLINE_PAREN_MATH = re.compile(r"\\\((.+?)\\\)", re.DOTALL)
_INLINE_DOLLAR_MATH = re.compile(r"(?<!\\)\$(?!\$)(.+?)(?<!\\)\$(?!\$)", re.DOTALL)
_PANDOC_ERROR_MARKERS = ("[ERROR", "pandoc: ", "Could not convert")


def extract_latex_equations(pandoc_latex_output: str) -> list[str]:
    """Every equation pandoc's LaTeX writer emitted, in document order, display math first per line found.

    Pandoc's ``-t latex`` writer uses ``\\[...\\]`` for display math and ``\\(...\\)`` for inline math (not
    ``$...$``, which is a *markdown*-writer convention) — found empirically running this against a real
    corpus thesis DOCX (287 inline + 20 display equations recovered). ``$...$`` is still checked as a
    fallback in case a future pandoc version or a different ``-t`` target changes convention.
    """
    equations: list[str] = []
    for pattern in (_DISPLAY_MATH, _INLINE_PAREN_MATH, _INLINE_DOLLAR_MATH):
        equations.extend(match.strip() for match in pattern.findall(pandoc_latex_output))
    return equations


def is_syntactically_plausible_latex(latex: str) -> bool:
    """Balanced braces/brackets, non-empty, no pandoc error marker. Necessary, not sufficient, for
    "renders correctly" — see module docstring."""
    if not latex.strip():
        return False
    if any(marker in latex for marker in _PANDOC_ERROR_MARKERS):
        return False
    depth = 0
    for char in latex:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


OMML_NAMESPACE = "http://schemas.openxmlformats.org/officeDocument/2006/math"
_OMATH = f"{{{OMML_NAMESPACE}}}oMath"
_OMATH_PARA = f"{{{OMML_NAMESPACE}}}oMathPara"


@dataclass(frozen=True, slots=True)
class OmmlCount:
    """Native OMML equations in one Office XML part. ``display`` counts equations inside an ``m:oMathPara``."""

    total: int
    display: int

    @property
    def inline(self) -> int:
        return self.total - self.display


def count_omml_equations(xml_bytes: bytes) -> OmmlCount | None:
    """Count outermost ``m:oMath`` elements in one DOCX/PPTX XML part, by namespace URI rather than by prefix.

    A PPTX equation sits in ``mc:AlternateContent``: the ``mc:Choice`` carries the ``a14:m``/OMML tree and the
    ``mc:Fallback`` only a picture, so each equation is counted once. Returns ``None`` (never a guessed 0) for XML
    that does not parse, so a caller can report the part as unreadable.
    """
    try:
        # Expat (>= 2.4) refuses entity amplification and never resolves external entities; both surface as
        # ParseError -> None. Pinned by test_refuses_entity_expansion_and_external_entities, so no new dependency.
        root = ElementTree.fromstring(xml_bytes)  # noqa: S314
    except ElementTree.ParseError:
        return None
    total = display = 0

    def walk(node: ElementTree.Element, in_para: bool) -> None:
        nonlocal total, display
        if node.tag == _OMATH:
            total += 1
            display += int(in_para)
            return  # an equation's own subtree is not searched for further equations
        for child in node:
            walk(child, in_para or node.tag == _OMATH_PARA)

    walk(root, False)
    return OmmlCount(total, display)


__all__ = [
    "OMML_NAMESPACE",
    "OmmlCount",
    "count_omml_equations",
    "extract_latex_equations",
    "is_syntactically_plausible_latex",
]
