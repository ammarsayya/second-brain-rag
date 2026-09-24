"""T-P1-08: every stateful CLI invocation creates a run row; logs are valid JSONL, correlated and redacted."""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from sbr.cli.runtime import command_runtime
from sbr.config import SbrConfig, load_config
from sbr.db.registry import RegistryDB
from sbr.obs.logging import LOG_FILE, Redactor, configure_logging, get_logger, shutdown_logging
from sbr.obs.runs import RunLedger, git_sha, run_scope
from sbr.provenance import ProvenanceStore
from sbr.schemas import RunStatus


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
        "[logging]\nlevel = 'DEBUG'\n"
    )
    p = tmp_path / "sbr.toml"
    p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture(autouse=True)
def _close_logging() -> Iterator[None]:
    yield
    shutdown_logging()


def make_app(cfg_file: Path) -> typer.Typer:
    app = typer.Typer()

    @app.callback()
    def root() -> None:
        """test app"""

    @app.command("ok")
    def ok() -> None:
        with command_runtime("test ok", cfg_file) as rt:
            rt.run.count("items", 3)
            get_logger("test").info("processing", extra={"sbr": {"stage": "scan", "subject_id": "b3:x"}})

    @app.command("boom")
    def boom() -> None:
        with command_runtime("test boom", cfg_file):
            raise ValueError("failure mentioning a path")

    @app.command("exit2")
    def exit2() -> None:
        with command_runtime("test exit2", cfg_file) as rt:
            rt.run.exit_code = 2
        raise typer.Exit(2)

    return app


def runs(cfg: SbrConfig) -> list[tuple[str, str, int | None, str | None]]:
    con = sqlite3.connect(cfg.db_dir / "registry.sqlite")
    try:
        return con.execute("SELECT command, status, exit_code, error_class FROM run ORDER BY started_at").fetchall()
    finally:
        con.close()


def log_lines(cfg: SbrConfig) -> list[dict[str, object]]:
    return [json.loads(line) for line in (cfg.logs_dir / LOG_FILE).read_text(encoding="utf-8").splitlines()]


def test_each_cli_invocation_records_one_run(cfg_file: Path, make_config: Callable[..., SbrConfig]) -> None:
    cfg = make_config()
    app = make_app(cfg_file)
    runner = CliRunner()
    assert runner.invoke(app, ["ok"]).exit_code == 0
    res = runner.invoke(app, ["boom"])
    assert res.exit_code == 1 and isinstance(res.exception, ValueError)
    assert runner.invoke(app, ["exit2"]).exit_code == 2
    assert runs(cfg) == [
        ("test ok", "succeeded", 0, None),
        ("test boom", "failed", 1, "ValueError"),
        ("test exit2", "failed", 2, None),
    ]
    with RegistryDB.open(cfg) as db:
        latest = RunLedger(db.conn).recent(1)[0]
        assert latest.git_sha is None or latest.git_sha == git_sha()
        assert latest.config_hash == load_config(cfg_file).config_hash()
        first = RunLedger(db.conn).recent(10)[-1]
        assert first.counts == {"items": 3}


def test_logs_are_jsonl_and_correlated(cfg_file: Path, make_config: Callable[..., SbrConfig]) -> None:
    cfg = make_config()
    CliRunner().invoke(make_app(cfg_file), ["ok"])
    lines = log_lines(cfg)
    assert lines, "log file is empty"
    run_ids = {line["run_id"] for line in lines}
    assert len(run_ids) == 1 and next(iter(run_ids)) is not None
    processing = next(line for line in lines if line["msg"] == "processing")
    assert processing["stage"] == "scan" and processing["subject_id"] == "b3:x" and processing["level"] == "INFO"
    assert {"ts", "level", "logger", "msg", "run_id"} <= set(processing)


