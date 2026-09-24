# 13 — Retrieval Architecture (PROPOSED)

RAG ≠ vector search. The corpus is German-dominant technical text with heavy abbreviation, compound nouns
("Übertragungsfunktion", "Zustandsrückführung"), math, and 58%+ duplicates. Each property calls for a specific component.

## 1. Pipeline

```
QUERY
 → UNDERSTANDING (lang, intent, domains, entities, math spans, course/genre hints)         [orchestrator]
 → DECOMPOSITION (sub-questions if multi-part/cross-domain)                                [orchestrator]
 → METADATA FILTERS (course, genre: exam/solution/script, domain, provenance class, date)  [deterministic]
 → PARALLEL RETRIEVAL per sub-question
      lexical/BM25 (German+English analyzers, decompounding, abbreviation expansion)
      dense (multilingual embeddings over chunk views; cross-lingual DE↔EN)
      math (symbol/structure n-grams over normalized LaTeX + equation-card embeddings)
      graph expansion (optional, PPR from query concepts; validated edges only)            [SPIKE-GRAPH]
      user notes & AI notes (same indexes, provenance-tagged)
      visual (figure cards; on-demand page inspection)                                    [SPIKE-MULTIMODAL]
 → FUSION (Reciprocal Rank Fusion, weights per query type; tuned on the gold set)
 → DEDUP COLLAPSE (duplicate/version groups → canonical + "also in: …"; keep annotated variants distinct)
 → RERANKING (cross-encoder, top-50 → top-k)                                               [SPIKE-RERANK]
 → EVIDENCE SELECTION (diversity across sources, coverage of sub-questions)
 → CONTEXT CONSTRUCTION (parent expansion, equation context rule, figure cards, token budget)
 → REASONING / SYNTHESIS (answer schema with basis labels)
 → GROUNDING VALIDATION → ANSWER + CITATIONS
```

## 2. Component justification

| Component | Justified because | Status |
|---|---|---|
| Lexical (BM25) | Exact technical terms, abbreviations (`PT2`, `DH`, `RGT`), equation labels, course names, German compounds. Dense models miss rare tokens | PROPOSED; engine per SPIKE-HYBRID |
| Dense | Paraphrase, cross-lingual (EN question over DE scripts), conceptual queries | PROPOSED; model per SPIKE-EMBED |
| Math index | Symbol and structure queries that neither BM25 on prose nor text embeddings handle (10 §5) | PROPOSED; SPIKE-MATHRET |
| Metadata filters | "Klausur", "Lösung", "RT2 SS2020", "in meinen Notizen": cheap, precise | ACCEPTED as necessary (SQL filters) |
| Dedup collapse | 58.6% duplicate PDFs would otherwise flood the top-k with identical evidence | ACCEPTED as necessary |
| Reranker | Usually a large precision gain. CPU cost must be measured | PROPOSED; SPIKE-RERANK |
| Graph expansion | Multi-hop and cross-domain questions | PROPOSED; enabled only if SPIKE-GRAPH shows a gain |
| Query decomposition | Cross-domain and multi-part questions | In the orchestrator (P9); the baseline (P7) runs without it for comparison |

## 3. Candidate technologies (details in 36_TECHNOLOGY_ASSESSMENT)

- **Lexical:** Tantivy (tantivy-py; German stemmer, custom tokenizers) vs SQLite FTS5 (simple, no German stemming built in → pre-stem tokens)
  vs LanceDB native FTS. German decompounding options: a CharSplit-style splitter, or dictionary-based splitting as a pre-tokenization filter.
- **Dense:** Qwen3-Embedding-0.6B, BGE-M3 (dense + sparse + multi-vector in one model), multilingual-e5-large-instruct,
  EmbeddingGemma-300m, jina-embeddings-v3 (license check: CC-BY-NC). All must run on CPU. Throughput is part of the spike.
- **Vector store:** LanceDB (embedded, Arrow/Lance files, metadata filtering, versioned tables; proposed) vs Qdrant (local mode or server)
  vs sqlite-vec vs pgvector (Postgres dependency).
- **Reranker:** bge-reranker-v2-m3, Qwen3-Reranker-0.6B, jina-reranker-v2 (license check), or an LLM reranker via the gateway (expensive).
- **Fusion:** RRF (k≈60 as a baseline) with per-query-type weights learned on the gold set (simple grid search, no black box).

## 4. Scale estimate (for sizing, verify in P6)

~330k pages at t0 (~500k at t1) → roughly 400k–900k chunk views. At 1024-dim float32 that is 1.6–3.7 GB of vectors (less with float16 or int8).
The lexical index is a few GB. CPU embedding throughput is the bottleneck (to be measured). Estimate: 5–30 chunks/s for 0.3–0.6B models
→ ~4–50 h per full embedding pass. That is acceptable as a background job and is why EmbeddingSets are versioned.

## 5. Math retrieval detail

- `math_tokens`: tokenization of `latex_normalized` into symbols, operators and structure markers (`\frac{`, `^{`, `_{`, `\begin{bmatrix}`).
  Indexed as unigrams, bigrams and structural paths (a lightweight symbol-layout-tree path approximation).
- Query parsing: detect LaTeX or Unicode math in the query; convert to the same tokens; also derive names via the equation-card index.
- Equation-card dense vectors: bilingual NL descriptions + variable meanings.
- Results always return with the equation context pack (10 §4).

## 6. Provenance-aware retrieval policies

- Default: search SOURCE_DERIVED + USER_AUTHORED + USER_ANNOTATION + AI_GENERATED + EXTERNAL_RESEARCH, with the provenance class
  in every hit. AINotes are **never** the sole evidence for a CORPUS claim. The validator follows AINote citations down to KUs.
- EXTERNAL_PENDING lives in a separate "pending" index used only by the Research workflow (PV-4).
- Sensitive documents: retrievable locally. Their text is never sent to external models unless policy allows it (the gateway enforces this).

## 7. Evaluation hooks

Every component is switchable per query via config flags. That enables ablations (dense only, BM25 only, hybrid, hybrid+rerank,
+graph, +math) on the gold set (20).
