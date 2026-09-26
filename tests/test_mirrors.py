"""T-P2-07 mirror-directory and cleanup-suggestion report - report only, no action taken."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from sbr.config import SbrConfig
from sbr.db.registry import RegistryDB
from sbr.registry.hash import hash_pending
from sbr.registry.scan import scan_root
from sbr.reports.mirrors import MirrorPair, build_mirrors_report, find_mirror_pairs, render_markdown


def _open(config: SbrConfig) -> RegistryDB:
    db = RegistryDB.open(config)
    db.migrate()
    return db


def test_find_mirror_pairs_qualifies_a_high_overlap_pair() -> None:
    folder_blobs = {
        "A\\one": frozenset({"b1", "b2", "b3", "b4", "b5"}),
        "B\\two": frozenset({"b1", "b2", "b3", "b4", "b5", "b6"}),  # shares all 5 of A's blobs
    }
    blob_sizes = {f"b{i}": 100 for i in range(1, 7)}
    pairs = find_mirror_pairs(folder_blobs, blob_sizes, min_overlap=0.5, min_shared_blobs=5)
    assert len(pairs) == 1
    pair = pairs[0]
    assert {pair.folder_a, pair.folder_b} == {"A\\one", "B\\two"}
    assert pair.shared_blobs == 5
    assert pair.overlap_pct == 1.0  # 5/min(5,6)
    assert pair.bytes_reclaimable == 500


def test_find_mirror_pairs_rejects_low_overlap() -> None:
    """Both sides have 20 blobs each, but only 5 are shared - 5/20 = 25% overlap even on the smaller side."""
    folder_blobs = {
        "A": frozenset({f"a{i}" for i in range(15)}) | frozenset({f"shared{i}" for i in range(5)}),
        "B": frozenset({f"b{i}" for i in range(15)}) | frozenset({f"shared{i}" for i in range(5)}),
    }
    pairs = find_mirror_pairs(folder_blobs, {}, min_overlap=0.5, min_shared_blobs=1)
    assert pairs == []


def test_find_mirror_pairs_rejects_too_few_shared_blobs_even_at_high_overlap() -> None:
    """A tiny folder that happens to share 2 files with a huge one is not 'mirrored' in any useful sense,
    however high its overlap fraction (2/2 = 100%) reads."""
    folder_blobs = {
        "tiny": frozenset({"b1", "b2"}),
        "huge": frozenset({"b1", "b2"} | {f"other{i}" for i in range(500)}),
    }
    pairs = find_mirror_pairs(folder_blobs, {}, min_overlap=0.5, min_shared_blobs=5)
    assert pairs == []


def test_pairs_are_sorted_by_reclaimable_bytes_descending() -> None:
    folder_blobs = {
        "A": frozenset({f"a{i}" for i in range(10)}),
        "B": frozenset({f"a{i}" for i in range(10)}),  # shares all of A, small blobs
        "C": frozenset({f"c{i}" for i in range(10)}),
        "D": frozenset({f"c{i}" for i in range(10)}),  # shares all of C, large blobs
    }
    blob_sizes = {**{f"a{i}": 10 for i in range(10)}, **{f"c{i}": 1000 for i in range(10)}}
    pairs = find_mirror_pairs(folder_blobs, blob_sizes, min_overlap=0.5, min_shared_blobs=5)
    assert [{p.folder_a, p.folder_b} for p in pairs] == [{"C", "D"}, {"A", "B"}]


def test_build_mirrors_report_against_a_real_registry(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    config = make_config()
    root = Path(config.roots.sources[0].path)
    # Two folders, each with 5 files, all pairwise-identical content -> a qualifying mirror pair.
    for folder in ("TreeA", "TreeB"):
        (root / folder).mkdir()
        for i in range(5):
            (root / folder / f"file{i}.txt").write_bytes(f"identical content {i}".encode())
    # An unrelated folder with its own unique content - must never appear in the report.
    (root / "Unrelated").mkdir()
    (root / "Unrelated" / "own.txt").write_bytes(b"nothing shared with anything else")

    with _open(config) as db:
        scan_root(config, db, "fx")
        hash_pending(config, db)
        pairs = build_mirrors_report(config, db, min_overlap=0.5, min_shared_blobs=5)

    assert len(pairs) == 1
    [pair] = pairs
    assert {pair.folder_a, pair.folder_b} == {"TreeA", "TreeB"}
    assert pair.shared_blobs == 5
    assert pair.overlap_pct == 1.0
    assert not any("Unrelated" in {p.folder_a, p.folder_b} for p in pairs)


def test_render_markdown_lists_every_pair_and_totals() -> None:
    pairs = [
        MirrorPair(
            folder_a="A", folder_b="B", blobs_a=5, blobs_b=5, shared_blobs=5, overlap_pct=1.0, bytes_reclaimable=500
        )
    ]
    markdown = render_markdown(pairs)
    assert "# Mirror-Directory Report" in markdown
    assert "no action taken" in markdown
    assert "| A | B | 5 | 5 | 5 | 100.00% | 500 |" in markdown
    assert "pairs found: 1" in markdown


def test_render_markdown_with_no_pairs_is_still_well_formed() -> None:
    markdown = render_markdown([])
    assert "pairs found: 0" in markdown


def test_cli_writes_markdown_and_prints_json(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from sbr.cli.app import app

    config = make_config()
    root = Path(config.roots.sources[0].path)
    for folder in ("TreeA", "TreeB"):
        (root / folder).mkdir()
        for i in range(5):
            (root / folder / f"file{i}.txt").write_bytes(f"identical content {i}".encode())

    config_file = tmp_path / "mirrors.toml"
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

    markdown_output = tmp_path / "out" / "mirrors.md"
    result = runner.invoke(
        app,
        ["report", "mirrors", "--config", str(config_file), "--markdown-output", str(markdown_output)],
    )
    assert result.exit_code == 0, result.output
    assert '"pairs_found": 1' in result.output
    assert markdown_output.exists()
    assert "# Mirror-Directory Report" in markdown_output.read_text(encoding="utf-8")
