# Decision Packages: Q-B03 (Compute & Privacy) and Q-B04 (Model Access)

Status: **recommendations only. The owner decides.** No model was called, no key configured, no corpus content sent
anywhere in preparing this. Figures marked *(measured)* come from this repo's reports; *(est.)* are order-of-magnitude
planning estimates that SPIKE-COMPUTE (T-P3-09) must replace with measurements; *(unverified)* I could not check from
the session and the owner should confirm.

## Facts that frame both questions

| Fact | Value | Source |
|---|---|---|
| Host | Apple M5 Max, 18 cores, 36 GB unified memory, 1.2 TB free | macOS migration plan |
| Resource guard | `max_ram_gb = 24` in `config/sbr.macos.example.toml` | repo |
| Scanned PDF candidates | 764 (OSD: rotate 0/90/180/270 = 314/54/169/32) | `spike_ocr_orientation.md` *(measured)* |
| Math gold entries needing transcription | 120 PDF crops; 497 PPTX equations need an extraction path | docs/28 *(measured)* |
| Corpus | 83,880 active-t3 files, 558.75 GB; textbooks dominate unit count (waves W0-W3, docs/08 §4) | docs/38 |
| Sensitive content | restricted/third-party items exist (IDs, CVs, certificates, grade lists, one legal paper); already gated by `spike_gate` + sensitivity classes | docs/22 §3 |
| Slowest known local engine | PaddleOCR-VL ~30 s/page CPU class *(docs/36, unverified on this host)* | docs/36 |

Hard rule from the existing design that both options must respect: restricted and third-party-personal documents are
never processed beyond metadata and never sent to a remote service (docs/22 §3, HC-20). This package does not propose
changing that.

---

## Q-B03: Compute and privacy policy

**Question:** may course material and/or textbooks go to cloud OCR/LLM APIs? Is a rented GPU acceptable? Budget ceiling?

### Options

| | A. Local-only | B. Local-first, remote for hard cases (approval per class) | C. Remote-first |
|---|---|---|---|
| Where text/figures go | Never leave the Mac | Course material local; chosen classes (e.g. textbook pages, failed OCR crops) to approved providers | Most extraction remote |
| Throughput | Bounded by one machine; Apple GPU (MPS/MLX) usable for embeddings and small VLMs *(unverified per engine)* | Local for bulk; remote only for the tail | Fastest wall-clock |
| Cost | none beyond power | variable, capped by budget | highest, scales with textbooks |
| Privacy | strongest | depends on per-class allowlist | weakest; copyrighted textbooks leave the machine |
| Reproducibility | strong (pinned local versions) | mixed; remote versions drift (response cache + version pinning mitigate) | weakest |
| Risk to this project | slow W3 textbooks; some engines have no Apple-Silicon build *(unverified)* | policy complexity; needs gateway + per-root switch (already designed) | contradicts "local-first" and docs/22 §4 copyright stance |

### Evidence-based observations

1. **Scale is dominated by textbooks (W3).** Strategy ADR-007 already limits W3 to text + structure, with math/figure
   tiers on demand (JIT). So the heavy compute question is mostly *deferred by design*; W0-W2 course material is the
   part that needs a policy now.
2. **The honest compute unknown is OCR/math engine speed on this host.** At ~30 s/page (docs/36 figure, unverified
   here) 764 scanned documents are a multi-day CPU job if every page needs the VLM; most pages should not (the
   orientation census shows many scans already OCR fine with Tesseract). SPIKE-COMPUTE (T-P3-09) is the right place
   to turn this into numbers, and it is blocked on T-P3-05/06/08, not on Q-B03 itself.
3. **Embeddings and reranking are local by design** (ADR-027). With 36 GB unified memory a 0.6B embedding model fits
   comfortably *(est.)*; Q-B03 does not affect them.
4. **The 120 handwritten/printed PDF math crops are small.** They can be done by a local math-OCR engine, a remote
   vision model, or by hand; the volume is too small for cost to matter and big enough that privacy of lecture
   slides is the real question.

### Recommendation (owner's decision)

**Option B, starting with a strict local-only default.** Concretely:
- Policy now: **local-only for everything**. Defer any remote class until SPIKE-COMPUTE produces measured local
  throughput and a measured quality gap.
