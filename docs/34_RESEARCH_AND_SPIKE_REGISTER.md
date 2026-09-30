# 34 — Research and Spike Register

A spike is a time-boxed experiment that turns a PROPOSED decision into ACCEPTED or REJECTED **with evidence from the owner's corpus**.
Each spike defines: question, candidates, data, metrics, decision rule, time-box, owner of the decision, linked ADR and task.

| Spike | Task | Question | Candidates | Data | Metrics / decision rule | Time-box | ADR | Status |
|---|---|---|---|---|---|---|---|---|
| **SPIKE-PARSER** | T-P3-05 | Which layout/parsing engine(s) handle MBI PDFs best on CPU? | PyMuPDF / pypdfium2 baseline, Docling, MinerU pipeline, PaddleOCR-VL 1.5+, Marker | MBI-Gold-Extract + Layout | Text CER, reading order, heading F1, TEDS, s/page, RAM, failure rate, license. Choose the best quality whose throughput fits the compute policy | 4 days | ADR-008 | NOT_STARTED |
| **SPIKE-MATH** | T-P3-06 | Which formula recognizer and validation setup gives acceptable LaTeX with honest confidence? | UniRec-0.1B, PP-FormulaNet, UniMERNet, MinerU formula, Docling formula, texify, pix2tex; remote multimodal LLM (upper bound) | MBI-Gold-Math (~300; by source kind: Word, MathType, LaTeX, scanned) | Normalized exact match, token edit, render-compare, **false-confidence rate ≤ 2%** at the chosen threshold, s/formula on CPU | 5 days | ADR-009 | NOT_STARTED |
| **SPIKE-OMML** | T-P3-07 | Is OMML→LaTeX conversion exact enough, and can DOCX equations be aligned to PDF pages? **(t2 scope extension: Equation Editor 3.0 / MathType OLE objects in legacy .doc)** | pandoc; alternative OMML→MathML→LaTeX converters; for Equation 3.0/MathType (MTEF): LibreOffice import→OMML or an MTEF converter | Thesis (422 equations), Praxisphase (388), exercise DOCX/PPTX; physics exam .doc files with Equation 3.0 | ≥98% render-correct; alignment ≥95% correct pages | 2 days | ADR-009 | NOT_STARTED |
| **SPIKE-OCR** | T-P3-08 | Which OCR works for German scanned and typewriter pages, and (t2) for English photographed slide captures (`Ckurs`)? | Tesseract 5 deu, PaddleOCR PP-OCRv5, parser built-in OCR, remote VLM | Scanned gold pages | CER, speed, confidence calibration | 2 days | ADR-010 | NOT_STARTED |
| **SPIKE-COMPUTE** | T-P3-09 | How long and how costly are the waves under each compute option? | Local CPU, rented GPU (open models), cloud OCR/LLM APIs | Measured speeds from the spikes above | Time/cost/privacy table per wave; owner decision (Q-B03) | 1 day | ADR-007 | NOT_STARTED |
| **SPIKE-FIGURE** | T-P3-10 | Can knowledge-bearing figures be separated from decoration cheaply? | Heuristic rules; small classifier | Gold layout pages | Precision/recall of knowledge-bearing detection | 2 days | — (11) | NOT_STARTED |
| **SPIKE-EMBED** | T-P6-04 | Which embedding model gives the best DE/EN technical retrieval on CPU? | Qwen3-Embedding-0.6B, BGE-M3, mE5-large-instruct, EmbeddingGemma-300m (+ license-checked others) | MBI-Retrieval | nDCG@10, recall@50, cross-lingual subset, chunks/s, RAM | 3 days | ADR-017, ADR-027 | NOT_STARTED |
| **SPIKE-HYBRID** | T-P6-05 | Does hybrid beat dense or BM25 alone? Which lexical engine and German analysis? | Tantivy, FTS5, LanceDB FTS; decompounding on/off; abbreviation expansion; RRF weights | MBI-Retrieval | nDCG@10 by query type; integration complexity | 3 days | ADR-016, ADR-018 | NOT_STARTED |
| **SPIKE-CHUNK** | T-P6-06 | Which chunking strategy and cap? | C1–C5 × {256, 512, 1024} | MBI-Retrieval + QA subset | nDCG@10, grounding, index size, embed time | 3 days | ADR-012 (policy) | NOT_STARTED |
| **SPIKE-MATHRET** | T-P6-09 | How should equations be retrieved? | Math-token lexical, structural n-grams, equation-card dense, combinations | Equation queries in MBI-Retrieval | Recall@10 on equation queries | 3 days | — (10 §5) | NOT_STARTED |
| **SPIKE-RERANK** | T-P6-11 | Is a reranker worth its CPU cost? | bge-reranker-v2-m3, Qwen3-Reranker-0.6B, LLM rerank | MBI-Retrieval | ΔnDCG@10 ≥ 0.03 at acceptable p95 latency | 2 days | ADR-019 | NOT_STARTED |
| **SPIKE-MODELGW** | T-P7-02 | How are OpenCode-configured models reached programmatically? Is LiteLLM or a thin adapter better? | Direct provider APIs, OpenCode server API, OpenCode Zen; LiteLLM vs in-house | Owner's accounts (Q-B04) | Working calls per role; structured-output support; cost visibility | 2 days | ADR-026 | NOT_STARTED |
| **SPIKE-GRAPH** | T-P8-06 | Does graph expansion improve cross-domain or multi-hop retrieval? | Neighborhood expansion, PPR (HippoRAG-style), LightRAG-style keys | MBI-MultiHop + MBI-Retrieval | Gain on MultiHop without retrieval loss | 4 days | ADR-020 | NOT_STARTED |
| **SPIKE-GRAPHIFY** | T-P8-07 | Does Graphify add value (core or exploration)? | Graphify on the normalized Regelungstechnik subset | Pilot vault notes | Edge precision, usefulness (owner), cost, provenance fit | 2 days | ADR-021 | NOT_STARTED |
| **SPIKE-AGENTFW** | T-P9-01 | Which orchestration and workflow framework? | Custom state machine, LangGraph, Pydantic AI | Orchestrator prototype | Checkpoint/interrupt support, testability, tracing, dependency weight | 3 days | ADR-024 | NOT_STARTED |
| **SPIKE-MULTIMODAL** | T-P9-09 | When does visual inspection improve answers? | Triggers: figure words, uncertain math, figure-card presence | Figure-bound and uncertain-math questions | Answer gain vs cost | 3 days | — (11 §4) | NOT_STARTED |
| **SPIKE-MEDIA** | T-P13-08 | Should lecture videos be transcribed? | Whisper variants on CPU; dedup against scripts | Video sample | Cost/hour, unique-knowledge yield | 2 days | ADR-030 | NOT_STARTED (conditional on Q-I01) |
| **SPIKE-IDEAS** | T-P14-02 | Can useful cross-domain project ideas be generated? | Workflow prototype | Gaps and strengths | Owner rating | 3 days | — | DEFERRED |

