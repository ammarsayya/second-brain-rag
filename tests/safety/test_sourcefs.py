"""TS-SAFE-1: SourceFS refuses write, rename and delete under source roots, and refuses escapes."""

from __future__ import annotations

import io
import os
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from sbr.config import SbrConfig
from sbr.sourcefs import SourceAccessError, SourceFS, split_relpath

MUTATOR_NAMES = {
    "write",
    "remove",
    "unlink",
    "rename",
    "replace",
    "delete",
    "move",
    "chmod",
    "mkdir",
    "touch",
    "truncate",
}


def test_sourcefs_exposes_no_mutators() -> None:
    public = {n for n in dir(SourceFS) if not n.startswith("_")}
    assert not {n for n in public if any(m in n.lower() for m in MUTATOR_NAMES)}


def test_read_operations_work(make_config: Callable[..., SbrConfig], source_tree: Path) -> None:
    fs = SourceFS(make_config())
    names = sorted(e.name for e in fs.iter_dir("fx"))
    assert names == ["Regelungstechnik", "empty"]
    sub = {e.name: e for e in fs.iter_dir("fx", "Regelungstechnik")}
    assert sub["skript.pdf"].is_file and sub["skript.pdf"].size == len(b"%PDF-1.7\nsynthetic\n")
    assert sub["Übung"].is_dir and sub["Übung"].relpath == "Regelungstechnik\\Übung"
    assert fs.read_bytes("fx", "Regelungstechnik/Übung/blatt 1.txt").decode("utf-8").startswith("Aufgabe 1")
    st = fs.stat("fx", "Regelungstechnik\\skript.pdf")
    assert st.is_file and not st.is_dir and st.mtime_ns > 0


def test_opened_file_refuses_writes(make_config: Callable[..., SbrConfig], source_tree: Path) -> None:
    fs = SourceFS(make_config())
    before = (source_tree / "Regelungstechnik" / "skript.pdf").read_bytes()
    with fs.open_binary("fx", "Regelungstechnik\\skript.pdf") as f:
        assert not f.writable()
        with pytest.raises(io.UnsupportedOperation):
            f.write(b"x")  # type: ignore[attr-defined]
        with pytest.raises((io.UnsupportedOperation, OSError)):
            f.truncate(0)
    assert (source_tree / "Regelungstechnik" / "skript.pdf").read_bytes() == before


@pytest.mark.parametrize(
    "relpath",
    [
        "..\\outside.txt",
        "a/../../outside.txt",
        "C:\\Windows\\win.ini",
        "\\abs",
        "/abs",
        "D:rel",
        "file.pdf:stream",
        "a\x00b",
    ],
)
def test_escapes_refused(make_config: Callable[..., SbrConfig], source_tree: Path, relpath: str) -> None:
    fs = SourceFS(make_config())
    with pytest.raises(SourceAccessError):
        fs.resolve("fx", relpath)


def test_unknown_root_refused(make_config: Callable[..., SbrConfig]) -> None:
    with pytest.raises(SourceAccessError, match="unknown source root"):
        SourceFS(make_config()).resolve("nope", "x")


def test_display_path_preserves_original(make_config: Callable[..., SbrConfig], source_tree: Path) -> None:
    fs = SourceFS(make_config())
    sp = fs.resolve("fx", "Regelungstechnik/./Übung/blatt 1.txt")
    assert sp.relpath == "Regelungstechnik\\Übung\\blatt 1.txt"
    assert sp.display_path.endswith("src_root\\Regelungstechnik\\Übung\\blatt 1.txt")
    if sys.platform == "win32":
        assert sp.os_path.startswith("\\\\?\\")


def test_split_relpath_normalizes_separators() -> None:
    assert split_relpath("a/b\\c/") == ("a", "b", "c")
    assert split_relpath("") == ()


@pytest.mark.skipif(sys.platform != "win32", reason="junctions are Windows-specific")
def test_junction_escape_refused(make_config: Callable[..., SbrConfig], source_tree: Path, tmp_path: Path) -> None:
    import _winapi

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("outside the root", encoding="utf-8")
    _winapi.CreateJunction(str(outside), str(source_tree / "link"))  # type: ignore[attr-defined]
    fs = SourceFS(make_config())
    link = next(e for e in fs.iter_dir("fx") if e.name == "link")
    assert link.is_link  # reported, not followed
    with pytest.raises(SourceAccessError, match="outside source root"):
        fs.read_bytes("fx", "link\\secret.txt")
    with pytest.raises(SourceAccessError):
        list(fs.iter_dir("fx", "link"))


@pytest.mark.skipif(sys.platform != "win32", reason="junctions are Windows-specific")
def test_junction_into_protected_refused(
    make_config: Callable[..., SbrConfig], source_tree: Path, tmp_path: Path
) -> None:
    import _winapi

    cfg = make_config()
    prot = Path(cfg.roots.protected[0])
    (prot / "dup.pdf").write_bytes(b"dup")
    # A junction inside the source root pointing into the protected quarantine must not be readable.
    _winapi.CreateJunction(str(prot), str(source_tree / "qlink"))  # type: ignore[attr-defined]
    with pytest.raises(SourceAccessError):
        SourceFS(cfg).read_bytes("fx", "qlink\\dup.pdf")


@pytest.mark.skipif(sys.platform != "win32", reason="MAX_PATH handling is Windows-specific")
def test_long_paths_supported(make_config: Callable[..., SbrConfig], source_tree: Path) -> None:
    parts = ["verzeichnis_mit_langem_namen_" + str(i).zfill(3) for i in range(12)]
    deep = "\\\\?\\" + str(source_tree) + "\\" + "\\".join(parts)
    os.makedirs(deep)
    with open(deep + "\\datei.txt", "wb") as f:
        f.write(b"tief")
    rel = "\\".join([*parts, "datei.txt"])
    assert len(str(source_tree) + rel) > 300
    assert SourceFS(make_config()).read_bytes("fx", rel) == b"tief"


def test_stat_error_recorded_not_raised(
    make_config: Callable[..., SbrConfig], source_tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fs = SourceFS(make_config())
    real_scandir = os.scandir

    class Boom:
        def __init__(self, entry: os.DirEntry[str]) -> None:
            self._e = entry
            self.name = entry.name

        def stat(self, follow_symlinks: bool = True) -> os.stat_result:
            raise PermissionError(13, "Permission denied")

    class It:
        def __init__(self, path: str) -> None:
            self._it = real_scandir(path)

        def __enter__(self) -> It:
            return self

        def __exit__(self, *a: object) -> None:
            self._it.close()

        def __iter__(self) -> It:
            return self

        def __next__(self) -> Boom:
            return Boom(next(self._it))

    monkeypatch.setattr(os, "scandir", It)
    entries = list(fs.iter_dir("fx"))
    assert entries and all(e.error and "PermissionError" in e.error for e in entries)
    assert all("src_root" not in (e.error or "") for e in entries)  # no paths in error text
