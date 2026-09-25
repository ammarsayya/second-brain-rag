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

### T-P2-03 — Change detection (new/modified/moved/deleted) — **DONE**
- Implemented by Codex from a pre-worked design (given up front to avoid a design round-trip, since this task
  required changing already-shipped T-P2-01/T-P2-02 code). Closed two real gaps:
  1. **Vanished-path detection** didn't exist — `scan.py` only ever touched paths it currently finds. Added
     `detect_changes()` in `src/sbr/registry/changes.py`, run after a scan's hash jobs fully drain, which finds
     every `PathObservation` not touched by the current scan and resolves it to MOVED (same blob reappears at a
     new path in the same scan) or DELETED, orphaning the blob when it loses its last PRESENT observation, and
     reactivating a blob from ORPHANED back to ACTIVE if content reappears later.
  2. **Previous blob_id was lost** before it could be compared (hash.py overwrote it). Fixed: `scan.py` no
     longer nulls `blob_id` on a detected change (keeps the stale value until hash.py replaces it); `hash.py`
     now records the previous value + `scan_id` durably in the completed `WorkOutput.artifacts` dict.
     `hash.py`'s new-blob `first_seen_scan` is now the hashing scan (blob birth), not the path's historical
     first-seen scan — needed for correct NEW-vs-ALIAS classification on in-place edits.
  3. Hash-job `stage_version` is now scan-scoped (`hash_job_version()`) so "are this scan's hash jobs done" is
     queryable without a `scan_id` column on `work_item`.
- No row is ever deleted from any table anywhere in this design — state transitions only. Every
  `tests/test_changes.py` scenario asserts row counts across `path_observation`/`blob`/`change_event`/
  `blob_relation` never shrink.
