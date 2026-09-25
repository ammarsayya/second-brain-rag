"""T-P2-11 course and abbreviation mapping."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from sbr.config import SbrConfig
from sbr.curation import CourseMapEntry
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.registry.classify import classify_pending
from sbr.registry.courses import ALIAS_CONFIDENCE, PATTERN_CONFIDENCE, build_matchers, classify_course
from sbr.registry.hash import hash_pending
from sbr.registry.scan import scan_root


def _open(config: SbrConfig) -> RegistryDB:
    db = RegistryDB.open(config)
    db.migrate()
    return db


def _run_pipeline(config: SbrConfig, db: RegistryDB) -> None:
    scan_root(config, db, "fx")
    hash_pending(config, db)
    classify_pending(config, db)


def _course_map_yaml(entries: str) -> str:
    return "courses:\n" + entries


def test_alias_match_picks_the_correct_course() -> None:
    matchers = build_matchers(
        [
            CourseMapEntry(course_id="MBI-123", name="Statik", aliases=["Statik"], folder_patterns=[]),
            CourseMapEntry(course_id="MBI-130", name="Kinematik", aliases=["kinematik"], folder_patterns=[]),
        ]
    )
    decision = classify_course(["mechanical", "statik", "tut"], matchers)
    assert decision.course_id == "MBI-123"
    assert decision.confidence == ALIAS_CONFIDENCE


def test_unmatched_folder_is_explicitly_unknown() -> None:
    matchers = build_matchers(
        [CourseMapEntry(course_id="MBI-123", name="Statik", aliases=["Statik"], folder_patterns=[])]
    )
    decision = classify_course(["books", "studium", "lernen"], matchers)
    assert decision.course_id is None
    assert decision.confidence is None


def test_more_specific_nested_pattern_overrides_a_broader_ancestor_default() -> None:
    """Regression scenario this map relies on: 'BachelorArbeit\\Praxisphase' must win over the broader
    'BachelorArbeit' default for files under it, since Praxisphase is a distinct module (MBI-215) from the
    thesis itself (MBI-216)."""
    matchers = build_matchers(
        [
            CourseMapEntry(course_id="MBI-216", name="Bachelorarbeit", aliases=[], folder_patterns=["BachelorArbeit"]),
            CourseMapEntry(
                course_id="MBI-215", name="Praxisphase", aliases=[], folder_patterns=["BachelorArbeit\\Praxisphase"]
            ),
        ]
    )
    inside_praxisphase = classify_course(["bachelorarbeit", "praxisphase", "bericht"], matchers)
    assert inside_praxisphase.course_id == "MBI-215"
    assert inside_praxisphase.confidence == PATTERN_CONFIDENCE

    elsewhere_in_thesis_tree = classify_course(["bachelorarbeit", "matlab", "projekte"], matchers)
    assert elsewhere_in_thesis_tree.course_id == "MBI-216"


def test_deeper_alias_match_beats_a_shallower_pattern_match() -> None:
    """Regression scenario this map relies on: 'Mechanical\\physik' is a broad 2-segment default (Physik 1),
    but a file under the deeper 'Phy2' subfolder must resolve to Physik 2 instead, even though the pattern has
    fewer tokens than the physik default - depth wins over matcher length."""
    matchers = build_matchers(
        [
            CourseMapEntry(course_id="MBI-102", name="Physik 1", aliases=[], folder_patterns=["Mechanical\\physik"]),
            CourseMapEntry(course_id="MBI-127", name="Physik 2", aliases=["Phy2"], folder_patterns=[]),
        ]
    )
    decision = classify_course(["mechanical", "physik", "physik", "phy2", "sk"], matchers)
    assert decision.course_id == "MBI-127"


def test_pattern_match_outranks_alias_match_at_equal_depth() -> None:
    matchers = build_matchers(
        [
            CourseMapEntry(course_id="ALIAS-ONLY", name="x", aliases=["reg1"], folder_patterns=[]),
            CourseMapEntry(
                course_id="PATTERN", name="y", aliases=[], folder_patterns=["mechanical\\regelungstechnik\\reg1"]
            ),
        ]
    )
    decision = classify_course(["mechanical", "regelungstechnik", "reg1"], matchers)
    assert decision.course_id == "PATTERN"
    assert decision.confidence == PATTERN_CONFIDENCE


def test_stage_persists_course_and_preserves_existing_genre(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    from sbr.registry.courses import classify_courses
    from sbr.registry.genre import classify_genres

    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Statik").mkdir()
    (root / "Statik" / "Klausur_SS2019.pdf").write_bytes(b"%PDF-1.7\nexam")

    curation_dir = Path(config.roots.curation)
    curation_dir.mkdir(parents=True, exist_ok=True)
    (curation_dir / "course_map.yaml").write_text(
        _course_map_yaml('  - course_id: "MBI-123"\n    name: "Statik"\n    aliases: ["Statik"]\n'),
        encoding="utf-8",
    )

    with _open(config) as db:
        _run_pipeline(config, db)
        genre_result = classify_genres(config, db)
        course_result = classify_courses(config, db)

        assert genre_result.classified == 1
        assert course_result.classified == 1
        assert course_result.unknown == 0

        [classification] = db.repo(reg.BLOB_CLASSIFICATION).find()
        assert classification.course_id == "MBI-123"
        assert classification.course_confidence == ALIAS_CONFIDENCE
        # the genre this blob already had must survive the courses stage's upsert unchanged
        assert classification.genre == "exam"


def test_stage_leaves_unmatched_folders_unclassified(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    from sbr.registry.courses import classify_courses

    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "books").mkdir()
    (root / "books" / "some_novel.pdf").write_bytes(b"%PDF-1.7\nnot a course document")

    curation_dir = Path(config.roots.curation)
    curation_dir.mkdir(parents=True, exist_ok=True)
    (curation_dir / "course_map.yaml").write_text(
        _course_map_yaml('  - course_id: "MBI-123"\n    name: "Statik"\n    aliases: ["Statik"]\n'),
        encoding="utf-8",
    )

    with _open(config) as db:
        _run_pipeline(config, db)
        result = classify_courses(config, db)

        assert result.considered == 1
        assert result.classified == 0
        assert result.unknown == 1
        assert db.repo(reg.BLOB_CLASSIFICATION).count() == 0


def test_re_run_is_idempotent(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    from sbr.registry.courses import classify_courses

    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Statik").mkdir()
    (root / "Statik" / "Klausur_SS2019.pdf").write_bytes(b"%PDF-1.7\nexam")

    curation_dir = Path(config.roots.curation)
    curation_dir.mkdir(parents=True, exist_ok=True)
    (curation_dir / "course_map.yaml").write_text(
        _course_map_yaml('  - course_id: "MBI-123"\n    name: "Statik"\n    aliases: ["Statik"]\n'),
        encoding="utf-8",
    )

    with _open(config) as db:
        _run_pipeline(config, db)
        classify_courses(config, db)
        classify_courses(config, db)

        assert db.repo(reg.BLOB_CLASSIFICATION).count() == 1


def test_cli_prints_json(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from sbr.cli.app import app

    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Statik").mkdir()
    (root / "Statik" / "Klausur_SS2019.pdf").write_bytes(b"%PDF-1.7\nexam")

    curation_dir = Path(config.roots.curation)
    curation_dir.mkdir(parents=True, exist_ok=True)
    (curation_dir / "course_map.yaml").write_text(
        _course_map_yaml('  - course_id: "MBI-123"\n    name: "Statik"\n    aliases: ["Statik"]\n'),
        encoding="utf-8",
    )

    config_file = tmp_path / "courses.toml"
    config_file.write_text(
        "[roots]\n"
        f"sources = [{{ id = 'fx', path = '{root.as_posix()}' }}]\n"
        f"var = '{Path(config.roots.var).as_posix()}'\n"
        f"curation = '{curation_dir.as_posix()}'\n"
        f"protected = ['{Path(config.roots.protected[0]).as_posix()}']\n",
        encoding="utf-8",
    )
    runner = CliRunner()

    with _open(config) as db:
        _run_pipeline(config, db)

    result = runner.invoke(app, ["courses", "--config", str(config_file)])
    assert result.exit_code == 0, result.output
    assert '"classified": 1' in result.output


def test_validate_courses_reports_every_level3_folder_mapped_or_unknown(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    """Smoke test for tools/validate_courses.py, the report tool for this task's own acceptance criterion."""
    import json
    import subprocess
    import sys

    from typer.testing import CliRunner

    from sbr.cli.app import app

    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Statik").mkdir()
    (root / "Statik" / "Klausur_SS2019.pdf").write_bytes(b"%PDF-1.7\nexam")
    (root / "books").mkdir()
    (root / "books" / "novel.pdf").write_bytes(b"%PDF-1.7\nnot a course document")

    curation_dir = Path(config.roots.curation)
    curation_dir.mkdir(parents=True, exist_ok=True)
    (curation_dir / "course_map.yaml").write_text(
        _course_map_yaml('  - course_id: "MBI-123"\n    name: "Statik"\n    aliases: ["Statik"]\n'),
        encoding="utf-8",
    )

    config_file = tmp_path / "courses.toml"
    config_file.write_text(
        "[roots]\n"
        f"sources = [{{ id = 'fx', path = '{root.as_posix()}' }}]\n"
        f"var = '{Path(config.roots.var).as_posix()}'\n"
        f"curation = '{curation_dir.as_posix()}'\n"
        f"protected = ['{Path(config.roots.protected[0]).as_posix()}']\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    with _open(config) as db:
        _run_pipeline(config, db)
    assert runner.invoke(app, ["courses", "--config", str(config_file)]).exit_code == 0

    output_path = tmp_path / "courses_coverage.json"
    completed = subprocess.run(
        [sys.executable, "tools/validate_courses.py", "--config", str(config_file), "--output", str(output_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["summary"]["every_folder_mapped_or_marked_unknown"] is True
    folders = {f["folder"]: f for f in report["folders"]}
    assert folders["Statik"]["mapped"] == 1
    assert folders["books"]["unknown"] == 1