- Pre-authorize *nothing* remote yet. If a remote class is later wanted, approve it per class (e.g. "math crops from
  course material, non-restricted") and record it in `curation/approvals.yaml`.
- No GPU rental: nothing measured justifies it, and it sends data off-machine.
- Budget ceiling: set **0** until a class is approved; then a monthly cap in the gateway config.

Why this order: it keeps the privacy guarantees intact, costs nothing, and makes the later remote request an
evidence-based exception instead of a blanket policy. It does delay engines that need a GPU stack unavailable on
macOS; SPIKE-COMPUTE will surface that.

### Owner answers requested

1. May any non-restricted course material go to a remote service? (default recommendation: no, revisit later)
2. May textbook content ever go remote? (recommendation: no)
3. Monthly ceiling, if any remote class is approved later.
4. GPU rental acceptable? (recommendation: no)

Unlocks: T-P3-09 decision, T-P3-11, T-P13-01.

---

## Q-B04: Model access

**Question:** which models and how are they accessed programmatically (provider keys, OpenCode Zen, Copilot, ...)?

### What the system needs from models (docs/17 roles)

| Role | Needs | Natural home |
|---|---|---|
| `embed`, `rerank`, `layout`, `ocr`, `math_ocr` | throughput, determinism, privacy | local |
| `classify` | cheap, structured output | small local or cheap API |
| `extract` | structured output, German, volume | cheap-tier API or 7-14B local *(slow, quality unverified)* |
| `reason` / `research` | strong reasoning, long context, tools | strong API |
| `judge` | calibrated, **different from the generator** | API |
| `vision` | multimodal, German; math/figure verification | API, JIT with caching |

First RAG pipeline needs only `embed`, `rerank` (local) and a `reason` model for the grounded answer. Everything else
is optional for a first working end-to-end path.

### Options

| | A. Local models only | B. Hybrid by role (local embed/rerank/OCR, remote reason/judge/vision) | C. Single remote provider for all LLM roles |
|---|---|---|---|
| Capability | weak `reason`/`judge`; self-judging risk | best fit to the role table | strong, simple |
| Privacy | strongest | role-level allowlist; sensitivity gate per call | all LLM traffic remote |
| Cost | none | metered, cacheable, budget-capped | metered |
| Fit with existing design | satisfies it, but gaps in judge/vision | **this is the design in docs/17** | contradicts per-role routing |

### Access path options (ADR-026, unresolved; the owner must say which applies)

1. **Direct provider API keys** through the model gateway (LiteLLM adapter or thin adapter set). Simplest and
   fully programmatic; needs a funded key per provider.
2. **OpenCode headless server** (`opencode serve` / SDK): session-oriented agent API, heavier, not a plain completion
   endpoint. Usable only if the owner's models are reachable only through OpenCode.
3. **OpenCode Zen gateway** if that is the owner's subscription (*unverified* whether it exposes a plain
   OpenAI-compatible endpoint for programmatic use).
4. **Subscription-only access (e.g. a coding-assistant subscription)** may **not** permit programmatic use outside the
   vendor tool; terms must be checked by the owner (*unverified*).

### Recommendation (owner's decision)

**Hybrid by role (B), gateway-first, local-only until a key is provided.**
- Build `sbr.models.Gateway` (T-P7-01) with a **fake/local backend first**; it is `Human approval: none` and needs
  no key. Sensitivity gate, role config, cost accounting and response cache can all be implemented and tested with
  fake models. This is the only engineering step that Q-B04 truly blocks (the T-P7-02 dependency edge is a plan
  dependency; see below).
- For the first grounded-answer path, use one remote `reason` model through the gateway **only after** the owner
  chooses a provider and key and approves what content may be sent (Q-B03).
- Prefer access path 1 (direct keys): it is the only path that is clearly programmatic and auditable.

### Gateway integration requirements (already specified, restated for the decision)

- Roles with `primary`, `fallbacks`, `max_cost_per_call`, `allowed_sensitivity`, `structured_output`, `cache`.
- Per-call sensitivity enforcement (restricted/third-party never remote).
- Records provider, resolved model version, prompt version, input hash, output (docs/17 §4).
- Per-run and per-day budgets, dry-run cost estimates for batch jobs.
- Secrets from env vars or OS keychain only (docs/22 §5).

### Owner answers requested

1. Which provider(s)/accounts exist, and which access path (1-4) applies?
2. Are those terms OK for programmatic use?
3. Which content classes may be sent to them (ties to Q-B03)?
4. Budget cap.

### A plan observation for the owner (not an agent change)

T-P7-01 (model gateway) depends on T-P7-02 (SPIKE-MODELGW), which is BLOCKED on Q-B04, so the gateway cannot start
under the current gates even though a fake-backend gateway needs no credentials. If the owner agrees, T-P7-01's
dependency could be split (an offline gateway core vs. live adapters). That is a plan change and is **not** made
here; the gates are unchanged.

Unlocks: T-P7-02, T-P7-01 (as currently gated), the 120 math drafts in T-P3-02.
