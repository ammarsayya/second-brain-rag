"""TS-MIG: fresh migrate to head; N-1 -> N upgrade with backup; failures roll back; downgrade; tamper checks."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from sbr.db.migrations import MigrationError, load_migrations
from sbr.db.registry import DEFAULT_MIGRATIONS, RegistryDB
from sbr.ids import new_id


def tables(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


@pytest.fixture
def mig_dir(tmp_path: Path) -> Path:
    d = tmp_path / "migrations"
    shutil.copytree(DEFAULT_MIGRATIONS, d)
    return d


def open_db(tmp_path: Path, mig_dir: Path) -> RegistryDB:
    return RegistryDB(tmp_path / "var" / "db" / "registry.sqlite", migrations_dir=mig_dir)


def test_real_migrations_are_well_formed() -> None:
    migs = load_migrations(DEFAULT_MIGRATIONS)
    assert [m.version for m in migs] == list(range(1, len(migs) + 1))
    assert all(m.down_sql for m in migs), "every registry migration ships a down script"


def test_fresh_database_migrates_to_head(tmp_path: Path) -> None:
    with RegistryDB(tmp_path / "var" / "db" / "registry.sqlite") as db:
        report = db.migrate()
        assert report.from_version == 0
        assert report.to_version == db.migrator.head == db.schema_version
        assert report.backup_path is None  # nothing to back up yet
        assert {"activity", "blob", "path_observation", "scan", "schema_version"} <= tables(db.conn)
        assert db.conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert db.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert db.migrate().applied == ()  # idempotent


def test_classification_column_up_and_down(tmp_path: Path) -> None:
    """SQLite accepts the v5 STRICT-table ADD COLUMN and can reverse it cleanly."""
    with RegistryDB(tmp_path / "var" / "db" / "registry.sqlite") as db:
        db.migrate(4)
        assert "encrypted" not in {row[1] for row in db.conn.execute("PRAGMA table_info(blob)")}
        report = db.migrate(5)
        assert report.applied == (5,)
        columns = {row[1]: row for row in db.conn.execute("PRAGMA table_info(blob)")}
        assert columns["encrypted"][3] == 1
        assert columns["encrypted"][4] == "0"
        report = db.migrate(4)
        assert report.reverted == (5,)
        assert "encrypted" not in {row[1] for row in db.conn.execute("PRAGMA table_info(blob)")}


def test_each_version_upgrades_to_head_with_backup(tmp_path: Path) -> None:
    """For every N-1 (1..head-1) and a synthetic next migration: data survives and a backup is taken first."""
    base = tmp_path / "m"
    shutil.copytree(DEFAULT_MIGRATIONS, base)
    head = len(load_migrations(base))
    (base / f"{head + 1:04d}_test_next.sql").write_text(
        "CREATE TABLE test_next (k INTEGER PRIMARY KEY) STRICT;\nINSERT INTO test_next VALUES (42);\n", encoding="utf-8"
    )
    (base / f"{head + 1:04d}_test_next.down.sql").write_text("DROP TABLE test_next;\n", encoding="utf-8")
    for start in range(1, head + 1):
        with RegistryDB(tmp_path / f"v{start}" / "db" / "registry.sqlite", migrations_dir=base) as db:
            db.migrate(start)
            db.conn.execute(
                "INSERT INTO source_root VALUES ('mbi', 'D:\\MBI-BRAIN', 'university', 1, '2026-09-24T00:00:00Z')"
            )
            report = db.migrate()
            assert report.from_version == start and report.to_version == head + 1
            assert report.backup_path is not None and report.backup_path.exists()
            assert db.conn.execute("SELECT k FROM test_next").fetchone() == (42,)
            assert db.conn.execute("SELECT root_id FROM source_root").fetchall() == [("mbi",)]
            backup = sqlite3.connect(report.backup_path)
            try:
                assert backup.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == start
                assert backup.execute("SELECT COUNT(*) FROM source_root").fetchone()[0] == 1
            finally:
                backup.close()


def test_failed_migration_rolls_back(tmp_path: Path, mig_dir: Path) -> None:
    head = len(load_migrations(mig_dir))
    (mig_dir / f"{head + 1:04d}_broken.sql").write_text(
        "CREATE TABLE half_done (k INTEGER) STRICT;\nTHIS IS NOT SQL;\n", encoding="utf-8"
    )
    with open_db(tmp_path, mig_dir) as db:
        db.migrate(head)
        with pytest.raises(MigrationError, match="rolled back"):
            db.migrate()
        assert db.schema_version == head
        assert "half_done" not in tables(db.conn)
        assert not db.conn.in_transaction


def test_foreign_key_violation_rolls_back(tmp_path: Path, mig_dir: Path) -> None:
    head = len(load_migrations(mig_dir))
    act = new_id("act")
    (mig_dir / f"{head + 1:04d}_bad_fk.sql").write_text(
        "PRAGMA foreign_keys = OFF;\n"  # ignored inside the migration transaction, by design
        "INSERT INTO activity (activity_id, kind, producer, producer_version, agent, started_at, status) VALUES "
        f"('{act}', 'k', 'p', 'v', 'system:t', 't', 'running');\n"
        "INSERT INTO scan (scan_id, root_id, started_at, status, code_version, activity_id) VALUES "
        f"('{new_id('scan')}', 'missing-root', 'x', 'running', 'v', '{act}');\n",
        encoding="utf-8",
    )
    with open_db(tmp_path, mig_dir) as db:
        db.migrate(head)
        with pytest.raises(MigrationError, match=r"(?i)foreign key"):
            db.migrate()
        assert db.schema_version == head
        assert db.conn.execute("SELECT COUNT(*) FROM scan").fetchone()[0] == 0


def test_downgrade_and_reupgrade(tmp_path: Path) -> None:
    with RegistryDB(tmp_path / "var" / "db" / "registry.sqlite") as db:
        db.migrate()
        report = db.migrate(0)
        assert report.reverted and db.schema_version == 0
        assert report.backup_path is not None and report.backup_path.exists()
        assert tables(db.conn) == {"schema_version"}
        db.migrate()
        assert "blob" in tables(db.conn)


def test_changed_applied_migration_is_detected(tmp_path: Path, mig_dir: Path) -> None:
    with open_db(tmp_path, mig_dir) as db:
        db.migrate()
    first = next(p for p in mig_dir.glob("0001_*.sql") if not p.name.endswith(".down.sql"))
    first.write_text(first.read_text(encoding="utf-8") + "\n-- edited\n", encoding="utf-8")
    with open_db(tmp_path, mig_dir) as db, pytest.raises(MigrationError, match="changed after it was applied"):
        db.migrate()


def test_crlf_checkout_does_not_change_checksum(tmp_path: Path, mig_dir: Path) -> None:
    with open_db(tmp_path, mig_dir) as db:
        db.migrate()
    for p in mig_dir.glob("*.sql"):
        p.write_bytes(p.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    with open_db(tmp_path, mig_dir) as db:
        assert db.migrate().applied == ()


def test_database_newer_than_code_is_refused(tmp_path: Path, mig_dir: Path) -> None:
    with open_db(tmp_path, mig_dir) as db:
        db.migrate()
        db.conn.execute("INSERT INTO schema_version VALUES (999, 'future', 'sha256:x', 'now')")
    with open_db(tmp_path, mig_dir) as db, pytest.raises(MigrationError, match="not on disk"):
        db.migrate()


@pytest.mark.parametrize(
    ("files", "needle"),
    [
        (["0001_a.sql", "0003_c.sql"], "contiguous"),
        (["0001_a.sql", "0002_b.down.sql"], "without an up"),
        (["0001_a.sql", "1_bad.sql"], "unrecognized"),
    ],
)
def test_malformed_migration_sets(tmp_path: Path, files: list[str], needle: str) -> None:
    for f in files:
        (tmp_path / f).write_text("SELECT 1;\n", encoding="utf-8")
    with pytest.raises(MigrationError, match=needle):
        load_migrations(tmp_path)


def test_database_inside_protected_root_refused(tmp_path: Path) -> None:
    from sbr.safety import SourceWriteError

    src = tmp_path / "src_root"
    with pytest.raises(SourceWriteError):
        RegistryDB(src / "registry.sqlite", protected=(str(src),))
    assert not src.exists()
