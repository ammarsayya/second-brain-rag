"""The T-P13-04 copy drill never mutates its source database."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from sbr.db.registry import RegistryDB

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "validate_migrations.py"


def test_copy_drill_round_trips_head_without_changing_source(tmp_path: Path) -> None:
    database = tmp_path / "source" / "registry.sqlite"
    with RegistryDB(database) as db:
        db.migrate()
        db.conn.execute(
            "INSERT INTO source_root VALUES ('fixture', 'X:/read-only-source', 'personal', 1, '2026-09-27T00:00:00Z')"
        )
    original = database.read_bytes()

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--database",
            str(database),
            "--work-dir",
            str(tmp_path / "work"),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "MIGRATION COPY DRILL PASS" in result.stdout
    assert '"source_unchanged": true' in result.stdout
    assert database.read_bytes() == original
    assert not list((tmp_path / "work").glob("drill-*"))


def test_copy_drill_refuses_a_database_that_is_not_at_head(tmp_path: Path) -> None:
    database = tmp_path / "source" / "registry.sqlite"
    with RegistryDB(database) as db:
        db.migrate(4)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--database",
            str(database),
            "--work-dir",
            str(tmp_path / "work"),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "expected head v5" in result.stderr
    assert not list((tmp_path / "work").glob("drill-*"))
