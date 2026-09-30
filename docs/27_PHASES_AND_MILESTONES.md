# 27 — Phases and Milestones

The phases follow the mission's starting hypothesis, **re-ordered by real dependencies**. The changes from the hypothesis are:
- **P3 is new: Gold Set & Extraction Spikes.** Parser and math choices need ground truth from the owner's corpus *before* the extraction pipeline is built (mission: "do not choose a parser without testing").
- **Math and visual understanding are merged into P4 extraction** (they are tiers of one pipeline) and are decided in P3.
- **Baseline grounded QA (P7) comes before graph (P8) and agentic orchestration (P9)**, so every advanced feature is measured against a baseline (R-26).
- **Obsidian/VaultWriter core is pulled forward into P4** (T-P4-13), because normalized notes are written from P4 onward. P10 adds living knowledge on top.
- Task details: `28_TASK_REGISTER.md`. Dependencies: `29_DEPENDENCY_MAP.md`.

| Phase | Name | Tasks |
|---|---|---|
| P0 | Corpus Audit & Architecture Planning | 9 (8 DONE) |
| P1 | Foundations | 13 |
| P2 | Source Registry, Manifest & Exact Dedup | 14 |
| P3 | Gold Set & Extraction Spikes (decision gate) | 11 |
| P4 | Extraction & Normalization | 16 |
| P5 | Knowledge Units, Near-Dedup & Taxonomy | 9 |
| P6 | Retrieval Infrastructure | 13 |
| P7 | Baseline Grounded QA | 8 |
| P8 | Knowledge Graph | 9 |
| P9 | Agentic Orchestration | 11 |
| P10 | Obsidian Curation & Living Knowledge | 8 |
| P11 | Gap Analysis | 5 |
| P12 | External Research & Approval | 7 |
| P13 | Scale-out, Hardening & Operations | 10 |
| P14 | Project/Idea Integration (future, DEFERRED) | 3 |
| | **Total** | **146** |

---

## P0 — Corpus Audit & Architecture Planning
- **Objective:** Understand the real corpus; design the architecture; create durable project memory.
- **Prerequisites:** none.
- **Tasks:** T-P0-01 … T-P0-09 (T-P0-09 = t2 re-audit and reconciliation, docs/37).
- **Outputs:** `audit/phase0/*`, `docs/00–36`, `CLAUDE.md`, `tools/validate_plan.py`.
- **Tests:** `python tools/validate_plan.py` passes.
- **Exit criteria:** Owner approves the plan (Q-B05) → T-P0-08 DONE.
- **Failure/recovery:** If the owner amends the architecture, update the decision log and task register, then re-run the validator.

## P1 — Foundations
- **Objective:** Repository, config, read-only source guard, ids and hashing, schemas, SQLite with migrations, provenance core, run ledger, job queue, governor, CLI, curation ledger, fixtures.
- **Prerequisites:** P0 exit.
- **Tasks:** T-P1-01 … T-P1-13.
- **Outputs:** the `sbr` package skeleton with a tested core.
- **Tests:** TS-SAFE, TS-PROV-1/2, TS-QUEUE (crash-resume), TS-MIG, unit tests.
- **Exit criteria:** All P1 tests green. A crash-resume test with a killed subprocess passes. Source-write attempts are provably blocked.
- **Failure/recovery:** The foundations are small and fully testable. Fix forward.

## P2 — Source Registry, Manifest & Exact Dedup
- **Objective:** A complete, incremental, read-only registry of all source files as content-addressed blobs, with classification, sensitivity, exact dedup, archives, twins, genre and course mapping.
- **Prerequisites:** P1 (SourceFS, ids, queue, curation).
- **Tasks:** T-P2-01 … T-P2-14.
- **Outputs:** `registry.sqlite`, manifest and duplicates reports, sensitivity list, course map, refreshed audit (after Q-B01).
- **Tests:** TS-CHANGE (move/modify/delete), TS-ARCH (archive safety), dedup equality versus the Phase-0 results, classification spot checks.
- **Exit criteria:** A real-corpus scan and hash completes read-only. Re-scan is incremental (< 5 min when nothing changed). The owner reviews the sensitivity flags. The manifest report exists.
- **Failure/recovery:** The scan is resumable. The registry can be rebuilt by rescanning.

