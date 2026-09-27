"""Durable, privacy-bounded execution traces (T-P9-02, HC-23).

Each span is written to a standalone SQLite store below ``var/traces``. Content-bearing values are converted to a
BLAKE3 fingerprint and a credential/path-scrubbed preview capped at :data:`TRACE_PREVIEW_MAX_CHARS` before SQLite
ever sees them. The store therefore never receives raw prompts, corpus text, model output, or tool arguments.
"""

from __future__ import annotations

import contextvars
import json
import re
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Any

from sbr.config import SbrConfig
from sbr.db.connection import connect, transaction
from sbr.db.migrations import MigrationReport, Migrator
from sbr.db.repository import Repository, TableSpec
from sbr.ids import hash_bytes, new_id
from sbr.obs.logging import Redactor, run_id_var
from sbr.safety import protected_roots
from sbr.schemas import RedactedValue, Span, SpanKind, SpanStatus, TraceToolCall
from sbr.schemas.trace import TRACE_PREVIEW_MAX_CHARS

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MIGRATIONS = REPO_ROOT / "migrations" / "traces"
SPAN = TableSpec("span", Span, ("span_id",))

span_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("sbr_span_id", default=None)
span_run_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("sbr_span_run_id", default=None)

_CREDENTIAL_RE = re.compile(
    r"(?i)(?:\bbearer\s+[-A-Za-z0-9._~+/]+=*|"
    r"\b(?:api[_-]?key|access[_-]?token|token|secret|password)\b\s*[:=]\s*[^\s,;]+|"
    r"\beyJ[-A-Za-z0-9_]+\.[-A-Za-z0-9_]+\.[-A-Za-z0-9_]+)"
)
_PATH_RE = re.compile(r"(?i)(?:\b[A-Z]:[\\/]|\\\\)[^\r\n\"']+")


class TraceError(RuntimeError):
    """Base class for trace-store failures."""


class TraceNotFoundError(TraceError):
    """No stored spans exist for the requested run."""


class TraceContextError(TraceError):
    """A span was started without a run correlation context."""


class TraceRedactor:
    """Convert arbitrary values to a hash plus a bounded, scrubbed preview."""

    def __init__(self, source_roots: tuple[str, ...] = ()) -> None:
        self._paths = Redactor(source_roots=source_roots)

    @staticmethod
    def _text(value: object) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        except (TypeError, ValueError, RecursionError):
            return f"<{type(value).__name__}:unserializable>"

    def value(self, value: object) -> RedactedValue:
        raw = self._text(value)
        scrubbed = self._paths.text(raw)
        scrubbed = _CREDENTIAL_RE.sub("<credential-redacted>", scrubbed)
        scrubbed = _PATH_RE.sub("<path-redacted>", scrubbed)
        preview = scrubbed[:TRACE_PREVIEW_MAX_CHARS]
        return RedactedValue(
            content_hash=hash_bytes(raw.encode("utf-8", errors="surrogatepass")),
            preview=preview,
            char_count=len(raw),
            truncated=scrubbed != raw or len(scrubbed) > TRACE_PREVIEW_MAX_CHARS,
        )

    def label(self, value: str | None) -> str | None:
        if value is None:
            return None
        scrubbed = self._paths.text(value)
        scrubbed = _CREDENTIAL_RE.sub("<credential-redacted>", scrubbed)
        scrubbed = _PATH_RE.sub("<path-redacted>", scrubbed).strip()
        return (scrubbed or "<redacted>")[:128]


