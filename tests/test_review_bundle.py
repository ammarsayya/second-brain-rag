"""Unified Phase 3 owner review bundle: checks, proposals, validation, ledger and gold-log export (no corpus)."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from tools import review_bundle as tool

from sbr.eval.review_bundle import (
    DECISIONS_SCHEMA,
    ReviewError,
    ReviewLedger,
    attach_proposals,
    double_check_items,
    gold_log_rows,
    layout_items,
    make_bundle,
    math_items,
    merge_paragraph_lines,
    pptx_items,
    pptx_rows_from_report,
    progress,
    taxonomy_items,
    validate_decisions,
)
from sbr.eval.review_html import render_html

M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
T0 = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


def omml(text: str) -> bytes:
    return f'<m:oMath xmlns:m="{M}"><m:r><m:t>{text}</m:t></m:r></m:oMath>'.encode()


LAYOUT = {
    "samples": [
        {
            "sample_id": "layout-001",
            "bucket": "multi_column",
            "relpath": "Mechanical\\skript.pdf",
            "page": 3,
            "gold": {
                "blocks": [
                    {"kind": "heading", "reading_order": 0, "text": "2 Regelkreis"},
                    {"kind": "paragraph", "reading_order": 1, "text": "Der Regelkreis be-"},
                    {"kind": "paragraph", "reading_order": 2, "text": "steht aus Strecke und Regler, y = G u."},
                    {"kind": "header_footer", "reading_order": 3, "text": "12"},
                ],
                "tables": [[["a", "b"], ["c"]]],
                "figures": [],
            },
        },
        {
            "sample_id": "layout-002",
            "bucket": "plain_text_control",
            "relpath": "Bewerbung\\Lebenslauf.pdf",
            "page": 1,
            "gold": {"blocks": [], "tables": [], "figures": []},
        },
    ]
}
MATH = {
    "samples": [
        {"sample_id": "math-001", "source_kind": "omml_exact", "source_group": "omml_exact", "latex": "x",
         "difficulty_tag": "inline_simple", "relpath": "a.docx", "crop": {"path": "c\\math-001.xml"}},
        {"sample_id": "math-002", "source_kind": "omml_exact", "source_group": "omml_exact", "latex": "L_{\\max}",
         "difficulty_tag": "inline_simple", "relpath": "a.docx", "crop": {"path": "c\\math-002.xml"}},
        {"sample_id": "math-003", "source_kind": None, "source_group": "pdf_native", "latex": None,
         "difficulty_tag": "display_simple", "relpath": "b.pdf", "status": "pending_ai_draft",
         "crop": {"path": "c\\math-003.pdf", "representation": "cropped_pdf"}},
    ]
}  # fmt: skip
CROPS = {"c\\math-001.xml": omml("x"), "c\\math-002.xml": omml("Umin")}
REPORT = """# x

## PPTX review sample (50 of 497, seed 1)

