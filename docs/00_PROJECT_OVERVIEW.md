# 00 — Project Overview

**Project:** Second Brain RAG (`second-brain-rag`, CLI name `sbr`)
**Owner:** Ammar Sayyadi (personal project)
**Status:** Phase 0 planning complete and reconciled against the finalized corpus (t2 re-audit, `37_T2_CORPUS_REAUDIT.md`). **Plan approved by the owner on 2026-09-24 (T-P0-08 DONE); Phase 1 implementation in progress.** Post-quarantine source baseline: t3 (`38_EXACT_DUPLICATE_QUARANTINE.md`).
**Last updated:** 2026-09-24

## What this is

A local-first **Agentic RAG Second Brain**. It turns the owner's Maschinenbau-Informatik university corpus
(`D:\MBI-BRAIN`, about 530–560 GB and still growing during migration) and, later, other knowledge into a
provenance-tracked, mathematically faithful, graph-connected knowledge system. The system can:

- answer questions with **verifiable citations** down to file and page;
- keep **the owner's knowledge, model knowledge and external research distinct**;
- preserve **equations as LaTeX** and **technical figures** as first-class knowledge;
- maintain an **Obsidian-compatible Markdown knowledge library** with user-authored, AI-generated and source-derived notes;
- detect **knowledge gaps**, research them autonomously, and ask the owner before anything external becomes permanent;
- later, connect engineering knowledge (robotics, dynamics, control, simulation) to new software and AI **projects**.

It is explicitly **not** "PDF → chunks → embeddings → vector DB → LLM".

## The three roots (ADR-001)

| Root | Role | Mutability |
|---|---|---|
| `D:\MBI-BRAIN` | Authoritative university source corpus (evidence) | **Read-only** to the system, always |
| `D:\AgenticAI\second-brain-rag` | Application code, config, docs, tests, audit and `var/` (indexes, DBs, caches, artifacts) | `var/` is **rebuildable** and may be deleted |
| **Knowledge vault** (location pending **Q-B02**, proposed `D:\MBI-VAULT`) | Obsidian vault holding normalized source notes (regenerable), user-authored notes, AI notes, approved research and maps | Authoritative for USER_AUTHORED, AI history and approvals. Versioned (git, proposed) |

Human curation decisions (canonical overrides, taxonomy edits, exclusions, approvals) live in a git-tracked
**curation ledger** (`curation/`, ADR-029). With that ledger, deleting `var/` never loses a human decision.

## Where to read next

| Need | Document |
|---|---|
| Why and what for | `01_VISION_AND_GOALS.md`, `02_REQUIREMENTS.md` |
| What the corpus actually contains | `37_T2_CORPUS_REAUDIT.md` (current, t2) and `03_CORPUS_AUDIT.md` (historical t0/t1) |
| Architecture | `06_SYSTEM_ARCHITECTURE.md`, then the topic documents 07–23 |
| What is decided and what is not | `24_DECISION_LOG.md`, `25_OPEN_QUESTIONS.md`, `34_RESEARCH_AND_SPIKE_REGISTER.md` |
| What to do next | `27_PHASES_AND_MILESTONES.md`, `28_TASK_REGISTER.md`, `30_IMPLEMENTATION_SEQUENCE.md`, `35_EXECUTION_STATE.json` |
| Plan consistency check | `python tools/validate_plan.py` |

## Document index

00 Overview · 01 Vision · 02 Requirements · 03 Corpus Audit · 04 Knowledge Model · 05 Provenance Model ·
06 System Architecture · 07 Agentic Architecture · 08 Ingestion · 09 Document Normalization · 10 Mathematical Content ·
11 Visual Content · 12 Taxonomy & Knowledge Graph · 13 Retrieval · 14 Chunking · 15 Gap Analysis · 16 External Research ·
17 Model Strategy · 18 Storage · 19 Obsidian · 20 Evaluation · 21 Observability & Operations · 22 Security & Safety ·
23 Failure Recovery · 24 Decision Log · 25 Open Questions · 26 Risk Register · 27 Phases & Milestones · 28 Task Register ·
29 Dependency Map · 30 Implementation Sequence · 31 Corpus Manifest Spec · 32 Data & Metadata Schemas · 33 Test Strategy ·
34 Research & Spike Register · 35 Execution State (JSON) · 36 Technology Assessment (added: the per-dependency evaluation required by the mission) · 37 T2 Corpus Re-audit (pre-quarantine baseline) · 38 Exact-duplicate quarantine (t3 post-quarantine baseline)
