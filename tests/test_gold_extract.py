"""T-P3-01: MBI-Gold-Extract stratified sample selection."""

from __future__ import annotations

from sbr.eval.gold_extract import (
    BlobDescriptor,
    BucketSpec,
    default_buckets,
    select_sample,
)


def _descriptor(blob_id: str, **overrides: object) -> BlobDescriptor:
    defaults: dict[str, object] = {
        "format": "pdf",
        "page_count": 10,
        "genre": None,
        "course_id": "MBI-123",
        "producer_class": "latex",
        "scanned": False,
        "annotated": False,
        "landscape": False,
        "has_omml": False,
    }
    defaults.update(overrides)
    return BlobDescriptor(blob_id=blob_id, **defaults)  # type: ignore[arg-type]


def test_select_sample_is_deterministic_for_the_same_seed() -> None:
    descriptors = [_descriptor(f"b{i}", genre="exam" if i % 2 == 0 else "solution") for i in range(50)]
    entries1, coverage1 = select_sample(descriptors, target_pages=20, seed=42)
    entries2, coverage2 = select_sample(descriptors, target_pages=20, seed=42)
    assert entries1 == entries2
    assert coverage1 == coverage2


def test_select_sample_differs_with_a_different_seed() -> None:
    descriptors = [_descriptor(f"b{i}", genre="exam") for i in range(50)]
    entries1, _ = select_sample(descriptors, target_pages=10, seed=1)
    entries2, _ = select_sample(descriptors, target_pages=10, seed=2)
    assert {e.blob_id for e in entries1} != {e.blob_id for e in entries2}


def test_a_blob_is_never_selected_twice_even_if_it_matches_multiple_buckets() -> None:
    """A single thesis PDF that is also scanned and landscape must only appear once in the sample - document
    diversity, not one blob quietly satisfying five buckets."""
    descriptors = [_descriptor("multi", genre="thesis", scanned=True, landscape=True, annotated=True)]
    entries, _ = select_sample(descriptors, target_pages=120, seed=1)
    assert len(entries) == 1
    assert entries[0].blob_id == "multi"


def test_rare_bucket_quota_is_honored_even_when_target_pages_would_otherwise_favor_abundant_buckets() -> None:
    """thesis is the first (highest-priority) bucket in the default list - it must fill its quota before any
    later, more abundant bucket eats the whole budget."""
    descriptors = [_descriptor(f"thesis{i}", genre="thesis") for i in range(20)] + [
        _descriptor(f"exam{i}", genre="exam") for i in range(200)
    ]
    entries, coverage = select_sample(descriptors, target_pages=30, seed=1)
    thesis_selected = sum(1 for e in entries if e.bucket == "thesis")
    assert thesis_selected == coverage["thesis"]["selected"]
    assert thesis_selected == min(6, 20)  # the default thesis bucket quota is 6


def test_coverage_reports_an_unfilled_bucket_honestly() -> None:
    """When the real eligible pool is smaller than a bucket's quota, coverage must show the shortfall, not
    silently pad it from elsewhere."""
    descriptors = [_descriptor("only_thesis", genre="thesis")]
    _, coverage = select_sample(descriptors, target_pages=120, seed=1)
    assert coverage["thesis"] == {"quota": 6, "selected": 1, "eligible_pool": 1}


def test_representative_page_avoids_page_one_on_long_documents() -> None:
    descriptors = [_descriptor("short", page_count=2), _descriptor("long", page_count=400)]
    buckets = [BucketSpec("all", lambda _d: True, 10)]
    entries, _ = select_sample(descriptors, buckets=buckets, target_pages=10, seed=1)
    pages = {e.blob_id: e.page for e in entries}
    assert pages["short"] == 1
    assert pages["long"] == 200


def test_representative_page_falls_back_to_page_one_when_page_count_is_unknown() -> None:
    descriptors = [_descriptor("unknown_pages", page_count=None)]
    buckets = [BucketSpec("all", lambda _d: True, 1)]
    entries, _ = select_sample(descriptors, buckets=buckets, target_pages=1, seed=1)
    assert entries[0].page == 1


def test_default_buckets_quotas_sum_to_at_least_the_default_target() -> None:
    """The default bucket list must be able to reach the ~120-page target in principle (quota sum), even
    though real-corpus eligible pools may fall short of some quotas."""
    total_quota = sum(spec.quota for spec in default_buckets())
    assert total_quota >= 120


def test_select_sample_never_exceeds_target_pages() -> None:
    descriptors = [_descriptor(f"b{i}", genre="textbook") for i in range(500)]
    entries, _ = select_sample(descriptors, target_pages=25, seed=1)
    assert len(entries) <= 25
