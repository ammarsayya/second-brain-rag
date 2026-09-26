"""Corpus manifest report (T-P2-14, docs/31 §3).

Read-only over the registry: this module never opens a source file or
mutates any table, only aggregates what earlier stages already wrote —
``sbr scan``/``hash``/``classify``/``sensitivity``/``dedup``/``archives``/
``genre``/``courses``/``names`` (T-P2-01 through T-P2-13). The manifest is
the transparency artifact docs/31 §3 describes: totals, breakdowns by
knowledge_class/format/folder, duplicates, archive inventory, sensitivity
*counts* (never names or paths — a sensitive blob's relpath must never
appear in this report, docs/22), genre/course distributions, and change
counts since the most recent scan per root.

Two sections docs/31 §3 names are intentionally reported as unavailable
rather than faked: **PDF page census** ("after the text tier") depends on a
later extraction phase that does not exist yet in P2, and there is no
``page_count`` field anywhere in the current schema to report from.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import PureWindowsPath

from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.schemas.registry import ObservationState, ScanRecord

MANIFEST_VERSION = "1"


@dataclass(frozen=True, slots=True)
class FolderCount:
    folder: str
    files: int
    bytes: int


@dataclass(frozen=True, slots=True)
class CategoryCount:
    key: str
    files: int
    bytes: int


@dataclass(frozen=True, slots=True)
class DuplicatesSummary:
    duplicate_groups: int
    redundant_bytes: int
    mirror_candidate_paths: int


@dataclass(frozen=True, slots=True)
class ArchivesSummary:
    members_total: int
    already_present: int
    extracted_new: int
    skipped_limit: int
    excluded: int


@dataclass(frozen=True, slots=True)
class ScanChangeSummary:
    root_id: str
    scan_id: str | None
    counts_by_type: dict[str, int]


@dataclass(frozen=True, slots=True)
class ManifestReport:
    manifest_version: str
    total_files: int
    total_bytes: int
    total_blobs: int
    total_unique_bytes: int
    by_knowledge_class: tuple[CategoryCount, ...]
    by_format: tuple[CategoryCount, ...]
    by_top_level_folder: tuple[FolderCount, ...]
    by_level2_folder: tuple[FolderCount, ...]
    duplicates: DuplicatesSummary
    archives: ArchivesSummary
    sensitivity: tuple[CategoryCount, ...]
    genre: tuple[CategoryCount, ...]
    course: tuple[CategoryCount, ...]
    changes_since_last_scan: tuple[ScanChangeSummary, ...]
    pdf_page_census: dict[str, object] = field(
        default_factory=lambda: {
            "available": False,
            "reason": "requires a text-extraction phase (docs/31 §3 'after the text tier'), not yet implemented",
        }
    )


def _top_level(relpath: str) -> str:
    return PureWindowsPath(relpath).parts[0] if relpath else "(root)"


def _level2(relpath: str) -> str:
    parts = PureWindowsPath(relpath).parts
    return "\\".join(parts[:2]) if len(parts) >= 2 else _top_level(relpath)


def _category_counts(counter_files: Counter[str], counter_bytes: Counter[str]) -> tuple[CategoryCount, ...]:
    return tuple(
        CategoryCount(key=key, files=counter_files[key], bytes=counter_bytes[key])
        for key in sorted(counter_files, key=lambda k: (-counter_files[k], k))
    )


def build_manifest(config: SbrConfig, db: RegistryDB) -> ManifestReport:
    """Aggregate the registry's current state into one :class:`ManifestReport`. Never writes anything."""
    observations = [o for o in db.repo(reg.PATH_OBSERVATION).find() if o.state == ObservationState.PRESENT]
    blobs = {b.blob_id: b for b in db.repo(reg.BLOB).find()}

    total_files = len(observations)
    total_bytes = sum(o.size for o in observations)
    referenced_blob_ids = {o.blob_id for o in observations if o.blob_id is not None}
    total_blobs = len(referenced_blob_ids)
    total_unique_bytes = sum(blobs[bid].size for bid in referenced_blob_ids if bid in blobs)

    class_files: Counter[str] = Counter()
    class_bytes: Counter[str] = Counter()
    format_files: Counter[str] = Counter()
    format_bytes: Counter[str] = Counter()
    for blob_id in referenced_blob_ids:
        blob = blobs.get(blob_id)
        if blob is None:
            continue
        class_files[blob.knowledge_class.value] += 1
        class_bytes[blob.knowledge_class.value] += blob.size
        fmt = blob.format or "(unknown)"
        format_files[fmt] += 1
        format_bytes[fmt] += blob.size

    top_files: Counter[str] = Counter()
    top_bytes: Counter[str] = Counter()
    l2_files: Counter[str] = Counter()
    l2_bytes: Counter[str] = Counter()
    observations_by_blob: dict[str, list[str]] = {}
    mirror_candidates = 0
    for obs in observations:
        top_files[_top_level(obs.relpath)] += 1
        top_bytes[_top_level(obs.relpath)] += obs.size
        l2_files[_level2(obs.relpath)] += 1
        l2_bytes[_level2(obs.relpath)] += obs.size
        if obs.blob_id is not None:
            observations_by_blob.setdefault(obs.blob_id, []).append(obs.obs_id)
        if obs.is_mirror_candidate:
            mirror_candidates += 1

    by_top_level_folder = tuple(
        FolderCount(folder=k, files=top_files[k], bytes=top_bytes[k])
        for k in sorted(top_files, key=lambda k: (-top_files[k], k))
    )
    by_level2_folder = tuple(
        FolderCount(folder=k, files=l2_files[k], bytes=l2_bytes[k])
        for k in sorted(l2_files, key=lambda k: (-l2_files[k], k))
    )

    duplicate_groups = 0
    redundant_bytes = 0
    for blob_id, obs_ids in observations_by_blob.items():
        if len(obs_ids) > 1:
            duplicate_groups += 1
            blob = blobs.get(blob_id)
            if blob is not None:
                redundant_bytes += blob.size * (len(obs_ids) - 1)
    duplicates = DuplicatesSummary(
        duplicate_groups=duplicate_groups, redundant_bytes=redundant_bytes, mirror_candidate_paths=mirror_candidates
    )

    members = db.repo(reg.ARCHIVE_MEMBER).find()
    member_status_counts = Counter(m.status.value for m in members)
    archives = ArchivesSummary(
        members_total=len(members),
        already_present=member_status_counts.get("already_present", 0),
        extracted_new=member_status_counts.get("extracted_new", 0),
        skipped_limit=member_status_counts.get("skipped_limit", 0),
        excluded=member_status_counts.get("excluded", 0),
    )

    sens_files: Counter[str] = Counter()
    sens_bytes: Counter[str] = Counter()
    for blob_id in referenced_blob_ids:
        blob = blobs.get(blob_id)
        if blob is None:
            continue
        sens_files[blob.sensitivity.value] += 1
        sens_bytes[blob.sensitivity.value] += blob.size
    sensitivity = _category_counts(sens_files, sens_bytes)

    classifications = db.repo(reg.BLOB_CLASSIFICATION).find()
    genre_files: Counter[str] = Counter()
    genre_bytes: Counter[str] = Counter()
    course_files: Counter[str] = Counter()
    course_bytes: Counter[str] = Counter()
    for c in classifications:
        blob = blobs.get(c.blob_id)
        size = blob.size if blob is not None else 0
        genre_key = c.genre or "(unclassified)"
        genre_files[genre_key] += 1
        genre_bytes[genre_key] += size
        course_key = c.course_id or "(unknown)"
        course_files[course_key] += 1
        course_bytes[course_key] += size
    genre = _category_counts(genre_files, genre_bytes)
    course = _category_counts(course_files, course_bytes)

    scans_by_root: dict[str, list[ScanRecord]] = {}
    for scan in db.repo(reg.SCAN).find():
        scans_by_root.setdefault(scan.root_id, []).append(scan)
    changes: list[ScanChangeSummary] = []
    for root in config.roots.sources:
        root_scans = scans_by_root.get(root.id, [])
        if not root_scans:
            changes.append(ScanChangeSummary(root_id=root.id, scan_id=None, counts_by_type={}))
            continue
        latest = max(root_scans, key=lambda s: s.started_at)
        events = db.repo(reg.CHANGE_EVENT).find({"scan_id": latest.scan_id})
        counts_by_type = dict(Counter(e.type.value for e in events))
        changes.append(ScanChangeSummary(root_id=root.id, scan_id=latest.scan_id, counts_by_type=counts_by_type))

    return ManifestReport(
        manifest_version=MANIFEST_VERSION,
        total_files=total_files,
        total_bytes=total_bytes,
        total_blobs=total_blobs,
        total_unique_bytes=total_unique_bytes,
        by_knowledge_class=_category_counts(class_files, class_bytes),
        by_format=_category_counts(format_files, format_bytes),
        by_top_level_folder=by_top_level_folder,
        by_level2_folder=by_level2_folder,
        duplicates=duplicates,
        archives=archives,
        sensitivity=sensitivity,
        genre=genre,
        course=course,
        changes_since_last_scan=tuple(changes),
    )


