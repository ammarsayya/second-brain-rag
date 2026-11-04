# 17 — Model Strategy

## 1. Model Gateway (ADR-025, ACCEPTED principle)

No component calls a provider SDK directly. All model calls go through `sbr.models.Gateway` with **roles**:

| Role | Used for | Requirements | Local-capable? |
|---|---|---|---|
| `embed` | Dense vectors | Multilingual DE/EN, CPU throughput, stable versions | **Yes: local by default** (ADR-027) |
| `rerank` | Cross-encoder reranking | Multilingual, CPU latency | Yes: local by default |
| `ocr` | Scanned pages | German, confidence output | Local (SPIKE-OCR) |
| `math_ocr` | Formula crops → LaTeX | Accuracy on MathType/Word/LaTeX/scanned | Local preferred; remote per Q-B03 |
| `layout` | Region detection | Formulas, figures, tables | Local |
| `classify` | Genre and topic classification, triage fallbacks | Cheap, fast, structured output | Small local or cheap API |
| `extract` | KU boundary checks, symbol definitions, relations, concepts | Structured output, German, cost-efficient | API (cheap tier) or a local 7–14B model (slow on CPU) |
| `reason` | Orchestrator planning, evidence judging, synthesis | Strong reasoning, long context, tool use | API (strong tier) |
| `judge` | Grounding and entailment checks, eval | Reliable and calibrated; **different from the generator when possible** | API |
| `vision` | Figure description, page inspection, math verification | Multimodal, German | API |
| `research` | Research planning and reading | Long context, tool use | API |

Each role config: `primary`, `fallbacks[]`, `max_cost_per_call`, `temperature`, `structured_output: true`, `allowed_sensitivity`
(e.g. `vision` may not receive `sensitive` docs if remote), `cache: true` (content-hash-keyed response cache for reproducibility and cost).

## 2. Access paths

**Policy (2026-11-04, ADR-039/ADR-040):** local-only execution. Remote providers are disabled and cannot be enabled by configuration in this phase; no corpus data leaves the host. Implemented in `sbr.models` (T-P7-01).

| Path | Status | Notes |
|---|---|---|
| **OpenCode-configured models** | PROPOSED → **SPIKE-MODELGW** (Q-B04 answered for architecture only, ADR-040; credentials/activation not authorized) | Options: (a) call the providers OpenCode uses directly, with the same keys, via an OpenAI-compatible or LiteLLM adapter; (b) the OpenCode headless server (`opencode serve`, an OpenAPI HTTP API plus `@opencode-ai/sdk`), which is agent-session-oriented, heavier, and not a plain completion API; (c) the OpenCode Zen gateway endpoint, if that is what the owner subscribes to. Which subscription or provider the owner uses is unknown |
| Anthropic (Claude), OpenAI (incl. Codex models), Google | Adapters planned | Direct SDKs behind the gateway |
| Local | Planned | Ollama or llama.cpp server (OpenAI-compatible) for small models; sentence-transformers or ONNX Runtime for embed/rerank; OCR and math engines as Python libraries |

**Candidate implementation:** LiteLLM as the adapter library under our Gateway (broad provider coverage, OpenAI-compatible) vs a thin
in-house adapter set. This is part of SPIKE-MODELGW. Our own Gateway interface stays the contract either way, so LiteLLM remains replaceable.

## 3. Specialization rationale

- **Embeddings and rerankers local:** throughput-bound, run over the whole corpus, privacy-relevant (sensitive docs), and deterministic versions are needed.
- **Reasoning and judging remote (initially):** CPU-only local LLMs large enough to judge grounding reliably are too slow (≫10 s per call).
- **Judge ≠ generator:** reduces self-preference bias in grounding and eval.
- **Vision on demand:** expensive, so it runs JIT with caching.

## 4. Versioning and reproducibility

Every call records the provider, model id, **resolved model version or date**, prompt template version, parameters, input hash and output.
Prompt templates live in `src/sbr/prompts/` with semantic versions. Evaluation results reference model and prompt versions.
Model upgrades go through eval gates (20).

## 5. Cost control

Per-run and per-day budgets. Dry-run cost estimation for batch jobs (relation extraction, AI notes) before execution. The cache is keyed by
(role, model version, prompt version, input hash).
