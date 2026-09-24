# 08 — Ingestion Architecture

Ingestion is **deterministic, incremental, idempotent and resumable** (HC-16, HC-24, NFR-02/03).

## 1. Stages

| # | Stage | Key | Output | Deterministic? |
|---|---|---|---|---|
| S1 | `scan` | (root, relpath) | PathObservation (size, mtime, scan_id) | Yes |
| S2 | `hash` | path observation with changed (size, mtime) | Blob (BLAKE3), magic type | Yes |
| S3 | `change_detect` | scan diff | new/modified/moved/deleted events; stale marks | Yes |
| S4 | `classify` | blob | format, knowledge_class, genre, course, sensitivity, language guess | Rules (+ small LLM fallback for ambiguous genre later) |
| S5 | `dedup_exact` | blob | duplicate group, canonical PathObservation, aliases | Yes |
| S6 | `archive_inventory` | archive blob | ArchiveMembers (streamed hashes) | Yes |
| S7 | `twin_detect` | document blobs | twin candidates (PDF↔DOCX/PPTX) | Yes (confirmation in S14) |
| S8 | `triage` | blob × page | per-page routing record (tiers needed) | Yes (signals) |
| S9 | `extract_text` | blob@extractor | DocIR text blocks | Yes |
| S10 | `extract_office` | office blob | DocIR incl. exact OMML → LaTeX | Yes |
| S11 | `ocr` | routed pages | OCR blocks with confidence | Model (local) |
| S12 | `math` | routed regions | Equations (LaTeX, confidence, validation) | Model (local or remote per policy) |
| S13 | `figures_tables` | routed pages | Figures, tables, captions, crops | Model or heuristics |
| S14 | `fuse` | document | twin fusion, annotation layer, structure tree, final DocIR | Yes (alignment algorithms) |
| S15 | `normalize` | document | normalized Markdown in the vault | Yes |
| S16 | `segment` | document | KUs, anchors, symbol links | Rules + LLM assist |
| S17 | `near_dedup` | documents | near-dup, version, containment, annotated-variant relations | Yes |
| S18 | `index_*` | KU/chunk × index version | lexical, dense, math entries | Yes (embedding models deterministic given version) |
| S19 | `graph_*` | KU | concept mentions, relations (P8) | LLM + rules |

## 2. Job queue and checkpointing (T-P1-09)

- **Table `work_item`**: `(subject_id, stage, stage_version)` is unique. Fields: state (`pending|leased|done|failed|skipped|stale`),
  lease_owner, lease_expires, attempts, last_error, priority, wave, created/updated, output_manifest_id.
- **Idempotency:** a stage is "done" for a subject only for a specific `stage_version` (code version + config hash + model version).
  Bumping the version re-enqueues exactly the affected subjects.
- **Leases:** a worker leases N items and extends the lease while working. Crashed workers' leases expire and are re-leased.
- **Atomic completion:** artifacts are written to a temp dir, then renamed. The manifest row and work_item state are updated in one SQLite transaction.
- **Retries:** exponential backoff. After `max_attempts` → `failed` plus a review list. Poison items never block the queue.
- **Dependencies:** stage DAG per subject. A stage is enqueued only when its prerequisites are done.

## 3. Change detection semantics

| Event | Detection | Action |
|---|---|---|
| New path, new blob | Path unseen, hash unseen | Register blob, enqueue the pipeline |
| New path, known blob | Hash seen | Add alias only (no reprocessing) |
| Moved | Path gone + same blob at a new path in the same scan | Update observation. Knowledge is untouched; citations resolve via blob |
| Modified | Same path, new (size, mtime) → new hash | New blob version; `version_of` relation to the previous blob at that path; old knowledge kept and marked superseded-at-path |
| Deleted | Path gone, blob has no remaining observations | Blob state `orphaned`. Derived knowledge is **not deleted**; it is flagged `source_missing` for owner review (the owner may have moved it outside the roots) |

Fast path: `(size, mtime)` unchanged → skip hashing. A periodic full re-hash (monthly, low priority) verifies integrity (bit rot, mtime lies).

## 4. Processing waves (value-prioritized, ADR-007)

| Wave | Content | Est. unique pages (t0) | Fidelity |
|---|---|---|---|
| W0 | Pilot: thesis (+twins), Regelungstechnik 1 canonical, one scanned Statik script | ~2–3k | Full, human-reviewed |
| W1 | Owner-authored documents (thesis, Praxisphase, projects), exams and solutions, lecture scripts and slides of core domains (control, dynamics, robotics, modelling, FEM, math, measurement) | ~25–40k | Full (all tiers) |
| W2 | Remaining course material (all courses, labs, exercises) | ~30–50k (t1 growth) | Full |
| W3 | Textbooks and manuals (ISBN-named) | ~260k+ | Text tier + structure + TOC for all. Math/figure tiers on retrieval demand (JIT) or in scheduled background batches, prioritized by query hits and domain |
| W4 | Secondary: spreadsheets, code (MATLAB/Java), `.fig` renders | — | Specialized tracks (P13) |
| Deferred | Video/audio | ~165 GB unique at t0 | ADR-030 |

## 5. Resource governor (NFR-06)

Config: `max_workers_cpu` (default 6 of 12 threads), `max_ram_gb` (default 40), process priority `BELOW_NORMAL`,
optional time windows (e.g. nights), disk-space floor (stop when D: free < 50 GB), and per-stage concurrency limits
(for example, only 1 heavy vision model process). Throughput and ETA are reported per stage in `sbr status`.

## 6. Archives (FR-05)

Archives are **containers**. S6 streams member entries (zip, rar via `rarfile`/`unrar`, 7z via `py7zr`) without writing to the source tree,
hashes each member and records `ArchiveMember`. Members whose hash matches an existing blob are marked already present
(the owner extracted them manually). New document members are extracted **into `var/archive_extract/<container>/`** and
registered as blobs with provenance `from_archive=<container_blob>/<member>`. Safety limits apply: max total uncompressed size,
max ratio (zip-bomb guard), no path traversal, no execution, and nesting depth ≤ 3. CP437 or other mojibake names are repaired
for display only.

## 7. Exclusions (config, curation-overridable)

Default exclude (registered, never processed): `__MACOSX/`, `._*`, `thumbs.db`, `.DS_Store`, `desktop.ini`, zero-byte files,
`.metadata/` (Eclipse), `_ProjectScratch/`, `slprj/`, `*.class`, `*.exe/*.dll/*.msi/*.bat` (never executed), CAE scratch
(`.wbjn`, `.mechdb` … registered as `tool_artifact`), `.git/` internals. **Third-party generated reference documentation** (man-page HTML, Javadoc, Doxygen, saved help trees; 24.5k HTML files at t2) is classified `third_party_reference`, registered and deduplicated, and excluded from default ingestion (ADR-038, PROPOSED). **Password-protected PDFs** are flagged `encrypted` and never bypassed. **Presentation build-step pages** are collapsed at triage (T-P4-04). Images are registered but processed only when
referenced or requested (their knowledge is usually already in documents; many are lab/render photos).
