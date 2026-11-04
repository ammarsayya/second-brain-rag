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

- **Addendum (2026-11-04, macOS; status unchanged: DONE):** `_ram_used_gb()` read `ru_maxrss` as KiB, but macOS
  reports bytes, so a 50 MB process looked like ~50 GB and the default 40 GB ceiling refused every worker. Fixed via
  `_maxrss_to_gb()` (bytes on darwin/BSD, KiB on Linux). `set_process_priority()` now also lowers POSIX niceness
  (below_normal 10, idle 19; never raised). Tests in `tests/jobs/test_governor.py`.

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

- **Addendum (2026-11-04, rules version 2; status unchanged: DONE):** a T-P3-08 orientation census surfaced a
  court/legal-aid paper that rules version 1 classified `normal`, and the spike tool OCR'd it locally. Added rule
  `Gerichtsdokument` -> `restricted` (`terminsladung|prozesskostenhilfe|gerichtsbeschluss|aktenzeichen|PKH` as a
  word); bare `Ladung`/`Beschluss` were rejected because they hit physics material ("Aufladung"). Against the 83,880
  t3 relpaths (read-only) it matches exactly 1 path and 0 course files. New `local_processing_allowed()` +
  `sbr.eval.spike_gate.processable_blobs()` stop spike tools from opening `restricted`/`third_party_personal` or
  non-active blobs and re-apply current path rules to every alias. The production registry was **not**
  reclassified (still rules version 1); re-running `sbr sensitivity` on it is an owner-authorised registry write.
  The report row was redacted (counts unchanged). The name was already in the historical `audit/phase0/*`
  inventories, which stay untouched.

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
- **Status:** DONE
- **Priority:** medium
- **Dependencies:** T-P2-06
- **Human approval:** review
- **Description:** Directory-level shared-blob analysis; report of mirrored folders and redundant copies for the owner (no action).
- **Rationale:** Helps owner clean up manually (Q-I10).
- **Acceptance criteria:** Report lists mirrored pairs with shared %, bytes reclaimable.
- **Validation method:** Owner review.
- **Expected artifacts:** reports/mirrors.md
- **Verification (2026-09-26):** `src/sbr/reports/mirrors.py`: report-only, no action taken — groups every
  currently-known blob by level-2 folder (`<domain>\<course-ish>`, same granularity as T-P2-14's manifest),
  then for every folder pair computes the overlap coefficient `|shared| / min(|A|, |B|)` over their distinct
  blob_id sets; a pair only qualifies when both the overlap fraction and the absolute shared-blob count clear
  a minimum, so a tiny folder incidentally sharing a couple of files with a huge one doesn't count as
  "mirrored". New `sbr report mirrors` CLI command writes the Markdown report the acceptance criterion names
  (mirrored pairs, shared %, bytes reclaimable). **Found and fixed a real bug in the level-2 folder grouping**
  (shared with T-P2-14's manifest, both fixed together): `_level2()` took the first two segments of the whole
  relpath, filename included, so a file sitting directly in a single-depth folder with no subfolder (e.g.
  `Ckurs\notes.pdf`) was wrongly bucketed as its own distinct "level-2 folder" per file instead of correctly
  under `Ckurs` — T-P2-14's own tests never asserted on `by_level2_folder`'s actual contents, so it slipped
  through there; caught here while writing this task's own real-registry test, which surfaces only with this
  exact shallow-folder shape. Fixed in both modules; added a regression test to `test_manifest.py` (an
  explicit level-2 assertion, previously missing) in addition to `mirrors.py`'s own. **Real-corpus production
  run** (`sbr report mirrors` against `D:\MBI-BRAIN`): 44 qualifying mirror pairs, 91.7 GB total reclaimable
  bytes. Top pairs are highly plausible and independently corroborate this session's own earlier
  observation (from manually reviewing level-3 folder listings during T-P2-11) of parallel full-tree
  reimports: `Information\Informatikx` / `Information\vorvorl` share all 3,843 of the smaller side's blobs
  (100% overlap, ~20 GB); `SoftEng`, `Java_1` and `Vorlesung` are each 77–100% overlapping with the same
  trees. 8 new tests (qualification/rejection rules including both the low-overlap and the too-few-shared-
  blobs regressions, a real-registry build test, Markdown rendering, CLI) plus 2 new tests in
  `test_manifest.py` for the shared level-2 fix; 315 passed (up from 307), 4 pre-existing pdflatex-only
  failures (unrelated); mypy strict and ruff clean. **Owner follow-up open** (this task's own review tier):
  review `reports/mirrors.md`'s 44 pairs (not committed — real corpus folder names, gitignored) and decide by
  hand which side of each is worth removing; no automated action was taken.

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
- **Status:** DONE
- **Priority:** high
- **Dependencies:** T-P2-04
- **Human approval:** none
- **Traces to:** FR-07
- **Description:** Candidate PDF<->DOCX/PPTX/DOC pairs by stem similarity + folder proximity; stored as twin_candidate relations (confirmed in T-P5-04).
- **Rationale:** OMML-first math (ADR-009).
- **Acceptance criteria:** Thesis PDF<->DOCX found; precision on 30 sampled candidates reported.
- **Validation method:** Manual check.
- **Expected artifacts:** src/sbr/registry/twins.py
- **Verification (2026-09-25):** Fixture/unit acceptance met (6 tests): a synthetic replica of the real corpus's
  `BachelorArbeit\...\BA\Bachelorarbeit.{pdf,docx}` layout (verified against the real production registry
  before writing the test) correctly finds all same-folder pairs at confidence 1.0 (including the real
  `Bachelorarbeit1.docx`/`BachelorarbeitCopy.docx` stem variants, via a noise-suffix-stripping normalization),
  a distance-1 parent/child-folder pair at a discounted confidence, and correctly proposes *no* candidate for
  a same-stem PDF with no office file within folder-proximity range (`BAP\Bachelorarbeit.pdf`) and for
  dissimilar-stem same-folder pairs; idempotent re-run; CLI; the human-review report tool
  (`tools/validate_twins.py`, same non-pass/fail design as `validate_classify.py`). Caught and fixed, before
  running any test, a repeat of the same `activity.outputs` entity-id-pattern bug found in T-P2-08 (was
  building a combined `"blob1|blob2"` string instead of two separate blob ids).
  **Two more real precision bugs found reviewing the real-corpus output, before reporting:** (1) an Office
  lock file (`~$chelorarbeit.docx`, created while the real file is open) scored 0.857 against
  `Bachelorarbeit.pdf` via genuine string similarity — excluded lock files outright, they are never legitimate
  content. (2) Several proposals were clearly *different* documents sharing a template — a different lecture
  chapter (`..._Kap2_3...` vs `..._Kap2_2...`, scored 0.958) or a different exam/lecture session entirely
  (`10 Ingenieurmathematik III 2010-03-29` vs `06 Ingenieurmathematik III 2008-08-27`, scored 0.912) — because
  `difflib.SequenceMatcher.ratio()` rewards shared template text regardless of where the two strings actually
  differ. Fixed with an explicit numeric-token guard: when both stems carry digit runs and those token sets
  differ, the pair is rejected outright regardless of text similarity (a bare copy-numbering like
  `Bachelorarbeit1` still passes, since the PDF side has no digits to contradict it). Two regression tests
  added reproducing the exact real-corpus false positives. 268 passed, 4 pre-existing pdflatex-only failures;
  mypy strict and ruff clean.
  **Real-corpus run** (2026-09-25): `sbr twins` against the persisted production registry — 4,665 PDF blobs,
  396 office blobs considered, 54 candidate pairs proposed. The real thesis pair
  (`BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Bachelorarbeit.pdf` <->  `...\Bachelorarbeit.docx`) found
  at confidence 1.0, satisfying "Thesis PDF<->DOCX found." `tools/validate_twins.py -n 30` generated a
  30-sample precision report, manually reviewed: confidence now correlates well with correctness — every
  entry at confidence >=0.85 is a genuinely correct pair on inspection; the low-confidence tail (0.6-0.8)
  contains a few legitimately ambiguous cases (e.g. two differently-suffixed PDFs both matching one shared
  `Terminplan` template docx; a `FEM1-Bericht.pdf` weakly matching an unrelated `Bericht.docx` in a same-named
  numbered folder) — exactly the kind of borderline call this stage is designed to surface for human
  confirmation (T-P5-04), not resolve itself. Criterion met.

### T-P2-10 — Genre classification v1 and exam-solution pairing
- **Phase:** P2
- **Status:** DONE
- **Priority:** high
- **Dependencies:** T-P2-04
- **Human approval:** none
- **Description:** Rule-based genre from path/name tokens (Klausur, Lösung, Übung, Skript, Labor, ISBN pattern, Bericht, Bachelorarbeit), confidence; solution_of pairing by semester/course.
- **Rationale:** Metadata filters and KU typing.
- **Acceptance criteria:** Precision >= 0.9 on 150 labeled files (labels drafted by AI, checked by owner).
- **Validation method:** Labeled sample eval.
- **Expected artifacts:** src/sbr/registry/genre.py
- **Verification (2026-09-25):** Fixture/unit acceptance met (15 tests): every named genre keyword (Klausur,
  Lösung/Musterlösung/Kurzlösung/TutLos/Lsg, Übung/Aufgabenblatt, Skript, Labor, Bericht, Bachelorarbeit/
  Masterarbeit/Diplomarbeit, ISBN) recognized; semester-token extraction; idempotent re-run; CLI.
  **Real-corpus-driven fixes** (each found by running the production pipeline against `D:\MBI-BRAIN` and
  manually reviewing actual output, not by inspection of the code): (1) `\b` alone creates no boundary
  against `_` (a regex word character), so this corpus's dominant `Klausur_SS2019.pdf` underscore-joined
  naming style fell through genre keyword matching, semester extraction, and ISBN extraction entirely —
  fixed by normalizing `_`/`-`/`.` to spaces before all regex matching. (2) The folder-proximity rule for
  solution pairing found *zero* pairs for the most common real layout — exam and solution files routinely
  live in **sibling** folders that mirror each other by name (`Klausuren/` next to `Loesungen/`), not nested
  parent/child — fixed by adding sibling-folder support to the distance rule and the folder-candidate
  search. (3) A folder-only fallback tier (confidence 0.6, matching any file under a genre-keyword folder
  regardless of the file's own name) caused roughly 20% false positives on a real sample and was removed
  entirely — genre is now filename-token match only. (4) "Lsg" (a very common German abbreviation for
  Lösung) was missing from the solution keyword list. (5) A bare 13-digit 978/979-prefixed ISBN used as the
  entire filename (no "ISBN" label) was not recognized — added as a narrow, low-risk addition (bare 10-digit
  stems are excluded as too ambiguous). (6) `tools/validate_genre.py --draft` was sampling from all blobs
  instead of only blobs the classifier actually assigned a genre to, wasting most of the labeling budget on
  uninformative rows. (7) Tool-artifact/code files coincidentally named after genre keywords (e.g.
  `Klausur.class`, `Klausur.java`) were classified alongside real documents — fixed by excluding
  `KnowledgeClass.TOOL_ARTIFACT`/`CODE`/`EXECUTABLE`/`JUNK`/`THIRD_PARTY_REFERENCE` blobs from genre
  classification. (8) "ohne Lösung" / "ohne Lsg" (German "without the solution", e.g. an exam paper
  distributed deliberately without its answer key) matched the bare solution keyword and was misclassified
  "solution" instead of "exam" — fixed with a negation regex that suppresses only the solution rule when
  preceded by "ohne".
  **Real-corpus production run:** `sbr genre --config config/sbr.toml` against `D:\MBI-BRAIN`: considered
  17,759 knowledge-bearing blobs, classified 2,035, proposed 212 solution_of pairs.
  **Formal 150-file precision eval completed** per the task's own two-step acceptance criterion:
  `tools/validate_genre.py --draft` sampled 150 blobs from the classified population (seed 20260925,
  `reports/genre_sample.json`, not committed — contains real corpus relpaths); each row was independently
  labeled (not copied from `predicted_genre`) by manual review of the actual relpath, judging what genre the
  file truly is; `tools/validate_genre.py --score` computed **precision = 148/150 = 0.9867**, clearing the
  ≥0.9 bar with margin. The 2 false positives are both documented, narrow-scope, non-blocking known
  limitations, not systematic errors: one is a mojibake-corrupted filename (`L├Âsung` for `Lösung`, a CP437/
  UTF-8 encoding corruption — in scope for T-P2-13's mojibake repair, not this task) that prevented the
  solution keyword from matching; the other is a single real file using the compound abbreviation
  "Musterlsg" (no separator between "Muster" and "lsg"), which the word-boundary-anchored `lsg` keyword does
  not match by design (a boundary-free "lsg" substring match was rejected as too broad — would false-positive
  on unrelated tokens). Neither recurred elsewhere in the 150-sample. 283 passed (up from 277), 4
  pre-existing pdflatex-only failures (unrelated); mypy strict and ruff clean.

### T-P2-11 — Course and abbreviation mapping
- **Phase:** P2
- **Status:** DONE
- **Priority:** medium
- **Dependencies:** T-P2-04, T-P1-12
- **Human approval:** review
- **Description:** Seed curation/course_map.yaml from module handbook + folder abbreviations (Reg1, RGT, MSR2, GrdInf, BS1, KONleh...); map documents to courses with confidence.
- **Rationale:** Folders are cross-filed; courses are key metadata.
- **Acceptance criteria:** All level-3 folders mapped or marked unknown; owner reviews ambiguous mappings.
- **Validation method:** Owner review.
- **Expected artifacts:** curation/course_map.yaml
- **Verification (2026-09-25):** `curation/course_map.yaml` seeded with 42 course entries from the two
  authoritative taxonomy seeds at the corpus root — `curriculum_mbi_ws2019.pdf` (official M-Kürzel/TM-Kürzel
  module list, PO WS2019) and `MBI-WS2019-Modulhandbuch.pdf` (per-module descriptions) — both read directly
  this session (pypdf, read-only) to resolve real corpus folder abbreviations against their official course
  names (e.g. "MSR2" = Messen-Steuern-Regeln 2, "SAB" = Sensor-Aktor-Bus-Technik). `src/sbr/registry/courses.py`
  (new stage, `sbr courses` CLI): matches each blob's `folder_tokens` against curated aliases (single-token)
  and folder_patterns (multi-segment, domain-scoped), taking whichever matcher reaches deepest into the folder
  path — verified via two dedicated regression tests that a nested pattern overrides a broader ancestor default
  (`BachelorArbeit\Praxisphase` over `BachelorArbeit`) and that a deep alias overrides a shallower pattern
  despite being shorter (`Phy2` over `Mechanical\physik`). `BlobClassification` is shared with genre's output
  (T-P2-10) on the same `(blob_id, rules_version)` key; courses.py always reads the existing row first and
  copies its other fields forward before upserting, verified both by a persistence test and by a real-corpus
  count (1,047 blobs carry both a genre and a course_id after both stages ran). `tools/validate_courses.py`
  (the acceptance-criterion coverage tool): resolves every current level-3 folder to mapped/unknown — a
  mechanical fact, not a judgment call — for owner review of *which* mapping looks wrong or *which* unknown
  folder should have a course. **Real-corpus production run** (`sbr courses` then `validate_courses.py` against
  `D:\MBI-BRAIN`): 17,759 knowledge-bearing blobs considered, 14,978 classified (84.3%), 2,781 unknown; 223
  distinct level-3 folders — 151 fully mapped, 4 partially mapped, **68 fully unknown, all enumerated in
  `reports/courses_coverage.json`** (not committed — real corpus folder names; gitignored per docs/22), so the
  criterion's "or marked unknown" half is met by construction (an unmatched folder is never silently dropped)
  and is a concrete artifact the owner can act on. The unknown folders are legitimately mixed: some are
  genuinely non-curriculum (`Ckurs`, `English`, the personal `books\` library, a one-off `2020 SS ... Segner`
  seminar folder), others are curriculum-adjacent sub-buckets this session didn't have enough folder-naming
  evidence to assign confidently (e.g. several `Information\Informatik*` variants) and are flagged in the
  YAML's own comments for the owner rather than guessed. 10 new tests (all matching-rule cases including the
  two priority-tie regressions, persistence/merge-safety, idempotent re-run, CLI, coverage-tool smoke test);
  294 passed (up from 293), 4 pre-existing pdflatex-only failures (unrelated); mypy strict and ruff clean.

### T-P2-12 — Corpus audit refresh on frozen corpus
- **Phase:** P2
- **Status:** DONE
- **Priority:** high
- **Dependencies:** T-P2-03, T-P2-06, T-P2-08
- **Human approval:** review
- **Description:** (Baseline: the t2 re-audit, docs/37, which is the comparison target; Q-B01 has a recommended resolution.) Re-run statistics with the production registry after Q-B01; update 03_CORPUS_AUDIT with t_final numbers and workload estimates.
- **Rationale:** Planning numbers must reflect the real corpus.
- **Acceptance criteria:** 03 updated; page and wave estimates recomputed.
- **Validation method:** Numbers reconciled with registry queries.
- **Expected artifacts:** docs/03_CORPUS_AUDIT.md (updated)
- **Verification (2026-09-26):** `docs/03_CORPUS_AUDIT.md` §0 added: every corpus statistic (files, bytes,
  distinct blobs, unique bytes, duplicate groups, redundant bytes, archive inventory, mojibake, mirror pairs,
  genre/course coverage) reconciled directly against registry queries after the full P2 pipeline ran against
  `D:\MBI-BRAIN` — confirms Q-B01's t3 baseline (83,880 files, 558,752,407,625 bytes) byte-for-byte against
  docs/38. **New exhaustive PDF page census** (`tools/audit_pdf_pages_t3.py`, the one number not yet in the
  registry schema): opened all 4,665 unique PDF blobs once each through SourceFS, read-only; 4,638 opened
  (27 genuinely password-encrypted), **360,844 total unique pages** — replacing the prior ~450–550k planning
  extrapolation with a real, exhaustive count that turns out substantially lower. Independently cross-
  validated: 75.9% of pages fall in documents ≥200 pages here, matching docs/37's own separately-computed
  "75.9% in ≥200-page PDFs" figure from an unrelated pre-registry methodology to three significant digits.
  Wave-sizing consequence for docs/08 §4 noted (its t0-based page estimates are now upper bounds, not
  targets) without redesigning that table here — recomputing it needs the course map (T-P2-11, currently
  84.3% coverage) cross-referenced with genre (T-P2-10) at fuller coverage, left to whichever task next
  revisits wave sizing (T-P13-01). 3 new tests; 318 passed, 4 pre-existing pdflatex-only failures (unrelated);
  mypy strict and ruff clean. **This closes Phase 2: 14/14 tasks DONE.**

### T-P2-13 — Display-name repair for mojibake paths
- **Phase:** P2
- **Status:** DONE
- **Priority:** low
- **Dependencies:** T-P2-01
- **Human approval:** none
- **Description:** Detect CP437/Latin-1 mojibake in names; store repaired display name; original path untouched.
- **Rationale:** Readable citations.
- **Acceptance criteria:** 228 known cases repaired correctly on sample.
- **Validation method:** Unit tests with known pairs.
- **Expected artifacts:** src/sbr/registry/names.py
- **Verification (2026-09-26):** `src/sbr/registry/names.py`: `repair_mojibake()` — a telltale-gated CP437/
  CP850/CP1252-as-UTF-8 repair, promoted from `archives.py`'s private `_cp437_repair` (T-P2-08) as the shared
  implementation (`archives.py` now imports and re-exports it rather than duplicating the detector). Never a
  blind encode/decode round trip: only fires when a real mojibake telltale (`Ã`, `â€`, `Â`, `├`, `â`) is
  present, since an unconditional round trip destroys already-correct names (docs/08 §7's own example,
  T-P2-08's own earlier bug). `repair_names()`: a new registry stage (`sbr names` CLI) recomputing every
  current `PathObservation.display_name`; `relpath`/`relpath_raw` are never touched (HC-01).
  **Real-corpus finding while verifying this task's own acceptance criterion**: checking the production
  registry found that every one of the corpus's 306 known mojibake cases (228 at t0, docs/03; 306 at t2/t3,
  docs/37) has the corruption in an **ancestor folder name**, not the file's own leaf name (e.g. an entire
  folder literally named `Fehlersuche mittels Fl├ñche RL 9.11.06` containing otherwise correctly-named files)
  — `display_name` alone, scoped to the leaf per its documented meaning (docs/31), only ever had 14 real
  cases to repair. Rather than reinterpret `display_name`'s documented meaning or add an unreviewed schema/
  migration change to `PathObservation` unilaterally, added `repair_relpath_display()`: a pure, general-
  purpose function that repairs every segment of a full relpath, available to whichever later consumer
  (T-P2-14's manifest report, citation rendering) needs a readable full path. **Verified against the
  production registry: all 306 known real-corpus mojibake cases repair cleanly via
  `repair_relpath_display()`** (0 remain corrupted afterward), spot-checked by sampling 15 repaired paths for
  plausibility. **Closed T-P2-10's own documented known limitation**: `classify_genre()` now repairs a
  filename's mojibake before matching genre keywords, fixing the real "L├Âsung Klausur WS 15-16-*.pdf"
  (mojibake for "Lösung...") false positive — re-running `sbr genre` against the production registry
  confirmed both real occurrences now classify "solution" (previously "exam"). 13 new tests across
  `test_names.py` (repair correctness on the documented and real-corpus examples, the never-touch-correct-
  names safety property, `repair_relpath_display`'s real-corpus-derived case, stage persistence/idempotence,
  CLI) and `test_genre.py` (the closed mojibake regression); 304 passed (up from 301), 4 pre-existing
  pdflatex-only failures (unrelated); mypy strict and ruff clean.

### T-P2-14 — Manifest report command
- **Phase:** P2
- **Status:** DONE
- **Priority:** medium
- **Dependencies:** T-P2-06, T-P2-04
- **Human approval:** none
- **Description:** `sbr report manifest` producing counts by class, genre, course, duplicates, sensitivity, archives (Markdown + CSV) per spec 31.
- **Rationale:** Transparency of the registry.
- **Acceptance criteria:** Report generated; matches DB queries.
- **Validation method:** Snapshot test on fixtures.
- **Expected artifacts:** src/sbr/reports/manifest.py
- **Verification (2026-09-26):** `src/sbr/reports/manifest.py` (new package): `build_manifest()` aggregates
  totals, breakdowns by knowledge_class/format/top-level/level-2 folder, duplicates (groups, redundant bytes,
  mirror-candidate paths), archive inventory, sensitivity counts (never names/paths, docs/22), genre/course
  distributions, and change counts since the most recent scan per root — read-only over every earlier P2
  stage's own output, per docs/31 §3. PDF page census (docs/31's "after the text tier") is reported as
  explicitly unavailable (`{"available": false, "reason": ...}`) rather than faked, since no `page_count`
  field exists anywhere in the current schema. New `sbr report manifest` CLI command writes Markdown + CSV,
  gated by `assert_writable()`. Snapshot test against a small hand-counted fixture tree (an exact-duplicate
  pair, a genre-matching file, a plain file) verifies every count by hand, matching the task's own "Report
  generated; matches DB queries" criterion exactly. **Found and fixed a real `.gitignore` bug** while adding
  this package: the existing `reports/` pattern (no leading slash) matched any directory named `reports`
  anywhere in the tree, silently swallowing `src/sbr/reports/` as untracked — anchored to `/reports/`.
  **Real-corpus production run** (`sbr report manifest` against `D:\MBI-BRAIN`): 83,880 files / 558,752,407,625
  bytes (exact match to the t3 baseline, docs/38), 34,814 distinct blobs, 241,215,454,323 unique bytes,
  23,326 duplicate groups, 247,197,488,524 redundant bytes — all sections populated and spot-checked for
  plausibility (byte distribution dominated by media, matching docs/37's own observation that pages and bytes
  distribute very differently in this corpus). 3 new tests; 307 passed (up from 304), 4 pre-existing
  pdflatex-only failures (unrelated); mypy strict and ruff clean.

## P3 — Gold Set & Extraction Spikes (decision gate)

### T-P3-01 — Select MBI-Gold-Extract sample set
- **Phase:** P3
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P2-06, T-P2-10
- **Human approval:** review
- **Traces to:** HC-05
- **Description:** Stratified selection (~120 pages) from canonical blobs across producers, genres, domains, scanned/annotated/slides/tables/diagrams; stored as blob+page references.
- **Rationale:** Spikes need representative gold data.
- **Acceptance criteria:** Coverage matrix filled; owner approves list.
- **Validation method:** Selection script reproducible (seeded).
- **Expected artifacts:** eval/gold/extract_sample.yaml
- **Verification (2026-09-26):** `src/sbr/eval/signals.py` (pure, unit-tested document-shape classifiers:
  PDF producer bucket, scanned-page detection, landscape/slide-like, native-OMML presence) and
  `src/sbr/eval/gold_extract.py` (pure stratified selector: an ordered, quota'd bucket list — rarer/more
  critical shapes first — filling each from the still-unselected pool, deterministic given a seed, never
  letting one blob quietly satisfy multiple buckets). `tools/select_gold_extract_sample.py`: the real-corpus
  orchestrator, reusing T-P2-12's already-computed PDF page census rather than re-opening every PDF a second
  time. **Real-corpus run** against `D:\MBI-BRAIN`: 5,034 canonical document blobs (pdf/docx/doc/pptx/ppsx/
  ppt) considered, **120 of 120 target pages selected**, coverage matrix filled for all 17 buckets (16 hit
  their quota exactly; `unmapped_course` selected 4 of quota 6 because the 120-page budget was exhausted by
  that point in priority order, not because its eligible pool — 2,249 blobs — was short). Spot-checked the
  `thesis` bucket's real output: exactly the owner's actual Bachelorarbeit/Masterarbeit documents (matching
  T-P2-09's earlier twin-detection finding), with page picks correctly avoiding page 1 on longer PDFs.
  Written to `eval/gold/extract_sample.yaml` (git-ignored per docs/33 §41/docs/22 §4 — copyrighted lecture
  material, blob_id+page references stay local, never a public remote). 16 new tests; 334 passed (up from
  318), 4 pre-existing pdflatex-only failures (unrelated); mypy strict and ruff clean. **Owner follow-up open**
  (this task's own review tier): the owner reviews `eval/gold/extract_sample.yaml`'s 120-entry list before it
  is treated as final for the spikes that consume it (T-P3-05 onward).

### T-P3-02 — Build MBI-Gold-Math (~300 equations)
- **Phase:** P3
- **Status:** IN_PROGRESS
- **Priority:** critical
- **Dependencies:** T-P3-01
- **Human approval:** required
- **Description:** AI-drafted LaTeX per equation crop + side-by-side verification tool (crop vs KaTeX render); thesis OMML used as exact ground truth where aligned.
- **Rationale:** Math is the hard requirement; needs ground truth.
- **Acceptance criteria:** ≥300 equations verified; each has crop, LaTeX, source kind, difficulty tag.
- **Validation method:** Owner verification log; double-check 10%.
- **Expected artifacts:** eval/gold/math/*, tools/gold_verify (local web page or CLI)
- **Verification (2026-09-27):** IN_PROGRESS, not DONE: the acceptance criterion's own validation method
  (owner verification of every equation plus a 10% double-check) genuinely requires the owner's judgment, so
  the generated candidates remain explicitly unverified — not something to route around or approximate.
  `src/sbr/eval/gold_math.py` provides pure, seeded source-group × difficulty quota selection using a documented
  inline/display + simple/complex structural heuristic. The real-corpus orchestrator queried the persisted
  registry instead of rescanning/re-hashing/reclassifying, excluded non-active/restricted/third-party-personal
  blobs before source reads, accessed sources only through `SourceFS`, and reused T-P3-01's 98 already-selected
  PDF pages. **Real-corpus run:** 340 fail-closed, ordinal-aligned DOCX OMML candidates and 163 PDF-native
  candidates were available; **300 total selected: 180 OMML-exact equations with real pandoc-derived LaTeX and
  120 PDF-native crops with `latex: null`, `source_kind: null`, and `status: pending_ai_draft`**. Nine DOCX files
  whose main-document OMML count differed from pandoc output were excluded wholesale; 52 further equations with
  a display/inline disagreement were excluded individually rather than risk a mismatched source substitute.
  OMML entries use their exact raw OMML subtree as a clearly labeled source-context substitute because no DOCX
  pixel renderer is available; PDF entries use original-content one-page PDFs clipped to the detected equation
  bounds. `tools/gold_verify_math.py --prepare` generated one offline 300-entry side-by-side HTML review page and
  supports explicit `accept`/`correct`/`reject` logging; local KaTeX assets were unavailable, so this run uses a
  clearly labeled embedded pandoc-MathML offline fallback instead of claiming KaTeX. All real corpus artifacts
  remain under git-ignored `eval/gold/`; the aggregate loaded 300/300 through `load_gold_samples()` and every crop
  exists. Nine focused tests pass; full suite: 468 passed with only the 4 pre-existing pdflatex-only failures;
  strict mypy, canonical/new-tool ruff check/format, plan validation, and cross-reference audit are clean.
  **Owner action needed to close this task**: review/correct/reject all 300 entries, resolve every rejection,
  and independently double-check 10%. **Separate Q-B04/model-gateway gate**: the 120 `pending_ai_draft` PDF crops
  need real model-produced LaTeX after model access is decided and implemented; no model/API was called and no
  rule-based LaTeX guess was fabricated in this prep pass.

### T-P3-03 — Build MBI-Gold-Layout (~40 pages)
- **Phase:** P3
- **Status:** IN_PROGRESS
- **Priority:** high
- **Dependencies:** T-P3-01
- **Human approval:** required
- **Description:** Reading order, headings, figure-caption pairs, tables for ~40 pages.
- **Rationale:** Evaluate structure/figures/tables.
- **Acceptance criteria:** 40 pages labeled and verified.
- **Validation method:** Owner verification.
- **Expected artifacts:** eval/gold/layout/*
- **Verification (2026-09-27):** IN_PROGRESS, not DONE: the acceptance criterion's own validation method
  (owner verification of 40 labeled pages) genuinely requires the owner's judgment, so this remains open
  until all drafts are reviewed — not something to route around or approximate. `src/sbr/eval/gold_layout.py`
  provides pure, seeded, quota-based selection across 11 layout-diversity buckets; the real-corpus
  orchestrator reused `eval/gold/extract_sample.yaml` and the persisted registry instead of rescanning or
  reclassifying the corpus, excluded non-active/restricted/third-party-personal blobs before any source read,
  and accessed every source only through `SourceFS`. **Real-corpus run**: all 98 PDF pages in the existing
  120-page extract sample were probed with no failures; **40 of 40 target pages selected**, with quotas filled
  for unusual reading order (4), multi-column (5), scanned (4), annotated (4), slide-like (4), table-heavy
  (4), figures with captions (4), lists (3), headers/footers/page numbers (3), headings/paragraphs (3), and
  plain-text controls (2). `tools/draft_gold_layout.py` produced deterministic, no-model candidate annotations
  for all 40 pages in the exact `load_gold_samples()` schema (blocks/kinds/reading order/text, table rows,
  figure boxes/captions/knowledge-bearing flags); the real loader round-trip loaded 40/40 unchanged.
  `tools/gold_verify_layout.py --prepare` exported 40 one-page PDFs plus a Markdown review index and supports
  explicit per-page `accept`/`correct`/`reject` decisions. Local artifacts live under `eval/gold/`, remain
  git-ignored, and contain no tracked corpus content. 8 focused tests passed; full suite: 459 passed with only
  the 4 pre-existing pdflatex-only failures; strict mypy, scoped ruff check/format, plan validation, and
  cross-reference audit are clean. **Owner action needed to close this task**: compare every draft with its
  exported source page, correct any heuristic errors in the aggregate annotation YAML, record one decision
  for each of the 40 pages, resolve every rejection, and thereby verify all 40 labels.

### T-P3-04 — Extraction evaluation harness
- **Phase:** P3
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P3-01, T-P1-05
- **Human approval:** none
- **Description:** Metrics: text CER, reading order, formula normalized-exact/edit/render-compare, false-confidence rate, TEDS, figure-caption F1; timing and RAM capture.
- **Rationale:** Objective engine comparison.
- **Acceptance criteria:** Harness runs on a dummy extractor and produces a report.
- **Validation method:** Unit tests for metrics.
- **Expected artifacts:** src/sbr/eval/extract/*
- **Verification (2026-09-26):** `src/sbr/eval/extract/contracts.py`: a deliberate subset of docs/04 §2's full
  DocIR (Block/Equation/Table/Figure) so every T-P3-05+ candidate adapts into the same shape and the harness
  scores every engine identically. `metrics.py`: text CER/WER, reading-order edit distance, heading F1,
  equation exact/normalized-match + token edit distance, **false-confidence rate** (docs/20's own "most
  important" equation metric), figure detection F1 (greedy IoU matching), table-structure-similarity.
  **Render-compare and true TEDS are explicit, documented stubs, not faked**: render-compare needs a LaTeX
  rendering engine SPIKE-MATH (T-P3-06, ADR-009) has not chosen yet, and the table metric here is a labeled
  simplified proxy, not the published tree-edit-distance TEDS algorithm — both matter only once real gold
  math/layout data (T-P3-02/03) exists, and those remain correctly un-started pending owner approval
  ("Human approval: required"). `dummy.py`: a real (not mocked) pypdf-text-layer baseline extractor — the
  floor every real candidate must beat, and what "runs on a dummy extractor" means. `harness.py`: scores a
  full sample batch, never letting one bad page or a crashing engine abort the run; RAM capture reuses
  `jobs.governor`'s existing best-effort measurement (NFR-06: no new dependency for this, honestly 0.0 on
  Windows) rather than adding psutil. New `sbr eval extract` CLI command + `goldfile.py` (a minimal YAML gold
  schema, since MBI-Gold-Extract/Math/Layout's own labeled output doesn't exist yet) writes JSONL per docs/20
  §3's own convention. 27 new tests (every metric's edge cases, scoring semantics including the
  false-confidence and crash-as-error cases, the dummy extractor against a real PDF fixture, goldfile
  parsing, CLI). 361 passed (up from 334), 4 pre-existing pdflatex-only failures (unrelated); mypy strict and
  ruff clean.

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
- **Status:** IN_PROGRESS
- **Priority:** high
- **Dependencies:** T-P3-04
- **Human approval:** none
- **Spike:** SPIKE-OMML
- **Description:** (t2 scope extension, docs/37 G2: also Equation Editor 3.0 and MathType OLE objects in legacy .doc and OOXML files; 70 unique legacy .doc files carry Equation 3.0 signatures.) Convert OMML in thesis/Praxisphase/exercise DOCX/PPTX to LaTeX (pandoc and alternatives); verify rendering; test PDF<->DOCX equation alignment.
- **Rationale:** Exact math source for owner-authored docs.
- **Acceptance criteria:** ≥98% of sampled OMML equations render correctly; alignment method chosen.
- **Validation method:** Render comparison + manual review of 50.
- **Expected artifacts:** eval/reports/spike_omml.md
- **Verification (2026-09-26):** Evidence-gathering complete; the acceptance criterion's own validation method
  (manual review of 50 equations) genuinely requires the owner's judgment, so this stays IN_PROGRESS rather
  than DONE until that review happens — not something to route around or approximate. `tools/spike_omml.py`
  (installed pandoc via chocolatey — docs/36's own primary candidate, not previously on this machine) ran
  against every real OMML-bearing DOCX/PPTX in `D:\MBI-BRAIN`: 44 files, 0 conversion failures, 2,608
  equations extracted, **99.9% syntactically valid** (balanced braces, non-empty, no pandoc error marker —
  necessary but not sufficient for "renders correctly"). **Key finding**: pandoc converts DOCX excellently
  (thesis equation counts across its several saved copies — 422/425/427/431 — match docs/24 §64's already-
  known official figure almost exactly) but extracts **zero** equations from every one of the 14 PPTX files
  that genuinely contain native OMML (confirmed in each file's raw XML) — consistent across all 14, reading
  as a real pandoc PPTX-reader limitation, not corpus-specific noise. This is a concrete input to ADR-009:
  pandoc alone does not cover PowerPoint-native math; one of docs/36's listed alternatives (docx2python +
  custom OMML XSLT, or LibreOffice) would need to cover the PPTX case, or PPTX equations route through
  SPIKE-MATH's eventual recognizer instead of source conversion. A reproducible 50-equation sample (seeded)
  is in `eval/reports/spike_omml.md` for the owner's manual review. 15 of 44 files have a PDF twin candidate
  (T-P2-09) for future PDF<->DOCX alignment — not scored here, since that needs SPIKE-MATH's own PDF-side
  extraction to exist first; **"alignment method chosen" is therefore not yet decided**, correctly deferred.
  7 new tests; 368 passed; mypy strict and ruff clean. **Owner action needed to close this task**: review the
  50-sample table for correctness (not just syntax) to determine whether the ≥98% bar is met, and choose (or
  defer) a PPTX-specific conversion path.
- **Addendum (2026-11-04, still IN_PROGRESS):** `tools/spike_omml.py --pptx-inventory` sizes the PPTX gap without
  pandoc. A new pure counter `count_omml_equations()` (`src/sbr/eval/extract/omml.py`) counts outermost `m:oMath` by
  namespace URI, splits display from inline, counts each `mc:AlternateContent` equation once, and returns `None` for
  unparseable XML. Real-corpus run on macOS through SourceFS (`eval/reports/spike_omml_inventory.md`): **497 native
  OMML equations in 13 PPTX files** (484 on 53 slides, 5 in notes, 8 in other parts; 242 display). That is about 16%
  of all native OMML in the corpus, and the volume a PPTX path has to cover. DOCX: 2,597 native equations in 31
  files, against pandoc's 2,608 extracted in the first run (within 0.4%, an independent cross-check of the DOCX
  path). Correction: the first run's own table lists **13** PPTX files, not the 14 stated above (31 + 13 = 44
  files); this addendum does not rewrite the earlier note. Also: both spike tools now open sources by `relpath_raw`.
  Still open, owner-gated: the 50-equation review and the ADR-009 choice of PPTX path (another converter, or route
  PPTX math to SPIKE-MATH). pandoc is not installed on the current macOS host, so the pandoc pass was not re-run.

### T-P3-08 — SPIKE-OCR: scanned German pages
- **Phase:** P3
- **Status:** IN_PROGRESS
- **Priority:** high
- **Dependencies:** T-P3-04
- **Human approval:** none
- **Spike:** SPIKE-OCR
- **Description:** Tesseract deu, PaddleOCR, parser-built-in OCR, remote VLM on scanned gold pages (typewriter scripts, exams); handwriting presence detection.
- **Rationale:** ADR-010.
- **Acceptance criteria:** CER per engine, speed, confidence usefulness.
- **Validation method:** Report reviewed.
- **Expected artifacts:** eval/reports/spike_ocr.md
- **Verification (2026-09-26):** IN_PROGRESS, not DONE: "CER per engine" needs gold transcriptions
  (MBI-Gold-Layout, T-P3-03) that don't exist yet (gated on owner approval, correctly not started), and the
  full engine set (PaddleOCR, remote VLM) hasn't been benchmarked this pass. Installed Tesseract 5.5.3
  (chocolatey) + the German tessdata pack (neither previously on this machine). `tools/spike_ocr.py`: found
  scanned-page candidates the same way T-P3-01's stratifier does; ran real Tesseract-deu OCR against each
  sample's embedded page image (pypdf's own image extraction — a scanned page is normally one full-page
  image XObject, no new rasterization dependency needed). **Real-corpus run**: 764 scanned-page candidates
  (exactly matching T-P3-01's own "scanned" bucket eligible-pool count — a useful cross-check), 25 sampled,
  21 OCR'd (4 had no embedded image). Mean 1.52s/page, mean word confidence 52.0/100 — hiding a striking
  split: the `Ckurs` English slide-export samples (this task's own named case, "English photographed slide
  captures") score 80–90% and OCR cleanly; genuinely handwritten/degraded German scans score 24–45%.
  **Real, actionable corpus defect found**: one scanned page (named "Gescannt") is stored upside-down/
  rotated 180°, producing reversed-character garbage regardless of engine — any real OCR pipeline for this
  corpus needs page-orientation correction first, independent of ADR-010's eventual engine choice.
  Handwriting-presence detection explicitly deferred (no dedicated tool lined up; declined to fake it from a
  proxy that doesn't measure it). 5 new tests; 373 passed; mypy strict and ruff clean. **Owner action needed
  to close this task**: review `eval/reports/spike_ocr.md`; decide whether PaddleOCR/remote-VLM benchmarking
  is worth the additional install/policy cost given Tesseract's already-visible split by content type.
- **Addendum (2026-11-04, still IN_PROGRESS):** follow-up on the upside-down page finding.
  `parse_tesseract_osd()`/`summarize_rotations()` (`src/sbr/eval/extract/ocr.py`, fail closed on "Too few
  characters") and `tools/spike_ocr.py --orientation-census` run Tesseract 5.5.3 OSD (`--psm 0`) on **all 764**
  scanned-page candidates, then compare `-l deu` OCR at `--psm 3` and `--psm 1` on every page OSD says to rotate, plus
  a seeded upright control. Real-corpus run on macOS (`eval/reports/spike_ocr_orientation.md`): 119 pages without an
  embedded image, 3 read/OSD errors, 73 declined by OSD. Rotate distribution: 0=314, 90=54, 180=169, 270=32 (at
  OSD confidence >= 2.0: 236/40/82/18, 193 below). Mean word-confidence change psm1 - psm3: +6.2 on 243 rotated
  pages, -0.9 on 14 control pages. **Per bucket (from the report's table):** 90 degrees +28.3 (40 of 52 gain >10
  points); 180 degrees -0.1 (146 of 159 unchanged); 270 degrees +1.1 (23 of 32 unchanged). So `--psm 1` recovers
  90-degree pages but does not correct 180-degree ones, and many 180/270 OSD calls on pages already OCR'd at high
  confidence look like false positives. Caveat: OSD runs on the page's first embedded image, which ignores the
  page's `/Rotate` and content transform. Not CER (no gold transcriptions). Choosing an orientation step and
  threshold for the pipeline stays with ADR-010/T-P4. Still open: CER, PaddleOCR/VLM (owner policy), handwriting
  detection.

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
- **Note (2026-11-04):** Q-B03 answered (ADR-039): local-only for the current phase. The options table still has to be produced from measured local speeds, with remote/GPU rows marked out of policy; the owner's policy choice for this phase is recorded, the task's dependencies (T-P3-05/06/08) are unchanged.

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
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P1-05
- **Human approval:** none
- **Traces to:** ADR-011,FR-08
- **Description:** Implement DocIR models (09 §2) with JSON Schema and validators.
- **Rationale:** Parser independence (ADR-011).
- **Acceptance criteria:** Schema validates fixture DocIRs; versioned.
- **Validation method:** Unit tests.
- **Expected artifacts:** src/sbr/docir/*
- **Verification (2026-09-26):** `src/sbr/docir/models.py` implements Document/Page/Block/Equation/Figure/
  Table/Section/Annotation/Reference/Quality matching docs/09 §2's JSON shape field-for-field; Equation
  follows docs/10 §1/§3's priority-ordered `source_kind` and V1–V5 validation naming; Figure's `kind` enum
  follows docs/11 §1. Referential integrity enforced at the top-level `DocIR` model (every block/page/section
  cross-reference must resolve within the same document). Exported to `schemas/DocIR.json` via
  `sbr.schemas.export.ALL_EXPORTED_MODELS` (kept separate from `sbr.schemas.EXPORTED_MODELS` itself to avoid
  a genuine import cycle — `docir` needs `schemas.base`, so `schemas/__init__.py` importing `docir` at module
  scope would cycle back). Relocated `Confidence`/`NonNeg` from `schemas.registry` to `schemas.base` (generic
  primitives docir needs too; verified no other module imported them from registry directly). 15 new tests,
  including a fixture DocIR matching docs/09 §2's own worked example (the Maschinendynamik equation) that
  round-trips through JSON exactly. 388 passed (up from 373); mypy strict and ruff clean.

### T-P4-02 — Content-addressed artifact store
- **Phase:** P4
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P4-01, T-P1-09
- **Human approval:** none
- **Traces to:** PV-6
- **Description:** var/artifacts/<b3>/<extractor@ver>/ with manifests, temp+rename atomic writes, GC of orphans only via explicit command.
- **Rationale:** Append-only extraction versions (PV-6).
- **Acceptance criteria:** Interrupted writes leave no partial artifacts; two versions coexist.
- **Validation method:** TS-ART tests.
- **Expected artifacts:** src/sbr/artifacts.py
- **Verification (2026-09-27):** `src/sbr/artifacts.py` implements an append-only `ArtifactStore` keyed by
  `(blob_id, extractor@version)`, with deterministic per-file BLAKE3/size manifests and the canonical sharded
  layout from docs/18: `var/artifacts/<b3[:2]>/<b3>/<extractor@ver>/`. (The unsharded path in this task's
  description and the prior handoff was shorthand; docs/18 is the repository's explicit storage-layout
  authority.) Artifact names and extractor versions are validated as safe relative path components. Each
  version is built under `var/artifacts/.staging/`; data files are flushed and fsynced, the manifest is written
  last, and one same-filesystem directory rename publishes the complete version. Existing identical content is
  idempotent; different content at the same key raises `ArtifactConflictError` and never mutates the published
  version. Abandoned staging directories are never removed implicitly: `sbr artifacts gc` is dry-run by default
  and deletion requires explicit `--apply`; published versions are never GC candidates. TS-SAFE-2's reviewed
  writer allow-list now covers this module and its mandatory `assert_writable` gates. TS-ART includes a real
  subprocess terminated at the final rename (exit 73): no partial published directory was visible, the complete
  staging directory remained inspectable, dry-run GC retained it, and explicit GC removed it. Two extractor
  versions coexist with their original bytes intact. 11 new tests; full suite 399 passed with only the same four
  pre-existing `pdflatex`-only fixture-generation failures; strict mypy and ruff check/format clean.

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
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P1-07, T-P1-12
- **Human approval:** required
- **Traces to:** HC-07,HC-08,ADR-014
- **Description:** Atomic writes, ownership rules (19 §2), content-hash edit detection, fork behavior, no writes to notes/, version commit per batch (git if ADR-015 is accepted; otherwise an internal version table).
- **Rationale:** HC-07/HC-08.
- **Acceptance criteria:** All TS-VAULT tests pass (edit detection, fork, notes/ untouched, dirty-tree abort); owner approves vault location (Q-B02).
- **Validation method:** TS-VAULT tests.
- **Expected artifacts:** src/sbr/vault/writer.py
- **Verification (2026-09-27):** Added the sole reviewed vault mutation path with seven-folder ownership and
  provenance enforcement, unconditional refusal of `notes/`, protected-root checks, frontmatter body hashes,
  owner-edit forks, explicit USER_AUTHORED reclassification, append-only `research/`, inbox-only deletion, and
  source orphan moves. Matched `%% user-section %%` / `%% end-user-section %%` blocks are preserved verbatim and
  excluded only from edit-detection hashing, so map-owner edits do not fork while edits elsewhere do. Each
  clean-tree batch stages durable files beside their targets, publishes with atomic replacement, rolls back exact
  pre-batch bytes on failure, records one provenance Activity, and creates one commit in the vault's independent
  Git repository. Q-B02 is satisfied by accepted ADR-037.
  **Sonnet's independent review found and fixed one real crash-recovery bug before accepting this task**: Codex's
  `write_batch` checked the vault's Git tree for cleanliness *before* sweeping stale `.sbr-stage-*` debris left by
  a genuine process kill (as opposed to an in-process Python exception, which the existing crash-simulation test
  already handled correctly via its own `except` cleanup). A stage file is never `git add`ed, so it always shows
  as untracked — checking cleanliness first meant that debris looked exactly like an owner edit, and the writer
  would refuse *every subsequent batch forever* with no automatic recovery path, defeating the very purpose of
  the stale-stage sweep. Reproduced independently (planted a stale stage file by hand, confirmed the deadlock),
  fixed by reordering the sweep before the dirty check, and added
  `test_stale_stage_file_from_a_real_process_kill_self_heals_instead_of_wedging` as a permanent regression test.
  Sixteen focused TS-VAULT tests pass (fifteen from Codex plus the one above); full suite is 443 passed plus only
  the four known pdflatex-only failures. Strict mypy and ruff check/format are clean; plan validation and
  cross-reference audit are clean.

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
- **Status:** IN_PROGRESS
- **Priority:** high
- **Dependencies:** T-P2-11, T-P1-12
- **Human approval:** required
- **Traces to:** FR-15,HC-14
- **Description:** Seed SKOS-like taxonomy from module handbook, curriculum, folder map; bilingual labels; stored in curation/taxonomy.yaml.
- **Rationale:** FR-15; knowledge organization independent of folders.
- **Acceptance criteria:** Owner approves v0; every course maps to ≥1 domain.
- **Validation method:** Owner review.
- **Expected artifacts:** curation/taxonomy.yaml
- **Verification (2026-09-27):** IN_PROGRESS, not DONE: the acceptance criterion's own validation method
  requires the owner to approve Taxonomy v0, so this implementation is an explicitly unapproved draft rather
  than a delegated sign-off. `curation/taxonomy.yaml` now loads through `load_taxonomy()` with 43 bilingual,
  SKOS-like concepts organized under 10 curriculum-level domains. Broader/narrower links are reciprocal,
  `related` links are symmetric, every relationship resolves to a defined concept, and intentional poly-hierarchy
  covers finite-element methods, simulation technology, robotics, and sensor/actuator/bus systems. The additive,
  backward-compatible `CourseMapEntry.domains` field keeps course ownership in `course_map.yaml` without changing
  folder matching; all 42 real curated courses have at least one valid domain assignment. Real-file tests load both
  committed YAML files and enforce unique/resolved taxonomy references plus 42/42 course coverage. Focused curation
  and course tests: 31 passed. Full suite: 470 passed with only the four pre-existing `pdflatex`-only fixture-
  generation failures; strict mypy and ruff check/format are clean. Plan validation and cross-reference audit are
  clean. **Owner action needed to close this task**: review and approve, correct, or reject the complete domain
  structure, both bilingual labels, every broader/narrower/related edge, and every one of the 42 course-to-domain
  assignments. Until that review is recorded, T-P5-06 remains IN_PROGRESS and Taxonomy v0 is not approved.

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
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P1-02
- **Scope limit (owner decision 2026-11-04, docs/24):** the `T-P7-02` dependency was removed so the gateway can be built before SPIKE-MODELGW, **with mock or local backends only**. Real-provider adapters, credentials and provider acceptance/benchmarking remain T-P7-02's job and need further owner authorization (ADR-040).
- **Human approval:** none
- **Traces to:** ADR-025,HC-20,ADR-035
- **Description:** Role routing, adapters, fallbacks, sensitivity gate, accounting, response cache, structured outputs.
- **Rationale:** ADR-025, HC-20.
- **Acceptance criteria:** Fake-model tests; sensitivity gate blocks remote calls for restricted docs; cost logged.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/models/*
- **Verification (2026-11-04, Linux container; not run on the owner's Mac):** DONE within the owner-limited scope
  (mock/local backends only). `src/sbr/models/` provides `Gateway` (role routing over all docs/17 §1 roles,
  capability checks at construction, sensitivity gate, bounded retries with backoff for retryable errors, local-only
  fallbacks, in-memory content-addressed response cache, structured output validated against a Pydantic schema,
  `CallRecord` accounting with cost, tokens, latency and hashes, logged without content), a deterministic
  `MockProvider`, and an `OpenAICompatibleProvider` for a loopback inference server (stdlib only; proxies ignored,
  redirects refused, size cap, deadline). `sbr.config` gains `[models.providers]` with loopback-only URLs,
  `allow_remote` fixed to `false`, `api_key_env` names only, and role/provider reference validation; `sbr.egress`
  holds the shared predicates. `sbr models status [--probe]` added. **Acceptance:** fake-model tests are in
  `tests/models/` (72 tests, including the loopback HTTP integration tests); restricted content is refused for
  every role before any provider call, and remote providers are refused at configuration, construction and call
  time; cost is logged per call (0.0 locally). Full suite 640 passed, 5 skipped; ruff, strict mypy, plan validation,
  cross-reference audit and schema export check clean. **Not done (explicitly out of scope):** remote adapters and
  credentials (T-P7-02, not authorized); `rerank` and local vision adapters (no backend yet; configuring those roles
  fails validation instead of claiming support); a persistent response cache under `var/`; any measurement against a
  real local model server (none in this environment).

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
- **Update (2026-11-04):** Q-B04 is answered at the architecture level (ADR-040), but credentials, provider activation, paid services and remote data transmission are explicitly **not** authorized, so the acceptance criterion (working call to ≥2 roles' models via the chosen access path) cannot be met. Status stays BLOCKED; its requirements are unchanged.

### T-P7-03 — Answer schema with knowledge-layer basis
- **Phase:** P7
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P1-05
- **Human approval:** none
- **Traces to:** HC-11,ADR-034
- **Description:** AnswerSegment{text, basis, citations[]}; rendering rules for labels.
- **Rationale:** HC-11, ADR-034.
- **Acceptance criteria:** Schema + renderer tests.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/answer/schema.py
- **Verification (2026-09-27):** Added strict, frozen `AnswerSegment`/`AnswerCitation` models and the closed
  ADR-034 basis enum (`CORPUS`, `USER`, `AI_NOTE`, `EXTERNAL_APPROVED`, `EXTERNAL_PENDING`, `MODEL`). Citations
  carry exactly one typed `ku_id` or `external_id`, an exact provenance `Locator`, and an optional quote.
  Validator policy requires citations for evidence-bearing layers, limits CORPUS to KU citations and external
  layers to external-source citations, and requires USER/MODEL claims to stay uncited so mixed claims must be
  split into separately labeled segments. AI-note claims must resolve to underlying KU/external evidence.
  Deterministic Markdown rendering visibly labels every segment, never merges adjacent bases, renders locator
  details, and refuses `EXTERNAL_PENDING` unless the caller explicitly opts in. `AnswerSegment` is exported as
  `schemas/AnswerSegment.json` through the existing deterministic schema pipeline. 12 new tests plus all schema
  snapshot/round-trip tests pass (55 focused). Full suite: 419 passed plus only the same four pre-existing
  `pdflatex`-only failures; strict mypy, ruff, and schema export `--check` are clean.

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
- **Status:** DONE
- **Priority:** high
- **Dependencies:** T-P1-08
- **Human approval:** none
- **Traces to:** HC-23
- **Description:** Span model for nodes/tools/model calls; SQLite storage; `sbr trace`; optional OTel export.
- **Rationale:** HC-23.
- **Acceptance criteria:** Trace of a run fully reconstructable.
- **Validation method:** Tests.
- **Expected artifacts:** src/sbr/obs/trace.py
- **Verification (2026-09-27):** Added a standalone, migrated `var/traces/traces.sqlite` store with one immutable
  span row per node/tool/model-call event, stable per-run sequence ordering, same-run parent linkage, UTC timing,
  outcomes, error class, model/prompt metadata, structured tool-call summaries, token/cost accounting, and
  hash-plus-160-character-preview redaction before SQLite receives content. `span_scope()` inherits run/span context
  and closes spans on success, `SystemExit`, `KeyboardInterrupt`, or any `BaseException`. `sbr trace <run_id>` renders
  the complete nested tree as JSON and reports unknown runs without a traceback. Seven focused trace/migration/CLI
  tests pass; full suite is 427 passed plus only the four known pdflatex-only failures. Strict mypy and ruff
  check/format are clean; schema export check, plan validation, and cross-reference audit are clean.

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
- **Status:** DONE
- **Priority:** critical
- **Dependencies:** T-P4-13, T-P1-12
- **Human approval:** none
- **Description:** Vault + ledger backups; DB snapshots; optional artifacts; restore drill.
- **Rationale:** Durability.
- **Acceptance criteria:** Restore drill succeeds on a clean machine path.
- **Validation method:** Drill log.
- **Expected artifacts:** src/sbr/ops/backup.py, docs runbook
- **Verification (2026-09-27):** Added a fail-closed, atomic backup package containing online SQLite snapshots of
  registry and traces through the existing `Migrator.backup("p13")` path, a verified full-history `git bundle
  create --all` of the independent vault, and byte-preserving copies of all eight production-loader-validated
  curation files. Every payload has manifest size/SHA-256 integrity metadata. Restore accepts only a non-existent,
  protected-root-safe target; validates the manifest, hashes, SQLite integrity/schema versions, Git bundle and
  curation schemas; stages the canonical `var`/vault/curation layout; clones and verifies full vault history; and
  publishes with one rename. The automated clean-machine drill writes real state, creates a backup, deletes the
  original live state and Migrator side snapshots, restores into a brand-new path, then opens the restored registry
  via `RegistryDB.open()` and reads its row/schema version, reads the restored trace, verifies vault HEAD/log/content,
  and round-trips restored curation YAML. Seven focused backup/restore tests pass. The artifact store is explicitly
  deferred because it is optional and rebuildable; `sbr backup --dest` is the create-side CLI and restore remains a
  tested Python API. Eight focused tests and 451 full-suite tests pass; the only four failures are the known
  `pdflatex`-unavailable fixture-generator tests. Strict mypy, ruff check/format, plan validation, and cross-reference
  audit are clean. See `docs/39_BACKUP_AND_RESTORE.md` for the procedure and drill log.

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
- **Status:** DONE
- **Priority:** high
- **Dependencies:** T-P1-06
- **Human approval:** none
- **Description:** Upgrade tests on copies of real DBs; rollback scripts.
- **Rationale:** R-18.
- **Acceptance criteria:** All migrations tested N-1->N.
- **Validation method:** CI suite.
- **Expected artifacts:** tests/migrations/*
- **Verification (2026-09-27):** Added `tests/migrations/` with a five-entry matrix over every actual registry
  migration currently on disk. For each migration N, the suite builds a real SQLite database at N-1, copies it
  through SQLite's online-backup API (so WAL state is included), upgrades only the copy to N, checks the exact
  applied version plus `integrity_check` and retained seed data, runs N's checked-in down script, verifies the
  schema returns exactly to N-1 with no FK violations, then reapplies N and rechecks integrity/data. Added
  `tools/validate_migrations.py` for the task's populated-real-DB requirement: it opens the source DB read-only,
  creates a transactionally consistent disposable copy, rolls the copy back one version and forward again,
  verifies integrity and all table row counts, confirms source size/mtime are unchanged, and deletes only its
  own uniquely named scratch directory. The drill ran against the existing 184,885,248-byte production registry:
  PASS at schema v5, 13 tables / 323,135 rows checked, source unchanged. Seven new CI tests pass (five adjacent
  transitions plus copy-drill success/refusal); strict ruff checks pass.

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
