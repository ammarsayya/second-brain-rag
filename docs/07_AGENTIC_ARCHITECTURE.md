# 07 — Agentic Architecture (PROPOSED)

## 1. Principle (ADR-006, HC-22)

"Agentic" means **the system decides how to answer and when it knows enough**. It does not mean "many LLM agents."
Anything with a correct deterministic procedure (scanning, hashing, dedup, parsing queues, schema validation,
index building, provenance writes, backups, integrity checks) is deterministic software. It is **exposed to agents as tools**
and never re-implemented by them.

## 2. Topology decision (ADR-023, ACCEPTED)

**One orchestrator plus two durable workflows. All other "capabilities" are steps or prompts, not agents.**

| Unit | Kind | Why separate |
|---|---|---|
| **Answer Orchestrator** | Bounded state machine with LLM decision nodes | Interactive, latency-sensitive, needs tight budgets |
| **Research Workflow** | Durable, resumable workflow with a human approval interrupt | Long-running (minutes to hours), external I/O, must survive restarts and wait for the owner |
| **Curation Workflow** | Scheduled batch workflow | Offline synthesis (maps, AI notes, gap analysis, staleness refresh); cost-bounded; no user waiting |

The mission's capabilities are mapped as follows:

| Capability | Realized as | Deterministic part | LLM part |
|---|---|---|---|
| Query Planner | Orchestrator node `understand_and_plan` | Language detection, keyword and metadata extraction | Intent, domains, decomposition, needs_math/visual |
| Retrieval Router | Orchestrator node `route` | Rule table (math → math index; figure words → figure cards; course named → filter) | Hints only (LLM proposes; rules validate) |
| Knowledge Synthesizer | Orchestrator node `synthesize`; Curation step | Evidence pack assembly, citation formatting | Writing with the answer schema |
| Gap Analyzer | Curation step plus orchestrator fallback | Coverage statistics, reference-concept matching | Reference-curriculum generation, gap typing |
| Researcher | Research Workflow | Fetching, storing, dedup, quarantine | Search planning, reading, extraction |
| Source Evaluator | Research Workflow step | Domain allow/deny lists, source-type heuristics, recency | Authority and relevance judgment with a rubric |
| Conflict Analyzer | Orchestrator node `analyze_conflicts` (conditional); Curation step | Candidate detection (same concept/equation, differing values) | Real vs apparent; assumptions; resolution |
| Knowledge Curator | Curation Workflow | VaultWriter, staleness detection, versioning | Note and map text |

## 3. Answer Orchestrator state machine

```
          ┌──────────────┐
 query ──►│ UNDERSTAND   │  → QueryPlan{intent, lang, domains[], sub_questions[], needs_math, needs_visual,
          └──────┬───────┘               layer_policy, filters}
                 ▼
          ┌──────────────┐
          │ ROUTE        │  → RetrievalPlan per sub-question: [lexical, dense, math, graph?, metadata filters]
          └──────┬───────┘
                 ▼
          ┌──────────────┐  tools: search_lexical, search_dense, search_math, expand_graph,
          │ RETRIEVE     │         get_ku, get_parent, get_equation_context, get_figure_card
          └──────┬───────┘
                 ▼
          ┌──────────────┐  → per sub-question: coverage{sufficient|partial|none}, conflicts?, needs_visual?
          │ EVALUATE     │
          └──┬───┬───┬───┘
   partial & │   │   │ conflicting
   budget left   │   └────────► ANALYZE_CONFLICTS ─┐
     ▼           │ none/partial & budget exhausted  │
   REFINE ──► RETRIEVE      ▼                       │
   (rewrite, widen,     GAP_NOTE (record gap;       │
    graph expand,        offer research) ───────────┤
    visual inspect)                                 ▼
                                             ┌──────────────┐
                                             │ SYNTHESIZE   │ AnswerSegments with basis + citations
                                             └──────┬───────┘
                                                    ▼
                                             ┌──────────────┐ deterministic citation checks +
                                             │ VALIDATE     │ entailment judge; relabel or drop unsupported
                                             └──────┬───────┘
                                                    ▼
                                             RESPOND (+ optional PROPOSE_UPDATE: AI-note or gap record)
```

