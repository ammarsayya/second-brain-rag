"""TS-CHANGE: append-only new/alias/modified/moved/deleted/re-added semantics."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from typer.testing import CliRunner

from sbr.cli.app import app
from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.ids import hash_bytes
from sbr.registry.changes import detect_changes
from sbr.registry.hash import hash_pending
from sbr.registry.scan import scan_root
from sbr.schemas.registry import BlobStatus, ChangeType, ObservationState, RelationStatus, RelationType

TRACKED_TABLES = (reg.PATH_OBSERVATION, reg.BLOB, reg.CHANGE_EVENT, reg.BLOB_RELATION)


def _open(config: SbrConfig) -> RegistryDB:
    db = RegistryDB.open(config)
    db.migrate()
    return db


def _scan_hash_changes(config: SbrConfig, db: RegistryDB):
    scan = scan_root(config, db, "fx")
    hashed = hash_pending(config, db)
    assert hashed.failed == 0
    return scan, detect_changes(config, db, "fx", scan.scan_id)


def _counts(db: RegistryDB) -> tuple[int, ...]:
    return tuple(db.repo(table).count() for table in TRACKED_TABLES)


def _assert_never_shrank(before: tuple[int, ...], after: tuple[int, ...]) -> None:
    assert all(later >= earlier for earlier, later in zip(before, after, strict=True))


def test_new_file_emits_new_and_registers_blob(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    config = make_config()
    source = tmp_path / "src_root" / "new.txt"
    source.write_bytes(b"new content")
    with _open(config) as db:
        before = _counts(db)
        scan, result = _scan_hash_changes(config, db)

        assert result.counts[ChangeType.NEW.value] == 1
        [event] = result.events
        assert event.type is ChangeType.NEW and event.scan_id == scan.scan_id
        assert event.blob_id == hash_bytes(b"new content")
        assert db.repo(reg.BLOB).get(event.blob_id) is not None
        _assert_never_shrank(before, _counts(db))


def test_duplicate_content_at_new_path_emits_alias(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    config = make_config()
    root = tmp_path / "src_root"
    (root / "original.txt").write_bytes(b"same bytes")
    with _open(config) as db:
        _scan_hash_changes(config, db)
        before = _counts(db)
        (root / "alias.txt").write_bytes(b"same bytes")
        _, result = _scan_hash_changes(config, db)

        assert [event.type for event in result.events] == [ChangeType.ALIAS]
        assert db.repo(reg.BLOB).count() == 1
        assert db.repo(reg.PATH_OBSERVATION).count() == 2
        _assert_never_shrank(before, _counts(db))


def test_modified_file_emits_version_relation_and_preserves_old_blob(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    config = make_config()
    source = tmp_path / "src_root" / "document.txt"
    source.write_bytes(b"version one")
    with _open(config) as db:
        _, first = _scan_hash_changes(config, db)
        old_blob_id = first.events[0].blob_id
        assert old_blob_id is not None
        old_blob = db.repo(reg.BLOB).get(old_blob_id)
        before = _counts(db)

        source.write_bytes(b"version two, changed")
        scan = scan_root(config, db, "fx")
        pre_hash = db.repo(reg.PATH_OBSERVATION).find({"relpath": "document.txt"})[0]
        assert pre_hash.blob_id == old_blob_id
        hash_pending(config, db)
        result = detect_changes(config, db, "fx", scan.scan_id)

        [event] = result.events
        assert event.type is ChangeType.MODIFIED
        assert event.details == {"previous_blob_id": old_blob_id}
        new_blob_id = hash_bytes(b"version two, changed")
        assert event.blob_id == new_blob_id
        new_blob = db.repo(reg.BLOB).get(new_blob_id)
        assert new_blob is not None and new_blob.first_seen_scan == scan.scan_id
        relation = db.repo(reg.BLOB_RELATION).get(new_blob_id, old_blob_id, RelationType.VERSION_OF)
        assert relation is not None
        assert relation.status is RelationStatus.CONFIRMED and relation.confidence == 1.0
        assert db.repo(reg.BLOB).get(old_blob_id) == old_blob
        manifests = db.repo(reg.WORK_OUTPUT).find()
        assert any(output.artifacts.get("previous_blob_id") == old_blob_id for output in manifests)
        _assert_never_shrank(before, _counts(db))


def test_move_emits_only_moved_and_keeps_historical_observation(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    config = make_config()
    root = tmp_path / "src_root"
    old_path = root / "old.txt"
    old_path.write_bytes(b"move me")
    with _open(config) as db:
        _scan_hash_changes(config, db)
        old_observation = db.repo(reg.PATH_OBSERVATION).find({"relpath": "old.txt"})[0]
        before = _counts(db)

        old_path.rename(root / "renamed.txt")
        _, result = _scan_hash_changes(config, db)

        assert [event.type for event in result.events] == [ChangeType.MOVED]
        assert result.events[0].obs_id == old_observation.obs_id
        stored_old = db.repo(reg.PATH_OBSERVATION).get(old_observation.obs_id)
        assert stored_old is not None and stored_old.state is ObservationState.MOVED
        [live] = db.repo(reg.PATH_OBSERVATION).find({"relpath": "renamed.txt", "state": ObservationState.PRESENT})
        assert live.blob_id == old_observation.blob_id
        assert db.repo(reg.PATH_OBSERVATION).count() == 2
        _assert_never_shrank(before, _counts(db))


def test_delete_marks_observation_and_orphans_last_blob(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    config = make_config()
    source = tmp_path / "src_root" / "gone.txt"
    source.write_bytes(b"gone")
    with _open(config) as db:
        _scan_hash_changes(config, db)
        old = db.repo(reg.PATH_OBSERVATION).find({"relpath": "gone.txt"})[0]
        before = _counts(db)

        source.unlink()
        _, result = _scan_hash_changes(config, db)

        assert [event.type for event in result.events] == [ChangeType.DELETED]
        stored = db.repo(reg.PATH_OBSERVATION).get(old.obs_id)
        assert stored is not None and stored.state is ObservationState.DELETED
        blob = db.repo(reg.BLOB).get(old.blob_id)
        assert blob is not None and blob.status is BlobStatus.ORPHANED
        assert db.repo(reg.PATH_OBSERVATION).count() == 1
        _assert_never_shrank(before, _counts(db))


def test_readded_path_is_fresh_alias_and_reactivates_blob(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    config = make_config()
    source = tmp_path / "src_root" / "return.txt"
    source.write_bytes(b"returns")
    with _open(config) as db:
        _scan_hash_changes(config, db)
        original = db.repo(reg.PATH_OBSERVATION).find({"relpath": "return.txt"})[0]
        source.unlink()
        _scan_hash_changes(config, db)
        before = _counts(db)

        source.write_bytes(b"returns")
        _, result = _scan_hash_changes(config, db)

        assert [event.type for event in result.events] == [ChangeType.ALIAS]
        observations = db.repo(reg.PATH_OBSERVATION).find({"relpath": "return.txt"})
        assert len(observations) == 2
        live = next(obs for obs in observations if obs.state is ObservationState.PRESENT)
        assert live.obs_id != original.obs_id and live.first_seen_scan == result.events[0].scan_id
        blob = db.repo(reg.BLOB).get(live.blob_id)
        assert blob is not None and blob.status is BlobStatus.ACTIVE
        _assert_never_shrank(before, _counts(db))


def test_changes_cli_prints_json(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    config = make_config()
    source = tmp_path / "src_root" / "cli.txt"
    source.write_bytes(b"cli")
    config_file = tmp_path / "changes.toml"
    config_file.write_text(
        "[roots]\n"
        f"sources = [{{ id = 'fx', path = '{source.parent.as_posix()}' }}]\n"
        f"var = '{Path(config.roots.var).as_posix()}'\n"
        f"curation = '{Path(config.roots.curation).as_posix()}'\n"
        f"protected = ['{Path(config.roots.protected[0]).as_posix()}']\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    scanned = runner.invoke(app, ["scan", "--root", "fx", "--config", str(config_file)])
    scan_id = json.loads(scanned.output)["scans"][0]["scan_id"]
    hashed = runner.invoke(app, ["hash", "--config", str(config_file)])
    assert hashed.exit_code == 0, hashed.output

    result = runner.invoke(app, ["changes", "--root", "fx", "--scan-id", scan_id, "--config", str(config_file)])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["counts"]["new"] == 1
    assert payload["events"][0]["type"] == "new"
