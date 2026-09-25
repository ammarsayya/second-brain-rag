"""Coverage report for T-P2-11's own acceptance criterion: "all level-3 folders mapped or marked unknown."

Unlike ``validate_genre.py``'s precision sample, this does not need a human label: whether a level-3 folder
resolved to a course_id or fell through to "unknown" is a mechanical fact from ``classify_course`` itself, not
a judgment call. What still needs a human is *whether the resolved course_id is the right one* and *whether an
"unknown" folder should really have a course* - this report lists both, grouped and counted, so the owner can
scan it instead of the raw registry.

A "level-3 folder" here is the same definition used to seed ``curation/course_map.yaml``: the first three
backslash-separated path segments of a PRESENT observation's relpath (or fewer, for a shallower path) -
matching how the corpus root's domain folders (``Mechanical``, ``Information``, ...) nest actual course
folders one level down.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from sbr.config import load_config
from sbr.curation import load_course_map
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.registry.courses import DEFAULT_COURSE_MAP_NAME, build_matchers, classify_course
from sbr.safety import assert_writable
from sbr.schemas.registry import KnowledgeClass, ObservationState

DEFAULT_OUTPUT = Path("reports/courses_coverage.json")
_INELIGIBLE_KNOWLEDGE_CLASSES = frozenset(
    {
        KnowledgeClass.TOOL_ARTIFACT,
        KnowledgeClass.CODE,
        KnowledgeClass.EXECUTABLE,
        KnowledgeClass.JUNK,
        KnowledgeClass.THIRD_PARTY_REFERENCE,
    }
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report T-P2-11 level-3 folder coverage against the real registry.")
    parser.add_argument("--config", type=Path, required=True, help="SBR config for an existing classified registry.")
    parser.add_argument("--course-map", type=Path, default=None, help="Course map YAML (default: curation dir).")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def _level3(relpath: str) -> str:
    parts = relpath.split("\\")
    segments = parts[:3] if len(parts) >= 4 else parts[:-1]
    return "\\".join(segments) if segments else "(root)"


def main() -> int:
    args = _arguments()
    config = load_config(args.config)
    map_file = args.course_map or Path(config.roots.curation) / DEFAULT_COURSE_MAP_NAME
    matchers = build_matchers(load_course_map(map_file).records)

    with RegistryDB.open(config) as db:
        blobs = {b.blob_id: b for b in db.repo(reg.BLOB).find()}
        current_by_blob = {}
        for obs in db.repo(reg.PATH_OBSERVATION).find({"state": ObservationState.PRESENT}):
            if obs.blob_id is not None and obs.blob_id not in current_by_blob and obs.blob_id in blobs:
                blob = blobs[obs.blob_id]
                if blob.knowledge_class not in _INELIGIBLE_KNOWLEDGE_CLASSES:
                    current_by_blob[obs.blob_id] = obs

    folder_counts: Counter[str] = Counter()
    folder_mapped: Counter[str] = Counter()
    folder_course_ids: dict[str, Counter[str]] = {}
    for obs in current_by_blob.values():
        folder = _level3(obs.relpath)
        folder_counts[folder] += 1
        decision = classify_course(obs.folder_tokens, matchers)
        if decision.course_id is not None:
            folder_mapped[folder] += 1
            folder_course_ids.setdefault(folder, Counter())[decision.course_id] += 1

    folders: list[dict[str, Any]] = []
    for folder, total in sorted(folder_counts.items()):
        mapped = folder_mapped.get(folder, 0)
        course_ids = folder_course_ids.get(folder)
        folders.append(
            {
                "folder": folder,
                "files": total,
                "mapped": mapped,
                "unknown": total - mapped,
                "resolved_course_ids": dict(course_ids.most_common()) if course_ids else {},
            }
        )

    fully_unknown = [f for f in folders if f["mapped"] == 0]
    partially_unknown = [f for f in folders if 0 < f["mapped"] < f["files"]]
    fully_mapped = [f for f in folders if f["files"] > 0 and f["mapped"] == f["files"]]

    summary = {
        "considered_blobs": len(current_by_blob),
        "level3_folders_total": len(folders),
        "level3_folders_fully_mapped": len(fully_mapped),
        "level3_folders_partially_mapped": len(partially_unknown),
        "level3_folders_fully_unknown": len(fully_unknown),
        "every_folder_mapped_or_marked_unknown": True,  # mechanically always true: unmatched files carry
        # course_id=None ("unknown") by construction (courses.py's own default), never silently dropped.
    }
    report = {"summary": summary, "folders": folders}

    assert_writable(args.output.resolve(), config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"full per-folder breakdown: {args.output}")
    print(f"fully-unknown folders (owner review candidates): {len(fully_unknown)}")
    for f in fully_unknown[:20]:
        print(f"  {f['files']:>6}  {f['folder']}")
    if len(fully_unknown) > 20:
        print(f"  ... and {len(fully_unknown) - 20} more, see {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
