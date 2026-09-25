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

### T-P2-06 — Exact duplicate groups and canonical selection — **DONE**
- Genuine design gap resolved: `curation/canonical_overrides.yaml` (blob-to-blob) doesn't fit this task's
  actual need (obs-level "which path is canonical within one exact-duplicate blob's aliases") — added a new,
  additive `curation/canonical_path_overrides.yaml` following the exact same `CurationModel`/loader conventions,
  leaving the existing file untouched for its intended later use (twins/near-dedup).
- Canonical heuristic: not-mirror-candidate → shallower path → shorter path → no `(1)`/`Kopie` marker →
  lexicographic tie-break. Owner overrides always win. Nothing is ever deleted (ADR-031).
- **Full production pipeline run against `D:\MBI-BRAIN`** (a first — needed because duplicate-group membership
  is a global property, not something a bounded sample can validate): `config/sbr.toml` created (local,
  gitignored, points at the real corpus). Results:
  - scan: 83,880 files / 558.75GB / 34.8s
  - hash: 83,784 hashed, 96 genuinely inaccessible (permission-locked/vanished — isolated correctly, ~62 min)
  - classify: 34,814 unique blobs (i.e. ~58% of files are exact duplicates of something else), 1,027 unknown
    extensions listed for review, 113 encrypted PDFs (**investigated**: sampled 5, all have genuine
    `/Encrypt N 0 R` trailer entries — a broader, safer superset than docs/37's narrower "13 files that prompt
    for a password" count, not a bug)
  - sensitivity: 19 restricted / 11 third_party_personal at the blob level
  - dedup: 23,326 duplicate groups, 11,488 singletons
- `tools/validate_dedup.py --config config/sbr.toml` vs. `audit/phase0/dup_groups.json`: **0 splits, 0 merges**
  across 8,084 comparable historical groups (25,195 surviving paths), 1,757 missing as expected (matches the
  documented 2,033-file t2→t3 quarantine in magnitude). Every Phase-0 duplicate relationship with 2+ surviving
  members today is still correctly grouped.
- Commits: `feat(P2): exact duplicate canonical selection (T-P2-06)`,
  `docs(P2): T-P2-06 DONE - real-corpus Phase-0 comparison verified`.
- `next_eligible_tasks` recomputed: adds T-P2-07, T-P2-14 (both depend on T-P2-06).
- **The full production registry (`var/db/registry.sqlite`, scanned+hashed+classified+sensitivity+dedup) is
  now persisted and reusable** — later P2 tasks that need real-corpus data don't need to re-scan/re-hash from
  scratch; the job-queue idempotency means re-running `sbr scan`/`sbr hash`/etc. only touches what changed.

## Codex delegation stopped (2026-09-25, owner instruction)

The owner's Codex token budget ran out. **From here, all remaining implementation is done directly by Claude,
not delegated to `codex:rescue`.** This applies to all subsequent tasks until/unless the owner says otherwise.

### T-P2-08 — Archive container inventory — **DONE**
- **Implemented directly by Claude** (Codex delegation stopped per owner instruction — token budget exhausted).
  `src/sbr/registry/archives.py`: streams zip (stdlib `zipfile`)/7z (`py7zr`)/tar (stdlib `tarfile`)/rar
  (`rarfile`, external tool) member entries, hashes each (same BLAKE3 identity as S2), matches against existing
  blobs (`already_present`), extracts new document-class members to `var/archive_extract/<container>/`.
  Safety: zip-bomb guard (5GiB total / 300:1 ratio caps, checked before any member is opened), path-traversal
  guard (`..`/absolute/drive-letter member paths excluded, never opened), no execution ever. v1 doesn't recurse
  into archives-within-archives (documented limitation).
- New deps: `py7zr` (pure Python) and `rarfile` (needs an external `unrar`-compatible tool — installed via
  `choco install unrar`, permanent system PATH; this directly implements docs/08 §6's own named architecture,
  not a new technology decision). `rarfile`'s missing type stubs handled via a scoped
  `[[tool.mypy.overrides]]` entry.
- **Found and fixed four real bugs during this task's own review, before and while running against the real
  corpus** (details in the docs/28 verification note — worth a careful read if touching this module):
  1. `activity.outputs` fed raw member paths (not just blob ids) for excluded/unopened members, failing the
     Activity schema's entity-id pattern.
  2. The CP437 "repair" function was corrupting already-correctly-decoded names — Python's `zipfile` already
     decodes CP437 correctly per spec (verified empirically: a name written as CP437 round-trips exactly); blindly
     re-encoding/re-decoding an already-correct name doesn't detect mojibake, it destroys it into different,
     still-printable-but-wrong characters. Fixed to only attempt repair when a specific mojibake telltale is
     present (docs/08 §7's own `Fl├ñche`→`Fläche` example), never as a blind guess.
  3. `containers_considered` (408) didn't sum with processed+unsupported+over_limit (406) against the real
     corpus — a `read_failure` outcome (genuinely corrupt archives) was never tracked, silently dropped from
     every summary. Fixed with a `containers_read_failure` field and a regression test asserting the counts
     always reconcile.
  4. RAR was never actually implemented — only the tool-availability check existed, always falling through to
     `unsupported`. Implemented `_rar_members()` once the tool was installed.
  Also found (not fixed, out of scope, flagged for a follow-up): `tests/safety/test_static_mutators.py`'s
  write-mode-`open()` detector assumes `open(file, mode)`'s positional order and misses `Path.open(mode)`
  method calls (mode as the *first* arg) — a real blind spot, documented in the allow-list entry rather than
  silently exploited or fixed with an unreviewed ripple across other files.
- **Real-corpus reconciliation** (read-only, against the persisted production registry): 408 unique archive
  blobs (387 zip, 21 rar), 405 fully inventoried, 20,671 total members (17,197 already_present — spot-checked
  8/8 genuinely correct — 2,846 skipped_limit, 628 extracted_new). Path-level pre-dedup count (847) is close to
  the t2 census's 812; the member-level "novel content" figure doesn't numerically match t2's 16,102, explained
  and verified as a methodology difference (BLAKE3 content-hash matching, strictly more precise than t2's
  same-name-sibling-folder heuristic) rather than a bug.
- Commits: `feat(P2): archive container inventory - zip/7z/tar/rar (T-P2-08)`,
  `fix(P2): implement real RAR support, track read_failure (T-P2-08)`,
  `docs(P2): T-P2-08 DONE - real-corpus archive reconciliation verified`.
- `next_eligible_tasks` recomputed: adds T-P2-12 (all three dependencies now DONE).

### T-P2-09 — Source-twin candidate detection — **DONE**
- Implemented directly. `src/sbr/registry/twins.py`: proposes PDF<->office-document candidate pairs
  (`BlobRelation`, `twin_candidate`, metadata-only, no SourceFS) from filename stem similarity
  (`difflib.SequenceMatcher` after stripping explicit copy-markers) and folder proximity (same folder, or
  immediate parent/child, grouped by folder for near-linear scaling). No schema gap — `TWIN_CANDIDATE` already
  existed.
- **Two real precision bugs found and fixed reviewing the real-corpus output before reporting**, both worth
  remembering if this module is touched again:
  1. Office lock files (`~$name.docx`) scored high via genuine string similarity on their filename — excluded
     outright, never legitimate content.
  2. `SequenceMatcher.ratio()` alone scored two *different* documents sharing a template as near-identical
     when the actually-distinguishing part (a chapter number, an exam date) differed — e.g. `..._Kap2_3...` vs
     `..._Kap2_2...` scored 0.958. Fixed with an explicit numeric-token guard: when both stems carry digits and
     those digit-sets differ, reject the pair outright regardless of text similarity (a bare copy-numbering
     like `Bachelorarbeit1` still passes, since only one side has digits to contradict it).
- **Real-corpus run**: 54 candidate pairs proposed (down from 104 pre-fix). Real thesis pair found at
  confidence 1.0. 30-sample precision report manually reviewed: confidence correlates well with correctness —
  every ≥0.85 entry correct, only the 0.6–0.8 tail has legitimately ambiguous cases (appropriate for a
  candidate-only system; T-P5-04 confirms/rejects later).
- Commits: `feat(P2): source-twin candidate detection (T-P2-09)`,
  `fix(P2): exclude Office lock files from twin detection (T-P2-09)`,
  `docs(P2): document twin-candidate stale-row limitation (T-P2-09)`,
  `fix(P2): reject twin candidates with mismatched numeric identifiers (T-P2-09)`,
  `docs(P2): T-P2-09 DONE - real-corpus twin detection verified`.
- **Known limitation documented in the module docstring**: a re-run doesn't remove a previously-proposed
  `candidate`-status row that no longer qualifies (the registry has no delete capability by design, and
  `RelationStatus` has no "superseded" value distinct from an owner's `rejected`) — flagged as future work, not
  built unilaterally. Hit once in practice (required a manual one-off SQL cleanup after each precision fix,
  same pattern needed if this module changes again).

### T-P2-10 — Genre classification v1 and exam-solution pairing — **DONE**
- Implemented directly. `src/sbr/registry/genre.py`: rule-based genre from filename tokens (Klausur, Lösung/
  Musterlösung/Kurzlösung/TutLos/Lsg, Übung/Aufgabenblatt, Skript, Labor, Bericht, Bachelorarbeit/
  Masterarbeit/Diplomarbeit, ISBN), plus solution_of pairing of solution files to exam/exercise targets by
  stem + sibling/parent-child folder proximity.
- **Eight real bugs found and fixed by running the production pipeline against `D:\MBI-BRAIN` and manually
  reviewing the actual output** (not by code inspection): (1) `\b` doesn't bound against `_`, breaking the
  corpus's dominant underscore-joined naming style — fixed by normalizing `_`/`-`/`.` to spaces before
  matching. (2) Solution pairing's folder-proximity rule found zero pairs for the common `Klausuren/` next to
  `Loesungen/` sibling-folder layout — added sibling support. (3) A folder-only fallback tier caused ~20%
  false positives and was removed — genre is filename-token match only now. (4) "Lsg" abbreviation was
  missing from solution keywords. (5) A bare 13-digit ISBN-as-filename (no "ISBN" label) wasn't recognized.
  (6) `validate_genre.py --draft` sampled from all blobs instead of only classified ones. (7) Tool-artifact/
  code files coincidentally named after genre keywords were excluded via a knowledge-class filter. (8) "ohne
  Lösung" (exam explicitly *without* its solution) matched the bare solution keyword — fixed with a negation
  regex scoped to the solution rule only.
- **Real-corpus production run**: `sbr genre` against `D:\MBI-BRAIN`: 17,759 knowledge-bearing blobs
  considered, 2,035 classified, 212 solution_of pairs proposed.
- **Formal 150-file precision eval** (the task's own two-step acceptance criterion): drafted via
  `tools/validate_genre.py --draft` (seed 20260925, sampled from the classified population only), each row
  independently labeled by reviewing the real relpath, scored via `--score`: **precision = 148/150 = 0.9867**,
  clearing the ≥0.9 bar. The 2 false positives are narrow, non-recurring known limitations: a mojibake-
  corrupted filename (`L├Âsung` for `Lösung` — in T-P2-13's scope, not this task) and one file using an
  unseparated "Musterlsg" abbreviation that the word-boundary-anchored `lsg` keyword correctly declines to
  match (a boundary-free substring match was rejected as too broad — it would false-positive on unrelated
  tokens containing "lsg").
- Commits: `feat(P2): genre classification and exam-solution pairing (T-P2-10)`,
  `fix(P2): remove folder-only genre fallback, fix ISBN/Lsg gaps (T-P2-10)`,
  `fix(P2): sample only classified blobs for genre precision eval (T-P2-10)`,
  `fix(P2): exclude non-knowledge-bearing classes from genre (T-P2-10)`,
  `fix(P2): recognize 'ohne Loesung' negation in genre classification (T-P2-10)`,
  `docs(P2): mark T-P2-10 DONE — real-corpus precision eval 0.9867 (T-P2-10)`.

## Next eligible tasks (per `docs/35_EXECUTION_STATE.json`, updated after T-P2-10)

`T-P13-04`, `T-P2-07`, `T-P2-11`, `T-P2-12`, `T-P2-13`, `T-P2-14`, `T-P3-01`, `T-P4-01`, `T-P4-13`, `T-P7-03`,
`T-P9-02`.

Per `docs/30_IMPLEMENTATION_SEQUENCE.md`'s recommended linear order, the P2 sequence after T-P2-10 is:
T-P2-11 (course map, owner review) → T-P2-13 (name repair) → T-P2-14 (manifest report) →
T-P2-07 (mirror report) → T-P2-12 (audit refresh, after Q-B01). **T-P2-11 (course and abbreviation mapping)
is next.**

Tasks marked "Human approval: review" (T-P2-05 done, T-P2-11, T-P2-12, T-P2-07) are implemented normally —
the owner reviews the *output* (a report/list), it is not a pre-start gate like "Human approval: required"
tasks.

T-P3-01 (Phase 3's first task) is now also eligible — T-P2-10 was its last blocking P2 dependency — but the
docs/30 sequence keeps P2 work first; do not jump to P3 while eligible P2 tasks with satisfied dependencies
remain, per the standing instruction not to jump to downstream phases prematurely.

## Safety confirmations (ongoing, re-verify every session)

- `D:\MBI-BRAIN`: **not modified.** Only touched via `SourceFS` read-only operations and, for validation
  scripts, plain read-only file I/O explicitly scoped for that purpose. `test_full_scan_makes_zero_source_mutations`
  and `tools/validate_scan.py`'s aggregate-state check both confirm this empirically, not just by design.
- `D:\studium_duplicated`: **not modified**, never scanned or ingested — excluded via `config.roots.protected`
  and `SourceFS`'s protected-path refusal, inherited automatically by every stage.
- `audit/`, t0–t3 evidence: not touched this session.
- No secrets exposed; no destructive actions taken.

## Exact next action

1. Implement T-P2-11 (course and abbreviation mapping) directly (no more Codex delegation, per standing
   instruction): seed `curation/course_map.yaml` from the module handbook + observed folder abbreviations
   (Reg1, RGT, MSR2, GrdInf, BS1, KONleh, ...); map documents to courses with a confidence score.
2. Acceptance criterion: all level-3 folders mapped or explicitly marked unknown. This is a "Human approval:
   review" task — implement and produce the mapping/report normally; the owner reviews ambiguous mappings
   afterward, it is not a pre-start gate.
3. Write tests, run `tools/check.ps1` equivalent (pytest + mypy strict + ruff check + ruff format --check),
   confirm only the 4 known pdflatex failures remain.
4. Run against the real production registry (`config/sbr.toml` against `D:\MBI-BRAIN`) and manually
   sanity-check the mapping output before claiming completion — this session's established discipline of
   independently re-verifying against real data has caught a real bug in every P2 task implemented directly so
   far.
5. Update `docs/28`/`docs/35` (DONE or IN_PROGRESS with a precise pending note), commit, run
   `validate_plan.py` / `audit_crossrefs.py`.
6. Continue the same IMPLEMENT → TEST → VERIFY (real corpus) → UPDATE STATE → VALIDATE → COMMIT → NEXT loop
   through the rest of P2 (T-P2-13, T-P2-14, T-P2-07, T-P2-12) toward 14/14 DONE, then reassess Phase 3's
   first eligible task (T-P3-01), until a genuine blocker (owner decision, credentials, destructive action, or
   an acceptance criterion genuinely impossible to satisfy).
