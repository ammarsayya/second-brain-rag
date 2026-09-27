from __future__ import annotations

import io
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from ruamel.yaml import YAML

from sbr.eval.extract.goldfile import load_gold_samples
from sbr.eval.gold_math import MathCandidate, default_quotas, difficulty_tag, select_math_sample
from sbr.sourcefs import SourceFS


class _FakeSourceFS:
    def read_bytes(self, root_id: str, relpath: str) -> bytes:
        assert root_id == "mbi"
        assert relpath == "thesis.docx"
        return b"synthetic-office-bytes"


@pytest.mark.parametrize(
    ("expression", "display", "expected"),
    [
        ("x + y", False, "inline_simple"),
        (r"x_1^2 + y_2^2 + z_3^2", False, "inline_complex"),
        (r"E = mc^2", True, "display_simple"),
        (r"\int_0^1 \frac{x^2}{1+x}\,dx", True, "display_complex"),
        (r"\begin{aligned}x&=1\\y&=2\end{aligned}", True, "display_complex"),
    ],
)
def test_difficulty_tag_is_transparent(expression: str, display: bool, expected: str) -> None:
    assert difficulty_tag(expression, display=display) == expected


def test_default_quotas_sum_to_target_and_preserve_source_ratio() -> None:
    quotas = default_quotas(300)
    assert sum(quotas.values()) == 300
    assert sum(value for (source, _tag), value in quotas.items() if source == "omml_exact") == 180
    assert sum(value for (source, _tag), value in quotas.items() if source == "pdf_native") == 120


def test_selection_is_seeded_unique_and_fills_sparse_cells() -> None:
    candidates = [
        MathCandidate(f"omml-{index:03d}", "blob-o", "omml_exact", "display_simple") for index in range(12)
    ] + [MathCandidate(f"pdf-{index:03d}", "blob-p", "pdf_native", "inline_simple") for index in range(12)]
    quotas = {
        ("omml_exact", "inline_complex"): 5,
        ("omml_exact", "display_simple"): 5,
        ("pdf_native", "display_complex"): 5,
        ("pdf_native", "inline_simple"): 5,
    }

    first, coverage = select_math_sample(candidates, target_equations=20, seed=17, quotas=quotas)
    second, _ = select_math_sample(candidates, target_equations=20, seed=17, quotas=quotas)

    assert [item.candidate_id for item in first] == [item.candidate_id for item in second]
    assert len(first) == len({item.candidate_id for item in first}) == 20
    assert sum(item.source_group == "omml_exact" for item in first) == 10
    assert sum(item.source_group == "pdf_native" for item in first) == 10
    assert coverage["omml_exact.inline_complex"] == {"quota": 5, "eligible_pool": 0, "selected": 0}
    assert coverage["omml_exact.display_simple"]["selected"] == 10


def test_duplicate_candidate_ids_are_refused() -> None:
    candidate = MathCandidate("same", "blob", "omml_exact", "inline_simple")
    with pytest.raises(ValueError, match="unique"):
        select_math_sample([candidate, candidate])


def test_real_omml_shape_round_trips_through_gold_loader() -> None:
    """The shape emitted for an exact entry remains compatible with the existing harness convention."""
    document = {
        "samples": [
            {
                "sample_id": "math-omml-001",
                "root_id": "mbi",
                "relpath": "thesis.docx",
                "page": 1,
                "source_group": "omml_exact",
                "source_kind": "omml_exact",
                "status": "candidate_exact_unverified",
                "latex": r"\frac{F}{m}",
                "difficulty_tag": "display_simple",
                "gold": {
                    "blocks": [],
                    "equations": [{"latex_normalized": r"\frac{F}{m}", "source_kind": "omml_exact"}],
                    "tables": [],
                    "figures": [],
                },
            }
        ]
    }
    stream = io.StringIO()
    YAML().dump(document, stream)

    with patch.object(Path, "read_text", return_value=stream.getvalue()):
        loaded = load_gold_samples(cast(SourceFS, _FakeSourceFS()), Path("synthetic-math.yaml"))
    assert loaded[0][0] == b"synthetic-office-bytes"
    assert loaded[0][2].equations[0].latex_normalized == r"\frac{F}{m}"
    assert loaded[0][2].equations[0].source_kind == "omml_exact"