| relpath | slide | part | # | LaTeX | exact |
|---|---|---|---|---|---|
| Deck.pptx | 18 | slide18.xml | 2 | `f=min\\left( -ln\\left( x \\right) \\right)` | True |
| Deck.pptx | 37 | slide37.xml | 27 | `\\{P\\}\\rightarrow\\{Term~nach~Zuweisungen\\}` | True |
| Deck.pptx | 42 | slide42.xml | 25 | `\\leq` | True |
"""
TAXONOMY = {
    "concepts": [
        {"concept_id": "root", "label_de": "Wurzel", "label_en": "Root", "narrower": ["leaf", "leaf2"]},
        {"concept_id": "leaf", "label_de": "Programmierung", "label_en": "Leaf", "broader": ["root"]},
        {"concept_id": "leaf2", "label_de": "Systemprogrammierung", "label_en": "Leaves", "broader": ["root"]},
    ]
}
COURSES = {"courses": [{"course_id": "C-1", "name": "Kurs", "domains": ["root", "leaf"]}]}


def bundle() -> dict[str, Any]:
    layout, withheld = layout_items(LAYOUT, {})
    math, _ = math_items(MATH, {}, read_crop=CROPS.get)
    pptx, _ = pptx_items(pptx_rows_from_report(REPORT))
    return make_bundle(
        [*layout, *math, *double_check_items(math), *pptx, *taxonomy_items(TAXONOMY, COURSES)],
        withheld={"layout": withheld},
    )


def items(b: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {i["item_id"]: i for i in b["items"]}


def decisions(b: dict[str, Any], *rows: dict[str, Any]) -> dict[str, Any]:
    return {"schema": DECISIONS_SCHEMA, "bundle_fingerprint": b["fingerprint"], "decisions": list(rows)}


# -- building ----------------------------------------------------------------------------------------------------


def test_restricted_paths_never_enter_the_bundle_only_their_count() -> None:
    b = bundle()
    assert "layout:layout-002" not in items(b)
    assert b["withheld_for_sensitivity"] == {"layout": 1}
    assert "Lebenslauf" not in json.dumps(b, ensure_ascii=False)


def test_layout_checks_and_paragraph_merge_proposal_keep_the_original() -> None:
    item = items(bundle())["layout:layout-001"]
    checks = {f["check"] for f in item["flags"]}
    assert {"column_heuristic", "ragged_table", "math_not_annotated", "line_level_paragraphs"} <= checks
    assert item["priority"] == 0  # risky bucket first
    assert len(item["original"]["gold"]["blocks"]) == 4  # original untouched
    merged = item["proposals"][0]["value"]
    assert [b["kind"] for b in merged] == ["heading", "paragraph", "header_footer"]
    assert merged[1]["text"] == "Der Regelkreis besteht aus Strecke und Regler, y = G u."
    assert item["proposals"][0]["origin"].startswith("machine:")


def test_merge_keeps_non_hyphen_breaks_as_spaces() -> None:
    lines = ["a b", "Regel-", "kreis", "Sensor-", "Aktor-Bus", "x-y"]
    blocks = [{"kind": "paragraph", "reading_order": i, "text": t} for i, t in enumerate(lines)]
    assert merge_paragraph_lines(blocks)[0]["text"] == "a b Regelkreis Sensor-Aktor-Bus x-y"


def test_math_checks_flag_mispairing_and_keep_pending_entries_unacceptable() -> None:
    by_id = items(bundle())
    assert {f["check"] for f in by_id["math:math-001"]["flags"]} == {"crop_agrees"}
    wrong = by_id["math:math-002"]
    assert "mispaired" in {f["check"] for f in wrong["flags"]} and wrong["priority"] == 0
    assert wrong["proposals"][0]["value"] == "Umin" and wrong["original"]["latex"] == "L_{\\max}"
    pending = by_id["math:math-003"]
    assert "accept" not in pending["allowed_decisions"]
    assert {f["check"] for f in pending["flags"]} == {"pending_transcription"}


def test_double_check_sample_is_ten_percent_with_latex_and_hides_first_pass() -> None:
    b = bundle()
    dc = [i for i in b["items"] if i["kind"] == "math_double_check"]
    assert len(dc) == 0  # round(3 * 0.1) == 0
    math, _ = math_items(
        {"samples": [dict(MATH["samples"][0], sample_id=f"math-{n:03d}") for n in range(300)]},
        {"math-005": {"decision": "accept"}},
        read_crop=lambda _: omml("x"),
    )
    picked = double_check_items(math)
    assert len(picked) == 30 and all(i["prior_decision"] is None for i in picked)
    assert picked == double_check_items(math)  # deterministic


def test_pptx_rows_parse_and_proposals_follow_converter_rules() -> None:
    by_id = {i["original"]["latex"]: i for i in items(bundle()).values() if i["kind"] == "pptx"}
    assert len(by_id) == 3
    fn = by_id["f=min\\left( -ln\\left( x \\right) \\right)"]
    assert fn["proposals"][0]["value"] == "f=\\min \\left( -\\ln \\left( x \\right) \\right)"
    prose = by_id["\\{P\\}\\rightarrow\\{Term~nach~Zuweisungen\\}"]
    assert "\\text{Term nach Zuweisungen}" in prose["proposals"][0]["value"]
    assert "fragment" in {f["check"] for f in by_id["\\leq"]["flags"]}


def test_taxonomy_items_flag_structure_and_have_an_explicit_gate() -> None:
    by_id = items(bundle())
    course = {f["check"] for f in by_id["taxonomy:course:C-1"]["flags"]}
    assert course == {"multiple_domains", "non_leaf_mapping"}
    assert "similar_label" in {f["check"] for f in by_id["taxonomy:concept:leaf"]["flags"]}
    assert by_id["taxonomy:approve-v0"]["allowed_decisions"] == ["accept", "reject", "uncertain"]


def test_ai_proposals_attach_with_their_own_origin_and_report_unknown_targets() -> None:
    tax = taxonomy_items(TAXONOMY, COURSES)
    notes = {
        "origin": "ai:claude-review@2026-11-04",
        "proposals": [
            {"target": "taxonomy:course:C-1", "proposal_id": "p", "field": "domains", "value": ["leaf"],
             "confidence": "low", "rationale": "r"},
            {"target": "taxonomy:course:NOPE", "proposal_id": "q", "field": "domains", "value": [],
             "confidence": "low", "rationale": "r"},
        ],
    }  # fmt: skip
    assert attach_proposals(tax, notes) == ["taxonomy:course:NOPE"]
    course = next(i for i in tax if i["item_id"] == "taxonomy:course:C-1")
    assert course["proposals"][0]["origin"] == "ai:claude-review@2026-11-04"
    assert course["original"]["domains"] == ["root", "leaf"]


def test_bundle_is_deterministic_and_carries_no_decisions() -> None:
    a, b = bundle(), bundle()
    assert a == b and a["fingerprint"] == b["fingerprint"]
    text = json.dumps(a)
    assert '"decision"' not in text  # no item is pre-decided
    with pytest.raises(ReviewError, match="duplicate"):
        make_bundle([*a["items"], a["items"][0]])


# -- decisions ---------------------------------------------------------------------------------------------------


def test_validation_is_all_or_nothing() -> None:
    b = bundle()
    good = {"item_id": "math:math-001", "decision": "accept"}
    for bad, match in [
        ({"item_id": "math:math-003", "decision": "accept"}, "not allowed"),
        ({"item_id": "math:nope", "decision": "accept"}, "unknown item"),
        ({"item_id": "math:math-002", "decision": "correct"}, "needs the corrected value"),
        ({"item_id": "math:math-002", "decision": "accept", "corrected": "x"}, "only valid with 'correct'"),
        ({"item_id": "math:math-002", "decision": "accept", "proposal_id": "native_latex"}, "is a 'correct'"),
        ({"item_id": "math:math-002", "decision": "correct", "proposal_id": "nope"}, "unknown proposal"),
        ({"item_id": "math:math-001", "decision": "reject"}, "duplicate decision"),
    ]:
        with pytest.raises(ReviewError, match=match):
            validate_decisions(b, decisions(b, good, bad))
    stale = decisions(b, good)
    stale["bundle_fingerprint"] = "sha256:" + "0" * 64
    with pytest.raises(ReviewError, match="different bundle"):
        validate_decisions(b, stale)


def test_adopting_a_proposal_records_its_value() -> None:
    b = bundle()
    (d,) = validate_decisions(b, decisions(b, {"item_id": "math:math-002", "decision": "correct",
                                               "proposal_id": "native_latex"}))  # fmt: skip
    assert (d.decision, d.corrected, d.proposal_id) == ("correct", "Umin", "native_latex")


def test_ledger_status_transitions_duplicates_and_supersede(tmp_path: Path) -> None:
    b = bundle()
    ledger = ReviewLedger(tmp_path / "ledger.jsonl")
    first = validate_decisions(b, decisions(b, {"item_id": "math:math-001", "decision": "uncertain"}))
    with pytest.raises(ReviewError, match="user:"):
        ledger.record(b, first, reviewer="owner", decided_at=T0)
    with pytest.raises(ReviewError, match="user:"):
        ledger.record(b, first, reviewer="model:claude/x@1", decided_at=T0)
    assert ledger.record(b, first, reviewer="user:owner", decided_at=T0) == {"recorded": 1, "unchanged": 0}
    assert ledger.record(b, first, reviewer="user:owner", decided_at=T0) == {"recorded": 0, "unchanged": 1}
    changed = validate_decisions(b, decisions(b, {"item_id": "math:math-001", "decision": "accept"}))
    with pytest.raises(ReviewError, match="already decided differently"):
        ledger.record(b, changed, reviewer="user:owner", decided_at=T0)
    assert ledger.record(b, changed, reviewer="user:owner", decided_at=T0, allow_supersede=True)["recorded"] == 1
    records = ledger.records()
    assert [r["decision"] for r in records] == ["uncertain", "accept"]  # history kept
    assert records[1]["supersedes"] == records[0]["record_id"]
    assert progress(b, ledger)["math"]["accept"] == 1


def test_ledger_records_are_deterministic(tmp_path: Path) -> None:
    b = bundle()
    one, two = ReviewLedger(tmp_path / "a.jsonl"), ReviewLedger(tmp_path / "b.jsonl")
    rows = validate_decisions(b, decisions(b, {"item_id": "math:math-001", "decision": "accept", "note": "ok"}))
    one.record(b, rows, reviewer="user:owner", decided_at=T0)
    two.record(b, rows, reviewer="user:owner", decided_at=T0)
    assert one.path.read_text() == two.path.read_text()


def test_gold_log_rows_match_the_existing_verify_tool_format(tmp_path: Path) -> None:
    b = bundle()
    ledger = ReviewLedger(tmp_path / "ledger.jsonl")
    rows = validate_decisions(
        b,
        decisions(
            b,
            {"item_id": "math:math-002", "decision": "correct", "corrected": r"U_{\min}", "note": "crop"},
            {"item_id": "math:math-001", "decision": "uncertain"},
            {"item_id": "layout:layout-001", "decision": "correct", "proposal_id": "merge_paragraph_lines"},
        ),
    )
    ledger.record(b, rows, reviewer="user:owner", decided_at=T0)
    math = gold_log_rows(ledger, "math")
    assert set(math) == {"math-002"}  # uncertain stays pending in the existing log
    assert math["math-002"]["corrected_latex"] == r"U_{\min}" and math["math-002"]["verified_at"] == T0.isoformat()
    layout = gold_log_rows(ledger, "layout")
    assert layout["layout-001"]["corrected_annotation"][0]["kind"] == "heading"


def test_html_embeds_the_bundle_safely_and_forbids_network() -> None:
    b = bundle()
    hostile = copy.deepcopy(b)
    hostile["items"][0]["title"] = "</script><script>alert(1)</script>"
    page = render_html(hostile)
    assert "connect-src 'none'" in page and "default-src 'none'" in page
    assert "</script><script>alert(1)" not in page
    assert b["fingerprint"] in render_html(b)


# -- tool --------------------------------------------------------------------------------------------------------


def test_import_refuses_curation_approval_without_an_explicit_accept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    b = bundle()
    out = tmp_path / "review"
    out.mkdir()
    (out / "bundle.json").write_text(json.dumps(b), encoding="utf-8")
    dec = tmp_path / "d.json"
    dec.write_text(json.dumps(decisions(b, {"item_id": "taxonomy:approve-v0", "decision": "uncertain"})))
    approvals = tmp_path / "approvals.yaml"
    approvals.write_text("[]\n", encoding="utf-8")
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    monkeypatch.setattr(tool, "APPROVALS", Path("approvals.yaml"))
    import argparse

    args = argparse.Namespace(out=out, decisions=dec, reviewer="user:owner", allow_supersede=False,
                              apply_gold_logs=False, write_curation_approval=True)  # fmt: skip
    with pytest.raises(ReviewError, match="no 'accept'"):
        tool.do_import(args, None)
    assert approvals.read_text() == "[]\n"
    args.reviewer = "user:someone"
    with pytest.raises(ReviewError, match="only user:owner"):
        tool.do_import(args, None)


def test_build_then_import_writes_logs_the_existing_verify_tools_can_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import argparse

    from ruamel.yaml import YAML
    from tools import gold_verify_math

    root = tmp_path / "repo"
    (root / "c").mkdir(parents=True)
    for name, data in CROPS.items():
        (root / name.replace("\\", "/")).write_bytes(data)
    yaml = YAML()
    layout, math = tmp_path / "layout.yaml", tmp_path / "math.yaml"
    with layout.open("w") as f:
        yaml.dump(LAYOUT, f)
    with math.open("w") as f:
        yaml.dump(MATH, f)
    report = tmp_path / "report.md"
    report.write_text(REPORT, encoding="utf-8")
    monkeypatch.setattr(tool, "ROOT", root)
    monkeypatch.setattr(tool, "LAYOUT_LOG", tmp_path / "layout_verification.yaml")
    monkeypatch.setattr(tool, "MATH_LOG", tmp_path / "math_verification.yaml")
    out = tmp_path / "review"
    args = argparse.Namespace(out=out, layout=layout, math=math, pptx_report=report)
    built = tool.build(args, None)
    assert built["sections"]["layout"] == 1 and built["sections"]["math"] == 3 and built["sections"]["pptx"] == 3
    assert built["withheld_for_sensitivity"] == {"layout": 1}
    assert (out / "index.html").read_text(encoding="utf-8").count(built["fingerprint"]) >= 1

    b = json.loads((out / "bundle.json").read_text(encoding="utf-8"))
    dec = tmp_path / "review_decisions.json"
    adopt = {"item_id": "math:math-002", "decision": "correct", "proposal_id": "native_latex"}
    reject = {"item_id": "math:math-003", "decision": "reject", "note": "illegible"}
    dec.write_text(json.dumps(decisions(b, adopt, reject)))
    imp = argparse.Namespace(out=out, decisions=dec, reviewer="user:owner", allow_supersede=False,
                             apply_gold_logs=True, write_curation_approval=False)  # fmt: skip
    result = tool.do_import(imp, None)
    assert result["recorded"] == 2 and result["math_log_rows"] == 2
    logged = gold_verify_math._existing_decisions(tmp_path / "math_verification.yaml")
    assert logged["math-002"]["corrected_latex"] == "Umin" and logged["math-003"]["decision"] == "reject"
    assert tool.do_import(imp, None)["recorded"] == 0  # identical re-import is a no-op


def test_ledger_with_config_refuses_to_write_into_a_source_root(make_config: Any) -> None:
    from sbr.safety import SourceWriteError

    config = make_config()
    b = bundle()
    target = Path(config.roots.sources[0].path) / "review_ledger.jsonl"
    rows = validate_decisions(b, decisions(b, {"item_id": "math:math-001", "decision": "accept"}))
    with pytest.raises(SourceWriteError):
        ReviewLedger(target, config).record(b, rows, reviewer="user:owner", decided_at=T0)
    assert not target.exists()
