"""T-P1-13: the synthetic fixture generator creates its tree deterministically, with the content it advertises."""

from __future__ import annotations

import time
import zipfile
from pathlib import Path

import pytest
from docx import Document
from pptx import Presentation
from pypdf import PdfReader

from sbr.ids import hash_bytes
from tests.fixtures.generate import FixtureGenerationError, build_latex_pdf, generate

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "corpus"
COMMITTED_SKRIPT = FIXTURE_ROOT / "Regelungstechnik" / "skript.pdf"

# Generator tests reuse the committed, genuinely pdflatex-compiled skript.pdf (``latex_pdf=``) so they verify every
# Python-built fixture without a TeX install. LaTeX compilation itself is covered by the ``pdflatex`` tests below.


def _hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hash_bytes(p.read_bytes()) for p in sorted(root.rglob("*")) if p.is_file()}


def test_generation_is_byte_deterministic_across_two_runs(tmp_path: Path) -> None:
    """No embedded timestamp, document id or metadata field may depend on wall-clock time or run order."""
    out1, out2 = tmp_path / "run1", tmp_path / "run2"
    generate(out1, latex_pdf=COMMITTED_SKRIPT)
    time.sleep(2.1)  # cross a real ZIP/DOS timestamp tick (2 s resolution): catches any un-pinned "now()"
    generate(out2, latex_pdf=COMMITTED_SKRIPT)

    h1, h2 = _hashes(out1), _hashes(out2)
    assert h1 == h2
    assert h1  # not vacuously empty


def test_generation_is_idempotent_when_rerun_into_the_same_directory(tmp_path: Path) -> None:
    out = tmp_path / "corpus"
    generate(out, latex_pdf=COMMITTED_SKRIPT)
    before = _hashes(out)
    generate(out, latex_pdf=COMMITTED_SKRIPT)
    assert _hashes(out) == before


def test_the_committed_fixture_corpus_matches_a_fresh_generation(tmp_path: Path) -> None:
    """The tree checked into git is exactly what the generator produces today (not stale).

    Every file except skript.pdf itself is rebuilt from scratch, including the three derived from it (the annotated
    PDF, the duplicate copy, the zip embedding it); skript.pdf's own staleness is the ``pdflatex`` test's job.
    """
    fresh = tmp_path / "fresh"
    generate(fresh, latex_pdf=COMMITTED_SKRIPT)
    assert _hashes(fresh) == _hashes(FIXTURE_ROOT)
    assert len(_hashes(fresh)) == 7


# -- content sanity: each advertised scenario is really present ------------------------------------------------


def test_latex_pdf_has_real_compiled_equations() -> None:
    reader = PdfReader(FIXTURE_ROOT / "Regelungstechnik" / "skript.pdf")
    text = reader.pages[0].extract_text()
    assert "Ax" in text and "Bu" in text


def test_docx_carries_a_real_omml_equation() -> None:
    path = FIXTURE_ROOT / "Regelungstechnik" / "Übung" / "uebung1.docx"
    Document(str(path))  # opens without raising: valid OOXML
    with zipfile.ZipFile(path) as zf:
        assert "m:oMath" in zf.read("word/document.xml").decode("utf-8")


def test_pptx_carries_a_real_omml_equation() -> None:
    path = FIXTURE_ROOT / "Regelungstechnik" / "Übung" / "folien.pptx"
    prs = Presentation(str(path))  # opens without raising: valid OOXML
    assert len(prs.slides) == 1
    with zipfile.ZipFile(path) as zf:
        assert "a14:m" in zf.read("ppt/slides/slide1.xml").decode("utf-8")


def test_scanned_pdf_has_no_text_layer() -> None:
    reader = PdfReader(FIXTURE_ROOT / "Regelungstechnik" / "Übung" / "scan_seite1.pdf")
    assert reader.pages[0].extract_text().strip() == ""


def test_annotated_pdf_carries_a_real_annotation() -> None:
    reader = PdfReader(FIXTURE_ROOT / "Regelungstechnik" / "Übung" / "skript_annotiert.pdf")
    annots = reader.pages[0].get("/Annots")
    assert annots is not None and len(annots) == 1