class TraceDB:
    """Standalone ``traces.sqlite`` facade. Call :meth:`migrate` before use."""

    def __init__(
        self,
        path: Path,
        *,
        protected: tuple[str, ...] = (),
        migrations_dir: Path = DEFAULT_MIGRATIONS,
        backup_dir: Path | None = None,
        source_roots: tuple[str, ...] = (),
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.path = path
        self.conn: sqlite3.Connection = connect(path, protected)
        self.migrator = Migrator(
            conn=self.conn,
            migrations_dir=migrations_dir,
            db_path=path,
            backup_dir=backup_dir or path.parent.parent / "backups" / "traces",
            protected=protected,
        )
        self.redactor = TraceRedactor((*source_roots, *protected))
        self._clock = clock

    @classmethod
    def open(cls, config: SbrConfig, *, migrations_dir: Path = DEFAULT_MIGRATIONS) -> TraceDB:
        roots = protected_roots(config)
        return cls(
            config.traces_dir / "traces.sqlite",
            protected=roots,
            migrations_dir=migrations_dir,
            backup_dir=config.var_path / "backups" / "traces",
            source_roots=tuple(source.path for source in config.roots.sources),
        )

    def migrate(self, target: int | None = None) -> MigrationReport:
        return self.migrator.migrate(target)

    @property
    def schema_version(self) -> int:
        return self.migrator.current_version()

    def _repo(self) -> Repository[Span]:
        return Repository(self.conn, SPAN)

    def start_span(
        self,
        run_id: str,
        kind: SpanKind,
        name: str,
        *,
        parent_span_id: str | None = None,
        inputs: object | None = None,
        prompt_version: str | None = None,
        model: str | None = None,
    ) -> Span:
        """Insert a running span and allocate its stable per-run sequence atomically."""
        with transaction(self.conn):
            row = self.conn.execute(
                "SELECT COALESCE(MAX(sequence), -1) + 1 FROM span WHERE run_id = ?", (run_id,)
            ).fetchone()
            span = Span(
                span_id=new_id("span"),
                run_id=run_id,
                parent_span_id=parent_span_id,
                sequence=int(row[0]),
                kind=kind,
                name=self.redactor.label(name) or "<redacted>",
                started_at=self._clock(),
                inputs=None if inputs is None else self.redactor.value(inputs),
                prompt_version=self.redactor.label(prompt_version),
                model=self.redactor.label(model),
            )
            self._repo().insert(span)
        return span

    def finish_span(
        self,
        span_id: str,
        status: SpanStatus,
        *,
        error_class: str | None = None,
        inputs: RedactedValue | None = None,
        prompt_version: str | None = None,
        model: str | None = None,
        raw_output: RedactedValue | None = None,
        parsed_output: RedactedValue | None = None,
        decision: RedactedValue | None = None,
        tool_calls: list[TraceToolCall] | None = None,
        cost_usd: float | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> Span:
        """Close one running span exactly once, preserving all buffered redacted observations."""
        if status is SpanStatus.RUNNING:
            raise ValueError("finish_span requires a terminal status")
        current = self._repo().get(span_id)
        if current is None:
            raise TraceNotFoundError(f"unknown span {span_id}")
        ended_at = max(self._clock(), current.started_at)
        done = Span.model_validate(
            {
                **current.model_dump(),
                "ended_at": ended_at,
                "duration_ms": (ended_at - current.started_at).total_seconds() * 1000,
                "status": status,
                "error_class": self.redactor.label(error_class),
                "inputs": inputs if inputs is not None else current.inputs,
                "prompt_version": (
                    self.redactor.label(prompt_version) if prompt_version is not None else current.prompt_version
                ),
                "model": self.redactor.label(model) if model is not None else current.model,
                "raw_output": raw_output,
                "parsed_output": parsed_output,
                "decision": decision,
                "tool_calls": tool_calls or [],
                "cost_usd": cost_usd,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
        )
        data = done.model_dump(mode="json")
        for key in ("inputs", "raw_output", "parsed_output", "decision", "tool_calls"):
            data[key] = json.dumps(data[key], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        cur = self.conn.execute(
            "UPDATE span SET ended_at = :ended_at, duration_ms = :duration_ms, status = :status, "
            "error_class = :error_class, inputs = :inputs, prompt_version = :prompt_version, model = :model, "
            "raw_output = :raw_output, parsed_output = :parsed_output, decision = :decision, tool_calls = :tool_calls, "
            "cost_usd = :cost_usd, input_tokens = :input_tokens, output_tokens = :output_tokens "
            "WHERE span_id = :span_id AND status = 'running'",
            data,
        )
        if cur.rowcount != 1:
            raise TraceError(f"span {span_id} is not running")
        return done

    def get_span(self, span_id: str) -> Span | None:
        return self._repo().get(span_id)

    def spans_for_run(self, run_id: str) -> list[Span]:
        rows = self.conn.execute(
            f"SELECT {', '.join(SPAN.columns)} FROM span WHERE run_id = ? ORDER BY sequence",  # noqa: S608
            (run_id,),
        ).fetchall()
        repo = self._repo()
        return [repo.from_row(row, SPAN.columns) for row in rows]

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> TraceDB:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self.close()


@dataclass
class SpanHandle:
    """Mutable in-flight observations; only redacted values reach :class:`TraceDB`."""

    store: TraceDB
    span: Span
    inputs: RedactedValue | None = None
    prompt_version: str | None = None
    model: str | None = None
    raw_output: RedactedValue | None = None
    parsed_output: RedactedValue | None = None
    decision: RedactedValue | None = None
    tool_calls: list[TraceToolCall] = field(default_factory=list)
    cost_usd: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None

    @property
    def span_id(self) -> str:
        return self.span.span_id

    def record_inputs(self, value: object) -> None:
        self.inputs = self.store.redactor.value(value)

    def record_raw_output(self, value: object) -> None:
        self.raw_output = self.store.redactor.value(value)

    def record_parsed_output(self, value: object) -> None:
        self.parsed_output = self.store.redactor.value(value)

    def record_decision(self, value: object) -> None:
        self.decision = self.store.redactor.value(value)

    def record_tool_call(self, name: str, inputs: object | None = None) -> None:
        self.tool_calls.append(
            TraceToolCall(
                name=self.store.redactor.label(name) or "<redacted>",
                inputs=None if inputs is None else self.store.redactor.value(inputs),
            )
        )

    def record_cost(
        self, *, cost_usd: float | None = None, input_tokens: int | None = None, output_tokens: int | None = None
    ) -> None:
        self.cost_usd = cost_usd
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

    def finish(self, status: SpanStatus, *, error_class: str | None = None) -> Span:
        return self.store.finish_span(
            self.span_id,
            status,
            error_class=error_class,
            inputs=self.inputs,
            prompt_version=self.prompt_version,
            model=self.model,
            raw_output=self.raw_output,
            parsed_output=self.parsed_output,
            decision=self.decision,
            tool_calls=self.tool_calls,
            cost_usd=self.cost_usd,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
        )


@contextmanager
def span_scope(
    store: TraceDB,
    kind: SpanKind,
    name: str,
    *,
    run_id: str | None = None,
    parent_span_id: str | None = None,
    inputs: object | None = None,
    prompt_version: str | None = None,
    model: str | None = None,
) -> Iterator[SpanHandle]:
    """Start and always finish a correlated span, mirroring ``run_scope`` exception semantics."""
    correlated_run_id = run_id if run_id is not None else (run_id_var.get() or span_run_id_var.get())
    if correlated_run_id is None:
        raise TraceContextError("span requires run_id or an active run_scope")
    parent = parent_span_id if parent_span_id is not None else span_id_var.get()
    span = store.start_span(
        correlated_run_id,
        kind,
        name,
        parent_span_id=parent,
        inputs=inputs,
        prompt_version=prompt_version,
        model=model,
    )
    handle = SpanHandle(
        store=store,
        span=span,
        inputs=span.inputs,
        prompt_version=span.prompt_version,
        model=span.model,
    )
    token = span_id_var.set(span.span_id)
    run_token = span_run_id_var.set(correlated_run_id)
    try:
        yield handle
    except KeyboardInterrupt:
        handle.finish(SpanStatus.INTERRUPTED, error_class="KeyboardInterrupt")
        raise
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
        status = SpanStatus.OK if code == 0 else SpanStatus.ERROR
        handle.finish(status, error_class=None if code == 0 else "SystemExit")
        raise
    except BaseException as exc:
        handle.finish(SpanStatus.ERROR, error_class=type(exc).__name__)
        raise
    else:
        handle.finish(SpanStatus.OK)
    finally:
        span_run_id_var.reset(run_token)
        span_id_var.reset(token)


def trace_tree(spans: list[Span]) -> list[dict[str, Any]]:
    """Return ordered nested dictionaries using only stored span data."""
    children: dict[str | None, list[Span]] = {}
    for span in spans:
        children.setdefault(span.parent_span_id, []).append(span)

    def node(span: Span) -> dict[str, Any]:
        value = span.model_dump(mode="json")
        value["children"] = [node(child) for child in children.get(span.span_id, [])]
        return value

    return [node(root) for root in children.get(None, [])]


def render_run_trace(store: TraceDB, run_id: str) -> dict[str, object]:
    """Build the CLI payload or raise a clean not-found error."""
    spans = store.spans_for_run(run_id)
    if not spans:
        raise TraceNotFoundError(f"no trace spans found for run {run_id}")
    return {"run_id": run_id, "span_count": len(spans), "spans": trace_tree(spans)}


__all__ = [
    "DEFAULT_MIGRATIONS",
    "SPAN",
    "TRACE_PREVIEW_MAX_CHARS",
    "SpanHandle",
    "TraceContextError",
    "TraceDB",
    "TraceError",
    "TraceNotFoundError",
    "TraceRedactor",
    "render_run_trace",
    "span_id_var",
    "span_run_id_var",
    "span_scope",
    "trace_tree",
]
