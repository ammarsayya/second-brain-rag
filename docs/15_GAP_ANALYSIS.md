# 15 — Gap Analysis

Gap detection is **not** "vector search returned nothing." It compares **what I have** with **what is needed
to understand a domain well**.

## 1. Model

```
Domain D
 ├─ Reference Model R(D): required concepts C1..Cn, with prerequisite edges, importance weights, "modern developments" list
 │     source: MODEL knowledge (LLM) + module handbook + taxonomy + (later) APPROVED external curricula/syllabi
 │     provenance: AI_GENERATED reference, owner-reviewable (T-P11-01), versioned
 └─ Holdings H(D): for each Ci the corpus evidence profile
        depth signals: has_definition, has_derivation, has_example, has_exercise(+solution), has_equations(validated), has_figures
        breadth: # distinct sources (canonical), source genres, authority (textbook > script > slides), recency (year)
        owner signals: user notes, annotations, thesis/project usage
        quality: extraction confidence of supporting KUs (low math confidence weakens coverage)
```

## 2. Coverage score (T-P11-02)

`coverage(Ci) = f(depth, breadth, quality, owner_engagement)` is a transparent weighted formula (weights tuned with the owner, not learned).
Each score comes with its evidence list. Domain strength is an importance-weighted aggregation. **Every number must be explainable.**

## 3. Gap types (T-P11-03)

| Type | Rule sketch |
|---|---|
| `missing` | Ci ∈ R(D) with no supporting KU (lexical + dense + concept-link check, *not just* top-k emptiness) |
| `shallow` | Only mentions; no definition, derivation or example |
| `missing_prerequisite` | Ci is covered but a prerequisite Cj is missing or shallow |
| `outdated` | The field has moved since the corpus date (2019–2024 material). Flagged by the reference model's "modern developments" list, e.g. learning-based control, modern motion planning, foundation models for robotics |
| `unverified_math` | Coverage relies on uncertain equations |
| `conflict_unresolved` | An open Conflict touches Ci |
| `isolated` | Covered, but without cross-domain links where the reference model expects them |

## 4. Outputs (T-P11-04)

- **Domain gap report** as a section in the domain Map (19): strengths, weak spots, missing prerequisites, modern gaps, and suggested research.
- **KnowledgeGap objects** (status: open, researching, proposal_ready, closed, dismissed) that feed the Research workflow.
- Answers to "What do I know about robotics?": holdings summary, coverage table, gaps and next steps, **with the layer of each statement labeled**.
  The reference model is MODEL-derived and says so.

## 5. Evaluation (T-P11-05)

**Seeded gaps:** temporarily hide selected documents (e.g. all observer-design material) from the holdings. The analyzer should flag the removed concepts.
Measure precision and recall of gap flags. The owner also rates the usefulness of reports on 3 domains.

## 6. Risks

The reference model can be biased or incomplete because it comes from an LLM, so it is reviewed and versioned, and approved external curricula can refine it later.
Coverage can be inflated by duplicates, so it counts canonical sources only.