def test_sensitive_content_is_redacted(make_config: Callable[..., SbrConfig]) -> None:
    cfg = make_config()
    src = cfg.roots.sources[0].path
    configure_logging(cfg.logs_dir, protected=(src, *cfg.roots.protected), level="DEBUG")
    log = get_logger("redaction")
    secret_path = src + "\\books\\Lebenslauf Max Mustermann.pdf"
    log.info("opening %s now", secret_path, extra={"sbr": {"relpath": "books\\Zeugnis.pdf", "text": "Note 1,0"}})

    def fail() -> None:
        raise OSError(f"cannot read {secret_path}")

    try:
        fail()
    except OSError:
        log.exception("read failed")
    shutdown_logging()
    raw = (cfg.logs_dir / LOG_FILE).read_text(encoding="utf-8")
    for leaked in ("Lebenslauf", "Mustermann", "Zeugnis", "Note 1,0"):
        assert leaked not in raw, leaked
    lines = [json.loads(x) for x in raw.splitlines()]
    assert lines[0]["msg"].startswith("opening <source-path sha256:")
    assert str(lines[0]["relpath"]).startswith("<redacted sha256:")
    assert "exc" in lines[1] and "OSError" in lines[1]["exc"]


def test_redactor_handles_separators_case_and_extended_paths() -> None:
    r = Redactor(source_roots=["D:\\MBI-BRAIN"])
    for s in ("see D:/mbi-brain/a b/c.pdf", "see \\\\?\\D:\\MBI-BRAIN\\x.pdf", "see d:\\MBI-BRAIN"):
        out = r.text(s)
        assert out.startswith("see <source-path sha256:") and "MBI" not in out.upper().replace("SHA256", "")
    assert r.text("no paths here") == "no paths here"
    assert r.value("content", {"k": 1}).startswith("<redacted")


def test_log_rotation(make_config: Callable[..., SbrConfig]) -> None:
    cfg = make_config()
    configure_logging(cfg.logs_dir, protected=cfg.roots.protected, max_bytes=2048, backup_count=3)
    log = get_logger("rot")
    for i in range(200):
        log.info("line %d %s", i, "x" * 50)
    shutdown_logging()
    files = sorted(p.name for p in cfg.logs_dir.iterdir())
    assert LOG_FILE in files and f"{LOG_FILE}.1" in files and len(files) <= 4
    for p in cfg.logs_dir.iterdir():
        for line in p.read_text(encoding="utf-8").splitlines():
            json.loads(line)


def test_run_rows_are_protected_and_activities_reference_runs(make_config: Callable[..., SbrConfig]) -> None:
    with RegistryDB.open(make_config()) as db:
        db.migrate()
        ledger = RunLedger(db.conn)
        with run_scope(ledger, "unit", config_hash=None) as h:
            act = ProvenanceStore(db.conn).start_activity("scan", "p", "1", "system:x", run_id=h.run_id)
            assert act.run_id == h.run_id
        with pytest.raises(sqlite3.IntegrityError, match="unknown run"):
            ProvenanceStore(db.conn).start_activity("scan", "p", "1", "system:x", run_id="run_" + "0" * 26)
        with pytest.raises(sqlite3.IntegrityError, match="never deleted"):
            db.conn.execute("DELETE FROM run")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            db.conn.execute("UPDATE run SET command = 'x'")
        with pytest.raises(KeyboardInterrupt), run_scope(ledger, "interrupted", config_hash=None):
            raise KeyboardInterrupt
        assert ledger.recent(1)[0].status is RunStatus.INTERRUPTED


def test_logging_refuses_protected_location(make_config: Callable[..., SbrConfig]) -> None:
    from sbr.safety import SourceWriteError

    cfg = make_config()
    with pytest.raises(SourceWriteError):
        configure_logging(Path(cfg.roots.sources[0].path) / "logs", protected=(cfg.roots.sources[0].path,))
    assert logging.getLogger("sbr").handlers == [] or all(
        not getattr(h, "_sbr_handler", False) for h in logging.getLogger("sbr").handlers
    )
