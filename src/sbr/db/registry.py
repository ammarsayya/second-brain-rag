"""``registry.sqlite`` facade (ADR-004, docs/31): connection, migrations and typed repositories."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from types import TracebackType

from pydantic import BaseModel

from sbr.config import SbrConfig
from sbr.db.connection import connect
from sbr.db.migrations import MigrationReport, Migrator
from sbr.db.repository import Repository, TableSpec
from sbr.safety import protected_roots
from sbr.schemas import (
    Activity,
    ArchiveMember,
    BlobClassification,
    BlobRecord,
    BlobRelation,
    ChangeEvent,
    PathObservation,
    ScanRecord,
    SourceRootRecord,
    WorkItem,
    WorkOutput,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MIGRATIONS = REPO_ROOT / "migrations" / "registry"

ACTIVITY = TableSpec("activity", Activity, ("activity_id",))
SOURCE_ROOT = TableSpec("source_root", SourceRootRecord, ("root_id",))
SCAN = TableSpec("scan", ScanRecord, ("scan_id",))
BLOB = TableSpec("blob", BlobRecord, ("blob_id",))
PATH_OBSERVATION = TableSpec("path_observation", PathObservation, ("obs_id",))
ARCHIVE_MEMBER = TableSpec("archive_member", ArchiveMember, ("container_blob", "member_path"))
BLOB_CLASSIFICATION = TableSpec("blob_classification", BlobClassification, ("blob_id", "rules_version"))
BLOB_RELATION = TableSpec("blob_relation", BlobRelation, ("src_blob", "dst_blob", "type"))
CHANGE_EVENT = TableSpec("change_event", ChangeEvent, ())
WORK_ITEM = TableSpec("work_item", WorkItem, ("job_id",))
WORK_OUTPUT = TableSpec("work_output", WorkOutput, ("manifest_id",))


class RegistryDB:
    """Open with :meth:`open` (from config) or directly with a path (tests). Call :meth:`migrate` before use."""

    def __init__(
        self,
        path: Path,
        *,
        protected: tuple[str, ...] = (),
        migrations_dir: Path = DEFAULT_MIGRATIONS,
        backup_dir: Path | None = None,
    ) -> None:
        self.path = path
        self.conn: sqlite3.Connection = connect(path, protected)
        self.migrator = Migrator(
            conn=self.conn,
            migrations_dir=migrations_dir,
            db_path=path,
            backup_dir=backup_dir or path.parent.parent / "backups" / "registry",
            protected=protected,
        )

    @classmethod
    def open(cls, config: SbrConfig, *, migrations_dir: Path = DEFAULT_MIGRATIONS) -> RegistryDB:
        return cls(
            config.db_dir / "registry.sqlite",
            protected=protected_roots(config),
            migrations_dir=migrations_dir,
            backup_dir=config.var_path / "backups" / "registry",
        )

    def migrate(self, target: int | None = None) -> MigrationReport:
        return self.migrator.migrate(target)

    @property
    def schema_version(self) -> int:
        return self.migrator.current_version()

    def repo[M: BaseModel](self, spec: TableSpec[M]) -> Repository[M]:
        return Repository(self.conn, spec)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> RegistryDB:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self.close()
