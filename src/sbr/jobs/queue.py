"""Job queue with leases and checkpoints (T-P1-09, docs/08 §2, HC-16, HC-24, NFR-02, NFR-03).

Idempotency key: ``(subject_id, stage, stage_version)`` (the ``work_item`` unique constraint). Enqueuing an existing
key is a no-op, so a restarted pipeline or a re-run of the same stage version never creates duplicate work; bumping
``stage_version`` is a new row, so it re-enqueues exactly the affected subjects without disturbing history.

A lease is identified by a random ``lease_token``, not just ownership of the row: only the current token's holder
may extend, complete or fail an item, so an item that was re-leased after its previous lease expired can never be
completed twice by the crashed worker that held it first. Leasing itself reclaims expired leases (there is no
separate reap step): ``lease()`` matches pending items *or* leased items whose ``lease_expires_ms`` is in the past,
so a crashed worker's items become available again the next time anyone leases that stage. Together this is what
makes a kill-and-restart lose no items and duplicate none (TS-QUEUE).

Completion is atomic: the output manifest row and the ``work_item`` state move in one SQLite transaction, so a crash
between them is impossible to observe (docs/08 §2 "atomic completion").
"""

from __future__ import annotations

import secrets
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime

from sbr.db.connection import transaction
from sbr.db.registry import WORK_ITEM, WORK_OUTPUT
from sbr.db.repository import Repository
from sbr.ids import new_id
from sbr.jobs.dag import ready_stages
from sbr.schemas import WorkItem, WorkItemState, WorkOutput

DEFAULT_LEASE_MS: int = 5 * 60 * 1000
DEFAULT_MAX_ATTEMPTS: int = 5
BACKOFF_BASE_MS: int = 1_000
BACKOFF_CAP_MS: int = 15 * 60 * 1000

__all__ = [
    "BACKOFF_BASE_MS",
    "BACKOFF_CAP_MS",
    "DEFAULT_LEASE_MS",
    "DEFAULT_MAX_ATTEMPTS",
    "JobQueue",
    "LeaseError",
    "backoff_ms",
]


def backoff_ms(attempt: int, *, base_ms: int = BACKOFF_BASE_MS, cap_ms: int = BACKOFF_CAP_MS) -> int:
    """Exponential backoff delay before attempt ``attempt`` (1-based) is retried, capped at ``cap_ms``."""
    if attempt < 1:
        raise ValueError("attempt is 1-based")
    return min(cap_ms, base_ms * (1 << (attempt - 1)))


class LeaseError(RuntimeError):
    """A complete/extend/fail call did not hold the lease it claimed to (already expired, re-leased, or unknown)."""


