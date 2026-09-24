"""Typed repositories: validated pydantic records in, validated records out (T-P1-06).

Columns are the model's field names. Lists and dicts are stored as JSON text, booleans as 0/1, enums as their values
and timestamps as ISO-8601 UTC strings. Records are validated on write (they are models) and again on read.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, get_args, get_origin

from pydantic import BaseModel

_IDENT_OK = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")


def _ident(name: str) -> str:
    if not name or not set(name) <= _IDENT_OK or name[0].isdigit():
        raise ValueError(f"unsafe SQL identifier {name!r}")
    return name


def _is_json_field(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin in (list, dict, tuple):
        return True
    return any(_is_json_field(a) for a in get_args(annotation) if a is not type(None))


def _is_bool_field(annotation: Any) -> bool:
    return annotation is bool


@dataclass(frozen=True)
class TableSpec[M: BaseModel]:
    table: str
    model: type[M]
    pk: tuple[str, ...]

    @property
    def columns(self) -> tuple[str, ...]:
        return tuple(self.model.model_fields)

    @property
    def json_columns(self) -> frozenset[str]:
        return frozenset(n for n, f in self.model.model_fields.items() if _is_json_field(f.annotation))

    @property
    def bool_columns(self) -> frozenset[str]:
        return frozenset(n for n, f in self.model.model_fields.items() if _is_bool_field(f.annotation))


class Repository[M: BaseModel]:
    """CRUD-light access to one table. Deletion is deliberately not offered (no failure path deletes knowledge)."""

    def __init__(self, conn: sqlite3.Connection, spec: TableSpec[M]) -> None:
        self.conn = conn
        self.spec = spec
        self._table = _ident(spec.table)
        self._cols = tuple(_ident(c) for c in spec.columns)
        for c in spec.pk:
            _ident(c)
        self._check_table()

    def _check_table(self) -> None:
        present = {row[1] for row in self.conn.execute(f"PRAGMA table_info({self._table})")}
        if not present:
            raise LookupError(f"table {self._table} does not exist (run migrations)")
        missing = set(self._cols) - present
        if missing:
            raise LookupError(f"table {self._table} lacks columns for model fields {sorted(missing)}")

    # -- mapping ----------------------------------------------------------------------------------------------------

    def _to_row(self, obj: M) -> dict[str, Any]:
        data = obj.model_dump(mode="json")
        for c in self.spec.json_columns:
            data[c] = json.dumps(data[c], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return data

    def _from_row(self, row: Iterable[Any], names: Iterable[str]) -> M:
        data = dict(zip(names, row, strict=True))
        for c in self.spec.json_columns:
            if data.get(c) is not None:
                data[c] = json.loads(data[c])
        for c in self.spec.bool_columns:
            if data.get(c) is not None:
                data[c] = bool(data[c])
        # Values come from STRICT tables written by this class; lax mode only converts JSON/ISO representations back.
        return self.spec.model.model_validate(data, strict=False)

    # -- operations -------------------------------------------------------------------------------------------------

    def insert(self, obj: M) -> None:
        if not isinstance(obj, self.spec.model):
            raise TypeError(f"expected {self.spec.model.__name__}, got {type(obj).__name__}")
        row = self._to_row(obj)
        cols = ", ".join(self._cols)
        params = ", ".join(f":{c}" for c in self._cols)
        self.conn.execute(f"INSERT INTO {self._table} ({cols}) VALUES ({params})", row)  # noqa: S608

    def upsert(self, obj: M) -> None:
        """Insert, or update every non-key column of the existing row with the same primary key."""
        if not self.spec.pk:
            raise TypeError(f"{self._table} has no natural primary key; use insert")
        row = self._to_row(obj)
        cols = ", ".join(self._cols)
        params = ", ".join(f":{c}" for c in self._cols)
        updates = ", ".join(f"{c} = excluded.{c}" for c in self._cols if c not in self.spec.pk)
        conflict = ", ".join(self.spec.pk)
        sql = f"INSERT INTO {self._table} ({cols}) VALUES ({params}) ON CONFLICT ({conflict}) DO UPDATE SET {updates}"  # noqa: S608
        self.conn.execute(sql, row)

    def get(self, *key: Any) -> M | None:
        if len(key) != len(self.spec.pk) or not self.spec.pk:
            raise TypeError(f"{self._table} key is {self.spec.pk}, got {len(key)} value(s)")
        where = " AND ".join(f"{c} = ?" for c in self.spec.pk)
        cur = self.conn.execute(f"SELECT {', '.join(self._cols)} FROM {self._table} WHERE {where}", key)  # noqa: S608
        row = cur.fetchone()
        return None if row is None else self._from_row(row, self._cols)

    def find(
        self, where: Mapping[str, Any] | None = None, *, order_by: str | None = None, limit: int | None = None
    ) -> list[M]:
        clause, params = self._where(where)
        sql = f"SELECT {', '.join(self._cols)} FROM {self._table}{clause}"  # noqa: S608
        if order_by is not None:
            sql += f" ORDER BY {_ident(order_by)}"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        return [self._from_row(r, self._cols) for r in self.conn.execute(sql, params)]

    def count(self, where: Mapping[str, Any] | None = None) -> int:
        clause, params = self._where(where)
        return int(self.conn.execute(f"SELECT COUNT(*) FROM {self._table}{clause}", params).fetchone()[0])  # noqa: S608

    def _where(self, where: Mapping[str, Any] | None) -> tuple[str, list[Any]]:
        if not where:
            return "", []
        parts, params = [], []
        for k, v in where.items():
            if _ident(k) not in self._cols:
                raise KeyError(f"{self._table} has no column {k!r}")
            if v is None:
                parts.append(f"{k} IS NULL")
            else:
                parts.append(f"{k} = ?")
                params.append(v.value if hasattr(v, "value") else v)
        return " WHERE " + " AND ".join(parts), params
