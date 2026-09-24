"""Synthetic test fixture corpus (T-P1-13, docs/33 §3): no copyrighted corpus content, safe to commit.

:func:`generate` builds the tree under ``tests/fixtures/corpus/`` deterministically: every file is generated from
scratch by this script, and running it twice produces byte-identical output (every embedded timestamp, document
id and metadata field below is pinned; nothing depends on the wall clock or the machine it runs on). The generated
tree is committed to git, so ordinary test runs never need the tools below — only *regenerating* the fixtures does:

* ``pdflatex`` (a TeX Live/MiKTeX install) with ``amsmath`` — for ``skript.pdf``'s real, compiled equations.
* the dev dependencies ``python-docx``, ``python-pptx``, ``pillow`` and ``pypdf`` (fixture generation only; never
  imported by ``src/sbr``).

Covers (docs/33 §3, T-P1-13's acceptance list): a LaTeX-compiled PDF with equations; a DOCX and a PPTX each with a
real OMML equation; a scanned-image PDF (no text layer); a PDF with a real annotation; a zip with legacy CP437
(non-UTF-8) entry names; an exact-duplicate file; an umlaut path. "Moved files" is a scenario a P2 test builds
itself by relocating a generated file between two scans, not a second baked tree — the interesting case is the
move, not the corpus.

Regenerate: ``uv run python tests/fixtures/generate.py [--out DIR]`` (default: ``tests/fixtures/corpus``).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from lxml import etree
from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.util import Emu
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import FreeText
from pypdf.generic import ArrayObject, ByteStringObject

FIXED_DATETIME = datetime(2026, 1, 1, tzinfo=UTC)
FIXED_STRUCT_TIME = time.gmtime(int(FIXED_DATETIME.timestamp()))
FIXED_ZIP_DATE_TIME = (2026, 1, 1, 0, 0, 0)
FIXED_PDF_ID = ByteStringObject(b"\x00" * 16)
SOURCE_DATE_EPOCH = str(int(FIXED_DATETIME.timestamp()))

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def _normalize_ooxml_zip(path: Path) -> None:
    """Rewrite a .docx/.pptx's own zip container with a fixed per-entry timestamp (python-docx/pptx use "now")."""
    with zipfile.ZipFile(path) as src:
        entries = [(info, src.read(info.filename)) for info in src.infolist()]
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as dst:
        for info, data in entries:
            info.date_time = FIXED_ZIP_DATE_TIME
            dst.writestr(info, data)


class FixtureGenerationError(RuntimeError):
    """A required tool (pdflatex) is missing, or it failed to produce output."""


# -- shared: a small OMML equation (a real m:oMath tree, not plain text) ----------------------------------------


def _omml_math() -> etree._Element:
    """``ẋ = Ax + Bu`` as an ``m:oMath`` tree: an accent (the dot) over ``x``, then a plain run for the rest."""
    xml = (
        f'<m:oMath xmlns:m="{M_NS}">'
        '<m:acc><m:accPr><m:chr m:val="̇"/></m:accPr>'
        "<m:e><m:r><m:t>x</m:t></m:r></m:e></m:acc>"
        '<m:r><m:t xml:space="preserve"> = Ax + Bu</m:t></m:r>'
        "</m:oMath>"
    )
    return etree.fromstring(xml.encode("utf-8"))


# -- LaTeX-compiled PDF with equations ----------------------------------------------------------------------------

_LATEX_SOURCE = r"""
\documentclass{article}
\usepackage{amsmath}
\pagestyle{empty}
\pdftrailerid{}
\begin{document}
Synthetic fixture: state-space model.

\begin{equation}
  \dot{x} = Ax + Bu
\end{equation}

\begin{equation}
  y = Cx + Du
\end{equation}
\end{document}
""".strip()


