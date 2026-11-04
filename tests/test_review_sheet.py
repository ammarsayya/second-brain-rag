"""Owner review sheets: exported with blank decisions, imported with strict validation (T-P3-02/T-P3-03)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from sbr.eval.review_sheet import DECISION_COLUMNS, SheetError, read_sheet_decisions, write_review_sheet


def test_exported_sheet_has_blank_decision_columns_and_round_trips(tmp_path: Path) -> None:
    sheet = tmp_path / "review.csv"
    write_review_sheet(sheet, [{"sample_id": "math-001", "latex": "a=b, c"}, {"sample_id": "math-002", "latex": "x"}])
    text = sheet.read_text(encoding="utf-8-sig")
    assert text.splitlines()[0] == "sample_id,latex," + ",".join(DECISION_COLUMNS)
    assert read_sheet_decisions(sheet) == []  # nothing decided yet: nothing is recorded


def _fill(sheet: Path, filled: dict[str, tuple[str, str, str]], extra: str = "") -> None:
    """Fill the decision cells of the exported sheet like a spreadsheet would."""
    with sheet.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream))
    for row in rows[1:]:
        if row[0] in filled:
            row[-3:] = filled[row[0]]
    with sheet.open("w", encoding="utf-8-sig", newline="") as stream:
        csv.writer(stream).writerows(rows)
        stream.write(extra)


def test_filled_rows_are_read_and_blank_rows_skipped(tmp_path: Path) -> None:
    sheet = tmp_path / "review.csv"
    write_review_sheet(sheet, [{"sample_id": "a"}, {"sample_id": "b"}, {"sample_id": "c"}])
    _fill(sheet, {"a": ("Accept", "", "looks right"), "c": ("correct", "x^{2}", "")})
    decisions = read_sheet_decisions(sheet)
    assert [(d.sample_id, d.decision, d.corrected, d.note) for d in decisions] == [
        ("a", "accept", "", "looks right"),
        ("c", "correct", "x^{2}", ""),
    ]


def test_an_unknown_decision_rejects_the_whole_sheet(tmp_path: Path) -> None:
    sheet = tmp_path / "review.csv"
    write_review_sheet(sheet, [{"sample_id": "a"}, {"sample_id": "b"}])
    _fill(sheet, {"a": ("accept", "", ""), "b": ("maybe", "", "")})
    with pytest.raises(SheetError, match="unknown decision"):
        read_sheet_decisions(sheet)


def test_a_duplicate_sample_id_rejects_the_whole_sheet(tmp_path: Path) -> None:
    sheet = tmp_path / "review.csv"
    write_review_sheet(sheet, [{"sample_id": "a"}])
    _fill(sheet, {"a": ("accept", "", "")}, extra="a,reject,,\r\n")
    with pytest.raises(SheetError, match="duplicate"):
        read_sheet_decisions(sheet)
