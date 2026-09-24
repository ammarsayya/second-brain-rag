"""TS-PROV-1/2 (T-P1-07): writes need a running activity; derived rows need derived_from links; locators resolve."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from datetime import UTC, datetime

import pytest

from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.connection import transaction
from sbr.db.registry import RegistryDB
from sbr.db.repository import Repository, TableSpec
from sbr.ids import hash_bytes, new_id
from sbr.provenance import ProvenanceError, ProvenanceStore, params_hash
from sbr.schemas import (
    ActivityStatus,
    BlobClassification,
    BlobRecord,
    ChangeEvent,
    DerivationRole,
    DerivedFrom,
    Locator,
    ScanRecord,
    SourceRootRecord,
    StrictModel,
)
from sbr.schemas.registry import ChangeType, RootKind

T0 = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


class KuTest(StrictModel):
    """Stand-in derived entity (the real knowledge tables arrive in P4/P5)."""

    ku_id: str
    text: str
    activity_id: str


KU = TableSpec("ku_test", KuTest, ("ku_id",))


@pytest.fixture
def db(make_config: Callable[..., SbrConfig]) -> Iterator[RegistryDB]:
    with RegistryDB.open(make_config()) as d:
        d.migrate()
        d.conn.execute("CREATE TABLE ku_test (ku_id TEXT PRIMARY KEY, text TEXT NOT NULL, activity_id TEXT) STRICT")
        yield d


@pytest.fixture
def prov(db: RegistryDB) -> ProvenanceStore:
    return ProvenanceStore(db.conn)


def base_rows(db: RegistryDB, act: str) -> dict[str, str]:
    scan = new_id("scan")
    db.repo(reg.SOURCE_ROOT).insert(
        SourceRootRecord(root_id="fx", path="C:\\fx", kind=RootKind.UNIVERSITY, read_only=True, added_at=T0)
    )
    db.repo(reg.SCAN).insert(ScanRecord(scan_id=scan, root_id="fx", started_at=T0, code_version="1", activity_id=act))
    blob = hash_bytes(b"pdf bytes")
    db.repo(reg.BLOB).insert(
        BlobRecord(blob_id=blob, size=9, first_seen_scan=scan, last_seen_scan=scan, activity_id=act)
    )
    return {"scan": scan, "blob": blob}


def test_activity_lifecycle(prov: ProvenanceStore) -> None:
    act = prov.start_activity("scan", "sbr.scan", "0.1", "system:scanner", params={"root": "fx"}, inputs=[])
    assert act.status is ActivityStatus.RUNNING and act.params_hash == params_hash({"root": "fx"})
    done = prov.finish_activity(act.activity_id, ActivityStatus.SUCCEEDED, outputs=[new_id("obs")])
    stored = prov.get_activity(act.activity_id)
    assert stored == done and stored.status is ActivityStatus.SUCCEEDED and stored.ended_at is not None
    with pytest.raises(ProvenanceError, match="not running"):
        prov.finish_activity(act.activity_id, ActivityStatus.FAILED)
    with pytest.raises(ProvenanceError, match="terminal status"):
        prov.finish_activity(act.activity_id, ActivityStatus.RUNNING)


def test_context_manager_records_success_and_failure(prov: ProvenanceStore) -> None:
    with prov.activity("hash", "sbr.hash", "0.1", "system:hasher") as h:
        h.outputs.append(hash_bytes(b"x"))
    ok = prov.get_activity(h.activity_id)
    assert ok is not None and ok.status is ActivityStatus.SUCCEEDED and ok.outputs == [hash_bytes(b"x")]

    with pytest.raises(ValueError, match="secret path"), prov.activity("hash", "sbr.hash", "0.1", "system:hasher") as f:
        raise ValueError("D:\\MBI-BRAIN\\secret path")
    failed = prov.get_activity(f.activity_id)
    assert failed is not None and failed.status is ActivityStatus.FAILED
    assert failed.notes == "error:ValueError"  # class only: messages may contain source paths


def test_activity_rows_are_protected(prov: ProvenanceStore, db: RegistryDB) -> None:
    act = prov.start_activity("scan", "p", "1", "system:x")
    with pytest.raises(sqlite3.IntegrityError, match="identity columns are immutable"):
        db.conn.execute("UPDATE activity SET producer = 'other' WHERE activity_id = ?", (act.activity_id,))
    with pytest.raises(sqlite3.IntegrityError, match="never deleted"):
        db.conn.execute("DELETE FROM activity WHERE activity_id = ?", (act.activity_id,))
    prov.finish_activity(act.activity_id, ActivityStatus.SUCCEEDED)
    with pytest.raises(sqlite3.IntegrityError, match="finished activities are immutable"):
        db.conn.execute("UPDATE activity SET notes = 'x' WHERE activity_id = ?", (act.activity_id,))
    with pytest.raises(sqlite3.IntegrityError, match="recorded as running"):
        db.conn.execute(
            "INSERT INTO activity (activity_id, kind, producer, producer_version, agent, started_at, ended_at, status) "
            "VALUES (?, 'k', 'p', 'v', 'system:x', 't', 't', 'succeeded')",
            (new_id("act"),),
        )


def test_writes_without_running_activity_fail(prov: ProvenanceStore, db: RegistryDB) -> None:
    """TS-PROV-1 for every provenance-bearing registry table."""
    act = prov.start_activity("scan", "p", "1", "system:x").activity_id
    ids = base_rows(db, act)
    prov.finish_activity(act, ActivityStatus.SUCCEEDED)
    unknown = new_id("act")
    attempts: list[Callable[[str], object]] = [
        lambda a: db.repo(reg.SCAN).insert(
            ScanRecord(scan_id=new_id("scan"), root_id="fx", started_at=T0, code_version="1", activity_id=a)
        ),
        lambda a: db.repo(reg.BLOB).insert(
            BlobRecord(
                blob_id=hash_bytes(a.encode()),
                size=1,
                first_seen_scan=ids["scan"],
                last_seen_scan=ids["scan"],
                activity_id=a,
            )
        ),
        lambda a: db.repo(reg.BLOB_CLASSIFICATION).insert(
            BlobClassification(blob_id=ids["blob"], rules_version=a, activity_id=a)
        ),
        lambda a: db.repo(reg.CHANGE_EVENT).insert(
            ChangeEvent(scan_id=ids["scan"], type=ChangeType.NEW, obs_id=new_id("obs"), activity_id=a)
        ),
        lambda a: prov.link(DerivedFrom(entity_id=new_id("ku"), source_entity_id=ids["blob"]), a),
        lambda a: db.conn.execute("UPDATE blob SET activity_id = ? WHERE blob_id = ?", (a, ids["blob"])),
    ]
    for a in (act, unknown):  # finished, and never recorded
        for attempt in attempts:
            with pytest.raises(sqlite3.IntegrityError, match="requires a running activity"):
                attempt(a)


def test_record_derived_is_atomic_and_needs_links(prov: ProvenanceStore, db: RegistryDB) -> None:
    act = prov.start_activity("segment", "sbr.segment", "0.1", "system:segmenter").activity_id
    ids = base_rows(db, act)
    kus = Repository(db.conn, KU)
    ku = new_id("ku")
    loc = Locator(blob_id=ids["blob"], representation="pdf", page_index=3)
    with pytest.raises(ProvenanceError, match="at least one derived_from"):
        prov.record_derived(kus, KuTest(ku_id=ku, text="t", activity_id=act), ku, [])
    with pytest.raises(ProvenanceError, match="not "):
        prov.record_derived(kus, KuTest(ku_id=ku, text="t", activity_id=act), ku,
                            [DerivedFrom(entity_id=new_id("ku"), source_entity_id=ids["blob"])])  # fmt: skip
    assert kus.count() == 0

    prov.record_derived(kus, KuTest(ku_id=ku, text="t", activity_id=act), ku,
                        [DerivedFrom(entity_id=ku, source_entity_id=ids["blob"], locator=loc)])  # fmt: skip
    assert prov.derived_from(ku) == [DerivedFrom(entity_id=ku, source_entity_id=ids["blob"], locator=loc)]

    # A failing link (self-derivation is refused by the DB) must roll back the entity insert as well.
    ku2 = new_id("ku")
    bad = DerivedFrom.model_construct(
        entity_id=ku2, source_entity_id=ku2, locator=None, role=DerivedFrom.model_fields["role"].default
    )
    with pytest.raises(sqlite3.IntegrityError):
        prov.record_derived(kus, KuTest(ku_id=ku2, text="t2", activity_id=act), ku2, [bad])
    assert kus.get(ku2) is None


def test_nested_transactions_use_savepoints(prov: ProvenanceStore, db: RegistryDB) -> None:
    act = prov.start_activity("segment", "p", "1", "system:x").activity_id
    ids = base_rows(db, act)
    kus = Repository(db.conn, KU)
    ku = new_id("ku")
    with pytest.raises(RuntimeError), transaction(db.conn):
        prov.record_derived(kus, KuTest(ku_id=ku, text="t", activity_id=act), ku,
                            [DerivedFrom(entity_id=ku, source_entity_id=ids["blob"])])  # fmt: skip
        raise RuntimeError("outer failure")
    assert kus.get(ku) is None and prov.derived_from(ku) == []


def test_pv1_and_locator_integrity_queries(prov: ProvenanceStore, db: RegistryDB) -> None:
    """TS-PROV-2: derived rows without links, or with unknown activities, and dangling locators are reported."""
    act = prov.start_activity("segment", "p", "1", "system:x").activity_id
    ids = base_rows(db, act)
    kus = Repository(db.conn, KU)
    good, orphan, ghost = new_id("ku"), new_id("ku"), new_id("ku")
    prov.record_derived(kus, KuTest(ku_id=good, text="g", activity_id=act), good,
                        [DerivedFrom(entity_id=good, source_entity_id=ids["blob"])])  # fmt: skip
    kus.insert(KuTest(ku_id=orphan, text="no link", activity_id=act))  # bypasses record_derived
    db.conn.execute("INSERT INTO ku_test VALUES (?, 'x', ?)", (ghost, new_id("act")))
    assert prov.pv1_violations("ku_test", "ku_id") == sorted([orphan, ghost])

    dangling = Locator(blob_id=hash_bytes(b"not registered"), representation="pdf", page_index=0)
    prov.link(
        DerivedFrom(entity_id=good, source_entity_id=ids["blob"], role=DerivationRole.EVIDENCE, locator=dangling), act
    )
    assert prov.unresolved_locators() == [(good, dangling.blob_id)]
    with pytest.raises(sqlite3.IntegrityError, match="never deleted"):
        db.conn.execute("DELETE FROM derived_from")
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        db.conn.execute("UPDATE derived_from SET role = 'context'")


def test_params_hash_is_order_independent() -> None:
    assert params_hash({"a": 1, "b": [2, 3]}) == params_hash({"b": [2, 3], "a": 1})
    assert params_hash(None) is None