## P3 — Gold Set & Extraction Spikes (decision gate)
- **Objective:** Build ground truth from MBI material and decide the parser, math, OCR and figure stack and the compute policy with evidence.
- **Prerequisites:** P2 (canonical blobs, genre) for sample selection.
- **Tasks:** T-P3-01 … T-P3-11 (SPIKE-PARSER, -MATH, -OMML, -OCR, -COMPUTE, -FIGURE).
- **Outputs:** MBI-Gold-Extract/Math/Layout; extraction harness; spike reports; ADR-007…010 updated.
- **Tests:** harness unit tests; reproducible spike runs.
- **Exit criteria:** T-P3-11 approved by the owner. Chosen engines meet the gates (20 §4). The compute policy is decided (Q-B03).
- **Failure/recovery:** If no engine meets the math gate, choose the best one with stricter uncertainty thresholds (more items flagged), escalate high-value pages to a remote tier if policy allows, and record the residual risk (R-01).

## P4 — Extraction & Normalization
- **Objective:** Production extraction pipeline (triage + tiers + twin fusion + annotations + structure) to DocIR, normalized Markdown and the protected vault writer, proven on pilot wave W0.
- **Prerequisites:** P3 decision (the engines); P1 (queue, provenance).
- **Tasks:** T-P4-01 … T-P4-16.
- **Outputs:** DocIR artifacts; normalized notes for W0; quality reports.
- **Tests:** harness regression on gold sets; TS-ART, TS-MATH, TS-VAULT.
- **Exit criteria:** The owner accepts the W0 pilot (T-P4-15). Metrics are within spike results. VaultWriter tests are green.
- **Failure/recovery:** Artifacts are versioned and append-only. The reprocess queue handles flagged items.

## P5 — Knowledge Units, Near-Dedup & Taxonomy
- **Objective:** Turn DocIR into citable KUs with stable anchors, symbol links, near-duplicate/version relations, taxonomy v0, topics, concept candidates and references.
- **Prerequisites:** P4 pilot outputs.
- **Tasks:** T-P5-01 … T-P5-09.
- **Outputs:** `knowledge.sqlite` (KUs, anchors, symbols, relations); `curation/taxonomy.yaml` v0.
- **Tests:** TS-ANCHOR; labeled-sample evaluations; the annotated-variant hard check.
- **Exit criteria:** KU and anchor targets met. The owner approves taxonomy v0.
- **Failure/recovery:** Re-segmentation is versioned. Anchors are aligned.

## P6 — Retrieval Infrastructure
- **Objective:** Measured hybrid retrieval: gold set, harness, chunk views, embeddings, lexical, vector, math index, fusion, dedup collapse, reranking and evidence packs.
- **Prerequisites:** P5 KUs.
- **Tasks:** T-P6-01 … T-P6-13 (SPIKE-EMBED, -HYBRID, -CHUNK, -MATHRET, -RERANK).
- **Outputs:** indexes, `sbr search`, spike reports, ADR-016…019 decided.
- **Tests:** retrieval harness; rebuild tests; filter tests.
- **Exit criteria:** Retrieval metrics beat the BM25-only and dense-only baselines on MBI-Retrieval. Duplicate rate in the top-10 is ≤ 5%.
- **Failure/recovery:** Indexes are rebuildable. EmbeddingSets coexist.

## P7 — Baseline Grounded QA
- **Objective:** Model gateway plus a grounded answer pipeline with knowledge-layer labels and a validator. This is the **baseline** for everything after it.
- **Prerequisites:** P6; SPIKE-MODELGW (can run as early as after P0 approval).
- **Tasks:** T-P7-01 … T-P7-08.
- **Outputs:** `sbr ask`; QA gold set; baseline scores.
- **Tests:** TS-GROUND; gateway sensitivity tests; QA eval.
- **Exit criteria:** Citation precision and layer-label accuracy are recorded. The unsupported-claim injection test catches ≥95%.
- **Failure/recovery:** Gateway fallbacks. Cached model outputs.

## P8 — Knowledge Graph
- **Objective:** An evidence-backed concept graph with quality gates; decide whether graph retrieval helps; assess Graphify.
- **Prerequisites:** P5 concepts; P7 gateway.
- **Tasks:** T-P8-01 … T-P8-09 (SPIKE-GRAPH, -GRAPHIFY).
- **Outputs:** graph tables, quality report, graph tools (if the gate passes), Obsidian links.
- **Tests:** evidence validity; quality sampling; retrieval ablation.
- **Exit criteria:** Edge precision meets the target. The graph retrieval decision is recorded.
- **Failure/recovery:** Rejected edges go to the curation ledger. Re-extraction is versioned.