- The Codex background job itself reported a nonzero final exit status after finishing (cause not determined —
  possibly an artifact of its sandboxed environment's own tooling), and it also left one stray gitignored file
  (`var/pytest_acl_plugin.py`, a sandbox ACL workaround script) which was deleted before commit. **Because of
  the nonzero exit, none of the work was taken on faith** — full independent re-verification was done before
  commit: `pytest -q` (222 passed, only the 4 known pdflatex failures), `mypy src/sbr` (clean), `ruff check`/
  `ruff format --check` (clean), a full read-through of `changes.py`'s move/delete/modify/reactivation logic
  and the `scan.py`/`hash.py` diffs, `validate_plan.py` (PLAN CONSISTENT), `audit_crossrefs.py` (CROSSREFS
  CLEAN). All confirmed correct independently of Codex's own claims.
- Commit: `feat(P2): change detection - new/alias/modified/moved/deleted (T-P2-03)`.
- No real-corpus acceptance criterion for this task (fixture-scenario-only per docs/28) — marked DONE directly,
  unlike T-P2-01/T-P2-02 which needed a separate real-corpus run.

### T-P2-04 — File classification v1 (format + knowledge class) — **DONE**
- Implemented by Codex in two passes: (1) full implementation (`src/sbr/registry/classify.py`,
  `config/classification.toml`, migration 0005 for `BlobRecord.encrypted`, `sbr classify` CLI,
  `tools/validate_classify.py`, `tests/test_classify.py`) — magic-byte detection via a TOML-configured
  signature table (PDF/ZIP/OLE2/JPEG/PNG/GIF/BMP/RAR/7z/gzip/PE/MP4/MP3), path-based junk/tool_artifact rules,
  bounded `/Encrypt`-marker PDF encryption detection (tail scan, no parsing/decryption). Two schema extensions
  authorized (explicitly required by T-P2-04's own task text): `KnowledgeClass.THIRD_PARTY_REFERENCE` (ADR-038,
  still `PROPOSED` in docs/24 — left alone, that's the owner's call, but the task register's acceptance
  criteria mandates the class regardless and it's fully reversible) and `BlobRecord.encrypted: bool`. (2) Same
  bounded-`--corpus`-sampling fix pattern as T-P2-02's `validate_hash.py` — `validate_classify.py` initially
  only supported `--config` (would have required fully classifying the whole real corpus first); added a
  `--corpus` bootstrap mode that scans, then hashes+classifies only the sampled set.
- Hit a `detect-secrets` false positive on commit: a PNG magic-byte hex constant in `classification.toml`
  triggered the hex-high-entropy heuristic. Resolved properly via the project's documented mechanism
  (`.secrets.baseline`, regenerated + inline comment), not by bypassing the hook.
- **Real-corpus validation executed** (2026-09-25, read-only, bounded to 200 sampled files, not a full-corpus
  pass): `tools/validate_classify.py --corpus D:\MBI-BRAIN -n 200`. This validator deliberately does not
  self-declare pass/fail (classification quality needs human judgment) — manually reviewed the generated
  report: distribution across all 11 knowledge classes, every sampled row correct on inspection (PDFs->document,
  man-page HTML->third_party_reference matching the census, ANSYS .agdb->tool_artifact, an unlisted `.launch`
  file correctly resolved via the `.metadata` path-rule fallback, all 5 unknowns genuinely unmapped extensions
  correctly surfaced for review). **PASS** (by manual judgment).
- Commits: `feat(P2): file classification v1 - format + knowledge class (T-P2-04)`,
  `docs(P2): T-P2-04 DONE - real-corpus classification review verified`.
- `docs/28`/`docs/35` updated to `DONE`. `next_eligible_tasks` recomputed: adds T-P2-05, T-P2-09, T-P2-10,
  T-P2-11.

### T-P2-05 — Exclusions and sensitivity classification — **DONE**
- Privacy-sensitive task (identifies the owner's own identity documents and third-party students' grade lists).
  Implemented by Codex from a careful brief specifying exact privacy-reporting constraints from docs/22 §3
  ("restricted: counts-only reporting"). Hit and resolved a Codex sandbox write-permission failure before this
  ran (verified with a throwaway probe file before re-delegating — nothing was touched during the failed
  attempt).
- No schema changes needed (`BlobRecord.status`/`.sensitivity` and the curation-override infrastructure already
  existed from T-P1-05/T-P1-12). Sets `status=EXCLUDED` for junk/tool_artifact/executable/third_party_reference/
  encrypted blobs (not `image` — that's later-phase routing, not registration-time exclusion). Sets
  `sensitivity` via path/name keyword rules (Vertrag/Bewerbung/Lebenslauf/Zeugnis/Ausweis/Immatrikulation →
  RESTRICTED; Noten/Ergebnisliste → THIRD_PARTY_PERSONAL, with a negative-lookbehind guard against the
  Noten/Knoten false positive), owner overrides always win.
- **Verified the privacy-critical report logic line-by-line**: default report never includes a RESTRICTED
  blob's relpath (counts only, e.g. "Vertrag: 5"), full paths require an explicit `--show-restricted-paths`
  flag with a printed warning; the CLI command's JSON output was tested to never leak the flagged filename.
- **Real-corpus review executed read-only, counts-only** (2026-09-25): ran the automatic rules against all
  83,880 real observed paths — 28 restricted, 31 third_party_personal, 83,821 normal. Proportionate, no
  false-positive explosion. **No sensitive relpath was ever printed into this session's transcript, terminal
  output, or any log** — only aggregate counts were reviewed, consistent with docs/22 §3's policy.
- Commits: `feat(P2): exclusions and sensitivity classification (T-P2-05)`,
  `docs(P2): T-P2-05 DONE - real-corpus sensitivity review verified`.
- No other task depends on T-P2-05; `next_eligible_tasks` unaffected beyond removing T-P2-05 itself.

## Next eligible tasks (per `docs/35_EXECUTION_STATE.json`, updated after T-P2-05)

`T-P13-04`, `T-P2-06`, `T-P2-08`, `T-P2-09`, `T-P2-10`, `T-P2-11`, `T-P2-13`, `T-P4-01`, `T-P4-13`, `T-P7-03`,
`T-P9-02`.

Per docs/30's sequence, T-P2-06 (exact duplicate groups and canonical selection) is next.

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
