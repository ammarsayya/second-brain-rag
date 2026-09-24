# 24 — Decision Log

Statuses: PROPOSED · ACCEPTED · DEFERRED · REJECTED · SUPERSEDED.
**Rule:** unvalidated major technology choices are never ACCEPTED. They stay PROPOSED with a linked spike.
ACCEPTED entries are architectural principles that follow directly from the hard constraints or from Phase-0 evidence, plus low-risk foundation choices.
All entries are dated 2026-09-24 unless noted. Format per entry: context → decision → rationale → alternatives → evidence → consequences.

---
### ADR-001 — Three-root architecture (sources / project var / vault + ledger)
- **Status:** ACCEPTED (the vault *location* is open: Q-B02)
- **Context:** HC-01, HC-12. User notes and AI history must survive deletion of derived infrastructure.
- **Decision:** Sources are read-only. The project `var/` is rebuildable. The Obsidian vault and the git-tracked curation ledger hold authoritative non-source knowledge and decisions.
- **Rationale:** Rebuildability requires authoritative human/AI knowledge to live outside `var/`. The project dir must not hold the only copy of user notes.
- **Alternatives:** vault inside the project dir (risk: confusion with rebuildable data; repo bloat); vault inside `D:\MBI-BRAIN` (violates the read-only corpus); Brain vault (violates Brain governance at this scale).
- **Evidence:** Mission §1, §19–20; Brain governance (no project mirrors in the Brain).
- **Consequences:** Three configured roots; the VaultWriter; separate backups for vault and ledger.

### ADR-002 — The system never writes to source roots
- **Status:** ACCEPTED · **Context:** HC-01/03 · **Decision:** SourceFS read-only access layer with static and runtime guards (22 §1).
- **Alternatives:** trust convention (rejected: silent-destruction risk). · **Consequences:** archive members are extracted to `var/` only; normalization never happens in place.

### ADR-003 — Content-addressed identity (BLAKE3-256) with path observations
- **Status:** ACCEPTED
- **Context:** 58.6% duplicate PDFs; the corpus changed by +34k files and 675 moves *during the audit*.
- **Decision:** Blob id = BLAKE3-256 of bytes. Paths are observations over time. xxh3 may be used as a fast pre-filter only.
- **Rationale:** Moves and renames cost nothing; dedup is exact; provenance survives reorganization.
- **Alternatives:** SHA-256 (slower, equally valid); path-based ids (break on every move, as observed).
- **Evidence:** 03 §1, §4. **Consequences:** Initial hashing of ~560 GB (videos may be hashed at low priority, see T-P2-02).

### ADR-004 — SQLite (WAL) for registry and operational metadata
- **Status:** ACCEPTED
- **Decision:** `registry.sqlite` (files, blobs, observations, jobs, runs, activities).
- **Rationale:** Local-first, zero-ops, transactional, sufficient for ~10⁵ files and ~10⁷ rows; simple backup; no lock-in (plain SQL).
- **Alternatives:** PostgreSQL (ops overhead, no need yet); DuckDB (analytics-oriented, weaker at concurrent transactional writes).
- **Consequences:** A single-writer discipline; workers write through a small write queue or short transactions.

### ADR-005 — Python 3.12 with uv-managed environments
- **Status:** ACCEPTED · **Context:** System Python is 3.14.7; ML/OCR wheels (torch, paddle, onnxruntime) lag new Python versions.
- **Decision:** Pin 3.12 (uv) for the project; spike-specific environments may differ (e.g. isolated parser envs).
- **Alternatives:** 3.14 (wheel availability risk), conda (heavier). · **Consequences:** Extractors that conflict can run as isolated subprocess environments behind the DocIR contract.

### ADR-006 — Deterministic pipeline, narrowly scoped agents
- **Status:** ACCEPTED · **Context:** HC-22/23 · **Decision:** All ingestion, dedup, indexing and provenance code is deterministic. LLMs are used only at interpretation points (07 §2) with typed outputs.
- **Consequences:** Most of the system is testable without models.

