"""Owner review sheets for the gold sets (T-P3-02 math, T-P3-03 layout).

The verify tools record one decision per CLI call, which is slow for 300 equations. A *review sheet* is a CSV the
owner fills in a spreadsheet: the tool exports it with every decision column **blank** (an agent never pre-fills a
decision), and imports it back with strict validation. The whole sheet is rejected on any bad row, so a typo can
never record half a review.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

__all__ = ["DECISIONS", "DECISION_COLUMNS", "SheetDecision", "SheetError", "read_sheet_decisions", "write_review_sheet"]

DECISIONS: Final = ("accept", "correct", "reject")
DECISION_COLUMNS: Final = ("decision", "corrected", "note")


class SheetError(ValueError):
    """The sheet cannot be imported; nothing from it was recorded."""


@dataclass(frozen=True, slots=True)
class SheetDecision:
    sample_id: str
    decision: str
    corrected: str
    note: str


def write_review_sheet(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    """Write ``rows`` (context columns, ``sample_id`` first) plus blank decision columns. UTF-8 with BOM, so
    spreadsheet apps open umlauts and LaTeX correctly."""
    context = list(rows[0].keys()) if rows else ["sample_id"]
    if context[0] != "sample_id":
        raise ValueError("the first column must be sample_id")
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow([*context, *DECISION_COLUMNS])
        for row in rows:
            writer.writerow([*(row.get(column, "") for column in context), *("" for _ in DECISION_COLUMNS)])


def read_sheet_decisions(path: Path) -> list[SheetDecision]:
    """Return the decided rows (blank ``decision`` rows are skipped). Raises :class:`SheetError` on an unknown
    decision, a duplicate sample id, or missing columns."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = {"sample_id", *DECISION_COLUMNS} - set(reader.fieldnames or [])
        if missing:
            raise SheetError(f"missing columns: {', '.join(sorted(missing))}")
        decided: list[SheetDecision] = []
        seen: set[str] = set()
        for line, row in enumerate(reader, start=2):
            sample_id = (row.get("sample_id") or "").strip()
            if sample_id in seen:
                raise SheetError(f"line {line}: duplicate sample id {sample_id}")
            seen.add(sample_id)
            decision = (row.get("decision") or "").strip().casefold()
            if not decision:
                continue
            if decision not in DECISIONS:
                raise SheetError(f"line {line}: unknown decision {decision!r} (use accept, correct or reject)")
            decided.append(
                SheetDecision(
                    sample_id, decision, (row.get("corrected") or "").strip(), (row.get("note") or "").strip()
                )
            )
    return decided
