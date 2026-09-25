"""T-P2-10 genre classification and exam/exercise-solution pairing."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.ids import new_id
from sbr.registry.classify import classify_pending
from sbr.registry.genre import classify_genre, extract_isbn, extract_semester, find_solution_pairs
from sbr.registry.hash import hash_pending
from sbr.registry.scan import scan_root
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


def test_every_named_genre_keyword_is_recognized() -> None:
    expected = {
        r"BachelorArbeit\Bachelorarbeit.pdf": "thesis",
        r"BachelorArbeit\Masterarbeit_Entwurf.pdf": "thesis",
        r"Reg1\Loesungen\Musterloesung_Klausur.pdf": "solution",
        r"Reg1\Loesungen\Kurzloesung.pdf": "solution",
        r"Reg1\Loesungen\TutLos_Blatt1.pdf": "solution",  # keyword must be in the filename itself, not just the folder
        r"Mechanical\Bericht_Labor1.pdf": "report",
        r"Mechanical\Labor\Versuch_1.pdf": "lab",
        r"Reg1\Klausuren\Klausur_SS2019.pdf": "exam",
        r"Reg1\Uebung\Aufgabenblatt_1.pdf": "exercise",
        r"Reg1\Aufgabenblaetter\Aufgabenblatt_2.pdf": "exercise",
        r"Reg1\Skripte\Skript_Kap1.pdf": "script",
    }
    for relpath, genre in expected.items():
        decision = classify_genre(relpath)
        assert decision.genre == genre, f"{relpath!r}: expected {genre!r}, got {decision.genre!r}"
        assert decision.confidence is not None and decision.confidence >= 0.6


def test_underscore_joined_filenames_still_match_at_filename_confidence() -> None:
    """Regression: '\\b' alone does not create a boundary against '_' (a regex word character), so
    'Klausur_SS2019.pdf' originally fell through to a weaker folder-only match instead of matching the
    filename itself. Fixed via delimiter normalization before matching."""
    decision = classify_genre(r"Reg1\Klausuren\Klausur_SS2019.pdf")
    assert decision.genre == "exam"
    assert decision.confidence == 0.9  # filename-level match, not the weaker 0.6 folder-only fallback
    assert decision.semester == "ss2019"


def test_unrelated_filenames_get_no_genre() -> None:
    for relpath in (r"Mechanical\werkstoffkunde\WK\1.PNG", r"Information\Elektrotechnik.pdf"):
        decision = classify_genre(relpath)
        assert decision.genre is None
        assert decision.confidence is None


def test_files_inside_a_named_project_folder_get_no_genre_from_the_folder_alone() -> None:
    """Regression: found on the real corpus's 150-file precision sample - roughly 20% of the sample was
    genre="thesis"/"lab"/"script" purely because the file lived somewhere under a "BachelorArbeit\\"/"Labor\\"/
    "Skript\\" folder tree, even for JPEGs, .mat data files, .m scripts, and a screenshot. A folder name is not
    evidence of what an individual file inside it actually is; only the file's own name counts now."""
    for relpath in (
        r"BachelorArbeit\MatlabBachelorArbeit\App_Innere\Bilder_3D\LastKoll1_parametrization_594.jpg",
        r"BachelorArbeit\Matlab\Bachelorarbeit\Test_Bachelor\Opt\tester.m",
        r"Mechanical\Kolbenmaschinen\Labor\Labor1\MS\Codes\2\Screenshot (84).png",
        r"Mechanical\messundsteuerungstechnik\Mathe\Math2\skript\Vorlesung_7.mp4",
    ):
        decision = classify_genre(relpath)
        assert decision.genre is None, f"{relpath!r}: expected no genre, got {decision.genre!r}"


def test_lsg_abbreviation_is_recognized_as_solution() -> None:
    """Regression: 'Lsg' (a common German abbreviation for Loesung) was not in the solution keyword list, so
    '08_Uebung_Lsg (1).pdf' - clearly an exercise SOLUTION - classified as the weaker 'exercise' genre instead
    (matching only 'Uebung')."""
    assert classify_genre(r"Course\08_Uebung_Lsg (1).pdf").genre == "solution"


def test_isbn_extraction_normalizes_hyphenated_and_underscored_forms() -> None:
    assert extract_isbn(r"books\Numerik_ISBN_978-3-540-72233-9.pdf") == "9783540722339"
    assert extract_isbn(r"books\Klausur.pdf") is None


def test_bare_isbn13_filename_is_recognized_without_an_isbn_label() -> None:
    """Regression: a textbook saved as e.g. '978-3-8348-9049-8.pdf' with no literal 'ISBN' text anywhere in
    the path was not detected at all - found on the real corpus's precision sample."""
    assert extract_isbn(r"books\matlab\978-3-8348-9049-8.pdf") == "9783834890498"
    # A bare 10-digit stem is deliberately NOT treated as an ISBN without an explicit label (too easily
    # something else - an ID, a phone number, a date-like string).
    assert extract_isbn(r"books\1234567890.pdf") is None


