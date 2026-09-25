"""T-P2-09 twin candidate detection: stem/folder heuristics, storage, and reporting."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.ids import new_id
from sbr.registry.classify import classify_pending
from sbr.registry.hash import hash_pending
from sbr.registry.scan import scan_root
from sbr.registry.twins import find_twin_candidates
from sbr.schemas import PathObservation
from sbr.schemas.registry import RelationStatus, RelationType


def _open(config: SbrConfig) -> RegistryDB:
    db = RegistryDB.open(config)
    db.migrate()
    return db


def _run_pipeline(config: SbrConfig, db: RegistryDB) -> None:
    scan_root(config, db, "fx")
    hash_pending(config, db)
    classify_pending(config, db)


def _obs(relpath: str, blob_id: str) -> PathObservation:
    return PathObservation(
        obs_id=new_id("obs"),
        root_id="mbi",
        relpath=relpath,
        relpath_raw=relpath,
        display_name=relpath.rsplit("\\", 1)[-1],
        blob_id=blob_id,
        size=1,
        mtime_ns=1,
        first_seen_scan=new_id("scan"),
        last_seen_scan=new_id("scan"),
        activity_id=new_id("act"),
    )


def _blob(seed: str) -> str:
    return "b3:" + (seed * 64)[:64]


def test_real_thesis_layout_same_folder_pairs_score_highest() -> None:
    pdfs = [
        _obs(r"BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit.pdf", _blob("1")),
        _obs(r"BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Bachelorarbeit.pdf", _blob("2")),
        _obs(r"BachelorArbeit\BAP\Bachelorarbeit.pdf", _blob("3")),  # no nearby office file: no candidate
    ]
    office = [
        _obs(r"BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit.docx", _blob("4")),
        _obs(r"BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit1.docx", _blob("5")),
        _obs(r"BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\BachelorarbeitCopy.docx", _blob("6")),
        _obs(r"BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Bachelorarbeit.docx", _blob("7")),
    ]

    candidates = find_twin_candidates(pdfs, office)
    by_pair = {(c.pdf_blob, c.office_blob): c for c in candidates}

    same_folder = by_pair[(_blob("1"), _blob("4"))]
    assert same_folder.confidence == 1.0
    assert same_folder.folder_distance == 0
    # "Bachelorarbeit1" is NOT stem-normalized to an exact match on purpose: a bare trailing digit is often a
    # meaningful identifier elsewhere in this corpus (exam/session numbers, chapter numbers), not a copy
    # marker, so it is deliberately not stripped. It still clears the similarity threshold via SequenceMatcher
    # overlap, just below 1.0.
    assert 0.9 < by_pair[(_blob("1"), _blob("5"))].confidence < 1.0
    assert by_pair[(_blob("1"), _blob("6"))].confidence == 1.0  # "BachelorarbeitCopy" is an explicit marker

    parent_folder = by_pair[(_blob("2"), _blob("7"))]
    assert parent_folder.confidence == 1.0
    assert parent_folder.folder_distance == 0

    cross_folder = by_pair[(_blob("1"), _blob("7"))]
    assert cross_folder.folder_distance == 1
    assert cross_folder.confidence < 1.0  # distance-1 is discounted relative to same-folder

    assert not any(c.pdf_blob == _blob("3") for c in candidates)


def test_different_chapter_numbers_are_not_proposed_as_twins() -> None:
    """Regression: found on the real corpus - '..._Kap2_3_V2.pdf' and '..._Kap2_2_V2.ppsx' (different chapter
    segments of a lecture series) scored 0.958 before the digit-stripping fix, because the shared template
    text dominated the ratio despite the chapter number - the actually distinguishing part - differing."""
    pdfs = [_obs(r"Course\SS-2019_Kinematik_Kap2_3_V2.pdf", _blob("1"))]
    office = [_obs(r"Course\SS-2019_Kinematik_Kap2_2_V2.ppsx", _blob("2"))]

    assert find_twin_candidates(pdfs, office) == []


def test_different_lecture_sessions_sharing_a_template_are_not_proposed() -> None:
    """Regression: found on the real corpus - PDFs and a .doc from clearly different lecture dates/session
    numbers ("10 Ingenieurmathematik III 2010-03-29" vs "06 Ingenieurmathematik III 2008-08-27") scored 0.912
    before the fix, purely from the shared "Ingenieurmathematik III" template text."""
    pdfs = [_obs(r"Course\10 Ingenieurmathematik III 2010-03-29.pdf", _blob("1"))]
    office = [_obs(r"Course\06 Ingenieurmathematik III 2008-08-27.doc", _blob("2"))]

    assert find_twin_candidates(pdfs, office) == []


def test_office_lock_file_is_never_proposed_despite_string_similarity() -> None:
    """Regression: found on the real corpus - '~$chelorarbeit.docx' (a Word lock file, created while the real
    file is open) scored 0.857 against 'Bachelorarbeit.pdf' via genuine string similarity on the shared
    'chelorarbeit' substring. Lock files are never legitimate content and must be excluded outright."""
    pdfs = [_obs(r"Folder\Bachelorarbeit.pdf", _blob("1"))]
    office = [
        _obs(r"Folder\~$chelorarbeit.docx", _blob("2")),
        _obs(r"Folder\Bachelorarbeit.docx", _blob("3")),
    ]

    candidates = find_twin_candidates(pdfs, office)

    assert {c.office_blob for c in candidates} == {_blob("3")}


def test_dissimilar_stems_in_the_same_folder_are_not_proposed() -> None:
    pdfs = [_obs(r"Course\Skript.pdf", _blob("a"))]
    office = [_obs(r"Course\Uebung3.docx", _blob("b"))]

    assert find_twin_candidates(pdfs, office) == []


def test_distant_folders_are_never_proposed_even_with_identical_stems() -> None:
    pdfs = [_obs(r"CourseA\Deep\Nested\Report.pdf", _blob("a"))]
    office = [_obs(r"CourseB\Elsewhere\Report.docx", _blob("b"))]

    assert find_twin_candidates(pdfs, office) == []


def test_stage_persists_candidates_as_twin_candidate_relations(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    from sbr.registry.twins import detect_twin_candidates

    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Skript.pdf").write_bytes(b"%PDF-1.7\ncontent")
    (root / "Skript.docx").write_bytes(b"PK\x03\x04office")

    with _open(config) as db:
        _run_pipeline(config, db)
        result = detect_twin_candidates(config, db)
        relations = db.repo(reg.BLOB_RELATION).find()

        assert result.pairs_proposed == 1
        [relation] = relations
        assert relation.type is RelationType.TWIN_CANDIDATE
        assert relation.status is RelationStatus.CANDIDATE
        assert relation.confidence == 1.0
        assert relation.evidence == {"stem_similarity": 1.0, "folder_distance": 0}


def test_re_run_is_idempotent(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    from sbr.registry.twins import detect_twin_candidates

    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Skript.pdf").write_bytes(b"%PDF-1.7\ncontent")
    (root / "Skript.docx").write_bytes(b"PK\x03\x04office")

    with _open(config) as db:
        _run_pipeline(config, db)
        detect_twin_candidates(config, db)
        detect_twin_candidates(config, db)

        assert db.repo(reg.BLOB_RELATION).count() == 1


def test_cli_and_report_tool(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    import subprocess
    import sys

    from typer.testing import CliRunner

    from sbr.cli.app import app

    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Skript.pdf").write_bytes(b"%PDF-1.7\ncontent")
    (root / "Skript.docx").write_bytes(b"PK\x03\x04office")
    config_file = tmp_path / "twins.toml"
    config_file.write_text(
        "[roots]\n"
        f"sources = [{{ id = 'fx', path = '{root.as_posix()}' }}]\n"
        f"var = '{Path(config.roots.var).as_posix()}'\n"
        f"curation = '{Path(config.roots.curation).as_posix()}'\n"
        f"protected = ['{Path(config.roots.protected[0]).as_posix()}']\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    assert runner.invoke(app, ["scan", "--root", "fx", "--config", str(config_file)]).exit_code == 0
    assert runner.invoke(app, ["hash", "--config", str(config_file)]).exit_code == 0
    assert runner.invoke(app, ["classify", "--config", str(config_file)]).exit_code == 0

    result = runner.invoke(app, ["twins", "--config", str(config_file)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["pairs_proposed"] == 1

    json_report = tmp_path / "twins.json"
    markdown_report = tmp_path / "twins.md"
    completed = subprocess.run(
        [
            sys.executable,
            "tools/validate_twins.py",
            "--config",
            str(config_file),
            "--json-output",
            str(json_report),
            "--markdown-output",
            str(markdown_report),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(json_report.read_text(encoding="utf-8"))
    assert report["verdict"] is None
    assert report["sampled"] == 1
    assert "Human review artifact only" in markdown_report.read_text(encoding="utf-8")