### ADR-007 — Tiered, triaged, value-prioritized extraction with lazy (JIT) upgrade
- **Status:** ACCEPTED (strategy). Engines: ADR-008/009/010 PROPOSED.
- **Context:** No GPU. ~330k (t0) to ~500k (t1 est.) unique pages; 80% textbook pages; math is corrupted in text layers; ~26k textless pages.
- **Decision:** Per-page triage routes pages to the cheapest sufficient tier. Waves W0–W3 (08 §4) process course material fully first. Textbooks get the text tier plus structure first, with math and figure tiers applied JIT or in background batches. An optional external compute tier is used only under the owner's policy (Q-B03).
- **Alternatives:** Full VLM parsing of everything locally (thousands of CPU hours); cloud-parse everything (privacy, copyright and cost decisions not yet made); text layer only (fails HC-05).
- **Evidence:** 03 §5–7; published CPU timings of ~30 s/page for 0.9B document VLMs (PaddleOCR-VL paper) versus ~6 s/page for the UniRec-integrated MinerU pipeline on GPU-class hardware (to be re-measured on CPU in SPIKE-COMPUTE).
- **Consequences:** Coverage is uneven over time and must be visible in the maps (extraction_quality per document).

### ADR-008 — Document parser / layout stack
- **Status:** PROPOSED → SPIKE-PARSER (T-P3-05)
- **Candidates:** PyMuPDF (text tier; AGPL, note the license) or pypdfium2 (permissive) as the text tier; for layout and full parsing: Docling (MIT, CPU-friendly, formula enrichment), MinerU 2.5 (pipeline and VLM backends; best published formula CDM), PaddleOCR-VL 1.5/1.6 (0.9B; top of OmniDocBench v1.5), Marker (GPL-3, model license restrictions).
- **Working hypothesis (to be tested):** PyMuPDF/pypdfium2 text tier plus Docling or the MinerU pipeline for layout on routed pages.
- **Decision criteria:** MBI-Gold accuracy (text, reading order, tables), CPU throughput, RAM, license, maintenance, Windows support.

### ADR-009 — Math recognition stack; OMML-first twin fusion
- **Status:** OMML-first twin fusion **ACCEPTED** (exact, deterministic, evidenced by 592 OMML equations in the thesis DOCX). Recognizer **PROPOSED** → SPIKE-MATH, SPIKE-OMML.
- **Candidates:** UniRec-0.1B, PP-FormulaNet, UniMERNet, MinerU formula module, Docling formula enrichment, texify, pix2tex (baseline); remote multimodal LLM as an upper bound or fallback.
- **Consequences:** Validation (V1–V5, 10 §2) is mandatory regardless of the engine.
- **Scope note (2026-09-24, t2 re-audit, docs/37 §10):** "Office-native equation objects" means OMML **and** Equation Editor 3.0 / MathType OLE objects (MTEF). 70 unique legacy `.doc` files carry Equation 3.0 signatures, and 2 DOCX embed Equation 3.0 OLE objects. Measured OMML: 49 unique OOXML files, 3,260 equations; the thesis has 422 (the earlier "592" was an over-count). **Status unchanged:** OMML-first is ACCEPTED; the conversion path for Equation 3.0/MathType is decided in SPIKE-OMML.

### ADR-010 — OCR engine for textless pages
- **Status:** PROPOSED → SPIKE-OCR (T-P3-08) · **Candidates:** Tesseract 5 (deu+eng), PaddleOCR (PP-OCRv5), the Docling/MinerU built-in OCR, a VLM (remote).

### ADR-011 — Parser-independent DocIR
- **Status:** ACCEPTED · **Decision:** All extractors emit DocIR (09 §2). Downstream never depends on a parser's native format.
- **Rationale:** Avoids parser lock-in (R-10); allows mixing engines per page and tier. **Consequences:** An adapter per engine.

