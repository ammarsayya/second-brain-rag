"""T-P3-02 review sheet: computed checks flag mis-paired candidates; decisions import all-or-nothing."""

from __future__ import annotations

import argparse
import csv
from collections.abc import Callable
from pathlib import Path

import pytest
from tools import gold_verify_math

from sbr.config import SbrConfig
from sbr.eval.review_sheet import SheetError

M = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def _gold(root: Path) -> Path:
    crops = root / "eval" / "gold" / "math" / "crops"
    crops.mkdir(parents=True)
    for name, text in (("math-001", "x"), ("math-002", "Umin")):
        (crops / f"{name}.omml.xml").write_text(
            f'<m:oMath xmlns:m="{M}"><m:r><m:t>{text}</m:t></m:r></m:oMath>', encoding="utf-8"
        )
    sample = root / "eval" / "gold" / "math_sample.yaml"
    crop = "eval\\\\gold\\\\math\\\\crops\\\\"
    sample.write_text(
        "samples:\n"
        f"- {{sample_id: math-001, source_kind: omml_exact, latex: 'x', crop: {{path: '{crop}math-001.omml.xml'}}}}\n"
        "- {sample_id: math-002, source_kind: omml_exact, latex: 'L_{\\max}',\n"
        f"   crop: {{path: '{crop}math-002.omml.xml'}}}}\n"
        "- {sample_id: math-003, source_kind: pdf_native, latex: null, crop: {path: 'x.pdf'}}\n",
        encoding="utf-8",
    )
    return sample


def _args(sample: Path, tmp_path: Path, **mode: object) -> argparse.Namespace:
    base: dict[str, object] = {"export_sheet": None, "record_sheet": None, "prepare": False, "record": None}
    base.update(mode)
    return argparse.Namespace(sample=sample, decisions=tmp_path / "decisions.yaml", note="", decision=None, **base)


def _fill(sheet: Path, filled: dict[str, tuple[str, str, str]]) -> None:
    with sheet.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream))
    for row in rows[1:]:
        if row[0] in filled:
            row[-3:] = filled[row[0]]
    with sheet.open("w", encoding="utf-8-sig", newline="") as stream:
        csv.writer(stream).writerows(rows)


def test_export_flags_mispaired_and_pending_and_leaves_decisions_blank(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    config = make_config()
    sample = _gold(tmp_path / "repo")
    sheet = tmp_path / "math_review.csv"
    result = gold_verify_math._export_sheet(_args(sample, tmp_path, export_sheet=sheet), config)

    assert result["checks"] == {"ok": 1, "mispaired": 1, "pending_ai_draft": 1}
    with sheet.open(encoding="utf-8-sig", newline="") as stream:
        rows = {row["sample_id"]: row for row in csv.DictReader(stream)}
    assert rows["math-002"]["native_latex_from_crop"] == "Umin"
    assert all(row["decision"] == row["corrected"] == row["note"] == "" for row in rows.values())


def test_record_sheet_is_all_or_nothing_and_keeps_pending_drafts_unacceptable(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    config = make_config()
    sample = _gold(tmp_path / "repo")
    sheet = tmp_path / "math_review.csv"
    gold_verify_math._export_sheet(_args(sample, tmp_path, export_sheet=sheet), config)

    _fill(sheet, {"math-001": ("accept", "", ""), "math-003": ("accept", "", "")})
    with pytest.raises(ValueError, match="pending_ai_draft"):
        gold_verify_math._record_sheet(_args(sample, tmp_path, record_sheet=sheet), config)
    assert not (tmp_path / "decisions.yaml").exists()  # nothing recorded from a bad sheet

    _fill(sheet, {"math-002": ("correct", r"U_{\min}", "crop shows U_min"), "math-003": ("reject", "", "")})
    result = gold_verify_math._record_sheet(_args(sample, tmp_path, record_sheet=sheet), config)
    assert result["counts"] == {"accept": 1, "correct": 1, "reject": 1}
    assert "corrected_latex: U_{\\min}" in (tmp_path / "decisions.yaml").read_text(encoding="utf-8")

    _fill(sheet, {"math-001": ("maybe", "", "")})
    with pytest.raises(SheetError):
        gold_verify_math._record_sheet(_args(sample, tmp_path, record_sheet=sheet), config)
