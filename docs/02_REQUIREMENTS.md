# 02 — Requirements

IDs are referenced by the architecture, decision log, tasks and tests. `HC` = hard constraint (from the mission, non-negotiable).
`FR` = functional, `NFR` = non-functional. The last column traces each requirement to where it is satisfied.

## Hard constraints

| ID | Constraint | Satisfied by |
|---|---|---|
| HC-01 | Never destroy authoritative sources | ADR-002, SourceFS guard (T-P1-03), tests TS-SAFE-* |
| HC-02 | `D:\MBI-BRAIN` is the authoritative university corpus | Config source root (T-P1-02) |
| HC-03 | Initial interaction with the corpus is read-only (and the system stays read-only toward it) | ADR-002, T-P1-03 |
| HC-04 | Provenance is preserved through every transformation | 05_PROVENANCE_MODEL, ADR-013, T-P1-07 |
| HC-05 | Equations are first-class knowledge | 10_MATHEMATICAL_CONTENT, ADR-009 |
| HC-06 | Important technical figures are first-class knowledge | 11_VISUAL_CONTENT |
| HC-07 | User-authored notes are first-class knowledge | 19_OBSIDIAN_INTEGRATION, T-P10-02 |
| HC-08 | Never silently overwrite user-authored knowledge | VaultWriter (T-P4-13), T-P10-07 |
| HC-09 | AI-generated knowledge must be identifiable | Provenance class AI_GENERATED, frontmatter |
| HC-10 | External researched knowledge requires approval before permanent ingestion | ADR-028, 16_EXTERNAL_RESEARCH |
| HC-11 | Model knowledge must not masquerade as corpus knowledge | ADR-034 answer schema, grounding validator (T-P7-05) |
| HC-12 | Generated infrastructure must be rebuildable | ADR-001, ADR-029, rebuild drill T-P13-03 |
| HC-13 | Document decomposition ≠ retrieval chunking | ADR-012, 14_CHUNKING_STRATEGY |
| HC-14 | Knowledge taxonomy ≠ storage layout | 12_TAXONOMY, vault layout (19) |
| HC-15 | Relationships between disciplines are first-class | Knowledge graph (12), cross-domain eval |
| HC-16 | Incremental ingestion from day one | Registry, job queue (T-P1-09, T-P2-03) |
| HC-17 | Every important source-derived answer claim is traceable | Provenance chain, citations (T-P7-05/06) |
| HC-18 | Uncertain extraction stays uncertain | Confidence and status fields; no silent "best guess" |
| HC-19 | Preserve the history of evolving AI knowledge | Vault git history (ADR-015), AI note versions |
| HC-20 | Avoid model/provider lock-in | Model gateway (ADR-025) |
| HC-21 | Avoid unnecessary database lock-in | DocIR plus open formats (SQLite, Arrow/Lance, Markdown, YAML) |
| HC-22 | No agents where deterministic software is better | ADR-006, 07_AGENTIC_ARCHITECTURE |
| HC-23 | Agent decisions are observable and debuggable | Trace store (T-P9-09) |
| HC-24 | Long-running operations are resumable | Job queue with checkpoints (T-P1-09) |
| HC-25 | Architecture scales beyond university material | Multi source roots, source-type plugins |

## Functional requirements

| ID | Requirement | Phase |
|---|---|---|
| FR-01 | Register all files under configured source roots as path observations of content-addressed blobs | P2 |
| FR-02 | Detect new, modified, moved and deleted files incrementally | P2 |
| FR-03 | Classify files (format by magic bytes, knowledge class, genre, course, sensitivity) | P2 |
| FR-04 | Group exact duplicates, select a canonical copy, keep aliases; never delete | P2 |
| FR-05 | Inventory archive members without extracting into the source tree | P2 |
| FR-06 | Detect near-duplicates, versions, containment and annotated variants | P5 |
| FR-07 | Detect source twins (PDF ↔ DOCX/PPTX) and prefer exact Office math | P2/P4 |
| FR-08 | Extract text, structure, equations (LaTeX), figures, tables and annotations into a parser-independent DocIR with confidence | P4 |
| FR-09 | OCR textless pages | P4 |
| FR-10 | Produce normalized, Obsidian-compatible Markdown with page anchors and provenance frontmatter | P4 |
| FR-11 | Decompose documents semantically (book → chapter → section) independently of chunking | P4/P5 |
| FR-12 | Segment Knowledge Units (definition, derivation, example, exercise, solution, figure explanation …) | P5 |
| FR-13 | Link equations to variable definitions, context, figures and source pages | P5 |
| FR-14 | Extract bibliographic references and match them to corpus sources | P5 |
| FR-15 | Maintain a knowledge taxonomy (multi-parent, bilingual) separate from folders | P5 |
| FR-16 | Hybrid retrieval: lexical, dense, math-aware, metadata, graph, visual on demand, with fusion and reranking | P6/P8 |
| FR-17 | Grounded answers with citations and knowledge-layer labels | P7 |
| FR-18 | Knowledge graph of concepts and relations, each edge with evidence and confidence | P8 |
| FR-19 | Agentic orchestration: planning, decomposition, routing, sufficiency, conflict analysis, stop conditions | P9 |
| FR-20 | On-demand visual inspection of pages and figures by multimodal models | P9 |
| FR-21 | Ingest user-authored notes as first-class knowledge | P10 |
| FR-22 | Generate and version AI synthesis notes and living domain maps with citations | P10 |
| FR-23 | Gap analysis: what I have vs what the domain needs | P11 |
| FR-24 | Autonomous gap research with source evaluation and an approval gate | P12 |
| FR-25 | Conflict analysis that never erases contradictory evidence | P9 |
| FR-26 | Expose capabilities as CLI and (later) an MCP server for OpenCode, Claude Code and other agents | P7/P13 |
| FR-27 | Future: ideas and projects linked to concepts and gaps | P14 |

## Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-01 | Local-first on the verified hardware (no CUDA GPU, 64 GB RAM, one SSD) |
| NFR-02 | Resumable at item granularity; a crash loses at most the in-flight items |
| NFR-03 | Idempotent stages keyed by (subject, stage, stage_version) |
| NFR-04 | Every artifact records its producer (tool/model name, version, parameters hash) |
| NFR-05 | Parser, embedding and model versions can coexist; switching is config plus rebuild, not a migration of knowledge |
| NFR-06 | Resource limits: configurable worker count, RAM ceilings, low process priority, time windows |
| NFR-07 | Observability: run ledger, structured logs, agent traces, per-stage metrics |
| NFR-08 | Evaluation is continuous: each phase adds benchmarks that run in CI or locally |
| NFR-09 | Sensitive documents never leave the machine unless the owner's policy allows it |
| NFR-10 | Bilingual (German/English) handling in lexical analysis, concepts and answers |
| NFR-11 | Schema migrations are versioned, tested and reversible where feasible |
| NFR-12 | Free disk space is monitored; `var/` growth is bounded (artifact GC and a page-render cache cap) |
