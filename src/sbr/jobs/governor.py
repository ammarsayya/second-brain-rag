"""Resource governor (T-P1-10, docs/08 §5, NFR-06): admission control for the job queue's worker pool.

``ResourceGovernor.check()`` answers one question — "may a worker for this stage (keep) run(ning) right now?" — from
live resource metrics and the configured limits. It never touches ``work_item`` rows itself (that stays the job
queue's job); a caller (the pipeline runner) owns its own in-flight worker counts and passes them in, and pauses
leasing when a :class:`PauseReason` comes back. Metrics are read through an injectable :data:`MetricsProvider`, so
tests exercise the decision logic with simulated disk/RAM/time values instead of the real machine's.
"""

from __future__ import annotations

import ctypes
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time
from enum import StrEnum
from pathlib import Path
from typing import Final

from sbr.config import GovernorConfig, ProcessPriority

_TIME_WINDOW_SPLIT: Final = "-"

__all__ = [
    "MetricsProvider",
    "PauseReason",
    "ResourceGovernor",
    "SystemMetrics",
    "real_metrics",
    "set_process_priority",
]


class PauseReason(StrEnum):
    """Why :meth:`ResourceGovernor.check` refused to admit a new worker, most urgent first."""

    DISK_FLOOR = "disk_floor"
    RAM_CEILING = "ram_ceiling"
    OUTSIDE_TIME_WINDOW = "outside_time_window"
    WORKER_POOL_FULL = "worker_pool_full"
    STAGE_CONCURRENCY_FULL = "stage_concurrency_full"


@dataclass(frozen=True, slots=True)
class SystemMetrics:
    """A resource snapshot. Production code builds this from the real machine; tests construct it directly."""

    disk_free_gb: float
    ram_used_gb: float
    now: datetime


MetricsProvider = Callable[[], SystemMetrics]


def real_metrics(disk_path: str | Path = ".") -> SystemMetrics:
    """Live metrics for ``disk_path``'s filesystem. RAM use falls back to 0.0 (never blocking) where unavailable."""
    _total, _used, free = shutil.disk_usage(disk_path)
    return SystemMetrics(disk_free_gb=free / 1e9, ram_used_gb=_ram_used_gb(), now=datetime.now().astimezone())


def _ram_used_gb() -> float:
    """Best-effort resident set size of this process, in GB. No third-party dependency (NFR-06 has no spike for one)."""
    try:
        import resource  # 'resource' is POSIX-only; absent (ImportError) on Windows, this project's target platform.
    except ImportError:
        return 0.0  # no 'resource' module (e.g. Windows): unknown, so never gate on it
    # ru_maxrss is kibibytes on Linux, bytes on macOS/BSD; kibibytes is the common case for this project's targets.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)  # type: ignore[attr-defined,no-any-return,unused-ignore]


def set_process_priority(priority: ProcessPriority) -> bool:
    """Best-effort set this process' priority class (docs/08 §5). Windows only; a no-op (returns False) elsewhere."""
    windll = getattr(ctypes, "windll", None)
    if windll is None:
        return False
    classes = {
        ProcessPriority.IDLE: 0x00000040,  # IDLE_PRIORITY_CLASS
        ProcessPriority.BELOW_NORMAL: 0x00004000,  # BELOW_NORMAL_PRIORITY_CLASS
        ProcessPriority.NORMAL: 0x00000020,  # NORMAL_PRIORITY_CLASS
    }
    handle = windll.kernel32.GetCurrentProcess()
    return bool(windll.kernel32.SetPriorityClass(handle, classes[priority]))


def _parse_window(window: str) -> tuple[time, time]:
    start_s, end_s = window.split(_TIME_WINDOW_SPLIT)
    return time.fromisoformat(start_s), time.fromisoformat(end_s)


def _in_window(now: time, window: str) -> bool:
    start, end = _parse_window(window)
    if start <= end:
        return start <= now <= end
    return now >= start or now <= end  # a window that wraps past midnight, e.g. "22:00-06:00"


class ResourceGovernor:
    """Admission control derived from :class:`~sbr.config.GovernorConfig`. One instance per process."""

    def __init__(self, config: GovernorConfig, *, metrics: MetricsProvider = real_metrics) -> None:
        self.config = config
        self._metrics = metrics

    def check(self, stage: str, *, active_workers: int, active_in_stage: int) -> PauseReason | None:
        """The first reason a new worker for ``stage`` may not start right now, or ``None`` if it may."""
        m = self._metrics()
        if not self._within_time_window(m.now):
            return PauseReason.OUTSIDE_TIME_WINDOW
        if m.disk_free_gb < self.config.disk_floor_gb:
            return PauseReason.DISK_FLOOR
        if m.ram_used_gb >= self.config.max_ram_gb:
            return PauseReason.RAM_CEILING
        if active_workers >= self.config.max_workers:
            return PauseReason.WORKER_POOL_FULL
        limit = self.config.stage_concurrency.get(stage)
        if limit is not None and active_in_stage >= limit:
            return PauseReason.STAGE_CONCURRENCY_FULL
        return None

    def _within_time_window(self, now: datetime) -> bool:
        if not self.config.time_windows:
            return True
        return any(_in_window(now.time(), w) for w in self.config.time_windows)

    def apply_process_priority(self) -> bool:
        """Best-effort set this process to the configured priority. Returns whether it took effect."""
        return set_process_priority(self.config.priority)
