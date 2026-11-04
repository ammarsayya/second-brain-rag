"""T-P2-05 metadata-only exclusions, sensitivity, curation, CLI, and privacy-safe reporting."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from typer.testing import CliRunner

from sbr.cli.app import app
from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.registry.classify import classify_pending
from sbr.registry.hash import hash_pending
from sbr.registry.scan import scan_root
from sbr.registry.sensitivity import automatic_sensitivity, classify_sensitivity, local_processing_allowed
from sbr.schemas import BlobRecord
from sbr.schemas.registry import BlobStatus, Sensitivity


def _open(config: SbrConfig) -> RegistryDB:
    db = RegistryDB.open(config)
    db.migrate()
    return db


def _write_curation(config: SbrConfig, *, exclusions: str = "", overrides: str = "") -> None:
    root = Path(config.roots.curation)
    root.mkdir(parents=True, exist_ok=True)
    (root / "exclusions.yaml").write_text(f"exclusions:\n{exclusions}", encoding="utf-8")
    (root / "sensitivity_overrides.yaml").write_text(f"overrides:\n{overrides}", encoding="utf-8")


def _write_config(path: Path, config: SbrConfig) -> None:
    source = Path(config.roots.sources[0].path).as_posix()
    path.write_text(
        "[roots]\n"
        f"sources = [{{ id = 'fx', path = '{source}' }}]\n"
        f"var = '{Path(config.roots.var).as_posix()}'\n"
        f"curation = '{Path(config.roots.curation).as_posix()}'\n"
        f"protected = ['{Path(config.roots.protected[0]).as_posix()}']\n",
        encoding="utf-8",
    )


def _by_path(db: RegistryDB) -> dict[str, BlobRecord]:
    blobs = {blob.blob_id: blob for blob in db.repo(reg.BLOB).find()}
    return {
        observation.relpath: blobs[observation.blob_id]
        for observation in db.repo(reg.PATH_OBSERVATION).find()
        if observation.blob_id is not None
    }


def _run_pipeline(config: SbrConfig, db: RegistryDB) -> None:
    scan_root(config, db, "fx")
    hash_pending(config, db)
    classify_pending(config, db)


def test_known_name_rules_and_knoten_false_positive() -> None:
    expected = {
        "Labornoten_SS21.xlsx": Sensitivity.THIRD_PARTY_PERSONAL,
        "Ergebnisliste_Klausur.pdf": Sensitivity.THIRD_PARTY_PERSONAL,
        "Ergebnislisten_WS22.xlsx": Sensitivity.THIRD_PARTY_PERSONAL,
        "Vertrag_Praxisphase.pdf": Sensitivity.RESTRICTED,
        "Bewerbung_2025.pdf": Sensitivity.RESTRICTED,
        "Lebenslauf_Aktuell.pdf": Sensitivity.RESTRICTED,
        "Zeugnis_Bachelor.pdf": Sensitivity.RESTRICTED,
        "Ausweis_Kopie.pdf": Sensitivity.RESTRICTED,
        "Immatrikulation_Bescheinigung.pdf": Sensitivity.RESTRICTED,
        "Terminsladung_Amtsgericht.pdf": Sensitivity.RESTRICTED,
        "PKH-Beschluss.pdf": Sensitivity.RESTRICTED,
        "Antrag_Prozesskostenhilfe.pdf": Sensitivity.RESTRICTED,
        "Gerichtsbeschluss_2020.pdf": Sensitivity.RESTRICTED,
        "Schreiben Aktenzeichen 12-3.pdf": Sensitivity.RESTRICTED,
        "Knotenpunkt_Analyse.pdf": Sensitivity.NORMAL,
        # Physics "Ladung" (electric charge) and words merely containing "pkh" must stay normal.
        "Zusaetzliche Bilder Aufladung.pdf": Sensitivity.NORMAL,
        "Ladungstraeger_Halbleiter.pdf": Sensitivity.NORMAL,
        "Schupkhaus.pdf": Sensitivity.NORMAL,
    }
    assert {name: automatic_sensitivity(name).sensitivity for name in expected} == expected
    assert automatic_sensitivity("Labornoten_SS21.xlsx").rule == "Noten"
    assert automatic_sensitivity("PKH-Beschluss.pdf").rule == "Gerichtsdokument"


def test_local_processing_gate_blocks_restricted_and_third_party_and_rechecks_paths() -> None:
    ok = local_processing_allowed
    assert ok(BlobStatus.ACTIVE, Sensitivity.NORMAL, ["Mechanik\\Skript.pdf"])
    assert ok(BlobStatus.ACTIVE, Sensitivity.PERSONAL, ["Mechanik\\Skript.pdf"])
    assert not ok(BlobStatus.ACTIVE, Sensitivity.RESTRICTED, ["Mechanik\\Skript.pdf"])
    assert not ok(BlobStatus.ACTIVE, Sensitivity.THIRD_PARTY_PERSONAL, ["Mechanik\\Skript.pdf"])
    assert not ok(BlobStatus.EXCLUDED, Sensitivity.NORMAL, ["Mechanik\\Skript.pdf"])
    # A registry classified under older rules still says "normal"; the current path rules must still block it.
    assert not ok(BlobStatus.ACTIVE, Sensitivity.NORMAL, ["lernen\\Terminsladung_und_PKH-Beschluss.pdf"])


def test_stage_classifies_known_examples_and_default_exclusions(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    root = tmp_path / "src_root"
    root.mkdir()
    samples = {
        "Labornoten_SS21.xlsx": b"grades",
        "Ergebnisliste_Klausur.pdf": b"%PDF-1.7\nresults",
        "Vertrag_Praxisphase.pdf": b"%PDF-1.7\ncontract",
        "Knotenpunkt_Analyse.pdf": b"%PDF-1.7\ngraph",
        "empty.txt": b"",
        "solver.wbjn": b"tool",
        "program.exe": b"binary",
        "reference.html": b"help",
        "encrypted.pdf": b"%PDF-1.7\n<< /Encrypt 2 0 R >>\n%%EOF",
        "figure.png": b"\x89PNG\r\n\x1a\nimage",
    }
    for name, content in samples.items():
        (root / name).write_bytes(content)
    config = make_config()
    _write_curation(config)

    with _open(config) as db:
        _run_pipeline(config, db)
        result = classify_sensitivity(config, db)
        by_path = _by_path(db)

    assert result.considered == len(samples)
    assert by_path["Labornoten_SS21.xlsx"].sensitivity is Sensitivity.THIRD_PARTY_PERSONAL
    assert by_path["Ergebnisliste_Klausur.pdf"].sensitivity is Sensitivity.THIRD_PARTY_PERSONAL
    assert by_path["Vertrag_Praxisphase.pdf"].sensitivity is Sensitivity.RESTRICTED
    assert by_path["Knotenpunkt_Analyse.pdf"].sensitivity is Sensitivity.NORMAL
    for name in ("empty.txt", "solver.wbjn", "program.exe", "reference.html", "encrypted.pdf"):
        assert by_path[name].status is BlobStatus.EXCLUDED
    assert by_path["figure.png"].status is BlobStatus.ACTIVE


def test_owner_overrides_take_precedence_and_exclusions_only_add(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    root = tmp_path / "src_root"
    root.mkdir()
    (root / "Vertrag_Privat.pdf").write_bytes(b"%PDF-1.7\ncontract")
    (root / "profile.txt").write_bytes(b"owner profile")
    (root / "manual.txt").write_bytes(b"exclude me")
    config = make_config()

    with _open(config) as db:
        _write_curation(config)
        _run_pipeline(config, db)
        before = _by_path(db)
        profile_blob = before["profile.txt"].blob_id
        _write_curation(
            config,
            exclusions="  - scope: path\n    pattern: '**/manual.txt'\n    reason: owner choice\n",
            overrides=(
                "  - scope: path\n    pattern: '**/Vertrag_*.pdf'\n    sensitivity: normal\n"
                f"  - scope: blob\n    pattern: '{profile_blob}'\n    sensitivity: personal\n"
            ),
        )
        classify_sensitivity(config, db)
        by_path = _by_path(db)

    assert by_path["Vertrag_Privat.pdf"].sensitivity is Sensitivity.NORMAL
    assert by_path["profile.txt"].sensitivity is Sensitivity.PERSONAL
    assert by_path["manual.txt"].status is BlobStatus.EXCLUDED


def test_cli_and_report_hide_restricted_paths_by_default_and_require_opt_in(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    root = tmp_path / "src_root"
    root.mkdir()
    restricted_name = "Vertrag_Praxisphase.pdf"
    third_party_name = "Labornoten_SS21.xlsx"
    (root / restricted_name).write_bytes(b"%PDF-1.7\ncontract")
    (root / third_party_name).write_bytes(b"grades")
    config = make_config()
    _write_curation(config)
    config_file = tmp_path / "sbr.toml"
    _write_config(config_file, config)

    with _open(config) as db:
        _run_pipeline(config, db)

    cli = CliRunner().invoke(app, ["sensitivity", "--config", str(config_file)])
    assert cli.exit_code == 0, cli.output
    payload = json.loads(cli.output)
    assert payload["sensitivity_counts"]["restricted"] == 1
    assert restricted_name not in cli.output

    default_report = tmp_path / "sensitivity-default.md"
    default_run = subprocess.run(
        [
            sys.executable,
            "tools/validate_sensitivity.py",
            "--config",
            str(config_file),
            "--output",
            str(default_report),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert default_run.returncode == 0, default_run.stderr
    default_text = default_report.read_text(encoding="utf-8")
    assert "- Vertrag: 1" in default_text
    assert restricted_name not in default_text
    assert third_party_name in default_text
    assert "sensitive RESTRICTED paths are exposed" not in default_text

    opt_in_report = tmp_path / "sensitivity-opt-in.md"
    opt_in_run = subprocess.run(
        [
            sys.executable,
            "tools/validate_sensitivity.py",
            "--config",
            str(config_file),
            "--output",
            str(opt_in_report),
            "--show-restricted-paths",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert opt_in_run.returncode == 0, opt_in_run.stderr
    opt_in_text = opt_in_report.read_text(encoding="utf-8")
    assert "WARNING: sensitive RESTRICTED paths are exposed" in opt_in_text
    assert restricted_name in opt_in_text
    assert "WARNING: sensitive RESTRICTED paths are exposed" in opt_in_run.stdout
