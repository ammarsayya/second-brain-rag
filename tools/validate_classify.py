"""Create a human-review sample for T-P2-04 classification precision.

The validator does not declare PASS or FAIL: format and knowledge-class quality
requires owner judgment against real filenames and context.  With ``--config``
it samples unique hashed blobs from an existing classified registry.  With
``--corpus`` it scans into a temporary registry, deterministically samples path
observations, hashes and classifies only that bounded sample, and leaves the
corpus untouched.  Both modes write the same machine-readable JSON and grouped
Markdown table, then print only an artifact summary to stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import tempfile
from collections import Counter, defaultdict
from pathlib import Path, PureWindowsPath
from typing import Any

from sbr import __version__
from sbr.config import SbrConfig, config_from_mapping, load_config, resolve_config_path
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.ids import hash_stream
from sbr.provenance import ProvenanceStore
from sbr.registry.classify import classify_pending
from sbr.registry.scan import scan_root
from sbr.safety import assert_writable
from sbr.schemas import BlobRecord, PathObservation
from sbr.schemas.registry import ObservationState
from sbr.sourcefs import SourceFS

DEFAULT_COUNT = 200
DEFAULT_SEED = 20_260_925
DEFAULT_JSON = Path("reports/classification_sample.json")
DEFAULT_MARKDOWN = Path("reports/classification_sample.md")
MAX_DISPLAY_PATH = 100


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build JSON and Markdown reports for manual classification review.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--corpus",
        type=Path,
        help="Corpus directory; S1 and a bounded S2/S3 sample use a temporary registry.",
    )
    target.add_argument("--config", type=Path, help="SBR config whose existing registry contains classified rows.")
    parser.add_argument("--root", help="Limit the sample to one configured source-root id.")
    parser.add_argument("-n", "--count", type=int, default=DEFAULT_COUNT, help="Maximum unique blobs to sample.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Deterministic random-sample seed.")
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    return parser.parse_args()


def _configured_target(args: argparse.Namespace, temp: Path) -> tuple[SbrConfig, str | None, bool]:
    if args.corpus is not None:
        corpus = Path(os.path.abspath(args.corpus))
        safety_path = resolve_config_path()
        if not safety_path.is_file():
            safety_path = Path(__file__).resolve().parents[1] / "config" / "sbr.example.toml"
        safety_config = load_config(safety_path)
        config = config_from_mapping(
            {
                "roots": {
                    "sources": [{"id": "validation", "path": str(corpus)}],
                    "var": str(temp / "var"),
                    "curation": str(temp / "curation"),
                    "protected": safety_config.roots.protected,
                }
            },
            origin="validate_classify --corpus",
        )
        return config, "validation", True

    config = load_config(args.config)
    if args.root is not None:
        config.source_root(args.root)
    return config, args.root, False


def _sample_observations(observations: list[PathObservation], count: int, seed: int) -> list[PathObservation]:
    candidates = sorted(
        (observation for observation in observations if observation.state is ObservationState.PRESENT),
        key=lambda observation: observation.obs_id,
    )
    return random.Random(seed).sample(candidates, min(count, len(candidates)))


def _bootstrap_sample(config: SbrConfig, db: RegistryDB, root_id: str, count: int, seed: int) -> None:
    scan_root(config, db, root_id)
    observations = db.repo(reg.PATH_OBSERVATION)
    selected = _sample_observations(observations.find({"root_id": root_id}), count, seed)
    blobs = db.repo(reg.BLOB)
    source_fs = SourceFS(config)
    provenance = ProvenanceStore(db.conn)
    with provenance.activity(
        kind="hash",
        producer="tools.validate_classify",
        producer_version=__version__,
        agent="system:validator",
        params={"count": count, "seed": seed, "bootstrap": True},
    ) as activity:
        for observation in selected:
            with source_fs.open_binary(observation.root_id, observation.relpath_raw) as stream:
                content = hash_stream(stream)
            blobs.upsert(
                BlobRecord(
                    blob_id=content.blob_id,
                    size=content.size,
                    first_seen_scan=observation.last_seen_scan,
                    last_seen_scan=observation.last_seen_scan,
                    activity_id=activity.activity_id,
                )
            )
            observations.upsert(
                observation.model_copy(update={"blob_id": content.blob_id, "activity_id": activity.activity_id})
            )
            activity.outputs.extend((content.blob_id, observation.obs_id))
    classify_pending(config, db)


def _truncated(relpath: str, limit: int = MAX_DISPLAY_PATH) -> str:
    if len(relpath) <= limit:
        return relpath
    keep = limit - 1
    left = keep // 2
    return relpath[:left] + "…" + relpath[-(keep - left) :]


def _sample_rows(
    blobs: list[BlobRecord],
    observations: list[PathObservation],
    count: int,
    seed: int,
) -> list[dict[str, Any]]:
    current: dict[str, list[PathObservation]] = defaultdict(list)
    for observation in observations:
        if observation.state is ObservationState.PRESENT and observation.blob_id is not None:
            current[observation.blob_id].append(observation)
    for rows in current.values():
        rows.sort(key=lambda row: (row.root_id, row.relpath))

    candidates = sorted((blob for blob in blobs if blob.blob_id in current), key=lambda blob: blob.blob_id)
    selected = random.Random(seed).sample(candidates, min(count, len(candidates)))
    rows: list[dict[str, Any]] = []
    for blob in selected:
        observation = current[blob.blob_id][0]
        extension = PureWindowsPath(observation.relpath).suffix.casefold() or "<none>"
        rows.append(
            {
                "blob_id": blob.blob_id,
                "root_id": observation.root_id,
                "relpath": observation.relpath,
                "relpath_display": _truncated(observation.relpath),
                "extension": extension,
                "magic_type": blob.magic_type,
                "format": blob.format,
                "knowledge_class": blob.knowledge_class.value,
                "encrypted": blob.encrypted,
            }
        )
    return sorted(rows, key=lambda row: (str(row["knowledge_class"]), str(row["relpath"])))


def _markdown(report: dict[str, Any]) -> str:
    rows = report["sample"]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["knowledge_class"])].append(row)
    lines = [
        "# Classification precision sample",
        "",
        "Human review artifact only — this report intentionally does not declare PASS or FAIL.",
        "",
        f"- Requested: {report['requested']}",
        f"- Available unique hashed blobs: {report['available']}",
        f"- Sampled: {report['sampled']}",
        f"- Seed: {report['seed']}",
        "",
    ]
    for knowledge_class in sorted(grouped):
        lines.extend(
            [
                f"## {knowledge_class} ({len(grouped[knowledge_class])})",
                "",
                "| Extension | Format | Magic type | Encrypted | Path | Blob |",
                "|---|---|---|---:|---|---|",
            ]
        )
        for row in grouped[knowledge_class]:
            path = str(row["relpath_display"]).replace("|", "\\|")
            lines.append(
                f"| {row['extension']} | {row['format'] or '—'} | {row['magic_type'] or '—'} | "
                f"{str(row['encrypted']).lower()} | `{path}` | `{str(row['blob_id'])[:15]}…` |"
            )
        lines.append("")
    return "\n".join(lines)


def _build_report(
    args: argparse.Namespace,
    config: SbrConfig,
    root_id: str | None,
    *,
    bootstrap: bool,
) -> dict[str, Any]:
    with RegistryDB.open(config) as db:
        db.migrate()
        if bootstrap:
            assert root_id is not None
            _bootstrap_sample(config, db, root_id, args.count, args.seed)
        observations = db.repo(reg.PATH_OBSERVATION).find(None if root_id is None else {"root_id": root_id})
        visible_blob_ids = {row.blob_id for row in observations if row.blob_id is not None}
        blobs = [blob for blob in db.repo(reg.BLOB).find() if blob.blob_id in visible_blob_ids]
        sample = _sample_rows(blobs, observations, args.count, args.seed)

    return {
        "purpose": "manual_classification_precision_review",
        "verdict": None,
        "requested": args.count,
        "available": len(blobs),
        "sampled": len(sample),
        "seed": args.seed,
        "knowledge_class_counts": dict(Counter(str(row["knowledge_class"]) for row in sample)),
        "sample": sample,
    }


def main() -> int:
    args = _arguments()
    if args.count < 1:
        raise ValueError("--count must be at least 1")
    if args.corpus is not None:
        with tempfile.TemporaryDirectory(prefix="sbr-classify-validation-") as raw_temp:
            config, root_id, bootstrap = _configured_target(args, Path(raw_temp))
            report = _build_report(args, config, root_id, bootstrap=bootstrap)
    else:
        config, root_id, bootstrap = _configured_target(args, Path())
        report = _build_report(args, config, root_id, bootstrap=bootstrap)

    for output in (args.json_output, args.markdown_output):
        assert_writable(output.resolve(), config)
        output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "sampled": report["sampled"],
                "available": report["available"],
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
