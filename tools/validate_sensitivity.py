"""Generate the privacy-safe human-review report for T-P2-05.

Restricted blobs are counts-only unless ``--show-restricted-paths`` is
explicitly supplied.  The default report never includes their blob ids,
filenames, relpaths, owner patterns, or owner reasons.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from sbr.config import load_config
from sbr.curation import Exclusion, SensitivityOverride, load_exclusions, load_sensitivity_overrides
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.registry.sensitivity import DEFAULT_EXCLUSIONS_NAME, DEFAULT_OVERRIDES_NAME, decide_blob
from sbr.safety import assert_writable
from sbr.schemas import BlobRecord, PathObservation
from sbr.schemas.registry import BlobStatus, ObservationState, Sensitivity

DEFAULT_OUTPUT = Path("reports/sensitivity.md")
RESTRICTED_WARNING = "WARNING: sensitive RESTRICTED paths are exposed below by explicit opt-in."


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the T-P2-05 privacy-safe sensitivity review report.")
    parser.add_argument("--config", type=Path, required=True, help="SBR config for an existing classified registry.")
    parser.add_argument("--root", help="Limit observations to one configured source-root id.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Markdown report path.")
    parser.add_argument(
        "--show-restricted-paths",
        action="store_true",
        help="Explicitly include restricted relpaths (off by default).",
    )
    return parser.parse_args()


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("`", "'")


def _current_by_blob(observations: list[PathObservation]) -> dict[str, list[PathObservation]]:
    current: dict[str, list[PathObservation]] = defaultdict(list)
    for observation in observations:
        if observation.state is ObservationState.PRESENT and observation.blob_id is not None:
            current[observation.blob_id].append(observation)
    for rows in current.values():
        rows.sort(key=lambda row: (row.root_id, row.relpath))
    return current


def build_report(
    blobs: list[BlobRecord],
    observations: list[PathObservation],
    *,
    exclusions: tuple[Exclusion, ...],
    overrides: tuple[SensitivityOverride, ...],
    show_restricted_paths: bool = False,
) -> str:
    """Render Markdown without restricted paths unless explicitly opted in."""
    current = _current_by_blob(observations)
    visible = [blob for blob in blobs if blob.blob_id in current]
    sensitivity_counts = Counter(blob.sensitivity.value for blob in visible)
    exclusion_counts = Counter(
        blob.knowledge_class.value if blob.status is BlobStatus.EXCLUDED else "active_or_orphaned" for blob in visible
    )
    restricted_rule_counts: Counter[str] = Counter()
    restricted_rows: list[tuple[str, str]] = []
    third_party_paths: list[str] = []

    for blob in visible:
        rows = current[blob.blob_id]
        decision = decide_blob(blob, rows, exclusions, overrides)
        if blob.sensitivity is Sensitivity.RESTRICTED:
            label = decision.sensitivity_rule if decision.sensitivity is Sensitivity.RESTRICTED else "Stored restricted"
            restricted_rule_counts[label] += 1
            restricted_rows.extend((row.relpath, label) for row in rows)
        elif blob.sensitivity is Sensitivity.THIRD_PARTY_PERSONAL:
            third_party_paths.extend(row.relpath for row in rows)

    lines = [
        "# Sensitivity and exclusions review",
        "",
        "Human review artifact only — fixture/unit classification is automated, but acceptance requires owner review.",
        "",
        "## Sensitivity counts",
        "",
    ]
    lines.extend(f"- {item.value}: {sensitivity_counts[item.value]}" for item in Sensitivity)
    lines.extend(["", "## Restricted rule counts (paths hidden by default)", ""])
    if restricted_rule_counts:
        lines.extend(f"- {label}: {restricted_rule_counts[label]}" for label in sorted(restricted_rule_counts))
    else:
        lines.append("- None: 0")

    if show_restricted_paths:
        lines.extend(["", f"> **{RESTRICTED_WARNING}**", "", "### Restricted paths", ""])
        lines.extend(f"- `{_escape(path)}` ({label})" for path, label in sorted(restricted_rows))

    lines.extend(["", "## Third-party personal paths", ""])
    if third_party_paths:
        lines.extend(f"- `{_escape(path)}`" for path in sorted(third_party_paths))
    else:
        lines.append("- None")

    lines.extend(["", "## Exclusion summary", ""])
    lines.append(f"- excluded total: {sum(1 for blob in visible if blob.status is BlobStatus.EXCLUDED)}")
    for label in sorted(exclusion_counts):
        lines.append(f"- {label}: {exclusion_counts[label]}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = _arguments()
    config = load_config(args.config)
    if args.root is not None:
        config.source_root(args.root)
    curation_root = Path(config.roots.curation)
    exclusions = load_exclusions(curation_root / DEFAULT_EXCLUSIONS_NAME).records
    overrides = load_sensitivity_overrides(curation_root / DEFAULT_OVERRIDES_NAME).records

    with RegistryDB.open(config) as db:
        db.migrate()
        where = None if args.root is None else {"root_id": args.root}
        observations = db.repo(reg.PATH_OBSERVATION).find(where)
        visible_ids = {row.blob_id for row in observations if row.blob_id is not None}
        blobs = [blob for blob in db.repo(reg.BLOB).find() if blob.blob_id in visible_ids]

    report = build_report(
        blobs,
        observations,
        exclusions=exclusions,
        overrides=overrides,
        show_restricted_paths=args.show_restricted_paths,
    )
    output = args.output.resolve()
    assert_writable(output, config)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    if args.show_restricted_paths:
        print(RESTRICTED_WARNING)
    print(
        json.dumps(
            {
                "report": str(args.output),
                "restricted_paths_shown": bool(args.show_restricted_paths),
                "human_review_required": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
