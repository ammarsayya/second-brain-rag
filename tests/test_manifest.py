"""T-P2-14 corpus manifest report: snapshot test on a small controlled fixture tree."""

from __future__ import annotations

import csv
import io
from collections.abc import Callable
from pathlib import Path

from sbr.config import SbrConfig
from sbr.db.registry import RegistryDB
from sbr.registry.classify import classify_pending
from sbr.registry.dedup import select_canonical_paths
from sbr.registry.genre import classify_genres
from sbr.registry.hash import hash_pending
from sbr.registry.scan import scan_root
from sbr.registry.sensitivity import classify_sensitivity
from sbr.reports.manifest import build_manifest, render_csv_rows, render_markdown


def _open(config: SbrConfig) -> RegistryDB:
    db = RegistryDB.open(config)
    db.migrate()
    return db


def _empty_curation_files(config: SbrConfig) -> None:
    curation_dir = Path(config.roots.curation)
    curation_dir.mkdir(parents=True, exist_ok=True)
    (curation_dir / "exclusions.yaml").write_text("exclusions: []\n", encoding="utf-8")
    (curation_dir / "sensitivity_overrides.yaml").write_text("overrides: []\n", encoding="utf-8")
    (curation_dir / "canonical_path_overrides.yaml").write_text("overrides: []\n", encoding="utf-8")


def test_manifest_totals_and_breakdowns_match_a_hand_counted_fixture_tree(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Statik").mkdir()
    (root / "Statik" / "Klausur_SS2019.pdf").write_bytes(b"%PDF-1.7\nexam one")
    (root / "Statik" / "Klausur_SS2019_Kopie.pdf").write_bytes(b"%PDF-1.7\nexam one")  # exact duplicate, same blob
    (root / "Reg1").mkdir()
    (root / "Reg1" / "Skript.pdf").write_bytes(b"%PDF-1.7\nscript one")
    (root / "notes.txt").write_text("plain text, no genre keyword", encoding="utf-8")
    _empty_curation_files(config)

    with _open(config) as db:
        scan_root(config, db, "fx")
        hash_pending(config, db)
        classify_pending(config, db)
        classify_sensitivity(config, db)
        select_canonical_paths(config, db)
        classify_genres(config, db)

        report = build_manifest(config, db)

    assert report.total_files == 4
    assert report.total_blobs == 3  # two Klausur files share one blob
    assert report.total_bytes == sum(
        len(b) for b in (b"%PDF-1.7\nexam one", b"%PDF-1.7\nexam one", b"%PDF-1.7\nscript one", b"")
    ) + len("plain text, no genre keyword")
    assert report.total_unique_bytes == len(b"%PDF-1.7\nexam one") + len(b"%PDF-1.7\nscript one") + len(
        "plain text, no genre keyword"
    )

    top_level = {f.folder: f.files for f in report.by_top_level_folder}
    assert top_level == {"Statik": 2, "Reg1": 1, "(root)": 1}  # notes.txt has no folder at all

    # Regression: an earlier version took the first two segments of the WHOLE path (filename included), so a
    # file directly inside a single-depth folder (no subfolder, exactly this fixture's shape) was wrongly
    # bucketed per-file instead of under its one real folder.
    level2 = {f.folder: f.files for f in report.by_level2_folder}
    assert level2 == {"Statik": 2, "Reg1": 1, "(root)": 1}

    assert report.duplicates.duplicate_groups == 1
    assert report.duplicates.redundant_bytes == len(b"%PDF-1.7\nexam one")

    genre_counts = {g.key: g.files for g in report.genre}
    assert genre_counts.get("exam") == 1  # only one blob for the duplicate pair
    assert genre_counts.get("script") == 1

    sensitivity_counts = {s.key: s.files for s in report.sensitivity}
    assert sum(sensitivity_counts.values()) == report.total_blobs

    assert report.archives.members_total == 0
    assert report.pdf_page_census["available"] is False


def test_render_markdown_and_csv_cover_every_section(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Klausur_SS2019.pdf").write_bytes(b"%PDF-1.7\nexam")
    _empty_curation_files(config)

    with _open(config) as db:
        scan_root(config, db, "fx")
        hash_pending(config, db)
        classify_pending(config, db)
        classify_sensitivity(config, db)
        select_canonical_paths(config, db)
        classify_genres(config, db)
        report = build_manifest(config, db)

    markdown = render_markdown(report)
    for heading in ("# Corpus Manifest", "## Totals", "## Duplicates", "## Archives", "## Genre", "## Course"):
        assert heading in markdown

    rows = render_csv_rows(report)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["section", "key", "files", "bytes"])
    writer.writerows(rows)
    parsed = list(csv.reader(io.StringIO(buffer.getvalue())))
    assert parsed[0] == ["section", "key", "files", "bytes"]
    assert any(row[0] == "totals" and row[1] == "files" for row in parsed[1:])


def test_cli_writes_markdown_and_csv_and_prints_json(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from sbr.cli.app import app

    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "Klausur_SS2019.pdf").write_bytes(b"%PDF-1.7\nexam")
    _empty_curation_files(config)

    config_file = tmp_path / "manifest.toml"
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
        scan_root(config, db, "fx")
        hash_pending(config, db)
        classify_pending(config, db)

    markdown_output = tmp_path / "out" / "manifest.md"
    csv_output = tmp_path / "out" / "manifest.csv"
    result = runner.invoke(
        app,
        [
            "report",
            "manifest",
            "--config",
            str(config_file),
            "--markdown-output",
            str(markdown_output),
            "--csv-output",
            str(csv_output),
        ],
    )
    assert result.exit_code == 0, result.output
    assert '"total_files": 1' in result.output
    assert markdown_output.exists()
    assert csv_output.exists()
    assert "# Corpus Manifest" in markdown_output.read_text(encoding="utf-8")
