"""TS-SAFE-1/TS-SAFE-3: the runtime guard blocks every mutator under source/protected roots; bytes stay identical.

TS-SAFE-3 in full (a whole pipeline run on fixtures) is extended as pipeline stages arrive (P2+); ``tree_digest`` and
``SourceWriteGuard`` are its harness.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from sbr.config import SbrConfig
from sbr.db.registry import RegistryDB
from sbr.registry.scan import scan_root
from sbr.safety import SourceWriteError, SourceWriteGuard, assert_writable
from sbr.sourcefs import SourceFS


def tree_digest(root: Path) -> dict[str, tuple[int, int, str]]:
    out: dict[str, tuple[int, int, str]] = {}
    for p in sorted(root.rglob("*")):
        st = p.lstat()
        digest = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "dir"
        out[p.relative_to(root).as_posix()] = (st.st_size if p.is_file() else 0, st.st_mtime_ns, digest)
    return out


def attempts(src: Path, prot: Path) -> list[tuple[str, Callable[[], object]]]:
    f = src / "Regelungstechnik" / "skript.pdf"
    q = prot / "q.bin"
    return [
        ("os.remove", lambda: os.remove(f)),
        ("os.unlink", lambda: os.unlink(f)),
        ("os.rename", lambda: os.rename(f, src / "moved.pdf")),
        ("os.replace", lambda: os.replace(f, src / "moved.pdf")),
        ("rename out", lambda: os.rename(f, src.parent / "stolen.pdf")),
        ("os.mkdir", lambda: os.mkdir(src / "newdir")),
        ("os.makedirs", lambda: os.makedirs(src / "a" / "b")),
        ("os.rmdir", lambda: os.rmdir(src / "empty")),
        ("os.chmod", lambda: os.chmod(f, 0o444)),
        ("os.utime", lambda: os.utime(f, (0, 0))),
        ("os.truncate", lambda: os.truncate(f, 0)),
        ("open w", lambda: open(f, "w")),
        ("open ab", lambda: open(f, "ab")),
        ("open r+", lambda: open(f, "r+b")),
        ("os.open", lambda: os.open(f, os.O_WRONLY)),
        ("Path.write_text", lambda: f.write_text("x")),
        ("Path.write_bytes", lambda: f.write_bytes(b"x")),
        ("Path.touch", lambda: (src / "new.txt").touch()),
        ("Path.unlink", lambda: f.unlink()),
        ("Path.rename", lambda: f.rename(src / "r.pdf")),
        ("Path.mkdir", lambda: (src / "m").mkdir()),
        ("shutil.move", lambda: shutil.move(f, src / "mv.pdf")),
        ("shutil.rmtree", lambda: shutil.rmtree(src / "Regelungstechnik")),
        ("shutil.copy into source", lambda: shutil.copy(__file__, src / "x.py")),
        ("write protected", lambda: q.write_bytes(b"x")),
        ("delete protected", lambda: shutil.rmtree(prot)),
    ]


def test_guard_blocks_all_mutators(make_config: Callable[..., SbrConfig], source_tree: Path) -> None:
    cfg = make_config()
    prot = Path(cfg.roots.protected[0])
    (prot / "q.bin").write_bytes(b"q")
    before, before_q = tree_digest(source_tree), tree_digest(prot)
    guard = SourceWriteGuard.for_config(cfg)
    ops = attempts(source_tree, prot)
    with guard:
        for name, op in ops:
            with pytest.raises(SourceWriteError):
                op()
            assert guard.violations, name
    assert len(guard.violations) >= len(ops)  # nested calls may record more than one
    assert tree_digest(source_tree) == before
    assert tree_digest(prot) == before_q


def test_guard_allows_reads_and_writes_elsewhere(
    make_config: Callable[..., SbrConfig], source_tree: Path, tmp_path: Path
) -> None:
    cfg = make_config()
    before = tree_digest(source_tree)
    fs = SourceFS(cfg)
    var = Path(cfg.roots.var)
    with SourceWriteGuard.for_config(cfg) as guard:
        data = fs.read_bytes("fx", "Regelungstechnik\\skript.pdf")
        with open(source_tree / "Regelungstechnik" / "skript.pdf", "rb") as fh:
            assert fh.read() == data
        var.mkdir(parents=True)
        (var / "artifact.bin").write_bytes(data)
        os.replace(var / "artifact.bin", var / "artifact2.bin")
        shutil.rmtree(var)
    assert guard.violations == []
    assert tree_digest(source_tree) == before


def test_guard_restores_originals(make_config: Callable[..., SbrConfig]) -> None:
    orig = (os.remove, os.open, shutil.move, open)
    with SourceWriteGuard.for_config(make_config()):
        assert os.remove is not orig[0]
    assert (os.remove, os.open, shutil.move, open) == orig


def test_guard_is_restored_after_error(make_config: Callable[..., SbrConfig]) -> None:
    original = os.rename
    with pytest.raises(RuntimeError), SourceWriteGuard.for_config(make_config()):
        raise RuntimeError("boom")
    assert os.rename is original


def test_assert_writable(make_config: Callable[..., SbrConfig], source_tree: Path) -> None:
    cfg = make_config()
    assert_writable(Path(cfg.roots.var) / "db" / "registry.sqlite", cfg)
    with pytest.raises(SourceWriteError):
        assert_writable(source_tree / "x", cfg)
    with pytest.raises(SourceWriteError):
        assert_writable(Path(cfg.roots.protected[0]) / "x", cfg)
    with pytest.raises(SourceWriteError):
        assert_writable(str(source_tree).upper().replace("\\", "/"), cfg)


def test_full_scan_makes_zero_source_mutations(make_config: Callable[..., SbrConfig], source_tree: Path) -> None:
    """TS-SAFE-3 for S1: run the real scanner while every source mutator is guarded."""
    cfg = make_config()
    before = tree_digest(source_tree)
    with RegistryDB.open(cfg) as db:
        db.migrate()
        with SourceWriteGuard.for_config(cfg) as guard:
            record = scan_root(cfg, db, "fx")
    assert record.files_seen == sum(1 for path in source_tree.rglob("*") if path.is_file())
    assert guard.violations == []
    assert tree_digest(source_tree) == before