def render_markdown(report: ManifestReport) -> str:
    lines: list[str] = ["# Corpus Manifest", ""]
    lines.append(f"manifest_version: {report.manifest_version}")
    lines.append("")
    lines.append("## Totals")
    lines.append("")
    lines.append(f"- files: {report.total_files}")
    lines.append(f"- bytes: {report.total_bytes}")
    lines.append(f"- blobs: {report.total_blobs}")
    lines.append(f"- unique bytes: {report.total_unique_bytes}")
    lines.append("")

    def _category_table(title: str, rows: tuple[CategoryCount, ...], key_header: str) -> None:
        lines.append(f"## {title}")
        lines.append("")
        lines.append(f"| {key_header} | files | bytes |")
        lines.append("|---|---|---|")
        for row in rows:
            lines.append(f"| {row.key} | {row.files} | {row.bytes} |")
        lines.append("")

    def _folder_table(title: str, rows: tuple[FolderCount, ...]) -> None:
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| folder | files | bytes |")
        lines.append("|---|---|---|")
        for row in rows:
            lines.append(f"| {row.folder} | {row.files} | {row.bytes} |")
        lines.append("")

    _category_table("By knowledge class", report.by_knowledge_class, "knowledge_class")
    _category_table("By format", report.by_format, "format")
    _folder_table("By top-level folder", report.by_top_level_folder)
    _folder_table("By level-2 folder", report.by_level2_folder)

    lines.append("## Duplicates")
    lines.append("")
    lines.append(f"- duplicate groups: {report.duplicates.duplicate_groups}")
    lines.append(f"- redundant bytes: {report.duplicates.redundant_bytes}")
    lines.append(f"- mirror-candidate paths: {report.duplicates.mirror_candidate_paths}")
    lines.append("")

    lines.append("## Archives")
    lines.append("")
    lines.append(f"- members total: {report.archives.members_total}")
    lines.append(f"- already present: {report.archives.already_present}")
    lines.append(f"- extracted new: {report.archives.extracted_new}")
    lines.append(f"- skipped (over limit): {report.archives.skipped_limit}")
    lines.append(f"- excluded: {report.archives.excluded}")
    lines.append("")

    _category_table("Sensitivity (counts only - no paths, docs/22)", report.sensitivity, "sensitivity")
    _category_table("Genre", report.genre, "genre")
    _category_table("Course", report.course, "course_id")

    lines.append("## Changes since the last scan (per root)")
    lines.append("")
    for change in report.changes_since_last_scan:
        lines.append(f"### {change.root_id}")
        lines.append("")
        if change.scan_id is None:
            lines.append("no scan recorded yet")
        else:
            lines.append(f"scan_id: {change.scan_id}")
            for change_type, count in sorted(change.counts_by_type.items()):
                lines.append(f"- {change_type}: {count}")
        lines.append("")

    lines.append("## PDF page census")
    lines.append("")
    lines.append(f"- available: {report.pdf_page_census['available']}")
    lines.append(f"- reason: {report.pdf_page_census['reason']}")
    lines.append("")
    return "\n".join(lines)


