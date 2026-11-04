"""Shared fixtures. Tests never touch the real corpus: every source root here is a temporary synthetic tree."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from sbr.config import SbrConfig, config_from_mapping


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """``pdflatex``-marked tests need a TeX install. Without one they are reported as skipped with the reason, never
    silently passed; ``SBR_REQUIRE_PDFLATEX=1`` makes them run (and fail) anyway, for CI or a TeX-equipped host."""
    if shutil.which("pdflatex") is not None or os.environ.get("SBR_REQUIRE_PDFLATEX") == "1":
        return
    skip = pytest.mark.skip(reason="pdflatex not on PATH (install TeX Live/MacTeX/MiKTeX, or SBR_REQUIRE_PDFLATEX=1)")
    for item in items:
        if "pdflatex" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def make_config(tmp_path: Path) -> Callable[..., SbrConfig]:
    """Build a config whose roots all live under ``tmp_path``."""

    def _make(**roots_over: Any) -> SbrConfig:
        src = tmp_path / "src_root"
        prot = tmp_path / "quarantine"
        src.mkdir(exist_ok=True)
        prot.mkdir(exist_ok=True)
        roots: dict[str, Any] = {
            "sources": [{"id": "fx", "path": str(src)}],
            "var": str(tmp_path / "var"),
            "curation": str(tmp_path / "curation"),
            "protected": [str(prot)],
        }
        roots.update(roots_over)
        return config_from_mapping({"roots": roots})

    return _make


@pytest.fixture
def source_tree(tmp_path: Path) -> Path:
    """A small synthetic source tree with umlauts, nesting and a trailing-space-free layout."""
    root = tmp_path / "src_root"
    (root / "Regelungstechnik" / "Übung").mkdir(parents=True)
    (root / "Regelungstechnik" / "skript.pdf").write_bytes(b"%PDF-1.7\nsynthetic\n")
    (root / "Regelungstechnik" / "Übung" / "blatt 1.txt").write_text("Aufgabe 1: ẋ = Ax + Bu\n", encoding="utf-8")
    (root / "empty").mkdir()
    return root
