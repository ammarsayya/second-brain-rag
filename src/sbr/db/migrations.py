"""Numbered SQL migrations with checksums, backup-before-migrate and transactional apply (T-P1-06, NFR-11, docs/23).

Layout: ``NNNN_name.sql`` (up) and optional ``NNNN_name.down.sql`` (down) in one directory per database. Versions are
contiguous from 1. Applied migrations are recorded in ``schema_version`` with the SHA-256 of their normalized text; an
applied migration whose file changed afterwards is an error (migrations are immutable once applied).

Each migration runs in one ``BEGIN IMMEDIATE`` transaction, followed by ``PRAGMA foreign_key_check`` before
``COMMIT``. Any failure rolls the database back to the previous version. A backup copy is taken with the SQLite online
backup API before an existing database is changed.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sbr.db.connection import ensure_db_dir

_FILE_RE = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")
_DOWN_RE = re.compile(r"^(\d{4})_([a-z0-9_]+)\.down\.sql$")

_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    checksum   TEXT NOT NULL,
    applied_at TEXT NOT NULL
) STRICT
"""


class MigrationError(RuntimeError):
    """A migration could not be loaded, verified or applied. The database is left at its previous version."""


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    up_sql: str
    down_sql: str | None

    @property
    def checksum(self) -> str:
        return "sha256:" + hashlib.sha256(self.up_sql.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class MigrationReport:
    from_version: int
    to_version: int
    applied: tuple[int, ...]
    reverted: tuple[int, ...] = ()
    backup_path: Path | None = None


def _read_sql(path: Path) -> str:
    # Normalize line endings so checksums survive git autocrlf conversions.
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def load_migrations(directory: Path) -> list[Migration]:
    if not directory.is_dir():
        raise MigrationError(f"migrations directory not found: {directory}")
    ups: dict[int, tuple[str, str]] = {}
    downs: dict[int, str] = {}
    for p in sorted(directory.iterdir()):
        if m := _DOWN_RE.match(p.name):
            downs[int(m.group(1))] = _read_sql(p)
        elif m := _FILE_RE.match(p.name):
            v = int(m.group(1))
            if v in ups:
                raise MigrationError(f"duplicate migration version {v:04d}")
            ups[v] = (m.group(2), _read_sql(p))
        elif p.suffix == ".sql":
            raise MigrationError(f"unrecognized migration file name: {p.name}")
    versions = sorted(ups)
    if versions != list(range(1, len(versions) + 1)):
        raise MigrationError(f"migration versions must be contiguous from 0001, got {versions}")
    orphan_downs = sorted(set(downs) - set(ups))
    if orphan_downs:
        raise MigrationError(f"down migrations without an up migration: {orphan_downs}")
    return [Migration(v, ups[v][0], ups[v][1], downs.get(v)) for v in versions]


@dataclass
class Migrator:
    conn: sqlite3.Connection
    migrations_dir: Path
    db_path: Path
    backup_dir: Path
    protected: Iterable[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        self.migrations = load_migrations(self.migrations_dir)
        self.conn.execute(_VERSION_TABLE)

    @property
    def head(self) -> int:
        return len(self.migrations)

    def current_version(self) -> int:
        row = self.conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()
        return int(row[0])

    def verify_applied(self) -> None:
        """Applied migrations must match their files byte for byte (after newline normalization)."""
        by_version = {m.version: m for m in self.migrations}
        for version, name, checksum in self.conn.execute("SELECT version, name, checksum FROM schema_version"):
            m = by_version.get(version)
            if m is None:
                raise MigrationError(f"database has migration {version:04d} ({name}) that is not on disk (newer code?)")
            if m.checksum != checksum:
                raise MigrationError(f"migration {version:04d}_{name} changed after it was applied")

    def backup(self, label: str) -> Path:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        target = self.backup_dir / f"{self.db_path.stem}-{label}-{stamp}.sqlite"
        ensure_db_dir(target, self.protected)
        dest = sqlite3.connect(target)
        try:
            self.conn.backup(dest)
        finally:
            dest.close()
        return target

    def migrate(self, target: int | None = None) -> MigrationReport:
        """Upgrade (or, with a lower ``target``, downgrade) the database. Default target: head."""
        self.verify_applied()
        goal = self.head if target is None else target
        if not 0 <= goal <= self.head:
            raise MigrationError(f"target version {goal} outside 0..{self.head}")
        current = self.current_version()
        if goal == current:
            return MigrationReport(current, current, ())
        backup = self.backup(f"v{current}-to-v{goal}") if current > 0 else None
        if goal > current:
            applied = tuple(self._apply_up(m) for m in self.migrations[current:goal])
            return MigrationReport(current, goal, applied, backup_path=backup)
        reverted = tuple(self._apply_down(m) for m in reversed(self.migrations[goal:current]))
        return MigrationReport(current, goal, (), reverted=reverted, backup_path=backup)

    def _run_in_transaction(self, script: str, label: str) -> None:
        try:
            self.conn.executescript("BEGIN IMMEDIATE;\n" + script)
            self._check_foreign_keys(label)
            self.conn.execute("COMMIT")
        except Exception as exc:
            if self.conn.in_transaction:
                self.conn.execute("ROLLBACK")
            if isinstance(exc, MigrationError):
                raise
            raise MigrationError(f"{label} failed and was rolled back: {exc}") from exc

    def _check_foreign_keys(self, label: str) -> None:
        problems = self.conn.execute("PRAGMA foreign_key_check").fetchall()
        if problems:
            raise MigrationError(f"{label}: foreign key violations after migration: {problems[:5]}")

    def _apply_up(self, m: Migration) -> int:
        applied_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        record = (
            f"\n;\nINSERT INTO schema_version (version, name, checksum, applied_at) "
            f"VALUES ({m.version}, '{m.name}', '{m.checksum}', '{applied_at}');\n"
        )
        self._run_in_transaction(m.up_sql + record, f"migration {m.version:04d}_{m.name}")
        return m.version

    def _apply_down(self, m: Migration) -> int:
        if m.down_sql is None:
            raise MigrationError(f"migration {m.version:04d}_{m.name} has no down script; restore from a backup")
        record = f"\n;\nDELETE FROM schema_version WHERE version = {m.version};\n"
        self._run_in_transaction(m.down_sql + record, f"down migration {m.version:04d}_{m.name}")
        return m.version
