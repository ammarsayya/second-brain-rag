"""T-P3-08 follow-up: tools/spike_ocr.py candidate discovery, raw-path access and the orientation census.

Tesseract itself is replaced by canned real outputs, so these tests run (rather than skip) on machines without it.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pypdf
import pytest
from tools import spike_ocr

from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.registry.classify import classify_pending
from sbr.registry.dedup import select_canonical_paths
from sbr.registry.hash import hash_pending
from sbr.registry.scan import scan_root

FIXTURES = Path(__file__).parent / "fixtures" / "corpus" / "Regelungstechnik"
OSD_UPSIDE_DOWN = (
    "Page number: 0\nOrientation in degrees: 180\nRotate: 180\nOrientation confidence: 17.32\n"
    "Script: Latin\nScript confidence: 28.10\n"
)
TSV_HEADER = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"


def _registry_with(make_config: Callable[..., SbrConfig], tmp_path: Path, files: dict[str, Path]) -> Path:
    """Build a migrated, hashed, classified registry over ``files`` and return a config file plus page census."""
    config = make_config()
    root = Path(config.roots.sources[0].path)
    for name, fixture in files.items():
        (root / name).write_bytes(fixture.read_bytes())
    config_file = tmp_path / "spike.toml"
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
    census_lines = []
    for blob in db.repo(reg.BLOB).find():
        obs = next(o for o in db.repo(reg.PATH_OBSERVATION).find() if o.obs_id == blob.canonical_obs_id)
        pages = len(pypdf.PdfReader(root / obs.relpath_raw).pages)
        census_lines.append(json.dumps({"blob_id": blob.blob_id, "page_count": pages}))
    db.close()
    (tmp_path / "census.jsonl").write_text("\n".join(census_lines) + "\n", encoding="utf-8")
    return config_file


def test_discovery_finds_only_the_scanned_page_and_keeps_the_raw_path(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    config_file = _registry_with(
        make_config,
        tmp_path,
        {"scan_seite1.pdf": FIXTURES / "Übung" / "scan_seite1.pdf", "skript.pdf": FIXTURES / "skript.pdf"},
    )
    source_fs, candidates = spike_ocr._find_scanned_candidates(config_file, tmp_path / "census.jsonl")

    [(_, root_id, relpath_raw, relpath, page)] = candidates
    assert (root_id, relpath_raw, relpath, page) == ("fx", "scan_seite1.pdf", "scan_seite1.pdf", 1)
    image = spike_ocr._first_page_image(source_fs, root_id, relpath_raw, page)
    assert image is not None and len(image) > 0


def test_discovery_never_opens_a_restricted_name_even_if_the_registry_says_normal(
    make_config: Callable[..., SbrConfig], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The sensitivity stage is not run here, so the registry still says "normal" (as the t3 registry, which was
    # classified under rules version 1, does). The gate must re-apply the current path rules.
    scan = FIXTURES / "Übung" / "scan_seite1.pdf"
    distinct = tmp_path / "distinct_scan.pdf"  # different bytes -> its own blob, still a scanned page
    distinct.write_bytes(scan.read_bytes() + b"\n%distinct\n")
    config_file = _registry_with(
        make_config,
        tmp_path,
        {"scan_seite1.pdf": scan, "Terminsladung_und_PKH-Beschluss.pdf": distinct},
    )
    _, candidates = spike_ocr._find_scanned_candidates(config_file, tmp_path / "census.jsonl")

    assert [c[3] for c in candidates] == ["scan_seite1.pdf"]
    err = capsys.readouterr().err
    assert "sensitivity gate: 1 blob(s) not opened" in err
    assert "PKH" not in err


def _fake_tesseract(calls: list[list[str]]) -> Callable[..., subprocess.CompletedProcess[str]]:
    def _run(cmd: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if "--psm" in cmd and cmd[cmd.index("--psm") + 1] == "0":
            return subprocess.CompletedProcess(cmd, 0, OSD_UPSIDE_DOWN, "")
        psm = cmd[cmd.index("--psm") + 1]
        conf = "20.0" if psm == "3" else "88.0"  # garbage upside-down text vs OSD-corrected text
        return subprocess.CompletedProcess(cmd, 0, TSV_HEADER + f"5\t1\t1\t1\t1\t1\t0\t0\t9\t9\t{conf}\tRegler\n", "")

    return _run


def test_orientation_census_compares_psm3_and_psm1_on_rotated_pages(
    make_config: Callable[..., SbrConfig], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file = _registry_with(make_config, tmp_path, {"scan_seite1.pdf": FIXTURES / "Übung" / "scan_seite1.pdf"})
    calls: list[list[str]] = []
    monkeypatch.setattr(spike_ocr.subprocess, "run", _fake_tesseract(calls))
    output = tmp_path / "orientation.md"
    args = argparse.Namespace(
        config=config_file,
        page_census=tmp_path / "census.jsonl",
        output=output,
        seed=1,
        control_size=5,
        min_orientation_confidence=2.0,
    )

    assert spike_ocr._orientation_census(args) == 0

    psm_modes = [cmd[cmd.index("--psm") + 1] for cmd in calls]
    assert psm_modes == ["0", "3", "1"]
    assert all("deu" in cmd for cmd in calls if "tsv" in cmd)
    report = output.read_text(encoding="utf-8")
    assert "OSD rotate distribution, any confidence: 0=0, 90=0, 180=1, 270=0" in report
    assert "mean word-confidence change psm1 - psm3, rotated pages: +68.0 over 1 pages" in report
    assert "| scan_seite1.pdf | 1 | 180 | 17.32 | 1 | 20.0 | 1 | 88.0 | 68.0 |  |" in report
    assert "Evidence, not a decision." in report


def test_orientation_census_reports_declined_pages_as_undetected(
    make_config: Callable[..., SbrConfig], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file = _registry_with(make_config, tmp_path, {"scan_seite1.pdf": FIXTURES / "Übung" / "scan_seite1.pdf"})

    def _declines(cmd: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            cmd, 1, "", "Too few characters. Skipping this page\nError during processing.\n"
        )

    monkeypatch.setattr(spike_ocr.subprocess, "run", _declines)
    output = tmp_path / "orientation.md"
    args = argparse.Namespace(
        config=config_file,
        page_census=tmp_path / "census.jsonl",
        output=output,
        seed=1,
        control_size=5,
        min_orientation_confidence=2.0,
    )

    assert spike_ocr._orientation_census(args) == 0

    report = output.read_text(encoding="utf-8")
    assert "pages OSD declined (too few characters): 1" in report
    assert "pages with another read or OSD error: 0" in report
    assert "rotated pages: n/a" in report