def render_csv_rows(report: ManifestReport) -> list[tuple[str, str, str, str]]:
    """Flatten every count into ``(section, key, files, bytes)`` rows - one CSV, every section, easy to parse."""
    rows: list[tuple[str, str, str, str]] = [
        ("totals", "files", str(report.total_files), ""),
        ("totals", "bytes", str(report.total_bytes), ""),
        ("totals", "blobs", str(report.total_blobs), ""),
        ("totals", "unique_bytes", str(report.total_unique_bytes), ""),
    ]
    category_sections: list[tuple[str, tuple[CategoryCount, ...]]] = [
        ("knowledge_class", report.by_knowledge_class),
        ("format", report.by_format),
        ("sensitivity", report.sensitivity),
        ("genre", report.genre),
        ("course", report.course),
    ]
    for section, items in category_sections:
        for item in items:
            rows.append((section, item.key, str(item.files), str(item.bytes)))
    folder_sections: list[tuple[str, tuple[FolderCount, ...]]] = [
        ("top_level_folder", report.by_top_level_folder),
        ("level2_folder", report.by_level2_folder),
    ]
    for section, folder_items in folder_sections:
        for folder_item in folder_items:
            rows.append((section, folder_item.folder, str(folder_item.files), str(folder_item.bytes)))
    rows.append(("duplicates", "duplicate_groups", str(report.duplicates.duplicate_groups), ""))
    rows.append(("duplicates", "redundant_bytes", str(report.duplicates.redundant_bytes), ""))
    rows.append(("duplicates", "mirror_candidate_paths", str(report.duplicates.mirror_candidate_paths), ""))
    rows.append(("archives", "members_total", str(report.archives.members_total), ""))
    rows.append(("archives", "already_present", str(report.archives.already_present), ""))
    rows.append(("archives", "extracted_new", str(report.archives.extracted_new), ""))
    rows.append(("archives", "skipped_limit", str(report.archives.skipped_limit), ""))
    rows.append(("archives", "excluded", str(report.archives.excluded), ""))
    for change in report.changes_since_last_scan:
        for change_type, count in sorted(change.counts_by_type.items()):
            rows.append((f"changes:{change.root_id}", change_type, str(count), ""))
    return rows


__all__ = [
    "MANIFEST_VERSION",
    "ArchivesSummary",
    "CategoryCount",
    "DuplicatesSummary",
    "FolderCount",
    "ManifestReport",
    "ScanChangeSummary",
    "build_manifest",
    "render_csv_rows",
    "render_markdown",
]
