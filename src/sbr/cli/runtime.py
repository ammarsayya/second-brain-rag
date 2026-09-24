"""Runtime for stateful CLI commands: config, registry, logging and a run-ledger row per invocation (T-P1-08).

Stateless commands (``--help``, ``version``) do not open any state. Every other command runs inside
:func:`command_runtime`, which records exactly one ``run`` row for the invocation.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from sbr.config import SbrConfig, load_config
from sbr.db.registry import RegistryDB
from sbr.obs.logging import configure_logging, shutdown_logging
from sbr.obs.runs import RunHandle, RunLedger, run_scope
from sbr.safety import protected_roots


@dataclass
class Runtime:
    config: SbrConfig
    db: RegistryDB
    ledger: RunLedger
    run: RunHandle


@contextmanager
def command_runtime(command: str, config_path: Path | None = None) -> Iterator[Runtime]:
    config = load_config(config_path)
    roots = protected_roots(config)
    configure_logging(
        config.logs_dir,
        protected=roots,
        level=config.logging.level,
        max_bytes=config.logging.max_bytes,
        backup_count=config.logging.backup_count,
    )
    try:
        with RegistryDB.open(config) as db:
            db.migrate()
            ledger = RunLedger(db.conn)
            with run_scope(ledger, command, config_hash=config.config_hash()) as run:
                yield Runtime(config=config, db=db, ledger=ledger, run=run)
    finally:
        shutdown_logging()
