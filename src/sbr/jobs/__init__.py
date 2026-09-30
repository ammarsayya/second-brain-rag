"""Job queue with leases and checkpoints (T-P1-09, docs/08 §2)."""

from __future__ import annotations

from sbr.jobs.dag import ready_stages
from sbr.jobs.governor import (
    MetricsProvider,
    PauseReason,
    ResourceGovernor,
    SystemMetrics,
    real_metrics,
    set_process_priority,
)
from sbr.jobs.queue import (
    BACKOFF_BASE_MS,
    BACKOFF_CAP_MS,
    DEFAULT_LEASE_MS,
    DEFAULT_MAX_ATTEMPTS,
    JobQueue,
    LeaseError,
    backoff_ms,
)

__all__ = [
    "BACKOFF_BASE_MS",
    "BACKOFF_CAP_MS",
    "DEFAULT_LEASE_MS",
    "DEFAULT_MAX_ATTEMPTS",
    "JobQueue",
    "LeaseError",
    "MetricsProvider",
    "PauseReason",
    "ResourceGovernor",
    "SystemMetrics",
    "backoff_ms",
    "ready_stages",
    "real_metrics",
    "set_process_priority",
]
