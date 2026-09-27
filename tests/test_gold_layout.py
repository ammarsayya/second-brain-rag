"""T-P3-03 prep: pure layout selection and gold-schema round trip."""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML
from tools.draft_gold_layout import analyze_pdf_page

from sbr.config import config_from_mapping
from sbr.eval.extract.goldfile import load_gold_samples
from sbr.eval.gold_layout import (
    LayoutBucketSpec,
    LayoutDescriptor,
    default_buckets,
    select_layout_sample,
)
from sbr.sourcefs import SourceFS


def _descriptor(blob_id: str, page: int = 1, **overrides: bool) -> LayoutDescriptor:
    values = {
        "multi_column": False,
        "headings_paragraphs": False,
        "table_heavy": False,
        "figures_with_captions": False,
        "lists": False,
        "headers_footers_page_numbers": False,
        "unusual_reading_order": False,
        "scanned": False,
        "annotated": False,
        "slide_like": False,
        "plain_text_control": False,
    }
    values.update(overrides)
    return LayoutDescriptor(blob_id=blob_id, page=page, **values)


def test_layout_selection_is_deterministic_for_same_seed() -> None:
    descriptors = [_descriptor(f"b{i}", multi_column=True) for i in range(30)]
    first = select_layout_sample(descriptors, target_pages=12, seed=42)
    second = select_layout_sample(descriptors, target_pages=12, seed=42)
    assert first == second


def test_layout_selection_changes_with_seed() -> None:
    descriptors = [_descriptor(f"b{i}", multi_column=True) for i in range(30)]
    first, _ = select_layout_sample(descriptors, target_pages=5, seed=1)
    second, _ = select_layout_sample(descriptors, target_pages=5, seed=2)
    assert {entry.blob_id for entry in first} != {entry.blob_id for entry in second}


def test_page_is_not_selected_twice_when_it_matches_many_buckets() -> None:
    descriptor = _descriptor("multi", multi_column=True, scanned=True, annotated=True, slide_like=True)
    entries, _ = select_layout_sample([descriptor], target_pages=40, seed=1)
    assert [(entry.blob_id, entry.page) for entry in entries] == [("multi", 1)]


def test_priority_bucket_quota_and_shortfall_are_reported() -> None:
    descriptors = [_descriptor(f"rare{i}", unusual_reading_order=True) for i in range(2)] + [
        _descriptor(f"common{i}", multi_column=True) for i in range(20)
    ]
    entries, coverage = select_layout_sample(descriptors, target_pages=8, seed=1)
    assert coverage["unusual_reading_order"] == {"quota": 4, "selected": 2, "eligible_pool": 2}
    assert sum(entry.bucket == "multi_column" for entry in entries) == 5


def test_diversity_fill_reaches_target_without_inventing_specialist_signals() -> None:
    descriptors = [_descriptor(f"plain{i}") for i in range(50)]
    entries, coverage = select_layout_sample(descriptors, target_pages=40, seed=7)
    assert len(entries) == 40
    assert coverage["diversity_fill"]["selected"] == 40


def test_default_quotas_can_reach_target() -> None:
    assert sum(bucket.quota for bucket in default_buckets()) >= 40


def test_custom_bucket_quota_is_honored() -> None:
    descriptors = [_descriptor(f"b{i}", lists=True) for i in range(10)]
    buckets = [LayoutBucketSpec("list_only", lambda descriptor: descriptor.lists, 3)]
    entries, coverage = select_layout_sample(descriptors, buckets=buckets, target_pages=10, seed=1)
    assert len(entries) == 3
    assert coverage["list_only"]["selected"] == 3


def test_heuristic_draft_round_trips_through_real_gold_loader(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "corpus" / "Regelungstechnik" / "skript.pdf"
    root = tmp_path / "source"
    root.mkdir()
    target = root / "fixture.pdf"
    target.write_bytes(fixture.read_bytes())
    protected = tmp_path / "protected"
    protected.mkdir()
    config = config_from_mapping(
        {
            "roots": {
                "sources": [{"id": "fx", "path": str(root)}],
                "var": str(tmp_path / "var"),
                "curation": str(tmp_path / "curation"),
                "protected": [str(protected)],
            }
        }
    )

    gold, _signals = analyze_pdf_page(target.read_bytes(), 1)
    annotation = tmp_path / "layout.yaml"
    with annotation.open("w", encoding="utf-8") as stream:
        YAML().dump(
            {
                "samples": [
                    {"sample_id": "layout-001", "root_id": "fx", "relpath": "fixture.pdf", "page": 1, "gold": gold}
                ]
            },
            stream,
        )

    [(pdf_bytes, page, parsed)] = load_gold_samples(SourceFS(config), annotation)
    assert pdf_bytes == fixture.read_bytes()
    assert page == 1
    assert parsed.page == 1
    assert parsed.blocks
    assert all(block.kind for block in parsed.blocks)
