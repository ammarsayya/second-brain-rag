"""T-P3-07 / ADR-009 evidence: measure PPTX-math extraction options on a synthetic benchmark deck.

No corpus content is used. The tool builds a deck the way PowerPoint stores math: each equation is an
``mc:AlternateContent`` whose ``mc:Choice`` holds ``a14:m`` (OMML) and whose ``mc:Fallback`` holds a unique marker text
``FALLBACK-<n>``. An option that reports a marker read the fallback, not the equation. Real PowerPoint fallbacks are
usually *pictures*, so any option that relies on the fallback gets no math at all on real decks.

Options measured (each only if its tool is installed):
  A  native OMML -> LaTeX (``sbr.eval.extract.omml_latex``), slides and notes
  B  LibreOffice headless: PPTX -> ODP (looks for MathML objects) and PPTX -> PDF (text layer)
  P  pandoc reading PPTX directly
  C  render slides and recognise formula images: not runnable here (no local formula recognizer; SPIKE-MATH open)

Usage: uv run python tools/spike_pptx_math.py [--output eval/reports/spike_pptx_math_options.md] [--workdir DIR]
"""

from __future__ import annotations

import argparse
import io
import platform
import re
import resource
import shutil
import subprocess
import sys
import tempfile
import time
import tracemalloc
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lxml import etree
from pptx import Presentation
from pptx.util import Emu

from sbr.eval.extract.omml_latex import latex_compare_key, omml_xml_to_latex

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
A14_NS = "http://schemas.microsoft.com/office/drawing/2010/main"


def r(text: str, sty: str | None = None) -> str:
    props = f'<m:rPr><m:sty m:val="{sty}"/></m:rPr>' if sty else ""
    return f'<m:r>{props}<m:t xml:space="preserve">{text}</m:t></m:r>'


def sub(base: str, s: str) -> str:
    return f"<m:sSub><m:e>{base}</m:e><m:sub>{s}</m:sub></m:sSub>"


def sup(base: str, s: str) -> str:
    return f"<m:sSup><m:e>{base}</m:e><m:sup>{s}</m:sup></m:sSup>"


def frac(n: str, d: str) -> str:
    return f"<m:f><m:num>{n}</m:num><m:den>{d}</m:den></m:f>"


def delim(inner: str) -> str:
    return f"<m:d><m:e>{inner}</m:e></m:d>"


@dataclass(frozen=True)
class Case:
    name: str
    omml: str
    expected: str  # reference LaTeX, compared with latex_compare_key
    in_notes: bool = False


CASES: tuple[Case, ...] = (
    Case("fraction", r("x=") + frac(r("a"), r("b")), r"x=\frac{a}{b}"),
    Case("subscript", sub(r("K"), r("p")), "{K}_{p}"),
    Case("superscript", sup(r("x"), r("2")), "{x}^{2}"),
    Case(
        "sum_with_limits",
        '<m:nary><m:naryPr><m:chr m:val="∑"/></m:naryPr>'
        f"<m:sub>{r('i=1')}</m:sub><m:sup>{r('n')}</m:sup><m:e>{sub(r('a'), r('i'))}</m:e></m:nary>",
        r"\sum_{i=1}^{n}{{a}_{i}}",
    ),
    Case(
        "integral",
        f"<m:nary><m:sub>{r('0')}</m:sub><m:sup>{r('T')}</m:sup><m:e>{r('u')}{delim(r('t'))}{r('dt')}</m:e></m:nary>",
        r"\int_{0}^{T}{u\left(t\right)dt}",
    ),
    Case(
        "radical", f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{r("2")}</m:e></m:rad>', r"\sqrt{2}"
    ),
    Case(
        "pseudo_inverse",
        r("p=") + sup(delim(sup(r("A"), r("T")) + r("A")), r("-1")) + sup(r("A"), r("T")) + sub(r("F"), r("ges")),
        r"p={\left({A}^{T}A\right)}^{-1}{A}^{T}{F}_{ges}",
    ),
    Case(
        "matrix",
        "<m:d><m:e><m:m>"
        f"<m:mr><m:e>{r('1')}</m:e><m:e>{r('0')}</m:e></m:mr><m:mr><m:e>{r('0')}</m:e><m:e>{r('1')}</m:e></m:mr>"
        "</m:m></m:e></m:d>",
        r"\left(\begin{matrix}1&0\\0&1\end{matrix}\right)",
    ),
    Case("function_in_run", r("f=min") + delim(r("x")), r"f=\min\left(x\right)"),
    Case("log_det_in_run", r("-ln") + delim(r("det") + delim(r("A"))), r"-\ln\left(\det\left(A\right)\right)"),
    Case("prose_in_math", r("{P}→{Term nach Zuweisungen}"), r"\{P\}\rightarrow\{\text{Term nach Zuweisungen}\}"),
    Case("accent_dot", '<m:acc><m:accPr><m:chr m:val="̇"/></m:accPr><m:e>' + r("q") + "</m:e></m:acc>", r"\dot{q}"),
    Case("greek_relation", sub(r("τ"), r("i")) + r("≤ω"), r"{\tau}_{i}\leq\omega"),
    Case("notes_equation", r("E=m") + sup(r("c"), r("2")), "E=m{c}^{2}", in_notes=True),
)