### ADR-012 — Decomposition ≠ chunking; Knowledge Units are the citation unit
- **Status:** ACCEPTED · **Evidence:** HC-13; citation drift risk. **Consequences:** Chunk policies are versioned and disposable; KU anchors are stable (05 §6).

### ADR-013 — Provenance classes
- **Status:** ACCEPTED · **Decision:** SOURCE_DERIVED, USER_AUTHORED, USER_ANNOTATION, AI_GENERATED, EXTERNAL_PENDING, EXTERNAL_RESEARCH, MODEL_KNOWLEDGE (answer-only) (05 §1).
- **Rationale:** The mission's minimum four plus: USER_ANNOTATION (evidenced by the owner's red-ink annotations in scripts), EXTERNAL_PENDING (quarantine), MODEL_KNOWLEDGE (answer labeling).

### ADR-014 — Obsidian vault as the human interface; backend independent
- **Status:** ACCEPTED · **Consequences:** VaultWriter ownership rules; the system works without Obsidian.

### ADR-015 — Git versioning of the vault for AI-note history
- **Status:** PROPOSED (owner preference; Q-I09 for remotes) · **Alternatives:** an internal version table only (less transparent); Obsidian File Recovery (not durable).

### ADR-016 — Lexical engine
- **Status:** PROPOSED → SPIKE-HYBRID · **Candidates:** Tantivy (German stemming), SQLite FTS5 (+ external stemming), LanceDB FTS.

### ADR-017 — Embedding model
- **Status:** PROPOSED → SPIKE-EMBED · **Candidates:** Qwen3-Embedding-0.6B, BGE-M3, multilingual-e5-large-instruct, EmbeddingGemma-300m (and jina-v3 subject to license).

### ADR-018 — Vector store: LanceDB (embedded)
- **Status:** PROPOSED → SPIKE-HYBRID (integration) · **Alternatives:** Qdrant (local/server), sqlite-vec, pgvector. · **Rationale:** embedded, file-based, Arrow, filtering, versioning; low lock-in via rebuildability.

### ADR-019 — Reranker
- **Status:** PROPOSED → SPIKE-RERANK · **Candidates:** bge-reranker-v2-m3, Qwen3-Reranker-0.6B, LLM reranking.

### ADR-020 — Graph storage: relational edges + in-memory analytics (no graph DB server)
- **Status:** PROPOSED → SPIKE-GRAPH · **Alternatives:** LadybugDB (embedded Kuzu fork; escape hatch), Neo4j, FalkorDB (rejected for now: ops).
- **Evidence:** Kuzu archived Oct 2025 (acquisition) → avoid betting on a young embedded graph DB as the core store.

### ADR-021 — Graphify is not the core knowledge graph
- **Status:** PROPOSED → SPIKE-GRAPHIFY · **Rationale:** file-level LLM extraction without page provenance or equation modelling, and agent-batch extraction cost at our scale (12 §6). **Possible role:** exploration and visualization; code-track graphs.

### ADR-022 — Microsoft GraphRAG (global community summaries over all chunks)
- **Status:** REJECTED (revisit if SPIKE-GRAPH shows global-summary needs that the Maps cannot meet)
- **Rationale:** LLM indexing cost over ~10⁶ chunk views on a CPU-only, budget-conscious local system; noise; staleness. Hierarchical summaries are covered by curated Maps.

### ADR-023 — Agent topology: one orchestrator + two durable workflows
- **Status:** ACCEPTED (topology) · **Rationale:** 07 §2; avoids swarm complexity while supporting long-running, approval-gated research.

### ADR-024 — Agent/workflow framework
- **Status:** PROPOSED → SPIKE-AGENTFW · **Candidates:** custom state machine + Pydantic-typed LLM calls; LangGraph; Pydantic AI.

### ADR-025 — Model gateway with role routing; no direct provider calls
- **Status:** ACCEPTED (principle) · **Consequences:** HC-20; the sensitivity gate and accounting are centralized.

