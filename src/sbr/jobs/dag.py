"""Stage DAG helper (T-P1-09, docs/08 §2): a pure function over "which stages are done", no I/O."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def ready_stages(dag: Mapping[str, Sequence[str]], done_stages: set[str]) -> list[str]:
    """Stages in ``dag`` that are not yet done but whose prerequisites all are.

    ``dag`` maps a stage name to the stages it depends on (``()`` for a root stage). The result is stable-ordered by
    ``dag`` iteration order, not topologically sorted across levels: call this again after each newly-enqueued
    stage completes to walk further down the graph.
    """
    return [stage for stage, prereqs in dag.items() if stage not in done_stages and set(prereqs) <= done_stages]
