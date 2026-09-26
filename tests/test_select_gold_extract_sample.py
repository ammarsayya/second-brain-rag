"""T-P3-01: smoke test for tools/select_gold_extract_sample.py against a small synthetic real registry."""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from collections.abc import Callable
from pathlib import Path

from ruamel.yaml import YAML

from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.registry.classify import classify_pending
from sbr.registry.dedup import select_canonical_paths
from sbr.registry.genre import classify_genres
from sbr.registry.hash import hash_pending
from sbr.registry.scan import scan_root

_OMML_DOCUMENT_XML = (
    b"<?xml version='1.0'?><w:document xmlns:w='w' xmlns:m='m'>"
    b"<w:body><w:p><m:oMath><m:r>x=1</m:r></m:oMath></w:p></w:body></w:document>"
)
_PLAIN_SLIDE_XML = b"<?xml version='1.0'?><p:sld xmlns:p='p'><p:cSld><p:spTree/></p:cSld></p:sld>"


def _make_docx_with_omml(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", _OMML_DOCUMENT_XML)


def _make_pptx_without_omml(path: Path, slides: int) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        for i in range(1, slides + 1):
            zf.writestr(f"ppt/slides/slide{i}.xml", _PLAIN_SLIDE_XML)


def _empty_curation_files(config: SbrConfig) -> None:
    curation_dir = Path(config.roots.curation)
    curation_dir.mkdir(parents=True, exist_ok=True)
    (curation_dir / "canonical_path_overrides.yaml").write_text("overrides: []\n", encoding="utf-8")


def test_selects_a_stratified_sample_across_pdf_and_office_formats(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    fixture_pdf = Path(__file__).parent / "fixtures" / "corpus" / "Regelungstechnik" / "skript.pdf"
    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Statik").mkdir()
    (root / "Statik" / "Klausur_SS2019.pdf").write_bytes(fixture_pdf.read_bytes())
    _make_docx_with_omml(root / "thesis.docx")
    _make_pptx_without_omml(root / "slides.pptx", slides=3)
    _empty_curation_files(config)

    db = RegistryDB.open(config)
    db.migrate()
    scan_root(config, db, "fx")
    hash_pending(config, db)
    classify_pending(config, db)
    select_canonical_paths(config, db)
    classify_genres(config, db)
    pdf_blob_id = next(o.blob_id for o in db.repo(reg.PATH_OBSERVATION).find() if o.relpath.endswith(".pdf"))
    db.close()

    page_census = tmp_path / "pages.jsonl"
    page_census.write_text(
        json.dumps({"blob_id": pdf_blob_id, "relpath": "Statik/Klausur_SS2019.pdf", "page_count": 3}) + "\n"
    )

    config_file = tmp_path / "gold.toml"
    config_file.write_text(
        "[roots]\n"
        f"sources = [{{ id = 'fx', path = '{root.as_posix()}' }}]\n"
        f"var = '{Path(config.roots.var).as_posix()}'\n"
        f"curation = '{Path(config.roots.curation).as_posix()}'\n"
        f"protected = ['{Path(config.roots.protected[0]).as_posix()}']\n",
        encoding="utf-8",
    )

    output = tmp_path / "extract_sample.yaml"
    completed = subprocess.run(
        [
            sys.executable,
            "tools/select_gold_extract_sample.py",
            "--config",
            str(config_file),
            "--output",
            str(output),
            "--page-census",
            str(page_census),
            "--target-pages",
            "10",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr

    yaml = YAML(typ="safe")
    doc = yaml.load(output.read_text(encoding="utf-8"))
    assert doc["descriptors_considered"] == 3
    formats = {entry["relpath"].rsplit(".", 1)[-1] for entry in doc["sample"]}
    assert formats == {"pdf", "docx", "pptx"}
    omml_entry = next(e for e in doc["sample"] if e["relpath"].endswith("thesis.docx"))
    assert omml_entry["bucket"] == "office_with_omml"
