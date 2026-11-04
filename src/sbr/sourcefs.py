"""SourceFS: the only module allowed to touch source roots (T-P1-03, HC-01, HC-03, ADR-002, docs/22 §1).

SourceFS exposes read-only operations only: ``stat``, ``iter_dir``, ``open_binary`` and ``read_bytes``. It has no
write, rename, delete, chmod or create operation, and a static test (TS-SAFE-2) keeps it that way.

Path handling (Windows first):

* Callers address files as ``(root_id, relpath)``. ``relpath`` accepts ``\\`` or ``/`` separators. Components ``..``,
  drive letters, absolute paths, NUL and ``:`` (alternate data streams) are refused.
* OS calls use extended-length paths (``\\\\?\\D:\\...``). Long paths work, and names with trailing dots or spaces are
  addressed exactly as stored instead of being silently rewritten by Win32 normalization.
* The resolved real path (symlinks and junctions followed) must stay inside the root and outside every protected
  path; otherwise the access is refused. Directory listings never follow links; they report them.
* The original path string (``root.path`` + ``relpath``) is preserved for provenance (:attr:`SourcePath.display_path`).

Path representation (cross-platform):

* The canonical, persisted ``relpath`` always joins components with ``\\`` on every OS. It is an identifier, not a
  native path, and its format is unchanged so registry data written on Windows stays valid on macOS and Linux.
* Native paths (``display_path``, ``os_path``) are built with the host's separator: ``ntpath`` on Windows,
  ``posixpath`` elsewhere. On POSIX a directory entry whose name contains a literal ``\\`` cannot be represented in a
  canonical relpath without ambiguity, so :meth:`SourceFS.iter_dir` reports it as an error entry instead of guessing.
"""

from __future__ import annotations

import io
import ntpath
import os
import posixpath
import stat as stat_mod
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from typing import BinaryIO

from sbr.config import SbrConfig, is_within, path_key

_IS_WINDOWS = sys.platform == "win32"
_READ_FLAGS = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0) | getattr(os, "O_CLOEXEC", 0)


class SourceAccessError(PermissionError):
    """Raised when a requested source access is refused (containment, traversal, protected path, unknown root)."""


@dataclass(frozen=True, slots=True)
class SourcePath:
    """A validated location inside a source root."""

    root_id: str
    relpath: str  # original components joined with "\\" ("" = the root itself)
    display_path: str  # original, human-facing path (provenance)
    os_path: str  # path handed to the OS (extended-length on Windows)


@dataclass(frozen=True, slots=True)
class SourceStat:
    size: int
    mtime_ns: int
    is_dir: bool
    is_file: bool
    is_link: bool  # symlink or junction / reparse point


@dataclass(frozen=True, slots=True)
class SourceEntry:
    """One directory entry, as reported without following links."""

    relpath: str
    name: str
    is_dir: bool
    is_file: bool
    is_link: bool
    size: int | None
    mtime_ns: int | None
    error: str | None = None  # stat failure recorded rather than raised


def _extended(path: str) -> str:
    """Return the extended-length form of an absolute Windows path (idempotent)."""
    if not _IS_WINDOWS:
        return path
    if path.startswith("\\\\?\\"):
        return path
    p = ntpath.normpath(path.replace("/", "\\"))
    if p.startswith("\\\\"):
        return "\\\\?\\UNC\\" + p[2:]
    return "\\\\?\\" + p


def _native_join(root: str, parts: tuple[str, ...]) -> str:
    """Join validated relpath components onto a root using the host OS separator."""
    if _IS_WINDOWS:
        root_clean = root.rstrip("\\/") if not root.endswith(":\\") else root
        return ntpath.join(root_clean, *parts) if parts else root_clean
    root_clean = root.rstrip("/") or "/"
    return posixpath.join(root_clean, *parts) if parts else root_clean


def split_relpath(relpath: str) -> tuple[str, ...]:
    """Validate and split a root-relative path into components. Raises :class:`SourceAccessError`."""
    if "\x00" in relpath:
        raise SourceAccessError("relpath contains NUL")
    unified = relpath.replace("/", "\\")
    drive, _ = ntpath.splitdrive(unified)
    if drive or unified.startswith("\\"):
        raise SourceAccessError(f"relpath must be relative to its root, got {relpath!r}")
    parts = tuple(p for p in unified.split("\\") if p not in ("", "."))
    for part in parts:
        if part == "..":
            raise SourceAccessError(f"relpath may not contain '..': {relpath!r}")
        if ":" in part:
            raise SourceAccessError(f"relpath component may not contain ':' (drive or alternate data stream): {part!r}")
    return parts


