"""SQLite connections (ADR-004): WAL, foreign keys, busy timeout, explicit transactions.

This is the only db module that creates directories. Every database path is checked against the protected roots
before anything is created (docs/22 §1).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

from sbr.safety import assert_outside

BUSY_TIMEOUT_MS = 5000


def ensure_db_dir(path: Path, protected: Iterable[str]) -> None:
    """Create the parent directory of a database or backup file after the protection check."""
    assert_outside(path, protected)
    path.parent.mkdir(parents=True, exist_ok=True)


def connect(path: Path, protected: Iterable[str] = ()) -> sqlite3.Connection:
    """Open a database in autocommit mode (transactions are explicit via :func:`transaction`)."""
    roots = tuple(protected)
    ensure_db_dir(path, roots)
    conn = sqlite3.connect(path, isolation_level=None, timeout=BUSY_TIMEOUT_MS / 1000, check_same_thread=True)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """``BEGIN IMMEDIATE`` … ``COMMIT``; rolls back on any exception (single-writer discipline, ADR-004)."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
