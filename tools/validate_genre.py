"""Build the T-P2-10 precision-eval sample (150 files, labels drafted by AI, checked by owner).

Unlike the other ``validate_*.py`` tools, this one is a two-step workflow rather
than a single report:

1. ``--draft`` samples N already-classified blobs, writes a JSON file with the
   classifier's own genre call alongside an empty ``"label"`` field, and a
   Markdown table for a human/AI reviewer to fill in.
2. After the ``label`` field in the JSON is filled in for every row (an
   independent judgment call on each path, not a copy of ``predicted_genre``),
   ``--score <path>`` reads that file back and computes precision: for the
   rows where a label was actually given, what fraction of the classifier's
   *non-null* predictions agree with the independent label.

This keeps "draft the labels" and "score against them" as two distinct,
auditable steps, matching the task's own two-step acceptance criterion.
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
from sbr.schemas.registry import ObservationState

DEFAULT_COUNT = 150
DEFAULT_SEED = 20_260_925
DEFAULT_OUTPUT = Path("reports/genre_sample.json")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Draft or score the T-P2-10 genre precision-eval sample.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--draft", action="store_true", help="Sample and write a fresh labeling sheet.")
    mode.add_argument("--score", type=Path, help="Score an already-labeled sheet (its 'label' fields filled in).")
    parser.add_argument("--config", type=Path, required=True, help="SBR config for an existing classified registry.")
    parser.add_argument("-n", "--count", type=int, default=DEFAULT_COUNT, help="Sample size for --draft.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Deterministic random-sample seed.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Where --draft writes the sheet.")
    return parser.parse_args()


def _draft(args: argparse.Namespace) -> dict[str, Any]:
    """Sample from blobs the classifier actually assigned a genre to.

    Precision (correct / predicted-positive) is only informative over the predicted-positive set: with a
    sparse classifier (this corpus: ~2,080 of 34,814 blobs get a genre), sampling uniformly from every blob
    would spend most of a 150-row budget on uninformative "no prediction" rows instead of genuinely
    stress-testing precision.
    """
    config = load_config(args.config)
    with RegistryDB.open(config) as db:
        observations = db.repo(reg.PATH_OBSERVATION).find({"state": ObservationState.PRESENT})
        relpath_by_blob: dict[str, str] = {}
        for obs in observations:
            if obs.blob_id is not None and obs.blob_id not in relpath_by_blob:
                relpath_by_blob[obs.blob_id] = obs.relpath
        classifications = {c.blob_id: c for c in db.repo(reg.BLOB_CLASSIFICATION).find()}

    candidates = sorted(
        blob_id
        for blob_id, classification in classifications.items()
        if classification.genre is not None and blob_id in relpath_by_blob
    )
    selected = random.Random(args.seed).sample(candidates, min(args.count, len(candidates)))
    rows = [
        {
            "blob_id": blob_id,
            "relpath": relpath_by_blob[blob_id],
            "predicted_genre": (classifications[blob_id].genre if blob_id in classifications else None),
            "predicted_confidence": (classifications[blob_id].genre_confidence if blob_id in classifications else None),
            "label": None,
        }
        for blob_id in selected
    ]
    sheet = {"purpose": "genre_precision_eval_draft", "seed": args.seed, "count": len(rows), "sample": rows}
    assert_writable(args.output.resolve(), config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(sheet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "drafted": len(rows),
        "output": str(args.output),
        "next_step": "fill in 'label' for every row, then --score",
    }


def _score(args: argparse.Namespace) -> dict[str, Any]:
    sheet = json.loads(args.score.read_text(encoding="utf-8"))
    rows = sheet["sample"]
    labeled = [row for row in rows if row.get("label") is not None]
    unlabeled = len(rows) - len(labeled)
    predicted_nonnull = [row for row in labeled if row.get("predicted_genre") is not None]
    correct = [row for row in predicted_nonnull if row["predicted_genre"] == row["label"]]
    false_positives = [row for row in predicted_nonnull if row["predicted_genre"] != row["label"]]
    missed = [row for row in labeled if row.get("predicted_genre") is None and row["label"] is not None]
    precision = len(correct) / len(predicted_nonnull) if predicted_nonnull else None
    return {
        "total_rows": len(rows),
        "labeled_rows": len(labeled),
        "unlabeled_rows": unlabeled,
        "predicted_nonnull": len(predicted_nonnull),
        "correct": len(correct),
        "precision": round(precision, 4) if precision is not None else None,
        "false_positives": [
            {"relpath": row["relpath"], "predicted": row["predicted_genre"], "label": row["label"]}
            for row in false_positives
        ],
        "missed_recall_examples": [{"relpath": row["relpath"], "label": row["label"]} for row in missed],
    }


def main() -> int:
    args = _arguments()
    result = _draft(args) if args.draft else _score(args)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
