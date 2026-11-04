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

## 6. Implementation (T-P7-01, 2026-11-04)

`sbr.models` implements §1 for the local-only phase (ADR-039, ADR-040).

| Piece | Module | State |
|---|---|---|
| Gateway (routing, sensitivity gate, retries, local fallbacks, cache, accounting) | `gateway.py` | implemented, tested |
| Deterministic mock adapter (generate, structured, embed, vision input) | `mock.py` | implemented, tested |
| Local OpenAI-compatible adapter (Ollama, llama.cpp server, LM Studio, vLLM) | `openai_compat.py` | implemented; tested against a loopback test server only, **not against a real inference server** |
| Remote adapters (Anthropic, OpenAI, OpenCode, ...) | none | not authorized (ADR-040); T-P7-02 |
| `rerank` capability | none | no adapter implements it; configuring `rerank` fails validation |
| Vision input on the local adapter | none | not implemented; `ocr`/`math_ocr`/`layout`/`vision` work only with the mock until a local VLM adapter is measured |

**Roles in practice.** Every docs/17 §1 role is routable. A role is usable only when its provider implements the
capability it needs (`ROLE_CAPABILITY`): `embed` needs `embed`; `ocr`, `math_ocr`, `layout`, `vision` need `vision`;
`classify`, `extract`, `reason`, `judge`, `research` need `generate`; `rerank` needs `rerank`. The checks run when
the gateway is built, so a misconfigured role fails at start-up, not mid-run.

**Call contract.** Every request carries an explicit `sensitivity`. `restricted` is refused for every role, and other
classes only where the role's `allowed_sensitivity` lists them. Each call yields a `CallRecord`: role, provider,
model, server-reported model version, prompt version, subject id, input/output SHA-256 and sizes, token usage,
latency, attempts, cache hit, outcome, error type, cost (0.0 locally), and `provenance_class = AI_GENERATED`. It is
logged on `sbr.models` without any prompt or output text.

**Reliability.** `max_retries` (0-5, default 1) applies only to retryable errors: timeouts, HTTP 429/5xx and dropped
connections. Backoff is 0.5 s, 1 s, 2 s, ..., capped at 4 s. A refused connection (no local server) is not retried;
the error says so and names the config key to fix. Each fallback is tried in turn and must be local. Policy errors
are never retried and never fall back. The response cache is in-memory only: a persistent, content-hash-keyed cache
under `var/` is still open work.

**Limitations.** The deadline covers the whole response, but it is checked between reads, so one stalled read can
take up to `timeout_s` more (worst case about 2 × `timeout_s`). Throughput, memory use and output quality of real
local models are **unmeasured**. That is SPIKE-EMBED, SPIKE-MATH and SPIKE-COMPUTE work on the owner's Mac.

CLI: `sbr models status [--probe]` lists providers, capabilities and role readiness. `--probe` only calls `GET /models`
on the configured loopback servers.
