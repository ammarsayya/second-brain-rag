"""Mirror-directory and cleanup-suggestion report (T-P2-07, Q-I10).

Read-only, report-only, **no action taken**: this identifies pairs of
folders that share a large fraction of their content (by BLAKE3 content
hash, the same identity T-P2-06's exact-dedup already established — not
filename similarity) so the owner can decide by hand whether one side is a
redundant full-or-partial copy worth removing. It never deletes, moves, or
marks anything; it only reports, per this task's own "no action" framing.

Detection is a folder-level generalization of T-P2-06's per-blob duplicate
grouping: group every currently-known blob by the set of level-2 folders
(``<domain>\\<course-ish>``, the same granularity :mod:`sbr.reports.manifest`
uses) it appears under, then for every pair of folders compute the overlap
coefficient ``|shared| / min(|A|, |B|)`` — "what fraction of the *smaller*
side's content also lives in the other side" — over their respective sets of
distinct blob_ids. A folder pair only qualifies as a candidate mirror when
both the overlap fraction and the absolute shared-blob count clear a
minimum (:data:`MIN_OVERLAP`, :data:`MIN_SHARED_BLOBS`): a tiny folder that
happens to share two files with a huge one is not "mirrored" by any useful
sense of the word, however high its overlap fraction reads.

``bytes_reclaimable`` is the total size of the shared blobs — the bytes that
would be freed if every one of the shared blobs were removed from whichever
side the owner decides is redundant. It is *not* automatically halved or
attributed to one side, since the report never decides which side to keep.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import PureWindowsPath

from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.schemas.registry import ObservationState

MIN_OVERLAP: float = 0.5
MIN_SHARED_BLOBS: int = 5


def _level2(relpath: str) -> str:
    """The first two folder segments, filename excluded (see manifest.py's ``_level2`` for the regression
    this avoids: a file directly inside a single-depth folder must bucket under that folder, not under a
    distinct per-file key that wrongly includes the filename)."""
    parts = PureWindowsPath(relpath).parts[:-1]
    if len(parts) >= 2:
        return "\\".join(parts[:2])
    return parts[0] if parts else "(root)"


@dataclass(frozen=True, slots=True)
class MirrorPair:
    folder_a: str
    folder_b: str
    blobs_a: int
    blobs_b: int
    shared_blobs: int
    overlap_pct: float
    bytes_reclaimable: int


def find_mirror_pairs(
    folder_blobs: dict[str, frozenset[str]],
    blob_sizes: dict[str, int],
    *,
    min_overlap: float = MIN_OVERLAP,
    min_shared_blobs: int = MIN_SHARED_BLOBS,
) -> list[MirrorPair]:
    """Pure function: every qualifying folder pair from a precomputed ``folder -> {blob_id, ...}`` map."""
    folders = sorted(folder_blobs)
    pairs: list[MirrorPair] = []
    for i, folder_a in enumerate(folders):
        blobs_a = folder_blobs[folder_a]
        if not blobs_a:
            continue
        for folder_b in folders[i + 1 :]:
            blobs_b = folder_blobs[folder_b]
            if not blobs_b:
                continue
            shared = blobs_a & blobs_b
            if len(shared) < min_shared_blobs:
                continue
            overlap = len(shared) / min(len(blobs_a), len(blobs_b))
            if overlap < min_overlap:
                continue
            pairs.append(
                MirrorPair(
                    folder_a=folder_a,
                    folder_b=folder_b,
                    blobs_a=len(blobs_a),
                    blobs_b=len(blobs_b),
                    shared_blobs=len(shared),
                    overlap_pct=round(overlap, 4),
                    bytes_reclaimable=sum(blob_sizes.get(bid, 0) for bid in shared),
                )
            )
    return sorted(pairs, key=lambda p: (-p.bytes_reclaimable, p.folder_a, p.folder_b))


def build_mirrors_report(
    config: SbrConfig,
    db: RegistryDB,
    *,
    min_overlap: float = MIN_OVERLAP,
    min_shared_blobs: int = MIN_SHARED_BLOBS,
) -> list[MirrorPair]:
    """Aggregate the registry's current PRESENT observations into folder-level blob sets, then find mirrors."""
    blobs = {b.blob_id: b for b in db.repo(reg.BLOB).find()}
    folder_to_blobs: dict[str, set[str]] = defaultdict(set)
    for obs in db.repo(reg.PATH_OBSERVATION).find({"state": ObservationState.PRESENT}):
        if obs.blob_id is not None:
            folder_to_blobs[_level2(obs.relpath)].add(obs.blob_id)
    folder_blobs = {folder: frozenset(ids) for folder, ids in folder_to_blobs.items()}
    blob_sizes = {blob_id: blob.size for blob_id, blob in blobs.items()}
    return find_mirror_pairs(folder_blobs, blob_sizes, min_overlap=min_overlap, min_shared_blobs=min_shared_blobs)


def render_markdown(pairs: list[MirrorPair]) -> str:
    lines: list[str] = [
        "# Mirror-Directory Report (T-P2-07)",
        "",
        "Report only - no action taken. Every pair below shares a large fraction of its content (by content "
        "hash, not filename) with the other; the owner decides by hand whether one side is a redundant copy "
        "worth removing.",
        "",
        f"- pairs found: {len(pairs)}",
        f"- total reclaimable bytes across all pairs (if every shared blob were removed from one side): "
        f"{sum(p.bytes_reclaimable for p in pairs)}",
        "",
        "| folder A | folder B | blobs A | blobs B | shared | overlap % | reclaimable bytes |",
        "|---|---|---|---|---|---|---|",
    ]
    for pair in pairs:
        lines.append(
            f"| {pair.folder_a} | {pair.folder_b} | {pair.blobs_a} | {pair.blobs_b} | {pair.shared_blobs} | "
            f"{pair.overlap_pct:.2%} | {pair.bytes_reclaimable} |"
        )
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "MIN_OVERLAP",
    "MIN_SHARED_BLOBS",
    "MirrorPair",
    "build_mirrors_report",
    "find_mirror_pairs",
    "render_markdown",
]