def _build_latex_pdf(out: Path) -> None:
    """Compile a small LaTeX document with two real equations. Byte-deterministic via ``SOURCE_DATE_EPOCH``."""
    pdflatex = shutil.which("pdflatex")
    if pdflatex is None:
        raise FixtureGenerationError(
            "pdflatex not found on PATH; install a TeX Live/MiKTeX distribution with amsmath to regenerate "
            f"{out.name} (the checked-in file does not need it)"
        )
    work = out.parent / f".{out.stem}_texbuild"
    work.mkdir(parents=True, exist_ok=True)
    tex = work / "doc.tex"
    tex.write_text(_LATEX_SOURCE, encoding="utf-8")
    env = {"SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH, "PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        [pdflatex, "-interaction=nonstopmode", "-halt-on-error", "-output-directory", str(work), str(tex)],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise FixtureGenerationError(f"pdflatex failed for {out.name}:\n{result.stdout[-2000:]}")
    shutil.copyfile(work / "doc.pdf", out)
    shutil.rmtree(work)


# -- DOCX with a real OMML equation --------------------------------------------------------------------------------


def _build_docx(out: Path) -> None:
    doc = Document()
    doc.core_properties.created = FIXED_DATETIME
    doc.core_properties.modified = FIXED_DATETIME
    doc.core_properties.last_modified_by = ""
    doc.core_properties.revision = 1
    doc.add_heading("Übungsblatt: Zustandsraummodell", level=1)
    doc.add_paragraph("Synthetisches Testfixture (keine urheberrechtlich geschützten Inhalte).")

    math_para = OxmlElement("m:oMathPara")
    math_para.append(_omml_math())
    doc.element.body.append(math_para)
    # Word requires a trailing sectPr as the body's last child; python-docx keeps it there already, so move it back.
    sect_pr = doc.element.body.find(qn("w:sectPr"))
    if sect_pr is not None:
        doc.element.body.append(sect_pr)

    doc.save(str(out))
    _normalize_ooxml_zip(out)


# -- PPTX with a real OMML equation (Office Math via the a14 DrawingML extension) -----------------------------------


def _build_pptx(out: Path) -> None:
    prs = Presentation()
    prs.core_properties.created = FIXED_DATETIME
    prs.core_properties.modified = FIXED_DATETIME
    prs.core_properties.last_modified_by = ""
    prs.core_properties.revision = 1

    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout
    box = slide.shapes.add_textbox(Emu(457200), Emu(457200), Emu(8_000_000), Emu(1_500_000))
    tf = box.text_frame
    tf.text = "Synthetisches Testfixture: Zustandsraummodell"

    p = tf.add_paragraph()
    a_ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
    mc_ns = "http://schemas.openxmlformats.org/markup-compatibility/2006"
    a14_ns = "http://schemas.microsoft.com/office/drawing/2010/main"
    fallback_text = escape("ẋ = Ax + Bu")
    xml = (
        f'<mc:AlternateContent xmlns:mc="{mc_ns}" xmlns:a="{a_ns}" xmlns:a14="{a14_ns}">'
        f'<mc:Choice xmlns:m="{M_NS}" Requires="a14">'
        f"<a14:m>{etree.tostring(_omml_math(), encoding='unicode')}</a14:m>"
        "</mc:Choice>"
        f"<mc:Fallback><a:r><a:t>{fallback_text}</a:t></a:r></mc:Fallback>"
        "</mc:AlternateContent>"
    )
    p._p.append(etree.fromstring(xml.encode("utf-8")))

    prs.save(str(out))
    _normalize_ooxml_zip(out)


# -- scanned-image PDF (image only, no text layer) --------------------------------------------------------------


def _build_scanned_pdf(out: Path) -> None:
    im = Image.new("L", (1240, 1754), color=255)  # A4 at 150 DPI
    draw = ImageDraw.Draw(im)
    draw.rectangle([40, 40, 1200, 1714], outline=0, width=3)
    draw.text((80, 80), "Synthetisches Scan-Fixture (kein Text-Layer)", fill=0)
    draw.line([80, 200, 1160, 200], fill=0, width=2)
    im.save(out, "PDF", resolution=150.0, creationDate=FIXED_STRUCT_TIME, modDate=FIXED_STRUCT_TIME, title=out.stem)


# -- annotated PDF (a real PDF annotation object) ------------------------------------------------------------------


def _build_annotated_pdf(source: Path, out: Path) -> None:
    reader = PdfReader(source)
    writer = PdfWriter()
    writer.append(reader)
    writer.add_annotation(
        page_number=0,
        annotation=FreeText(
            text="Owner note: siehe Herleitung in der Vorlesung.",
            rect=(50, 700, 300, 750),
            font="Helvetica",
            font_size="10pt",
        ),
    )
    writer.add_metadata(
        {"/CreationDate": "D:20260101000000Z", "/ModDate": "D:20260101000000Z", "/Producer": "sbr-fixtures"}
    )
    writer._ID = ArrayObject([FIXED_PDF_ID, FIXED_PDF_ID])
    with out.open("wb") as f:
        writer.write(f)


# -- zip with legacy CP437 (non-UTF-8) entry names ------------------------------------------------------------------


class _Cp437ZipInfo(zipfile.ZipInfo):
    """Forces CP437 encoding without the UTF-8 flag, simulating a pre-UTF-8 (DOS-era) zip tool (docs/08 §6)."""

    def _encodeFilenameFlags(self) -> tuple[bytes, int]:  # noqa: N802 - overrides zipfile.ZipInfo's exact name
        return self.filename.encode("cp437"), self.flag_bits


def _build_archive(out: Path, duplicate_of: Path) -> None:
    with zipfile.ZipFile(out, "w") as zf:
        legacy = _Cp437ZipInfo("Übung\\Aufgabenblätter\\ÜBUNG3.TXT", date_time=FIXED_ZIP_DATE_TIME)
        legacy.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(legacy, b"Synthetisches Fixture: Aufgabenblatt 3.\n")

        plain = zipfile.ZipInfo("notes/readme.txt", date_time=FIXED_ZIP_DATE_TIME)
        plain.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(plain, b"Synthetic fixture archive; no copyrighted content.\n")

        dup = zipfile.ZipInfo("archiv/skript_duplikat.pdf", date_time=FIXED_ZIP_DATE_TIME)
        dup.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(dup, duplicate_of.read_bytes())


# -- orchestration --------------------------------------------------------------------------------------------------


def generate(root: Path) -> None:
    """Build the fixture corpus under ``root``, replacing anything already there."""
    if root.exists():
        shutil.rmtree(root)
    reg = root / "Regelungstechnik"
    uebung = reg / "Übung"  # "Übung": an umlaut path component, exercised throughout SourceFS tests
    formelsammlung = root / "Formelsammlung"
    for d in (reg, uebung, formelsammlung):
        d.mkdir(parents=True)

    skript = reg / "skript.pdf"
    _build_latex_pdf(skript)
    _build_docx(uebung / "uebung1.docx")
    _build_pptx(uebung / "folien.pptx")
    _build_scanned_pdf(uebung / "scan_seite1.pdf")
    _build_annotated_pdf(skript, uebung / "skript_annotiert.pdf")
    # An exact duplicate (ADR-031): same bytes, different path/folder, as the owner's own copies commonly are.
    shutil.copyfile(skript, formelsammlung / "skript_kopie.pdf")
    _build_archive(root / "archiv.zip", duplicate_of=skript)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "corpus")
    args = parser.parse_args()
    generate(args.out)
    print(f"generated fixture corpus at {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
