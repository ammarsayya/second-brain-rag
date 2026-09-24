"""Run ledger (T-P1-08, docs/21 §1): every stateful CLI or worker invocation is one ``run`` row.

:func:`run_scope` records the run as ``running``, sets the ``run_id`` context variable used by the logger, and
finishes it as ``succeeded``, ``failed`` (error class only, never the message) or ``interrupted``.
Arguments are never stored: they may contain source paths.
"""

from __future__ import annotations

import functools
import json
import os
import shutil
import sqlite3
import subprocess
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sbr import __version__
from sbr.db import registry as reg
from sbr.db.repository import Repository, TableSpec
from sbr.ids import new_id
from sbr.obs.logging import get_logger, run_id_var
from sbr.schemas import RunRecord, RunStatus

RUN = TableSpec("run", RunRecord, ("run_id",))
REPO_ROOT = reg.REPO_ROOT

log = get_logger("run")


@functools.cache
def git_sha(repo_root: Path = REPO_ROOT) -> str | None:
    """Commit of the running code (``+dirty`` if tracked files changed), or ``None`` outside a git checkout."""
    git = shutil.which("git")
    if git is None:
        return None
    try:
        sha = subprocess.run(  # noqa: S603 - fixed argv, resolved git binary
            [git, "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout.strip()
        dirty = subprocess.run(  # noqa: S603 - fixed argv, resolved git binary
            [git, "status", "--porcelain", "--untracked-files=no"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return f"{sha}+dirty" if dirty else sha


@dataclass
class RunHandle:
    run: RunRecord
    counts: dict[str, int] = field(default_factory=dict)
    exit_code: int = 0

    @property
    def run_id(self) -> str:
        return self.run.run_id

    def count(self, key: str, n: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + n


class RunLedger:
    def __init__(self, conn: sqlite3.Connection, *, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self.conn = conn
        self.repo: Repository[RunRecord] = Repository(conn, RUN)
        self._clock = clock

    def start(self, command: str, *, config_hash: str | None) -> RunRecord:
        run = RunRecord(
            run_id=new_id("run"),
            command=command,
            config_hash=config_hash,
            code_version=__version__,
            git_sha=git_sha(),
            pid=os.getpid(),
            started_at=self._clock(),
        )
        self.repo.insert(run)
        return run

    def finish(
        self, run_id: str, status: RunStatus, *, exit_code: int | None, error_class: str | None, counts: dict[str, int]
    ) -> RunRecord:
        current = self.repo.get(run_id)
        if current is None:
            raise LookupError(f"unknown run {run_id}")
        done = RunRecord.model_validate(
            {
                **current.model_dump(),
                "status": status,
                "ended_at": max(self._clock(), current.started_at),
                "exit_code": exit_code,
                "error_class": error_class,
                "counts": counts,
            }
        )
        cur = self.conn.execute(
            "UPDATE run SET status = ?, ended_at = ?, exit_code = ?, error_class = ?, counts = ? "
            "WHERE run_id = ? AND status = 'running'",
            (
                status.value,
                done.model_dump(mode="json")["ended_at"],
                exit_code,
                error_class,
                json.dumps(counts, sort_keys=True),
                run_id,
            ),
        )
        if cur.rowcount != 1:
            raise LookupError(f"run {run_id} is not running")
        return done

    def recent(self, limit: int = 20) -> list[RunRecord]:
        rows = self.conn.execute(
            f"SELECT {', '.join(RUN.columns)} FROM run ORDER BY started_at DESC, run_id DESC LIMIT ?",  # noqa: S608
            (int(limit),),
        ).fetchall()
        return [self.repo.from_row(r, RUN.columns) for r in rows]


@contextmanager
def run_scope(ledger: RunLedger, command: str, *, config_hash: str | None) -> Iterator[RunHandle]:
    run = ledger.start(command, config_hash=config_hash)
    handle = RunHandle(run)
    token = run_id_var.set(run.run_id)
    log.info("run started", extra={"sbr": {"command": command}})
    try:
        yield handle
    except KeyboardInterrupt:
        ledger.finish(run.run_id, RunStatus.INTERRUPTED, exit_code=130, error_class="KeyboardInterrupt",
                      counts=handle.counts)  # fmt: skip
        log.warning("run interrupted")
        raise
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
        status = RunStatus.SUCCEEDED if code == 0 else RunStatus.FAILED
        ledger.finish(run.run_id, status, exit_code=code, error_class=None if code == 0 else "SystemExit",
                      counts=handle.counts)  # fmt: skip
        raise
    except BaseException as exc:
        ledger.finish(run.run_id, RunStatus.FAILED, exit_code=1, error_class=type(exc).__name__, counts=handle.counts)
        log.exception("run failed", extra={"sbr": {"error_class": type(exc).__name__}})
        raise
    else:
        status = RunStatus.SUCCEEDED if handle.exit_code == 0 else RunStatus.FAILED
        ledger.finish(run.run_id, status, exit_code=handle.exit_code, error_class=None, counts=handle.counts)
        log.info("run finished", extra={"sbr": {"status": status.value, "counts": handle.counts}})
    finally:
        run_id_var.reset(token)
