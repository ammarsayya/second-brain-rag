# Implementation Handoff — Second Brain RAG

Living handoff for autonomous/continued sessions. Update after every completed or paused task so no progress is
lost between sessions. Canonical task state lives in `docs/28_TASK_REGISTER.md` and `docs/35_EXECUTION_STATE.json`;
this file is a human-readable summary plus session-to-session continuity notes, not a third source of truth.

## Orchestration model (this and future sessions)

- Sonnet 5 = architect / orchestrator / reviewer.
- `codex:rescue` (Codex, via the codex-companion background `task` mechanism) = implementation executor.
- Every Codex delegation is independently reviewed by Sonnet: diff read, architecture/contract fit checked,
  tests re-run locally (not just trusted from Codex's report), safety constraints verified, mypy/ruff/pytest
  re-run before commit.
- Codex's sandboxed environment cannot write `.git/refs` (branch creation fails with `Permission denied`) —
  Sonnet creates branches and commits after review, not Codex. Codex is told not to commit; it leaves changes
  in the working tree.
- This session runs **natively on the owner's real Windows machine** with direct read access to `D:\MBI-BRAIN`
  and `D:\studium_duplicated` — unlike a cloud/Linux sandbox, real-corpus acceptance criteria can be executed
  directly by the orchestrator, not just prepared as scripts for later. Always confirm this is still true in a
  new session before assuming it (check `Test-Path D:\MBI-BRAIN` / `test -d /d/MBI-BRAIN`).

## Environment notes

- Toolchain: `uv` at `C:\Users\ammar\AppData\Roaming\Python\Python314\Scripts\uv.exe` (add to PATH in bash: not
  on PATH by default in this environment). Python 3.12 via uv.
- `tools/check.ps1` runs lint (ruff), format check, mypy strict on `src/sbr`, and pytest.
- **Known pre-existing, non-blocking test failures**: 4 tests in `tests/test_fixture_generator.py` fail with
  `FixtureGenerationError: pdflatex not found on PATH` — this machine has no local TeX Live/MiKTeX install. The
  checked-in fixture corpus does not need it; only *regenerating* `skript.pdf` does. Do not attempt to fix by
  installing TeX Live unless asked; treat as environment-only and unrelated to any task's own regressions.
  Baseline going forward: **206 passed, 4 known-failed** (pytest -q), growing as new tasks add tests.
- Codex's default model was misconfigured (`gpt-6-sol`, unsupported by this ChatGPT account) at session start;
  fixed by editing `~/.codex/config.toml` to `model = "gpt-5.6-sol"`. If Codex delegations start failing with a
  400 "model not supported" error again, check that file first.
- Codex background jobs (`codex-companion.mjs task --background`) are **not** tracked by the Claude harness's
  own task-notification system when launched this way from a subagent — the subagent hands back immediately
  after launching the job. Poll with
  `node "C:/Users/ammar/.claude/plugins/cache/openai-codex/codex/1.0.6/scripts/codex-companion.mjs" status <job-id> --json`
  and fetch the final report with `... result <job-id> --json` (look at `storedJob.result.rawOutput`).

## Phase status

- **Phase 0**: DONE (approved 2026-09-24).
- **Phase 1**: DONE, all 13 tasks (T-P1-01 … T-P1-13). Verified independently this session: git log matches,
  `validate_plan.py` / `audit_crossrefs.py` clean, full test suite green (bar the pdflatex-only failures above).
- **Phase 2**: IN PROGRESS. Branch `p2-source-registry` (created from `p1-foundations`).

## Task log (this session, 2026-09-24 onward)

### T-P2-01 — Scanner (path observations) — **DONE**
- Implemented by Codex, reviewed and independently re-tested by Sonnet.
- `src/sbr/registry/scan.py` (+ `__init__.py`, added by Sonnet for consistency with sibling packages),
  `sbr scan [--root ID]` CLI command, `tools/validate_scan.py` real-corpus validator, `tests/test_scan.py`,
  extended `tests/safety/test_runtime_guard.py` with `test_full_scan_makes_zero_source_mutations` (TS-SAFE-3).
- Fixed in review: pre-existing mypy strict failure in `src/sbr/jobs/governor.py` (`resource.getrusage` has no
  Windows stubs — only surfaced because this session runs mypy on real Windows for the first time; prior
  sessions ran in a Linux/cloud container). Fixed with a narrowly-scoped `# type: ignore`, no behavior change.
  Committed separately (`fix(P1): mypy-clean resource.getrusage on Windows`) before the T-P2-01 commit.
- **Real-corpus validation executed** (2026-09-24, this session, read-only):
  `python tools/validate_scan.py --corpus "D:\MBI-BRAIN"` →
  scanner=83,880 files, independent os.walk=83,880 files (exact match; matches docs/38 t3 baseline exactly),
  elapsed 34.8s (limit 300s), 0 errors, source-tree aggregate state unchanged before/after. **PASS.**
- Commits on `p2-source-registry`: `fix(P1): mypy-clean resource.getrusage on Windows`,
  `feat(P2): read-only source scanner (T-P2-01)`, `docs(P2): T-P2-01 DONE - real-corpus scan verified`.
- `docs/28` and `docs/35` updated to `DONE`. `next_eligible_tasks` recomputed: adds T-P2-02, T-P2-13.

### T-P2-02 — Content hashing stage (BLAKE3) — **DONE**
- Implemented by Codex in two passes: (1) initial implementation (`src/sbr/registry/hash.py`,
  `src/sbr/registry/priority.py`, `sbr hash` CLI, `tools/validate_hash.py`, `tests/test_hash.py`, TS-SAFE-3
  coverage); Codex correctly paused mid-task to ask approval on the priority-heuristic design (extension
  allow-list feeding `WorkItem.priority`, wired at `scan.py`'s existing enqueue call) — approved, matched what
  was already recommended. (2) Review found a real issue: `tools/validate_hash.py --corpus` was calling the
  unbounded `hash_pending()`, which would have BLAKE3-hashed the entire real corpus (558GB) just to sample 50
  files. Sent back for a scoped fix — bootstrap mode now samples first, then production-hashes only the sampled
  set. First resume attempt lost sandbox write access (a tooling artifact of `--resume`, not a permission
  issue); retried as `--fresh` with full context, succeeded.
- **Real-corpus validation executed** (2026-09-24, read-only, bounded):
  `python tools/validate_hash.py --corpus "D:\MBI-BRAIN" -n 50` → 50/50 sampled hashes matched an independent
  BLAKE3 read path (separate code path: plain file I/O + `blake3` package directly), 0 mismatches, 37.7s.
  **PASS.**
- Commits: `feat(P2): content hashing stage, BLAKE3 (T-P2-02)`, `docs(P2): T-P2-02 DONE - real-corpus hash
  spot-check verified`.
- `docs/28`/`docs/35` updated to `DONE`. `next_eligible_tasks` recomputed: adds T-P2-03, T-P2-04, T-P2-06,
  T-P2-08.

### T-P2-03 — Change detection (new/modified/moved/deleted) — **IN PROGRESS**
- Delegated to Codex with a full pre-worked design (given to avoid a design round-trip, since this task closes
  two real gaps in already-shipped S1/S2 code): (1) vanished-path detection doesn't exist yet in `scan.py` —
  paths that disappear from the source tree are never marked MOVED/DELETED; (2) the "previous blob_id" needed
  to detect Modified + emit a `version_of` `BlobRelation` gets overwritten by `hash.py` before anything can
  read it — recommended fix is to preserve it in the completed `WorkItem`'s artifacts dict rather than losing
  it. Full event-detection design given for New/Alias/Modified/Moved/Deleted per docs/08 §3's table.
  Acceptance: fixture scenarios (move, rename, modify, delete, re-add) via a new `tests/test_changes.py`
  (TS-CHANGE), and the invariant that no row is ever deleted from any table. No real-corpus acceptance
  criterion for this task (fixture-only), so Codex was authorized to mark it DONE directly if its own full test
  run passes, unlike T-P2-01/02.
- **Not yet reviewed** — check back for completion, then: review diff (this one needs particular scrutiny given
  its depth — verify the blob_id preservation approach, the moved-vs-deleted logic, the re-added-path handling,
  and that literally zero rows are ever deleted), re-run tests independently, update state if Codex's own
  DONE claim doesn't hold up, commit, continue.

## Next eligible tasks (per `docs/35_EXECUTION_STATE.json`, updated after T-P2-02)

`T-P13-04`, `T-P2-03` (in progress), `T-P2-04`, `T-P2-06`, `T-P2-08`, `T-P2-13`, `T-P4-01`, `T-P4-13`,
`T-P7-03`, `T-P9-02`.

Per `docs/30_IMPLEMENTATION_SEQUENCE.md`'s recommended linear order, the P2 sequence after T-P2-02 is:
T-P2-03 (change detection) → T-P2-04 (classification) → T-P2-05 (exclusions/sensitivity, owner review) →
T-P2-06 (exact dedup) → T-P2-08 (archives) → T-P2-09 (twins) → T-P2-10 (genre) →
T-P2-11 (course map, owner review) → T-P2-13 (name repair) → T-P2-14 (manifest report) →
T-P2-07 (mirror report) → T-P2-12 (audit refresh, after Q-B01).

Tasks marked "Human approval: review" (T-P2-05, T-P2-11, T-P2-12, T-P2-07) are implemented normally — the
owner reviews the *output* (a report/list), it is not a pre-start gate like "Human approval: required" tasks.

## Safety confirmations (ongoing, re-verify every session)

- `D:\MBI-BRAIN`: **not modified.** Only touched via `SourceFS` read-only operations and, for validation
  scripts, plain read-only file I/O explicitly scoped for that purpose. `test_full_scan_makes_zero_source_mutations`
  and `tools/validate_scan.py`'s aggregate-state check both confirm this empirically, not just by design.
- `D:\studium_duplicated`: **not modified**, never scanned or ingested — excluded via `config.roots.protected`
  and `SourceFS`'s protected-path refusal, inherited automatically by every stage.
- `audit/`, t0–t3 evidence: not touched this session.
- No secrets exposed; no destructive actions taken.

## Exact next action

1. Check Codex's T-P2-02 background job status/result (`codex-companion.mjs status/result <job-id>`).
2. Review the diff against the same bar as T-P2-01 (architecture fit, safety, tests, mypy/ruff/pytest re-run
   independently).
3. Fix or send back any issues found; do not accept completion claims at face value.
4. Once solid: run `tools/validate_hash.py` against `D:\MBI-BRAIN` myself (read-only, ~50-hash spot check).
5. Update `docs/28`/`docs/35` to DONE (or IN_PROGRESS with a precise pending note if the real-corpus step is
   deferred), commit, run `validate_plan.py` / `audit_crossrefs.py`.
6. Move to T-P2-03 (change detection) — next in the docs/30 sequence, deps (T-P2-02) will be satisfied.
7. Continue the same READ → DELEGATE → REVIEW → TEST → VERIFY → UPDATE STATE → VALIDATE → COMMIT → NEXT loop
   through P2 and beyond until a genuine blocker (owner decision, credentials, destructive action, or
   local-Windows-only work with nothing else independently eligible).
