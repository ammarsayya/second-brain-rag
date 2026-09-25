"""T-P2-04 S4 classification: rules, signatures, PDF encryption, reports, CLI, and safety."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO, cast

from typer.testing import CliRunner

from sbr.cli.app import app
from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.registry.classify import classify_pending, load_classification_rules
from sbr.registry.hash import hash_pending
from sbr.registry.scan import scan_root
from sbr.safety import SourceWriteGuard
from sbr.schemas import BlobRecord
from sbr.schemas.registry import KnowledgeClass
from sbr.sourcefs import SourceFS

T0_EXTENSIONS = {
    KnowledgeClass.DOCUMENT: {".pdf", ".txt", ".md", ".tex"},
    KnowledgeClass.OFFICE: {".docx", ".doc", ".pptx", ".ppt", ".ppsx"},
    KnowledgeClass.SPREADSHEET: {".xlsx", ".xls", ".csv"},
    KnowledgeClass.MEDIA: {".mp4", ".avi", ".mkv", ".m4v", ".webm", ".mov", ".mp3"},
    KnowledgeClass.IMAGE: {".jpg", ".jpeg", ".png", ".bmp", ".gif"},
    KnowledgeClass.CODE: {".java", ".m", ".c", ".h", ".ino", ".py", ".sh"},
    KnowledgeClass.DATA: {".mat", ".fig", ".slx", ".mlapp"},
    KnowledgeClass.TOOL_ARTIFACT: {".wbjn", ".mechdb", ".agdb", ".rst", ".wbpz", ".class", ".exml", ".ctxt"},
    KnowledgeClass.ARCHIVE: {".zip", ".rar", ".7z", ".tar", ".gz"},
    KnowledgeClass.EXECUTABLE: {".exe", ".jar", ".bat"},
    KnowledgeClass.THIRD_PARTY_REFERENCE: {".html", ".htm"},
}


def _open(config: SbrConfig) -> RegistryDB:
    db = RegistryDB.open(config)
    db.migrate()
    return db


def _write_config(path: Path, config: SbrConfig) -> None:
    source = Path(config.roots.sources[0].path).as_posix()
    path.write_text(
        "[roots]\n"
        f"sources = [{{ id = 'fx', path = '{source}' }}]\n"
        f"var = '{Path(config.roots.var).as_posix()}'\n"
        f"curation = '{Path(config.roots.curation).as_posix()}'\n"
        f"protected = ['{Path(config.roots.protected[0]).as_posix()}']\n",
        encoding="utf-8",
    )


def _classified_by_path(db: RegistryDB) -> dict[str, BlobRecord]:
    blobs = {blob.blob_id: blob for blob in db.repo(reg.BLOB).find()}
    return {
        observation.relpath: blobs[observation.blob_id]
        for observation in db.repo(reg.PATH_OBSERVATION).find()
        if observation.blob_id is not None
    }


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_rules_map_every_t0_extension() -> None:
    rules = load_classification_rules()
    for expected_class, extensions in T0_EXTENSIONS.items():
        assert {extension: rules.extensions.get(extension) for extension in extensions} == {
            extension: expected_class for extension in extensions
        }


def test_extension_path_and_zero_byte_classification(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    root = tmp_path / "src_root"
    root.mkdir()
    samples = {
        "notes.txt": KnowledgeClass.DOCUMENT,
        "paper.docx": KnowledgeClass.OFFICE,
        "table.csv": KnowledgeClass.SPREADSHEET,
        "clip.mkv": KnowledgeClass.MEDIA,
        "photo.jpeg": KnowledgeClass.IMAGE,
        "script.py": KnowledgeClass.CODE,
        "model.mat": KnowledgeClass.DATA,
        "solver.wbjn": KnowledgeClass.TOOL_ARTIFACT,
        "bundle.tar": KnowledgeClass.ARCHIVE,
        "run.bat": KnowledgeClass.EXECUTABLE,
        "help.html": KnowledgeClass.THIRD_PARTY_REFERENCE,
    }
    for index, name in enumerate(samples):
        (root / name).write_bytes(f"sample-{index}".encode())
    (root / "empty.pdf").write_bytes(b"")
    (root / ".metadata").mkdir()
    (root / ".metadata" / "index.html").write_bytes(b"tool help")
    (root / "__MACOSX").mkdir()
    (root / "__MACOSX" / "notes.txt").write_bytes(b"junk")

    config = make_config()
    with _open(config) as db:
        scan_root(config, db, "fx")
        hash_pending(config, db)
        result = classify_pending(config, db)
        by_path = _classified_by_path(db)

        assert result.updated == len(samples) + 3
        for name, expected in samples.items():
            assert by_path[name].knowledge_class is expected
            assert by_path[name].format == Path(name).suffix[1:]
        assert by_path["empty.pdf"].knowledge_class is KnowledgeClass.JUNK
        assert by_path["empty.pdf"].format == "empty"
        assert by_path[".metadata\\index.html"].knowledge_class is KnowledgeClass.TOOL_ARTIFACT
        assert by_path["__MACOSX\\notes.txt"].knowledge_class is KnowledgeClass.JUNK


def test_magic_is_authoritative_and_container_extensions_are_preserved(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    root = tmp_path / "src_root"
    root.mkdir()
    (root / "no_extension").write_bytes(b"%PDF-1.7\nplain\n")
    (root / "misleading.txt").write_bytes(b"\x89PNG\r\n\x1a\nimage")
    (root / "office.docx").write_bytes(b"PK\x03\x04office")
    (root / "archive.txt").write_bytes(b"PK\x03\x04archive")
    (root / "legacy").write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1legacy")

    config = make_config()
    with _open(config) as db:
        scan_root(config, db, "fx")
        hash_pending(config, db)
        classify_pending(config, db)
        by_path = _classified_by_path(db)

        assert (by_path["no_extension"].format, by_path["no_extension"].knowledge_class) == (
            "pdf",
            KnowledgeClass.DOCUMENT,
        )
        assert (by_path["misleading.txt"].format, by_path["misleading.txt"].knowledge_class) == (
            "png",
            KnowledgeClass.IMAGE,
        )
        assert (by_path["office.docx"].format, by_path["office.docx"].knowledge_class) == (
            "docx",
            KnowledgeClass.OFFICE,
        )
        assert (by_path["archive.txt"].format, by_path["archive.txt"].knowledge_class) == (
            "zip",
            KnowledgeClass.ARCHIVE,
        )
        assert (by_path["legacy"].format, by_path["legacy"].knowledge_class) == (
            "ole2",
            KnowledgeClass.OFFICE,
        )


def test_pdf_encryption_marker_is_flagged_without_decryption(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    root = tmp_path / "src_root"
    root.mkdir()
    (root / "protected.pdf").write_bytes(b"%PDF-1.7\n1 0 obj\n<< /Encrypt 2 0 R >>\n%%EOF")
    (root / "plain.pdf").write_bytes(b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\n%%EOF")
    config = make_config()

    with _open(config) as db:
        scan_root(config, db, "fx")
        hash_pending(config, db)
        classify_pending(config, db)
        by_path = _classified_by_path(db)
        assert by_path["protected.pdf"].encrypted is True
        assert by_path["plain.pdf"].encrypted is False


def test_unknown_extensions_are_returned_for_review(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    root = tmp_path / "src_root"
    root.mkdir()
    (root / "review.xyzzy").write_bytes(b"not recognized")
    (root / "extensionless").write_bytes(b"not recognized either")
    config = make_config()

    with _open(config) as db:
        scan_root(config, db, "fx")
        hash_pending(config, db)
        result = classify_pending(config, db)
        assert {(item.relpath, item.extension) for item in result.unknowns} == {
            ("extensionless", "<none>"),
            ("review.xyzzy", ".xyzzy"),
        }
        by_path = _classified_by_path(db)
        assert by_path["review.xyzzy"].format == "xyzzy"
        assert by_path["review.xyzzy"].knowledge_class is KnowledgeClass.UNKNOWN


class FailingOpenSourceFS(SourceFS):
    def open_binary(self, root_id: str, relpath: str) -> BinaryIO:
        if relpath == "bad.pdf":
            raise PermissionError(13, "sensitive source path")
        return super().open_binary(root_id, relpath)


def test_source_error_isolated_and_path_free(make_config: Callable[..., SbrConfig], tmp_path: Path) -> None:
    root = tmp_path / "src_root"
    root.mkdir()
    (root / "bad.pdf").write_bytes(b"%PDF-1.7\nblocked")
    (root / "good.txt").write_bytes(b"good")
    config = make_config()
    with _open(config) as db:
        scan_root(config, db, "fx")
        hash_pending(config, db)
        result = classify_pending(config, db, source_fs=FailingOpenSourceFS(config))

        assert result.updated == 1
        assert len(result.failures) == 1
        assert result.failures[0].error == "PermissionError: errno=13 winerror=None"
        assert "sensitive" not in result.failures[0].error


class TrackingReader:
    def __init__(self, stream: BinaryIO, reads: list[int]) -> None:
        self._stream = stream
        self._reads = reads

    def read(self, size: int = -1) -> bytes:
        self._reads.append(size)
        return self._stream.read(size)

    def seek(self, offset: int, whence: int = 0) -> int:
        return self._stream.seek(offset, whence)

    def __enter__(self) -> TrackingReader:
        return self

    def __exit__(self, *args: object) -> None:
        self._stream.close()


class BoundedReadSourceFS(SourceFS):
    def __init__(self, config: SbrConfig, reads: list[int]) -> None:
        super().__init__(config)
        self._reads = reads

    def open_binary(self, root_id: str, relpath: str) -> BinaryIO:
        return cast(BinaryIO, TrackingReader(super().open_binary(root_id, relpath), self._reads))


def test_pdf_classification_reads_only_header_and_bounded_tail(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    root = tmp_path / "src_root"
    root.mkdir()
    (root / "large.pdf").write_bytes(b"%PDF-1.7\n" + b"x" * (2 * 1024 * 1024))
    config = make_config()
    with _open(config) as db:
        scan_root(config, db, "fx")
        hash_pending(config, db)
        reads: list[int] = []
        result = classify_pending(config, db, source_fs=BoundedReadSourceFS(config, reads))
        assert result.updated == 1
        assert reads == [64, 1024 * 1024]


def test_classification_makes_zero_source_mutations(make_config: Callable[..., SbrConfig], source_tree: Path) -> None:
    config = make_config()
    before = _tree_bytes(source_tree)
    with _open(config) as db:
        scan_root(config, db, "fx")
        hash_pending(config, db)
        with SourceWriteGuard.for_config(config) as guard:
            result = classify_pending(config, db)
    assert result.updated == len(before)
    assert guard.violations == []
    assert _tree_bytes(source_tree) == before


def test_classify_cli_and_manual_review_reports(
    make_config: Callable[..., SbrConfig], source_tree: Path, tmp_path: Path
) -> None:
    config = make_config()
    (source_tree / "unknown.xyzzy").write_bytes(b"review me")
    config_file = tmp_path / "classify.toml"
    _write_config(config_file, config)
    runner = CliRunner()
    assert runner.invoke(app, ["scan", "--root", "fx", "--config", str(config_file)]).exit_code == 0
    assert runner.invoke(app, ["hash", "--config", str(config_file)]).exit_code == 0
    classified = runner.invoke(app, ["classify", "--config", str(config_file)])
    assert classified.exit_code == 0, classified.output
    payload = json.loads(classified.output)
    assert payload["updated"] == 3
    assert payload["unknown_count"] == 1
    assert payload["unknowns"][0]["extension"] == ".xyzzy"

    json_report = tmp_path / "classification.json"
    markdown_report = tmp_path / "classification.md"
    completed = subprocess.run(
        [
            sys.executable,
            "tools/validate_classify.py",
            "--config",
            str(config_file),
            "--root",
            "fx",
            "--count",
            "200",
            "--json-output",
            str(json_report),
            "--markdown-output",
            str(markdown_report),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(json_report.read_text(encoding="utf-8"))
    assert report["verdict"] is None
    assert report["sampled"] == 3
    assert all("relpath_display" in row for row in report["sample"])
    assert "Human review artifact only" in markdown_report.read_text(encoding="utf-8")
