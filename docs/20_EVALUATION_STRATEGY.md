# 20 — Evaluation Strategy

Evaluation starts in P3, **before** major technology choices. Every phase adds benchmarks, and each benchmark becomes a regression gate.

## 1. Benchmarks (built from the owner's corpus; stored in `eval/` with gold labels in git, sources referenced by blob hash)

| Benchmark | Content | Built in | Labels by |
|---|---|---|---|
| **MBI-Gold-Extract** | ~120 stratified pages (LaTeX, Word-OMML-PDF, MathType, scanned typewriter, annotated, slides, tables, block diagrams, plots, code, DE/EN) | P3 (T-P3-01) | Owner-verified AI drafts |
| **MBI-Gold-Math** | ~300 equations with verified LaTeX + crops (incl. thesis OMML as exact ground truth for Word equations) | P3 (T-P3-02) | Twin OMML (exact) + owner verification of AI drafts |
| **MBI-Gold-Layout** | ~40 pages: reading order, figure–caption pairs, tables, headings | P3 (T-P3-03) | Owner-verified |
| **MBI-Retrieval** | ~150 queries: factual, definition, equation-by-name, equation-by-symbol, figure, exercise/solution, cross-course, cross-lingual, abbreviation, duplicate-trap | P6 (T-P6-01) | LLM-generated from KUs + owner review; relevance judgments pooled |
| **MBI-QA** | ~50 questions with reference answers + required citations; incl. "not in corpus" questions (for layer labeling) | P7 (T-P7-07) | Owner-reviewed |
| **MBI-MultiHop** | ~40 cross-domain / multi-hop questions (robotics ↔ control ↔ dynamics ↔ math) | P9 (T-P9-10) | Owner-reviewed |
| **MBI-Graph-Sample** | 200 sampled edges per extraction version | P8 (T-P8-06) | LLM judge + owner spot check |
| **MBI-Gaps-Seeded** | Held-out document sets defining known gaps | P11 (T-P11-05) | Constructed |
| **Research rubric** | 10 research runs rated on sources, faithfulness, usefulness | P12 (T-P12-07) | Owner |

## 2. Metrics

| Area | Metrics |
|---|---|
| Text extraction | CER/WER vs gold, reading-order edit distance, heading F1 |
| Equations | Exact match of normalized LaTeX, token edit distance, **render-compare similarity**, CDM-style character match, **false-confidence rate** (wrong but marked verified; the most important metric), coverage (detected/total) |
| Tables | TEDS (structure + content) |
| Figures | Detection F1 (knowledge-bearing), caption-pairing accuracy, decorative false-positive rate |
| Dedup | Exact: must be 100% (hash). Near-dup and version: precision/recall on a labeled pair set; **annotated variants never collapsed** (hard check) |
| Retrieval | Recall@5/10/50, nDCG@10, MRR, duplicate rate in top-10, per query type; cross-lingual subset |
| Reranking | ΔnDCG@10 vs latency |
| QA grounding | Citation precision (cited span supports the claim), citation recall (claims with citations), faithfulness (judge), **layer-label accuracy** (corpus vs model vs external), unsupported-claim rate |
| Provenance | % of answer claims resolvable to blob+page (target 100% for CORPUS basis), locator validity |
| Graph | Edge precision by type, evidence validity rate, cross-domain edge precision |
| Agentic | Answer quality delta vs baseline, iterations, stop-reason distribution, cost, latency |
| Gaps | Precision/recall on seeded gaps; owner usefulness rating |
| Research | Source authority mix, claim support rate, owner acceptance rate |
| Hallucination | Rate of claims not entailed by evidence nor labeled MODEL |
| Conflicts | Detection recall on constructed contradictions; no-erasure check |

## 3. Tooling (PROPOSED)

- Our own harness (`sbr eval <benchmark>`) with JSONL results and run metadata (versions of parser, models, prompts, index).
- IR metrics: `ranx` (or `pytrec_eval`).
- LLM-judge metrics: in-house judge prompts via the gateway `judge` role, calibrated against owner labels on a subset.
  RAGAS and DeepEval are candidates for faithfulness metrics but are not required dependencies (lock-in and version churn).
- Reports: Markdown in `eval/reports/` with trend tables.

## 4. Gates

| Gate | Condition (initial; revisited with data) |
|---|---|
| Parser/math choice (P3) | Best engine on MBI-Gold-Math with false-confidence rate ≤ 2% at chosen thresholds; throughput plan fits Q-B03 policy |
| Enable reranker (P6) | ΔnDCG@10 ≥ +0.03 and p95 latency acceptable on CPU |
| Enable graph expansion (P8) | Gain on MBI-MultiHop without loss on MBI-Retrieval |
| Orchestrator behaviors (P9) | No regression on MBI-QA grounding; gain on MultiHop |
| Model/prompt upgrades | No regression > 2 points on any gated metric |
| Embedding swap (P13) | New set ≥ old on MBI-Retrieval |

## 5. Human effort budget (Q-I06)

Gold creation needs owner time: roughly 6–12 hours in P3 (math and layout verification with a side-by-side tool) and 3–5 hours in P6/P7
(query and answer review). AI drafts minimize the effort. The owner verifies rather than authors.
