"""Run T-P13-04's rollback/re-upgrade drill on a disposable copy of a populated registry DB."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import uuid
from pathlib import Path

from sbr.db.migrations import load_migrations
from sbr.db.registry import DEFAULT_MIGRATIONS, RegistryDB


class DrillError(RuntimeError):
    """The migration-copy drill could not prove a safe round trip."""


def _consistent_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_conn = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    destination_conn = sqlite3.connect(destination)
    try:
        source_conn.execute("PRAGMA query_only = ON")
        source_conn.backup(destination_conn)
    finally:
        destination_conn.close()
        source_conn.close()


def _row_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' AND name != 'schema_version' ORDER BY name"
        )
    ]
    return {table: int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]) for table in tables}


def validate_copy_round_trip(database: Path, migrations: Path, work_dir: Path) -> dict[str, object]:
    """Copy ``database`` through SQLite, then downgrade/re-upgrade only the disposable copy."""
    source = database.resolve(strict=True)
    if not source.is_file():
        raise DrillError("database is not a regular file")
    migration_set = load_migrations(migrations)
    if not migration_set:
        raise DrillError("no migrations found")

    before_stat = source.stat()
    scratch = (work_dir / f"drill-{uuid.uuid4().hex}").resolve()
    work_root = work_dir.resolve()
    if work_root not in scratch.parents:
        raise DrillError("scratch path escaped the requested work directory")
    copy_path = scratch / "registry-copy.sqlite"
    try:
        _consistent_copy(source, copy_path)
        with RegistryDB(copy_path, migrations_dir=migrations, backup_dir=scratch / "backups") as copy:
            head = copy.migrator.head
            if copy.schema_version != head:
                raise DrillError(f"source copy is at schema v{copy.schema_version}, expected head v{head}")
            if copy.conn.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise DrillError("source copy failed SQLite integrity_check")
            counts_before = _row_counts(copy.conn)

            down = copy.migrate(head - 1)
            if down.reverted != (head,):
                raise DrillError(f"expected to revert migration {head}, got {down.reverted}")
            up = copy.migrate(head)
            if up.applied != (head,):
                raise DrillError(f"expected to reapply migration {head}, got {up.applied}")
            if copy.conn.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise DrillError("round-tripped copy failed SQLite integrity_check")
            counts_after = _row_counts(copy.conn)
            if counts_after != counts_before:
                raise DrillError("table row counts changed across rollback/re-upgrade")

        after_stat = source.stat()
        if (after_stat.st_size, after_stat.st_mtime_ns) != (before_stat.st_size, before_stat.st_mtime_ns):
            raise DrillError("source database metadata changed during the copy drill")
        return {
            "status": "pass",
            "schema_version": len(migration_set),
            "tables_checked": len(counts_before),
            "rows_checked": sum(counts_before.values()),
            "source_unchanged": True,
        }
    finally:
        if scratch.is_dir():
            shutil.rmtree(scratch)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("var/db/registry.sqlite"))
    parser.add_argument("--migrations", type=Path, default=DEFAULT_MIGRATIONS)
    parser.add_argument("--work-dir", type=Path, default=Path("var/migration_validation"))
    args = parser.parse_args(argv)
    try:
        result = validate_copy_round_trip(args.database, args.migrations, args.work_dir)
    except (DrillError, FileNotFoundError, sqlite3.Error) as exc:
        print(f"MIGRATION COPY DRILL FAILED: {exc}", file=sys.stderr)
        return 1
    print("MIGRATION COPY DRILL PASS: " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
