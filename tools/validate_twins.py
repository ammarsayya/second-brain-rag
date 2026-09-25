"""Create a human-review precision sample for T-P2-09 twin candidates.

Like ``validate_classify.py``, this does not declare PASS/FAIL: whether a
proposed PDF<->office pair is genuinely the same document needs a human
glance at the two filenames and paths, not a mechanical check. It samples
already-stored ``twin_candidate`` BlobRelation rows and writes a JSON +
Markdown report for review, sorted by descending confidence so the weakest,
most-in-doubt candidates are easy to find at the bottom.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from sbr.config import load_config
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.safety import assert_writable
from sbr.schemas.registry import ObservationState, RelationType

DEFAULT_COUNT = 30
DEFAULT_SEED = 20_260_925
DEFAULT_JSON = Path("reports/twins_sample.json")
DEFAULT_MARKDOWN = Path("reports/twins_sample.md")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build JSON and Markdown reports for manual twin-candidate review.")
    parser.add_argument("--config", type=Path, required=True, help="SBR config for an existing registry.")
    parser.add_argument("-n", "--count", type=int, default=DEFAULT_COUNT, help="Maximum candidates to sample.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Deterministic random-sample seed.")
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if args.count < 1:
        raise ValueError("--count must be at least 1")
    config = load_config(args.config)

    with RegistryDB.open(config) as db:
        observations = db.repo(reg.PATH_OBSERVATION).find({"state": ObservationState.PRESENT})
        relpath_by_blob: dict[str, str] = {}
        for obs in observations:
            if obs.blob_id is not None and obs.blob_id not in relpath_by_blob:
                relpath_by_blob[obs.blob_id] = obs.relpath
        relations = [
            r for r in db.repo(reg.BLOB_RELATION).find() if r.type is RelationType.TWIN_CANDIDATE
        ]

    ordered = sorted(relations, key=lambda r: (-r.confidence, r.src_blob, r.dst_blob))
    selected = random.Random(args.seed).sample(ordered, min(args.count, len(ordered)))
    selected.sort(key=lambda r: -r.confidence)

    rows: list[dict[str, Any]] = [
        {
            "pdf_blob": relation.src_blob,
            "office_blob": relation.dst_blob,
            "pdf_relpath": relpath_by_blob.get(relation.src_blob, "<no current path>"),
            "office_relpath": relpath_by_blob.get(relation.dst_blob, "<no current path>"),
            "confidence": relation.confidence,
            "evidence": relation.evidence,
        }
        for relation in selected
    ]

    report: dict[str, Any] = {
        "purpose": "manual_twin_precision_review",
        "verdict": None,
        "requested": args.count,
        "available": len(ordered),
        "sampled": len(rows),
        "seed": args.seed,
        "sample": rows,
    }

    lines = [
        "# Twin-candidate precision sample",
        "",
        "Human review artifact only — this report intentionally does not declare PASS or FAIL.",
        "",
        f"- Requested: {report['requested']}",
        f"- Available twin_candidate relations: {report['available']}",
        f"- Sampled: {report['sampled']}",
        f"- Seed: {report['seed']}",
        "",
        "| Confidence | Stem sim. | Folder dist. | PDF | Office document |",
        "|---:|---:|---:|---|---|",
    ]
    for row in rows:
        evidence = row["evidence"]
        lines.append(
            f"| {row['confidence']:.3f} | {evidence.get('stem_similarity', '—')} | "
            f"{evidence.get('folder_distance', '—')} | `{row['pdf_relpath']}` | `{row['office_relpath']}` |"
        )
    lines.append("")

    for output in (args.json_output, args.markdown_output):
        assert_writable(output.resolve(), config)
        output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            {
                "sampled": len(rows),
                "available": len(ordered),
                "json_report": str(args.json_output),
                "markdown_report": str(args.markdown_output),
                "human_review_required": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
