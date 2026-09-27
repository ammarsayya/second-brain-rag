"""T-P13-04: every real registry migration works N-1 -> N, down, and up again on a DB copy."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sbr.db.migrations import load_migrations
from sbr.db.registry import DEFAULT_MIGRATIONS, RegistryDB

MIGRATIONS = load_migrations(DEFAULT_MIGRATIONS)


def sqlite_backup(source: Path, destination: Path) -> None:
    """Make a transactionally consistent database copy through SQLite, including WAL state."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_conn = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    destination_conn = sqlite3.connect(destination)
    try:
        source_conn.backup(destination_conn)
    finally:
        destination_conn.close()
        source_conn.close()


def schema(conn: sqlite3.Connection) -> list[tuple[str, str, str | None]]:
    return [
        (kind, name, sql)
        for kind, name, sql in conn.execute(
            "SELECT type, name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' AND name != 'schema_version' ORDER BY type, name"
        )
    ]


@pytest.mark.parametrize("target", [migration.version for migration in MIGRATIONS])
def test_each_actual_migration_up_down_and_up_again_on_a_database_copy(target: int, tmp_path: Path) -> None:
    fixture_path = tmp_path / f"fixture-v{target - 1}.sqlite"
    with RegistryDB(fixture_path) as fixture:
        fixture.migrate(target - 1)
        if target > 1:
            fixture.conn.execute(
                "INSERT INTO source_root VALUES ('fixture', 'X:/read-only-source', 'personal', 1, "
                "'2026-09-27T00:00:00Z')"
            )
        before_schema = schema(fixture.conn)

    copy_path = tmp_path / "copies" / f"upgrade-v{target - 1}-to-v{target}.sqlite"
    sqlite_backup(fixture_path, copy_path)

    with RegistryDB(copy_path, backup_dir=tmp_path / "backups") as copy:
        up = copy.migrate(target)
        assert up.from_version == target - 1
        assert up.to_version == target
        assert up.applied == (target,)
        assert up.backup_path is None if target == 1 else up.backup_path is not None
        assert copy.conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        if target > 1:
            assert copy.conn.execute("SELECT root_id FROM source_root").fetchall() == [("fixture",)]

        down = copy.migrate(target - 1)
        assert down.reverted == (target,)
        assert schema(copy.conn) == before_schema
        assert copy.conn.execute("PRAGMA foreign_key_check").fetchall() == []

        second_up = copy.migrate(target)
        assert second_up.applied == (target,)
        assert copy.conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        if target > 1:
            assert copy.conn.execute("SELECT root_id FROM source_root").fetchall() == [("fixture",)]