class SourceFS:
    """Read-only access to the configured source roots."""

    def __init__(self, config: SbrConfig) -> None:
        self._roots: dict[str, str] = {s.id: s.path for s in config.roots.sources}
        self._protected: tuple[str, ...] = tuple(config.roots.protected)

    @property
    def root_ids(self) -> tuple[str, ...]:
        return tuple(self._roots)

    def root_path(self, root_id: str) -> str:
        try:
            return self._roots[root_id]
        except KeyError:
            raise SourceAccessError(f"unknown source root {root_id!r}") from None

    def is_under_source(self, path: str | os.PathLike[str]) -> bool:
        """True if ``path`` lies inside any source root or protected path (lexical check)."""
        return any(is_within(path, r) for r in (*self._roots.values(), *self._protected))

    # -- resolution -------------------------------------------------------------------------------------------------

    def resolve(self, root_id: str, relpath: str = "") -> SourcePath:
        """Validate ``relpath`` and return its :class:`SourcePath`. Does not touch the filesystem."""
        root = self.root_path(root_id)
        parts = split_relpath(relpath)
        display = _native_join(root, parts)
        for prot in self._protected:
            if is_within(display, prot):
                raise SourceAccessError("path lies inside a protected path")
        return SourcePath(root_id=root_id, relpath="\\".join(parts), display_path=display, os_path=_extended(display))

    def _check_real(self, sp: SourcePath) -> None:
        """Refuse access if links resolve outside the root or into a protected path."""
        real = os.path.realpath(sp.os_path)
        root_real = os.path.realpath(_extended(self._roots[sp.root_id]))
        if not is_within(real, root_real):
            raise SourceAccessError(f"{sp.relpath!r} resolves outside source root {sp.root_id!r}")
        for prot in self._protected:
            if is_within(real, prot):
                raise SourceAccessError(f"{sp.relpath!r} resolves into a protected path")

    # -- read-only operations ---------------------------------------------------------------------------------------

    def stat(self, root_id: str, relpath: str = "") -> SourceStat:
        """Stat without following a final link."""
        sp = self.resolve(root_id, relpath)
        st = os.lstat(sp.os_path)
        return _to_stat(st)

    def iter_dir(self, root_id: str, relpath: str = "") -> Iterator[SourceEntry]:
        """List a directory without following links. Per-entry stat errors are recorded, not raised."""
        sp = self.resolve(root_id, relpath)
        self._check_real(sp)
        with os.scandir(sp.os_path) as it:
            for entry in it:
                child = f"{sp.relpath}\\{entry.name}" if sp.relpath else entry.name
                if not _IS_WINDOWS and "\\" in entry.name:
                    yield SourceEntry(
                        child, entry.name, False, False, False, None, None, error="UnrepresentableName: backslash"
                    )
                    continue
                try:
                    st = entry.stat(follow_symlinks=False)
                    is_link = entry.is_symlink() or entry.is_junction() or _is_reparse(st)
                    yield SourceEntry(
                        relpath=child,
                        name=entry.name,
                        is_dir=entry.is_dir(follow_symlinks=False),
                        is_file=entry.is_file(follow_symlinks=False),
                        is_link=is_link,
                        size=st.st_size,
                        mtime_ns=st.st_mtime_ns,
                    )
                except OSError as exc:
                    yield SourceEntry(child, entry.name, False, False, False, None, None, error=_err(exc))

    def open_binary(self, root_id: str, relpath: str) -> BinaryIO:
        """Open a source file for binary reading. The returned object refuses every write."""
        sp = self.resolve(root_id, relpath)
        self._check_real(sp)
        fd = os.open(sp.os_path, _READ_FLAGS)
        try:
            raw = io.FileIO(fd, mode="rb", closefd=True)
        except BaseException:
            os.close(fd)
            raise
        return io.BufferedReader(raw)

    def read_bytes(self, root_id: str, relpath: str) -> bytes:
        with self.open_binary(root_id, relpath) as f:
            return f.read()


def _is_reparse(st: os.stat_result) -> bool:
    attrs = getattr(st, "st_file_attributes", 0)
    return bool(attrs & getattr(stat_mod, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)) if attrs else False


def _to_stat(st: os.stat_result) -> SourceStat:
    return SourceStat(
        size=st.st_size,
        mtime_ns=st.st_mtime_ns,
        is_dir=stat_mod.S_ISDIR(st.st_mode),
        is_file=stat_mod.S_ISREG(st.st_mode),
        is_link=stat_mod.S_ISLNK(st.st_mode) or _is_reparse(st),
    )


def _err(exc: OSError) -> str:
    """Error class without the path (paths are sensitive in logs)."""
    return f"{type(exc).__name__}: errno={exc.errno} winerror={getattr(exc, 'winerror', None)}"


__all__ = [
    "SourceAccessError",
    "SourceEntry",
    "SourceFS",
    "SourcePath",
    "SourceStat",
    "path_key",
    "split_relpath",
]
