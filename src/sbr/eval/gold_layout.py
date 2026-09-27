"""Pure, deterministic selection for the owner-verified MBI-Gold-Layout set (T-P3-03).

The real-corpus orchestrator probes only pages already chosen for MBI-Gold-Extract and turns each page into
a :class:`LayoutDescriptor`.  This module then applies priority-ordered bucket quotas without doing file or
registry I/O.  A page can satisfy several signals, but it is selected once and assigned to the first bucket
that consumes it.  The final catch-all bucket keeps the sample near its requested size while preserving an
honest coverage matrix when a specialist bucket has too few remaining candidates.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass

DEFAULT_TARGET_PAGES = 40
DEFAULT_SEED = 20_260_927


@dataclass(frozen=True, slots=True)
class LayoutDescriptor:
    """Layout signals for one already-selected PDF page."""

    blob_id: str
    page: int
    multi_column: bool = False
    headings_paragraphs: bool = False
    table_heavy: bool = False
    figures_with_captions: bool = False
    lists: bool = False
    headers_footers_page_numbers: bool = False
    unusual_reading_order: bool = False
    scanned: bool = False
    annotated: bool = False
    slide_like: bool = False
    plain_text_control: bool = False

    @property
    def key(self) -> tuple[str, int]:
        return self.blob_id, self.page


@dataclass(frozen=True, slots=True)
class LayoutSampleEntry:
    blob_id: str
    page: int
    bucket: str


@dataclass(frozen=True, slots=True)
class LayoutBucketSpec:
    name: str
    predicate: Callable[[LayoutDescriptor], bool]
    quota: int


def default_buckets() -> list[LayoutBucketSpec]:
    """Priority-ordered quotas: difficult/rare structures first, controls last."""
    return [
        LayoutBucketSpec("unusual_reading_order", lambda d: d.unusual_reading_order, 4),
        LayoutBucketSpec("multi_column", lambda d: d.multi_column, 5),
        LayoutBucketSpec("scanned", lambda d: d.scanned, 4),
        LayoutBucketSpec("annotated", lambda d: d.annotated, 4),
        LayoutBucketSpec("slide_like", lambda d: d.slide_like, 4),
        LayoutBucketSpec("table_heavy", lambda d: d.table_heavy, 4),
        LayoutBucketSpec("figures_with_captions", lambda d: d.figures_with_captions, 4),
        LayoutBucketSpec("lists", lambda d: d.lists, 3),
        LayoutBucketSpec("headers_footers_page_numbers", lambda d: d.headers_footers_page_numbers, 3),
        LayoutBucketSpec("headings_paragraphs", lambda d: d.headings_paragraphs, 3),
        LayoutBucketSpec("plain_text_control", lambda d: d.plain_text_control, 2),
        LayoutBucketSpec("diversity_fill", lambda _d: True, DEFAULT_TARGET_PAGES),
    ]


def select_layout_sample(
    descriptors: Sequence[LayoutDescriptor],
    *,
    buckets: Sequence[LayoutBucketSpec] | None = None,
    target_pages: int = DEFAULT_TARGET_PAGES,
    seed: int = DEFAULT_SEED,
) -> tuple[list[LayoutSampleEntry], dict[str, dict[str, int]]]:
    """Return a seeded page sample and per-bucket quota/eligible/selected counts."""
    specs = list(buckets) if buckets is not None else default_buckets()
    rng = random.Random(seed)  # noqa: S311 - reproducible sampling, not cryptography
    remaining = {descriptor.key: descriptor for descriptor in descriptors}
    entries: list[LayoutSampleEntry] = []
    coverage: dict[str, dict[str, int]] = {}

    for spec in specs:
        eligible = sorted(key for key, descriptor in remaining.items() if spec.predicate(descriptor))
        take = min(spec.quota, len(eligible), max(0, target_pages - len(entries)))
        chosen = rng.sample(eligible, take) if take else []
        for key in sorted(chosen):
            descriptor = remaining.pop(key)
            entries.append(LayoutSampleEntry(descriptor.blob_id, descriptor.page, spec.name))
        coverage[spec.name] = {"quota": spec.quota, "selected": len(chosen), "eligible_pool": len(eligible)}
        if len(entries) >= target_pages:
            break

    return entries, coverage


__all__ = [
    "DEFAULT_SEED",
    "DEFAULT_TARGET_PAGES",
    "LayoutBucketSpec",
    "LayoutDescriptor",
    "LayoutSampleEntry",
    "default_buckets",
    "select_layout_sample",
]
