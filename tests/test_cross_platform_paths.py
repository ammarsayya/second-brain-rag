"""Cross-platform path regressions: canonical relpaths vs native paths, Unicode NFC/NFD, umlauts, zip separators.

The canonical, persisted ``relpath`` is ``\\``-joined and NFC on every OS; ``relpath_raw`` is the exact on-disk name;
native paths use the host separator. These tests pin that contract so registry data stays portable between Windows,
macOS and Linux. Only the host this suite runs on is exercised for real; the Windows/POSIX join branches are
pure string logic and are tested on any host via ``_IS_WINDOWS``.
"""

from __future__ import annotations

import errno
import io
import os
import re
import sys
import unicodedata
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from sbr import sourcefs as sourcefs_mod
from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.registry.archives import _zip_members
from sbr.registry.classify import classify_pending
from sbr.registry.hash import hash_pending
from sbr.registry.scan import scan_root
from sbr.reports.manifest import build_manifest, render_csv_rows, render_markdown
from sbr.sourcefs import SourceFS, SourcePath, split_relpath

FIXTURE_CORPUS = Path(__file__).resolve().parent / "fixtures" / "corpus"

UEBUNG_NFC = unicodedata.normalize("NFC", "Übung")
UEBUNG_NFD = unicodedata.normalize("NFD", "Übung")
BLAETTER_NFD = unicodedata.normalize("NFD", "Aufgabenblätter.pdf")


def _open(config: SbrConfig) -> RegistryDB:
    db = RegistryDB.open(config)
    db.migrate()
    return db


# -- canonical relpath: Windows-style and POSIX-style input are the same identifier --------------------------------


@pytest.mark.parametrize(
    "relpath",
    [
        "Regelungstechnik\\Übung\\blatt 1.txt",  # Windows-style
        "Regelungstechnik/Übung/blatt 1.txt",  # POSIX-style
        "Regelungstechnik/Übung\\blatt 1.txt",  # mixed
        "./Regelungstechnik//Übung/blatt 1.txt/",  # redundant components
    ],
)
def test_windows_and_posix_style_relpaths_resolve_to_one_canonical_identifier(
    make_config: Callable[..., SbrConfig], source_tree: Path, relpath: str
) -> None:
    fs = SourceFS(make_config())
    sp = fs.resolve("fx", relpath)
    assert split_relpath(relpath) == ("Regelungstechnik", "Übung", "blatt 1.txt")
    assert sp.relpath == "Regelungstechnik\\Übung\\blatt 1.txt"
    assert sp.display_path == str(source_tree / "Regelungstechnik" / "Übung" / "blatt 1.txt")
    assert fs.read_bytes("fx", relpath) == "Aufgabe 1: ẋ = Ax + Bu\n".encode()


def test_native_join_uses_the_host_separator_for_each_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    parts = ("Regelungstechnik", "Übung", "blatt 1.txt")
    monkeypatch.setattr(sourcefs_mod, "_IS_WINDOWS", True)
    assert sourcefs_mod._native_join("D:\\MBI-BRAIN\\", parts) == "D:\\MBI-BRAIN\\Regelungstechnik\\Übung\\blatt 1.txt"
    assert sourcefs_mod._native_join("D:\\", parts) == "D:\\Regelungstechnik\\Übung\\blatt 1.txt"
    assert sourcefs_mod._native_join("D:\\MBI-BRAIN", ()) == "D:\\MBI-BRAIN"
    monkeypatch.setattr(sourcefs_mod, "_IS_WINDOWS", False)
    assert (
        sourcefs_mod._native_join("/Users/ammar/DriveD/MBI-BRAIN/", parts)
        == "/Users/ammar/DriveD/MBI-BRAIN/Regelungstechnik/Übung/blatt 1.txt"
    )
    assert sourcefs_mod._native_join("/", parts) == "/Regelungstechnik/Übung/blatt 1.txt"
    assert sourcefs_mod._native_join("/srv/corpus", ()) == "/srv/corpus"


