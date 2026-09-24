"""Structured JSONL logging with run correlation and redaction (T-P1-08, NFR-07, docs/22 §3).

* One JSON object per line: ``ts``, ``level``, ``logger``, ``msg``, ``run_id``, plus ``stage``/``subject_id`` and any
  fields passed as ``extra={"sbr": {...}}``.
* ``run_id`` and ``stage`` come from context variables set by the run ledger, so all log lines of a run correlate.
* Redaction runs before formatting. Values of sensitive keys become ``<redacted sha256:… len=N>``, and any text
  containing a configured source-root path is cut at that path. Exception tracebacks are redacted as well.
* Files rotate by size (``logging.max_bytes`` × ``logging.backup_count`` from the config).
"""

from __future__ import annotations

import contextvars
import hashlib
import json
import logging
import logging.handlers
import re
import traceback
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sbr.safety import assert_outside

LOGGER_NAME = "sbr"
LOG_FILE = "sbr.jsonl"

run_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("sbr_run_id", default=None)
stage_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("sbr_stage", default=None)

DEFAULT_SENSITIVE_KEYS = frozenset(
    {"path", "relpath", "relpath_raw", "display_path", "display_name", "filename", "text", "content", "quote",
     "excerpt", "snippet", "os_path"}
)  # fmt: skip
_RESERVED = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"message", "asctime", "sbr"}


def fingerprint(value: str) -> str:
    return (
        f"<redacted sha256:{hashlib.sha256(value.encode('utf-8', 'surrogatepass')).hexdigest()[:12]} len={len(value)}>"
    )


class Redactor:
    """Removes sensitive content from log fields and messages."""

    def __init__(
        self, source_roots: Iterable[str] = (), sensitive_keys: Iterable[str] = DEFAULT_SENSITIVE_KEYS
    ) -> None:
        self.sensitive_keys = frozenset(k.lower() for k in sensitive_keys)
        patterns = []
        for root in source_roots:
            body = re.escape(root.rstrip("\\/")).replace(r"\\", r"[\\/]")
            patterns.append(body)
        # A source path runs until a quote or line break: paths contain spaces, so cutting later is the safe side.
        self._path_re = (
            re.compile(r"(?:\\\\\?\\)?(?:" + "|".join(patterns) + r")[^\r\n'\"]*", re.I) if patterns else None
        )

    def text(self, value: str) -> str:
        if self._path_re is None:
            return value
        return self._path_re.sub(lambda m: "<source-path " + fingerprint(m.group(0))[10:], value)

    def value(self, key: str, value: Any) -> Any:
        if key.lower() in self.sensitive_keys and value is not None:
            return fingerprint(value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False))
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, Mapping):
            return {str(k): self.value(str(k), v) for k, v in value.items()}
        if isinstance(value, list | tuple):
            return [self.value(key, v) for v in value]
        return value


class RedactionFilter(logging.Filter):
    """Applies a :class:`Redactor` to the message, ``extra={"sbr": ...}`` fields and exception text."""

    def __init__(self, redactor: Redactor) -> None:
        super().__init__()
        self.redactor = redactor

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self.redactor.text(record.getMessage())
        record.args = None
        fields = getattr(record, "sbr", None)
        if isinstance(fields, Mapping):
            record.sbr = {str(k): self.redactor.value(str(k), v) for k, v in fields.items()}
        if record.exc_info and record.exc_info[1] is not None:
            exc = record.exc_info[1]
            text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            record.sbr_exc = self.redactor.text(text)
            record.exc_info = None
            record.exc_text = None
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "run_id": run_id_var.get(),
        }
        fields = getattr(record, "sbr", None)
        if isinstance(fields, Mapping):
            for k, v in fields.items():
                out.setdefault(str(k), v)
        for k, v in record.__dict__.items():
            if k not in _RESERVED and k != "sbr_exc" and not k.startswith("_"):
                out.setdefault(k, v)
        out.setdefault("stage", stage_var.get())
        exc = getattr(record, "sbr_exc", None)
        if exc:
            out["exc"] = exc
        return json.dumps(out, ensure_ascii=False, default=str, separators=(",", ":"))


def configure_logging(
    logs_dir: Path,
    *,
    protected: Iterable[str],
    level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 10,
    source_roots: Iterable[str] = (),
) -> logging.Handler:
    """Attach one rotating JSONL handler to the ``sbr`` logger (replacing a previous sbr handler)."""
    roots = tuple(protected)
    target = logs_dir / LOG_FILE
    assert_outside(target, roots)
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(LOGGER_NAME)
    for h in list(logger.handlers):
        if getattr(h, "_sbr_handler", False):
            logger.removeHandler(h)
            h.close()
    handler = logging.handlers.RotatingFileHandler(
        target, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8", delay=True
    )
    handler._sbr_handler = True  # type: ignore[attr-defined]
    handler.addFilter(RedactionFilter(Redactor(source_roots=(*tuple(source_roots), *roots))))
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return handler


def shutdown_logging() -> None:
    logger = logging.getLogger(LOGGER_NAME)
    for h in list(logger.handlers):
        if getattr(h, "_sbr_handler", False):
            logger.removeHandler(h)
            h.close()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{LOGGER_NAME}.{name}" if not name.startswith(LOGGER_NAME) else name)
