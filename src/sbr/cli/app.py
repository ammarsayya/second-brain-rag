"""Typer application for the ``sbr`` command (T-P1-01; ``status``/``runs``/``doctor``/``config show`` from T-P1-11).

Every data-bearing command prints one JSON object to stdout and exits 0 on success. A configuration problem prints
one line to stderr and exits 1 — no traceback, since :class:`~sbr.config.ConfigError` already lists every problem.
``--help`` and ``version`` stay stateless (no config load, no database, no run row); every other command opens the
registry and records exactly one run (T-P1-08's :func:`~sbr.cli.runtime.command_runtime`), so they all behave the
same way against a freshly migrated, empty database.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn

import typer

from sbr import __version__
from sbr.cli.runtime import Runtime, command_runtime
from sbr.config import ConfigError
from sbr.db import registry as reg
from sbr.registry.archives import inventory_archives
from sbr.registry.changes import detect_changes
from sbr.registry.classify import DEFAULT_RULES_PATH, classify_pending
from sbr.registry.courses import classify_courses
from sbr.registry.dedup import select_canonical_paths
from sbr.registry.genre import classify_genres
from sbr.registry.hash import DEFAULT_BATCH_SIZE, hash_pending
from sbr.registry.names import repair_names
from sbr.registry.scan import scan_sources
from sbr.registry.sensitivity import classify_sensitivity
from sbr.registry.twins import detect_twin_candidates
from sbr.reports.manifest import build_manifest, render_csv_rows, render_markdown
from sbr.safety import assert_writable
from sbr.schemas import WorkItemState

app = typer.Typer(
    name="sbr",
    help="Second Brain RAG: provenance-tracked knowledge system over read-only source corpora.",
    no_args_is_help=True,
    add_completion=False,
)
config_app = typer.Typer(help="Configuration commands.")
app.add_typer(config_app, name="config")
report_app = typer.Typer(help="Read-only reports over the registry.")
app.add_typer(report_app, name="report")

ConfigOption = typer.Option(
    None, "--config", help="Path to the TOML config file (default: $SBR_CONFIG or config/sbr.toml)."
)
ClassificationRulesOption = typer.Option(DEFAULT_RULES_PATH, "--rules", help="Classification rules TOML file.")
ExclusionsOption = typer.Option(None, "--exclusions", help="Owner exclusion-curation YAML file.")
SensitivityOverridesOption = typer.Option(None, "--overrides", help="Owner sensitivity-override YAML file.")
CanonicalPathOverridesOption = typer.Option(None, "--overrides", help="Owner canonical-path override YAML file.")
CourseMapOption = typer.Option(None, "--course-map", help="Owner course-mapping curation YAML file.")
ManifestMarkdownOption = typer.Option(Path("reports/manifest.md"), "--markdown-output")
ManifestCsvOption = typer.Option(Path("reports/manifest.csv"), "--csv-output")


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


@app.command("classify")
def classify_cmd(
    rules: Path = ClassificationRulesOption,
    config: Path | None = ConfigOption,
) -> None:
    """Classify every hashed blob that is missing a format or remains unknown."""

    def body(rt: Runtime) -> dict[str, object]:
        result = classify_pending(rt.config, rt.db, rules_path=rules)
        return {
            "activity_id": result.activity_id,
            "considered": result.considered,
            "updated": result.updated,
            "unknown_count": len(result.unknowns),
            "unknowns": [
                {
                    "blob_id": item.blob_id,
                    "root_id": item.root_id,
                    "relpath": item.relpath,
                    "extension": item.extension,
                }
                for item in result.unknowns
            ],
            "failure_count": len(result.failures),
            "failures": [{"blob_id": item.blob_id, "error": item.error} for item in result.failures],
        }

    _run("classify", config, body)


@app.command("sensitivity")
def sensitivity_cmd(
    exclusions: Path | None = ExclusionsOption,
    overrides: Path | None = SensitivityOverridesOption,
    config: Path | None = ConfigOption,
) -> None:
    """Apply metadata-only default exclusions and sensitivity rules."""

    def body(rt: Runtime) -> dict[str, object]:
        result = classify_sensitivity(
            rt.config,
            rt.db,
            exclusions_path=exclusions,
            overrides_path=overrides,
        )
        return {
            "activity_id": result.activity_id,
            "considered": result.considered,
            "updated": result.updated,
            "excluded": result.excluded,
            "sensitivity_counts": result.sensitivity_counts,
        }

    _run("sensitivity", config, body)


@app.command("changes")
def changes_cmd(
    root_id: str = typer.Option(..., "--root", help="Configured source-root id."),
    scan_id: str = typer.Option(..., "--scan-id", help="Completed scan id to classify after hashing."),
    config: Path | None = ConfigOption,
) -> None:
    """Record new, alias, modified, moved, and deleted changes for one scan."""

    def body(rt: Runtime) -> dict[str, object]:
        try:
            result = detect_changes(rt.config, rt.db, root_id, scan_id)
        except KeyError:
            raise typer.BadParameter(f"unknown source root id {root_id!r}", param_hint="--root") from None
        return {
            "activity_id": result.activity_id,
            "scan_id": scan_id,
            "root_id": root_id,
            "counts": result.counts,
            "events": [event.model_dump(mode="json") for event in result.events],
        }

    _run("changes", config, body)


@app.command("dedup")
def dedup_cmd(
    overrides: Path | None = CanonicalPathOverridesOption,
    config: Path | None = ConfigOption,
) -> None:
    """Select one canonical PRESENT path for every known blob; retain every alias."""

    def body(rt: Runtime) -> dict[str, object]:
        result = select_canonical_paths(rt.config, rt.db, overrides_path=overrides)
        return {
            "activity_id": result.activity_id,
            "considered": result.considered,
            "duplicate_groups": result.duplicate_groups,
            "singletons": result.singletons,
            "without_present_observation": result.without_present_observation,
            "updated": result.updated,
            "overrides_applied": result.overrides_applied,
        }

    _run("dedup", config, body)


@app.command("archives")
def archives_cmd(config: Path | None = ConfigOption) -> None:
    """Inventory zip/7z/tar members of every classified archive blob."""

    def body(rt: Runtime) -> dict[str, object]:
        result = inventory_archives(rt.config, rt.db)
        return {
            "activity_id": result.activity_id,
            "containers_considered": result.containers_considered,
            "containers_processed": result.containers_processed,
            "containers_unsupported": result.containers_unsupported,
            "containers_over_limit": result.containers_over_limit,
            "containers_read_failure": result.containers_read_failure,
            "members_total": result.members_total,
            "members_already_present": result.members_already_present,
            "members_extracted_new": result.members_extracted_new,
            "members_skipped_limit": result.members_skipped_limit,
            "members_excluded": result.members_excluded,
        }

    _run("archives", config, body)


@app.command("twins")
def twins_cmd(config: Path | None = ConfigOption) -> None:
    """Propose PDF<->office-document twin candidates by stem similarity and folder proximity."""

    def body(rt: Runtime) -> dict[str, object]:
        result = detect_twin_candidates(rt.config, rt.db)
        return {
            "activity_id": result.activity_id,
            "pdf_candidates_considered": result.pdf_candidates_considered,
            "office_candidates_considered": result.office_candidates_considered,
            "pairs_proposed": result.pairs_proposed,
        }

    _run("twins", config, body)


@app.command("genre")
def genre_cmd(config: Path | None = ConfigOption) -> None:
    """Classify genre from path/name tokens and propose exam/exercise-solution pairings."""

    def body(rt: Runtime) -> dict[str, object]:
        result = classify_genres(rt.config, rt.db)
        return {
            "activity_id": result.activity_id,
            "considered": result.considered,
            "classified": result.classified,
            "solution_pairs_proposed": result.solution_pairs_proposed,
        }

    _run("genre", config, body)


@app.command("courses")
def courses_cmd(
    course_map: Path | None = CourseMapOption,
    config: Path | None = ConfigOption,
) -> None:
    """Assign a curated course_id/confidence from folder tokens (curation/course_map.yaml)."""

    def body(rt: Runtime) -> dict[str, object]:
        result = classify_courses(rt.config, rt.db, course_map_path=course_map)
        return {
            "activity_id": result.activity_id,
            "considered": result.considered,
            "classified": result.classified,
            "unknown": result.unknown,
        }

    _run("courses", config, body)


@app.command("names")
def names_cmd(config: Path | None = ConfigOption) -> None:
    """Repair CP437/CP850/CP1252 mojibake in display_name; relpath is never touched."""

    def body(rt: Runtime) -> dict[str, object]:
        result = repair_names(rt.config, rt.db)
        return {
            "activity_id": result.activity_id,
            "considered": result.considered,
            "repaired": result.repaired,
        }

    _run("names", config, body)


@report_app.command("manifest")
def report_manifest_cmd(
    markdown_output: Path = ManifestMarkdownOption,
    csv_output: Path = ManifestCsvOption,
    config: Path | None = ConfigOption,
) -> None:
    """Aggregate totals/breakdowns/duplicates/archives/sensitivity/genre/course into a Markdown + CSV report."""

    def body(rt: Runtime) -> dict[str, object]:
        report = build_manifest(rt.config, rt.db)
        assert_writable(markdown_output.resolve(), rt.config)
        assert_writable(csv_output.resolve(), rt.config)
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        csv_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(render_markdown(report), encoding="utf-8")
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["section", "key", "files", "bytes"])
        writer.writerows(render_csv_rows(report))
        csv_output.write_text(buffer.getvalue(), encoding="utf-8")
        return {
            "manifest_version": report.manifest_version,
            "total_files": report.total_files,
            "total_bytes": report.total_bytes,
            "total_blobs": report.total_blobs,
            "total_unique_bytes": report.total_unique_bytes,
            "duplicate_groups": report.duplicates.duplicate_groups,
            "markdown_output": str(markdown_output),
            "csv_output": str(csv_output),
        }

    _run("report manifest", config, body)


@config_app.command("show")
def config_show_cmd(config: Path | None = ConfigOption) -> None:
    """Print the effective, validated configuration as JSON."""
    _run("config show", config, lambda rt: dict(rt.config.model_dump(mode="json")))


def main() -> None:
    """Console-script entry point."""
    app()
