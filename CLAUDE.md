# CLAUDE.md — Second Brain RAG

A local-first **Agentic RAG Second Brain** over the owner's Maschinenbau-Informatik university corpus. It has hybrid retrieval,
first-class equations (LaTeX) and technical figures, strict provenance, an evidence-backed knowledge graph, an Obsidian vault,
gap analysis, and approval-gated external research. It is not "PDF → chunks → vector DB".

## Authoritative paths

| Path | Role | Rule |
|---|---|---|
| `/Users/ammar/DriveD/MBI-BRAIN` | Source corpus (authoritative evidence) | **READ-ONLY, always.** Never rename, move, delete, rewrite, convert in place or dedupe. `/Users/ammar/DriveD/Studium` is empty and obsolete. Do not use it |
| `/Users/ammar/DriveD/AgenticAI/second-brain-rag` | Code, config, docs, tests, audit, `var/` | `var/` is rebuildable; nothing authoritative may live only there |
| Vault (proposed `/Users/ammar/DriveD/MBI-VAULT`, open question Q-B02) | Obsidian knowledge (user, AI, source-derived notes) | The system never writes `notes/` and never overwrites user-edited files |
| `curation/` (git) | Human decisions (taxonomy, overrides, approvals) | Authoritative; replayed on rebuild |

## Critical constraints (the full list is HC-01…HC-25 in docs/02)

1. Sources are immutable evidence. All source access goes through the SourceFS read-only layer (task T-P1-03).
2. Every derived record carries provenance (activity + derived_from + locator to blob/page/bbox).
3. Equations and figures are first-class. Uncertain extraction stays marked uncertain.
4. Provenance classes stay distinct: SOURCE_DERIVED · USER_AUTHORED · USER_ANNOTATION · AI_GENERATED · EXTERNAL_PENDING · EXTERNAL_RESEARCH · MODEL_KNOWLEDGE.
   External knowledge becomes permanent **only after owner approval**. Model knowledge is never presented as corpus knowledge.
5. Use deterministic code wherever possible. Agents are only the orchestrator plus the research and curation workflows.
6. Do not ACCEPT a technology choice without its spike (docs/34). Keep uncertainty explicit.
7. Model calls go only through the model gateway (role routing, sensitivity gate).

## Current state (2026-09-24)

- **Phase 0 is DONE.** The owner approved the plan on 2026-09-24 (T-P0-08, Q-B05). Q-B01 is closed. Q-B02 is answered (ADR-037). **Q-B03 (2026-11-04): local-only compute (ADR-039). Q-B04 (2026-11-04): hybrid-capable gateway, local-only execution; no credentials, remote calls or paid providers authorized (ADR-040).**
  **Phase 1 (foundations) is DONE** (all 13 tasks; SourceFS, ids/hashing, core schemas, SQLite registry, provenance, run
  ledger, job queue, resource governor, CLI skeleton, curation ledger, synthetic fixture corpus). **Phase 2 (source
  registry, manifest & exact dedup) is next.** See `docs/35_EXECUTION_STATE.json` for task status.
- **Corpus baselines:** t2 = pre-quarantine historical baseline (85,913 files / 561.5 GB; docs/37). **t3 = post-quarantine implementation-source baseline**
  (83,880 files / 558.75 GB; 2,033 exact copies quarantined; docs/38, `audit/phase0/t3/`). `docs/03` is the historical t0/t1 record.
- `/Users/ammar/DriveD/studium_duplicated` is quarantine/rollback evidence. It is **not a source root**, is never ingested and never written.
- `audit/` (t0/t1/t2/t3, `dedup_quarantine/`) is historical evidence. Never modify it. `.venv-audit/` is disposable audit tooling.
- Toolchain: uv (macOS: `~/.local/bin/uv`; Windows: user-site `%APPDATA%\Python\Python314\Scripts\uv.exe`); the project uses Python 3.12 via uv. Run `python tools/check.py` (any OS) or `tools/check.ps1` (Windows) for lint, types and tests. macOS migration status: `docs/reports/2026-11-04_macos_migration_plan.md`.

## How to continue

1. Read `docs/00_PROJECT_OVERVIEW.md`, then `docs/35_EXECUTION_STATE.json` (`next_eligible_tasks`).
2. Take the next eligible task from `docs/30_IMPLEMENTATION_SEQUENCE.md`. Its full spec is in `docs/28_TASK_REGISTER.md`.
   Stop and ask the owner for tasks marked `Human approval: required`.
3. The first implementation task after approval is **T-P1-01** (repository bootstrap). No code may touch `/Users/ammar/DriveD/MBI-BRAIN` before T-P1-03 is DONE.
4. After each task: update its status in 28 **and** 35, record decisions in 24 and answers in 25, then run
   `python tools/validate_plan.py`. It must print `PLAN CONSISTENT`.
5. Project documentation belongs in `docs/` only. The Brain (`/Users/ammar/DriveD/AgenticAI/My-Knowledge/brain`) holds only the registry record
   **PRJ-0030** and, later, distilled cross-project knowledge, per Brain governance.

## Documentation map

Architecture 06 · Agents 07 · Ingestion 08 · Normalization 09 · Math 10 · Visual 11 · Graph 12 · Retrieval 13 · Chunking 14 ·
Gaps 15 · Research 16 · Models 17 · Storage 18 · Obsidian 19 · Eval 20 · Ops 21 · Security 22 · Recovery 23 ·
Decisions 24 · Questions 25 · Risks 26 · Phases 27 · Tasks 28 · Dependencies 29 · Sequence 30 · Manifest 31 · Schemas 32 ·
Tests 33 · Spikes 34 · State 35 · Technology assessment 36 · T2 re-audit 37.
