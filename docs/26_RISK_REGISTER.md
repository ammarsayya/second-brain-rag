# 26 — Risk Register

Probability (P) and Impact (I): L/M/H. Owner/component = where mitigation lives.

| ID | Risk | P | I | Mitigation | Detection | Owner/component |
|---|---|---|---|---|---|---|
| R-01 | **Mathematical extraction corruption** (wrong LaTeX that looks right) | H | H | OMML-first twins; validation V1–V5; calibrated confidence; false-confidence metric gate; crops always cited | MBI-Gold-Math; render-compare; owner flags | Math tier (P3/P4) |
| R-02 | **Silent provenance loss** | M | H | PV-1 DB constraints; activity-required writes; locator integrity job | `sbr doctor`; TS-PROV tests | Data layer (P1) |
| R-03 | **Duplicate explosion** in retrieval and coverage stats | H | M | Exact dedup before extraction; near-dup groups; dedup collapse in retrieval; coverage over canonical docs | Duplicate rate in top-10 metric | Registry (P2), retrieval (P6) |
| R-04 | Annotated variants collapsed as duplicates → loss of owner knowledge | M | H | ADR-032; annotation detection before near-dup canonicalization; hard test | Dedup eval hard check | P4/P5 |
| R-05 | **Graph noise** (low-value edges) | H | M | Evidence-required edges; status levels; quality gates; graph used only for expansion | Edge precision sampling | Graph (P8) |
| R-06 | **Hallucinated graph relationships** | M | H | Edges without verifiable spans → `inferred`, excluded; cross-domain extra scrutiny | Evidence validity rate | P8 |
| R-07 | **Poor retrieval** (German compounds, abbreviations, math) | M | H | Hybrid; decompounding; abbreviation map; math index; gold-set tuning | MBI-Retrieval metrics | P6 |
| R-08 | **Model/provider lock-in** | M | M | Gateway roles; adapters; cached outputs; eval-gated swaps | Adapter test suite | P7 |
| R-09 | OpenCode models not programmatically accessible as expected | M | M | SPIKE-MODELGW early in P7; direct provider adapters as fallback | Spike result | P7 |
| R-10 | **Parser lock-in** | M | M | DocIR (ADR-011); multi-engine adapters | Parser swap drill | P4, P13 |
| R-11 | **Very long initial ingestion** on CPU | H | M | Triage, waves, JIT, optional remote compute (Q-B03), dedup-first | ETA reporting per stage | P4, P13 |
| R-12 | **Excessive resource usage** (laptop thermals, RAM, disk) | M | M | Governor; disk floor; render cache cap; nighttime windows | Resource metrics | P1/P4 |
| R-13 | **Index corruption** | L | M | Rebuildable indexes; integrity checks | Count and consistency checks | P6 |
| R-14 | **User-note overwrite** | L | H | VaultWriter ownership and hash checks; git; tests | TS-VAULT tests; git diff audit | P4/P10 |
| R-15 | **Citation drift** after re-extraction or re-chunking | M | H | KU anchors; alignment; tombstones; stale marking | Citation stability metric in the parser drill | P5/P13 |
| R-16 | **Stale AI synthesis** | H | M | Input fingerprints; staleness queue; `status: stale` banner | Staleness report | P10 |
| R-17 | **External research contamination** | M | H | Quarantine; pending index; approval ledger; tests | TS-PROV-3; audits | P12 |
| R-18 | **Schema migration problems** | M | M | Versioned migrations; backup-before-migrate; migration tests on DB copies | Migration suite | P1/P13 |
| R-19 | Corpus changes during processing (ongoing migration) | H | M | Content addressing; move detection; Q-B01 freeze for statistics | Scan diffs | P2 |
| R-20 | Sensitive data sent to external models | M | H | Sensitivity classes; gateway gate; redacted logs | Gateway audit log | P2/P7 |
| R-21 | LLM judge miscalibration (grounding and eval) | M | M | Judge ≠ generator; calibration on owner labels; deterministic checks first | Judge-agreement metric | P7/P9 |
| R-22 | Owner time for gold sets insufficient | M | M | AI-drafted gold; minimal verification UI; prioritize math | Gold-set progress | P3 |
| R-23 | License constraints (AGPL PyMuPDF, GPL Marker, NC-licensed models) | M | L | Private use only; permissive alternatives listed; license column in 36 | Dependency review | P1/P3 |
| R-24 | Disk exhaustion on D: (377 GB free at t0, shrinking) | M | M | Capacity plan (18 §3); relocatable `var/`; floor guard | Governor | P1 |
| R-25 | Prompt injection from external research content | M | M | Content treated as data; tool permissions; approval path | Research logs | P12 |
| R-26 | Over-engineering (agents, graph) before the baseline works | M | M | Baseline RAG in P7 before agentic P9; spike gates | Phase exit criteria | Planning |
| R-27 | Presentation build-step pages (65 PDFs, ~8.8k pages at t2) multiply math/OCR cost and flood retrieval with near-identical pages | H | M | Build-step detection in triage; process the final state only; intra-document near-dup collapse | Build-step report; duplicate rate in top-10 | P4/P5 (T-P4-04, T-P5-03) |
| R-28 | Password-protected PDFs (13) silently missing from the knowledge base | M | L | `encrypted` flag; listed in the coverage report; owner passwords optional (Q-N07) | Manifest report | P2 (T-P2-04) |
| R-29 | Personal identity documents (ID scans, CVs, certificates) processed or sent to external models | M | H | `restricted` default rules; gateway sensitivity gate; counts-only reporting; owner may relocate (Q-I12) | Sensitivity report review | P2/P7 (T-P2-05, ADR-035) |
| R-30 | Knowledge that exists only inside unextracted archives (342 ZIPs, 16,102 members at t2) is missed | M | M | Archive member inventory and extraction to `var/` (T-P2-08) | Archive census reconciliation | P2 |
| R-31 | Third-party reference HTML (24.5k man-page files) floods lexical retrieval and coverage statistics | H | M | ADR-038 `third_party_reference` class excluded by default | Retrieval eval noise metrics | P2/P6 |