**Stopping conditions:** all sub-questions sufficient; OR `max_iterations` (default 3 refine loops) reached; OR the token/cost budget is
exhausted; OR two consecutive refinements add no new evidence (novelty < threshold). On stop without sufficiency, the answer
states what is missing, and a KnowledgeGap candidate is recorded.

**Failure behavior:** a tool error is retried once and then skipped with a trace note. A model error falls back to the configured fallback
model for that role. Validation failure is never silent: unsupported CORPUS claims are relabeled `MODEL` (if the model is confident and the
layer policy allows it) or removed, and the answer lists the removals.

**State:** `OrchestratorRun{run_id, query, plan, iterations[], evidence_ids[], conflicts[], answer, validations[], costs}`
is persisted in the trace store (T-P9-09) and is replayable.

**Validation strategy:** agentic eval set (T-P9-10) compared against the baseline pipeline (P7). Metrics: answer quality, grounding,
layer accuracy, cost and latency. Regressions block enabling a new orchestrator behavior.

## 4. Research Workflow (see 16)

`GAP → PLAN → SEARCH → FETCH → EVALUATE_SOURCES → EXTRACT → SYNTHESIZE → PROPOSAL → [INTERRUPT: owner approve/reject/edit] → INGEST | ARCHIVE`

- **Responsibility:** close one KnowledgeGap with evidence-backed, evaluated external knowledge.
- **Tools:** web_search, fetch_url, arxiv/openalex/semantic-scholar APIs, youtube_transcript, pdf_store(quarantine), local retrieval (to compare with the corpus).
- **Inputs:** KnowledgeGap, budgets (max sources, max tokens, max wall time), source policy.
- **Outputs:** a ResearchProposal note plus quarantined sources.
- **State:** a durable checkpoint per step (SQLite). It resumes after a crash and can wait days for approval.
- **Stopping:** each target claim has ≥2 independent authoritative sources, or the budget is exhausted, or the source pool is exhausted.
  It reports residual uncertainty.
- **Failure:** partial proposals are allowed and marked incomplete. Fetch failures are logged.
- **Validation:** human approval (always) plus the research rubric eval (T-P12-07).

## 5. Curation Workflow

Scheduled or manual batches: refresh stale AINotes, update domain Maps, run gap analysis, propose concept merges.
Budgeted per run. All outputs go through the VaultWriter. Every generated artifact records input fingerprints.

## 6. Tools contract

Every tool is a typed function with Pydantic input and output models, deterministic where possible, side-effect-classified
(`read`, `write_var`, `write_vault`, `external_io`) and permission-gated. Agents cannot call `write_vault` tools except
through Curation or Research ingest paths. The tool registry is also exported as an **MCP server** (P13). External agents
(OpenCode, Claude Code) can then use the Second Brain.

## 7. Framework (ADR-024, PROPOSED → SPIKE-AGENTFW)

Candidates: (a) **custom explicit state machine** plus a thin structured-output LLM client; (b) **LangGraph**
(checkpointers, interrupts, mature human-in-the-loop); (c) **Pydantic AI** (typed tools and outputs; graph support).
Selection criteria: durable checkpoints on SQLite, interrupts for approval, trace export (OTel), testability with fake models,
lock-in, and dependency weight. The working hypothesis is custom state machine plus Pydantic-typed LLM calls for the Orchestrator
(small, fully testable) and LangGraph *or* the custom workflow engine on the same SQLite job store for Research. The decision comes from the spike.

## 8. Observability of agent decisions (HC-23)

Every node writes a trace span: inputs (hashed or truncated), prompt version, model, raw output, parsed output, decision,
tool calls, latencies and costs. `sbr trace <run_id>` renders the path. Spans are exported to Phoenix (ADR-033) when enabled.
