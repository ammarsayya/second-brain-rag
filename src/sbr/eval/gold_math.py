"""Pure selection and difficulty tagging for MBI-Gold-Math (T-P3-02 prep).

The real-corpus orchestrator supplies equation candidates.  This module only classifies their structural
difficulty and selects a reproducible source-group x difficulty sample.  ``pdf_native`` means a crop selected
for later model drafting; it is deliberately not a DocIR ``source_kind`` because no recognition has happened.
"""

from __future__ import annotations

import random
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

DEFAULT_TARGET_EQUATIONS = 300
DEFAULT_SEED = 20_260_927

SOURCE_GROUPS = ("omml_exact", "pdf_native")
DIFFICULTY_TAGS = ("inline_simple", "inline_complex", "display_simple", "display_complex")

_COMPLEX_LATEX = re.compile(
    r"\\begin\{|\\(?:d?frac|tfrac|cfrac|int|iint|iiint|sum|prod|lim|sqrt|cases|matrix|aligned|substack)\b"
)
_SCRIPTS = re.compile(r"[_^](?:\{[^{}]*\}|[A-Za-z0-9])")


@dataclass(frozen=True, slots=True)
class MathCandidate:
    """One independently located equation candidate, with no corpus bytes attached."""

    candidate_id: str
    blob_id: str
    source_group: str
    difficulty_tag: str

    def __post_init__(self) -> None:
        if self.source_group not in SOURCE_GROUPS:
            raise ValueError(f"unsupported source_group: {self.source_group}")
        if self.difficulty_tag not in DIFFICULTY_TAGS:
            raise ValueError(f"unsupported difficulty_tag: {self.difficulty_tag}")


def difficulty_tag(latex_or_text: str, *, display: bool) -> str:
    """Classify presentation plus a deliberately simple, documented structural-complexity proxy.

    Complex means any environment/high-order operator, two or more fractions, three or more script
    occurrences, an explicit TeX line break, or a long expression.  For PDF candidates the input is only
    used to tag the crop; it is never retained or promoted to LaTeX ground truth.
    """
    compact = " ".join(latex_or_text.split())
    complex_structure = (
        bool(_COMPLEX_LATEX.search(compact))
        or compact.count(r"\frac") >= 2
        or len(_SCRIPTS.findall(compact)) >= 3
        or r"\\" in compact
        or len(compact) >= 80
    )
    return f"{'display' if display else 'inline'}_{'complex' if complex_structure else 'simple'}"


def default_quotas(target_equations: int = DEFAULT_TARGET_EQUATIONS) -> dict[tuple[str, str], int]:
    """Return balanced 60% OMML / 40% PDF-native quotas, split evenly by difficulty cell."""
    if target_equations < 0:
        raise ValueError("target_equations must be non-negative")
    omml_target = round(target_equations * 0.6)
    source_targets = {"omml_exact": omml_target, "pdf_native": target_equations - omml_target}
    quotas: dict[tuple[str, str], int] = {}
    for source_group in SOURCE_GROUPS:
        base, remainder = divmod(source_targets[source_group], len(DIFFICULTY_TAGS))
        for index, tag in enumerate(DIFFICULTY_TAGS):
            quotas[(source_group, tag)] = base + (index < remainder)
    return quotas


def select_math_sample(
    candidates: Sequence[MathCandidate],
    *,
    target_equations: int = DEFAULT_TARGET_EQUATIONS,
    seed: int = DEFAULT_SEED,
    quotas: Mapping[tuple[str, str], int] | None = None,
) -> tuple[list[MathCandidate], dict[str, dict[str, int]]]:
    """Select deterministically by cell, then fill source deficits and finally the global target.

    Each candidate id must be unique.  Coverage reports the requested quota, original eligible pool and
    final selected count for every source-group x difficulty cell, including fallback selections.
    """
    by_id = {candidate.candidate_id: candidate for candidate in candidates}
    if len(by_id) != len(candidates):
        raise ValueError("candidate_id values must be unique")
    requested = dict(quotas) if quotas is not None else default_quotas(target_equations)
    rng = random.Random(seed)  # noqa: S311 - reproducible gold sampling, not cryptography
    remaining = dict(by_id)
    selected: list[MathCandidate] = []

    eligible_counts = Counter((item.source_group, item.difficulty_tag) for item in candidates)
    for source_group in SOURCE_GROUPS:
        for tag in DIFFICULTY_TAGS:
            quota = requested.get((source_group, tag), 0)
            eligible_ids = sorted(
                candidate_id
                for candidate_id, item in remaining.items()
                if item.source_group == source_group and item.difficulty_tag == tag
            )
            available_budget = max(0, target_equations - len(selected))
            chosen = rng.sample(eligible_ids, min(quota, len(eligible_ids), available_budget))
            for candidate_id in sorted(chosen):
                selected.append(remaining.pop(candidate_id))

    source_targets = Counter[str]()
    for (source_group, _tag), quota in requested.items():
        source_targets[source_group] += quota
    for source_group in SOURCE_GROUPS:
        deficit = max(0, source_targets[source_group] - sum(item.source_group == source_group for item in selected))
        eligible_ids = sorted(
            candidate_id for candidate_id, item in remaining.items() if item.source_group == source_group
        )
        for candidate_id in sorted(rng.sample(eligible_ids, min(deficit, len(eligible_ids)))):
            selected.append(remaining.pop(candidate_id))

    global_deficit = max(0, target_equations - len(selected))
    for candidate_id in sorted(rng.sample(sorted(remaining), min(global_deficit, len(remaining)))):
        selected.append(remaining.pop(candidate_id))

    selected_counts = Counter((item.source_group, item.difficulty_tag) for item in selected)
    coverage = {
        f"{source_group}.{tag}": {
            "quota": requested.get((source_group, tag), 0),
            "eligible_pool": eligible_counts[(source_group, tag)],
            "selected": selected_counts[(source_group, tag)],
        }
        for source_group in SOURCE_GROUPS
        for tag in DIFFICULTY_TAGS
    }
    return selected, coverage


__all__ = [
    "DEFAULT_SEED",
    "DEFAULT_TARGET_EQUATIONS",
    "DIFFICULTY_TAGS",
    "SOURCE_GROUPS",
    "MathCandidate",
    "default_quotas",
    "difficulty_tag",
    "select_math_sample",
]
