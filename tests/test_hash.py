"""T-P2-02 S2 hashing: correctness, idempotency, leases, priority and isolation."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO

import blake3
from typer.testing import CliRunner

from sbr.cli.app import app
from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.jobs import JobQueue, LeaseError
from sbr.registry.hash import hash_pending
from sbr.registry.scan import HASH_STAGE, scan_root
from sbr.schemas import ActivityStatus, WorkItemState
from sbr.sourcefs import SourceFS


def _open(config: SbrConfig) -> RegistryDB:
    db = RegistryDB.open(config)
    db.migrate()
    return db


def _blob_id(data: bytes) -> str:
    return "b3:" + blake3.blake3(data).hexdigest()


def test_scan_then_hash_records_correct_blobs_and_observation_links(
    make_config: Callable[..., SbrConfig], source_tree: Path
) -> None:
    config = make_config()
    with _open(config) as db:
        scan_root(config, db, "fx")
        result = hash_pending(config, db, batch_size=1)
        observations = db.repo(reg.PATH_OBSERVATION).find(order_by="relpath")
        blobs = {blob.blob_id: blob for blob in db.repo(reg.BLOB).find()}

        assert result.hashed == len(observations) == 2
        assert result.failed == 0
        assert result.bytes_hashed == sum(item.size for item in observations)
        for observation in observations:
            path = source_tree.joinpath(*observation.relpath.replace("\\", "/").split("/"))
            expected = _blob_id(path.read_bytes())
            assert observation.blob_id == expected
            blob = blobs[expected]
            assert blob.size == path.stat().st_size
            assert blob.magic_type is None and blob.format is None
            assert blob.first_seen_scan == observation.first_seen_scan
            assert blob.last_seen_scan == observation.last_seen_scan
            assert blob.activity_id == result.activity_id
            assert observation.activity_id == result.activity_id

        activity = db.repo(reg.ACTIVITY).get(result.activity_id)
        assert activity is not None and activity.status is ActivityStatus.SUCCEEDED
        assert db.repo(reg.WORK_ITEM).count({"stage": HASH_STAGE, "state": WorkItemState.DONE}) == 2


def test_duplicate_paths_share_one_blob_row(make_config: Callable[..., SbrConfig], source_tree: Path) -> None:
    original = source_tree / "Regelungstechnik" / "skript.pdf"
    duplicate = source_tree / "Formelsammlung" / "skript_kopie.pdf"
    duplicate.parent.mkdir()
    duplicate.write_bytes(original.read_bytes())
    config = make_config()

    with _open(config) as db:
        scan_root(config, db, "fx")
        result = hash_pending(config, db)
        duplicate_id = _blob_id(original.read_bytes())
        matching = db.repo(reg.PATH_OBSERVATION).find({"blob_id": duplicate_id})

        assert result.hashed == 3
        assert len(matching) == 2
        assert {item.relpath for item in matching} == {
            "Formelsammlung\\skript_kopie.pdf",
            "Regelungstechnik\\skript.pdf",
        }
        assert db.repo(reg.BLOB).count() == 2


def test_unchanged_rescan_enqueues_and_hashes_nothing(make_config: Callable[..., SbrConfig], source_tree: Path) -> None:
    config = make_config()
    with _open(config) as db:
        scan_root(config, db, "fx")
        first = hash_pending(config, db)
        jobs_before = db.repo(reg.WORK_ITEM).count()
        activities_before = db.repo(reg.ACTIVITY).count()

        scan_root(config, db, "fx")
        second = hash_pending(config, db)

        assert first.hashed == 2
        assert second.leased == second.hashed == second.failed == 0
        assert db.repo(reg.WORK_ITEM).count() == jobs_before
        assert db.repo(reg.BLOB).count() == 2
        assert db.repo(reg.ACTIVITY).count() == activities_before + 2  # re-scan plus empty hash run


def test_expired_lease_resumes_after_simulated_worker_crash_without_duplicates(
    make_config: Callable[..., SbrConfig], source_tree: Path
) -> None:
    now = [1_000]
    config = make_config()
    with _open(config) as db:
        scanner_queue = JobQueue(db.conn, clock_ms=lambda: now[0])
        scan_root(config, db, "fx", queue=scanner_queue)
        worker_a = JobQueue(db.conn, clock_ms=lambda: now[0], owner="system:worker-a")
        abandoned = worker_a.lease(HASH_STAGE, count=1, lease_ms=100)[0]
        assert abandoned.lease_token is not None

        worker_b = JobQueue(db.conn, clock_ms=lambda: now[0], owner="system:worker-b")
        assert worker_b.lease(HASH_STAGE, count=1, lease_ms=100)[0].job_id != abandoned.job_id
        # Simulate that worker B also died before doing work, then restart after all leases expire.
        now[0] += 101
        restarted = JobQueue(db.conn, clock_ms=lambda: now[0], owner="system:worker-restart")
        result = hash_pending(config, db, queue=restarted, batch_size=2, lease_ms=100)

        assert result.hashed == 2
        assert result.failed == 0
        assert db.repo(reg.PATH_OBSERVATION).count({"blob_id": None}) == 0
        assert db.repo(reg.BLOB).count() == 2
        jobs = db.repo(reg.WORK_ITEM).find({"stage": HASH_STAGE})
        assert all(job.state is WorkItemState.DONE for job in jobs)
        assert all(job.attempts == 2 for job in jobs)
        try:
            worker_a.complete(abandoned.job_id, abandoned.lease_token)
        except LeaseError:
            pass
        else:
            raise AssertionError("a stale crashed-worker lease completed a job")


def test_document_extensions_are_leased_before_media(make_config: Callable[..., SbrConfig], source_tree: Path) -> None:
    document = source_tree / "notes.PDF"
    media = source_tree / "clip.mp4"
    document.write_bytes(b"document")
    media.write_bytes(b"media")
    config = make_config()

    with _open(config) as db:
        scan_root(config, db, "fx")
        observations = {row.obs_id: row.relpath for row in db.repo(reg.PATH_OBSERVATION).find()}
        leased = JobQueue(db.conn).lease(HASH_STAGE, count=20)
        paths = [observations[item.subject_id] for item in leased]

        assert paths.index("notes.PDF") < paths.index("clip.mp4")
        doc_job = next(item for item in leased if observations[item.subject_id] == "notes.PDF")
        media_job = next(item for item in leased if observations[item.subject_id] == "clip.mp4")
        assert doc_job.priority > media_job.priority


def test_one_vanished_file_fails_path_free_and_rest_of_batch_completes(
    make_config: Callable[..., SbrConfig], source_tree: Path
) -> None:
    config = make_config()
    with _open(config) as db:
        scan_root(config, db, "fx")
        vanished = source_tree / "Regelungstechnik" / "skript.pdf"
        vanished.unlink()
        result = hash_pending(config, db, batch_size=10)
        jobs = db.repo(reg.WORK_ITEM).find({"stage": HASH_STAGE})
        failed_attempt = next(job for job in jobs if job.last_error is not None)

        assert result.hashed == 1 and result.failed == 1
        assert db.repo(reg.BLOB).count() == 1
        assert failed_attempt.state is WorkItemState.PENDING
        assert failed_attempt.last_error is not None
        assert "FileNotFoundError" in failed_attempt.last_error
        assert str(vanished) not in failed_attempt.last_error
        assert db.repo(reg.WORK_ITEM).count({"state": WorkItemState.DONE}) == 1


class OpenFailureSourceFS(SourceFS):
    def open_binary(self, root_id: str, relpath: str) -> BinaryIO:
        if relpath.endswith("skript.pdf"):
            raise PermissionError(13, "sensitive source path")
        return super().open_binary(root_id, relpath)


def test_sourcefs_open_error_is_isolated_and_message_does_not_leak_path(
    make_config: Callable[..., SbrConfig], source_tree: Path
) -> None:
    config = make_config()
    with _open(config) as db:
        scan_root(config, db, "fx")
        result = hash_pending(config, db, source_fs=OpenFailureSourceFS(config))
        errors = [job.last_error for job in db.repo(reg.WORK_ITEM).find() if job.last_error]

        assert result.hashed == 1 and result.failed == 1
        assert errors == ["PermissionError: errno=13 winerror=None"]
        assert all("sensitive" not in error and str(source_tree) not in error for error in errors)


def test_hash_cli_uses_runtime_pattern_and_prints_json(
    make_config: Callable[..., SbrConfig], source_tree: Path, tmp_path: Path
) -> None:
    config = make_config()
    config_file = tmp_path / "hash.toml"
    config_file.write_text(
        "[roots]\n"
        f"sources = [{{ id = 'fx', path = '{source_tree.as_posix()}' }}]\n"
        f"var = '{Path(config.roots.var).as_posix()}'\n"
        f"curation = '{Path(config.roots.curation).as_posix()}'\n"
        f"protected = ['{Path(config.roots.protected[0]).as_posix()}']\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    scanned = runner.invoke(app, ["scan", "--root", "fx", "--config", str(config_file)])
    assert scanned.exit_code == 0, scanned.output

    result = runner.invoke(app, ["hash", "--batch-size", "1", "--config", str(config_file)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["hashed"] == 2
    assert payload["failed"] == 0
    assert payload["bytes_hashed"] > 0
