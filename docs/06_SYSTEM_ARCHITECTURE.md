# 06 — System Architecture (PROPOSED)

**Status:** PROPOSED. Structural principles are ACCEPTED (see 24). Engine choices are pending spikes (see 34).

## 1. Architectural drivers (from the audit)

1. **Math fidelity cannot come from text layers** (03 §6). Visual recognition or Office twins are needed, and both are expensive on CPU.
2. **No GPU.** ~330k unique PDF pages at t0, ~450–550k projected at t1. 80% are textbook pages; 2,373 short course documents total only 21k pages.
3. **58.6% exact PDF duplication**, mirrored folders, near-duplicates and annotated variants.
4. **The corpus is still changing.** Identity must be content-based.
5. **User and AI knowledge live side by side** with the source-derived knowledge and must never be clobbered.

## 2. Layered architecture

```
┌──────────────────────────────── INTERFACES ─────────────────────────────────┐
│ CLI `sbr` │ MCP server (P13: OpenCode / Claude Code / other agents) │ Obsidian vault │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │
┌───────────────▼──────────────── AGENTIC LAYER (07) ─────────────────────────┐
│ Answer Orchestrator (state machine) │ Research Workflow (durable, approval) │
│ Curation Workflow (batch: maps, AI notes, gaps) │ Tool registry │ Trace store │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │ tools (typed, deterministic services)
┌───────────────▼──────────────── KNOWLEDGE SERVICES ─────────────────────────┐
│ Retrieval service (13): lexical │ dense │ math │ metadata │ graph │ fusion │ rerank │
│ Evidence pack builder │ Grounding validator │ Graph service (12) │ Vault service (19) │
│ Model Gateway (17): role→model routing, sensitivity gate, accounting, cache │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │
┌───────────────▼──────────────── KNOWLEDGE BUILD PIPELINE (deterministic) ───┐
│ P2 Registry: scan → hash → change-detect → classify → exact-dedup → twins → archives │
│ P4 Extraction: triage → text tier → office tier → OCR tier → math tier → figure/table tier │
│               → annotation layer → structure → DocIR → normalized Markdown           │
│ P5 Knowledge: KU segmentation → symbols → near-dedup → anchors → taxonomy → citations  │
│ P6 Indexing: chunk views → lexical │ embeddings │ math index │ graph build (P8)        │
│ Job queue (SQLite) · checkpoints · leases · retries · run ledger · resource governor  │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │
┌───────────────▼──────────────── STORAGE (18) ───────────────────────────────┐
│ SOURCES (read-only)   D:\MBI-BRAIN (+ future roots, external-accepted root)          │
│ VAULT (authoritative) sources/ concepts/ maps/ notes/ ai/ research/ inbox/  [git]     │
│ CURATION LEDGER       curation/*.yaml (overrides, taxonomy, approvals)       [git]    │
│ VAR (rebuildable)     registry.sqlite · knowledge.sqlite · artifacts/ · lance/ ·      │
│                       lexical/ · graph/ · cache/ · traces/ · logs/                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 3. Key architectural decisions (summary; full records in 24)

| Area | Decision | Status |
|---|---|---|
| Roots | Sources read-only / project `var/` rebuildable / vault plus curation ledger authoritative | ACCEPTED (ADR-001, 002, 029) |
| Identity | BLAKE3 content-addressed blobs, path observations | ACCEPTED (ADR-003) |
| Metadata store | SQLite (WAL) | ACCEPTED (ADR-004) |
| Intermediate representation | Parser-independent DocIR with per-element confidence | ACCEPTED (ADR-011) |
| Extraction strategy | Triage → tiered engines → value-prioritized waves → lazy JIT upgrade | ACCEPTED as strategy (ADR-007); engines PROPOSED (ADR-008/009/010) |
| Knowledge units | Decomposition ≠ chunking; KU is the unit of citation | ACCEPTED (ADR-012) |
| Retrieval | Hybrid (lexical + dense + math + metadata, graph optional) with RRF and reranking | PROPOSED (ADR-016…019) |
| Graph | Relational edge tables + in-memory analytics; no graph server | PROPOSED (ADR-020) |
| Agents | One orchestrator + two durable workflows; everything else is tools or steps | ACCEPTED topology (ADR-023); framework PROPOSED (ADR-024) |
| Models | Gateway with role routing; local embeddings | ACCEPTED principle (ADR-025); specifics PROPOSED |

## 4. Data flow: a PDF from disk to an answer

1. **Scan** sees `…\Reg1\sk\[4]_RGT_1_Modellierung_linearer_Systeme_SS20.pdf` and records a PathObservation.
2. **Hash** computes BLAKE3. The blob is new, so it is registered. Other paths with the same blob become aliases.
3. **Classify**: pdf, document, genre=lecture_script (from `sk` and the name), course=Regelungstechnik 1 (from `RGT_1`), semester SS20, sensitivity=normal.
4. **Triage** each page: text layer OK; math fonts = MathType → `math_tier=needed`; drawings → figure candidates.
5. **Extract**: the text tier gives blocks and reading order. The math tier recognizes formula regions (after SPIKE-MATH) and stores
   LaTeX with confidence and a crop reference. The figure tier detects a block diagram and its caption.
6. **Structure**: the section tree comes from numbering and fonts. **Normalized Markdown** is written to `vault/sources/…` by the VaultWriter.
7. **KU segmentation**: "Definition Übertragungsfunktion" becomes a definition KU containing the equation `G(s)=Y(s)/U(s)` and its variable definitions.
8. **Index**: chunk views are built. Lexical tokens (German stems, math tokens), a dense embedding, and a math index entry for the equation card are written.
9. **Ask**: "Wie lautet die Übertragungsfunktion eines PT2-Glieds und was bedeutet D?" The orchestrator plans:
   domain = control, needs_math = true. It runs hybrid retrieval and math retrieval, reranks, and builds an evidence pack.
   The sufficiency judge says yes. The answer is synthesized with CORPUS segments citing KUs, and the grounding validator checks each claim.
   The answer is returned with citations `[RGT 1 Skript SS20, Folie 23]`.

## 5. Self-challenge (Step 9 of the mission)

| Question | Answer in this architecture | Residual risk |
|---|---|---|
| **Where can it fail?** | Math recognition quality; noisy concept graphs; LLM judges misjudging grounding; disk space; long ingestion on CPU | R-01, R-05, R-06, R-11, R-12 |
| **What assumptions are unverified?** | That CPU-feasible formula recognizers reach acceptable accuracy on MathType/German scripts; that lexical+dense hybrids beat dense alone here; that graph retrieval helps cross-domain questions; that OpenCode models are reachable programmatically | Each has a spike (34); decisions stay PROPOSED |
| **What becomes expensive at 530 GB?** | Not bytes (76% video, excluded) but **pages × vision models** and **LLM calls per KU** (relation extraction, synthesis). Mitigations: dedup first (-58% PDFs); triage (only ~20% of pages are math-heavy); waves (course docs 21k pages first); lazy JIT upgrade; cost-bounded relation extraction on canonical docs only; optional rented GPU or cloud (Q-B03) | Full-fidelity textbook processing may remain partial for a long time. This is acceptable and visible in coverage maps |
| **What if we change embedding models?** | EmbeddingSets are versioned and coexist. Build the new set in the background, evaluate it on the gold set, flip the config, then drop the old set. KUs and citations are untouched | Rebuild time (~hours on CPU). Planned drill T-P13-05 |
| **What if we change parsers?** | DocIR is parser-independent. The new extractor writes a new artifact version, anchors align (PV-7), and citations are preserved or tombstoned with review | Alignment errors → stale-note review queue. Drill T-P13-06 |
| **What if an extraction is wrong?** | Every element carries confidence and a crop. The owner or the system can flag it; the reprocess queue targets it with a better tier; old versions are kept; AINotes citing it go stale | Undetected silent errors in high-confidence items. Mitigated by gold-set calibration and render-compare validation |
| **What if the user edits an Obsidian note?** | USER_AUTHORED notes are never written. If the owner edits a *generated* note, the VaultWriter detects the hash mismatch, leaves the file untouched and reclassifies it (user-modified); the regenerated version goes to a sibling or conflict file (19 §4) | Owner confusion. Mitigated by clear frontmatter and banners |
| **What if the graph has hallucinated relations?** | Edges require evidence spans mentioning both ends, carry status and confidence, and pass sampling-based precision gates. Retrieval uses the graph only for expansion, never as sole evidence. Answers cite KUs, not edges | Noise dilutes expansion. SPIKE-GRAPH measures the net effect before enabling it |
| **What if processing stops halfway?** | Items are leased from the SQLite job queue. Completion is recorded atomically with artifact manifests; a restart resumes pending and expired leases. Artifacts are written temp-then-rename | Corrupted SQLite on power loss → WAL plus periodic backups plus rebuildability |
| **Can every index be rebuilt?** | Yes: `var/` is derived from sources, vault and ledger. The drill T-P13-03 proves it. Exceptions are recorded, not hidden: expensive model outputs (vision LaTeX, AI descriptions) are *cached artifacts*. Rebuilding them costs compute, so artifact caches are backed up optionally | Compute cost of a full rebuild. Artifact backup is optional (Q-I09) |
| **Can every answer be traced?** | CORPUS claims → KU → blocks → locator → blob → path. MODEL claims are labeled as such. EXTERNAL claims → approved proposal → external source copy | LLM may mislabel. The validator checks citations; the eval measures layer-label accuracy |

## 6. Deployment shape (local-first)

- One Python package `sbr` (3.12, managed by uv) with CLI entry points. Worker processes are spawned by the job runner with a resource governor.
- No servers are required for core function (SQLite, LanceDB and Tantivy are embedded). Optional local services:
  Phoenix (traces), Ollama or llama.cpp (local LLMs), OpenCode server (model access; SPIKE-MODELGW).
- Migration path: storage adapters (Repository pattern) isolate SQLite, Lance and Tantivy. Moving to Postgres/pgvector,
  Qdrant or a graph DB later is an adapter plus a rebuild, not a redesign (HC-21).
