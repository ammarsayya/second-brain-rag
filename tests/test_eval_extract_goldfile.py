"""T-P3-04: gold-file loading via SourceFS (read-only)."""

from __future__ import annotations

from pathlib import Path

from sbr.config import config_from_mapping
from sbr.eval.extract.goldfile import load_gold_samples
from sbr.sourcefs import SourceFS


def test_load_gold_samples_parses_every_field(tmp_path: Path) -> None:
    root = tmp_path / "src_root"
    root.mkdir()
    prot = tmp_path / "quarantine"
    prot.mkdir()
    (root / "doc.pdf").write_bytes(b"%PDF-1.7\nfake content")

    config = config_from_mapping(
        {
            "roots": {
                "sources": [{"id": "fx", "path": str(root)}],
                "var": str(tmp_path / "var"),
                "curation": str(tmp_path / "curation"),
                "protected": [str(prot)],
            }
        }
    )
    source_fs = SourceFS(config)

    gold_file = tmp_path / "gold.yaml"
    gold_file.write_text(
        "samples:\n"
        "  - relpath: doc.pdf\n"
        "    root_id: fx\n"
        "    page: 2\n"
        "    gold:\n"
        "      blocks:\n"
        "        - {kind: heading, reading_order: 0, text: 'Kapitel 1'}\n"
        "        - {kind: paragraph, reading_order: 1, text: 'Text hier.'}\n"
        "      equations:\n"
        "        - {latex_normalized: 'x^2 + y^2', source_kind: latex_source}\n"
        "      tables:\n"
        "        - [['a', 'b'], ['c', 'd']]\n"
        "      figures:\n"
        "        - {bbox: [0, 0, 10, 10], caption: 'Bild 1', is_knowledge_bearing: true}\n",
        encoding="utf-8",
    )

    [(pdf_bytes, page, gold)] = load_gold_samples(source_fs, gold_file)
    assert pdf_bytes == b"%PDF-1.7\nfake content"
    assert page == 2
    assert gold.page == 2
    assert [b.kind for b in gold.blocks] == ["heading", "paragraph"]
    assert gold.equations[0].latex_normalized == "x^2 + y^2"
    assert gold.tables == ((("a", "b"), ("c", "d")),)
    assert gold.figures[0].caption == "Bild 1"
    assert gold.figures[0].is_knowledge_bearing is True


def test_load_gold_samples_handles_multiple_entries_and_defaults(tmp_path: Path) -> None:
    root = tmp_path / "src_root"
    root.mkdir()
    prot = tmp_path / "quarantine"
    prot.mkdir()
    (root / "a.pdf").write_bytes(b"A")
    (root / "b.pdf").write_bytes(b"B")

    config = config_from_mapping(
        {
            "roots": {
                "sources": [{"id": "fx", "path": str(root)}],
                "var": str(tmp_path / "var"),
                "curation": str(tmp_path / "curation"),
                "protected": [str(prot)],
            }
        }
    )
    source_fs = SourceFS(config)

    gold_file = tmp_path / "gold.yaml"
    gold_file.write_text(
        "samples:\n"
        "  - relpath: a.pdf\n"
        "    root_id: fx\n"
        "    page: 1\n"
        "    gold: {}\n"
        "  - relpath: b.pdf\n"
        "    root_id: fx\n"
        "    page: 1\n"
        "    gold: {}\n",
        encoding="utf-8",
    )

    samples = load_gold_samples(source_fs, gold_file)
    assert len(samples) == 2
    assert {s[0] for s in samples} == {b"A", b"B"}
    assert samples[0][2].blocks == ()
