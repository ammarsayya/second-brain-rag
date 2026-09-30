"""T-P1-06: typed repositories round-trip registry records through registry.sqlite and enforce DB constraints."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.connection import transaction
from sbr.db.registry import RegistryDB
from sbr.db.repository import Repository, TableSpec
from sbr.ids import hash_bytes, new_id
from sbr.provenance import ProvenanceStore
from sbr.schemas import (
    ActivityStatus,
    BlobRecord,
    BlobRelation,
    ChangeEvent,
    PathObservation,
    ScanRecord,
    SourceRootRecord,
)
from sbr.schemas.registry import ChangeType, RelationType, RootKind

T0 = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


@pytest.fixture
def db(make_config: Callable[..., SbrConfig]) -> Iterator[RegistryDB]:
    cfg = make_config()
    with RegistryDB.open(cfg) as d:
        d.migrate()
        yield d


def seed(db: RegistryDB) -> dict[str, str]:
    act = ProvenanceStore(db.conn).start_activity("scan", "test", "1", "system:test").activity_id
    scan = new_id("scan")
    db.repo(reg.SOURCE_ROOT).insert(
        SourceRootRecord(root_id="fx", path="C:\\fixture", kind=RootKind.UNIVERSITY, read_only=True, added_at=T0)
    )
    db.repo(reg.SCAN).insert(ScanRecord(scan_id=scan, root_id="fx", started_at=T0, code_version="0.1", activity_id=act))
    return {"act": act, "scan": scan}


def test_open_from_config_places_db_under_var(make_config: Callable[..., SbrConfig]) -> None:
    cfg = make_config()
    with RegistryDB.open(cfg) as d:
        assert d.path == Path(cfg.roots.var) / "db" / "registry.sqlite"
        assert d.path.exists()


def test_round_trip_and_queries(db: RegistryDB) -> None:
    ids = seed(db)
    b1, b2 = hash_bytes(b"a"), hash_bytes(b"b")
    blobs = db.repo(reg.BLOB)
    for b in (b1, b2):
        blobs.insert(BlobRecord(blob_id=b, size=1, first_seen_scan=ids["scan"], last_seen_scan=ids["scan"],
                                activity_id=ids["act"]))  # fmt: skip
    obs = PathObservation(
        obs_id=new_id("obs"),
        root_id="fx",
        relpath="\u00dcbung\\a.pdf",
        relpath_raw="U\u0308bung\\a.pdf",
        display_name="a.pdf",
        blob_id=b1,
        size=1,
        mtime_ns=5,
        first_seen_scan=ids["scan"],
        last_seen_scan=ids["scan"],
        folder_tokens=["\u00fcbung"],
        is_mirror_candidate=True,
        activity_id=ids["act"],
    )
    observations = db.repo(reg.PATH_OBSERVATION)
    observations.insert(obs)
    assert observations.get(obs.obs_id) == obs
    assert observations.find({"blob_id": b1}) == [obs]
    rel = BlobRelation(src_blob=b1, dst_blob=b2, type=RelationType.TWIN_CANDIDATE, confidence=0.5,
                       evidence={"why": ["name", "size"]}, activity_id=ids["act"])  # fmt: skip
    db.repo(reg.BLOB_RELATION).insert(rel)
    assert db.repo(reg.BLOB_RELATION).get(b1, b2, "twin_candidate") == rel
    ev = ChangeEvent(scan_id=ids["scan"], type=ChangeType.NEW, obs_id=obs.obs_id, blob_id=b1, activity_id=ids["act"])
    db.repo(reg.CHANGE_EVENT).insert(ev)
    assert db.repo(reg.CHANGE_EVENT).find({"scan_id": ids["scan"]}) == [ev]
    assert blobs.count() == 2
    assert db.repo(reg.ACTIVITY).get(ids["act"]).status is ActivityStatus.RUNNING  # type: ignore[union-attr]


def test_upsert_updates_non_key_columns(db: RegistryDB) -> None:
    ids = seed(db)
    scan2 = new_id("scan")
    db.repo(reg.SCAN).insert(ScanRecord(scan_id=scan2, root_id="fx", started_at=T0, code_version="0.1",
                                        activity_id=ids["act"]))  # fmt: skip
    b = hash_bytes(b"x")
    blobs = db.repo(reg.BLOB)
    first = BlobRecord(
        blob_id=b, size=1, first_seen_scan=ids["scan"], last_seen_scan=ids["scan"], activity_id=ids["act"]
    )
    blobs.upsert(first)
    blobs.upsert(first.model_copy(update={"last_seen_scan": scan2}))
    got = blobs.get(b)
    assert got is not None and got.last_seen_scan == scan2 and got.first_seen_scan == ids["scan"]
    assert blobs.count() == 1


def test_foreign_keys_enforced(db: RegistryDB) -> None:
    ids = seed(db)  # a running activity, so only the missing scans can fail the insert
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        db.repo(reg.BLOB).insert(BlobRecord(blob_id=hash_bytes(b"z"), size=1, first_seen_scan=new_id("scan"),
                                            last_seen_scan=new_id("scan"), activity_id=ids["act"]))  # fmt: skip


def test_one_present_observation_per_path(db: RegistryDB) -> None:
    ids = seed(db)

    def obs(state: str = "present") -> PathObservation:
        return PathObservation.model_validate(
            {"obs_id": new_id("obs"), "root_id": "fx", "relpath": "a.pdf", "relpath_raw": "a.pdf", "display_name": "a",
             "size": 1, "mtime_ns": 1, "first_seen_scan": ids["scan"], "last_seen_scan": ids["scan"], "state": state,
             "activity_id": ids["act"]},
            strict=False,
        )  # fmt: skip

    repo = db.repo(reg.PATH_OBSERVATION)
    repo.insert(obs("deleted"))
    repo.insert(obs())
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        repo.insert(obs())


def test_db_check_constraints_back_up_the_models(db: RegistryDB) -> None:
    seed(db)
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        db.conn.execute(
            "INSERT INTO source_root VALUES ('w', 'C:\\w', 'university', 0, '2026-09-24T00:00:00Z')"
        )  # writable non-quarantine root
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        db.conn.execute(
            "INSERT INTO activity (activity_id, kind, producer, producer_version, agent, started_at, status) "
            "VALUES ('act_x', 'k', 'p', 'v', 'anonymous', 't', 'running')"
        )


def test_transaction_rolls_back(db: RegistryDB) -> None:
    ids = seed(db)
    blobs = db.repo(reg.BLOB)
    with pytest.raises(RuntimeError), transaction(db.conn):
        blobs.insert(BlobRecord(blob_id=hash_bytes(b"t"), size=1, first_seen_scan=ids["scan"],
                                last_seen_scan=ids["scan"], activity_id=ids["act"]))  # fmt: skip
        raise RuntimeError("abort")
    assert blobs.count() == 0


def test_repository_guards(db: RegistryDB) -> None:
    with pytest.raises(TypeError, match="expected BlobRecord"):
        db.repo(reg.BLOB).insert(SourceRootRecord(root_id="x", path="C:\\x", kind=RootKind.PERSONAL, read_only=True,
                                                  added_at=T0))  # type: ignore[arg-type]  # fmt: skip
    with pytest.raises(KeyError):
        db.repo(reg.BLOB).find({"nope": 1})
    with pytest.raises(TypeError, match="no natural primary key"):
        db.repo(reg.CHANGE_EVENT).upsert(
            ChangeEvent(scan_id=new_id("scan"), type=ChangeType.NEW, obs_id=new_id("obs"), activity_id=new_id("act"))
        )
    with pytest.raises(LookupError, match="does not exist"):
        Repository(db.conn, TableSpec("no_such_table", BlobRecord, ("blob_id",)))
    with pytest.raises(ValueError, match="unsafe SQL identifier"):
        Repository(db.conn, TableSpec("blob; DROP TABLE blob", BlobRecord, ("blob_id",)))
