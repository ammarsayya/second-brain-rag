"""T-P9-02: durable, reconstructable, privacy-bounded execution traces."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from sbr.cli.app import app
from sbr.config import SbrConfig
from sbr.ids import hash_bytes, new_id
from sbr.obs.logging import run_id_var, shutdown_logging
from sbr.obs.trace import TRACE_PREVIEW_MAX_CHARS, TraceDB, span_scope, trace_tree
from sbr.schemas import SpanKind, SpanStatus

runner = CliRunner()


@pytest.fixture
def trace_db(tmp_path: Path) -> Iterator[TraceDB]:
    with TraceDB(tmp_path / "traces" / "traces.sqlite") as db:
        db.migrate()
        yield db


@pytest.fixture(autouse=True)
def _close_logging() -> Iterator[None]:
    yield
    shutdown_logging()


def test_trace_store_crud_and_ordered_run_query(trace_db: TraceDB) -> None:
    run_id = new_id("run")
    first = trace_db.start_span(run_id, SpanKind.NODE, "root")
    second = trace_db.start_span(run_id, SpanKind.TOOL_CALL, "lookup", parent_span_id=first.span_id)

    closed_first = trace_db.finish_span(first.span_id, SpanStatus.OK, cost_usd=0.01)
    closed_second = trace_db.finish_span(second.span_id, SpanStatus.ERROR, error_class="TimeoutError")

    assert closed_first.status is SpanStatus.OK
    assert closed_second.status is SpanStatus.ERROR
    assert closed_second.error_class == "TimeoutError"
    assert trace_db.get_span(first.span_id) == closed_first
    assert [span.span_id for span in trace_db.spans_for_run(run_id)] == [first.span_id, second.span_id]


def test_trace_of_run_is_fully_reconstructable_from_stored_spans(trace_db: TraceDB) -> None:
    run_id = new_id("run")
    with span_scope(trace_db, SpanKind.NODE, "orchestrator", run_id=run_id, inputs={"request": "safe summary"}) as root:
        root.record_decision("retrieve then answer")
        root.record_tool_call("search", {"query": "bounded"})
        with span_scope(trace_db, SpanKind.TOOL_CALL, "search") as tool:
            tool.record_raw_output({"hits": 3})
            with span_scope(
                trace_db,
                SpanKind.MODEL_CALL,
                "rank",
                prompt_version="rank-v2",
                model="provider/model-v1",
            ) as model:
                model.record_parsed_output({"selected": [0, 2]})
                model.record_cost(cost_usd=0.004, input_tokens=120, output_tokens=18)
        with (
            pytest.raises(ValueError, match="synthetic failure"),
            span_scope(trace_db, SpanKind.TOOL_CALL, "failed-fetch"),
        ):
            raise ValueError("synthetic failure with a private message")

    spans = trace_db.spans_for_run(run_id)
    assert [span.sequence for span in spans] == [0, 1, 2, 3]
    assert [span.status for span in spans] == [
        SpanStatus.OK,
        SpanStatus.OK,
        SpanStatus.OK,
        SpanStatus.ERROR,
    ]
    assert spans[1].parent_span_id == spans[0].span_id
    assert spans[2].parent_span_id == spans[1].span_id
    assert spans[3].parent_span_id == spans[0].span_id
    assert spans[3].error_class == "ValueError"
    assert all(span.ended_at is not None and span.duration_ms is not None for span in spans)
    assert all(span.duration_ms is not None and span.duration_ms >= 0 for span in spans)

    tree = trace_tree(spans)
    assert len(tree) == 1
    assert tree[0]["name"] == "orchestrator"
    assert [child["name"] for child in tree[0]["children"]] == ["search", "failed-fetch"]
    assert tree[0]["children"][0]["children"][0]["name"] == "rank"
    assert tree[0]["children"][1]["status"] == "error"
    assert tree[0]["children"][1]["error_class"] == "ValueError"


def test_trace_redacts_raw_sensitive_content_before_sqlite(trace_db: TraceDB) -> None:
    raw = "PRIVATE_CORPUS_EXCERPT:" + (" confidential-text" * 80) + " token=super-secret-token"
    run_id = new_id("run")
    with span_scope(trace_db, SpanKind.MODEL_CALL, "answer", run_id=run_id) as handle:
        handle.record_inputs(raw)
        handle.record_raw_output(raw)

    stored = trace_db.spans_for_run(run_id)[0]
    assert stored.inputs is not None
    assert stored.raw_output is not None
    assert stored.inputs.content_hash == hash_bytes(raw.encode())
    assert len(stored.inputs.preview) == TRACE_PREVIEW_MAX_CHARS
    assert stored.inputs.truncated is True
    assert raw != stored.inputs.preview

    trace_db.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    persisted = trace_db.path.read_bytes()
    assert raw.encode() not in persisted
    assert b"super-secret-token" not in persisted


def test_span_scope_closes_span_as_error_when_body_raises(trace_db: TraceDB) -> None:
    run_id = new_id("run")
    with (
        pytest.raises(RuntimeError, match="crash"),
        span_scope(trace_db, SpanKind.NODE, "fragile-node", run_id=run_id) as handle,
    ):
        handle.record_inputs("in-flight input")
        raise RuntimeError("crash message must not be stored")

    stored = trace_db.spans_for_run(run_id)[0]
    assert stored.status is SpanStatus.ERROR
    assert stored.error_class == "RuntimeError"
    assert stored.ended_at is not None
    assert stored.duration_ms is not None
    assert stored.inputs is not None
    assert "crash message" not in trace_db.path.read_text(encoding="utf-8", errors="ignore")


def test_span_scope_inherits_run_context_and_parent_context(trace_db: TraceDB) -> None:
    run_id = new_id("run")
    token = run_id_var.set(run_id)
    try:
        with span_scope(trace_db, SpanKind.NODE, "root") as root, span_scope(trace_db, SpanKind.TOOL_CALL, "child"):
            pass
    finally:
        run_id_var.reset(token)

    spans = trace_db.spans_for_run(run_id)
    assert len(spans) == 2
    assert spans[1].parent_span_id == root.span_id


@pytest.fixture
def cfg_file(make_config: Callable[..., SbrConfig], tmp_path: Path) -> tuple[SbrConfig, Path]:
    cfg = make_config()
    source = cfg.roots.sources[0].path
    path = tmp_path / "sbr.toml"
    path.write_text(
        "[roots]\n"
        f"sources = [{{ id = 'fx', path = '{source}' }}]\n"
        f"var = '{cfg.roots.var}'\n"
        f"curation = '{cfg.roots.curation}'\n"
        f"protected = ['{cfg.roots.protected[0]}']\n",
        encoding="utf-8",
    )
    return cfg, path


def test_trace_cli_renders_tree_and_unknown_run_fails_cleanly(cfg_file: tuple[SbrConfig, Path]) -> None:
    cfg, config_path = cfg_file
    run_id = new_id("run")
    with TraceDB.open(cfg) as db:
        db.migrate()
        with span_scope(db, SpanKind.NODE, "root", run_id=run_id), span_scope(db, SpanKind.TOOL_CALL, "child"):
            pass

    result = runner.invoke(app, ["trace", run_id, "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    payload: dict[str, Any] = json.loads(result.output)
    assert payload["run_id"] == run_id
    assert payload["span_count"] == 2
    assert payload["spans"][0]["name"] == "root"
    assert payload["spans"][0]["children"][0]["name"] == "child"

    unknown = new_id("run")
    missing = runner.invoke(app, ["trace", unknown, "--config", str(config_path)])
    assert missing.exit_code == 1
    assert f"no trace spans found for run {unknown}" in missing.output
    assert "Traceback" not in missing.output