## P9 — Agentic Orchestration
- **Objective:** Orchestrator with planning, routing, sufficiency, conflicts, visual inspection and JIT upgrades, fully traced, and proven better than the baseline.
- **Prerequisites:** P7 baseline; P8 (optional graph tool).
- **Tasks:** T-P9-01 … T-P9-11 (SPIKE-AGENTFW, -MULTIMODAL).
- **Outputs:** orchestrator, traces, MultiHop eval.
- **Tests:** TS-AGENT (all transitions with fake models); TS-CONFLICT; agentic eval.
- **Exit criteria:** Gain on MultiHop with no QA regression; cost within budget.
- **Failure/recovery:** Behaviors are feature-flagged. The system falls back to the baseline pipeline.

## P10 — Obsidian Curation & Living Knowledge
- **Objective:** User-note ingestion, AI synthesis notes, concept notes, living maps, staleness handling and edit-conflict handling.
- **Prerequisites:** P4 VaultWriter; P7 validator; P8 curated graph.
- **Tasks:** T-P10-01 … T-P10-08.
- **Outputs:** vault `concepts/`, `ai/`, `maps/`, review queues.
- **Tests:** TS-VAULT end-to-end; staleness tests.
- **Exit criteria:** The owner approves the conventions and the Control Engineering map. Zero user-note overwrites in tests.
- **Failure/recovery:** Git history of the vault. Fork semantics.

## P11 — Gap Analysis
- **Objective:** Reference models, coverage scoring, gap classification and reports ("What do I know about X?").
- **Prerequisites:** P5 taxonomy; P8 concepts; P10 maps.
- **Tasks:** T-P11-01 … T-P11-05.
- **Exit criteria:** Seeded-gap precision and recall are recorded. The owner finds the reports useful (3 domains).
- **Failure/recovery:** Reference models are versioned in the curation ledger.

## P12 — External Research & Approval
- **Objective:** A durable research workflow with source evaluation, proposals, approval and contamination guards.
- **Prerequisites:** P9 framework; P11 gaps; P10 conventions.
- **Tasks:** T-P12-01 … T-P12-07.
- **Exit criteria:** The contamination tests pass. The owner rates 10 research runs.
- **Failure/recovery:** Durable checkpoints. The quarantine is separate from the main indexes.

## P13 — Scale-out, Hardening & Operations
- **Objective:** Full-corpus waves, backups, rebuild/migration/swap/upgrade drills, MCP server, media and code tracks (if in scope), runbooks.
- **Prerequisites:** P4 pilot, P3 compute policy, P2 audit refresh (Q-B01).
- **Tasks:** T-P13-01 … T-P13-10. *Note:* T-P13-01 can start after P4 and run in the background while P5–P12 proceed.
- **Exit criteria:** W1+W2 complete; the W3 text tier is complete; all drills pass.

## P14 — Project/Idea Integration (future)
- **Objective:** Idea and project objects and generation workflows built on gaps, strengths and cross-domain links. DEFERRED; hooks only.

---

## Milestones

| Milestone | Definition | Phases |
|---|---|---|
| **M0 Plan approved** | T-P0-08 DONE | P0 |
| **M1 Safe registry** | Full read-only registry with dedup and sensitivity; incremental re-scan | P1–P2 |
| **M2 Extraction decided** | Spike-based parser/math/OCR decisions; gold sets exist | P3 |
| **M3 Pilot knowledge** | W0 normalized in the vault; KUs and anchors; taxonomy v0 | P4–P5 |
| **M4 Searchable brain** | Measured hybrid retrieval over W0/W1 | P6 (+ W1 in P13 running in the background) |
| **M5 Grounded answers** | `sbr ask` with citations and layer labels; baseline metrics | P7 |
| **M6 Connected & agentic** | Validated graph; orchestrator beats the baseline | P8–P9 |
| **M7 Living second brain** | Maps, AI notes, user notes, gap reports | P10–P11 |
| **M8 Growing brain** | Approved research loop; full-corpus waves; drills; MCP | P12–P13 |