def test_archive_has_a_legacy_cp437_entry_name_and_an_embedded_duplicate() -> None:
    with zipfile.ZipFile(FIXTURE_ROOT / "archiv.zip") as zf:
        names = zf.namelist()
        infos = {i.filename: i for i in zf.infolist()}
        umlaut_names = [n for n in names if "Ü" in n or "ä" in n]
        assert umlaut_names, "expected at least one umlaut-bearing legacy entry name"
        assert all(infos[n].flag_bits & 0x800 == 0 for n in umlaut_names)  # no UTF-8 flag: genuine CP437

        dup_bytes = zf.read("archiv/skript_duplikat.pdf")
    original = (FIXTURE_ROOT / "Regelungstechnik" / "skript.pdf").read_bytes()
    assert hash_bytes(dup_bytes) == hash_bytes(original)


def test_the_formelsammlung_copy_is_an_exact_duplicate_of_the_original() -> None:
    a = (FIXTURE_ROOT / "Regelungstechnik" / "skript.pdf").read_bytes()
    b = (FIXTURE_ROOT / "Formelsammlung" / "skript_kopie.pdf").read_bytes()
    assert hash_bytes(a) == hash_bytes(b)


def test_an_umlaut_path_component_is_present() -> None:
    assert (FIXTURE_ROOT / "Regelungstechnik" / "Übung").is_dir()


def test_generate_replaces_a_pre_existing_directory(tmp_path: Path) -> None:
    out = tmp_path / "corpus"
    out.mkdir()
    stale = out / "stale.txt"
    stale.write_text("leftover from a previous run", encoding="utf-8")
    generate(out, latex_pdf=COMMITTED_SKRIPT)
    assert not stale.exists()
    assert (out / "Regelungstechnik" / "skript.pdf").exists()


def test_regenerating_in_place_can_reuse_the_skript_pdf_inside_the_target(tmp_path: Path) -> None:
    """``--reuse-latex-pdf tests/fixtures/corpus/Regelungstechnik/skript.pdf`` must survive the target being cleared."""
    out = tmp_path / "corpus"
    generate(out, latex_pdf=COMMITTED_SKRIPT)
    before = _hashes(out)
    generate(out, latex_pdf=out / "Regelungstechnik" / "skript.pdf")
    assert _hashes(out) == before


def test_reusing_a_missing_or_non_pdf_latex_file_fails_loudly(tmp_path: Path) -> None:
    out = tmp_path / "corpus"
    with pytest.raises(FixtureGenerationError, match="cannot read"):
        generate(out, latex_pdf=tmp_path / "missing.pdf")
    not_pdf = tmp_path / "not.pdf"
    not_pdf.write_bytes(b"plain text")
    with pytest.raises(FixtureGenerationError, match="not a PDF"):
        generate(out, latex_pdf=not_pdf)
    assert not out.exists()  # validated before anything was cleared or written


# -- integration: real LaTeX compilation (needs pdflatex; see the ``pdflatex`` marker in pyproject.toml) -----------


def _pdftex_banner(path: Path) -> str:
    return str((PdfReader(path).metadata or {}).get("/PTEX.Fullbanner", ""))


@pytest.mark.pdflatex
def test_pdflatex_compilation_is_byte_deterministic_and_has_real_equations(tmp_path: Path) -> None:
    first, second = tmp_path / "a" / "skript.pdf", tmp_path / "b" / "skript.pdf"
    first.parent.mkdir()
    second.parent.mkdir()
    build_latex_pdf(first)
    time.sleep(1.1)  # SOURCE_DATE_EPOCH and \pdftrailerid{} must pin every timestamp and the trailer id
    build_latex_pdf(second)
    assert first.read_bytes() == second.read_bytes()
    text = PdfReader(first).pages[0].extract_text()
    assert "Ax" in text and "Bu" in text and "Cx" in text


@pytest.mark.pdflatex
def test_full_generation_with_pdflatex_reproduces_the_committed_corpus(tmp_path: Path) -> None:
    """End-to-end regeneration. Byte equality of skript.pdf (and the files embedding it) is only defined for the
    pdfTeX build that compiled the committed file; with any other build the test says so instead of passing."""
    fresh = tmp_path / "fresh"
    generate(fresh)
    fresh_skript = fresh / "Regelungstechnik" / "skript.pdf"
    assert "Ax" in PdfReader(fresh_skript).pages[0].extract_text()
    committed_banner, fresh_banner = _pdftex_banner(COMMITTED_SKRIPT), _pdftex_banner(fresh_skript)
    if fresh_banner != committed_banner:
        pytest.skip(f"toolchain differs: committed skript.pdf by {committed_banner!r}, this host has {fresh_banner!r}")
    assert _hashes(fresh) == _hashes(FIXTURE_ROOT)
