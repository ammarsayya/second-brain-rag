"""T-P2-06 exact-duplicate canonical selection; aliases are never removed."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path, PureWindowsPath

from tools.validate_dedup import compare_groups
from typer.testing import CliRunner

from sbr.cli.app import app
from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.provenance import ProvenanceStore
from sbr.registry.dedup import select_canonical_paths
from sbr.registry.hash import hash_pending
from sbr.registry.scan import scan_root
from sbr.schemas import PathObservation


def _open(config: SbrConfig) -> RegistryDB:
    db = RegistryDB.open(config)
    db.migrate()
    return db


def _write_files(root: Path, relpaths: list[str], content: bytes = b"identical") -> None:
    for relpath in relpaths:
        target = root.joinpath(*PureWindowsPath(relpath).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


def _empty_overrides(config: SbrConfig) -> Path:
    path = Path(config.roots.curation) / "canonical_path_overrides.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("overrides: []\n", encoding="utf-8")
    return path


def _seed(config: SbrConfig, db: RegistryDB, relpaths: list[str]) -> list[PathObservation]:
    _write_files(Path(config.roots.sources[0].path), relpaths)
    scan_root(config, db, "fx")
    result = hash_pending(config, db)
    assert result.failed == 0
    rows = db.repo(reg.PATH_OBSERVATION).find()
    assert len(rows) == len(relpaths)
    assert len({row.blob_id for row in rows}) == 1
    return rows


def _canonical(db: RegistryDB) -> PathObservation:
    [blob] = db.repo(reg.BLOB).find()
    assert blob.canonical_obs_id is not None
    observation = db.repo(reg.PATH_OBSERVATION).get(blob.canonical_obs_id)
    assert observation is not None
    return observation


def _mark_mirror(db: RegistryDB, relpath: str) -> None:
    [observation] = db.repo(reg.PATH_OBSERVATION).find({"relpath": relpath})
    provenance = ProvenanceStore(db.conn)
    with provenance.activity(
        kind="test_setup",
        producer="tests.test_dedup",
        producer_version="1",
        agent="system:test",
    ) as activity:
        db.repo(reg.PATH_OBSERVATION).upsert(
            observation.model_copy(update={"is_mirror_candidate": True, "activity_id": activity.activity_id})
        )


def _table_counts(db: RegistryDB) -> dict[str, int]:
    tables = [
        str(row[0])
        for row in db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    return {
        table: int(db.conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])  # noqa: S608
        for table in tables
    }


def _assert_never_shrank(before: dict[str, int], after: dict[str, int]) -> None:
    assert before.keys() == after.keys()
    assert all(after[table] >= count for table, count in before.items())


def test_non_mirror_wins_before_shorter_path(make_config: Callable[..., SbrConfig]) -> None:
    config = make_config()
    overrides = _empty_overrides(config)
    with _open(config) as db:
        _seed(config, db, ["a.txt", "much-longer-name.txt"])
        _mark_mirror(db, "a.txt")

        select_canonical_paths(config, db, overrides_path=overrides)

        assert _canonical(db).relpath == "much-longer-name.txt"


def test_shortest_path_wins_when_mirror_status_matches(make_config: Callable[..., SbrConfig]) -> None:
    config = make_config()
    overrides = _empty_overrides(config)
    with _open(config) as db:
        _seed(config, db, ["short.txt", "much-longer-name.txt"])

        select_canonical_paths(config, db, overrides_path=overrides)

        assert _canonical(db).relpath == "short.txt"


def test_shallower_path_wins_before_character_length(make_config: Callable[..., SbrConfig]) -> None:
    config = make_config()
    overrides = _empty_overrides(config)
    with _open(config) as db:
        _seed(config, db, ["a\\b.txt", "long.txt"])

        select_canonical_paths(config, db, overrides_path=overrides)

        assert _canonical(db).relpath == "long.txt"


def test_duplicate_download_marker_loses_when_prior_ranks_tie(
    make_config: Callable[..., SbrConfig],
) -> None:
    config = make_config()
    overrides = _empty_overrides(config)
    with _open(config) as db:
        _seed(config, db, ["x (1).txt", "clean.txt"])

        select_canonical_paths(config, db, overrides_path=overrides)

        assert _canonical(db).relpath == "clean.txt"


def test_kopie_marker_loses_when_prior_ranks_tie(make_config: Callable[..., SbrConfig]) -> None:
    config = make_config()
    overrides = _empty_overrides(config)
    with _open(config) as db:
        _seed(config, db, ["Kopie.txt", "clean.txt"])

        select_canonical_paths(config, db, overrides_path=overrides)

        assert _canonical(db).relpath == "clean.txt"


def test_lexicographic_final_tie_break_is_deterministic(make_config: Callable[..., SbrConfig]) -> None:
    config = make_config()
    overrides = _empty_overrides(config)
    with _open(config) as db:
        _seed(config, db, ["b.txt", "a.txt"])

        first = select_canonical_paths(config, db, overrides_path=overrides)
        second = select_canonical_paths(config, db, overrides_path=overrides)

        assert _canonical(db).relpath == "a.txt"
        assert first.updated == 1
        assert second.updated == 0


def test_owner_override_precedes_automatic_heuristic(make_config: Callable[..., SbrConfig]) -> None:
    config = make_config()
    override_file = _empty_overrides(config)
    with _open(config) as db:
        rows = _seed(config, db, ["clean.txt", "x (1).txt"])
        blob_id = rows[0].blob_id
        assert blob_id is not None
        override_file.write_text(
            "overrides:\n"
            f"  - blob_id: '{blob_id}'\n"
            "    root_id: fx\n"
            "    relpath: 'x (1).txt'\n"
            "    reason: Owner-preferred location\n",
            encoding="utf-8",
        )

        result = select_canonical_paths(config, db, overrides_path=override_file)

        assert _canonical(db).relpath == "x (1).txt"
        assert result.overrides_applied == 1


def test_dedup_never_deletes_any_row_and_retains_full_aliases(make_config: Callable[..., SbrConfig]) -> None:
    config = make_config()
    overrides = _empty_overrides(config)
    with _open(config) as db:
        original = _seed(config, db, ["original.txt", "alias.txt"])
        before = _table_counts(db)

        select_canonical_paths(config, db, overrides_path=overrides)

        after = _table_counts(db)
        stored = db.repo(reg.PATH_OBSERVATION).find()
        _assert_never_shrank(before, after)
        assert stored == original
        assert len(stored) == 2


def test_single_observation_is_its_own_canonical(make_config: Callable[..., SbrConfig]) -> None:
    config = make_config()
    overrides = _empty_overrides(config)
    with _open(config) as db:
        [only] = _seed(config, db, ["only.txt"])

        result = select_canonical_paths(config, db, overrides_path=overrides)

        assert _canonical(db).obs_id == only.obs_id
        assert result.singletons == 1
        assert result.duplicate_groups == 0


def test_dedup_cli_prints_json(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    config = make_config()
    _write_files(Path(config.roots.sources[0].path), ["original.txt", "alias.txt"])
    _empty_overrides(config)
    config_file = tmp_path / "dedup.toml"
    config_file.write_text(
        "[roots]\n"
        f"sources = [{{ id = 'fx', path = '{Path(config.roots.sources[0].path).as_posix()}' }}]\n"
        f"var = '{Path(config.roots.var).as_posix()}'\n"
        f"curation = '{Path(config.roots.curation).as_posix()}'\n"
        f"protected = ['{Path(config.roots.protected[0]).as_posix()}']\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    assert runner.invoke(app, ["scan", "--root", "fx", "--config", str(config_file)]).exit_code == 0
    assert runner.invoke(app, ["hash", "--config", str(config_file)]).exit_code == 0

    result = runner.invoke(app, ["dedup", "--config", str(config_file)])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["duplicate_groups"] == 1
    assert payload["updated"] == 1


def test_phase0_comparison_ignores_quarantined_missing_group_members() -> None:
    report = compare_groups(
        [["kept-a.txt", "kept-b.txt", "quarantined.txt"]],
        [("kept-a.txt", "b3:" + "a" * 64), ("kept-b.txt", "b3:" + "a" * 64)],
        max_discrepancies=10,
    )

    assert report["ok"] is True
    assert report["comparable_phase0_groups"] == 1
    assert report["missing_phase0_paths"] == 1


def test_phase0_comparison_reports_splits_and_merges_without_blind_failure() -> None:
    report = compare_groups(
        [["a.txt", "b.txt"], ["c.txt", "d.txt"]],
        [
            ("a.txt", "blob-1"),
            ("b.txt", "blob-2"),
            ("c.txt", "blob-1"),
            ("d.txt", "blob-3"),
        ],
        max_discrepancies=10,
    )

    assert report["ok"] is False
    assert report["split_discrepancies"] == 2
    assert report["merge_discrepancies"] == 1
    assert len(report["split_details"]) == 2  # type: ignore[arg-type]
