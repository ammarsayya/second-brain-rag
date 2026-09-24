"""T-P1-10: worker pool limits respected from simulated metrics (unit tests only; no real disk/RAM probing)."""

from __future__ import annotations

import ctypes
from datetime import datetime

import pytest

from sbr.config import GovernorConfig, ProcessPriority
from sbr.jobs.governor import PauseReason, ResourceGovernor, SystemMetrics, set_process_priority

NOON = datetime(2026, 9, 24, 12, 0)
MIDNIGHT_THIRTY = datetime(2026, 9, 24, 0, 30)


def metrics(*, disk_free_gb: float = 1000.0, ram_used_gb: float = 1.0, now: datetime = NOON) -> SystemMetrics:
    return SystemMetrics(disk_free_gb=disk_free_gb, ram_used_gb=ram_used_gb, now=now)


def test_admits_a_worker_when_every_limit_has_headroom() -> None:
    gov = ResourceGovernor(GovernorConfig(max_workers=6), metrics=lambda: metrics())
    assert gov.check("extract_text", active_workers=0, active_in_stage=0) is None


def test_queue_pauses_at_the_disk_floor() -> None:
    gov = ResourceGovernor(GovernorConfig(disk_floor_gb=50.0), metrics=lambda: metrics(disk_free_gb=49.9))
    assert gov.check("extract_text", active_workers=0, active_in_stage=0) is PauseReason.DISK_FLOOR


def test_disk_floor_boundary_is_inclusive_of_the_floor_itself() -> None:
    gov = ResourceGovernor(GovernorConfig(disk_floor_gb=50.0), metrics=lambda: metrics(disk_free_gb=50.0))
    assert gov.check("extract_text", active_workers=0, active_in_stage=0) is None


def test_ram_ceiling_pauses_admission() -> None:
    gov = ResourceGovernor(GovernorConfig(max_ram_gb=40.0), metrics=lambda: metrics(ram_used_gb=40.0))
    assert gov.check("extract_text", active_workers=0, active_in_stage=0) is PauseReason.RAM_CEILING


def test_worker_pool_count_is_respected() -> None:
    gov = ResourceGovernor(GovernorConfig(max_workers=3), metrics=lambda: metrics())
    assert gov.check("extract_text", active_workers=2, active_in_stage=0) is None
    assert gov.check("extract_text", active_workers=3, active_in_stage=0) is PauseReason.WORKER_POOL_FULL


def test_per_stage_concurrency_limit_is_independent_of_the_pool_wide_limit() -> None:
    gov = ResourceGovernor(
        GovernorConfig(max_workers=6, stage_concurrency={"vision": 1}), metrics=lambda: metrics()
    )
    assert gov.check("vision", active_workers=1, active_in_stage=1) is PauseReason.STAGE_CONCURRENCY_FULL
    assert gov.check("extract_text", active_workers=1, active_in_stage=1) is None  # unlimited stage, pool has room


def test_time_window_admits_inside_and_refuses_outside() -> None:
    gov = ResourceGovernor(
        GovernorConfig(time_windows=["22:00-06:00"]), metrics=lambda: metrics(now=MIDNIGHT_THIRTY)
    )
    assert gov.check("extract_text", active_workers=0, active_in_stage=0) is None

    gov_daytime = ResourceGovernor(GovernorConfig(time_windows=["22:00-06:00"]), metrics=lambda: metrics(now=NOON))
    assert gov_daytime.check("extract_text", active_workers=0, active_in_stage=0) is PauseReason.OUTSIDE_TIME_WINDOW


def test_no_time_windows_configured_means_always_allowed() -> None:
    gov = ResourceGovernor(GovernorConfig(time_windows=[]), metrics=lambda: metrics(now=NOON))
    assert gov.check("extract_text", active_workers=0, active_in_stage=0) is None


@pytest.mark.parametrize(
    ("disk_free_gb", "ram_used_gb", "active_workers"), [(0.0, 0.0, 0), (1000.0, 1000.0, 0), (1000.0, 0.0, 99)]
)
def test_the_most_urgent_reason_wins_when_several_limits_are_breached(
    disk_free_gb: float, ram_used_gb: float, active_workers: int
) -> None:
    gov = ResourceGovernor(
        GovernorConfig(disk_floor_gb=50.0, max_ram_gb=40.0, max_workers=1),
        metrics=lambda: metrics(disk_free_gb=disk_free_gb, ram_used_gb=ram_used_gb),
    )
    assert gov.check("extract_text", active_workers=active_workers, active_in_stage=0) is not None


def test_priority_is_set_on_windows_and_a_no_op_elsewhere(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, int]] = []

    class FakeKernel32:
        @staticmethod
        def GetCurrentProcess() -> str:  # noqa: N802 - mirrors the win32 API name
            return "handle"

        @staticmethod
        def SetPriorityClass(handle: str, priority_class: int) -> int:  # noqa: N802 - mirrors the win32 API name
            calls.append((handle, priority_class))
            return 1

    class FakeWindll:
        kernel32 = FakeKernel32()

    monkeypatch.setattr(ctypes, "windll", FakeWindll(), raising=False)
    assert set_process_priority(ProcessPriority.BELOW_NORMAL) is True
    assert calls == [("handle", 0x00004000)]

    monkeypatch.delattr(ctypes, "windll", raising=False)
    assert set_process_priority(ProcessPriority.BELOW_NORMAL) is False
