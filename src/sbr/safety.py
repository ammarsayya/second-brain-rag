"""Runtime source-protection guard (T-P1-03, TS-SAFE-1/3, docs/22 §1).

:class:`SourceWriteGuard` patches the process's filesystem mutators for the duration of a ``with`` block. Every
mutating call whose target lies inside a protected root (all source roots plus configured protected paths) is
recorded and refused with :class:`SourceWriteError`. Calls elsewhere pass through unchanged, so tests and stages can
still write into ``var/`` or temporary directories.

:func:`assert_writable` is the check that every sbr writer (artifact store, DB, logs, vault writer) calls before it
creates or changes a file.
"""

from __future__ import annotations

import builtins
import io
import os
import shutil
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any

from sbr.config import SbrConfig, is_within


class SourceWriteError(PermissionError):
    """A mutating filesystem operation targeted a source root or protected path."""


def protected_roots(config: SbrConfig) -> tuple[str, ...]:
    return (*(s.path for s in config.roots.sources), *config.roots.protected)


def assert_outside(path: str | os.PathLike[str], roots: Iterable[str]) -> None:
    """Raise :class:`SourceWriteError` if ``path`` lies inside any of ``roots``."""
    for root in roots:
        if is_within(os.path.abspath(path), root):  # noqa: PTH100 - lexical, see _targets_protected
            raise SourceWriteError("refusing to write inside a read-only source or protected root")


def assert_writable(path: str | os.PathLike[str], config: SbrConfig) -> None:
    """Raise :class:`SourceWriteError` if ``path`` lies inside a source root or a protected path."""
    assert_outside(path, protected_roots(config))


_WRITE_FLAGS = (
    os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC | getattr(os, "O_TEMPORARY", 0) | os.O_EXCL
)

# (module, attribute, indices of path arguments)
_PATH_MUTATORS: tuple[tuple[Any, str, tuple[int, ...]], ...] = (
    (os, "remove", (0,)),
    (os, "unlink", (0,)),
    (os, "rmdir", (0,)),
    (os, "removedirs", (0,)),
    (os, "mkdir", (0,)),
    (os, "makedirs", (0,)),
    (os, "rename", (0, 1)),
    (os, "renames", (0, 1)),
    (os, "replace", (0, 1)),
    (os, "chmod", (0,)),
    (os, "utime", (0,)),
    (os, "truncate", (0,)),
    (os, "link", (0, 1)),
    (os, "symlink", (0, 1)),
    (shutil, "move", (0, 1)),
    (shutil, "rmtree", (0,)),
    (shutil, "copy", (1,)),
    (shutil, "copy2", (1,)),
    (shutil, "copyfile", (1,)),
    (shutil, "copytree", (1,)),
    (shutil, "copymode", (1,)),
    (shutil, "copystat", (1,)),
)
for _opt in ("chown", "lchmod", "lchown"):
    if hasattr(os, _opt):
        _PATH_MUTATORS = (*_PATH_MUTATORS, (os, _opt, (0,)))


def _is_write_mode(mode: str) -> bool:
    return any(c in mode for c in "wax+")


@dataclass
class SourceWriteGuard:
    """Context manager that refuses and records mutations under protected roots."""

    roots: Iterable[str]
    violations: list[str] = field(default_factory=list)
    _root_list: tuple[str, ...] = field(default=(), repr=False)
    _saved: list[tuple[Any, str, Any]] = field(default_factory=list, repr=False)

    @classmethod
    def for_config(cls, config: SbrConfig) -> SourceWriteGuard:
        return cls(roots=protected_roots(config))

    def _targets_protected(self, value: Any) -> bool:
        if isinstance(value, int) or value is None:
            return False  # file descriptors are checked where they are opened
        try:
            p = os.fsdecode(os.fspath(value))
        except TypeError:
            return False
        # Lexical absolutization on purpose: resolving links here could hide the literal target.
        return any(is_within(os.path.abspath(p), r) for r in self._root_list)  # noqa: PTH100

    def _refuse(self, op: str) -> None:
        self.violations.append(op)
        raise SourceWriteError(f"blocked {op} under a read-only source or protected root")

    def _wrap_path_fn(self, name: str, fn: Callable[..., Any], idx: tuple[int, ...]) -> Callable[..., Any]:
        def guarded(*args: Any, **kwargs: Any) -> Any:
            candidates = [args[i] for i in idx if i < len(args)]
            candidates += [kwargs[k] for k in ("path", "src", "dst", "name", "dir_fd_path") if k in kwargs]
            if any(self._targets_protected(c) for c in candidates):
                self._refuse(name)
            return fn(*args, **kwargs)

        return guarded

    def _wrap_open(self, name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
        def guarded(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
            if _is_write_mode(kwargs.get("mode", mode)) and self._targets_protected(file):
                self._refuse(f"{name}(mode={mode!r})")
            return fn(file, mode, *args, **kwargs)

        return guarded

    def _wrap_os_open(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        def guarded(path: Any, flags: int, *args: Any, **kwargs: Any) -> Any:
            if flags & _WRITE_FLAGS and self._targets_protected(path):
                self._refuse("os.open(write flags)")
            return fn(path, flags, *args, **kwargs)

        return guarded

    def __enter__(self) -> SourceWriteGuard:
        self._root_list = tuple(self.roots)
        patches: list[tuple[Any, str, Any]] = []
        for mod, attr, idx in _PATH_MUTATORS:
            patches.append((mod, attr, self._wrap_path_fn(f"{mod.__name__}.{attr}", getattr(mod, attr), idx)))
        patches.append((builtins, "open", self._wrap_open("open", builtins.open)))
        patches.append((io, "open", self._wrap_open("io.open", io.open)))
        patches.append((os, "open", self._wrap_os_open(os.open)))
        for mod, attr, new in patches:
            self._saved.append((mod, attr, getattr(mod, attr)))
            setattr(mod, attr, new)
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        while self._saved:
            mod, attr, original = self._saved.pop()
            setattr(mod, attr, original)
