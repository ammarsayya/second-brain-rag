"""Plan consistency validator for docs/ (T-P0-07).

Checks that the authoritative Markdown registers and the machine-readable execution state agree:
  - required planning documents exist
  - task IDs unique; required fields present; statuses/priorities/approval values valid
  - every dependency exists; dependency graph acyclic; no dependency on a later phase
  - DONE tasks only depend on DONE tasks
  - phase summary table counts match the task sections
  - 35_EXECUTION_STATE.json task statuses, totals and next_eligible_tasks match 28
  - spikes referenced in 28 exist in 34 and vice versa
  - ADR ids referenced in tasks exist in 24; ADR status buckets in 35 agree with 24
Usage: python tools/validate_plan.py   (exit code 0 = consistent)
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
REQUIRED = [
    "00_PROJECT_OVERVIEW.md", "01_VISION_AND_GOALS.md", "02_REQUIREMENTS.md", "03_CORPUS_AUDIT.md", "04_KNOWLEDGE_MODEL.md",
    "05_PROVENANCE_MODEL.md", "06_SYSTEM_ARCHITECTURE.md", "07_AGENTIC_ARCHITECTURE.md", "08_INGESTION_ARCHITECTURE.md",
    "09_DOCUMENT_NORMALIZATION.md", "10_MATHEMATICAL_CONTENT.md", "11_VISUAL_CONTENT.md", "12_TAXONOMY_AND_KNOWLEDGE_GRAPH.md",
    "13_RETRIEVAL_ARCHITECTURE.md", "14_CHUNKING_STRATEGY.md", "15_GAP_ANALYSIS.md", "16_EXTERNAL_RESEARCH.md",
    "17_MODEL_STRATEGY.md", "18_STORAGE_STRATEGY.md", "19_OBSIDIAN_INTEGRATION.md", "20_EVALUATION_STRATEGY.md",
    "21_OBSERVABILITY_AND_OPERATIONS.md", "22_SECURITY_AND_SAFETY.md", "23_FAILURE_RECOVERY.md", "24_DECISION_LOG.md",
    "25_OPEN_QUESTIONS.md", "26_RISK_REGISTER.md", "27_PHASES_AND_MILESTONES.md", "28_TASK_REGISTER.md",
    "29_DEPENDENCY_MAP.md", "30_IMPLEMENTATION_SEQUENCE.md", "31_CORPUS_MANIFEST_SPEC.md", "32_DATA_AND_METADATA_SCHEMAS.md",
    "33_TEST_STRATEGY.md", "34_RESEARCH_AND_SPIKE_REGISTER.md", "35_EXECUTION_STATE.json", "36_TECHNOLOGY_ASSESSMENT.md", "37_T2_CORPUS_REAUDIT.md",
]
STATUSES = {"NOT_STARTED", "IN_PROGRESS", "BLOCKED", "DONE", "DEFERRED"}
PRIORITIES = {"critical", "high", "medium", "low"}
APPROVALS = {"none", "review", "required"}
FIELDS = ["Phase", "Status", "Priority", "Dependencies", "Human approval", "Description", "Rationale",
          "Acceptance criteria", "Validation method", "Expected artifacts"]

errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def parse_tasks(text: str) -> dict[str, dict]:
    tasks: dict[str, dict] = {}
    for block in re.split(r"^### ", text, flags=re.M)[1:]:
        head, _, body = block.partition("\n")
        m = re.match(r"(T-P\d+-\d+) — (.+)", head.strip())
        if not m:
            continue
        tid = m.group(1)
        if tid in tasks:
            err(f"duplicate task id {tid}")
        fields = dict(re.findall(r"^- \*\*(.+?):\*\* (.*)$", body, flags=re.M))
        for f in FIELDS:
            if f not in fields:
                err(f"{tid}: missing field '{f}'")
        deps = [] if fields.get("Dependencies", "none") == "none" else [d.strip() for d in fields["Dependencies"].split(",")]
        tasks[tid] = {"phase": fields.get("Phase"), "status": fields.get("Status"), "priority": fields.get("Priority"),
                      "approval": fields.get("Human approval"), "deps": deps, "spike": fields.get("Spike"),
                      "traces": fields.get("Traces to", "")}
    return tasks


def main() -> int:
    for name in REQUIRED:
        if not (DOCS / name).exists():
            err(f"missing required document {name}")
    reg = (DOCS / "28_TASK_REGISTER.md").read_text(encoding="utf-8")
    tasks = parse_tasks(reg)
    pnum = lambda p: int(p[1:])  # noqa: E731

    for tid, t in tasks.items():
        if t["status"] not in STATUSES:
            err(f"{tid}: invalid status {t['status']}")
        if t["priority"] not in PRIORITIES:
            err(f"{tid}: invalid priority {t['priority']}")
        if t["approval"] not in APPROVALS:
            err(f"{tid}: invalid approval {t['approval']}")
        if t["phase"] != tid.split("-")[1]:
            err(f"{tid}: phase field {t['phase']} disagrees with id")
        for d in t["deps"]:
            if d not in tasks:
                err(f"{tid}: unknown dependency {d}")
            elif pnum(tasks[d]["phase"]) > pnum(t["phase"]):
                err(f"{tid}: depends on later-phase task {d}")
            elif t["status"] == "DONE" and tasks[d]["status"] != "DONE":
                err(f"{tid}: DONE but dependency {d} is {tasks[d]['status']}")

    # cycle detection (Kahn)
    indeg = {t: 0 for t in tasks}
    children = defaultdict(list)
    for tid, t in tasks.items():
        for d in t["deps"]:
            if d in tasks:
                indeg[tid] += 1
                children[d].append(tid)
    queue = [t for t, n in indeg.items() if n == 0]
    seen = 0
    while queue:
        n = queue.pop()
        seen += 1
        for c in children[n]:
            indeg[c] -= 1
            if indeg[c] == 0:
                queue.append(c)
    if seen != len(tasks):
        err("dependency cycle detected")

    # summary table
    counts = Counter(t["phase"] for t in tasks.values())
    for p, n in re.findall(r"^\| (P\d+) \| [^|]+ \| (\d+) \|", reg, flags=re.M):
        if counts[p] != int(n):
            err(f"summary table says {p}={n}, sections contain {counts[p]}")
    m = re.search(r"\| \*\*Total\*\* \| \| \*\*(\d+)\*\*", reg)
    if not m or int(m.group(1)) != len(tasks):
        err("summary total does not match number of tasks")

    # execution state
    state = json.loads((DOCS / "35_EXECUTION_STATE.json").read_text(encoding="utf-8"))
    for tid, t in tasks.items():
        if state["tasks"].get(tid) != t["status"]:
            err(f"35 status for {tid} = {state['tasks'].get(tid)} but 28 says {t['status']}")
    for tid in state["tasks"]:
        if tid not in tasks:
            err(f"35 lists unknown task {tid}")
    if state["task_totals"]["total"] != len(tasks):
        err("35 task_totals.total mismatch")
    done = {t for t, v in tasks.items() if v["status"] == "DONE"}
    eligible = sorted(t for t, v in tasks.items() if v["status"] == "NOT_STARTED" and all(d in done for d in v["deps"]))
    if sorted(state["next_eligible_tasks"]) != eligible:
        err(f"35 next_eligible_tasks {state['next_eligible_tasks']} != computed {eligible}")
    if sorted(state["completed_tasks"]) != sorted(done):
        err("35 completed_tasks mismatch")
    for key, status in (("in_progress_tasks", "IN_PROGRESS"), ("blocked_tasks", "BLOCKED")):
        if sorted(state[key]) != sorted(t for t, v in tasks.items() if v["status"] == status):
            err(f"35 {key} mismatch")

    # spikes
    spike_doc = (DOCS / "34_RESEARCH_AND_SPIKE_REGISTER.md").read_text(encoding="utf-8")
    doc_spikes = set(re.findall(r"^\| \*\*(SPIKE-[A-Z]+)\*\* \| (T-P\d+-\d+)", spike_doc, flags=re.M))
    task_spikes = {(t["spike"], tid) for tid, t in tasks.items() if t["spike"]}
    for s in doc_spikes - task_spikes:
        err(f"spike {s[0]} -> {s[1]} in 34 but not in 28")
    for s in task_spikes - doc_spikes:
        err(f"spike {s[0]} -> {s[1]} in 28 but not in 34")
    if set(state["spikes"]) != {s for s, _ in task_spikes}:
        err("35 spikes do not match 28")

    # decisions
    dec = (DOCS / "24_DECISION_LOG.md").read_text(encoding="utf-8")
    adr_status = {a: s for a, s in re.findall(r"^### (ADR-\d+) — .*?\n- \*\*Status:\*\* ([A-Z]+)", dec, flags=re.M | re.S)}
    for tid, t in tasks.items():
        for a in re.findall(r"ADR-\d+", t["traces"]):
            if a not in adr_status:
                err(f"{tid} traces to unknown {a}")
    for bucket, expected in (("accepted", "ACCEPTED"), ("proposed", "PROPOSED"), ("deferred", "DEFERRED"), ("rejected", "REJECTED")):
        for entry in state["decisions"][bucket]:
            a = re.match(r"ADR-\d+", entry).group(0)
            if "(" in entry:  # split decisions such as ADR-009 are documented inline
                continue
            if adr_status.get(a) != expected:
                err(f"35 lists {a} as {expected} but 24 says {adr_status.get(a)}")

    if errors:
        print(f"PLAN INCONSISTENT: {len(errors)} problem(s)")
        for e in errors:
            print("  -", e)
        return 1
    print(f"PLAN CONSISTENT: {len(tasks)} tasks, {len(done)} done, next eligible: {', '.join(eligible) or '—'}; "
          f"{len(adr_status)} decisions; {len(task_spikes)} spikes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
