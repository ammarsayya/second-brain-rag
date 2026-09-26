"""T-P2-13 display-name mojibake repair."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.registry.classify import classify_pending
from sbr.registry.hash import hash_pending
from sbr.registry.names import repair_mojibake, repair_names, repair_relpath_display
from sbr.registry.scan import scan_root


def _open(config: SbrConfig) -> RegistryDB:
    db = RegistryDB.open(config)
    db.migrate()
    return db


def _run_pipeline(config: SbrConfig, db: RegistryDB) -> None:
    scan_root(config, db, "fx")
    hash_pending(config, db)
    classify_pending(config, db)


def test_repairs_the_documented_example() -> None:
    """docs/08 §7's own example, and docs/03's corpus census signal."""
    assert repair_mojibake("Fl├ñche") == "Fläche"


def test_repairs_a_real_corpus_example_found_during_genre_precision_review() -> None:
    """T-P2-10's known limitation: 'L├Âsung Klausur WS 15-16-1.pdf' - the mojibake-corrupted form of
    'Lösung Klausur WS 15-16-1.pdf' - prevented the solution keyword from matching and was misclassified
    'exam' instead of 'solution'. This is what unblocks fixing that once display names are repaired."""
    assert repair_mojibake("L├Âsung Klausur WS 15-16-1.pdf") == "Lösung Klausur WS 15-16-1.pdf"


def test_correct_unicode_names_are_never_touched() -> None:
    """The core safety property: repair must never fire without telltale evidence, since a blind round trip
    destroys already-correct names into different, still-printable-but-wrong characters."""
    for name in ("Übung/Aufgabenblätter/ÜBUNG3.TXT", "plain_ascii_name.txt", "Klausur_SS2019.pdf"):
        assert repair_mojibake(name) == name


def test_relpath_display_repairs_a_corrupted_ancestor_folder_not_just_the_leaf() -> None:
    """Real-corpus finding: checking this task's own acceptance criterion against the production registry
    found that every one of the corpus's 306 known mojibake cases (docs/03, docs/37) has the corruption in an
    ANCESTOR FOLDER name, not the file's own leaf name - e.g. an entire folder literally named
    'Fehlersuche mittels Fl├ñche RL 9.11.06' containing otherwise correctly-named files. display_name
    (docs/31) stays scoped to the leaf per its documented meaning; this general-purpose full-path repair is
    what actually resolves the other 306 cases when a consumer needs a readable path."""
    corrupted = (
        r"Mechanical\messundsteuerungstechnik\Mes\Messtechnik\Projektunterlagen\Projekt Bildverarbeitung"
        r"\Aufgabe 2\Bilder\Fehlersuche mittels Fl├ñche RL 9.11.06\C RL2350045.bmp"
    )
    repaired = (
        r"Mechanical\messundsteuerungstechnik\Mes\Messtechnik\Projektunterlagen\Projekt Bildverarbeitung"
        r"\Aufgabe 2\Bilder\Fehlersuche mittels Fläche RL 9.11.06\C RL2350045.bmp"
    )
    assert repair_relpath_display(corrupted) == repaired


def test_relpath_display_leaves_a_correct_path_untouched() -> None:
    assert repair_relpath_display(r"Mechanical\Statik\Klausur_SS2019.pdf") == r"Mechanical\Statik\Klausur_SS2019.pdf"


def test_stage_repairs_display_name_but_never_touches_relpath(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Fl├ñche.pdf").write_bytes(b"%PDF-1.7\nmojibake name")

    with _open(config) as db:
        _run_pipeline(config, db)
        [before] = db.repo(reg.PATH_OBSERVATION).find()
        assert before.display_name == "Fl├ñche.pdf"

        result = repair_names(config, db)
        assert result.considered == 1
        assert result.repaired == 1

        [after] = db.repo(reg.PATH_OBSERVATION).find()
        assert after.display_name == "Fläche.pdf"
        assert after.relpath == before.relpath  # the observed path itself is never rewritten (HC-01)
        assert after.relpath_raw == before.relpath_raw
        assert after.obs_id == before.obs_id  # same observation, patched in place - not a new row


def test_stage_leaves_correct_names_alone(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Klausur_SS2019.pdf").write_bytes(b"%PDF-1.7\nnot mojibake")

    with _open(config) as db:
        _run_pipeline(config, db)
        result = repair_names(config, db)
        assert result.considered == 1
        assert result.repaired == 0


def test_re_run_is_idempotent(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Fl├ñche.pdf").write_bytes(b"%PDF-1.7\nmojibake name")

    with _open(config) as db:
        _run_pipeline(config, db)
        first = repair_names(config, db)
        second = repair_names(config, db)

        assert first.repaired == 1
        assert second.repaired == 0  # already-repaired name has no telltale left, nothing to redo
        assert db.repo(reg.PATH_OBSERVATION).count() == 1


def test_cli_prints_json(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from sbr.cli.app import app

    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Fl├ñche.pdf").write_bytes(b"%PDF-1.7\nmojibake name")
    config_file = tmp_path / "names.toml"
    config_file.write_text(
        "[roots]\n"
        f"sources = [{{ id = 'fx', path = '{root.as_posix()}' }}]\n"
        f"var = '{Path(config.roots.var).as_posix()}'\n"
        f"curation = '{Path(config.roots.curation).as_posix()}'\n"
        f"protected = ['{Path(config.roots.protected[0]).as_posix()}']\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    with _open(config) as db:
        _run_pipeline(config, db)

    result = runner.invoke(app, ["names", "--config", str(config_file)])
    assert result.exit_code == 0, result.output
    assert '"repaired": 1' in result.output
