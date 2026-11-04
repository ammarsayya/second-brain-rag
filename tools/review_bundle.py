"""Unified Phase 3 owner review: build the bundle + offline HTML page, import exported decisions, show progress.

  build   Collect every review item that exists on this host into eval/gold/review/{bundle.json,index.html}:
          layout (eval/gold/layout/layout_annotations.yaml), math (eval/gold/math_sample.yaml + crops),
          PPTX math (the 50-equation sample in eval/reports/spike_omml_native.md) and taxonomy (curation/*.yaml).
          Sections whose inputs are missing are reported and skipped; nothing is invented.
  status  Review progress per section, from the ledger.
  import  Validate an exported review_decisions.json against the bundle (all-or-nothing) and append it to the
          ledger eval/gold/review/review_ledger.jsonl. --reviewer is required (user:<name>); it is never inferred.
          --apply-gold-logs also writes layout/math decisions into the existing verify-tool logs.
          --write-curation-approval appends the Taxonomy v0 approval to curation/approvals.yaml, only if the
          ledger holds an explicit 'accept' of item taxonomy:approve-v0.

Everything is local. Opening index.html needs no server; the page makes no network requests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from sbr.config import load_config
from sbr.curation import Approval, ApprovalDecision, append_approval, load_approvals
from sbr.eval.review_bundle import (
    ReviewError,
    ReviewLedger,
    attach_proposals,
    double_check_items,
    gold_log_rows,
    layout_items,
    make_bundle,
    math_items,
    pptx_items,
    pptx_rows_from_report,
    progress,
    read_crop_under,
    taxonomy_items,
    validate_decisions,
)
from sbr.eval.review_html import render_html
from sbr.safety import assert_writable

ROOT = Path(__file__).resolve().parent.parent
REVIEW_DIR = Path("eval/gold/review")
LAYOUT = Path("eval/gold/layout/layout_annotations.yaml")
LAYOUT_LOG = Path("eval/gold/layout/layout_verification.yaml")
MATH = Path("eval/gold/math_sample.yaml")
MATH_LOG = Path("eval/gold/math/math_verification.yaml")
PPTX_REPORT = Path("eval/reports/spike_omml_native.md")
TAXONOMY = Path("curation/taxonomy.yaml")
COURSES = Path("curation/course_map.yaml")
APPROVALS = Path("curation/approvals.yaml")
TAXONOMY_NOTES = Path("eval/reviews/taxonomy_v0_ai_review.yaml")


def _yaml_load(path: Path) -> Any:
    return YAML(typ="safe").load(path.read_text(encoding="utf-8"))


def _log_rows(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return {str(r["sample_id"]): dict(r) for r in (_yaml_load(path) or {}).get("decisions", [])}


def _writable(path: Path, config: Any) -> None:
    if config is not None:
        assert_writable(path.resolve(), config)


_MARK = "SBRREVIEWSPLIT"


def render_mathml(items: list[dict[str, Any]]) -> str:
    """Pre-render LaTeX (originals and LaTeX proposals) to MathML with one local pandoc call, if pandoc exists."""
    pandoc = shutil.which("pandoc")
    if pandoc is None:
        return "LaTeX only (pandoc not installed: no rendered formulas)"
    jobs: list[tuple[dict[str, Any], str, str]] = []
    for item in items:
        if isinstance(item["original"].get("latex"), str):
            jobs.append((item, "original", item["original"]["latex"]))
        jobs += [(item, p["proposal_id"], p["value"]) for p in item["proposals"] if p["field"] == "latex"]
    if not jobs:
        return "no formulas"
    source = "\n\n".join(f"{_MARK}{n}\n\n$${latex}$$" for n, (_, _, latex) in enumerate(jobs))
    proc = subprocess.run(
        [pandoc, "-f", "markdown", "-t", "html5", "--mathml"], input=source, capture_output=True, text=True,
        timeout=600, check=False,
    )  # fmt: skip
    if proc.returncode != 0:
        return f"LaTeX only (pandoc failed: exit {proc.returncode})"
    chunks = re.split(rf"<p>{_MARK}(\d+)</p>", proc.stdout)
    rendered = {int(chunks[i]): chunks[i + 1] for i in range(1, len(chunks) - 1, 2)}
    for n, (item, key, _) in enumerate(jobs):
        match = re.search(r"<math\b.*?</math>", rendered.get(n, ""), re.S)
        if match and not re.search(r"<script|\son\w+=|javascript:", match.group(0), re.I):
            item.setdefault("render", {})[key] = match.group(0)
    version = subprocess.run([pandoc, "--version"], capture_output=True, text=True, check=False).stdout.split("\n")[0]
    return f"MathML pre-rendered by local {version}"


def build(args: argparse.Namespace, config: Any) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    withheld: dict[str, int] = {}
    missing: list[str] = []
    if args.layout.exists():
        layout, n = layout_items(_yaml_load(args.layout), _log_rows(LAYOUT_LOG))
        items += layout
        withheld["layout"] = n
    else:
        missing.append(f"layout ({args.layout})")
    if args.math.exists():
        math, n = math_items(_yaml_load(args.math), _log_rows(MATH_LOG), read_crop=read_crop_under(ROOT))
        items += math + double_check_items(math)
        withheld["math"] = n
    else:
        missing.append(f"math ({args.math})")
    if args.pptx_report.exists():
        pptx, n = pptx_items(pptx_rows_from_report(args.pptx_report.read_text(encoding="utf-8")))
        items += pptx
        withheld["pptx"] = n
    else:
        missing.append(f"pptx ({args.pptx_report})")
    taxonomy = taxonomy_items(_yaml_load(TAXONOMY), _yaml_load(COURSES))
    unattached = attach_proposals(taxonomy, _yaml_load(TAXONOMY_NOTES)) if TAXONOMY_NOTES.exists() else []
    items += taxonomy
    renderer = render_mathml(items)
    bundle = make_bundle(items, withheld={k: v for k, v in withheld.items() if v})
    bundle["renderer"] = renderer
    args.out.mkdir(parents=True, exist_ok=True)
    for name, text in (
        ("bundle.json", json.dumps(bundle, ensure_ascii=False, indent=1, sort_keys=True) + "\n"),
        ("index.html", render_html(bundle)),
    ):
        _writable(args.out / name, config)
        (args.out / name).write_text(text, encoding="utf-8")
    return {
        "bundle": str(args.out / "bundle.json"),
        "page": str(args.out / "index.html"),
        "fingerprint": bundle["fingerprint"],
        "sections": bundle["sections"],
        "withheld_for_sensitivity": bundle["withheld_for_sensitivity"],
        "missing_inputs": missing,
        "renderer": renderer,
        "unattached_proposals": unattached,
    }


def _merge_gold_log(path: Path, header: dict[str, Any], rows: dict[str, dict[str, Any]], *, allow: bool) -> int:
    existing = _log_rows(path)
    conflicts = [
        k
        for k, row in rows.items()
        if k in existing
        and existing[k]["decision"] != row["decision"]
        and existing[k].get("review_record") != row["review_record"]
    ]
    if conflicts and not allow:
        raise ReviewError(f"{path}: different decisions already logged for {', '.join(sorted(conflicts))}")
    existing.update(rows)
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.width = 120
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        yaml.dump({**header, "decisions": [existing[k] for k in sorted(existing)]}, stream)
    return len(rows)


def do_import(args: argparse.Namespace, config: Any) -> dict[str, Any]:
    bundle = json.loads((args.out / "bundle.json").read_text(encoding="utf-8"))
    decisions = validate_decisions(bundle, json.loads(args.decisions.read_text(encoding="utf-8")))
    ledger = ReviewLedger(args.out / "review_ledger.jsonl", config)
    result: dict[str, Any] = ledger.record(
        bundle, decisions, reviewer=args.reviewer, decided_at=datetime.now(UTC), allow_supersede=args.allow_supersede
    )
    if args.apply_gold_logs:
        for kind, path, header in (
            ("layout", LAYOUT_LOG, {"purpose": "T-P3-03 owner verification log", "annotations": str(LAYOUT)}),
            (
                "math",
                MATH_LOG,
                {
                    "purpose": "T-P3-02 owner verification log; completion also requires a separate 10 percent "
                    "double-check",
                    "sample": str(MATH),
                },
            ),
        ):
            rows = gold_log_rows(ledger, kind)
            if rows:
                _writable(path, config)
                result[f"{kind}_log_rows"] = _merge_gold_log(path, header, rows, allow=args.allow_supersede)
    if args.write_curation_approval:
        if args.reviewer != "user:owner":  # curation AgentRef admits only user:owner as a human decider
            raise ReviewError(f"only user:owner can approve Taxonomy v0 (got {args.reviewer})")
        record = ledger.latest().get("taxonomy:approve-v0")
        if not record or record["decision"] != "accept":
            raise ReviewError("no 'accept' of taxonomy:approve-v0 in the ledger; nothing written to approvals.yaml")
        digest = hashlib.sha256((ROOT / TAXONOMY).read_bytes() + (ROOT / COURSES).read_bytes()).hexdigest()
        approval_id = f"taxonomy-v0-{digest[:12]}"
        if any(a.approval_id == approval_id for a in load_approvals(ROOT / APPROVALS).records):
            result["curation_approval"] = f"{approval_id} already recorded"
        else:
            append_approval(
                ROOT / APPROVALS,
                Approval(
                    approval_id=approval_id,
                    kind="taxonomy_v0",
                    subject=f"curation/taxonomy.yaml + curation/course_map.yaml sha256:{digest}",
                    decision=ApprovalDecision.APPROVED,
                    decided_by=args.reviewer,
                    decided_at=datetime.fromisoformat(record["decided_at"]),
                    note=f"review ledger record {record['record_id']}",
                ),
            )
            result["curation_approval"] = approval_id
    result["progress"] = progress(bundle, ledger)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified Phase 3 owner review (build, status, import).")
    parser.add_argument("command", choices=("build", "status", "import"))
    parser.add_argument("--config", type=Path, help="sbr config; when given, every write is checked against it")
    parser.add_argument("--out", type=Path, default=REVIEW_DIR)
    parser.add_argument("--layout", type=Path, default=LAYOUT)
    parser.add_argument("--math", type=Path, default=MATH)
    parser.add_argument("--pptx-report", type=Path, default=PPTX_REPORT)
    parser.add_argument("--decisions", type=Path, help="review_decisions.json exported from the page (import)")
    parser.add_argument("--reviewer", help="who made these decisions, e.g. user:owner (import; required)")
    parser.add_argument("--allow-supersede", action="store_true", help="allow changing an already recorded decision")
    parser.add_argument("--apply-gold-logs", action="store_true")
    parser.add_argument("--write-curation-approval", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config) if args.config else None
    try:
        if args.command == "build":
            result = build(args, config)
        elif args.command == "status":
            bundle = json.loads((args.out / "bundle.json").read_text(encoding="utf-8"))
            result = {"progress": progress(bundle, ReviewLedger(args.out / "review_ledger.jsonl"))}
        else:
            if not args.decisions or not args.reviewer:
                parser.error("import needs --decisions and --reviewer")
            result = do_import(args, config)
    except ReviewError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
