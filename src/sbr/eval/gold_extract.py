"""MBI-Gold-Extract sample selection (T-P3-01): a stratified, seeded, reproducible pick of ~120 (blob, page)
references from the corpus's canonical blobs, for the extraction-technology spikes (T-P3-05 onward) to run
against. Pure selection logic only - no file I/O, no registry access; see ``tools/select_gold_extract_sample.py``
for the real-corpus orchestrator that gathers :class:`BlobDescriptor` rows and calls :func:`select_sample` here.

Stratification is bucket-quota, priority-ordered, not a full factorial coverage matrix: with a ~120-item
budget and roughly genre(8) x producer(5) x domain(84%-mapped) x four independent shape flags, a full cross
product has far more cells than samples could ever fill. Instead, an ORDERED list of buckets (rarer/more
critical document shapes first - thesis, scanned, annotated, slide-like, native-OMML math - then the more
common per-genre buckets) each gets a small quota; buckets are filled in order from the remaining
not-yet-selected pool, so a rare-but-important shape is guaranteed representation before the budget is spent
on abundant, easy-to-satisfy categories. A blob selected for one bucket is removed from every other bucket's
pool - the goal is document/page *diversity*, not letting one thesis PDF quietly satisfy five buckets at once.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass

DEFAULT_TARGET_PAGES = 120
DEFAULT_SEED = 20_260_926


@dataclass(frozen=True, slots=True)
class BlobDescriptor:
    """Everything the stratifier needs to know about one canonical blob, gathered by the real-corpus probe."""

    blob_id: str
    format: str
    page_count: int | None
    genre: str | None
    course_id: str | None
    producer_class: str | None  # PDF only; None for Office formats
    scanned: bool
    annotated: bool
    landscape: bool
    has_omml: bool


@dataclass(frozen=True, slots=True)
class GoldSampleEntry:
    blob_id: str
    page: int  # 1-based
    bucket: str  # which bucket this entry was selected to satisfy


@dataclass(frozen=True, slots=True)
class BucketSpec:
    name: str
    predicate: Callable[[BlobDescriptor], bool]
    quota: int


def default_buckets() -> list[BucketSpec]:
    """The priority-ordered bucket list. Rarer/more critical shapes first (see module docstring)."""
    return [
        BucketSpec("thesis", lambda d: d.genre == "thesis", 6),
        BucketSpec("scanned", lambda d: d.scanned, 10),
        BucketSpec("annotated", lambda d: d.annotated, 6),
        BucketSpec("landscape_slide_like", lambda d: d.landscape, 8),
        BucketSpec("office_with_omml", lambda d: d.has_omml, 10),
        BucketSpec(
            "office_without_omml", lambda d: d.format in {"docx", "pptx", "doc", "ppt", "ppsx"} and not d.has_omml, 6
        ),
        BucketSpec("pdf_producer_latex", lambda d: d.producer_class == "latex", 6),
        BucketSpec("pdf_producer_word", lambda d: d.producer_class == "word", 6),
        BucketSpec("pdf_producer_powerpoint", lambda d: d.producer_class == "powerpoint", 6),
        BucketSpec("genre_exam", lambda d: d.genre == "exam", 8),
        BucketSpec("genre_solution", lambda d: d.genre == "solution", 8),
        BucketSpec("genre_exercise", lambda d: d.genre == "exercise", 8),
        BucketSpec("genre_script", lambda d: d.genre == "script", 8),
        BucketSpec("genre_lab", lambda d: d.genre == "lab", 6),
        BucketSpec("genre_report", lambda d: d.genre == "report", 4),
        BucketSpec("genre_textbook", lambda d: d.genre == "textbook", 10),
        BucketSpec("unmapped_course", lambda d: d.course_id is None, 6),
        BucketSpec("unclassified_genre", lambda d: d.genre is None, 8),
    ]


def representative_page(page_count: int | None) -> int:
    """A page likely to have real content: page 1 for a short document, otherwise a middle page - avoiding
    a title/cover page on anything long enough to have one.

    Public (not just an internal helper of :func:`select_sample`): the real-corpus probe
    (``tools/select_gold_extract_sample.py``) needs to pick the SAME page to compute a blob's shape signals
    (scanned/annotated/landscape) on, before the final selection even runs - otherwise the probed page and
    the page that ends up in the gold sample could silently disagree.
    """
    if page_count is None or page_count <= 3:
        return 1
    return max(1, page_count // 2)


def select_sample(
    descriptors: Sequence[BlobDescriptor],
    *,
    buckets: Sequence[BucketSpec] | None = None,
    target_pages: int = DEFAULT_TARGET_PAGES,
    seed: int = DEFAULT_SEED,
) -> tuple[list[GoldSampleEntry], dict[str, dict[str, int]]]:
    """Pure, deterministic: the same inputs always produce the same sample. Returns (entries, coverage)."""
    bucket_specs = list(buckets) if buckets is not None else default_buckets()
    rng = random.Random(seed)  # noqa: S311 - deterministic sampling for reproducible gold-set selection, not crypto
    remaining = {d.blob_id: d for d in descriptors}

    entries: list[GoldSampleEntry] = []
    coverage: dict[str, dict[str, int]] = {}
    for spec in bucket_specs:
        eligible = sorted(bid for bid, d in remaining.items() if spec.predicate(d))
        take = min(spec.quota, len(eligible), max(0, target_pages - len(entries)))
        chosen = rng.sample(eligible, take) if take > 0 else []
        for blob_id in sorted(chosen):
            descriptor = remaining.pop(blob_id)
            entries.append(
                GoldSampleEntry(blob_id=blob_id, page=representative_page(descriptor.page_count), bucket=spec.name)
            )
        coverage[spec.name] = {"quota": spec.quota, "selected": len(chosen), "eligible_pool": len(eligible)}
        if len(entries) >= target_pages:
            break
    return entries, coverage


__all__ = [
    "DEFAULT_SEED",
    "DEFAULT_TARGET_PAGES",
    "BlobDescriptor",
    "BucketSpec",
    "GoldSampleEntry",
    "default_buckets",
    "representative_page",
    "select_sample",
]