### ADR-026 — Access to OpenCode-configured models
- **Status:** PROPOSED → SPIKE-MODELGW; blocked on Q-B04.

### ADR-027 — Local embeddings and reranking
- **Status:** PROPOSED (confirm with SPIKE-EMBED throughput) · **Rationale:** privacy, cost, reproducibility for corpus-wide passes.

### ADR-028 — External research quarantine + owner approval before permanence
- **Status:** ACCEPTED (HC-10).

### ADR-029 — Curation ledger (git-tracked YAML) for human decisions
- **Status:** ACCEPTED · **Rationale:** human decisions must survive `var/` rebuilds (HC-12).

### ADR-030 — Video/audio media track deferred
- **Status:** DEFERRED (Q-I01) · **Context:** ~165 GB unique video at t0 (more at t1); CPU transcription is slow; the knowledge largely duplicates the scripts. Revisit in P13 with a spike.

### ADR-031 — Exact duplicates are never deleted; canonical + aliases
- **Status:** ACCEPTED · **Consequences:** Dedup is a relation, not an action on sources. Cleanup *suggestions* for the owner are a report only.

### ADR-032 — Annotated variants are distinct versions (USER_ANNOTATION), never collapsed
- **Status:** ACCEPTED · **Evidence:** 03 §6 (annotated dynamics script); 10.8% of sampled PDFs contain annotation objects.

### ADR-033 — Observability: OpenTelemetry traces with local Phoenix (optional)
- **Status:** PROPOSED · **Alternatives:** Langfuse (self-host via Docker, heavier), traces in SQLite only. The trace store in SQLite is ACCEPTED as the baseline; the Phoenix export is optional.

### ADR-034 — Answer schema with knowledge-layer basis per segment
- **Status:** ACCEPTED · **Decision:** each answer segment has `basis ∈ {CORPUS, USER, AI_NOTE→resolved, EXTERNAL_APPROVED, EXTERNAL_PENDING(opt-in), MODEL}` plus citations. Validator-enforced (HC-11).

### ADR-035 — Sensitivity gate for external model calls
- **Status:** ACCEPTED (policy defaults are configurable; Q-I04).

### ADR-036 — Code track (MATLAB/Java/C) scope
- **Status:** DEFERRED to P13 (Q-I07). Thesis MATLAB is flagged high-value for the equation↔code linking experiment.

### ADR-038 — Third-party generated reference documentation is registered but not ingested by default
- **Status:** PROPOSED (2026-09-24; t2 re-audit, docs/37 §15)
- **Context:** t2 contains 24,516 HTML files, 99.8% of them Linux man-pages in two identical trees plus a ZIP copy (12,246 unique contents), plus Javadoc and Eclipse help. Vendor manuals (NI, CoDeSys, Wonderware, LS-DYNA) are similar third-party reference material in PDF form.
- **Decision (proposed):** Classify generated or third-party reference documentation (man-page HTML, Javadoc, Doxygen, saved help systems) as `third_party_reference`: registered, deduplicated, **excluded from default knowledge ingestion and main indexes**. An optional separate, clearly labeled "reference" collection can be enabled later. PDF manuals remain normal documents (lower authority tier) unless the owner decides otherwise.
- **Rationale:** Thousands of near-template pages would dominate lexical retrieval and coverage statistics without adding owner or lecture knowledge. They are publicly re-obtainable.
- **Alternatives:** ingest everything (retrieval pollution); delete (forbidden; sources are read-only); ingest only man pages referenced by course material (possible future refinement).
- **Evidence:** `audit/phase0/t2/html_census_t2.jsonl`. **Consequences:** HTML needs no extractor in P4 for now; T-P2-04 adds the class; 08 §7 updated. The owner may override via the curation ledger (Q-I13).

### ADR-037 — MBI vault separate from the owner's Brain; the Brain holds registry metadata only
- **Status:** PROPOSED (Q-B02) · **Rationale:** Brain governance forbids project-documentation mirrors and bulk content. The corpus vault would add tens of thousands of notes.
