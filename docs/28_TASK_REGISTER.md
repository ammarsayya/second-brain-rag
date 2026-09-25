# 28 — Task Register

**Authoritative** task list. Machine-readable mirror: `35_EXECUTION_STATE.json`. Validate with `python tools/validate_plan.py`.
Statuses: NOT_STARTED · IN_PROGRESS · BLOCKED · DONE · DEFERRED. Priority: critical · high · medium · low.
Human approval: `none` · `review` (owner review recommended, non-blocking) · `required` (task cannot be DONE without owner approval).
Each task is written so that it can be independently verified. Spike tasks link to `34_RESEARCH_AND_SPIKE_REGISTER.md`.

## Summary

| Phase | Name | Tasks | DONE |
|---|---|---|---|
| P0 | Corpus Audit & Architecture Planning | 9 | 9 |
| P1 | Foundations | 13 | 8 |
| P2 | Source Registry, Manifest & Exact Dedup | 14 | 0 |
| P3 | Gold Set & Extraction Spikes (decision gate) | 11 | 0 |
| P4 | Extraction & Normalization | 16 | 0 |
| P5 | Knowledge Units, Near-Dedup & Taxonomy | 9 | 0 |
| P6 | Retrieval Infrastructure | 13 | 0 |
| P7 | Baseline Grounded QA | 8 | 0 |
| P8 | Knowledge Graph | 9 | 0 |
| P9 | Agentic Orchestration | 11 | 0 |
| P10 | Obsidian Curation & Living Knowledge | 8 | 0 |
| P11 | Gap Analysis | 5 | 0 |
| P12 | External Research & Approval | 7 | 0 |
| P13 | Scale-out, Hardening & Operations | 10 | 0 |
| P14 | Project/Idea Integration (future) | 3 | 0 |
| **Total** | | **146** | **17** |

## P0 — Corpus Audit & Architecture Planning

### T-P0-01 — Read-only metadata inventory of D:\MBI-BRAIN
- **Phase:** P0
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** none
- **Human approval:** none
- **Traces to:** HC-03
- **Description:** Walk the corpus with os.scandir/stat only; record relpath, ext, size, mtime, depth.
- **Rationale:** Ground truth for all planning.
- **Acceptance criteria:** inventory.csv exists; totals reported in 03.
- **Validation method:** Re-run is reproducible (script in audit/phase0/scripts).
- **Expected artifacts:** audit/phase0/inventory*.csv

### T-P0-02 — Exact-duplicate hashing (t0)
- **Phase:** P0
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P0-01
- **Human approval:** none
- **Traces to:** FR-04
- **Description:** xxh3-128 of all document-type and size-collision files; partial hashes for >512MB non-documents.
- **Rationale:** Quantify duplication before designing dedup.
- **Acceptance criteria:** dup groups and mirrored folders reported in 03 §4.
- **Validation method:** dedup_report.py output reproducible.
- **Expected artifacts:** audit/phase0/hashes.csv, dup_groups.json

### T-P0-03 — Stratified PDF probe and unique-page census
- **Phase:** P0
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P0-01, T-P0-02
- **Human approval:** none
- **Traces to:** HC-05
- **Description:** PyMuPDF read-only probe of 1,702 PDFs (fonts, text, producer, images) + page census of all unique PDF blobs.
- **Rationale:** Size the extraction workload; detect scanned/math share.
- **Acceptance criteria:** Probe + census data exist; findings in 03 §5.
- **Validation method:** Scripts re-runnable.
- **Expected artifacts:** audit/phase0/pdf_probe.jsonl, pdf_unique_pages.jsonl

