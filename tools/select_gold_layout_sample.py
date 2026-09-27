"""Select the ~40-page MBI-Gold-Layout candidate set from MBI-Gold-Extract (T-P3-03 prep).

This intentionally reuses ``eval/gold/extract_sample.yaml`` instead of scanning the corpus again.  Only its
PDF pages are probed, every source read goes through SourceFS, and the persisted registry supplies the current
canonical path plus the sensitivity/status gate.  Restricted, third-party-personal, excluded, orphaned, and
missing blobs are never opened.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from draft_gold_layout import analyze_pdf_page
from sbr.config import load_config
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.eval.gold_layout import DEFAULT_SEED, DEFAULT_TARGET_PAGES, LayoutDescriptor, select_layout_sample
from sbr.safety import assert_writable
from sbr.schemas.registry import BlobStatus, Sensitivity
from sbr.sourcefs import SourceFS

DEFAULT_INPUT = Path("eval/gold/extract_sample.yaml")
DEFAULT_OUTPUT = Path("eval/gold/layout_sample.yaml")
_BLOCKED_SENSITIVITY = {Sensitivity.RESTRICTED, Sensitivity.THIRD_PARTY_PERSONAL}


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select a seeded layout-diverse subset of MBI-Gold-Extract.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--target-pages", type=int, default=DEFAULT_TARGET_PAGES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def _load_yaml(path: Path) -> dict[str, Any]:
    doc = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise TypeError(f"expected a YAML mapping in {path}")
    return doc


def main() -> int:
    args = _arguments()
    config = load_config(args.config)
    source_fs = SourceFS(config)
    extract_doc = _load_yaml(args.input)

    with RegistryDB.open(config) as db:
        blobs = {blob.blob_id: blob for blob in db.repo(reg.BLOB).find()}
        observations = {obs.obs_id: obs for obs in db.repo(reg.PATH_OBSERVATION).find()}

    descriptors: list[LayoutDescriptor] = []
    locations: dict[tuple[str, int], tuple[str, str]] = {}
    signals_by_key: dict[tuple[str, int], dict[str, bool]] = {}
    skipped: dict[str, int] = {}
    probe_failures: list[dict[str, str]] = []

    for entry in extract_doc.get("sample", []):
        blob_id = str(entry["blob_id"])
        page = int(entry["page"])
        blob = blobs.get(blob_id)
        reason: str | None = None
        if blob is None:
            reason = "missing_registry_blob"
        elif blob.format != "pdf":
            reason = "non_pdf"
        elif blob.status is not BlobStatus.ACTIVE:
            reason = f"status_{blob.status.value}"
        elif blob.sensitivity in _BLOCKED_SENSITIVITY:
            reason = f"sensitivity_{blob.sensitivity.value}"
        elif blob.canonical_obs_id is None or blob.canonical_obs_id not in observations:
            reason = "missing_canonical_observation"
        if reason is not None:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue

        observation = observations[blob.canonical_obs_id]
        try:
            pdf_bytes = source_fs.read_bytes(observation.root_id, observation.relpath)
            _gold, signals = analyze_pdf_page(pdf_bytes, page)
        except Exception as exc:  # record a bounded page failure; do not manufacture signals
            probe_failures.append({"blob_id": blob_id, "page": str(page), "error": type(exc).__name__})
            continue
        descriptor = LayoutDescriptor(blob_id=blob_id, page=page, **signals)
        descriptors.append(descriptor)
        locations[descriptor.key] = (observation.root_id, observation.relpath)
        signals_by_key[descriptor.key] = signals

    selected, coverage = select_layout_sample(descriptors, target_pages=args.target_pages, seed=args.seed)
    output_doc: dict[str, Any] = {
        "purpose": "T-P3-03 layout candidate set; owner verification required",
        "source_sample": str(args.input),
        "seed": args.seed,
        "target_pages": args.target_pages,
        "descriptors_considered": len(descriptors),
        "selected": len(selected),
        "skipped": skipped,
        "probe_failures": probe_failures,
        "coverage": coverage,
        "sample": [
            {
                "blob_id": item.blob_id,
                "page": item.page,
                "bucket": item.bucket,
                "signals": signals_by_key[(item.blob_id, item.page)],
                "root_id": locations[(item.blob_id, item.page)][0],
                "relpath": locations[(item.blob_id, item.page)][1],
            }
            for item in selected
        ],
    }
    assert_writable(args.output.resolve(), config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.width = 120
    with args.output.open("w", encoding="utf-8") as stream:
        yaml.dump(output_doc, stream)

    print(
        json.dumps(
            {
                "source_entries": len(extract_doc.get("sample", [])),
                "descriptors_considered": len(descriptors),
                "selected": len(selected),
                "skipped": skipped,
                "probe_failures": probe_failures,
                "coverage": coverage,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    print(f"layout sample written to {args.output} (git-ignored, local only)")
    return 0 if len(selected) == args.target_pages else 2


if __name__ == "__main__":
    raise SystemExit(main())