def test_iter_dir_children_carry_canonical_backslash_relpaths(
    make_config: Callable[..., SbrConfig], source_tree: Path
) -> None:
    fs = SourceFS(make_config())
    children = {e.name: e for e in fs.iter_dir("fx", "Regelungstechnik")}
    assert set(children) == {"skript.pdf", "Übung"}
    assert children["Übung"].relpath == "Regelungstechnik\\Übung"
    nested = {e.relpath for e in fs.iter_dir("fx", children["Übung"].relpath)}
    assert nested == {"Regelungstechnik\\Übung\\blatt 1.txt"}


@pytest.mark.skipif(sys.platform == "win32", reason="NTFS cannot hold a literal backslash in a file name")
def test_posix_name_with_literal_backslash_is_reported_not_misparsed(
    make_config: Callable[..., SbrConfig], source_tree: Path
) -> None:
    (source_tree / "empty" / "a\\b.txt").write_bytes(b"ambiguous")
    entries = list(SourceFS(make_config()).iter_dir("fx", "empty"))
    assert len(entries) == 1
    assert entries[0].error == "UnrepresentableName: backslash"
    assert entries[0].size is None and not entries[0].is_file


# -- Unicode: NFD on disk, NFC in the registry, the exact raw name used for access --------------------------------


class _ExactNameSourceFS(SourceFS):
    """Simulates a normalization-sensitive filesystem (ext4, NTFS) on any host, including normalization-insensitive
    APFS: each relpath component must match a directory entry byte-for-byte."""

    def resolve(self, root_id: str, relpath: str = "") -> SourcePath:
        sp = super().resolve(root_id, relpath)
        current = Path(self.root_path(root_id))
        for part in split_relpath(relpath):
            if part not in os.listdir(current):
                raise FileNotFoundError(errno.ENOENT, "no entry with this exact (normalization-sensitive) name")
            current = current / part
        return sp


def _nfd_tree(root: Path) -> None:
    folder = root / "Regelungstechnik" / UEBUNG_NFD
    folder.mkdir(parents=True)
    (folder / BLAETTER_NFD).write_bytes(b"%PDF-1.7\numlaut nfd\n")
    (root / "Regelungstechnik" / "skript.pdf").write_bytes(b"%PDF-1.7\nplain\n")


def test_nfd_names_are_stored_nfc_and_raw_and_hash_uses_the_exact_on_disk_name(
    make_config: Callable[..., SbrConfig],
) -> None:
    config = make_config()
    root = Path(config.roots.sources[0].path)
    _nfd_tree(root)
    on_disk = os.listdir(root / "Regelungstechnik")
    assert UEBUNG_NFD in on_disk  # the host kept the NFD form (APFS, ext4 and NTFS all preserve it)

    fs = _ExactNameSourceFS(config)
    with _open(config) as db:
        record = scan_root(config, db, "fx", source_fs=fs)
        assert record.files_seen == 2 and record.errors == 0

        observations = {o.relpath: o for o in db.repo(reg.PATH_OBSERVATION).find()}
        nfc_relpath = unicodedata.normalize("NFC", f"Regelungstechnik\\{UEBUNG_NFD}\\{BLAETTER_NFD}")
        assert set(observations) == {nfc_relpath, "Regelungstechnik\\skript.pdf"}
        umlaut = observations[nfc_relpath]
        assert unicodedata.is_normalized("NFC", umlaut.relpath)
        assert umlaut.relpath_raw == f"Regelungstechnik\\{UEBUNG_NFD}\\{BLAETTER_NFD}"
        assert umlaut.relpath != umlaut.relpath_raw
        assert umlaut.folder_tokens == ["regelungstechnik", unicodedata.normalize("NFC", "übung")]

        hashed = hash_pending(config, db, source_fs=fs)
        assert hashed.failed == 0 and hashed.hashed == 2
        classified = classify_pending(config, db, source_fs=fs)
        assert classified.failures == ()


