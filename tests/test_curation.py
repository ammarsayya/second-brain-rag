"""T-P1-12: curation/*.yaml schemas, loader, validation and append-only approvals."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from sbr.curation import (
    Approval,
    ApprovalDecision,
    CanonicalOverride,
    ConceptCurationAction,
    CurationError,
    ExclusionScope,
    TaxonomyConcept,
    append_approval,
    load_approvals,
    load_canonical_overrides,
    load_concept_curation,
    load_course_map,
    load_curation_file,
    load_exclusions,
    load_sensitivity_overrides,
    load_taxonomy,
)

CANONICAL = "b3:" + "a" * 64
ALIAS = "b3:" + "b" * 64
T0 = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


# -- the real, git-tracked seed files load cleanly -----------------------------------------------------------


def test_the_seeded_curation_files_all_load_empty() -> None:
    root = Path(__file__).resolve().parent.parent / "curation"
    assert load_taxonomy(root / "taxonomy.yaml").records == ()
    assert load_course_map(root / "course_map.yaml").records == ()
    assert load_canonical_overrides(root / "canonical_overrides.yaml").records == ()
    assert load_exclusions(root / "exclusions.yaml").records == ()
    assert load_sensitivity_overrides(root / "sensitivity_overrides.yaml").records == ()
    assert load_concept_curation(root / "concept_curation.yaml").records == ()
    assert load_approvals(root / "approvals.yaml").records == ()


# -- schemas round-trip real content -------------------------------------------------------------------------


def test_taxonomy_round_trips(tmp_path: Path) -> None:
    p = tmp_path / "taxonomy.yaml"
    p.write_text(
        "concepts:\n"
        "  - concept_id: control_theory\n"
        "    label_en: Control theory\n"
        "    label_de: Regelungstechnik\n"
        "    narrower: [pid_control]\n"
        "  - concept_id: pid_control\n"
        "    label_en: PID control\n"
        "    label_de: PID-Regelung\n"
        "    broader: [control_theory]\n",
        encoding="utf-8",
    )
    cf = load_taxonomy(p)
    assert [c.concept_id for c in cf.records] == ["control_theory", "pid_control"]
    assert cf.records[0].narrower == ["pid_control"]


def test_course_map_allows_mixed_case_owner_abbreviations(tmp_path: Path) -> None:
    p = tmp_path / "course_map.yaml"
    p.write_text(
        "courses:\n"
        "  - course_id: Reg1\n"
        "    name: Regelungstechnik 1\n"
        "    aliases: [RGT, Reg1]\n"
        "    folder_patterns: ['Regelungstechnik/**']\n",
        encoding="utf-8",
    )
    [course] = load_course_map(p).records
    assert course.course_id == "Reg1"
    assert course.aliases == ["RGT", "Reg1"]


def test_canonical_override_requires_at_least_one_alias() -> None:
    with pytest.raises(Exception, match="at least 1"):
        CanonicalOverride(canonical=CANONICAL, aliases=[])


def test_exclusion_and_sensitivity_override_scopes(tmp_path: Path) -> None:
    exclusions = tmp_path / "exclusions.yaml"
    exclusions.write_text("exclusions:\n  - scope: path\n    pattern: '**/thumbs.db'\n", encoding="utf-8")
    [excl] = load_exclusions(exclusions).records
    assert excl.scope is ExclusionScope.PATH

    overrides = tmp_path / "sensitivity_overrides.yaml"
    overrides.write_text(
        f"overrides:\n  - scope: blob\n    pattern: '{ALIAS}'\n    sensitivity: restricted\n", encoding="utf-8"
    )
    [ovr] = load_sensitivity_overrides(overrides).records
    assert ovr.sensitivity == "restricted"


def test_concept_curation_rename_action(tmp_path: Path) -> None:
    p = tmp_path / "concept_curation.yaml"
    p.write_text("entries:\n  - concept_id: old_name\n    action: rename\n    renamed_to: new_name\n", encoding="utf-8")
    [entry] = load_concept_curation(p).records
    assert entry.action is ConceptCurationAction.RENAME
    assert entry.renamed_to == "new_name"


# -- rejection with line numbers ------------------------------------------------------------------------------


def test_syntactically_invalid_yaml_is_rejected_with_a_line_number(tmp_path: Path) -> None:
    p = tmp_path / "broken.yaml"
    p.write_text("concepts:\n  - concept_id: a\n  bad indent here\n", encoding="utf-8")
    with pytest.raises(CurationError, match=r"line \d+"):
        load_taxonomy(p)


def test_a_missing_required_field_is_rejected_naming_the_entry_and_line(tmp_path: Path) -> None:
    p = tmp_path / "taxonomy.yaml"
    p.write_text(
        "concepts:\n  - concept_id: ok_one\n    label_en: Ok\n    label_de: Ok\n  - concept_id: missing_labels\n",
        encoding="utf-8",
    )
    with pytest.raises(CurationError, match="entry 1"):
        load_taxonomy(p)


def test_an_unknown_field_is_rejected() -> None:
    with pytest.raises(Exception, match="Extra inputs"):
        TaxonomyConcept(concept_id="x", label_en="X", label_de="X", made_up_field=True)  # type: ignore[call-arg]


def test_a_non_mapping_top_level_document_is_rejected(tmp_path: Path) -> None:
    p = tmp_path / "taxonomy.yaml"
    p.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(CurationError, match="expected a mapping"):
        load_taxonomy(p)


def test_a_missing_file_is_rejected_cleanly(tmp_path: Path) -> None:
    with pytest.raises(CurationError, match="not found"):
        load_taxonomy(tmp_path / "does-not-exist.yaml")


def test_a_bare_list_file_that_is_not_a_list_is_rejected(tmp_path: Path) -> None:
    p = tmp_path / "approvals.yaml"
    p.write_text("not_a_list: true\n", encoding="utf-8")
    with pytest.raises(CurationError, match="expected a list"):
        load_curation_file(p, Approval, list_key=None)


# -- comments survive a load (round-trip, "where feasible") --------------------------------------------------


def test_loading_does_not_require_stripping_comments(tmp_path: Path) -> None:
    """The loader itself is read-only; comments are untouched because the file is never rewritten by a read."""
    p = tmp_path / "taxonomy.yaml"
    original = (
        "# a human note explaining this concept\nconcepts:\n  - concept_id: x\n    label_en: X\n    label_de: X\n"
    )
    p.write_text(original, encoding="utf-8")
    load_taxonomy(p)
    assert p.read_text(encoding="utf-8") == original


# -- append-only approvals -------------------------------------------------------------------------------------


def approval(approval_id: str = "app_001", **over: object) -> Approval:
    base: dict[str, object] = {
        "approval_id": approval_id,
        "kind": "external_research",
        "subject": "https://example.org/paper",
        "decision": ApprovalDecision.APPROVED,
        "decided_by": "user:owner",
        "decided_at": T0,
    }
    base.update(over)
    return Approval.model_validate(base)


def test_append_approval_creates_the_file_if_absent(tmp_path: Path) -> None:
    p = tmp_path / "approvals.yaml"
    append_approval(p, approval())
    [rec] = load_approvals(p).records
    assert rec.approval_id == "app_001"
    assert rec.decision is ApprovalDecision.APPROVED


def test_append_approval_preserves_existing_entries_and_their_comments(tmp_path: Path) -> None:
    p = tmp_path / "approvals.yaml"
    p.write_text(
        "# first approval, granted after reviewing the license\n"
        "- approval_id: app_000\n"
        "  kind: external_research\n"
        "  subject: https://example.org/first\n"
        "  decision: approved\n"
        "  decided_by: user:owner\n"
        "  decided_at: 2026-01-01T00:00:00Z\n",
        encoding="utf-8",
    )
    append_approval(p, approval("app_001"))

    text = p.read_text(encoding="utf-8")
    assert "# first approval, granted after reviewing the license" in text
    records = load_approvals(p).records
    assert [r.approval_id for r in records] == ["app_000", "app_001"]


def test_append_approval_refuses_a_duplicate_approval_id(tmp_path: Path) -> None:
    p = tmp_path / "approvals.yaml"
    append_approval(p, approval("app_001"))
    with pytest.raises(CurationError, match="already recorded"):
        append_approval(p, approval("app_001"))
    assert len(load_approvals(p).records) == 1  # the rejected duplicate never touched the file


def test_append_approval_refuses_a_non_list_approvals_file(tmp_path: Path) -> None:
    p = tmp_path / "approvals.yaml"
    p.write_text("not_a_list: true\n", encoding="utf-8")
    with pytest.raises(CurationError, match="bare list"):
        append_approval(p, approval())