def _math_paragraph(case: Case, marker: str) -> etree._Element:
    xml = (
        f'<mc:AlternateContent xmlns:mc="{MC_NS}" xmlns:a="{A_NS}" xmlns:a14="{A14_NS}">'
        f'<mc:Choice xmlns:m="{M_NS}" Requires="a14"><a14:m><m:oMathPara xmlns:m="{M_NS}"><m:oMath>{case.omml}'
        "</m:oMath></m:oMathPara></a14:m></mc:Choice>"
        f"<mc:Fallback><a:r><a:t>{marker}</a:t></a:r></mc:Fallback></mc:AlternateContent>"
    )
    return etree.fromstring(xml.encode("utf-8"))


def build_deck(path: Path) -> list[tuple[Case, str]]:
    """Write the benchmark deck; return (case, fallback marker) in deck order."""
    prs = Presentation()
    out: list[tuple[Case, str]] = []
    for index, case in enumerate(CASES, start=1):
        marker = f"FALLBACK-{index:02d}"
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        box = slide.shapes.add_textbox(Emu(457200), Emu(457200), Emu(8_000_000), Emu(1_500_000))
        box.text_frame.text = f"Folie {index}: {case.name}"
        frame = slide.notes_slide.notes_text_frame if case.in_notes else box.text_frame
        paragraph = frame.add_paragraph()
        paragraph._p.append(_math_paragraph(case, marker))
        out.append((case, marker))
    prs.save(str(path))
    return out


def _rss_children_mb() -> float:
    peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return peak / (1024 * 1024) if sys.platform == "darwin" else peak / 1024


def option_a(deck: Path, cases: list[tuple[Case, str]]) -> dict[str, Any]:
    tracemalloc.start()
    t0 = time.perf_counter()
    found: list[tuple[str, str]] = []
    with zipfile.ZipFile(deck) as zf:
        names = sorted(
            (n for n in zf.namelist() if re.fullmatch(r"ppt/(slides/slide|notesSlides/notesSlide)\d+\.xml", n)),
            key=lambda n: (n.startswith("ppt/notes"), int(re.findall(r"\d+", n)[-1])),
        )
        for name in names:
            for eq in omml_xml_to_latex(zf.read(name)) or []:
                found.append((name, eq.latex))
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rows = []
    by_part: dict[str, list[str]] = {}
    for name, latex in found:
        by_part.setdefault(name, []).append(latex)
    correct = 0
    notes_found = [latex for name, latex in found if name.startswith("ppt/notesSlides/")]
    for index, (case, _) in enumerate(cases, start=1):
        # python-pptx numbers notes parts in creation order, independent of the slide number
        part = "ppt/notesSlides/" if case.in_notes else f"ppt/slides/slide{index}.xml"
        got = notes_found.pop(0) if case.in_notes and notes_found else (by_part.get(part) or [""])[0]
        ok = latex_compare_key(got) == latex_compare_key(case.expected)
        correct += ok
        rows.append({"case": case.name, "part": part.split("/")[-1], "latex": got, "ok": ok})
    return {
        "equations_found": len(found),
        "correct": correct,
        "seconds": elapsed,
        "peak_python_mb": peak / 1e6,
        "rows": rows,
    }


def option_b(deck: Path, cases: list[tuple[Case, str]], workdir: Path) -> dict[str, Any]:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice is None:
        return {"available": False}
    version = subprocess.run([soffice, "--version"], capture_output=True, text=True, check=False).stdout.strip()
    profile = (workdir / "lo-profile").as_uri()
    result: dict[str, Any] = {"available": True, "version": version}
    for fmt in ("odp", "pdf"):
        rss_before = _rss_children_mb()
        t0 = time.perf_counter()
        proc = subprocess.run(
            [soffice, "--headless", "--norestore", f"-env:UserInstallation={profile}", "--convert-to", fmt,
             "--outdir", str(workdir), str(deck)],
            capture_output=True, text=True, timeout=600, check=False,
        )  # fmt: skip
        result[f"{fmt}_seconds"] = time.perf_counter() - t0
        result[f"{fmt}_peak_rss_mb_upper_bound"] = max(rss_before, _rss_children_mb())
        result[f"{fmt}_returncode"] = proc.returncode
    odp = workdir / (deck.stem + ".odp")
    if odp.is_file():
        with zipfile.ZipFile(odp) as zf:
            content = zf.read("content.xml").decode("utf-8")
            objects = [n for n in zf.namelist() if re.fullmatch(r"Object \d+/content\.xml", n)]
            mathml = sum(b"<math" in zf.read(n) for n in objects)
        result["odp_mathml_objects"] = mathml
        result["odp_fallback_markers"] = sum(marker in content for _, marker in cases)
    pdf = workdir / (deck.stem + ".pdf")
    if pdf.is_file():
        import pypdf

        text = "\n".join(page.extract_text() or "" for page in pypdf.PdfReader(io.BytesIO(pdf.read_bytes())).pages)
        result["pdf_fallback_markers"] = sum(marker in text for _, marker in cases)
    return result


