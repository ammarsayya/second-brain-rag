"""T-P3-07 follow-up: tools/spike_omml.py native-OMML inventory (no pandoc needed)."""

from __future__ import annotations

import argparse
import io
import zipfile
from collections.abc import Callable
from pathlib import Path

from tools import spike_omml

from sbr.config import SbrConfig
from sbr.db.registry import RegistryDB
from sbr.registry.classify import classify_pending
from sbr.registry.dedup import select_canonical_paths
from sbr.registry.hash import hash_pending
from sbr.registry.scan import scan_root

FIXTURES = Path(__file__).parent / "fixtures" / "corpus" / "Regelungstechnik" / "Übung"


def test_part_kind_classifies_content_parts_and_ignores_the_rest() -> None:
    assert spike_omml.part_kind("ppt/slides/slide12.xml") == "pptx_slide"
    assert spike_omml.part_kind("ppt/notesSlides/notesSlide1.xml") == "pptx_notes"
    assert spike_omml.part_kind("ppt/slideMasters/slideMaster1.xml") == "pptx_layout_or_master"
    assert spike_omml.part_kind("word/document.xml") == "docx_body"
    assert spike_omml.part_kind("word/footnotes.xml") == "other_part"
    assert spike_omml.part_kind("ppt/slides/_rels/slide1.xml.rels") is None
    assert spike_omml.part_kind("[Content_Types].xml") is None
    assert spike_omml.part_kind("docProps/core.xml") is None


def test_inventory_counts_the_fixture_pptx_and_docx_equations() -> None:
    pptx = spike_omml.inventory_office_file((FIXTURES / "folien.pptx").read_bytes())
    assert pptx["total"] == 1
    assert pptx["parts"]["pptx_slide"] == {"total": 1, "display": 0}
    assert (pptx["slides_with_omml"], pptx["slides"], pptx["unreadable_parts"]) == (1, 1, 0)

    docx = spike_omml.inventory_office_file((FIXTURES / "uebung1.docx").read_bytes())
    assert docx["total"] >= 1
    assert docx["parts"]["docx_body"]["display"] >= 1  # the fixture's body-level m:oMathPara (T-P1-13)


def test_inventory_reports_bad_zips_and_unparseable_parts_instead_of_zero() -> None:
    assert spike_omml.inventory_office_file(b"not a zip")["error"] == "BadZipFile"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", "<p:sld")
    broken = spike_omml.inventory_office_file(buffer.getvalue())
    assert (broken["unreadable_parts"], broken["slides"], broken["total"]) == (1, 1, 0)


def test_pptx_inventory_end_to_end_over_a_registry(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    config = make_config()
    root = Path(config.roots.sources[0].path)
    for name in ("folien.pptx", "uebung1.docx"):
        (root / name).write_bytes((FIXTURES / name).read_bytes())
    config_file = tmp_path / "omml.toml"
    config_file.write_text(
        "[roots]\n"
        f"sources = [{{ id = 'fx', path = '{root.as_posix()}' }}]\n"
        f"var = '{Path(config.roots.var).as_posix()}'\n"
        f"curation = '{Path(config.roots.curation).as_posix()}'\n"
        f"protected = ['{Path(config.roots.protected[0]).as_posix()}']\n",
        encoding="utf-8",
    )
    curation_dir = Path(config.roots.curation)
    curation_dir.mkdir(parents=True, exist_ok=True)
    (curation_dir / "canonical_path_overrides.yaml").write_text("overrides: []\n", encoding="utf-8")
    db = RegistryDB.open(config)
    db.migrate()
    scan_root(config, db, "fx")
    hash_pending(config, db)
    classify_pending(config, db)
    select_canonical_paths(config, db)
    db.close()

    output = tmp_path / "inventory.md"
    assert spike_omml._pptx_inventory(argparse.Namespace(config=config_file, output=output)) == 0

    report = output.read_text(encoding="utf-8")
    assert "- files that could not be read from the source: 0" in report
    assert "## PPTX" in report and "- native OMML equations: 1 - pptx_slide=1 (0 display)" in report
    assert "- slides carrying native OMML: 1" in report
    assert "| pptx | folien.pptx | 1 | 0 | 1 / 1 | False |" in report
    assert "| docx | uebung1.docx |" in report