class JobQueue:
    """Access to ``work_item``/``work_output`` (docs/08 §2). One instance per open registry connection.

    ``clock_ms`` is injectable so tests can simulate lease expiry and backoff without sleeping or spawning a real
    subprocess; production code leaves it at the wall clock.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        clock_ms: Callable[[], int] | None = None,
        owner: str = "system:worker",
    ) -> None:
        self.conn = conn
        self.items: Repository[WorkItem] = Repository(conn, WORK_ITEM)
        self.outputs: Repository[WorkOutput] = Repository(conn, WORK_OUTPUT)
        self._clock_ms = clock_ms or (lambda: int(datetime.now(UTC).timestamp() * 1000))
        self._owner = owner

    def _now(self) -> datetime:
        return datetime.fromtimestamp(self._clock_ms() / 1000, tz=UTC)

    # -- enqueue ----------------------------------------------------------------------------------------------------

    def enqueue(
        self,
        subject_id: str,
        stage: str,
        stage_version: str,
        *,
        priority: int = 0,
        wave: str | None = None,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        not_before_ms: int = 0,
    ) -> WorkItem:
        """Idempotently enqueue ``(subject_id, stage, stage_version)``; returns the existing row if already present."""
        with transaction(self.conn):
            existing = self._find_one(subject_id=subject_id, stage=stage, stage_version=stage_version)
            if existing is not None:
                return existing
            now = self._now()
            item = WorkItem(
                job_id=new_id("job"),
                subject_id=subject_id,
                stage=stage,
                stage_version=stage_version,
                priority=priority,
                wave=wave,
                max_attempts=max_attempts,
                not_before_ms=not_before_ms,
                created_at=now,
                updated_at=now,
            )
            self.items.insert(item)
            return item

    def advance(
        self,
        subject_id: str,
        dag: Mapping[str, Sequence[str]],
        versions: Mapping[str, str],
        **enqueue_kwargs: object,
    ) -> list[WorkItem]:
        """Enqueue every stage of ``dag`` whose prerequisites are done for ``subject_id`` at their current version.

        ``versions`` gives each stage's current ``stage_version``; a stage is "done" for this purpose only when the
        subject's ``done`` row is at that exact version (an older completion does not count once bumped).
        """
        rows = self.items.find({"subject_id": subject_id})
        done = {r.stage for r in rows if r.state is WorkItemState.DONE and r.stage_version == versions.get(r.stage)}
        return [
            self.enqueue(subject_id, stage, versions[stage], **enqueue_kwargs)  # type: ignore[arg-type]
            for stage in ready_stages(dag, done)
        ]

    def _find_one(self, **where: object) -> WorkItem | None:
        rows = self.items.find(where, limit=1)
        return rows[0] if rows else None

    # -- leasing ------------------------------------------------------------------------------------------------

    def lease(
        self,
        stage: str,
        *,
        owner: str | None = None,
        count: int = 1,
        lease_ms: int = DEFAULT_LEASE_MS,
    ) -> list[WorkItem]:
        """Atomically claim up to ``count`` ready items for ``stage``.

        Ready means pending and due, or leased with an expired lease (a crashed worker's item) — see module
        docstring. Claimed items are ordered by priority, then how long they have been waiting. An expired lease
        whose ``attempts`` already reached ``max_attempts`` is never re-leased: it is retired to ``failed`` here,
        the same terminal outcome an explicit :meth:`fail` call would reach, so a crashed worker cannot keep a
        poison item cycling through the queue forever.
        """
        if count <= 0:
            raise ValueError("count must be positive")
        owner_ref = owner or self._owner
        now_ms = self._clock_ms()
        leased: list[WorkItem] = []
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE work_item SET state = 'failed', lease_owner = NULL, lease_token = NULL, "
                "lease_expires_ms = NULL, last_error = COALESCE(last_error, 'lease expired after max_attempts'), "
                "updated_at = ? "
                "WHERE stage = ? AND state = 'leased' AND lease_expires_ms <= ? AND attempts >= max_attempts",
                (self._now().isoformat(), stage, now_ms),
            )
            candidates = self.conn.execute(
                "SELECT job_id FROM work_item WHERE stage = ? AND attempts < max_attempts AND ("
                "  (state = 'pending' AND not_before_ms <= ?)"
                "  OR (state = 'leased' AND lease_expires_ms <= ?)"
                ") ORDER BY priority DESC, not_before_ms, created_at LIMIT ?",
                (stage, now_ms, now_ms, count),
            ).fetchall()
            for (job_id,) in candidates:
                token = secrets.token_hex(16)
                cur = self.conn.execute(
                    "UPDATE work_item SET state = 'leased', lease_owner = ?, lease_token = ?, lease_expires_ms = ?, "
                    "attempts = attempts + 1, updated_at = ? "
                    "WHERE job_id = ? AND state IN ('pending', 'leased')",
                    (owner_ref, token, now_ms + lease_ms, self._now().isoformat(), job_id),
                )
                if cur.rowcount == 1:
                    row = self.items.get(job_id)
                    if row is not None:
                        leased.append(row)
        return leased

    def extend(self, job_id: str, lease_token: str, *, lease_ms: int = DEFAULT_LEASE_MS) -> WorkItem:
        """Extend a held lease. Raises :class:`LeaseError` if ``lease_token`` is no longer (or never was) current."""
        now_ms = self._clock_ms()
        with transaction(self.conn):
            cur = self.conn.execute(
                "UPDATE work_item SET lease_expires_ms = ?, updated_at = ? "
                "WHERE job_id = ? AND state = 'leased' AND lease_token = ?",
                (now_ms + lease_ms, self._now().isoformat(), job_id, lease_token),
            )
            if cur.rowcount != 1:
                raise LeaseError(f"job {job_id} is not held under lease {lease_token!r}")
            row = self.items.get(job_id)
        assert row is not None  # noqa: S101 - just updated inside the same transaction
        return row

    def complete(self, job_id: str, lease_token: str, *, artifacts: Mapping[str, str] | None = None) -> WorkOutput:
        """Atomically write the artifact manifest and mark the item done. The manifest is never orphaned or partial."""
        now = self._now()
        with transaction(self.conn):
            self._require_leased(job_id, lease_token)
            output = WorkOutput(
                manifest_id=new_id("man"), job_id=job_id, artifacts=dict(artifacts or {}), created_at=now
            )
            self.outputs.insert(output)
            cur = self.conn.execute(
                "UPDATE work_item SET state = 'done', lease_owner = NULL, lease_token = NULL, lease_expires_ms = NULL, "
                "output_manifest_id = ?, last_error = NULL, updated_at = ? "
                "WHERE job_id = ? AND state = 'leased' AND lease_token = ?",
                (output.manifest_id, now.isoformat(), job_id, lease_token),
            )
            if cur.rowcount != 1:
                raise LeaseError(f"job {job_id} is not held under lease {lease_token!r}")
        return output

    def fail(self, job_id: str, lease_token: str, *, error: str) -> WorkItem:
        """Record a failed attempt: retry with backoff below ``max_attempts``, else terminal ``failed``.

        A poison item (``failed``) is never leased again, so it can never block the rest of the queue.
        """
        now = self._now()
        with transaction(self.conn):
            item = self._require_leased(job_id, lease_token)
            if item.attempts >= item.max_attempts:
                new_state, not_before_ms = WorkItemState.FAILED, item.not_before_ms
            else:
                new_state = WorkItemState.PENDING
                not_before_ms = self._clock_ms() + backoff_ms(item.attempts)
            cur = self.conn.execute(
                "UPDATE work_item SET state = ?, lease_owner = NULL, lease_token = NULL, lease_expires_ms = NULL, "
                "not_before_ms = ?, last_error = ?, updated_at = ? "
                "WHERE job_id = ? AND state = 'leased' AND lease_token = ?",
                (new_state.value, not_before_ms, error[:2000], now.isoformat(), job_id, lease_token),
            )
            if cur.rowcount != 1:
                raise LeaseError(f"job {job_id} is not held under lease {lease_token!r}")
            row = self.items.get(job_id)
        assert row is not None  # noqa: S101 - just updated inside the same transaction
        return row

    def _require_leased(self, job_id: str, lease_token: str) -> WorkItem:
        item = self.items.get(job_id)
        if item is None:
            raise LeaseError(f"unknown job {job_id}")
        if item.state is not WorkItemState.LEASED or item.lease_token != lease_token:
            raise LeaseError(f"job {job_id} is not held under lease {lease_token!r}")
        return item