## Research sources consulted in Phase 0 (2026-09-24)

- OmniDocBench (CVPR 2025; v1.5 leaderboard, formula CDM metric): <https://github.com/opendatalab/OmniDocBench>
- MinerU2.5 technical report: <https://arxiv.org/pdf/2509.22186>
- PaddleOCR-VL (0.9B document VLM; page-speed figures): <https://arxiv.org/pdf/2510.14528>, <https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6>
- UniRec-0.1B (text+formula recognizer; 7× faster when integrated into MinerU2.5): <https://arxiv.org/abs/2512.21095>
- HunyuanOCR-1.5: <https://arxiv.org/pdf/2607.04884>
- "OmniDocBench is Saturated" (LlamaIndex): <https://www.llamaindex.ai/blog/omnidocbench-is-saturated-what-s-next-for-ocr-benchmarks>
- Parser comparison articles (Docling vs Marker vs MinerU, 2026; secondary sources, lower weight): <https://builderai.tools/blog/pdf-parsing-for-rag-mineru-docling-marker-compared>
- Kuzu archival and the LadybugDB fork: <https://thedataquarry.com/blog/from-kuzu-to-ladybug/>, <https://ladybugdb.com/>
- Embedding model landscape 2026: <https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models>
- OpenCode server and providers: <https://opencode.ai/docs/server/>, <https://opencode.ai/docs/providers/>
- Graphify: local skill definition `~/.claude/skills/graphify/SKILL.md` (package `graphifyy`)

**Uncertainty note:** most benchmark numbers are for GPU inference and English/Chinese documents. None are for German MathType engineering scripts on a CPU laptop.
That is exactly why the spikes exist. Statements in these docs about ARQMath, HippoRAG and GraphRAG come from model knowledge and are to be verified during the spikes.
