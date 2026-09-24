"""T-P1-13: the synthetic fixture generator creates its tree deterministically, with the content it advertises."""

from __future__ import annotations

import time
import zipfile
from pathlib import Path

from docx import Document
from pptx import Presentation
from pypdf import PdfReader

from sbr.ids import hash_bytes
from tests.fixtures.generate import generate

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "corpus"


def _hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hash_bytes(p.read_bytes()) for p in sorted(root.rglob("*")) if p.is_file()}


def test_generation_is_byte_deterministic_across_two_runs(tmp_path: Path) -> None:
    """No embedded timestamp, document id or metadata field may depend on wall-clock time or run order."""
    out1, out2 = tmp_path / "run1", tmp_path / "run2"
    generate(out1)
    time.sleep(1.1)  # cross a real wall-clock second: catches any un-pinned "now()" timestamp
    generate(out2)

    h1, h2 = _hashes(out1), _hashes(out2)
    assert h1 == h2
    assert h1  # not vacuously empty


def test_generation_is_idempotent_when_rerun_into_the_same_directory(tmp_path: Path) -> None:
    out = tmp_path / "corpus"
    generate(out)
    before = _hashes(out)
    generate(out)
    assert _hashes(out) == before


def test_the_committed_fixture_corpus_matches_a_fresh_generation(tmp_path: Path) -> None:
    """The tree checked into git is exactly what the generator produces today (not stale)."""
    fresh = tmp_path / "fresh"
    generate(fresh)
    assert _hashes(fresh) == _hashes(FIXTURE_ROOT)


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
    generate(out)
    assert not stale.exists()
    assert (out / "Regelungstechnik" / "skript.pdf").exists()
