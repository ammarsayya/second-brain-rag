"""TS-ARCH: archive member inventory, safety limits, CP437 repair, already-present detection."""

from __future__ import annotations

import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from sbr.config import SbrConfig, config_from_mapping
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.ids import hash_bytes
from sbr.registry.archives import _cp437_repair, inventory_archives
from sbr.registry.classify import classify_pending
from sbr.registry.hash import hash_pending
from sbr.registry.scan import scan_root
from sbr.safety import SourceWriteGuard
from sbr.schemas.registry import ArchiveMemberStatus

FIXTURE_CORPUS = Path(__file__).parent / "fixtures" / "corpus"


def _open(config: SbrConfig) -> RegistryDB:
    db = RegistryDB.open(config)
    db.migrate()
    return db


def _run_pipeline(config: SbrConfig, db: RegistryDB) -> None:
    scan_root(config, db, "fx")
    hash_pending(config, db)
    classify_pending(config, db)


def _fixture_config(tmp_path: Path) -> SbrConfig:
    return config_from_mapping(
        {
            "roots": {
                "sources": [{"id": "fx", "path": str(FIXTURE_CORPUS.resolve())}],
                "var": str(tmp_path / "var"),
                "curation": str(tmp_path / "curation"),
                "protected": [str(tmp_path / "quarantine")],
            }
        }
    )


def test_committed_archive_fixture_finds_already_present_and_repairs_cp437(tmp_path: Path) -> None:
    """archiv.zip (T-P1-13) has a CP437 umlaut name and a member duplicating Regelungstechnik/skript.pdf."""
    config = _fixture_config(tmp_path)
    with _open(config) as db:
        _run_pipeline(config, db)
        result = inventory_archives(config, db)

        assert result.containers_processed == 1
        assert result.containers_unsupported == 0
        assert result.containers_over_limit == 0
        assert result.members_total == 3

        members = db.repo(reg.ARCHIVE_MEMBER).find()
        by_path = {m.member_path: m for m in members}
        assert set(by_path) == {
            "Übung/Aufgabenblätter/ÜBUNG3.TXT",
            "notes/readme.txt",
            "archiv/skript_duplikat.pdf",
        }

        duplicate = by_path["archiv/skript_duplikat.pdf"]
        assert duplicate.status is ArchiveMemberStatus.ALREADY_PRESENT
        assert duplicate.member_blob == hash_bytes((FIXTURE_CORPUS / "Regelungstechnik" / "skript.pdf").read_bytes())

        legacy = by_path["Übung/Aufgabenblätter/ÜBUNG3.TXT"]
        assert legacy.status is ArchiveMemberStatus.EXTRACTED_NEW  # .TXT is a document extension
        # zipfile already decodes this (no UTF-8 flag) entry correctly via CP437 per spec; the display
        # name must stay exactly as-is, not be "repaired" into something else (see test_cp437_repair_*).
        assert legacy.member_name_display == "Übung/Aufgabenblätter/ÜBUNG3.TXT"

        readme = by_path["notes/readme.txt"]
        assert readme.status is ArchiveMemberStatus.EXTRACTED_NEW
        assert readme.extracted_path is not None
        assert Path(readme.extracted_path).read_bytes() == b"Synthetic fixture archive; no copyrighted content.\n"
        assert str(config.var_path) in readme.extracted_path
        assert "archive_extract" in readme.extracted_path


def test_re_run_is_idempotent_and_skips_already_inventoried_container(tmp_path: Path) -> None:
    config = _fixture_config(tmp_path)
    with _open(config) as db:
        _run_pipeline(config, db)
        first = inventory_archives(config, db)
        second = inventory_archives(config, db)

        assert first.containers_processed == 1
        assert second.containers_considered == 1
        assert second.containers_processed == 0
        assert second.members_total == 0
        assert db.repo(reg.ARCHIVE_MEMBER).count() == 3


def test_extraction_never_writes_to_the_source_tree(tmp_path: Path) -> None:
    config = _fixture_config(tmp_path)
    before = (FIXTURE_CORPUS / "archiv.zip").read_bytes()
    with _open(config) as db:
        _run_pipeline(config, db)
        with SourceWriteGuard.for_config(config) as guard:
            inventory_archives(config, db)
    assert guard.violations == []
    assert (FIXTURE_CORPUS / "archiv.zip").read_bytes() == before


def test_cp437_repair_fixes_the_documented_example_without_touching_correct_names() -> None:
    # docs/08 §7's own example: a UTF-8 name ("Fläche") misread through a single-byte codepage elsewhere
    # in the pipeline produces this exact garbled form; repair must reconstruct the original.
    assert _cp437_repair("Fl├ñche") == "Fläche"
    # An already-correct name (no mojibake telltale) must never be altered, even if a blind cp437<->utf-8
    # round trip on it would happen to produce different, still-printable characters (a real bug found in
    # review: 'Ü' incorrectly became 'š' this way before the telltale-gated guard was added).
    assert _cp437_repair("Übung/Aufgabenblätter/ÜBUNG3.TXT") == "Übung/Aufgabenblätter/ÜBUNG3.TXT"
    assert _cp437_repair("plain_ascii_name.txt") == "plain_ascii_name.txt"


