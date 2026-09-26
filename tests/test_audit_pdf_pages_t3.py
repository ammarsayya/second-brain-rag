"""T-P2-12: smoke test for tools/audit_pdf_pages_t3.py, the corpus-audit-refresh page census."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from tools.audit_pdf_pages_t3 import _percentile

from sbr.config import SbrConfig
from sbr.db.registry import RegistryDB
from sbr.registry.classify import classify_pending
from sbr.registry.dedup import select_canonical_paths
from sbr.registry.hash import hash_pending
from sbr.registry.scan import scan_root


def test_percentile_of_empty_list_is_zero() -> None:
    assert _percentile([], 0.5) == 0


def test_percentile_picks_the_nearest_ranked_value() -> None:
    values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert _percentile(values, 0.0) == 1
    assert _percentile(values, 1.0) == 10
    assert _percentile(values, 0.5) == 5  # round(0.5 * 9) = round(4.5) = 4 (banker's rounding) -> values[4]


def test_census_opens_real_pdfs_and_counts_pages(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    """Uses the checked-in real PDF fixtures (T-P1-13) rather than a synthetic byte string, since pypdf needs a
    genuinely well-formed PDF to open."""
    fixture_pdf = Path(__file__).parent / "fixtures" / "corpus" / "Regelungstechnik" / "skript.pdf"
    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "skript.pdf").write_bytes(fixture_pdf.read_bytes())

    config_file = tmp_path / "census.toml"
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

    jsonl_output = tmp_path / "pages.jsonl"
    summary_output = tmp_path / "summary.json"
    completed = subprocess.run(
        [
            sys.executable,
            "tools/audit_pdf_pages_t3.py",
            "--config",
            str(config_file),
            "--jsonl-output",
            str(jsonl_output),
            "--summary-output",
            str(summary_output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    summary = json.loads(summary_output.read_text(encoding="utf-8"))
    assert summary["unique_pdf_blobs"] == 1
    assert summary["opened"] == 1
    assert summary["errored"] == 0
    assert summary["total_unique_pages"] > 0

    [row] = [json.loads(line) for line in jsonl_output.read_text(encoding="utf-8").splitlines()]
    assert row["relpath"] == "skript.pdf"
    assert row["page_count"] == summary["total_unique_pages"]
