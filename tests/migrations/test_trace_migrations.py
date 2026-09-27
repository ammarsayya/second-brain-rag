"""T-P9-02: the standalone trace migration applies, rolls back, and reapplies."""

from __future__ import annotations

from pathlib import Path

from sbr.obs.trace import TraceDB


def _objects(db: TraceDB) -> set[str]:
    return {
        str(row[0])
        for row in db.conn.execute(
            "SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' AND name != 'schema_version'"
        )
    }


def test_trace_migration_up_down_and_up_again(tmp_path: Path) -> None:
    with TraceDB(tmp_path / "trace.sqlite", backup_dir=tmp_path / "backups") as db:
        up = db.migrate()
        assert up.applied == (1,)
        assert {"span", "span_run_parent", "span_no_delete", "span_finished_immutable"} <= _objects(db)
        columns = {str(row[1]) for row in db.conn.execute("PRAGMA table_info(span)")}
        assert {"span_id", "run_id", "parent_span_id", "sequence", "kind", "status", "tool_calls"} <= columns
        assert db.conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)

        down = db.migrate(0)
        assert down.reverted == (1,)
        assert _objects(db) == set()

        second_up = db.migrate()
        assert second_up.applied == (1,)
        assert "span" in _objects(db)
        assert db.conn.execute("PRAGMA foreign_key_check").fetchall() == []
