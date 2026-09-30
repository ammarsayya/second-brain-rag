"""T-P1-11: sbr status/runs/doctor/config show against a freshly migrated, empty database; consistent exit codes."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from sbr.cli.app import app
from sbr.config import SbrConfig
from sbr.obs.logging import shutdown_logging

runner = CliRunner()


@pytest.fixture(autouse=True)
def _close_logging() -> Iterator[None]:
    yield
    shutdown_logging()


@pytest.fixture
def cfg_file(make_config: Callable[..., SbrConfig], tmp_path: Path) -> Path:
    cfg = make_config()
    src = cfg.roots.sources[0].path
    text = (
        "[roots]\n"
        f"sources = [{{ id = 'fx', path = '{src}' }}]\n"
        f"var = '{cfg.roots.var}'\n"
        f"curation = '{cfg.roots.curation}'\n"
        f"protected = ['{cfg.roots.protected[0]}']\n"
    )
    p = tmp_path / "sbr.toml"
    p.write_text(text, encoding="utf-8")
    return p


def invoke(cfg_file: Path, *args: str) -> tuple[int, dict[str, Any]]:
    result = runner.invoke(app, [*args, "--config", str(cfg_file)])
    assert result.exit_code == 0, result.output
    payload: dict[str, Any] = json.loads(result.output)
    return result.exit_code, payload


def test_status_works_against_an_empty_database(cfg_file: Path) -> None:
    _, payload = invoke(cfg_file, "status")
    assert payload["schema_version"] > 0
    counts = payload["counts"]
    assert counts["blobs"] == 0
    assert counts["scans"] == 0
    assert counts["work_items"] == {s: 0 for s in ("pending", "leased", "done", "failed", "skipped", "stale")}


def test_runs_works_against_an_empty_database_then_shows_prior_runs(cfg_file: Path) -> None:
    """The very first invocation of ``runs`` against an empty ledger sees only its own (still-running) row."""
    _, payload = invoke(cfg_file, "runs")
    assert len(payload["runs"]) == 1  # its own row, queried before it finished
    assert payload["runs"][0]["status"] == "running"

    _, payload = invoke(cfg_file, "runs")
    rows = payload["runs"]
    assert len(rows) == 2  # the previous "runs" invocation's now-finished row, plus its own (newest first)
    assert rows[0]["status"] == "running"  # this invocation, queried before it finished
    assert rows[1]["command"] == "runs"
    assert rows[1]["status"] == "succeeded"
    assert rows[1]["exit_code"] == 0


def test_runs_limit_is_respected(cfg_file: Path) -> None:
    invoke(cfg_file, "status")
    invoke(cfg_file, "status")
    invoke(cfg_file, "status")
    _, payload = invoke(cfg_file, "runs", "--limit", "2")
    assert len(payload["runs"]) == 2


def test_runs_rejects_a_non_positive_limit(cfg_file: Path) -> None:
    result = runner.invoke(app, ["runs", "--limit", "0", "--config", str(cfg_file)])
    assert result.exit_code != 0


def test_doctor_reports_ok_with_the_configured_source_roots(cfg_file: Path) -> None:
    _, payload = invoke(cfg_file, "doctor")
    assert payload["status"] == "ok"
    assert payload["source_roots"] == ["fx"]


def test_config_show_prints_the_effective_validated_configuration(cfg_file: Path) -> None:
    _, payload = invoke(cfg_file, "config", "show")
    roots = payload["roots"]
    assert [s["id"] for s in roots["sources"]] == ["fx"]
    assert payload["governor"]["max_workers"] == 6  # the built-in default, since none was set


def test_a_missing_config_file_fails_cleanly_with_exit_code_one(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.toml"
    result = runner.invoke(app, ["status", "--config", str(missing)])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_help_and_version_stay_stateless(cfg_file: Path, make_config: Callable[..., SbrConfig]) -> None:
    """--help and version never touch the database, even when one is configured."""
    assert runner.invoke(app, ["--help"]).exit_code == 0
    assert runner.invoke(app, ["version"]).exit_code == 0
    assert not (make_config().db_dir / "registry.sqlite").exists()
