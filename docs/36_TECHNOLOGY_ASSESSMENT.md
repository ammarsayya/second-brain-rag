# 36 — Technology Assessment

This is the per-dependency evaluation required by the mission (§38). Confidence refers to the **recommendation**, given current evidence.
"Local suitability" means suitability for the verified hardware: CPU-only, 64 GB RAM, one SSD, Windows 11.
Nothing marked PROPOSED is chosen. Spikes decide (34).

## Document processing

| Dependency | Purpose / why needed | Alternatives | Advantages | Disadvantages | Maturity | Local suitability | Scalability | Resources | Lock-in | Recommendation | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **PyMuPDF** | Text tier: text, fonts, spans, bboxes, rendering | pypdfium2, pdfplumber, pypdf | Very fast, rich span/font data (used in the audit), rendering | AGPL license (fine for private use) | High | Excellent | ~10²–10³ pages/s | Low | Low (behind DocIR) | PROPOSED text tier (pypdfium2 as a permissive fallback) | High |
| **Docling** (IBM, MIT) | Layout, tables, reading order, formula enrichment, DOCX/PPTX | MinerU, Marker, Unstructured | Permissive license, CPU-friendly models, Office support, active | Formula quality below MinerU on dense math (reported) | Medium-high | Good | Moderate on CPU | Medium | Low | Candidate in SPIKE-PARSER | Medium |
| **MinerU 2.5** | High-quality parsing incl. formulas (best published formula CDM) | Docling, PaddleOCR-VL | Top formula/text scores; pipeline and VLM backends | VLM backend GPU-oriented; heavier installation | Medium | Pipeline plausible on CPU, VLM slow | GPU-bound for VLM | High | Low | Candidate (pipeline backend; UniRec integration) | Medium |
| **PaddleOCR-VL 1.5/1.6** | 0.9B document VLM, SOTA on OmniDocBench v1.5 | MinerU2.5, HunyuanOCR | Compact, multilingual, formulas and tables | ~30 s/page CPU class; Paddle stack on Windows | Medium | Poor for bulk, OK for targeted pages | GPU needed for bulk | High | Low | Candidate for the targeted/remote tier | Medium |
| **Marker** (+Surya/texify) | PDF→Markdown with math | Docling, MinerU | Good Markdown, optional LLM mode | GPL-3; model weights under restricted license | Medium | GPU preferred | Moderate | Medium-high | Medium | Candidate; license check | Low-medium |
| **UniRec-0.1B** | Crop-level text+formula recognition | PP-FormulaNet, UniMERNet, texify, pix2tex | 0.1B params, 2–9× faster than VLMs at similar accuracy (paper) | New (Dec 2025); packaging maturity unknown | Low-medium | **Promising for CPU** | Good | Low | Low | Top candidate in SPIKE-MATH | Medium |
| **pandoc** (OMML→LaTeX) | Exact Office math conversion | docx2python + custom OMML XSLT, LibreOffice | Deterministic, mature | Edge cases in matrices and accents | High | Excellent | Excellent | Low | None | PROPOSED (SPIKE-OMML) | High |
| **LibreOffice headless** | .doc/.ppt → modern formats (into var/) | MS Office COM automation | Free, scriptable | Conversion fidelity varies | High | Good | OK | Medium | None | PROPOSED for legacy formats | Medium |
| **Tesseract 5 (deu)** | OCR for scanned pages | PaddleOCR, parser OCR, VLM | Mature, CPU, German models | Weaker on complex layouts and math | High | Good | Good | Low | None | Candidate in SPIKE-OCR | Medium |
| python-docx / python-pptx | Office structure and notes | docx2python | Mature | No math rendering (OMML via pandoc) | High | Excellent | Excellent | Low | None | PROPOSED | High |

## Retrieval

| Dependency | Purpose | Alternatives | Pros | Cons | Maturity | Local | Scale | Resources | Lock-in | Recommendation | Conf. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Tantivy** (tantivy-py) | BM25 with German stemming | SQLite FTS5, LanceDB FTS, Elasticsearch/OpenSearch | Fast, embedded, analyzers | Python binding less feature-rich than Rust | High (engine) | Excellent | 10⁷ docs | Low | Low | PROPOSED (SPIKE-HYBRID) | Medium |
| SQLite FTS5 | BM25 inside SQLite | Tantivy | Zero extra dependency, transactional | No German stemmer; needs pre-stemming | High | Excellent | Good | Low | None | Alternative | Medium |
| **LanceDB** | Vector store + filters + versioned tables | Qdrant, sqlite-vec, pgvector, Chroma | Embedded, Arrow/Lance files, hybrid support, rebuildable | Young format evolution; Windows edge cases to check | Medium | Good | 10⁸ vectors | Low-medium | Low (rebuildable) | PROPOSED | Medium |
| Qdrant | Vector DB | LanceDB | Mature filtering, quantization | Server process (or local mode) | High | Good | Very high | Medium | Low | Alternative | Medium |
| **Qwen3-Embedding-0.6B** | Multilingual embeddings | BGE-M3, mE5-large-instruct, EmbeddingGemma-300m, jina-v3 (NC license) | Strong multilingual, instruction-aware | CPU throughput to be measured | Medium-high | OK | Batch-bound | Medium | Low (EmbeddingSets) | Candidate | Medium |
| **BGE-M3** | Dense + sparse + multi-vector | Qwen3-Embedding | One model for hybrid signals, 8k context | Older; larger | High | OK | Batch-bound | Medium | Low | Candidate | Medium |
| **bge-reranker-v2-m3 / Qwen3-Reranker-0.6B** | Cross-encoder reranking | LLM reranking | Large precision gains typical | CPU latency (~50 pairs/query) | High/Medium | OK | Per query | Medium | Low | Candidates (SPIKE-RERANK) | Medium |
| ranx | IR metrics and fusion | pytrec_eval | Simple, includes fusion methods | — | Medium-high | Excellent | — | Low | None | PROPOSED | High |

