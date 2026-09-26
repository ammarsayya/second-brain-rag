"""T-P3-04 acceptance criterion: 'Harness runs on a dummy extractor and produces a report' via the CLI."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from sbr.cli.app import app

FIXTURE_PDF = Path(__file__).parent / "fixtures" / "corpus" / "Regelungstechnik" / "skript.pdf"


def test_eval_extract_cli_writes_a_jsonl_report(tmp_path: Path) -> None:
    root = tmp_path / "src_root"
    root.mkdir()
    prot = tmp_path / "quarantine"
    prot.mkdir()
    (root / "skript.pdf").write_bytes(FIXTURE_PDF.read_bytes())

    config_file = tmp_path / "eval.toml"
    config_file.write_text(
        "[roots]\n"
        f"sources = [{{ id = 'fx', path = '{root.as_posix()}' }}]\n"
        f"var = '{(tmp_path / 'var').as_posix()}'\n"
        f"curation = '{(tmp_path / 'curation').as_posix()}'\n"
        f"protected = ['{prot.as_posix()}']\n",
        encoding="utf-8",
    )

    gold_file = tmp_path / "gold.yaml"
    gold_file.write_text(
        "samples:\n"
        "  - relpath: skript.pdf\n"
        "    root_id: fx\n"
        "    page: 1\n"
        "    gold:\n"
        "      blocks: []\n"
        "      equations: []\n"
        "      tables: []\n"
        "      figures: []\n",
        encoding="utf-8",
    )

    output = tmp_path / "harness.jsonl"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "eval",
            "extract",
            "--config",
            str(config_file),
            "--gold",
            str(gold_file),
            "--extractor",
            "dummy_text_layer",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    assert '"pages_scored": 1' in result.output

    lines = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert lines[0]["type"] == "page"
    assert lines[-1]["type"] == "summary"
    assert lines[-1]["extractor_name"] == "dummy_text_layer"


def test_eval_extract_cli_rejects_an_unknown_extractor(tmp_path: Path) -> None:
    root = tmp_path / "src_root"
    root.mkdir()
    prot = tmp_path / "quarantine"
    prot.mkdir()
    config_file = tmp_path / "eval.toml"
    config_file.write_text(
        "[roots]\n"
        f"sources = [{{ id = 'fx', path = '{root.as_posix()}' }}]\n"
        f"var = '{(tmp_path / 'var').as_posix()}'\n"
        f"curation = '{(tmp_path / 'curation').as_posix()}'\n"
        f"protected = ['{prot.as_posix()}']\n",
        encoding="utf-8",
    )
    gold_file = tmp_path / "gold.yaml"
    gold_file.write_text("samples: []\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["eval", "extract", "--config", str(config_file), "--gold", str(gold_file), "--extractor", "nonexistent"],
    )
    assert result.exit_code != 0