def test_nfc_and_nfd_spellings_of_one_tree_produce_identical_manifests(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    """Stable manifest serialization: the report depends on canonical relpaths, never on the on-disk form."""

    def manifest_for(form: str) -> tuple[str, list[tuple[str, str, str, str]]]:
        base = tmp_path / form
        src = base / "src"
        folder = src / unicodedata.normalize(form, "Strömungslehre") / unicodedata.normalize(form, "Übungen")
        folder.mkdir(parents=True)
        (folder / unicodedata.normalize(form, "Lösung_1.pdf")).write_bytes(b"%PDF-1.7\nloesung\n")
        (src / "notes.txt").write_text("plain", encoding="utf-8")
        config = make_config(
            sources=[{"id": "fx", "path": str(src)}], var=str(base / "var"), curation=str(base / "cur")
        )
        with _open(config) as db:
            scan_root(config, db, "fx")
            hash_pending(config, db)
            classify_pending(config, db)
            report = build_manifest(config, db)
        # Only per-run ids (scan_...) may differ between the two runs; everything path-derived must be identical.
        mask = re.compile(r"scan_[0-9A-HJKMNP-TV-Z]{26}")
        rows = [tuple(mask.sub("scan_<id>", cell) for cell in row) for row in render_csv_rows(report)]
        return mask.sub("scan_<id>", render_markdown(report)), rows

    nfc, nfd = manifest_for("NFC"), manifest_for("NFD")
    assert nfc == nfd
    assert "Strömungslehre" in nfc[0] and unicodedata.normalize("NFD", "Strömungslehre") not in nfc[0]


# -- fixture discovery: the committed corpus is found completely, once, in canonical form --------------------------


def test_committed_fixture_corpus_is_discovered_completely_and_canonically(tmp_path: Path) -> None:
    from sbr.config import config_from_mapping

    config = config_from_mapping(
        {
            "roots": {
                "sources": [{"id": "fx", "path": str(FIXTURE_CORPUS)}],
                "var": str(tmp_path / "var"),
                "curation": str(tmp_path / "curation"),
                "protected": [str(tmp_path / "quarantine")],
            }
        }
    )
    with _open(config) as db:
        record = scan_root(config, db, "fx")
        relpaths = sorted(o.relpath for o in db.repo(reg.PATH_OBSERVATION).find())
    assert record.errors == 0
    assert relpaths == sorted(
        [
            "Formelsammlung\\skript_kopie.pdf",
            "Regelungstechnik\\skript.pdf",
            f"Regelungstechnik\\{UEBUNG_NFC}\\folien.pptx",
            f"Regelungstechnik\\{UEBUNG_NFC}\\scan_seite1.pdf",
            f"Regelungstechnik\\{UEBUNG_NFC}\\skript_annotiert.pdf",
            f"Regelungstechnik\\{UEBUNG_NFC}\\uebung1.docx",
            "archiv.zip",
        ]
    )


# -- archives: legacy backslash member names are canonical "/" on every OS ----------------------------------------


def test_zip_member_paths_use_forward_slashes_on_every_os() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("plain/readme.txt", b"posix-style")
        legacy = zipfile.ZipInfo("Übung/Lösungen/BLATT1.TXT")
        legacy.orig_filename = "Übung\\Lösungen\\BLATT1.TXT"
        zf.writestr(legacy, b"legacy")
    # Rewrite the stored name bytes to the DOS-tool form (backslashes), which zipfile would not emit itself.
    raw = buffer.getvalue().replace("Übung/Lösungen/".encode(), "Übung\\Lösungen\\".encode())
    with zipfile.ZipFile(io.BytesIO(raw)) as check:
        assert any("\\" in info.orig_filename for info in check.infolist())

    plans, opener = _zip_members(io.BytesIO(raw))
    assert sorted(p.path for p in plans) == ["plain/readme.txt", "Übung/Lösungen/BLATT1.TXT"]
    with opener("Übung/Lösungen/BLATT1.TXT") as member:
        assert member.read() == b"legacy"