## Knowledge and graph

| Dependency | Purpose | Alternatives | Pros | Cons | Recommendation | Conf. |
|---|---|---|---|---|---|---|
| **SQLite edge tables + NetworkX/igraph** | Graph storage and analytics | LadybugDB, Neo4j, FalkorDB, ArcadeDB | No server, transactional, fits in memory at our scale, PPR/communities available | No Cypher; hand-written traversals | PROPOSED (ADR-020) | Medium-high |
| LadybugDB | Embedded Cypher graph (Kuzu fork) | Neo4j | Embedded, columnar, Cypher | Young fork after Kuzu's archival (Oct 2025) | Escape hatch only | Medium |
| Neo4j | Graph DB server | — | Mature ecosystem | JVM server, ops, licensing tiers | Rejected for now | High |
| Microsoft GraphRAG | Community-summary GraphRAG | LightRAG, HippoRAG 2 | Global questions | LLM cost over all chunks, noise | REJECTED as-is (ADR-022) | Medium-high |
| HippoRAG 2 ideas (PPR over concepts) | Multi-hop retrieval | Neighborhood expansion | Good multi-hop results in the literature | Needs a clean concept graph | Test in SPIKE-GRAPH | Medium |
| **Graphify** | Folder → KG with confidence labels, communities, Obsidian export, MCP | Own graph | Good exploration UX; confidence-label pattern | File-level, no page provenance, no math, agent-batch cost at scale | Not core; exploration candidate (ADR-021) | Medium |
| Obsidian | Human interface | Logseq, custom UI | Owner uses it; Markdown; links; ecosystem | Not a backend | ACCEPTED as interface (ADR-014) | High |

## Agentic system

| Dependency | Purpose | Alternatives | Recommendation | Conf. |
|---|---|---|---|---|
| Custom state machine + Pydantic | Orchestrator | LangGraph, Pydantic AI | Leading hypothesis for the orchestrator (small, testable) → SPIKE-AGENTFW | Medium |
| LangGraph | Durable workflows, interrupts, checkpointers | Custom SQLite workflow engine, DBOS, Temporal (too heavy) | Candidate for the Research workflow | Medium |
| Pydantic AI | Typed agents and tools | — | Candidate | Medium |
| **LiteLLM** | Provider adapters under our Gateway | Thin in-house adapters, OpenCode server | Candidate (SPIKE-MODELGW) | Medium |
| OpenCode server (`opencode serve`) | Access to OpenCode-configured providers via an HTTP/OpenAPI SDK | Direct provider APIs | Session/agent-oriented API; evaluate fit | Low-medium |
| MCP Python SDK | Expose sbr tools to agents | — | PROPOSED for P13 | High |

## Infrastructure

| Dependency | Purpose | Alternatives | Recommendation | Conf. |
|---|---|---|---|---|
| **SQLite (WAL)** | Registry, jobs, knowledge, traces | PostgreSQL, DuckDB | ACCEPTED for registry (ADR-004) | High |
| Own SQLite job queue | Resumable stage processing | Celery/RQ (need a broker), Prefect/Dagster (heavy), Huey (SQLite backend) | PROPOSED own implementation (small, fits provenance) | Medium-high |
| BLAKE3 | Content ids | SHA-256 | ACCEPTED (ADR-003) | High |
| uv + Python 3.12 | Environments | conda, pip-tools | ACCEPTED (ADR-005) | High |
| Arize Phoenix (local) | OTel trace UI and eval views | Langfuse (Docker), none | PROPOSED optional (ADR-033) | Medium |
| git (vault + curation) | History and backup | Internal versioning | PROPOSED (ADR-015) | Medium-high |

## Evaluation

| Dependency | Purpose | Recommendation | Conf. |
|---|---|---|---|
| Own `sbr eval` harness | All benchmarks with version metadata | PROPOSED core | High |
| ranx | IR metrics | PROPOSED | High |
| RAGAS / DeepEval | LLM-judge metrics | Optional; in-house judge prompts calibrated on owner labels preferred | Medium |
| KaTeX (via Node) or MathJax | LaTeX syntax validation and rendering for render-compare | Candidate in SPIKE-MATH | Medium |
