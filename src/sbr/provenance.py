"""Provenance core API (T-P1-07, HC-04, docs/05, PV-1).

* Activities are recorded as ``running`` and finished exactly once (the DB triggers in migration 0002 enforce this).
* Every provenance-bearing write must name a running activity. The database refuses anything else, including raw
  SQL, so "writes without an activity" cannot happen by accident (TS-PROV-1).
* :meth:`ProvenanceStore.record_derived` writes a derived entity together with at least one ``derived_from`` link
  in one transaction (PV-1). An empty derivation is refused before anything is written.
* :meth:`ProvenanceStore.pv1_violations` and :meth:`ProvenanceStore.unresolved_locators` are the integrity queries
  that ``sbr doctor`` and TS-PROV-2 use.

Failure notes store only the exception class, never its message: messages may contain source paths (docs/22 §3).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from sbr.db.connection import transaction
from sbr.db.repository import Repository, _ident
from sbr.ids import UlidGenerator, new_id
from sbr.schemas import Activity, ActivityStatus, DerivationRole, DerivedFrom, Locator


class ProvenanceError(RuntimeError):
    """A write would break a provenance invariant (PV-1, HC-04)."""


def utcnow() -> datetime:
    return datetime.now(UTC)


def params_hash(params: Mapping[str, Any] | None) -> str | None:
    """Stable hash of producer parameters (NFR-04)."""
    if params is None:
        return None
    canonical = json.dumps(params, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class ActivityHandle:
    """Mutable collector for a running activity; outputs added here are recorded when it finishes."""

    activity: Activity
    outputs: list[str] = field(default_factory=list)
    notes: str | None = None

    @property
    def activity_id(self) -> str:
        return self.activity.activity_id


class ProvenanceStore:
    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        clock: Callable[[], datetime] = utcnow,
        ids: UlidGenerator | None = None,
    ) -> None:
        self.conn = conn
        self._clock = clock
        self._ids = ids

    # -- activities -------------------------------------------------------------------------------------------------

    def start_activity(
        self,
        kind: str,
        producer: str,
        producer_version: str,
        agent: str,
        *,
        params: Mapping[str, Any] | None = None,
        run_id: str | None = None,
        inputs: Sequence[str] = (),
    ) -> Activity:
        act = Activity(
            activity_id=new_id("act", self._ids),
            kind=kind,
            producer=producer,
            producer_version=producer_version,
            params_hash=params_hash(params),
            agent=agent,
            run_id=run_id,
            started_at=self._clock(),
            inputs=list(inputs),
        )
        self.conn.execute(
            "INSERT INTO activity (activity_id, kind, producer, producer_version, params_hash, agent, run_id, "
            "started_at, status, inputs, outputs) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, '[]')",
            (
                act.activity_id,
                act.kind,
                act.producer,
                act.producer_version,
                act.params_hash,
                act.agent,
                act.run_id,
                _iso(act.started_at),
                json.dumps(act.inputs),
            ),
        )
        return act

    def finish_activity(
        self,
        activity_id: str,
        status: ActivityStatus,
        *,
        outputs: Sequence[str] = (),
        notes: str | None = None,
    ) -> Activity:
        if status is ActivityStatus.RUNNING:
            raise ProvenanceError("finish_activity needs a terminal status")
        current = self.get_activity(activity_id)
        if current is None:
            raise ProvenanceError(f"unknown activity {activity_id}")
        finished = current.model_copy(
            update={
                "status": status,
                "ended_at": max(self._clock(), current.started_at),
                "outputs": list(outputs),
                "notes": notes,
            }
        )
        Activity.model_validate(finished.model_dump(mode="json"), strict=False)  # re-check invariants
        cur = self.conn.execute(
            "UPDATE activity SET status = ?, ended_at = ?, outputs = ?, notes = ? "
            "WHERE activity_id = ? AND status = 'running'",
            (status.value, _iso(finished.ended_at), json.dumps(list(outputs)), notes, activity_id),
        )
        if cur.rowcount != 1:
            raise ProvenanceError(f"activity {activity_id} is not running")
        return finished

    @contextmanager
    def activity(
        self,
        kind: str,
        producer: str,
        producer_version: str,
        agent: str,
        *,
        params: Mapping[str, Any] | None = None,
        run_id: str | None = None,
        inputs: Sequence[str] = (),
    ) -> Iterator[ActivityHandle]:
        """Run a block as one activity: ``succeeded`` on normal exit, ``failed`` (with the error class) otherwise."""
        handle = ActivityHandle(
            self.start_activity(kind, producer, producer_version, agent, params=params, run_id=run_id, inputs=inputs)
        )
        try:
            yield handle
        except BaseException as exc:
            status = ActivityStatus.CANCELLED if isinstance(exc, KeyboardInterrupt) else ActivityStatus.FAILED
            self.finish_activity(
                handle.activity_id, status, outputs=handle.outputs, notes=f"error:{type(exc).__name__}"
            )
            raise
        self.finish_activity(handle.activity_id, ActivityStatus.SUCCEEDED, outputs=handle.outputs, notes=handle.notes)

    def get_activity(self, activity_id: str) -> Activity | None:
        from sbr.db.registry import ACTIVITY  # local import: registry imports schemas only

        return Repository(self.conn, ACTIVITY).get(activity_id)

    # -- derivation links -------------------------------------------------------------------------------------------

    def link(self, link: DerivedFrom, activity_id: str) -> None:
        self.conn.execute(
            "INSERT INTO derived_from (entity_id, source_entity_id, role, locator, activity_id) VALUES (?, ?, ?, ?, ?)",
            (
                link.entity_id,
                link.source_entity_id,
                link.role.value,
                None if link.locator is None else link.locator.model_dump_json(),
                activity_id,
            ),
        )

    def record_derived[M: BaseModel](
        self, repo: Repository[M], obj: M, entity_id: str, derived_from: Sequence[DerivedFrom]
    ) -> None:
        """Insert ``obj`` and its derivation links atomically. At least one link is required (PV-1)."""
        if not derived_from:
            raise ProvenanceError("PV-1: a derived entity needs at least one derived_from link")
        activity_id = getattr(obj, "activity_id", None)
        if not activity_id:
            raise ProvenanceError("PV-1: a derived entity needs a producing activity_id")
        for d in derived_from:
            if d.entity_id != entity_id:
                raise ProvenanceError(f"derived_from link is for {d.entity_id}, not {entity_id}")
        with transaction(self.conn):
            repo.insert(obj)
            for d in derived_from:
                self.link(d, activity_id)

    def derived_from(self, entity_id: str) -> list[DerivedFrom]:
        rows = self.conn.execute(
            "SELECT entity_id, source_entity_id, role, locator FROM derived_from WHERE entity_id = ? "
            "ORDER BY source_entity_id, role",
            (entity_id,),
        )
        return [
            DerivedFrom(
                entity_id=e,
                source_entity_id=s,
                role=DerivationRole(r),
                locator=None if loc is None else Locator.model_validate_json(loc),
            )
            for e, s, r, loc in rows
        ]

    # -- integrity (PV-1, PV-3 part) --------------------------------------------------------------------------------

    def pv1_violations(self, table: str, id_column: str) -> list[str]:
        """Ids of rows in a derived-entity table that have no derived_from link or no known activity."""
        t, c = _ident(table), _ident(id_column)
        sql = (
            f"SELECT x.{c} FROM {t} AS x "  # noqa: S608 - identifiers validated
            f"LEFT JOIN activity a ON a.activity_id = x.activity_id "
            f"WHERE a.activity_id IS NULL OR NOT EXISTS (SELECT 1 FROM derived_from d WHERE d.entity_id = x.{c}) "
            f"ORDER BY 1"
        )
        return [r[0] for r in self.conn.execute(sql)]

    def unresolved_locators(self) -> list[tuple[str, str]]:
        """(entity_id, blob_id) pairs whose locator points at a blob the registry does not know."""
        rows = self.conn.execute(
            "SELECT d.entity_id, json_extract(d.locator, '$.blob_id') AS b FROM derived_from d "
            "WHERE d.locator IS NOT NULL AND NOT EXISTS (SELECT 1 FROM blob WHERE blob.blob_id = b) ORDER BY 1"
        )
        return [(e, b) for e, b in rows]


def _iso(ts: datetime | None) -> str | None:
    return None if ts is None else ts.astimezone(UTC).isoformat().replace("+00:00", "Z")
