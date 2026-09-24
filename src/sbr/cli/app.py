"""Typer application for the ``sbr`` command (T-P1-01; ``status``/``runs``/``doctor``/``config show`` from T-P1-11).

Every data-bearing command prints one JSON object to stdout and exits 0 on success. A configuration problem prints
one line to stderr and exits 1 — no traceback, since :class:`~sbr.config.ConfigError` already lists every problem.
``--help`` and ``version`` stay stateless (no config load, no database, no run row); every other command opens the
registry and records exactly one run (T-P1-08's :func:`~sbr.cli.runtime.command_runtime`), so they all behave the
same way against a freshly migrated, empty database.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn

import typer

from sbr import __version__
from sbr.cli.runtime import Runtime, command_runtime
from sbr.config import ConfigError
from sbr.db import registry as reg
from sbr.registry.hash import DEFAULT_BATCH_SIZE, hash_pending
from sbr.registry.scan import scan_sources
from sbr.schemas import WorkItemState

app = typer.Typer(
    name="sbr",
    help="Second Brain RAG: provenance-tracked knowledge system over read-only source corpora.",
    no_args_is_help=True,
    add_completion=False,
)
config_app = typer.Typer(help="Configuration commands.")
app.add_typer(config_app, name="config")

ConfigOption = typer.Option(
    None, "--config", help="Path to the TOML config file (default: $SBR_CONFIG or config/sbr.toml)."
)


@app.callback()
def root() -> None:
    """Second Brain RAG command group."""


@app.command("version")
def version_cmd() -> None:
    """Print the sbr version."""
    typer.echo(__version__)


def _fail(exc: ConfigError) -> NoReturn:
    typer.echo(str(exc), err=True)
    raise typer.Exit(code=1)


def _print(payload: dict[str, object]) -> None:
    typer.echo(json.dumps(payload, indent=2, sort_keys=True, default=str))


def _run(command: str, config: Path | None, body: Callable[[Runtime], dict[str, object]]) -> None:
    """Open the runtime for one stateful command, print ``body``'s JSON result, and translate config errors."""
    try:
        with command_runtime(command, config) as rt:
            _print(body(rt))
    except ConfigError as exc:
        _fail(exc)


@app.command("status")
def status_cmd(config: Path | None = ConfigOption) -> None:
    """Registry schema version and record counts (works against a freshly migrated, empty database)."""

    def body(rt: Runtime) -> dict[str, object]:
        return {
            "schema_version": rt.db.schema_version,
            "config_hash": rt.config.config_hash(),
            "counts": {
                "activities": rt.db.repo(reg.ACTIVITY).count(),
                "source_roots": rt.db.repo(reg.SOURCE_ROOT).count(),
                "scans": rt.db.repo(reg.SCAN).count(),
                "blobs": rt.db.repo(reg.BLOB).count(),
                "path_observations": rt.db.repo(reg.PATH_OBSERVATION).count(),
                "work_items": {s.value: rt.db.repo(reg.WORK_ITEM).count({"state": s.value}) for s in WorkItemState},
            },
        }

    _run("status", config, body)


@app.command("runs")
def runs_cmd(
    limit: int = typer.Option(20, "--limit", help="Maximum number of runs to show."),
    config: Path | None = ConfigOption,
) -> None:
    """List the most recent run-ledger entries, newest first (works against a freshly migrated, empty database)."""
    if limit < 1:
        raise typer.BadParameter("--limit must be at least 1")

    def body(rt: Runtime) -> dict[str, object]:
        return {
            "runs": [
                {
                    "run_id": r.run_id,
                    "command": r.command,
                    "status": r.status.value,
                    "started_at": r.started_at.isoformat(),
                    "ended_at": r.ended_at.isoformat() if r.ended_at is not None else None,
                    "exit_code": r.exit_code,
                }
                for r in rt.ledger.recent(limit)
            ]
        }

    _run("runs", config, body)


@app.command("doctor")
def doctor_cmd(config: Path | None = ConfigOption) -> None:
    """Basic health check: the config loads and the database migrates to head. Deeper checks land with later tasks."""

    def body(rt: Runtime) -> dict[str, object]:
        return {
            "status": "ok",
            "schema_version": rt.db.schema_version,
            "source_roots": [s.id for s in rt.config.roots.sources],
        }

    _run("doctor", config, body)


@app.command("scan")
def scan_cmd(
    root_id: str | None = typer.Option(None, "--root", help="Scan only this configured source-root id."),
    config: Path | None = ConfigOption,
) -> None:
    """Observe source paths read-only and enqueue hashing for new or changed files."""

    def body(rt: Runtime) -> dict[str, object]:
        if root_id is not None:
            try:
                rt.config.source_root(root_id)
            except KeyError:
                raise typer.BadParameter(f"unknown source root id {root_id!r}", param_hint="--root") from None
        records = scan_sources(rt.config, rt.db, root_ids=None if root_id is None else (root_id,))
        return {
            "scans": [
                {
                    "scan_id": record.scan_id,
                    "root_id": record.root_id,
                    "status": record.status.value,
                    "files_seen": record.files_seen,
                    "bytes_seen": record.bytes_seen,
                    "errors": record.errors,
                }
                for record in records
            ]
        }

    _run("scan", config, body)


@app.command("hash")
def hash_cmd(
    batch_size: int = typer.Option(DEFAULT_BATCH_SIZE, "--batch-size", help="Hash-job leases per batch."),
    config: Path | None = ConfigOption,
) -> None:
    """Hash all currently-ready S2 work through read-only SourceFS streams."""
    if batch_size < 1:
        raise typer.BadParameter("--batch-size must be at least 1")

    def body(rt: Runtime) -> dict[str, object]:
        result = hash_pending(rt.config, rt.db, batch_size=batch_size)
        return {
            "activity_id": result.activity_id,
            "leased": result.leased,
            "hashed": result.hashed,
            "bytes_hashed": result.bytes_hashed,
            "failed": result.failed,
            "elapsed_seconds": round(result.elapsed_seconds, 6),
        }

    _run("hash", config, body)


@config_app.command("show")
def config_show_cmd(config: Path | None = ConfigOption) -> None:
    """Print the effective, validated configuration as JSON."""
    _run("config show", config, lambda rt: dict(rt.config.model_dump(mode="json")))


def main() -> None:
    """Console-script entry point."""
    app()