def option_p(deck: Path) -> dict[str, Any]:
    pandoc = shutil.which("pandoc")
    if pandoc is None:
        return {"available": False}
    version = subprocess.run([pandoc, "--version"], capture_output=True, text=True, check=False).stdout.splitlines()[0]
    formats = subprocess.run([pandoc, "--list-input-formats"], capture_output=True, text=True, check=False).stdout
    if "pptx" not in formats.split():
        return {"available": True, "version": version, "reads_pptx": False}
    proc = subprocess.run([pandoc, "-f", "pptx", "-t", "latex", str(deck)], capture_output=True, text=True, check=False)
    return {"available": True, "version": version, "reads_pptx": True, "math_spans": proc.stdout.count("$")}


def render(a: dict[str, Any], b: dict[str, Any], p: dict[str, Any], n: int) -> str:
    lines = [
        "# PPTX math extraction options: synthetic benchmark (T-P3-07, ADR-009 evidence)",
        "",
        f"Host: {platform.system()} {platform.machine()}, Python {platform.python_version()}. "
        f"Benchmark: {n} synthetic equations ({sum(c.in_notes for c in CASES)} in notes), each with a unique fallback "
        "marker. **No corpus content. Not a decision**: the ADR-009 PPTX path is the owner's choice.",
        "",
        "## Results",
        "",
        "| Option | Equations recovered as math | Structure kept | Notes | Time | Memory |",
        "|---|---|---|---|---|---|",
        f"| A native OMML->LaTeX | {a['correct']}/{n} correct ({a['equations_found']} found) | yes (LaTeX) | yes | "
        f"{a['seconds'] * 1000:.1f} ms | {a['peak_python_mb']:.1f} MB Python peak |",
    ]
    if b.get("available"):
        lines.append(
            f"| B LibreOffice PPTX->ODP | {b.get('odp_mathml_objects', 0)}/{n} MathML objects; "
            f"{b.get('odp_fallback_markers', 0)}/{n} fallback markers | "
            f"{'yes' if b.get('odp_mathml_objects') else 'no'} | n/a | {b['odp_seconds']:.1f} s (cold start) | "
            f"<= {b['odp_peak_rss_mb_upper_bound']:.0f} MB RSS |"
        )
        lines.append(
            f"| B LibreOffice PPTX->PDF | text only; {b.get('pdf_fallback_markers', 0)}/{n} fallback markers | no | "
            f"n/a | {b['pdf_seconds']:.1f} s | <= {b['pdf_peak_rss_mb_upper_bound']:.0f} MB RSS |"
        )
    else:
        lines.append("| B LibreOffice | not installed on this host | | | | |")
    if p.get("available") and not p.get("reads_pptx"):
        lines.append(f"| P pandoc | `{p['version']}` has no PPTX reader | no | no | | |")
    elif p.get("available"):
        lines.append(f"| P pandoc | {p['math_spans'] // 2} math spans | | | | |")
    lines.append("| C render + formula recognizer | not runnable: no local recognizer (SPIKE-MATH, T-P3-06) | | | | |")
    lines += ["", "## Option A per equation", "", "| case | part | LaTeX | matches reference |", "|---|---|---|---|"]
    lines += [f"| {row['case']} | {row['part']} | `{row['latex']}` | {row['ok']} |" for row in a["rows"]]
    if b.get("available"):
        lines += ["", f"LibreOffice: `{b['version']}`."]
    lines += [
        "",
        "## How to read this",
        "",
        "- A fallback marker in an output means that option read the picture/text fallback, not the equation. On real "
        "PowerPoint files the fallback is normally an image, so that path yields **no math**.",
        "- Memory for B is the peak RSS of all child processes so far (an upper bound); A is traced Python allocation.",
        "- Synthetic coverage is not corpus fidelity: the owner's review of the 50 real equations in "
        "`eval/reports/spike_omml_native.md` (re-run `tools/spike_omml.py --native-latex` on the Mac after converter "
        "changes) is the acceptance evidence.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=Path("eval/reports/spike_pptx_math_options.md"))
    parser.add_argument("--workdir", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        work = args.workdir or Path(tmp)
        work.mkdir(parents=True, exist_ok=True)
        deck = work / "pptx_math_benchmark.pptx"
        cases = build_deck(deck)
        a = option_a(deck, cases)
        b = option_b(deck, cases, work)
        p = option_p(deck)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render(a, b, p, len(cases)), encoding="utf-8")
    print(f"A {a['correct']}/{len(cases)}; B {b}; P {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
