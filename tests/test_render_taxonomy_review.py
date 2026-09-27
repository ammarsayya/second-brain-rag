from __future__ import annotations

from pathlib import Path

from tools.render_taxonomy_review import render_taxonomy_review

DEFAULT_OUTPUT = Path("eval/gold/taxonomy/review/index.html")


def test_render_real_taxonomy_review() -> None:
    output = DEFAULT_OUTPUT

    summary = render_taxonomy_review(
        Path("curation/taxonomy.yaml"),
        Path("curation/course_map.yaml"),
        output,
    )

    assert output.is_file()
    rendered = output.read_text(encoding="utf-8")
    assert summary["concept_count"] == 43
    assert summary["course_count"] == 42
    assert "mathematical_and_physical_foundations" in rendered
    assert "finite_element_methods" in rendered
    assert "MBI-101" in rendered
    assert 'id="unmapped-ambiguous"' in rendered
    assert "Concepts with zero directly mapped courses" in rendered
    assert 'id="cross-disciplinary"' in rendered
    assert "Owner decision: APPROVE / REQUEST CHANGES" in rendered
