"""TS-QUEUE (T-P1-09): crash-resume loses/duplicates nothing; version bumps re-enqueue exactly the affected subject."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest

from sbr.config import SbrConfig
from sbr.db.registry import RegistryDB
from sbr.ids import hash_bytes
from sbr.jobs import JobQueue, LeaseError, backoff_ms, ready_stages
from sbr.schemas import WorkItem, WorkItemState

B1, B2 = hash_bytes(b"one"), hash_bytes(b"two")


class FakeClock:
    """Millisecond clock a test can advance deterministically (no real sleeps, no subprocess)."""

    def __init__(self, start_ms: int = 1_000_000) -> None:
        self.ms = start_ms

    def __call__(self) -> int:
        return self.ms

    def advance(self, delta_ms: int) -> None:
        self.ms += delta_ms


@pytest.fixture
def db(make_config: Callable[..., SbrConfig]) -> Iterator[RegistryDB]:
    cfg = make_config()
    with RegistryDB.open(cfg) as d:
        d.migrate()
        yield d


def make_queue(db: RegistryDB, clock: FakeClock | None = None) -> JobQueue:
    return JobQueue(db.conn, clock_ms=clock or FakeClock())


def token(item: WorkItem) -> str:
    """A leased item's lease_token, narrowed from the schema's ``str | None`` for calls that require it."""
    assert item.lease_token is not None
    return item.lease_token


# -- enqueue / idempotency --------------------------------------------------------------------------------------


def test_enqueue_is_idempotent_on_the_natural_key(db: RegistryDB) -> None:
    q = make_queue(db)
    first = q.enqueue(B1, "extract_text", "v1")
    second = q.enqueue(B1, "extract_text", "v1")
    assert first.job_id == second.job_id
    assert q.items.count() == 1


def test_bumping_stage_version_enqueues_only_the_affected_subject(db: RegistryDB) -> None:
    q = make_queue(db)
    q.enqueue(B1, "extract_text", "v1")
    q.enqueue(B2, "extract_text", "v1")

    bumped = q.enqueue(B1, "extract_text", "v2")

    assert q.items.count() == 3
    assert bumped.stage_version == "v2"
    # B2's v1 row is untouched: the version bump did not touch a subject it does not concern.
    assert q._find_one(subject_id=B2, stage="extract_text", stage_version="v1") is not None
    assert q._find_one(subject_id=B2, stage="extract_text", stage_version="v2") is None


# -- leasing -----------------------------------------------------------------------------------------------------


def test_lease_claims_only_ready_items_in_priority_order(db: RegistryDB) -> None:
    q = make_queue(db)
    q.enqueue(B1, "extract_text", "v1", priority=0)
    q.enqueue(B2, "extract_text", "v1", priority=5)
    q.enqueue(B1, "classify", "v1")  # different stage: never returned by a lease on "extract_text"

    leased = q.lease("extract_text", count=10)

    assert [i.subject_id for i in leased] == [B2, B1]
    assert all(i.state is WorkItemState.LEASED for i in leased)
    assert all(i.attempts == 1 for i in leased)


def test_lease_does_not_reclaim_an_item_before_its_lease_expires(db: RegistryDB) -> None:
    clock = FakeClock()
    q = make_queue(db, clock)
    q.enqueue(B1, "extract_text", "v1")
    q.lease("extract_text", lease_ms=60_000)

    clock.advance(1_000)  # well before the 60s lease expires
    assert q.lease("extract_text") == []


def test_crash_then_restart_reclaims_exactly_once(db: RegistryDB) -> None:
    """Simulates a killed worker: a fresh JobQueue (as a restarted process would open) resumes cleanly (TS-QUEUE)."""
    clock = FakeClock()
    worker_a = make_queue(db, clock)
    worker_a.enqueue(B1, "extract_text", "v1")
    [claimed_by_a] = worker_a.lease("extract_text", owner="system:worker-a", lease_ms=30_000)
    assert claimed_by_a.attempts == 1

    # Worker A is killed here: it never completes or fails the item, and its process is gone.
    clock.advance(29_000)  # still within the lease: a second worker must not steal it yet
    worker_b = make_queue(db, clock)  # a fresh instance, as a restarted process would open
    assert worker_b.lease("extract_text", owner="system:worker-b") == []

    clock.advance(2_000)  # now past the 30s lease
    [claimed_by_b] = worker_b.lease("extract_text", owner="system:worker-b")
    assert claimed_by_b.job_id == claimed_by_a.job_id
    assert claimed_by_b.attempts == 2  # one lease per worker, not lost, not duplicated
    assert claimed_by_b.lease_owner == "system:worker-b"

    # The dead worker's stale lease token can no longer complete the item (it is not the current holder).
    with pytest.raises(LeaseError):
        worker_a.complete(claimed_by_a.job_id, token(claimed_by_a), artifacts={"doc": B2})

    output = worker_b.complete(claimed_by_b.job_id, token(claimed_by_b), artifacts={"doc": B2})
    done = worker_b.items.get(claimed_by_b.job_id)
    assert done is not None
    assert done.state is WorkItemState.DONE
    assert done.output_manifest_id == output.manifest_id
    assert worker_b.outputs.get(output.manifest_id) == output
    # No duplicate row was ever created for this (subject, stage, version).
    assert worker_b.items.count({"subject_id": B1, "stage": "extract_text", "stage_version": "v1"}) == 1


def test_extend_requires_the_current_lease_token(db: RegistryDB) -> None:
    clock = FakeClock()
    q = make_queue(db, clock)
    q.enqueue(B1, "extract_text", "v1")
    [item] = q.lease("extract_text", lease_ms=1_000)

    extended = q.extend(item.job_id, token(item), lease_ms=60_000)
    assert extended.lease_expires_ms == clock.ms + 60_000

    with pytest.raises(LeaseError):
        q.extend(item.job_id, "not-the-token")


# -- retries and backoff -------------------------------------------------------------------------------------


def test_backoff_is_exponential_and_capped() -> None:
    assert backoff_ms(1) == 1_000
    assert backoff_ms(2) == 2_000
    assert backoff_ms(3) == 4_000
    assert backoff_ms(20) == 15 * 60 * 1000  # capped
    with pytest.raises(ValueError, match="1-based"):
        backoff_ms(0)


def test_fail_retries_with_backoff_then_becomes_terminal(db: RegistryDB) -> None:
    clock = FakeClock()
    q = make_queue(db, clock)
    q.enqueue(B1, "extract_text", "v1", max_attempts=2)

    [item] = q.lease("extract_text")
    after_first_fail = q.fail(item.job_id, token(item), error="boom")
    assert after_first_fail.state is WorkItemState.PENDING
    assert after_first_fail.not_before_ms == clock.ms + backoff_ms(1)
    assert after_first_fail.last_error == "boom"

    clock.advance(after_first_fail.not_before_ms - clock.ms)
    [item2] = q.lease("extract_text")
    assert item2.attempts == 2
    terminal = q.fail(item2.job_id, token(item2), error="boom again")
    assert terminal.state is WorkItemState.FAILED

    # A poison item never blocks the queue: it is never returned by lease() again.
    clock.advance(10**9)
    assert q.lease("extract_text") == []


def test_a_stale_lease_token_cannot_fail_an_item_either(db: RegistryDB) -> None:
    clock = FakeClock()
    q = make_queue(db, clock)
    q.enqueue(B1, "extract_text", "v1", max_attempts=2)
    [item] = q.lease("extract_text", lease_ms=1_000)
    clock.advance(2_000)
    [reclaimed] = q.lease("extract_text")  # a second worker now legitimately holds it

    with pytest.raises(LeaseError):
        q.fail(item.job_id, token(item), error="too late")
    still_leased = q.items.get(reclaimed.job_id)
    assert still_leased is not None
    assert still_leased.state is WorkItemState.LEASED


def test_an_expired_lease_past_max_attempts_is_retired_instead_of_re_leased(db: RegistryDB) -> None:
    clock = FakeClock()
    q = make_queue(db, clock)
    q.enqueue(B1, "extract_text", "v1", max_attempts=1)
    [item] = q.lease("extract_text", lease_ms=1_000)

    clock.advance(2_000)  # the crashed worker's only allowed attempt has now expired
    assert q.lease("extract_text") == []  # never handed to a second worker: it is retired, not re-leased

    retired = q.items.get(item.job_id)
    assert retired is not None
    assert retired.state is WorkItemState.FAILED


# -- stage DAG enqueueing ------------------------------------------------------------------------------------


def test_ready_stages_needs_every_prerequisite_done() -> None:
    dag = {"extract": (), "classify": ("extract",), "index": ("extract", "classify")}
    assert ready_stages(dag, done_stages=set()) == ["extract"]
    assert ready_stages(dag, done_stages={"extract"}) == ["classify"]
    assert ready_stages(dag, done_stages={"extract", "classify"}) == ["index"]


def test_advance_enqueues_downstream_stages_once_their_prerequisites_complete(db: RegistryDB) -> None:
    clock = FakeClock()
    q = make_queue(db, clock)
    dag = {"extract": (), "classify": ("extract",)}
    versions = {"extract": "v1", "classify": "v1"}

    [first] = q.advance(B1, dag, versions)
    assert first.stage == "extract"
    # Calling advance() again before extract is done re-derives the same (idempotent) row, not a duplicate.
    [again] = q.advance(B1, dag, versions)
    assert again.job_id == first.job_id
    assert q.items.count() == 1  # classify's prerequisite is not done yet, so it was never enqueued

    [item] = q.lease("extract")
    q.complete(item.job_id, token(item))

    [classify_item] = q.advance(B1, dag, versions)
    assert classify_item.stage == "classify"
    [again] = q.advance(B1, dag, versions)  # idempotent: re-derives the same row, no duplicate
    assert again.job_id == classify_item.job_id
    assert q.items.count() == 2
