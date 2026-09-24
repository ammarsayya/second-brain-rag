# 18 — Storage Strategy

## 1. Roots and layout

```
D:\MBI-BRAIN\                        SOURCE ROOT (read-only, authoritative evidence)

D:\AgenticAI\second-brain-rag\       PROJECT
  CLAUDE.md  README.md  pyproject.toml
  docs\                              project memory (this documentation)
  src\sbr\                           application package
  tests\                             tests + synthetic fixtures (no copyrighted corpus content)
  config\                            sbr.toml (+ profiles), exclusion rules, role→model config
  curation\                          AUTHORITATIVE human decisions (git-tracked YAML)  [ADR-029]
     taxonomy.yaml  course_map.yaml  canonical_overrides.yaml  exclusions.yaml
     concept_curation.yaml  approvals.yaml  sensitivity_overrides.yaml
  tools\                             planning/ops scripts (validate_plan.py)
  schemas\                           exported JSON Schemas (T-P1-05)
  migrations\                        numbered SQL migrations per DB (T-P1-06)
  eval\                              gold sets (blob+page refs, local only) and eval reports
  reports\                           generated reports (manifest, sensitivity, mirrors, quality) — local only
  audit\                             phase-0 audit artifacts (local only; sensitive paths)
  var\                               REBUILDABLE (gitignored)
     db\registry.sqlite              files, blobs, observations, jobs, runs, activities
     db\knowledge.sqlite             documents, sections, KUs, equations, figures, concepts, edges, claims
     artifacts\<b3[:2]>\<b3>\<extractor@ver>\   DocIR JSON, crops, OCR, per-stage manifests
     archive_extract\                new documents extracted from archives
     index\lexical\<index_ver>\      Tantivy / FTS
     index\lance\<embedding_set>\    LanceDB tables
     index\graph\                    graph snapshots (GraphML/Parquet) for fast load
     cache\render\                   page renders (LRU, size-capped)
     cache\llm\                      response cache (content-hash keyed)
     research\quarantine\            fetched external sources pending approval
     traces\ logs\ backups\

<VAULT ROOT> (Q-B02; proposed D:\MBI-VAULT)     OBSIDIAN VAULT (git-versioned, ADR-015)
  sources\<domain>\<course>\…md      SOURCE_DERIVED normalized notes (regenerable)
  concepts\                          AI_GENERATED concept notes (+ user edits → forks)
  maps\                              living domain maps
  ai\                                AI synthesis notes
  notes\                             USER_AUTHORED (system never writes here)
  research\                          approved external research notes
  inbox\research\  inbox\review\     proposals, verification queues
  _assets\                           figure crops (knowledge-bearing, W1/W2)
  _system\                           README for the vault, templates (read-only for the owner)

<EXTERNAL ACCEPTED ROOT> (proposed D:\MBI-EXTERNAL)   approved external sources (read-only after approval)
```

## 2. Store choices

| Data | Store | Why | Status |
|---|---|---|---|
| Registry, jobs, runs, activities | SQLite (WAL) | Zero-ops, transactional, proven at millions of rows, easy backup (`.backup`) | ACCEPTED (ADR-004) |
| Knowledge objects and graph edges | SQLite (separate DB file) | Same; separation allows rebuilding knowledge without re-scanning | PROPOSED with ADR-020 |
| DocIR and artifacts | Files (JSON + PNG), content-addressed | Parser-independent, inspectable, append-only | ACCEPTED (ADR-011) |
| Vectors | LanceDB | Embedded, Arrow-native, filtering, multiple tables and versions | PROPOSED (ADR-018) |
| Lexical | Tantivy or FTS5 | See 13 | PROPOSED (ADR-016) |
| Human decisions | YAML in git (`curation/`) | Diffable, reviewable, survives `var/` deletion | ACCEPTED (ADR-029) |
| Knowledge notes | Markdown in the vault (git) | Obsidian, human-readable, versioned history | ACCEPTED (ADR-014); git PROPOSED (ADR-015) |

## 3. Capacity (D: had 377 GB free at t0 and less after t1 growth)

Estimates: registry DB < 1 GB; knowledge DB 2–10 GB; DocIR artifacts 5–30 GB; figure crops 5–20 GB (knowledge-bearing only);
vectors 2–8 GB per EmbeddingSet (2 coexisting during a swap); lexical 2–5 GB; render cache capped at 20 GB; LLM cache 1–5 GB. Total ≈ **30–100 GB**.
A disk floor guard (stop at 50 GB free) applies. `var/` may be moved to C: via config if D: fills (same physical SSD).

## 4. Rebuildability matrix

| Delete this | Rebuild from | Cost |
|---|---|---|
| `var/index/*` | knowledge.sqlite + artifacts | Hours (embedding pass) |
| `var/db/knowledge.sqlite` | artifacts + curation ledger | Hours (segmentation, LLM-assisted steps hit the cache) |
| `var/artifacts` | sources + ledger | **Days to weeks** (vision/OCR tiers). Backups are optional but recommended once W1/W2 are done (Q-I09) |
| `var/db/registry.sqlite` | Rescan sources + ledger | < 1 h (hashing) |
| vault `sources/` | DocIR renderer | Minutes |
| vault `notes/`, `research/`, approvals | **Not rebuildable: back up** | — |
| `curation/` | **Not rebuildable: git + backup** | — |

## 5. Backups (T-P13-02)

Vault and curation: git commit per batch, plus a push to a private remote or external disk (Q-I09). Optional nightly `var/` snapshot of the
SQLite DBs (`.backup` API) and artifacts. A restore drill is part of P13.