def test_semester_extraction() -> None:
    assert extract_semester(r"Reg1\Klausur_SS2019.pdf") == "ss2019"
    assert extract_semester(r"Reg1\Klausur_WS1819.pdf") == "ws1819"
    assert extract_semester(r"Reg1\Klausur.pdf") is None


def test_solution_pairs_with_sibling_folder_and_matching_semester() -> None:
    """Regression: exam and solution files routinely live in SIBLING folders that mirror each other by name
    (e.g. 'Klausuren/' next to 'Loesungen/'), not nested parent/child - the first version of the folder-
    proximity rule (copied from T-P2-09's twin detection, where PDF/office pairs share a folder) missed this
    entirely and found zero pairs for the most common real layout."""
    exam = _obs(r"Reg1\Klausuren\Klausur_SS2019.pdf", _blob("1"))
    solution = _obs(r"Reg1\Loesungen\Musterloesung_Klausur_SS2019.pdf", _blob("2"))
    wrong_semester_exam = _obs(r"Reg1\Klausuren\Klausur_WS1819.pdf", _blob("3"))

    pairs = find_solution_pairs(
        [(solution, "ss2019")],
        [(exam, "ss2019"), (wrong_semester_exam, "ws1819")],
    )

    assert len(pairs) == 1
    assert pairs[0].solution_blob == _blob("2")
    assert pairs[0].target_blob == _blob("1")


def test_stage_persists_genre_and_solution_pairs(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    from sbr.registry.genre import classify_genres

    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Klausuren").mkdir()
    (root / "Loesungen").mkdir()
    (root / "Klausuren" / "Klausur_SS2019.pdf").write_bytes(b"%PDF-1.7\nexam")
    (root / "Loesungen" / "Musterloesung_Klausur_SS2019.pdf").write_bytes(b"%PDF-1.7\nsolution")

    with _open(config) as db:
        _run_pipeline(config, db)
        result = classify_genres(config, db)
        classifications = {c.blob_id: c for c in db.repo(reg.BLOB_CLASSIFICATION).find()}
        relations = [r for r in db.repo(reg.BLOB_RELATION).find() if r.type is RelationType.SOLUTION_OF]

        assert result.classified == 2
        assert result.solution_pairs_proposed == 1
        genres = {c.genre for c in classifications.values()}
        assert genres == {"exam", "solution"}
        [relation] = relations
        assert relation.status is RelationStatus.CANDIDATE
        assert relation.confidence > 0


def test_tool_artifact_and_code_files_are_never_assigned_a_genre(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    """Regression: found on the real corpus's 150-file precision sample - a compiled Java class file
    'Klausur.class', a source file 'Klausur.java', and a BlueJ tool artifact 'Klausur.ctxt' all matched the
    'exam' keyword by filename alone despite not being exam documents in any meaningful sense. Genre now only
    applies to knowledge-bearing knowledge classes, matching this task's own stated rationale."""
    from sbr.registry.genre import classify_genres

    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Klausur.class").write_bytes(b"\xca\xfe\xba\xbe" + b"\x00" * 20)  # real Java class-file magic bytes
    (root / "Klausur.java").write_bytes(b"class Klausur {}")
    (root / "Klausur.pdf").write_bytes(b"%PDF-1.7\nreal exam document")

    with _open(config) as db:
        _run_pipeline(config, db)
        result = classify_genres(config, db)
        classifications = {c.blob_id: c for c in db.repo(reg.BLOB_CLASSIFICATION).find()}
        by_path = {obs.relpath: classifications.get(obs.blob_id) for obs in db.repo(reg.PATH_OBSERVATION).find()}

        assert result.classified == 1
        assert by_path["Klausur.pdf"] is not None and by_path["Klausur.pdf"].genre == "exam"
        assert by_path.get("Klausur.class") is None
        assert by_path.get("Klausur.java") is None


def test_re_run_is_idempotent(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    from sbr.registry.genre import classify_genres

    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Klausur_SS2019.pdf").write_bytes(b"%PDF-1.7\nexam")

    with _open(config) as db:
        _run_pipeline(config, db)
        classify_genres(config, db)
        classify_genres(config, db)

        assert db.repo(reg.BLOB_CLASSIFICATION).count() == 1


def test_cli_prints_json(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from sbr.cli.app import app

    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Klausur_SS2019.pdf").write_bytes(b"%PDF-1.7\nexam")
    config_file = tmp_path / "genre.toml"
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

    result = runner.invoke(app, ["genre", "--config", str(config_file)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["classified"] == 1