def _seed_zip(root: Path, name: str, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(root / name, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for member_path, content in entries.items():
            zf.writestr(member_path, content)


def test_path_traversal_member_is_excluded_not_opened(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    config = make_config()
    root = Path(config.roots.sources[0].path)
    _seed_zip(root, "traversal.zip", {"../../evil.txt": b"escape attempt", "safe.txt": b"fine"})

    with _open(config) as db:
        _run_pipeline(config, db)
        inventory_archives(config, db)
        members = {m.member_path: m for m in db.repo(reg.ARCHIVE_MEMBER).find()}

        assert members["../../evil.txt"].status is ArchiveMemberStatus.EXCLUDED
        assert members["../../evil.txt"].member_blob is None
        assert members["safe.txt"].status is ArchiveMemberStatus.EXTRACTED_NEW


def test_zip_bomb_ratio_skips_every_member_without_reading_content(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    config = make_config()
    root = Path(config.roots.sources[0].path)
    # A real zip: 20 MiB of zero bytes compresses to well under 64 KiB (>300:1), a genuine high-ratio archive
    # (zipfile recomputes file_size from real written data, so declared size cannot simply be lied about).
    with zipfile.ZipFile(root / "bomb.zip", "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("huge.bin", b"\x00" * (20 * 1024 * 1024))

    with _open(config) as db:
        _run_pipeline(config, db)
        result = inventory_archives(config, db)
        members = db.repo(reg.ARCHIVE_MEMBER).find()

        assert result.containers_over_limit == 1
        assert result.containers_processed == 0
        assert len(members) == 1
        assert members[0].status is ArchiveMemberStatus.SKIPPED_LIMIT
        assert members[0].member_blob is None  # never opened/hashed


def test_non_document_new_member_is_recorded_but_not_extracted(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    config = make_config()
    root = Path(config.roots.sources[0].path)
    _seed_zip(root, "media.zip", {"clip.mp4": b"not a real video but new content"})

    with _open(config) as db:
        _run_pipeline(config, db)
        inventory_archives(config, db)
        [member] = db.repo(reg.ARCHIVE_MEMBER).find()

        assert member.status is ArchiveMemberStatus.SKIPPED_LIMIT
        assert member.member_blob is not None  # still hashed and known
        assert member.extracted_path is None  # but not physically extracted


def test_corrupt_archive_is_tracked_as_read_failure_not_silently_dropped(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    """Regression: a container whose outcome isn't processed/unsupported/over_limit must still be counted.

    Found in review: containers_considered (408) didn't add up to processed + unsupported + over_limit against
    the real corpus (385 + 21 + 0 = 406, two short) because read_failure outcomes were silently untracked.
    """
    config = make_config()
    root = Path(config.roots.sources[0].path)
    # Real ZIP magic bytes (classify.py detects it as knowledge_class=archive, format=zip) but truncated/corrupt,
    # so zipfile.ZipFile() raises BadZipFile when actually opened for member inventory.
    (root / "corrupt.zip").write_bytes(b"PK\x03\x04" + b"\x00" * 40)

    with _open(config) as db:
        _run_pipeline(config, db)
        result = inventory_archives(config, db)

        assert result.containers_considered == 1
        assert result.containers_read_failure == 1
        assert result.containers_processed == 0
        assert (
            result.containers_processed
            + result.containers_unsupported
            + result.containers_over_limit
            + result.containers_read_failure
            == result.containers_considered
        )
        assert db.repo(reg.ARCHIVE_MEMBER).count() == 0


def test_rar_dispatch_is_inventoried_when_the_tool_is_available(
    make_config: Callable[..., SbrConfig], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RAR needs the proprietary `rar` packer to build a real fixture, which this environment doesn't have

    (only the free `unrar` extractor). This test proves this module's own RAR dispatch/integration logic end
    to end — real-corpus reconciliation (docs/28 T-P2-08) is what actually exercises `rarfile`'s own RAR
    parsing against genuine archives, which no synthetic fixture here can substitute for.
    """
    import rarfile as rarfile_module

    from sbr.registry import archives as archives_module

    class _StubRarInfo:
        def __init__(self, filename: str, file_size: int) -> None:
            self.filename = filename
            self.file_size = file_size

        def is_dir(self) -> bool:
            return False

    class _StubRarFile:
        def __init__(self, path: Path) -> None:
            self._entries = {"inside.txt": b"content that only lives in this rar"}

        def infolist(self) -> list[_StubRarInfo]:
            return [_StubRarInfo(name, len(data)) for name, data in self._entries.items()]

        def open(self, name: str) -> Any:
            import io

            return io.BytesIO(self._entries[name])

    monkeypatch.setattr(rarfile_module, "tool_setup", lambda: None)
    monkeypatch.setattr(archives_module.rarfile, "RarFile", _StubRarFile)

    config = make_config()
    root = Path(config.roots.sources[0].path)
    (root / "fake.rar").write_bytes(b"Rar!\x1a\x07\x01\x00" + b"\x00" * 20)  # real RAR5 magic bytes

    with _open(config) as db:
        _run_pipeline(config, db)
        result = inventory_archives(config, db)
        [member] = db.repo(reg.ARCHIVE_MEMBER).find()

        assert result.containers_processed == 1
        assert result.containers_unsupported == 0
        assert member.member_path == "inside.txt"
        assert member.status is ArchiveMemberStatus.EXTRACTED_NEW
        assert member.extracted_path is not None
        assert Path(member.extracted_path).read_bytes() == b"content that only lives in this rar"


def test_cli_prints_json(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from sbr.cli.app import app

    config = make_config()
    root = Path(config.roots.sources[0].path)
    _seed_zip(root, "cli.zip", {"note.txt": b"cli smoke test"})
    config_file = tmp_path / "archives.toml"
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

    result = runner.invoke(app, ["archives", "--config", str(config_file)])

    assert result.exit_code == 0, result.output
    import json

    payload = json.loads(result.output)
    assert payload["containers_processed"] == 1
    assert payload["members_extracted_new"] == 1
