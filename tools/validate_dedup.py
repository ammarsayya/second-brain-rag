"""Read-only Phase-0 survivor comparison for T-P2-06 exact duplicates.

The historical artifact predates the duplicate quarantine, so this validator
compares only paths present both there and in the selected current registry
root.  A historical group is discrepant only when at least two of its paths
survive and those survivors no longer share one blob id.  The reverse check
also reports current blobs that merge survivors from distinct Phase-0 groups.

One JSON object is written to stdout and a human-readable summary to stderr.
The registry is opened with SQLite ``mode=ro`` and ``query_only``; this tool
does not migrate or otherwise mutate it.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path, PureWindowsPath
from typing import Any

from sbr.config import load_config

DEFAULT_PHASE0 = Path("audit/phase0/dup_groups.json")
DEFAULT_MAX_DISCREPANCIES = 100


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare current exact-duplicate groups with Phase-0 survivors.")
    parser.add_argument("--config", type=Path, required=True, help="SBR config for an existing hashed registry.")
    parser.add_argument("--root", help="Configured source-root id; required when more than one root exists.")
    parser.add_argument("--phase0", type=Path, default=DEFAULT_PHASE0, help="Historical duplicate-group JSON file.")
    parser.add_argument(
        "--max-discrepancies",
        type=int,
        default=DEFAULT_MAX_DISCREPANCIES,
        help="Maximum detailed split/merge records in JSON; totals are never capped.",
    )
    return parser.parse_args()


def _path_key(value: str) -> str:
    return str(PureWindowsPath(value.replace("/", "\\"))).casefold()


def _load_phase0(path: Path) -> list[list[str]]:
    document: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, list) or any(
        not isinstance(group, list) or len(group) < 2 or any(not isinstance(item, str) for item in group)
        for group in document
    ):
        raise ValueError("Phase-0 artifact must be an array of string arrays with at least two paths each")
    return document


def _current_paths(db_path: Path, root_id: str) -> list[tuple[str, str]]:
    uri = db_path.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        conn.execute("PRAGMA query_only = ON")
        rows = conn.execute(
            "SELECT relpath, blob_id FROM path_observation "
            "WHERE root_id = ? AND state = 'present' AND blob_id IS NOT NULL ORDER BY relpath",
            (root_id,),
        ).fetchall()
    return [(str(relpath), str(blob_id)) for relpath, blob_id in rows]


def compare_groups(
    phase0_groups: list[list[str]],
    current_rows: list[tuple[str, str]],
    *,
    max_discrepancies: int,
) -> dict[str, object]:
    if max_discrepancies < 0:
        raise ValueError("--max-discrepancies must be zero or greater")

    current_by_path = {_path_key(relpath): (relpath, blob_id) for relpath, blob_id in current_rows}
    phase0_group_by_path: dict[str, int] = {}
    historical_path_count = 0
    for index, group in enumerate(phase0_groups):
        for path in group:
            key = _path_key(path)
            prior = phase0_group_by_path.setdefault(key, index)
            if prior != index:
                raise ValueError(f"Phase-0 path occurs in more than one group: {path}")
            historical_path_count += 1

    split_details: list[dict[str, object]] = []
    split_total = 0
    comparable_groups = 0
    surviving_paths = 0
    for index, group in enumerate(phase0_groups):
        survivors = [current_by_path[_path_key(path)] for path in group if _path_key(path) in current_by_path]
        surviving_paths += len(survivors)
        if len(survivors) < 2:
            continue
        comparable_groups += 1
        by_blob: dict[str, list[str]] = defaultdict(list)
        for relpath, blob_id in survivors:
            by_blob[blob_id].append(relpath)
        if len(by_blob) > 1:
            split_total += 1
            if len(split_details) < max_discrepancies:
                split_details.append(
                    {
                        "phase0_group_index": index,
                        "surviving_paths": sorted(relpath for relpath, _ in survivors),
                        "current_partitions": [sorted(paths) for _, paths in sorted(by_blob.items())],
                    }
                )

    current_by_blob: dict[str, list[str]] = defaultdict(list)
    for relpath, blob_id in current_rows:
        current_by_blob[blob_id].append(relpath)
    duplicate_groups = {blob_id: paths for blob_id, paths in current_by_blob.items() if len(paths) > 1}

    merge_details: list[dict[str, object]] = []
    merge_total = 0
    for paths in duplicate_groups.values():
        group_indexes = {
            phase0_group_by_path[key] for path in paths if (key := _path_key(path)) in phase0_group_by_path
        }
        if len(group_indexes) > 1:
            merge_total += 1
            if len(merge_details) < max_discrepancies:
                merge_details.append(
                    {
                        "current_paths": sorted(paths),
                        "phase0_group_indexes": sorted(group_indexes),
                    }
                )

    return {
        "ok": split_total == 0 and merge_total == 0,
        "phase0_groups": len(phase0_groups),
        "phase0_paths": historical_path_count,
        "current_present_hashed_paths": len(current_rows),
        "current_duplicate_groups": len(duplicate_groups),
        "surviving_phase0_paths": surviving_paths,
        "missing_phase0_paths": historical_path_count - surviving_paths,
        "comparable_phase0_groups": comparable_groups,
        "split_discrepancies": split_total,
        "merge_discrepancies": merge_total,
        "split_details": split_details,
        "merge_details": merge_details,
        "details_truncated": split_total > len(split_details) or merge_total > len(merge_details),
    }


def _validate(args: argparse.Namespace) -> dict[str, object]:
    config = load_config(args.config)
    if args.root is None and len(config.roots.sources) != 1:
        raise ValueError("--root is required when the configuration has multiple source roots")
    root_id = args.root or config.roots.sources[0].id
    config.source_root(root_id)
    phase0_groups = _load_phase0(args.phase0)
    result = compare_groups(
        phase0_groups,
        _current_paths(config.db_dir / "registry.sqlite", root_id),
        max_discrepancies=args.max_discrepancies,
    )
    result.update(
        {
            "root_id": root_id,
            "phase0_file": str(args.phase0),
            "registry_open_mode": "read_only",
            "exit_status": 0 if result["ok"] else 1,
        }
    )
    return result


def main() -> int:
    try:
        result = _validate(_arguments())
    except KeyboardInterrupt:
        result = {"ok": False, "exit_status": 1, "error": "KeyboardInterrupt"}
    except Exception as exc:
        error = type(exc).__name__
        result = {"ok": False, "exit_status": 1, "error": error}

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    print(
        "dedup validation: "
        + ("PASS" if result["ok"] else "REVIEW")
        + f"; comparable={result.get('comparable_phase0_groups', 0)}"
        + f" splits={result.get('split_discrepancies', 0)}"
        + f" merges={result.get('merge_discrepancies', 0)}"
        + f" surviving={result.get('surviving_phase0_paths', 0)}"
        + f" missing_expected={result.get('missing_phase0_paths', 0)}",
        file=sys.stderr,
    )
    return int(result["exit_status"])


if __name__ == "__main__":
    raise SystemExit(main())
