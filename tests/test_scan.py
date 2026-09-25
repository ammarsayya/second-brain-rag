"""T-P2-01 scanner: deterministic observations, resume, error isolation and S2 enqueueing."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from sbr.cli.app import app
from sbr.config import SbrConfig, config_from_mapping
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.registry.scan import HASH_STAGE, scan_root
from sbr.schemas import ActivityStatus
from sbr.schemas.registry import ScanStatus
from sbr.sourcefs import SourceEntry


def _open(config: SbrConfig) -> RegistryDB:
    db = RegistryDB.open(config)
    db.migrate()
    return db


def _scan(config: SbrConfig, **kwargs: Any) -> tuple[RegistryDB, Any]:
    db = _open(config)
    return db, scan_root(config, db, "fx", **kwargs)


def test_empty_corpus(make_config: Callable[..., SbrConfig]) -> None:
    config = make_config()
    db, record = _scan(config)
    try:
        assert record.status is ScanStatus.COMPLETED
        assert (record.files_seen, record.bytes_seen, record.errors) == (0, 0, 0)
        assert db.repo(reg.PATH_OBSERVATION).count() == 0
        assert db.repo(reg.WORK_ITEM).count() == 0
    finally:
        db.close()


def test_fixture_metadata_unicode_nesting_duplicates_and_zero_byte(
    make_config: Callable[..., SbrConfig], source_tree: Path
) -> None:
    duplicate = source_tree / "Formelsammlung" / "skript_kopie.pdf"
    duplicate.parent.mkdir()
    duplicate.write_bytes(b"%PDF-1.7\nsynthetic\n")
    zero = source_tree / "leer.txt"
    zero.write_bytes(b"")
    expected = {
        str(path.relative_to(source_tree)).replace("/", "\\"): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in source_tree.rglob("*")
        if path.is_file()
    }

    db, record = _scan(make_config())
    try:
        observations = db.repo(reg.PATH_OBSERVATION).find(order_by="relpath")
        assert record.files_seen == len(expected)
        assert {item.relpath: (item.size, item.mtime_ns) for item in observations} == expected
        assert any("Übung" in item.relpath for item in observations)
        assert next(item for item in observations if item.relpath == "leer.txt").size == 0
        assert len([item for item in observations if item.display_name in {"skript.pdf", "skript_kopie.pdf"}]) == 2
        assert all(item.first_seen_scan == record.scan_id == item.last_seen_scan for item in observations)
        assert db.repo(reg.WORK_ITEM).count({"stage": HASH_STAGE}) == len(expected)
    finally:
        db.close()


def test_committed_generated_corpus_matches_exact_metadata(tmp_path: Path) -> None:
    corpus = Path(__file__).parent / "fixtures" / "corpus"
    config = config_from_mapping(
        {
            "roots": {
                "sources": [{"id": "fx", "path": str(corpus.resolve())}],
                "var": str(tmp_path / "var"),
                "curation": str(tmp_path / "curation"),
                "protected": [str(tmp_path / "quarantine")],
            }
        }
    )
    expected = {
        str(path.relative_to(corpus)).replace("/", "\\"): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in corpus.rglob("*")
        if path.is_file()
    }
    db, record = _scan(config)
    try:
        got = db.repo(reg.PATH_OBSERVATION).find(order_by="relpath")
        assert record.files_seen == len(expected)
        assert {item.relpath: (item.size, item.mtime_ns) for item in got} == expected
    finally:
        db.close()


class FakeSourceFS:
    def __init__(self, entries: dict[str, list[SourceEntry] | BaseException]) -> None:
        self.entries = entries
        self.calls: list[str] = []

    def iter_dir(self, root_id: str, relpath: str = "") -> Iterator[SourceEntry]:
        assert root_id == "fx"
        self.calls.append(relpath)
        value = self.entries[relpath]
        if isinstance(value, BaseException):
            raise value
        yield from value


class SpyQueue:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, int]] = []

    def enqueue(self, subject_id: str, stage: str, stage_version: str, *, priority: int = 0) -> None:
        self.calls.append((subject_id, stage, stage_version, priority))


def _entry(
    relpath: str,
    *,
    directory: bool = False,
    link: bool = False,
    size: int | None = 1,
    mtime: int | None = 2,
    error: str | None = None,
) -> SourceEntry:
    return SourceEntry(
        relpath=relpath,
        name=relpath.rsplit("\\", 1)[-1],
        is_dir=directory,
        is_file=not directory and not link and error is None,
        is_link=link,
        size=size,
        mtime_ns=mtime,
        error=error,
    )


def test_errors_continue_and_are_counted(make_config: Callable[..., SbrConfig]) -> None:
    fake = FakeSourceFS(
        {
            "": [_entry("bad", directory=True), _entry("good.txt"), _entry("stat.bin", error="PermissionError")],
            "bad": PermissionError(13, "denied"),
        }
    )
    db, record = _scan(make_config(), source_fs=fake)  # type: ignore[arg-type]
    try:
        assert record.status is ScanStatus.COMPLETED
        assert (record.files_seen, record.errors) == (1, 2)
        assert db.repo(reg.PATH_OBSERVATION).find()[0].relpath == "good.txt"
    finally:
        db.close()


def test_deterministic_order_windows_relpaths_and_protected_link_not_followed(
    make_config: Callable[..., SbrConfig],
) -> None:
    fake = FakeSourceFS(
        {
            "": [_entry("z.txt"), _entry("Dossier", directory=True), _entry("quarantine", directory=True, link=True)],
            "Dossier": [_entry("Dossier\\β.txt"), _entry("Dossier\\a.txt")],
        }
    )
    queue = SpyQueue()
    db, record = _scan(make_config(), source_fs=fake, queue=queue)  # type: ignore[arg-type]
    try:
        observations = db.repo(reg.PATH_OBSERVATION).find()
        by_id = {item.obs_id: item.relpath for item in observations}
        assert [by_id[subject] for subject, _, _, _ in queue.calls] == [
            "Dossier\\a.txt",
            "Dossier\\β.txt",
            "z.txt",
        ]
        assert fake.calls == ["", "Dossier"]
        assert all("/" not in item.relpath for item in observations)
        assert record.errors == 0
    finally:
        db.close()


def test_repeat_scan_reuses_observations_and_only_enqueues_changes(
    make_config: Callable[..., SbrConfig], source_tree: Path
) -> None:
    config = make_config()
    with _open(config) as db:
        first = scan_root(config, db, "fx")
        before = {item.relpath: item for item in db.repo(reg.PATH_OBSERVATION).find()}
        jobs_before = db.repo(reg.WORK_ITEM).count()
        second = scan_root(config, db, "fx")
        unchanged = {item.relpath: item for item in db.repo(reg.PATH_OBSERVATION).find()}
        assert len(unchanged) == len(before)
        assert db.repo(reg.WORK_ITEM).count() == jobs_before
        for relpath, item in unchanged.items():
            assert item.obs_id == before[relpath].obs_id
            assert item.first_seen_scan == first.scan_id
            assert item.last_seen_scan == second.scan_id

        target = source_tree / "Regelungstechnik" / "skript.pdf"
        target.write_bytes(target.read_bytes() + b"changed")
        spy = SpyQueue()
        third = scan_root(config, db, "fx", queue=spy)  # type: ignore[arg-type]
        changed = db.repo(reg.PATH_OBSERVATION).find({"relpath": "Regelungstechnik\\skript.pdf"})[0]
        assert changed.obs_id == before[changed.relpath].obs_id
        assert changed.last_seen_scan == third.scan_id
        assert changed.blob_id == before[changed.relpath].blob_id
        assert spy.calls == [(changed.obs_id, HASH_STAGE, f"1+scan.{third.scan_id.removeprefix('scan_')}", 100)]


def test_interrupt_marks_scan_and_activity_then_root_can_restart(make_config: Callable[..., SbrConfig]) -> None:
    fake = FakeSourceFS({"": KeyboardInterrupt()})
    config = make_config()
    with _open(config) as db:
        with pytest.raises(KeyboardInterrupt):
            scan_root(config, db, "fx", source_fs=fake)  # type: ignore[arg-type]
        interrupted = db.repo(reg.SCAN).find()[0]
        activity = db.repo(reg.ACTIVITY).get(interrupted.activity_id)
        assert interrupted.status is ScanStatus.INTERRUPTED
        assert activity is not None and activity.status is ActivityStatus.CANCELLED

        completed = scan_root(config, db, "fx")
        assert completed.status is ScanStatus.COMPLETED
        assert db.repo(reg.SCAN).count() == 2


def test_scan_cli_uses_runtime_pattern_and_prints_json(
    make_config: Callable[..., SbrConfig], source_tree: Path, tmp_path: Path
) -> None:
    config = make_config()
    config_file = tmp_path / "scan.toml"
    config_file.write_text(
        "[roots]\n"
        f"sources = [{{ id = 'fx', path = '{source_tree}' }}]\n"
        f"var = '{config.roots.var}'\n"
        f"curation = '{config.roots.curation}'\n"
        f"protected = ['{config.roots.protected[0]}']\n",
        encoding="utf-8",
    )
    result = CliRunner().invoke(app, ["scan", "--root", "fx", "--config", str(config_file)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["scans"][0]["status"] == "completed"
    assert payload["scans"][0]["files_seen"] == 2
