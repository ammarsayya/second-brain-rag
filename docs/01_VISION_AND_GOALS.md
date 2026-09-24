# 01 — Vision and Goals

## Vision

A personal knowledge system that **understands** the owner's engineering and computer science education,
**connects** it across disciplines, **knows what it does not know**, **grows** through approved research,
and **turns knowledge into projects**.

```
KNOWLEDGE → UNDERSTAND → CONNECT → IDENTIFY GAPS → RESEARCH → EXPAND KNOWLEDGE → GENERATE IDEAS → APPLY TO PROJECTS
```

## Why

The owner studied Maschinenbau-Informatik (mechanical engineering and computer science, roughly 2019–2024) and now works mainly in
full-stack software and AI. The university knowledge (robotics, dynamics, control, modelling, simulation, FEM,
measurement, numerics) is valuable but locked in ~13.5k heavily duplicated, badly named, partly scanned PDFs and videos.
The bachelor thesis dealt with the mathematical and dynamic formulation of a medical robot's stability. That makes robotics,
dynamics, control and simulation the highest-value bridge to future AI and physical-systems work.

## Goals (ordered)

| # | Goal | Measured by (see 20_EVALUATION_STRATEGY) |
|---|---|---|
| G1 | **Never lose or corrupt authoritative knowledge** (sources, user notes, approvals) | Zero writes to source roots; zero overwrites of user notes (tests and audits) |
| G2 | **Faithful extraction**, especially mathematics | Equation fidelity on MBI-Gold; uncertainty flagged, never hidden |
| G3 | **Trustworthy answers** with citations to file and page, and clear knowledge-layer labels | Citation precision/recall, grounding rate, layer-label accuracy |
| G4 | **Retrieval quality** on real questions (German/English, equations, cross-domain) | Recall@k and nDCG on the MBI retrieval gold set |
| G5 | **Connected knowledge**: concepts, relations and cross-domain links with evidence | Graph edge precision; gain on cross-domain questions |
| G6 | **Self-knowledge**: coverage, strength and gaps per domain | Gap detection precision/recall on seeded gaps |
| G7 | **Controlled growth** through researched, approved external knowledge | No unapproved external content in permanent indexes; human-rated research quality |
| G8 | **Operability at scale** on a laptop without a GPU: resumable, incremental, rebuildable | Resume after crash without rework; rebuild `var/` from scratch |
| G9 | **Future project generation** is not blocked by today's design | Extension points exist (Idea/Project objects, capability APIs) |

## Non-goals (for now)

- Multi-user, cloud or Kubernetes deployment.
- Replacing Obsidian with a custom UI.
- External bibliographic enrichment of the historical corpus (optional future capability, Q-N01).
- Reorganizing or cleaning `D:\MBI-BRAIN` itself. The system produces *suggestions* only.
- Video lecture transcription in the first release (ADR-030, DEFERRED).
- Project/idea generation (P14, design hooks only).

## Guiding principles

1. **Sources are evidence; everything else is interpretation.**
2. **Deterministic where possible, agentic where it pays** (ADR-006).
3. **Uncertainty is data.** Every extraction and relation carries confidence and status.
4. **Measure before choosing.** Major technology choices stay PROPOSED until a spike on MBI material decides them.
5. **Rebuildable infrastructure, durable knowledge.**
6. **Spend compute where knowledge value is highest** (course material first, textbooks later or lazily).