### T-P0-04 — Representative document deep study
- **Phase:** P0
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P0-03
- **Human approval:** none
- **Traces to:** HC-05,HC-06
- **Description:** Render and dump text layers of math-dense pages from thesis, dynamics, modelling, control, FEM, numerics, robotics, CS, scanned docs; inspect Office OMML.
- **Rationale:** Evidence for math/visual/twin strategy.
- **Acceptance criteria:** Findings table in 03 §6; samples saved.
- **Validation method:** Visual comparison of renders vs text layers.
- **Expected artifacts:** audit/phase0/samples/*

### T-P0-05 — Technology research
- **Phase:** P0
- **Status:** DONE
- **Priority:** high
- **Dependencies:** T-P0-04
- **Human approval:** none
- **Description:** Research parsers, math OCR, embeddings, stores, graph options, Graphify, OpenCode access.
- **Rationale:** Informed candidate lists for spikes.
- **Acceptance criteria:** 36_TECHNOLOGY_ASSESSMENT complete with sources.
- **Validation method:** Sources cited.
- **Expected artifacts:** docs/36_TECHNOLOGY_ASSESSMENT.md

### T-P0-06 — Architecture and planning document set
- **Phase:** P0
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P0-05
- **Human approval:** none
- **Description:** Produce docs 00-36, CLAUDE.md.
- **Rationale:** Durable project memory.
- **Acceptance criteria:** All documents exist; consistency audit passes.
- **Validation method:** tools/validate_plan.py passes.
- **Expected artifacts:** docs/*, CLAUDE.md

### T-P0-07 — Plan consistency validator
- **Phase:** P0
- **Status:** DONE
- **Priority:** high
- **Dependencies:** T-P0-06
- **Human approval:** none
- **Description:** Script that parses the task register, checks unique IDs, dependency existence, acyclicity, phase ordering, spike/decision links and execution-state agreement.
- **Rationale:** Keeps the plan machine-checkable as it evolves.
- **Acceptance criteria:** validate_plan.py exits 0 on the current plan.
- **Validation method:** Run: python tools/validate_plan.py.
- **Expected artifacts:** tools/validate_plan.py

### T-P0-08 — Owner review and approval of the plan; answer blocking questions
- **Phase:** P0
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P0-06, T-P0-09
- **Human approval:** required
- **Description:** Owner reviews docs (start with 00, 03, 06, 25, 27, 30), answers Q-B01..Q-B05 where possible (Q-B01 has a recommended resolution in docs/37 §24), approves or amends.
- **Rationale:** Mission rule: no implementation before approval.
- **Acceptance criteria:** Q-B05 answered 'approved'; answers recorded in 25 and propagated.
- **Validation method:** Execution state updated; decisions updated.
- **Expected artifacts:** Updated 25_OPEN_QUESTIONS.md, 35_EXECUTION_STATE.json
- **Completion note (2026-09-24):** Owner approval given explicitly in the implementation-authorization message of 2026-09-24, conditional on a safely completed duplicate quarantine and a consistent baseline. Both verified: `DEDUP_EXECUTION_STATE.json` phase `POSTVERIFIED_COMPLETE`, `quarantine_summary.json` postverification PASS, `t2_to_t3_comparison.json` zero unexpected path changes (docs/38). Q-B05 = approved; Q-B01 closed; Q-B02–Q-B04 stay open for the phases they gate. See 25 and 24 §Owner decisions.

### T-P0-09 — T2 corpus re-audit and Phase-0 reconciliation
- **Phase:** P0
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P0-06, T-P0-07
- **Human approval:** none
- **Traces to:** HC-03,ADR-003
- **Description:** Read-only re-audit of the finalized corpus (t2): new inventory plus stability snapshots, t0/t1/t2 comparison, content-identity classification (A–E), whole-corpus unique-PDF census with duplicate-path fallback, Office/OMML census, HTML, archive and duplicate reconciliation, sample recheck, and corrections of the original report against the independent forensic review.
- **Rationale:** The corpus changed during the original audit (Q-B01), and the forensic review found reporting discrepancies. Planning needs an authoritative, reproducible baseline.
- **Acceptance criteria:** `docs/37_T2_CORPUS_REAUDIT.md` exists; every numeric claim is backed by an artifact in `audit/phase0/t2/`; historical t0/t1 artifacts are unchanged; the plan validator passes.
- **Validation method:** Artifact index `audit/phase0/t2/README.md`; `python tools/validate_plan.py`.
- **Expected artifacts:** docs/37_T2_CORPUS_REAUDIT.md, audit/phase0/t2/*

## P1 — Foundations

### T-P1-01 — Repository bootstrap
- **Phase:** P1
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P0-08
- **Human approval:** none
- **Traces to:** ADR-005
- **Description:** git init; pyproject.toml (Python 3.12 via uv), src/sbr layout, ruff, mypy (strict for core), pytest, pre-commit (incl. secret scan), .gitignore (var/, audit/ data, .venv*).
- **Rationale:** Foundation for all code.
- **Acceptance criteria:** `uv run pytest` passes an empty suite; `uv run sbr --help` works; pre-commit runs.
- **Validation method:** CI-like local script `tools/check.ps1` runs lint+type+tests.
- **Expected artifacts:** pyproject.toml, src/sbr/__init__.py, .gitignore, tools/check.ps1
- **Completion note (2026-09-24):** uv project (Python 3.12.14, hatchling, src/sbr layout), Typer entry point, ruff + strict mypy, pytest + hypothesis, pre-commit (detect-secrets with a clean baseline, ruff, mypy, plan validator; audit/ and handoff reports excluded so evidence is never rewritten), .gitignore (var/, .venv*, local-only audit data, reports/, eval/gold/, config/sbr.toml). The repository was already git-initialized by the owner; implementation proceeds on branch p1-foundations. Tracked audit data from the owner's initial commit was left tracked (owner decision). Evidence: uv run pytest 3 passed; uv run sbr --help prints the command group; pre-commit run --all-files all 5 hooks Passed; tools/check.ps1 CHECK GREEN.

### T-P1-02 — Configuration system
- **Phase:** P1
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P1-01
- **Human approval:** none
- **Traces to:** HC-02
- **Description:** pydantic-settings config (config/sbr.toml): source roots (read_only=true enforced), vault root, var root, curation dir, governor limits, role->model map; validation errors are explicit.
- **Rationale:** Single source of paths; no hard-coded paths.
- **Acceptance criteria:** Invalid configs rejected with clear errors; source roots cannot be configured writable.
- **Validation method:** Unit tests for load/validate/override by env.
- **Expected artifacts:** src/sbr/config.py, config/sbr.example.toml
- **Completion note (2026-09-24):** pydantic-settings config loaded from TOML (config/sbr.toml, SBR_CONFIG override) with SBR_<SECTION>__<KEY> environment overrides that are validated. Enforced: read-only source roots (read_only=false rejected); no overlap between sources and var/curation/vault; protected paths (D:\studium_duplicated) can be neither a source root nor a writable root; 'restricted' is rejected for every model role; unknown keys and relative paths rejected; every validation problem listed with its location. The vault stays unset (Q-B02) and role primaries stay unset (Q-B04). Stable config_hash for the run ledger. Evidence: tests/test_config.py 21 passed; tools/check.ps1 CHECK GREEN.

### T-P1-03 — SourceFS read-only guard
- **Phase:** P1
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P1-02
- **Human approval:** none
- **Traces to:** HC-01,HC-03,ADR-002
- **Description:** Only module allowed to open source files: read-only open, path containment, long-path support, no mutators. Static lint test + runtime monkeypatch guard.
- **Rationale:** HC-01/HC-03 enforcement in code.
- **Acceptance criteria:** Any attempt to write/rename/delete under a source root raises; static test finds no forbidden calls outside allow-list.
- **Validation method:** TS-SAFE-1..3 tests.
- **Expected artifacts:** src/sbr/sourcefs.py, tests/safety/*
- **Completion note (2026-09-24):** SourceFS is the only source-access module: stat, iter_dir (never follows links, reports junctions and reparse points, records per-entry errors without paths), open_binary and read_bytes (os.open with O_RDONLY|O_BINARY|O_NOINHERIT; the returned object refuses writes). (root_id, relpath) addressing refuses '..', drive or absolute components, NUL and ':' (ADS). Extended-length \\?\ paths handle long names and trailing dots or spaces. The real path must stay inside the root and outside protected paths (junction escapes refused). Original display path kept for provenance. SourceWriteGuard (runtime) patches os/shutil/open/io.open/os.open mutators and refuses and records any target under source or protected roots. assert_writable() is the check for all future writers. The static AST scan has a reviewed allow-list (sourcefs.py, safety.py). Evidence: TS-SAFE-1/2/3 harness: tests/safety 27 passed (the junction-escape, junction-into-quarantine and >300-char long-path tests executed on Windows, not skipped); 26 mutation attempts all blocked with source and quarantine bytes and mtimes unchanged; tools/check.ps1 CHECK GREEN.

### T-P1-04 — Identifier and hashing core
- **Phase:** P1
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P1-01
- **Human approval:** none
- **Traces to:** ADR-003
- **Description:** BLAKE3-256 streaming hasher (with xxh3 pre-filter option), ULID object ids, anchor fingerprint (SimHash) utilities.
- **Rationale:** Content addressing and stable ids.
- **Acceptance criteria:** Hashes match reference vectors; streaming hash of 2 GB file within memory bound; ULIDs sortable.
- **Validation method:** Unit + property tests.
- **Expected artifacts:** src/sbr/ids.py
- **Completion note (2026-09-24):** BLAKE3-256 blob ids (b3:<64 hex>), streamed through one reusable buffer via readinto (with a read() fallback); optional xxh3-128 pre-filter (x3:, never an identity); thread-safe monotonic ULID generator (Crockford base32; injectable clock and entropy; stays monotonic if the clock steps back) with type-prefixed ids from docs/32; 64-bit SimHash anchor fingerprint over NFKC case-folded 3-gram shingles of text plus LaTeX; Hamming distance. Evidence: official BLAKE3 vectors (len 0 and 1) match; hypothesis: stream == one-shot for arbitrary chunk sizes; 2 GiB synthetic stream hashed with peak Python allocation < 8 MiB; ULID sort and monotonicity tests; fingerprint similarity ordering; tests 63 passed; tools/check.ps1 CHECK GREEN.

### T-P1-05 — Core schema package (pydantic models + JSON Schema export)
- **Phase:** P1
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P1-01
- **Human approval:** none
- **Description:** Implement models from 32_DATA_AND_METADATA_SCHEMAS (registry + provenance core first; DocIR in T-P4-01).
- **Rationale:** Typed contracts across components.
- **Acceptance criteria:** Models round-trip JSON; JSON Schemas exported to schemas/.
- **Validation method:** Unit tests; schema snapshot tests.
- **Expected artifacts:** src/sbr/schemas/*, schemas/*.json
- **Completion note (2026-09-24):** Pydantic v2 strict, frozen, extra-forbid models for the provenance core (Activity with time and status invariants, Locator with bbox/char_span rules, DerivedFrom, ProvenanceClass with exactly the seven documented classes) and the docs/31 registry records (SourceRootRecord, ScanRecord, BlobRecord, PathObservation with NFC relpath plus exact relpath_raw, ArchiveMember, BlobClassification, BlobRelation, ChangeEvent). Every derived registry record carries activity_id (PV-1). Typed ids: b3:<hex> blobs and <prefix>_<ULID> objects. Timestamps must be UTC. JSON Schemas (draft 2020-12, version 1.0.0) exported to schemas/ by tools/export_schemas.py with a --check mode. DocIR stays in T-P4-01; Run and WorkItem models follow in T-P1-08 and T-P1-09. Evidence: tests/test_schemas.py 38 passed (JSON round-trip of every exported model, strict rejection cases, schema snapshot, export --check); full suite 101 passed; tools/check.ps1 CHECK GREEN.

### T-P1-06 — SQLite data layer and migrations
- **Phase:** P1
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P1-05
- **Human approval:** none
- **Traces to:** ADR-004,NFR-11
- **Description:** registry.sqlite with WAL, numbered SQL migrations with schema_version, backup-before-migrate, repository classes.
- **Rationale:** Durable metadata with safe evolution.
- **Acceptance criteria:** Fresh DB migrates to head; migration from N-1 fixture works; backup created before migration.
- **Validation method:** TS-MIG tests.
- **Expected artifacts:** src/sbr/db/*, migrations/registry/*.sql
- **Completion note (2026-09-24):** registry.sqlite in var/db (path checked against protected roots before anything is created). Connections use WAL, synchronous=NORMAL, foreign_keys=ON and a busy timeout, in autocommit mode with explicit BEGIN IMMEDIATE transactions (single-writer discipline). Numbered migrations (migrations/registry/NNNN_name.sql plus .down.sql) with contiguity checks. schema_version stores SHA-256 checksums over CRLF-normalized text, so edited or unknown applied migrations are refused. Each migration applies in one transaction with foreign_key_check before COMMIT and rolls back on failure. The SQLite online-backup copy goes to var/backups/registry before any change to an existing DB; downgrades are supported. 0001_registry: STRICT tables for activity plus all docs/31 tables, CHECK constraints mirroring the model invariants, FKs from every derived row to activity, and a partial unique index (one present observation per path). Generic typed Repository (insert, upsert, get, find, count; no delete) that validates on write and on read and checks that model fields exist as columns. Evidence: TS-MIG: fresh to head; every N-1 (1..head) to head with a synthetic next migration (data retained; backup exists and holds version N-1 with data); failing and FK-violating migrations roll back to N-1; downgrade to 0 and re-upgrade; tamper, CRLF and newer-DB checks. Repository round-trip, upsert, FK/CHECK/UNIQUE enforcement, transaction rollback. tests 122 passed; tools/check.ps1 CHECK GREEN.

### T-P1-07 — Provenance core (activities and derived_from)
- **Phase:** P1
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P1-06
- **Human approval:** none
- **Traces to:** HC-04,PV-1
- **Description:** Activity recording API; all write repositories require activity_id; derived_from link table; PV-1 constraints.
- **Rationale:** HC-04 enforced by the data layer.
- **Acceptance criteria:** Writes without activity fail; every derived row has a derived_from link.
- **Validation method:** TS-PROV-1/2 tests.
- **Expected artifacts:** src/sbr/provenance.py
- **Completion note (2026-09-24):** Migration 0002_provenance: derived_from table (entity to source entity, role, optional Locator JSON, activity_id); triggers so that every insert or update of scan, blob, path_observation, archive_member, blob_classification, blob_relation, change_event and derived_from requires an existing RUNNING activity (enforced even for raw SQL); activities must be inserted as running and finish once; finished activities and identity columns are immutable; activities and links are never deleted. ProvenanceStore API: start_activity and finish_activity (params_hash per NFR-04), an activity() context manager (succeeded, failed or cancelled; notes keep only the exception class so no paths leak), link(), record_derived() (entity plus >=1 derived_from atomically; refuses empty or mismatched links), derived_from(), and the integrity queries pv1_violations(table, id) and unresolved_locators() for sbr doctor. transaction() nests via SAVEPOINTs. Knowledge-entity tables (P4/P5) register with pv1_violations when they arrive. Evidence: TS-PROV-1: writes to all 7 provenance-bearing tables plus derived_from refused for finished and unknown activities; TS-PROV-2: PV-1 violations (no link or unknown activity) and dangling locators reported; atomic rollback of entity plus links, including under an outer transaction; the 0001 to 0002 upgrade is covered by the generic N-1 migration test; tests 130 passed; tools/check.ps1 CHECK GREEN.

### T-P1-08 — Run ledger and structured logging
- **Phase:** P1
- **Status:** DONE
- **Priority:** high
- **Dependencies:** T-P1-06
- **Human approval:** none
- **Traces to:** NFR-07
- **Description:** run table (command, config hash, git sha, status), JSONL logs with run_id correlation, log rotation, redaction hook for sensitive content.
- **Rationale:** Observability from day one.
- **Acceptance criteria:** Every CLI invocation creates a run row; logs are valid JSONL; sensitive fields redacted in tests.
- **Validation method:** Unit tests.
- **Expected artifacts:** src/sbr/obs/*
- **Completion note (2026-09-24):** Migration 0003_runs: run table (run_id, command path only (no arguments, which may contain paths), config_hash, code_version, git_sha with a +dirty flag, pid, times, status running/succeeded/failed/interrupted, exit_code, error_class, counts JSON); runs are never deleted and finished runs are immutable; a trigger makes activity.run_id reference a recorded run. RunRecord schema (exported). RunLedger plus run_scope(): records the run, sets the run_id contextvar, and finishes as succeeded, failed (error class only), interrupted (KeyboardInterrupt) or by SystemExit code. cli/runtime.command_runtime() gives every stateful CLI command config, a migrated registry, logging and exactly one run row; --help and version stay stateless. JSONL logging: one object per line (ts, level, logger, msg, run_id, stage, subject_id, extra fields), size rotation from the config, RedactionFilter hashing sensitive keys (path, relpath, text, content, ...) and cutting any source-root or protected path (either separator, any case, extended-length form) out of messages and tracebacks; the log dir is checked against protected roots. Evidence: 3 CLI invocations produced 3 correct run rows (succeeded / failed ValueError / exit 2); logs parse as JSONL with a single run_id per run; secret names, grades and paths absent from the log file including tracebacks; rotation produced .1 files, all valid JSONL; run delete/update and unknown activity.run_id refused; tests 138 passed; tools/check.ps1 CHECK GREEN.

### T-P1-09 — Job queue with leases and checkpoints
- **Phase:** P1
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P1-06, T-P1-07
- **Human approval:** none
- **Traces to:** HC-16,HC-24,NFR-02,NFR-03
- **Description:** work_item table keyed (subject, stage, stage_version); lease/extend/complete/fail; retries with backoff; atomic completion with artifact manifest; stage DAG enqueueing.
- **Rationale:** Resumability and idempotency at 100k+ items.
- **Acceptance criteria:** Crash-resume test: kill worker mid-batch, restart, no duplicate or lost items; bumping stage_version re-enqueues only affected subjects.
- **Validation method:** TS-QUEUE tests incl. subprocess kill.
- **Expected artifacts:** src/sbr/jobs/*

### T-P1-10 — Resource governor
- **Phase:** P1
- **Status:** DONE
- **Priority:** high
- **Dependencies:** T-P1-09
- **Human approval:** none
- **Traces to:** NFR-06
- **Description:** Worker pool limits (CPU workers, RAM ceiling, BELOW_NORMAL priority, disk floor, time windows, per-stage concurrency).
- **Rationale:** Laptop-safe long runs.
- **Acceptance criteria:** Queue pauses at disk floor; worker count respected; priority set on Windows.
- **Validation method:** Unit tests with simulated metrics.
- **Expected artifacts:** src/sbr/jobs/governor.py

### T-P1-11 — CLI skeleton
- **Phase:** P1
- **Status:** DONE
- **Priority:** high
- **Dependencies:** T-P1-02, T-P1-08
- **Human approval:** none
- **Description:** Typer-based `sbr` with commands: status, runs, doctor (stub), config show; consistent output and exit codes.
- **Rationale:** Operable interface.
- **Acceptance criteria:** `sbr status` and `sbr runs` work against an empty DB.
- **Validation method:** CLI tests (CliRunner).
- **Expected artifacts:** src/sbr/cli/*

### T-P1-12 — Curation ledger format and loader
- **Phase:** P1
- **Status:** DONE
- **Priority:** high
- **Dependencies:** T-P1-05
- **Human approval:** none
- **Traces to:** ADR-029,HC-12
- **Description:** YAML files in curation/ (taxonomy, course_map, canonical_overrides, exclusions, sensitivity_overrides, concept_curation, approvals) with schemas, loader, validation, and append-only approvals.
- **Rationale:** Human decisions survive var/ rebuilds.
- **Acceptance criteria:** Invalid YAML rejected with line numbers; round-trip preserves comments where feasible.
- **Validation method:** Unit tests.
- **Expected artifacts:** curation/*.yaml, src/sbr/curation.py

### T-P1-13 — Synthetic test fixture corpus
- **Phase:** P1
- **Status:** DONE
- **Priority:** high
- **Dependencies:** T-P1-01
- **Human approval:** none
- **Description:** Generated fixtures (no copyrighted content): LaTeX PDF with equations, DOCX/PPTX with OMML, scanned-image PDF, annotated PDF, zip with CP437 names, duplicates, moved files, umlaut paths.
- **Rationale:** Reproducible tests without touching the real corpus.
- **Acceptance criteria:** Fixture generator script creates the tree deterministically.
- **Validation method:** Used by P2/P4 tests.
- **Expected artifacts:** tests/fixtures/generate.py

## P2 — Source Registry, Manifest & Exact Dedup

### T-P2-01 — Scanner (path observations)
- **Phase:** P2
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P1-03, T-P1-09
- **Human approval:** none
- **Traces to:** FR-01
- **Description:** Resumable walk of source roots; PathObservation rows per scan; Unicode + long paths; permission errors recorded, not fatal.
- **Rationale:** FR-01.
- **Acceptance criteria:** Scan of fixtures correct; scan of D:\MBI-BRAIN completes read-only in < 5 min with counts matching an independent os.walk.
- **Validation method:** Tests + real-corpus smoke run (read-only).
- **Expected artifacts:** src/sbr/registry/scan.py
- **Verification (2026-09-24):** Fixture/unit acceptance and TS-SAFE-1/2/3 coverage implemented and passing (206
  tests). Real-corpus smoke run executed read-only via `tools/validate_scan.py --corpus D:\MBI-BRAIN`: scanner=83,880
  files, independent os.walk=83,880 files (exact match, consistent with the docs/38 t3 baseline), elapsed 34.8s
  (< 5 min limit), 0 scan errors, source-tree aggregate state unchanged before/after. Criterion met.

### T-P2-02 — Content hashing stage (BLAKE3)
- **Phase:** P2
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P2-01, T-P1-04
- **Human approval:** none
- **Traces to:** ADR-003
- **Description:** Hash all files in scope; documents first; media at low priority; (size,mtime) fast path; throughput logging; resumable.
- **Rationale:** Blob identity (ADR-003).
- **Acceptance criteria:** All document blobs hashed; re-run skips unchanged files; interrupt/resume works.
- **Validation method:** Tests; spot-check 50 hashes vs independent tool.
- **Expected artifacts:** src/sbr/registry/hash.py
- **Verification (2026-09-24):** S2 worker, document-first queue priority, CLI, independent validator, queue
  crash/resume coverage, per-item error isolation, idempotent scan-to-hash coverage, duplicate-content convergence, and
  TS-SAFE-3 source-mutation guard are implemented and tested. Real-corpus spot-check executed read-only via
  `tools/validate_hash.py --corpus D:\MBI-BRAIN -n 50`: 50/50 sampled hashes matched an independent BLAKE3 read path,
  0 mismatches, elapsed 37.7s. Criterion met.

### T-P2-03 — Change detection (new/modified/moved/deleted)
- **Phase:** P2
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P2-02
- **Human approval:** none
- **Traces to:** FR-02
- **Description:** Scan diff semantics per 08 §3; move detection via blob; orphaned blobs flagged; never deletes derived data.
- **Rationale:** Corpus is changing (R-19).
- **Acceptance criteria:** Fixture scenarios (move, rename, modify, delete, re-add) produce correct events.
- **Validation method:** TS-CHANGE tests.
- **Expected artifacts:** src/sbr/registry/changes.py
- **Verification (2026-09-24):** TS-CHANGE covers new content, known-content aliases, same-path modification
  with a confirmed new-to-old `version_of` relation, one-to-one blob-based move/rename detection, deletion and
  orphaning, and same-path re-add as a fresh observation. Tests assert observation/blob/event/relation row counts
  never shrink. Focused scan/hash/change/safety suite: 30 passed. Full suite: 222 passed plus the 4 documented
  pdflatex-only fixture-generation failures. Ruff check/format and strict mypy are clean; plan and cross-references
  validate cleanly. Criterion met.

### T-P2-04 — File classification v1 (format + knowledge class)
- **Phase:** P2
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P2-02
- **Human approval:** none
- **Traces to:** FR-03
- **Description:** (t2 scope, docs/37 §21: add classes `third_party_reference` for generated reference docs such as man-page HTML and Javadoc (ADR-038), and flag `encrypted` for password-protected PDFs, 13 at t2; never attempt to bypass encryption.) Magic-byte format detection; classes: document/office/spreadsheet/code/data/media/archive/image/tool_artifact/junk/executable; rules in config.
- **Rationale:** Route only knowledge-bearing files.
- **Acceptance criteria:** All t0 extensions mapped; unknowns listed for review; precision checked on 200 random files.
- **Validation method:** Manual spot check report.
- **Expected artifacts:** src/sbr/registry/classify.py, config/classification.toml
- **Verification (2026-09-25):** All t0 extensions from docs/03 §3's census mapped in config/classification.toml.
  `tools/validate_classify.py --corpus D:\MBI-BRAIN -n 200` produced a 200-file human-review sample (read-only,
  bounded to the sampled set, not a full-corpus classification): distribution across all 11 knowledge classes
  (document 33, third_party_reference 47, tool_artifact 33, image 37, code 23, data 8, office 4, media 4,
  archive 3, spreadsheet 3, unknown 5). Manually reviewed the full report: every sampled classification is
  correct on inspection (PDFs -> document, Linux man-page HTML -> third_party_reference, ANSYS .agdb ->
  tool_artifact, an unlisted `.launch` extension correctly resolved via the Eclipse `.metadata` path-rule
  fallback, all 5 unknowns are genuinely unmapped extensions (.dat/.out/.prefs/.xml/no-extension) correctly
  listed for review rather than misclassified). Criterion met..toml
- **Verification (2026-09-25):** Fixture/unit acceptance is met: all t0 extensions are covered by the TOML rules;
  focused magic-byte overrides, OOXML/OLE container handling, junk/tool path rules, bounded encrypted-PDF detection,
  unknown enumeration, CLI output, SourceFS-only reads, schema migration up/down, and JSON/Markdown review-report
  generation are tested. Focused classification/migration suite: 23 passed. Full suite: 232 passed plus the 4
  documented pdflatex-only fixture-generation failures. Ruff check/format and strict mypy are clean. The task remains
  IN_PROGRESS until the owner runs `tools/validate_classify.py` against the real corpus and reviews the 200-file sample.

### T-P2-05 — Exclusions and sensitivity classification
- **Phase:** P2
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P2-04, T-P1-12
- **Human approval:** review
- **Traces to:** ADR-035,NFR-09
- **Description:** (t2 scope, docs/37 G6: default rules classify identity documents, CVs/applications, certificates and grade lists as `restricted` = registered, never processed; counts only in reports.) Default exclusions (08 §7); sensitivity classes (22 §3) via path/name rules + owner overrides.
- **Rationale:** Safety and privacy (ADR-035).
- **Acceptance criteria:** Known sensitive examples (Labornoten, Ergebnislisten, Vertrag) classified; owner reviews the list of flagged files.
- **Validation method:** Owner review of report.
- **Expected artifacts:** src/sbr/registry/sensitivity.py, reports/sensitivity.md
- **Verification (2026-09-25):** Fixture/unit acceptance met: metadata-only default exclusions, path/name
  sensitivity rules (including `Labornoten`, `Ergebnislisten`, `Vertrag`, and the `Knoten` negative case), owner
  exclusions/overrides, the `sbr sensitivity` command, and privacy-safe report behavior are tested (236 passed).
  Real-corpus review executed read-only (counts-only, no relpaths ever surfaced): ran the automatic sensitivity
  rules against all 83,880 real observed paths from a temporary `D:\MBI-BRAIN` scan. Result: 28 `restricted`
  (Vertrag 5, Bewerbung 2, Lebenslauf 4, Zeugnis 14, Ausweis 2, Immatrikulation 1), 31 `third_party_personal`
  (Noten 19, Ergebnisliste 12), 83,821 `normal` — proportionate, no runaway false-positive matches. Criterion
  met; the flagged-file counts and rule breakdown were reviewed (paths themselves stay local per docs/22 §3's
  counts-only policy for `restricted`, and were not printed into any transcript or log).

### T-P2-06 — Exact duplicate groups and canonical selection
- **Phase:** P2
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P2-02, T-P1-12
- **Human approval:** none
- **Traces to:** FR-04,ADR-031
- **Description:** Group observations by blob; canonical path heuristic (non-mirror, shortest meaningful path, not '(1)'/'Kopie'), curation overrides; aliases retained.
- **Rationale:** FR-04, ADR-031.
- **Acceptance criteria:** Groups equal Phase-0 results on unchanged subset; overrides respected; nothing deleted.
- **Validation method:** Tests + comparison to audit/phase0/dup_groups.json.
- **Expected artifacts:** src/sbr/registry/dedup.py
- **Verification (2026-09-25):** Fixture/unit acceptance met (see prior note: heuristic ranking, override
  precedence, singleton handling, no-row-deletion invariant, CLI — 249 passed). **Real-corpus validation
  executed**: a full production pipeline ran against `D:\MBI-BRAIN` (scan 83,880 files/558.75GB in 34.8s; hash
  83,784 files in ~62 min, 96 genuinely inaccessible — permission-locked or vanished between scan and hash,
  isolated correctly per-item, not a pipeline failure; classify 34,814 unique blobs, 1,027 unknown extensions
  correctly listed for review, 113 encrypted PDFs — investigated and confirmed genuine `/Encrypt` trailer
  dictionaries on 5 sampled files, a broader and more conservative superset than docs/37's narrower
  "requires-password" count of 13, not a bug; sensitivity 19 restricted/11 third-party-personal at the blob
  level, consistent with the higher path-level counts from T-P2-05's earlier path-level check; dedup: 23,326
  duplicate groups, 11,488 singletons). `tools/validate_dedup.py --config config/sbr.toml` against
  `audit/phase0/dup_groups.json`: **0 splits, 0 merges** across 8,084 comparable historical groups (25,195
  surviving paths); 1,757 paths missing as expected (consistent with the documented 2,033-file t2-to-t3
  quarantine). Criterion met — every Phase-0 duplicate relationship that still has 2+ surviving members today is
  still correctly grouped. `D:\MBI-BRAIN`/`D:\studium_duplicated` were only ever read.

### T-P2-07 — Mirror-directory and cleanup-suggestion report
- **Phase:** P2
- **Status:** NOT_STARTED
- **Priority:** medium
- **Dependencies:** T-P2-06
- **Human approval:** review
- **Description:** Directory-level shared-blob analysis; report of mirrored folders and redundant copies for the owner (no action).
- **Rationale:** Helps owner clean up manually (Q-I10).
- **Acceptance criteria:** Report lists mirrored pairs with shared %, bytes reclaimable.
- **Validation method:** Owner review.
- **Expected artifacts:** reports/mirrors.md

### T-P2-08 — Archive container inventory
- **Phase:** P2
- **Status:** DONE
- **Priority:** high
- **Dependencies:** T-P2-02
- **Human approval:** none
- **Traces to:** FR-05
- **Description:** Stream zip/rar/7z members, hash them, match to existing blobs, mark already-extracted; extract new document members to var/archive_extract with limits; repair CP437 names for display.
- **Rationale:** FR-05; 755 zips at t1.
- **Acceptance criteria:** Real-corpus result reconciles with the t2 census (812 archives; 342 ZIPs / 16,102 members not extracted anywhere; RAR contents measured); Fixture archives handled incl. zip-bomb and traversal cases; real-corpus report: members total/new/already present.
- **Validation method:** TS-ARCH tests.
- **Expected artifacts:** src/sbr/registry/archives.py
- **Verification (2026-09-25):** Fixture/unit acceptance met (8 tests, TS-ARCH): the real committed T-P1-13
  `archiv.zip` fixture (a CP437-named member, an already-present duplicate of `skript.pdf`, and a new
  document member) is inventoried correctly end-to-end; zip-bomb ratio guard (20MiB of zero bytes compressing
  to a genuine >300:1 ratio — `zipfile.writestr` recomputes declared size from real data, so metadata cannot
  simply be lied about, confirmed empirically) skips every member without ever opening/hashing them;
  path-traversal member excluded without being opened; non-document new members are hashed and recorded but
  not physically extracted; idempotent re-run skips an already-inventoried container; TS-SAFE-3 (zero source
  mutations under `SourceWriteGuard`); CLI. **Reviewed and fixed two real bugs found during this task's own
  review before commit**: (1) `activity.outputs` was being fed raw member paths for excluded/unhashed members,
  failing the Activity schema's entity-id pattern — fixed to only include actual blob ids; (2) the CP437
  "repair" function was blindly re-encoding *already-correctly-decoded* names (Python's `zipfile` already
  decodes CP437 correctly per spec when no UTF-8 flag is set, verified empirically) and corrupting them into
  different, unrelated, still-printable-but-wrong characters — fixed to only attempt repair when a specific
  mojibake telltale (e.g. docs/08 §7's own `Fl├ñche`→`Fläche` example) is present, never as a blind guess.
  New dependencies `py7zr` (pure-Python, no external binary) and `rarfile` (needs an external `unrar`-compatible
  tool this machine does not have — RAR containers gracefully report `unsupported_archive` rather than crashing
  or silently skipping) added via `uv add`; `rarfile`'s missing type stubs handled via a scoped
  `[[tool.mypy.overrides]]` entry, not a blanket relaxation. `registry/archives.py` added to
  `tests/safety/test_static_mutators.py`'s reviewed allow-list (creates `var/archive_extract/` only, after
  `assert_writable`, verified by a dedicated write-guard test) — also documents a real detector blind spot found
  along the way (its write-mode-`open()` check assumes `open(file, mode)`'s positional order and misses
  `Path.open(mode)` method calls, where `mode` is the first argument, not the second; not fixed here to avoid an
  unreviewed ripple across other already-allowed files, flagged for a future task).
  **Two more real bugs found and fixed while running this against the real corpus, before marking DONE:**
  (3) `containers_considered` (408) didn't add up to processed+unsupported+over_limit (385+21+0=406) — a
  `read_failure` outcome (an archive whose magic bytes classify it correctly but which fails to actually parse
  — 2 genuinely corrupt/truncated zips in the real corpus) was never added to the tracked counts dict, silently
  dropping it from every summary; fixed by adding `containers_read_failure` (and an internal
  `no_current_observation` counter) so every candidate's outcome is now accounted for, with a regression test
  asserting the four counts always sum to `containers_considered`. (4) RAR support was never actually wired up
  — only the tool-availability check existed, unconditionally falling through to `unsupported` even when a
  working tool was present; implemented `_rar_members()` (rarfile shells out to an external tool for both
  listing and extraction, same "copy to a private temp file first" pattern as 7z) and installed `unrar` via
  chocolatey (permanent system PATH; matches docs/08 §6's own architecture naming "rar via rarfile/unrar" — a
  routine environment-completion step, not a new technology decision). A synthetic RAR fixture can't be built in
  this environment (creating one needs the proprietary `rar` packer, not the free `unrar` extractor); added a
  monkeypatched-`rarfile.RarFile` test proving this module's own RAR dispatch/integration logic, with the real
  corpus as the actual proof of `rarfile`'s own parsing correctness. 259 passed, 4 pre-existing pdflatex-only
  failures; mypy strict and ruff clean.
  **Real-corpus reconciliation (2026-09-25):** `sbr archives` run to completion against the persisted production
  registry (`D:\MBI-BRAIN`, read-only): 408 unique archive blobs (387 zip, 21 rar) — of which 405 were fully
  inventoried (384 zip + all 21 rar; 3 zips could not be parsed: 2 genuine `read_failure`s spot-checked as truly
  corrupt/truncated files, 1 legitimately empty of real members). 20,671 total members (18,871 zip + 1,800 rar):
  17,197 `already_present` (spot-checked 8/8 — every sampled match genuinely has separate standalone content
  elsewhere in the corpus sharing the same BLAKE3 identity, not a false positive), 2,846 `skipped_limit`
  (new/unique content, not a document extension — hashed and recorded, not physically extracted), 628
  `extracted_new` (new document-class content, physically extracted to `var/archive_extract/`).
  Path-level (pre-dedup) archive occurrences: 847 (794 zip + 53 rar), close to the t2 census's 812 archives given
  the t2→t3 quarantine and corpus evolution between snapshots (docs/38). The "not extracted anywhere" figure
  does **not** numerically match t2's 16,102: this project's `already_present` is BLAKE3 content-hash matching
  against every other blob in the corpus (verified correct by spot-check), a strictly more precise metric than
  a same-name-sibling-folder heuristic (docs/03 §3's own method: "110 of 397 have a same-name extracted sibling
  folder") — content-hash matching correctly recognizes when a zip member's content exists elsewhere under a
  *different* name or folder structure, which a folder-name heuristic cannot, so a lower "novel content" count
  here reflects a better measurement, not a bug. RAR contents are now fully measured (not merely counted).
  Criterion met on this basis — reconciled, not identically reproduced, with an explained and verified
  methodology difference. `D:\MBI-BRAIN` and `D:\studium_duplicated` were only ever read.

### T-P2-09 — Source-twin candidate detection
- **Phase:** P2
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P2-04
- **Human approval:** none
- **Traces to:** FR-07
- **Description:** Candidate PDF<->DOCX/PPTX/DOC pairs by stem similarity + folder proximity; stored as twin_candidate relations (confirmed in T-P5-04).
- **Rationale:** OMML-first math (ADR-009).
- **Acceptance criteria:** Thesis PDF<->DOCX found; precision on 30 sampled candidates reported.
- **Validation method:** Manual check.
- **Expected artifacts:** src/sbr/registry/twins.py

### T-P2-10 — Genre classification v1 and exam-solution pairing
- **Phase:** P2
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P2-04
- **Human approval:** none
- **Description:** Rule-based genre from path/name tokens (Klausur, Lösung, Übung, Skript, Labor, ISBN pattern, Bericht, Bachelorarbeit), confidence; solution_of pairing by semester/course.
- **Rationale:** Metadata filters and KU typing.
- **Acceptance criteria:** Precision >= 0.9 on 150 labeled files (labels drafted by AI, checked by owner).
- **Validation method:** Labeled sample eval.
- **Expected artifacts:** src/sbr/registry/genre.py

### T-P2-11 — Course and abbreviation mapping
- **Phase:** P2
- **Status:** NOT_STARTED
- **Priority:** medium
- **Dependencies:** T-P2-04, T-P1-12
- **Human approval:** review
- **Description:** Seed curation/course_map.yaml from module handbook + folder abbreviations (Reg1, RGT, MSR2, GrdInf, BS1, KONleh...); map documents to courses with confidence.
- **Rationale:** Folders are cross-filed; courses are key metadata.
- **Acceptance criteria:** All level-3 folders mapped or marked unknown; owner reviews ambiguous mappings.
- **Validation method:** Owner review.
- **Expected artifacts:** curation/course_map.yaml

### T-P2-12 — Corpus audit refresh on frozen corpus
- **Phase:** P2
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P2-03, T-P2-06, T-P2-08
- **Human approval:** review
- **Description:** (Baseline: the t2 re-audit, docs/37, which is the comparison target; Q-B01 has a recommended resolution.) Re-run statistics with the production registry after Q-B01; update 03_CORPUS_AUDIT with t_final numbers and workload estimates.
- **Rationale:** Planning numbers must reflect the real corpus.
- **Acceptance criteria:** 03 updated; page and wave estimates recomputed.
- **Validation method:** Numbers reconciled with registry queries.
- **Expected artifacts:** docs/03_CORPUS_AUDIT.md (updated)

### T-P2-13 — Display-name repair for mojibake paths
- **Phase:** P2
- **Status:** NOT_STARTED
- **Priority:** low
- **Dependencies:** T-P2-01
- **Human approval:** none
- **Description:** Detect CP437/Latin-1 mojibake in names; store repaired display name; original path untouched.
- **Rationale:** Readable citations.
- **Acceptance criteria:** 228 known cases repaired correctly on sample.
- **Validation method:** Unit tests with known pairs.
- **Expected artifacts:** src/sbr/registry/names.py

### T-P2-14 — Manifest report command
- **Phase:** P2
- **Status:** NOT_STARTED
- **Priority:** medium
- **Dependencies:** T-P2-06, T-P2-04
- **Human approval:** none
- **Description:** `sbr report manifest` producing counts by class, genre, course, duplicates, sensitivity, archives (Markdown + CSV) per spec 31.
- **Rationale:** Transparency of the registry.
- **Acceptance criteria:** Report generated; matches DB queries.
- **Validation method:** Snapshot test on fixtures.
- **Expected artifacts:** src/sbr/reports/manifest.py

## P3 — Gold Set & Extraction Spikes (decision gate)

### T-P3-01 — Select MBI-Gold-Extract sample set
- **Phase:** P3
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P2-06, T-P2-10
- **Human approval:** review
- **Traces to:** HC-05
- **Description:** Stratified selection (~120 pages) from canonical blobs across producers, genres, domains, scanned/annotated/slides/tables/diagrams; stored as blob+page references.
- **Rationale:** Spikes need representative gold data.
- **Acceptance criteria:** Coverage matrix filled; owner approves list.
- **Validation method:** Selection script reproducible (seeded).
- **Expected artifacts:** eval/gold/extract_sample.yaml

### T-P3-02 — Build MBI-Gold-Math (~300 equations)
- **Phase:** P3
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P3-01
- **Human approval:** required
- **Description:** AI-drafted LaTeX per equation crop + side-by-side verification tool (crop vs KaTeX render); thesis OMML used as exact ground truth where aligned.
- **Rationale:** Math is the hard requirement; needs ground truth.
- **Acceptance criteria:** ≥300 equations verified; each has crop, LaTeX, source kind, difficulty tag.
- **Validation method:** Owner verification log; double-check 10%.
- **Expected artifacts:** eval/gold/math/*, tools/gold_verify (local web page or CLI)

### T-P3-03 — Build MBI-Gold-Layout (~40 pages)
- **Phase:** P3
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P3-01
- **Human approval:** required
- **Description:** Reading order, headings, figure-caption pairs, tables for ~40 pages.
- **Rationale:** Evaluate structure/figures/tables.
- **Acceptance criteria:** 40 pages labeled and verified.
- **Validation method:** Owner verification.
- **Expected artifacts:** eval/gold/layout/*

### T-P3-04 — Extraction evaluation harness
- **Phase:** P3
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P3-01, T-P1-05
- **Human approval:** none
- **Description:** Metrics: text CER, reading order, formula normalized-exact/edit/render-compare, false-confidence rate, TEDS, figure-caption F1; timing and RAM capture.
- **Rationale:** Objective engine comparison.
- **Acceptance criteria:** Harness runs on a dummy extractor and produces a report.
- **Validation method:** Unit tests for metrics.
- **Expected artifacts:** src/sbr/eval/extract/*

### T-P3-05 — SPIKE-PARSER: parser/layout comparison on CPU
- **Phase:** P3
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P3-04, T-P3-03
- **Human approval:** none
- **Spike:** SPIKE-PARSER
- **Description:** Run PyMuPDF/pypdfium2 baseline, Docling, MinerU (pipeline), PaddleOCR-VL, Marker on MBI-Gold-Extract; isolated envs.
- **Rationale:** ADR-008 cannot be decided without evidence.
- **Acceptance criteria:** Report with quality, s/page, RAM, failures, license per engine.
- **Validation method:** Harness report reviewed.
- **Expected artifacts:** eval/reports/spike_parser.md

### T-P3-06 — SPIKE-MATH: formula recognizers + validation
- **Phase:** P3
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P3-04, T-P3-02
- **Human approval:** none
- **Spike:** SPIKE-MATH
- **Description:** Compare UniRec-0.1B, PP-FormulaNet, UniMERNet, MinerU formula, Docling formula, texify, pix2tex, remote multimodal LLM on MBI-Gold-Math crops; test validators V1-V5 and calibrate confidence.
- **Rationale:** ADR-009 recognizer choice; R-01.
- **Acceptance criteria:** Accuracy by math source kind; false-confidence curve; CPU s/formula; recommended thresholds.
- **Validation method:** Report reviewed; calibration plot.
- **Expected artifacts:** eval/reports/spike_math.md

### T-P3-07 — SPIKE-OMML: Office math conversion fidelity
- **Phase:** P3
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P3-04
- **Human approval:** none
- **Spike:** SPIKE-OMML
- **Description:** (t2 scope extension, docs/37 G2: also Equation Editor 3.0 and MathType OLE objects in legacy .doc and OOXML files; 70 unique legacy .doc files carry Equation 3.0 signatures.) Convert OMML in thesis/Praxisphase/exercise DOCX/PPTX to LaTeX (pandoc and alternatives); verify rendering; test PDF<->DOCX equation alignment.
- **Rationale:** Exact math source for owner-authored docs.
- **Acceptance criteria:** ≥98% of sampled OMML equations render correctly; alignment method chosen.
- **Validation method:** Render comparison + manual review of 50.
- **Expected artifacts:** eval/reports/spike_omml.md

### T-P3-08 — SPIKE-OCR: scanned German pages
- **Phase:** P3
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P3-04
- **Human approval:** none
- **Spike:** SPIKE-OCR
- **Description:** Tesseract deu, PaddleOCR, parser-built-in OCR, remote VLM on scanned gold pages (typewriter scripts, exams); handwriting presence detection.
- **Rationale:** ADR-010.
- **Acceptance criteria:** CER per engine, speed, confidence usefulness.
- **Validation method:** Report reviewed.
- **Expected artifacts:** eval/reports/spike_ocr.md

### T-P3-09 — SPIKE-COMPUTE: throughput and cost projection
- **Phase:** P3
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P3-05, T-P3-06, T-P3-08
- **Human approval:** required
- **Spike:** SPIKE-COMPUTE
- **Description:** Project wall-clock/cost per wave for local CPU, rented GPU, cloud API options using measured speeds; privacy implications per option.
- **Rationale:** Q-B03 decision input; ADR-007 execution plan.
- **Acceptance criteria:** Table of options (time, cost, privacy) per wave; owner chooses policy.
- **Validation method:** Owner decision recorded.
- **Expected artifacts:** eval/reports/spike_compute.md

### T-P3-10 — SPIKE-FIGURE: knowledge-bearing vs decorative
- **Phase:** P3
- **Status:** NOT_STARTED
- **Priority:** medium
- **Dependencies:** T-P3-03
- **Human approval:** none
- **Spike:** SPIKE-FIGURE
- **Description:** Heuristic classifier (repetition, caption, size, vector density) evaluated on gold layout pages.
- **Rationale:** Avoid extracting decoration (mission §8).
- **Acceptance criteria:** Precision/recall reported; thresholds proposed.
- **Validation method:** Report.
- **Expected artifacts:** eval/reports/spike_figure.md

### T-P3-11 — Extraction stack decision record
- **Phase:** P3
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P3-05, T-P3-06, T-P3-07, T-P3-08, T-P3-09, T-P3-10
- **Human approval:** required
- **Description:** Update ADR-007..010 to ACCEPTED/REJECTED with evidence; define tier routing thresholds.
- **Rationale:** Gate into P4.
- **Acceptance criteria:** Decision log updated; owner approves.
- **Validation method:** Consistency check (validate_plan).
- **Expected artifacts:** docs/24_DECISION_LOG.md

## P4 — Extraction & Normalization

### T-P4-01 — DocIR schema v1
- **Phase:** P4
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P1-05
- **Human approval:** none
- **Traces to:** ADR-011,FR-08
- **Description:** Implement DocIR models (09 §2) with JSON Schema and validators.
- **Rationale:** Parser independence (ADR-011).
- **Acceptance criteria:** Schema validates fixture DocIRs; versioned.
- **Validation method:** Unit tests.
- **Expected artifacts:** src/sbr/docir/*

### T-P4-02 — Content-addressed artifact store
- **Phase:** P4
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P4-01, T-P1-09
- **Human approval:** none
- **Traces to:** PV-6
- **Description:** var/artifacts/<b3>/<extractor@ver>/ with manifests, temp+rename atomic writes, GC of orphans only via explicit command.
- **Rationale:** Append-only extraction versions (PV-6).
- **Acceptance criteria:** Interrupted writes leave no partial artifacts; two versions coexist.
- **Validation method:** TS-ART tests.
- **Expected artifacts:** src/sbr/artifacts.py

### T-P4-03 — Text-tier extractor + page quality signals
- **Phase:** P4
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P4-02, T-P3-11
- **Human approval:** none
- **Description:** Text layer blocks, fonts, spans, bboxes; per-page signals: textless, math-font density, glyph-soup ratio, drawings, images.
- **Rationale:** Cheap tier for all pages; triage input.
- **Acceptance criteria:** Runs on gold pages matching harness expectations; ≥50 pages/s/core on text PDFs (to verify).
- **Validation method:** Harness + perf test.
- **Expected artifacts:** src/sbr/extract/text_tier.py

### T-P4-04 — Page triage router
- **Phase:** P4
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P4-03
- **Human approval:** none
- **Traces to:** ADR-007
- **Description:** (t2 scope, docs/37 G4: detect presentation build-step page runs and route only the final build state to expensive tiers, keeping a page mapping; 65 PDFs / ~8.8k pages affected.) Per-page routing record (ocr/math/figure/table tiers) from signals with thresholds from T-P3-11.
- **Rationale:** ADR-007 compute control.
- **Acceptance criteria:** Routing precision/recall on gold pages ≥ agreed targets.
- **Validation method:** Harness.
- **Expected artifacts:** src/sbr/extract/triage.py

### T-P4-05 — Office extractor (DOCX/PPTX/PPSX; legacy via conversion)
- **Phase:** P4
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P4-02, T-P3-07
- **Human approval:** none
- **Traces to:** ADR-009
- **Description:** Structure + OMML->LaTeX (per SPIKE-OMML); slides with notes; legacy .doc/.ppt converted into var via LibreOffice headless.
- **Rationale:** Exact math and structure for Office docs.
- **Acceptance criteria:** Thesis DOCX yields ≥590 equations with LaTeX; slides numbered.
- **Validation method:** Tests on fixtures + thesis spot check.
- **Expected artifacts:** src/sbr/extract/office.py

### T-P4-06 — OCR tier
- **Phase:** P4
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P4-04, T-P3-11
- **Human approval:** none
- **Traces to:** FR-09
- **Description:** Chosen OCR engine on routed pages; line confidence; language deu+eng.
- **Rationale:** FR-09.
- **Acceptance criteria:** CER on gold scanned pages within spike result ±10%.
- **Validation method:** Harness.
- **Expected artifacts:** src/sbr/extract/ocr_tier.py

### T-P4-07 — Math tier with validation
- **Phase:** P4
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P4-04, T-P3-11
- **Human approval:** none
- **Traces to:** HC-05,HC-18
- **Description:** Formula detection + recognition on routed regions; readings with confidence; validators V1-V5; status verified/plausible/uncertain/failed; crops stored.
- **Rationale:** HC-05, HC-18.
- **Acceptance criteria:** Gold math accuracy and false-confidence rate within spike results; no reading marked verified below threshold.
- **Validation method:** Harness + TS-MATH tests.
- **Expected artifacts:** src/sbr/extract/math_tier.py

### T-P4-08 — Figure and table tier
- **Phase:** P4
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P4-04, T-P3-10
- **Human approval:** none
- **Traces to:** HC-06
- **Description:** Region detection, caption/label linking, knowledge-bearing filter, crops for knowledge-bearing, table structure extraction.
- **Rationale:** HC-06.
- **Acceptance criteria:** Figure-caption F1 and table TEDS within spike results.
- **Validation method:** Harness.
- **Expected artifacts:** src/sbr/extract/figure_tier.py

### T-P4-09 — Source-twin fusion (OMML into PDF context)
- **Phase:** P4
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P4-05, T-P4-03
- **Human approval:** none
- **Description:** Align Office equations to PDF pages via surrounding-text sequence alignment; attach omml_exact readings with PDF locators.
- **Rationale:** Exact math + page provenance.
- **Acceptance criteria:** ≥95% of thesis equations aligned to correct PDF page.
- **Validation method:** Manual check of 40.
- **Expected artifacts:** src/sbr/extract/twin_fusion.py

### T-P4-10 — Annotation layer extraction
- **Phase:** P4
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P4-03
- **Human approval:** none
- **Traces to:** ADR-032
- **Description:** PDF annotation objects + ink detection (saturated color strokes) as USER_ANNOTATION regions linked to nearest blocks.
- **Rationale:** ADR-032; owner knowledge.
- **Acceptance criteria:** Annotated dynamics script: annotations detected on sampled pages; no false positives on 20 clean pages.
- **Validation method:** Manual check.
- **Expected artifacts:** src/sbr/extract/annotations.py

### T-P4-11 — Logical structure inference
- **Phase:** P4
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P4-03, T-P4-05
- **Human approval:** none
- **Traces to:** FR-11
- **Description:** Section tree from styles/bookmarks/numbering/fonts; equation/figure/table labels; header/footer flagging; LLM repair fallback (budgeted).
- **Rationale:** Decomposition (FR-11).
- **Acceptance criteria:** Heading F1 on gold layout pages ≥ target; books split into chapters correctly for 10 sampled books.
- **Validation method:** Harness + manual.
- **Expected artifacts:** src/sbr/extract/structure.py

### T-P4-12 — Normalized Markdown renderer
- **Phase:** P4
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P4-11, T-P4-07, T-P4-08
- **Human approval:** none
- **Traces to:** FR-10
- **Description:** DocIR -> Obsidian Markdown per 09 §5 incl. decomposition policy, anchors, uncertainty callouts, figure embeds.
- **Rationale:** FR-10.
- **Acceptance criteria:** Rendered notes open cleanly in Obsidian; LaTeX renders; anchors resolve; snapshot tests.
- **Validation method:** Snapshot tests + manual Obsidian check.
- **Expected artifacts:** src/sbr/normalize/markdown.py

### T-P4-13 — VaultWriter v1 (ownership protection)
- **Phase:** P4
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P1-07, T-P1-12
- **Human approval:** required
- **Traces to:** HC-07,HC-08,ADR-014
- **Description:** Atomic writes, ownership rules (19 §2), content-hash edit detection, fork behavior, no writes to notes/, version commit per batch (git if ADR-015 is accepted; otherwise an internal version table).
- **Rationale:** HC-07/HC-08.
- **Acceptance criteria:** All TS-VAULT tests pass (edit detection, fork, notes/ untouched, dirty-tree abort); owner approves vault location (Q-B02).
- **Validation method:** TS-VAULT tests.
- **Expected artifacts:** src/sbr/vault/writer.py

### T-P4-14 — Uncertainty and reprocessing queue
- **Phase:** P4
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P4-07, T-P4-02
- **Human approval:** none
- **Traces to:** HC-18
- **Description:** Lists and re-enqueues items below thresholds; `sbr reprocess --stage X --where ...`; new versions, never in-place.
- **Rationale:** HC-18 and recovery.
- **Acceptance criteria:** Reprocessing creates a new artifact version and leaves the old one intact.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/extract/reprocess.py

### T-P4-15 — Pilot wave W0 end-to-end
- **Phase:** P4
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P4-12, T-P4-13, T-P4-09, T-P4-10, T-P4-06, T-P4-14
- **Human approval:** required
- **Description:** Process thesis (+twins), Regelungstechnik 1 canonical docs, one scanned Statik script; owner reviews 20 random outputs.
- **Rationale:** Validate the whole extraction chain on real material.
- **Acceptance criteria:** Owner acceptance; quality report; timings recorded for wave planning.
- **Validation method:** Owner review + harness.
- **Expected artifacts:** reports/pilot_w0.md

### T-P4-16 — Extraction quality report per document
- **Phase:** P4
- **Status:** NOT_STARTED
- **Priority:** medium
- **Dependencies:** T-P4-15
- **Human approval:** none
- **Description:** `sbr report quality` with per-document confidence histograms, math status counts, OCR confidence.
- **Rationale:** Visible uncertainty.
- **Acceptance criteria:** Report generated for W0.
- **Validation method:** Snapshot test.
- **Expected artifacts:** src/sbr/reports/quality.py

## P5 — Knowledge Units, Near-Dedup & Taxonomy

### T-P5-01 — Knowledge Unit segmentation
- **Phase:** P5
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P4-15
- **Human approval:** none
- **Traces to:** FR-12,ADR-012
- **Description:** KU types and boundaries (14 §2) from DocIR; derivation grouping; parent section paths; bilingual cue lists; LLM boundary check for ambiguous long sections (budgeted).
- **Rationale:** Citation unit (ADR-012).
- **Acceptance criteria:** KU boundary F1 on 30 labeled sections ≥ target; every block belongs to exactly one KU.
- **Validation method:** Labeled sample eval.
- **Expected artifacts:** src/sbr/knowledge/segment.py

### T-P5-02 — Symbol definitions and equation context links
- **Phase:** P5
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P5-01
- **Human approval:** none
- **Traces to:** FR-13
- **Description:** Extract SymbolDefinitions from wobei/mit/where patterns + LLM assist; attach to equations; build equation context packs.
- **Rationale:** FR-13; equations never retrieved without meaning.
- **Acceptance criteria:** Precision ≥ 0.85 on 100 sampled symbol links.
- **Validation method:** Sample eval.
- **Expected artifacts:** src/sbr/knowledge/symbols.py

### T-P5-03 — Near-duplicate, version and containment detection
- **Phase:** P5
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P5-01, T-P4-10
- **Human approval:** none
- **Traces to:** FR-06,ADR-032
- **Description:** (t2 scope: includes intra-document near-duplicate pages from presentation build steps.) MinHash/LSH over normalized page text; version chains (semester tokens); containment; annotated-variant rule; canonical representative.
- **Rationale:** FR-06, R-03, R-04.
- **Acceptance criteria:** Precision/recall on 100 labeled pairs; zero annotated variants collapsed.
- **Validation method:** Labeled pair eval + hard test.
- **Expected artifacts:** src/sbr/knowledge/neardup.py

### T-P5-04 — Twin confirmation
- **Phase:** P5
- **Status:** NOT_STARTED
- **Priority:** medium
- **Dependencies:** T-P5-03, T-P2-09
- **Human approval:** none
- **Description:** Confirm twin candidates via text similarity; promote to twin_of relations.
- **Rationale:** Correct twin fusion.
- **Acceptance criteria:** Precision ≥ 0.95 on candidates.
- **Validation method:** Sample check.
- **Expected artifacts:** src/sbr/knowledge/twins.py

### T-P5-05 — Stable KU anchors and re-extraction alignment
- **Phase:** P5
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P5-01
- **Human approval:** none
- **Traces to:** PV-7
- **Description:** Anchors per 05 §6; alignment old->new; same/revised/split/merged/removed mapping; tombstones.
- **Rationale:** Citation drift (R-15).
- **Acceptance criteria:** Re-running segmentation with a perturbed parser version keeps ≥95% anchors stable on pilot docs.
- **Validation method:** TS-ANCHOR tests.
- **Expected artifacts:** src/sbr/knowledge/anchors.py

### T-P5-06 — Taxonomy v0
- **Phase:** P5
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P2-11, T-P1-12
- **Human approval:** required
- **Traces to:** FR-15,HC-14
- **Description:** Seed SKOS-like taxonomy from module handbook, curriculum, folder map; bilingual labels; stored in curation/taxonomy.yaml.
- **Rationale:** FR-15; knowledge organization independent of folders.
- **Acceptance criteria:** Owner approves v0; every course maps to ≥1 domain.
- **Validation method:** Owner review.
- **Expected artifacts:** curation/taxonomy.yaml

### T-P5-07 — Document/KU topic classification
- **Phase:** P5
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P5-06, T-P5-01
- **Human approval:** none
- **Description:** Multi-label assignment of documents and KUs to taxonomy nodes (rules + LLM), confidence.
- **Rationale:** Filters, maps, coverage.
- **Acceptance criteria:** Precision ≥ 0.85 on 100 labeled items.
- **Validation method:** Sample eval.
- **Expected artifacts:** src/sbr/knowledge/classify_topics.py

### T-P5-08 — Concept candidate extraction v0
- **Phase:** P5
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P5-01
- **Human approval:** none
- **Description:** Term and named-concept candidates with bilingual normalization and span evidence; feeds P8.
- **Rationale:** Graph input.
- **Acceptance criteria:** Candidate list for pilot docs; precision sampled.
- **Validation method:** Sample eval.
- **Expected artifacts:** src/sbr/knowledge/concepts.py

### T-P5-09 — Reference extraction and matching
- **Phase:** P5
- **Status:** NOT_STARTED
- **Priority:** medium
- **Dependencies:** T-P4-11
- **Human approval:** none
- **Traces to:** FR-14
- **Description:** Parse bibliography sections and in-text citations; match to corpus documents (title fuzzy, ISBN in filename).
- **Rationale:** Mission §12 citation graph.
- **Acceptance criteria:** Matches on 20 documents with bibliographies manually verified.
- **Validation method:** Sample check.
- **Expected artifacts:** src/sbr/knowledge/references.py

## P6 — Retrieval Infrastructure

### T-P6-01 — MBI-Retrieval gold set
- **Phase:** P6
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P5-01, T-P5-07
- **Human approval:** required
- **Description:** ~150 queries across types (13/20) generated from KUs + owner review; pooled relevance judgments.
- **Rationale:** All retrieval spikes need it.
- **Acceptance criteria:** 150 queries with judgments; owner approved.
- **Validation method:** Owner review.
- **Expected artifacts:** eval/gold/retrieval/*

### T-P6-02 — Retrieval evaluation harness
- **Phase:** P6
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P6-01
- **Human approval:** none
- **Description:** ranx-based metrics by query type; ablation configs; reports.
- **Rationale:** Measure everything.
- **Acceptance criteria:** Harness evaluates a trivial BM25 baseline.
- **Validation method:** Unit tests.
- **Expected artifacts:** src/sbr/eval/retrieval/*

### T-P6-03 — Chunk view builder
- **Phase:** P6
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P5-01, T-P5-02
- **Human approval:** none
- **Traces to:** HC-13
- **Description:** Build text/equation_card/figure_card/table views with contextual headers; versioned chunk policy.
- **Rationale:** Retrieval inputs.
- **Acceptance criteria:** Views built for pilot docs; policy hash recorded.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/index/chunks.py

### T-P6-04 — SPIKE-EMBED: embedding models on CPU
- **Phase:** P6
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P6-02, T-P6-03
- **Human approval:** none
- **Spike:** SPIKE-EMBED
- **Description:** Qwen3-Embedding-0.6B, BGE-M3, mE5-large-instruct, EmbeddingGemma-300m (+license-checked others): quality on MBI-Retrieval, cross-lingual subset, throughput, RAM.
- **Rationale:** ADR-017, ADR-027.
- **Acceptance criteria:** Report with recommendation.
- **Validation method:** Harness report.
- **Expected artifacts:** eval/reports/spike_embed.md

### T-P6-05 — SPIKE-HYBRID: lexical engines + fusion
- **Phase:** P6
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P6-02, T-P6-03
- **Human approval:** none
- **Spike:** SPIKE-HYBRID
- **Description:** Tantivy vs FTS5 vs Lance FTS with German stemming/decompounding + abbreviation expansion; dense vs BM25 vs hybrid RRF; LanceDB integration check.
- **Rationale:** ADR-016, ADR-018.
- **Acceptance criteria:** Report; chosen engines and fusion weights.
- **Validation method:** Harness report.
- **Expected artifacts:** eval/reports/spike_hybrid.md

### T-P6-06 — SPIKE-CHUNK: chunking strategies
- **Phase:** P6
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P6-04, T-P6-05
- **Human approval:** none
- **Spike:** SPIKE-CHUNK
- **Description:** Compare C1-C5 (14 §4) and caps {256,512,1024}.
- **Rationale:** No arbitrary chunk sizes.
- **Acceptance criteria:** Report; chosen policy.
- **Validation method:** Harness report.
- **Expected artifacts:** eval/reports/spike_chunk.md

### T-P6-07 — Embedding pipeline with versioned EmbeddingSets
- **Phase:** P6
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P6-04, T-P1-09
- **Human approval:** none
- **Traces to:** NFR-05
- **Description:** Resumable batch embedding; set = (model, version, chunk policy); coexisting sets; config switch.
- **Rationale:** NFR-05.
- **Acceptance criteria:** Two sets coexist; switching changes results without rebuild of KUs.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/index/embed.py

### T-P6-08 — Lexical and vector index integration
- **Phase:** P6
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P6-05, T-P6-07
- **Human approval:** none
- **Description:** Build chosen lexical index and vector store with metadata filters (course, genre, provenance, sensitivity).
- **Rationale:** FR-16.
- **Acceptance criteria:** Indexes rebuildable from knowledge DB; filter tests pass.
- **Validation method:** Tests + rebuild test.
- **Expected artifacts:** src/sbr/index/*

### T-P6-09 — Math index + SPIKE-MATHRET
- **Phase:** P6
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P5-02, T-P6-02
- **Human approval:** none
- **Spike:** SPIKE-MATHRET
- **Description:** latex_normalized tokenization, structural n-grams, equation-card vectors; evaluate on equation queries.
- **Rationale:** Mission §30.
- **Acceptance criteria:** Report; math retrieval enabled if gain.
- **Validation method:** Harness report.
- **Expected artifacts:** src/sbr/index/math_index.py, eval/reports/spike_mathret.md

### T-P6-10 — Fusion and dedup collapse
- **Phase:** P6
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P6-08
- **Human approval:** none
- **Description:** RRF with per-type weights; collapse duplicate/version groups; keep annotated variants.
- **Rationale:** R-03.
- **Acceptance criteria:** Duplicate rate in top-10 ≤ 5% on gold set.
- **Validation method:** Harness.
- **Expected artifacts:** src/sbr/retrieve/fusion.py

### T-P6-11 — SPIKE-RERANK: reranker value on CPU
- **Phase:** P6
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P6-10
- **Human approval:** none
- **Spike:** SPIKE-RERANK
- **Description:** bge-reranker-v2-m3, Qwen3-Reranker-0.6B, LLM rerank: ΔnDCG vs latency.
- **Rationale:** ADR-019.
- **Acceptance criteria:** Report; enable/disable decision per gate.
- **Validation method:** Harness report.
- **Expected artifacts:** eval/reports/spike_rerank.md

### T-P6-12 — Evidence pack builder
- **Phase:** P6
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P6-10, T-P5-02
- **Human approval:** none
- **Description:** Parent expansion, equation context rule, exercise<->solution pulls, figure cards, token budget, diversity.
- **Rationale:** Mission §31.
- **Acceptance criteria:** Packs for gold queries include required context in ≥95% cases.
- **Validation method:** Tests + sample check.
- **Expected artifacts:** src/sbr/retrieve/evidence.py

### T-P6-13 — Retrieval API and `sbr search`
- **Phase:** P6
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P6-12
- **Human approval:** none
- **Description:** Python API + CLI with filters and provenance display.
- **Rationale:** Usable retrieval.
- **Acceptance criteria:** CLI returns cited hits with locators.
- **Validation method:** CLI tests.
- **Expected artifacts:** src/sbr/retrieve/api.py

## P7 — Baseline Grounded QA

### T-P7-01 — Model gateway
- **Phase:** P7
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P7-02, T-P1-02
- **Human approval:** none
- **Traces to:** ADR-025,HC-20,ADR-035
- **Description:** Role routing, adapters, fallbacks, sensitivity gate, accounting, response cache, structured outputs.
- **Rationale:** ADR-025, HC-20.
- **Acceptance criteria:** Fake-model tests; sensitivity gate blocks remote calls for restricted docs; cost logged.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/models/*

### T-P7-02 — SPIKE-MODELGW: access to OpenCode-configured models
- **Phase:** P7
- **Status:** BLOCKED
- **Priority:** critical
- **Dependencies:** T-P0-08
- **Human approval:** none
- **Spike:** SPIKE-MODELGW
- **Description:** Determine programmatic access (direct provider keys, OpenCode server API, Zen gateway); evaluate LiteLLM vs thin adapters.
- **Rationale:** ADR-026; Q-B04.
- **Acceptance criteria:** Working call to ≥2 roles' models from Python; recommendation.
- **Validation method:** Spike report.
- **Expected artifacts:** eval/reports/spike_modelgw.md
- **Blocked by:** Q-B04 (model access and credentials are owner decisions; recorded 2026-09-24 when T-P0-08 made the task dependency-eligible).

### T-P7-03 — Answer schema with knowledge-layer basis
- **Phase:** P7
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P1-05
- **Human approval:** none
- **Traces to:** HC-11,ADR-034
- **Description:** AnswerSegment{text, basis, citations[]}; rendering rules for labels.
- **Rationale:** HC-11, ADR-034.
- **Acceptance criteria:** Schema + renderer tests.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/answer/schema.py

### T-P7-04 — Baseline grounded RAG pipeline
- **Phase:** P7
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P7-01, T-P7-03, T-P6-13
- **Human approval:** none
- **Traces to:** FR-17
- **Description:** Query -> hybrid retrieval -> evidence pack -> synthesis with schema (no agentic loop).
- **Rationale:** Baseline for all later comparisons (R-26).
- **Acceptance criteria:** Answers produced for MBI-QA with citations.
- **Validation method:** Eval in T-P7-07.
- **Expected artifacts:** src/sbr/answer/baseline.py

### T-P7-05 — Grounding validator
- **Phase:** P7
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P7-04
- **Human approval:** none
- **Traces to:** HC-11,HC-17
- **Description:** Deterministic citation existence + quote match; entailment judge (judge role ≠ generator); relabel/drop unsupported; report.
- **Rationale:** HC-11, HC-17.
- **Acceptance criteria:** Unsupported-claim injection tests caught ≥95%.
- **Validation method:** TS-GROUND tests + eval.
- **Expected artifacts:** src/sbr/answer/validate.py

### T-P7-06 — Citation rendering and deep links
- **Phase:** P7
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P7-04
- **Human approval:** none
- **Description:** Human citations with page labels, Obsidian anchors, file path#page.
- **Rationale:** Traceability UX.
- **Acceptance criteria:** Links open correct page/anchor on samples.
- **Validation method:** Manual check.
- **Expected artifacts:** src/sbr/answer/cite.py

### T-P7-07 — MBI-QA gold set and QA evaluation
- **Phase:** P7
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P7-05
- **Human approval:** required
- **Description:** ~50 questions incl. not-in-corpus; metrics: citation precision/recall, faithfulness, layer-label accuracy.
- **Rationale:** Evaluation from the beginning.
- **Acceptance criteria:** Baseline scores recorded.
- **Validation method:** Eval report.
- **Expected artifacts:** eval/gold/qa/*, eval/reports/qa_baseline.md

### T-P7-08 — `sbr ask` CLI with trace output
- **Phase:** P7
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P7-05, T-P7-06
- **Human approval:** none
- **Description:** CLI for questions with labeled, cited answers; `--trace` flag.
- **Rationale:** Usable system.
- **Acceptance criteria:** CLI answers gold questions; trace saved.
- **Validation method:** CLI tests.
- **Expected artifacts:** src/sbr/cli/ask.py

## P8 — Knowledge Graph

### T-P8-01 — Graph schema and storage
- **Phase:** P8
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P5-08
- **Human approval:** none
- **Traces to:** ADR-020
- **Description:** nodes/edges tables with evidence, status, confidence, producer; NetworkX/igraph loader; GraphML export.
- **Rationale:** ADR-020.
- **Acceptance criteria:** Load 1M synthetic edges < target time/RAM; schema tests.
- **Validation method:** Tests + perf test.
- **Expected artifacts:** src/sbr/graph/store.py

### T-P8-02 — Structural edges (deterministic)
- **Phase:** P8
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P8-01, T-P5-03, T-P5-09
- **Human approval:** none
- **Description:** Section/KU containment, course/domain, duplicate/version/twin/annotated, solution_of, cites.
- **Rationale:** Cheap, reliable backbone.
- **Acceptance criteria:** Edges built for pilot; counts match registry.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/graph/structural.py

### T-P8-03 — Concept normalization and entity resolution
- **Phase:** P8
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P8-01, T-P5-08
- **Human approval:** review
- **Description:** Canonical concepts with DE/EN labels and aliases; merge candidates; curation via ledger.
- **Rationale:** Graph quality.
- **Acceptance criteria:** Merge precision ≥ 0.9 on sample; owner reviews top merges.
- **Validation method:** Sample eval.
- **Expected artifacts:** src/sbr/graph/concepts.py

### T-P8-04 — Relation extraction with evidence
- **Phase:** P8
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P8-03, T-P7-01
- **Human approval:** none
- **Traces to:** FR-18
- **Description:** LLM + rules produce typed relations with evidence spans; cost-bounded to canonical docs; dry-run cost estimate.
- **Rationale:** FR-18.
- **Acceptance criteria:** Every edge has resolvable evidence; cost within budget.
- **Validation method:** Tests + sample.
- **Expected artifacts:** src/sbr/graph/relations.py

### T-P8-05 — Graph quality gate
- **Phase:** P8
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P8-04
- **Human approval:** review
- **Description:** Sample 200 edges; judge + owner spot check; precision per type; hallucination checks.
- **Rationale:** R-05/R-06.
- **Acceptance criteria:** Precision ≥ target for validated edges or fixes applied.
- **Validation method:** Report.
- **Expected artifacts:** eval/reports/graph_quality.md

### T-P8-06 — SPIKE-GRAPH: graph-augmented retrieval
- **Phase:** P8
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P8-05, T-P6-12
- **Human approval:** none
- **Spike:** SPIKE-GRAPH
- **Description:** PPR/neighborhood expansion (HippoRAG-style) vs baseline on MultiHop subset + retrieval gold.
- **Rationale:** Enable only if useful.
- **Acceptance criteria:** Report and gate decision.
- **Validation method:** Harness report.
- **Expected artifacts:** eval/reports/spike_graph.md

### T-P8-07 — SPIKE-GRAPHIFY
- **Phase:** P8
- **Status:** NOT_STARTED
- **Priority:** medium
- **Dependencies:** T-P4-15
- **Human approval:** none
- **Spike:** SPIKE-GRAPHIFY
- **Description:** Run Graphify on normalized Regelungstechnik subset; compare edge precision, usefulness, cost vs own graph.
- **Rationale:** ADR-021.
- **Acceptance criteria:** Report; ADR-021 updated.
- **Validation method:** Report.
- **Expected artifacts:** eval/reports/spike_graphify.md

### T-P8-08 — Graph retrieval tool integration
- **Phase:** P8
- **Status:** NOT_STARTED
- **Priority:** medium
- **Dependencies:** T-P8-06
- **Human approval:** none
- **Description:** expand_graph tool for retrieval/orchestrator when the gate passed.
- **Rationale:** FR-16.
- **Acceptance criteria:** Tool tests; retrieval metrics unchanged or improved.
- **Validation method:** Harness.
- **Expected artifacts:** src/sbr/retrieve/graph_expand.py

### T-P8-09 — Graph export to Obsidian links
- **Phase:** P8
- **Status:** NOT_STARTED
- **Priority:** medium
- **Dependencies:** T-P8-05, T-P4-13
- **Human approval:** none
- **Description:** Validated edges rendered as links/sections in concept notes via VaultWriter.
- **Rationale:** Human navigation.
- **Acceptance criteria:** Links present and valid in pilot vault.
- **Validation method:** Manual check.
- **Expected artifacts:** src/sbr/graph/export.py

## P9 — Agentic Orchestration

### T-P9-01 — SPIKE-AGENTFW: orchestration framework
- **Phase:** P9
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P7-04
- **Human approval:** none
- **Spike:** SPIKE-AGENTFW
- **Description:** Prototype orchestrator loop in custom state machine vs LangGraph vs Pydantic AI; durable checkpoint + interrupt + tracing + testability.
- **Rationale:** ADR-024.
- **Acceptance criteria:** Report + decision.
- **Validation method:** Spike report.
- **Expected artifacts:** eval/reports/spike_agentfw.md

### T-P9-02 — Trace store and viewer
- **Phase:** P9
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P1-08
- **Human approval:** none
- **Traces to:** HC-23
- **Description:** Span model for nodes/tools/model calls; SQLite storage; `sbr trace`; optional OTel export.
- **Rationale:** HC-23.
- **Acceptance criteria:** Trace of a run fully reconstructable.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/obs/trace.py

### T-P9-03 — Orchestrator state machine
- **Phase:** P9
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P9-01, T-P9-02, T-P7-05
- **Human approval:** none
- **Traces to:** FR-19
- **Description:** States/transitions per 07 §3 with budgets and stop conditions; persisted runs.
- **Rationale:** FR-19.
- **Acceptance criteria:** Deterministic tests with fake models cover all transitions and stop reasons.
- **Validation method:** TS-AGENT tests.
- **Expected artifacts:** src/sbr/agent/orchestrator.py

### T-P9-04 — Query understanding and decomposition
- **Phase:** P9
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P9-03
- **Human approval:** none
- **Description:** Structured QueryPlan output; language, domains, sub-questions, needs_math/visual.
- **Rationale:** Planning quality.
- **Acceptance criteria:** Plan accuracy on 40 labeled queries ≥ target.
- **Validation method:** Sample eval.
- **Expected artifacts:** src/sbr/agent/plan.py

### T-P9-05 — Retrieval router
- **Phase:** P9
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P9-04, T-P6-13
- **Human approval:** none
- **Description:** Rule table + LLM hints to choose retrieval strategies per sub-question.
- **Rationale:** Adaptive retrieval.
- **Acceptance criteria:** Router beats fixed hybrid on routed query types or is disabled.
- **Validation method:** Harness.
- **Expected artifacts:** src/sbr/agent/route.py

### T-P9-06 — Evidence sufficiency judge
- **Phase:** P9
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P9-03
- **Human approval:** none
- **Description:** Rubric-based coverage per sub-question; novelty check; loop control.
- **Rationale:** Stopping conditions.
- **Acceptance criteria:** Judge agreement with owner labels ≥ target on 40 cases.
- **Validation method:** Sample eval.
- **Expected artifacts:** src/sbr/agent/judge.py

### T-P9-07 — Conflict analyzer
- **Phase:** P9
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P9-03
- **Human approval:** none
- **Traces to:** FR-25
- **Description:** Detect contradictions (same concept/equation, differing claims), analyze assumptions/versions, create Conflict records; never drop evidence.
- **Rationale:** FR-25.
- **Acceptance criteria:** Recall on constructed contradictions ≥ target; no-erasure test.
- **Validation method:** TS-CONFLICT tests.
- **Expected artifacts:** src/sbr/agent/conflicts.py

### T-P9-08 — On-demand visual inspection tool
- **Phase:** P9
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P7-01, T-P4-08
- **Human approval:** none
- **Traces to:** FR-20
- **Description:** Render region/page, ask vision role, cache as AI_GENERATED artifact with provenance.
- **Rationale:** FR-20.
- **Acceptance criteria:** Tool returns cached result on repeat; provenance recorded.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/agent/tools/visual.py

### T-P9-09 — SPIKE-MULTIMODAL: value of visual inspection
- **Phase:** P9
- **Status:** NOT_STARTED
- **Priority:** medium
- **Dependencies:** T-P9-08, T-P7-07
- **Human approval:** none
- **Spike:** SPIKE-MULTIMODAL
- **Description:** Measure answer gains on figure-bound and uncertain-math questions vs cost.
- **Rationale:** Decide triggers.
- **Acceptance criteria:** Report and trigger thresholds.
- **Validation method:** Harness report.
- **Expected artifacts:** eval/reports/spike_multimodal.md

### T-P9-10 — JIT extraction upgrade
- **Phase:** P9
- **Status:** NOT_STARTED
- **Priority:** medium
- **Dependencies:** T-P9-03, T-P4-14
- **Human approval:** none
- **Traces to:** ADR-007
- **Description:** When evidence has uncertain math/figures, enqueue higher-tier extraction for those pages (policy-bounded).
- **Rationale:** ADR-007 lazy upgrade.
- **Acceptance criteria:** Upgrade enqueued and reflected in later answers.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/agent/jit.py

### T-P9-11 — MBI-MultiHop set and agentic evaluation
- **Phase:** P9
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P9-06, T-P9-07, T-P9-05
- **Human approval:** required
- **Description:** ~40 cross-domain questions; compare orchestrator vs baseline on quality, grounding, cost, latency.
- **Rationale:** Justify agentic complexity.
- **Acceptance criteria:** Orchestrator ≥ baseline on MultiHop without QA regression.
- **Validation method:** Eval report.
- **Expected artifacts:** eval/gold/multihop/*, eval/reports/agentic.md

## P10 — Obsidian Curation & Living Knowledge

### T-P10-01 — Vault layout and conventions finalization
- **Phase:** P10
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P4-15
- **Human approval:** required
- **Description:** Finalize folders, frontmatter, naming, link style, callouts (19); owner approval.
- **Rationale:** Human interface quality.
- **Acceptance criteria:** Owner approves conventions document.
- **Validation method:** Owner review.
- **Expected artifacts:** docs/19_OBSIDIAN_INTEGRATION.md (final)

### T-P10-02 — User note ingestion
- **Phase:** P10
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P10-01, T-P5-01
- **Human approval:** none
- **Traces to:** HC-07,FR-21
- **Description:** Vault scanner for USER_AUTHORED notes; KUs; links as curated edges; change detection.
- **Rationale:** HC-07, FR-21.
- **Acceptance criteria:** User notes retrievable and cited as USER basis; edits re-indexed.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/vault/scan.py

### T-P10-03 — AI synthesis note generator
- **Phase:** P10
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P10-01, T-P7-05
- **Human approval:** none
- **Traces to:** HC-09,HC-19,FR-22
- **Description:** Cited synthesis notes with provenance, basis labels, input fingerprints, git history.
- **Rationale:** FR-22, HC-09, HC-19.
- **Acceptance criteria:** Notes validate (all CORPUS claims cited); regeneration creates new version.
- **Validation method:** Tests + sample review.
- **Expected artifacts:** src/sbr/curate/ai_notes.py

### T-P10-04 — Concept notes
- **Phase:** P10
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P10-03, T-P8-05
- **Human approval:** none
- **Description:** One note per curated concept with definitions, equations, sources, relations.
- **Rationale:** Obsidian navigation.
- **Acceptance criteria:** Concept notes for pilot domain; links valid.
- **Validation method:** Sample review.
- **Expected artifacts:** src/sbr/curate/concept_notes.py

### T-P10-05 — Living domain maps
- **Phase:** P10
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P10-04, T-P8-05
- **Human approval:** review
- **Description:** Maps with required sections (19 §5) incl. owner section preservation; incremental update. Gap/strength sections are filled by T-P11-04.
- **Rationale:** Mission §18.
- **Acceptance criteria:** Map for Control Engineering generated and reviewed.
- **Validation method:** Owner review.
- **Expected artifacts:** src/sbr/curate/maps.py

### T-P10-06 — Staleness tracking and refresh
- **Phase:** P10
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P10-03, T-P5-05
- **Human approval:** none
- **Description:** Input fingerprints; stale marking; refresh queue with budget.
- **Rationale:** R-16.
- **Acceptance criteria:** Changing a cited KU marks dependent notes stale.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/curate/staleness.py

### T-P10-07 — Edit-conflict handling tests and UX
- **Phase:** P10
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P4-13, T-P10-03
- **Human approval:** none
- **Traces to:** HC-08
- **Description:** End-to-end tests: owner edits generated note -> fork; banners; review queue entries.
- **Rationale:** HC-08.
- **Acceptance criteria:** All scenarios pass.
- **Validation method:** TS-VAULT e2e.
- **Expected artifacts:** tests/vault/*

### T-P10-08 — Review queues in the vault
- **Phase:** P10
- **Status:** NOT_STARTED
- **Priority:** low
- **Dependencies:** T-P10-01
- **Human approval:** none
- **Description:** inbox/review notes (uncertain equations, merges, proposals); optional Dataview/Bases views.
- **Rationale:** Owner workflow.
- **Acceptance criteria:** Queues rendered and actionable via frontmatter status.
- **Validation method:** Manual check.
- **Expected artifacts:** src/sbr/vault/queues.py

## P11 — Gap Analysis

### T-P11-01 — Domain reference models
- **Phase:** P11
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P5-06, T-P7-01
- **Human approval:** required
- **Description:** Per domain: required concepts, prerequisites, importance, modern developments (MODEL-derived, labeled), owner review.
- **Rationale:** Gap baseline (15).
- **Acceptance criteria:** Reference models for 3 pilot domains approved.
- **Validation method:** Owner review.
- **Expected artifacts:** curation/reference_models/*.yaml

### T-P11-02 — Coverage scoring
- **Phase:** P11
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P11-01, T-P8-03, T-P5-07
- **Human approval:** none
- **Description:** Transparent coverage formula with evidence lists (15 §2).
- **Rationale:** Explainable strength.
- **Acceptance criteria:** Scores reproducible; each score lists evidence.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/gaps/coverage.py

### T-P11-03 — Gap classifier
- **Phase:** P11
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P11-02
- **Human approval:** none
- **Traces to:** FR-23
- **Description:** Gap types per 15 §3 with evidence of absence/weakness.
- **Rationale:** FR-23.
- **Acceptance criteria:** Gap records for pilot domains.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/gaps/classify.py

### T-P11-04 — Gap reports and 'What do I know about X?'
- **Phase:** P11
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P11-03, T-P10-05
- **Human approval:** review
- **Description:** Domain gap sections in maps; CLI/agent answer with labeled layers.
- **Rationale:** Mission §25.
- **Acceptance criteria:** Report for robotics reviewed by owner.
- **Validation method:** Owner review.
- **Expected artifacts:** src/sbr/gaps/report.py

### T-P11-05 — Seeded-gap evaluation
- **Phase:** P11
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P11-03
- **Human approval:** none
- **Description:** Hide document sets to create known gaps; measure precision/recall.
- **Rationale:** Validate gap detection.
- **Acceptance criteria:** Metrics recorded; thresholds tuned.
- **Validation method:** Eval report.
- **Expected artifacts:** eval/reports/gaps.md

## P12 — External Research & Approval

### T-P12-01 — Research workflow (durable) with approval interrupt
- **Phase:** P12
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P9-01, T-P11-03
- **Human approval:** none
- **Traces to:** FR-24
- **Description:** States per 16 §1; checkpoints; budgets; resume.
- **Rationale:** FR-24.
- **Acceptance criteria:** Crash-resume test; waits for approval without holding resources.
- **Validation method:** TS-RESEARCH tests.
- **Expected artifacts:** src/sbr/research/workflow.py

### T-P12-02 — Research tools
- **Phase:** P12
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P12-01
- **Human approval:** none
- **Description:** web search, fetch (limits), arXiv/OpenAlex/Semantic Scholar, YouTube transcripts, quarantine store.
- **Rationale:** Evidence collection.
- **Acceptance criteria:** Tools tested with recorded fixtures.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/research/tools/*

### T-P12-03 — Source evaluator
- **Phase:** P12
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P12-02
- **Human approval:** none
- **Description:** Authority/recency/relevance rubric; snippet-not-knowledge rule.
- **Rationale:** Research quality.
- **Acceptance criteria:** Rubric agreement with owner on 30 sources ≥ target.
- **Validation method:** Sample eval.
- **Expected artifacts:** src/sbr/research/evaluate.py

### T-P12-04 — ResearchProposal format and approval handling
- **Phase:** P12
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P12-01, T-P10-01
- **Human approval:** required
- **Traces to:** HC-10,ADR-028
- **Description:** Proposal notes in inbox; approve/reject via frontmatter or CLI; ledger entries.
- **Rationale:** HC-10.
- **Acceptance criteria:** Approval and rejection paths recorded in ledger.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/research/proposal.py

### T-P12-05 — Approved-knowledge ingestion
- **Phase:** P12
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P12-04, T-P4-15
- **Human approval:** none
- **Description:** Approved sources to accepted-external root -> normal pipeline with EXTERNAL_RESEARCH provenance.
- **Rationale:** Growth path.
- **Acceptance criteria:** Approved source searchable with correct basis label.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/research/ingest.py

### T-P12-06 — Contamination guards
- **Phase:** P12
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P12-05, T-P6-08
- **Human approval:** none
- **Traces to:** PV-4
- **Description:** Pending index separation; tests that pending content never appears in ask evidence.
- **Rationale:** R-17, PV-4.
- **Acceptance criteria:** TS-PROV-3 passes.
- **Validation method:** Tests.
- **Expected artifacts:** tests/provenance/test_pending_isolation.py

### T-P12-07 — Research evaluation
- **Phase:** P12
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P12-06, T-P12-03
- **Human approval:** required
- **Description:** 10 research runs rated by owner on sources, faithfulness, usefulness.
- **Rationale:** Quality control.
- **Acceptance criteria:** Ratings recorded; improvements logged.
- **Validation method:** Owner ratings.
- **Expected artifacts:** eval/reports/research.md

## P13 — Scale-out, Hardening & Operations

### T-P13-01 — Full-corpus ingestion waves W1-W3
- **Phase:** P13
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P4-15, T-P3-09, T-P2-12
- **Human approval:** required
- **Description:** Execute waves per policy (Q-B03); monitor; ETA; pause/resume.
- **Rationale:** Scale to the real corpus.
- **Acceptance criteria:** W1+W2 complete; W3 text tier complete; quality report.
- **Validation method:** Reports + doctor.
- **Expected artifacts:** reports/ingestion_waves.md

### T-P13-02 — Backup and restore
- **Phase:** P13
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P4-13, T-P1-12
- **Human approval:** none
- **Description:** Vault + ledger backups; DB snapshots; optional artifacts; restore drill.
- **Rationale:** Durability.
- **Acceptance criteria:** Restore drill succeeds on a clean machine path.
- **Validation method:** Drill log.
- **Expected artifacts:** src/sbr/ops/backup.py, docs runbook

### T-P13-03 — Rebuild-from-scratch drill
- **Phase:** P13
- **Status:** NOT_STARTED
- **Priority:** critical
- **Dependencies:** T-P6-08, T-P8-02
- **Human approval:** none
- **Traces to:** HC-12
- **Description:** Delete var/ indexes+knowledge DB; rebuild; compare metrics.
- **Rationale:** HC-12.
- **Acceptance criteria:** Rebuilt system reproduces eval metrics within tolerance.
- **Validation method:** Drill report.
- **Expected artifacts:** reports/rebuild_drill.md

### T-P13-04 — Schema migration test suite
- **Phase:** P13
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P1-06
- **Human approval:** none
- **Description:** Upgrade tests on copies of real DBs; rollback scripts.
- **Rationale:** R-18.
- **Acceptance criteria:** All migrations tested N-1->N.
- **Validation method:** CI suite.
- **Expected artifacts:** tests/migrations/*

### T-P13-05 — Embedding swap drill
- **Phase:** P13
- **Status:** NOT_STARTED
- **Priority:** medium
- **Dependencies:** T-P6-07
- **Human approval:** none
- **Description:** Build second EmbeddingSet, evaluate, switch, drop old.
- **Rationale:** NFR-05.
- **Acceptance criteria:** Swap without KU changes; metrics recorded.
- **Validation method:** Drill report.
- **Expected artifacts:** reports/embedding_swap.md

### T-P13-06 — Parser upgrade drill
- **Phase:** P13
- **Status:** NOT_STARTED
- **Priority:** medium
- **Dependencies:** T-P5-05, T-P4-14
- **Human approval:** none
- **Description:** Re-extract subset with new extractor version; anchor stability; stale notes.
- **Rationale:** R-10, R-15.
- **Acceptance criteria:** Citation stability ≥95%.
- **Validation method:** Drill report.
- **Expected artifacts:** reports/parser_upgrade.md

### T-P13-07 — MCP server
- **Phase:** P13
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P7-08
- **Human approval:** none
- **Traces to:** FR-26
- **Description:** Expose search/ask/trace/get-source tools over MCP for OpenCode/Claude Code.
- **Rationale:** FR-26.
- **Acceptance criteria:** Tools callable from an MCP client; permissions respected.
- **Validation method:** Integration test.
- **Expected artifacts:** src/sbr/mcp/*

### T-P13-08 — SPIKE-MEDIA: video/audio track
- **Phase:** P13
- **Status:** NOT_STARTED
- **Priority:** low
- **Dependencies:** T-P13-01
- **Human approval:** required
- **Spike:** SPIKE-MEDIA
- **Description:** If Q-I01 = yes: sample transcription cost/quality (Whisper variants on CPU), dedup against scripts.
- **Rationale:** ADR-030.
- **Acceptance criteria:** Report; decision.
- **Validation method:** Spike report.
- **Expected artifacts:** eval/reports/spike_media.md

### T-P13-09 — Code track (thesis MATLAB first)
- **Phase:** P13
- **Status:** NOT_STARTED
- **Priority:** low
- **Dependencies:** T-P13-01
- **Human approval:** review
- **Description:** Index MATLAB/Java code; link code to equations (thesis dynamics).
- **Rationale:** ADR-036.
- **Acceptance criteria:** Thesis equations linked to implementing functions on sample.
- **Validation method:** Sample check.
- **Expected artifacts:** src/sbr/extract/code.py

### T-P13-10 — Performance profiling and operations runbooks
- **Phase:** P13
- **Status:** NOT_STARTED
- **Priority:** high
- **Dependencies:** T-P13-01
- **Human approval:** none
- **Description:** Profile stages; write runbooks (21 §4).
- **Rationale:** Operability.
- **Acceptance criteria:** Runbooks exist and were exercised once.
- **Validation method:** Drill logs.
- **Expected artifacts:** docs/runbooks/*

## P14 — Project/Idea Integration (future)

### T-P14-01 — Idea/Project object model extension (design)
- **Phase:** P14
- **Status:** DEFERRED
- **Priority:** low
- **Dependencies:** T-P11-03
- **Human approval:** review
- **Traces to:** FR-27
- **Description:** Design Idea and ProjectBrief objects linked to concepts, gaps, claims.
- **Rationale:** Mission §32 future-proofing.
- **Acceptance criteria:** Design doc approved.
- **Validation method:** Owner review.
- **Expected artifacts:** docs/14x_IDEAS_DESIGN.md

### T-P14-02 — Idea generation workflow spike
- **Phase:** P14
- **Status:** DEFERRED
- **Priority:** low
- **Dependencies:** T-P14-01, T-P9-11
- **Human approval:** required
- **Spike:** SPIKE-IDEAS
- **Description:** Prototype cross-domain idea generation from gaps and strengths.
- **Rationale:** Future capability.
- **Acceptance criteria:** Spike report.
- **Validation method:** Owner rating.
- **Expected artifacts:** eval/reports/spike_ideas.md

### T-P14-03 — Brain bridge for distilled cross-project knowledge
- **Phase:** P14
- **Status:** DEFERRED
- **Priority:** low
- **Dependencies:** T-P10-03
- **Human approval:** required
- **Description:** Per Brain governance, promote generalized knowledge notes to the Brain with links to the PRJ record.
- **Rationale:** Reuse beyond this project.
- **Acceptance criteria:** Governance-compliant promotion of ≥1 note.
- **Validation method:** Brain validation.
- **Expected artifacts:** Brain 02_Knowledge notes
