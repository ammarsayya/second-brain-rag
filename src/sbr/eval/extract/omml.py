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


__all__ = ["extract_latex_equations", "is_syntactically_plausible_latex"]
