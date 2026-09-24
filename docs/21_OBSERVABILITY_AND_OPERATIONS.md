# 21 — Observability and Operations

## 1. Signals

| Signal | Where | Content |
|---|---|---|
| **Run ledger** | `registry.sqlite: run` | Every CLI or worker invocation: command, config hash, code version (git sha), start/end, status, counts |
| **Activities** | `activity` table | Provenance-grade record of each producing step (05) |
| **Work queue metrics** | `work_item` aggregates | Per stage: pending/leased/done/failed, throughput (items/min, pages/min), ETA, error classes |
| **Structured logs** | `var/logs/*.jsonl` | Leveled JSON logs with run_id, stage, subject_id; rotated |
| **Agent traces** | `var/traces/` + optional Phoenix (OTel) | Spans per orchestrator node, tool call, model call (07 §8) |
| **Model accounting** | `model_call` table | Role, provider, model version, tokens, cost, latency, cache hit |
| **Quality metrics** | Eval reports + extraction quality summaries | Per document and aggregated (math status counts, OCR confidence) |
| **Resource metrics** | Governor samples | CPU %, RAM, disk free, per-worker RSS |

## 2. Commands (planned CLI surface)

`sbr status` (pipeline dashboard in the terminal) · `sbr runs` · `sbr doctor` (integrity checks: locators resolve, orphan artifacts,
DB integrity, vault hash consistency, source read-only check) · `sbr queue {list,retry,skip}` · `sbr trace <run>` ·
`sbr eval <bench>` · `sbr report {manifest,duplicates,quality,coverage}` · `sbr backup` · `sbr rebuild {index,knowledge,all}`.

## 3. Operating model (single-owner laptop)

- Long jobs run in the background with the governor (08 §5). They pause automatically on low battery or low disk (configurable), and resume.
- Nightly (optional): incremental scan, change detection, queue processing, AI-note staleness refresh within budget, backups.
- Weekly: `sbr doctor --full`, eval regression suite, report.
- Upgrades: bump a stage_version → dry-run impact (`sbr plan-reprocess`) → run → eval gate.

## 4. Runbooks (created in P13, T-P13-10)

Resume after crash · disk full · corrupted SQLite (restore from `.backup`, rebuild) · model provider outage (fallbacks) ·
parser upgrade · embedding swap · vault conflict storm (bulk user edits) · restore from backup.
