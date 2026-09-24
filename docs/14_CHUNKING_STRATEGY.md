# 14 — Chunking Strategy

**Chunk sizes are NOT chosen yet.** They are decided by SPIKE-CHUNK on MBI material (mission constraint).

## 1. Hierarchy

```
SOURCE (blob) → DOCUMENT → CHAPTER → SECTION → SUBSECTION   ← decomposition (09): human/Obsidian files
                                   → KNOWLEDGE UNIT (KU)    ← meaning + citation unit (stable anchors)
                                   → RETRIEVAL CHUNK VIEWS  ← index-specific, versioned, disposable
```

## 2. Knowledge Units (T-P5-01)

KU boundaries follow meaning. Candidate KU types observed in the corpus:
- definition ("Definition", "Unter … versteht man")
- law/theorem/principle ("Prinzip der virtuellen Arbeit")
- derivation (a chain of numbered equations with connecting prose, e.g. (3-114)…(3-120))
- method/procedure (steps; "Vorgehensweise")
- example ("Beispiel")
- exercise (Aufgabe n) and solution (Lösung n), linked
- figure explanation (figure + caption + referencing paragraph)
- table (+ explanation)
- slide (in decks, often one KU per slide or slide group)
- code listing (+ explanation)

Segmentation signals: headings and numbering, keyword cues (bilingual), equation chains, figure/table labels, slide boundaries,
and an LLM-assisted boundary check for long ambiguous sections (budgeted, confidence-marked).

**Derivations are kept together** up to a size cap. Beyond the cap they split at equation boundaries, and each part carries a pointer
to the derivation's first KU and its goal statement.

## 3. Chunk views (derived from KUs)

| View | Content | Index |
|---|---|---|
| `text` | KU text with LaTeX inline, prefixed by a contextual header (document title › section path › KU type) | lexical + dense |
| `equation_card` | Equation LaTeX + NL description + variables + section path | math + dense + lexical |
| `figure_card` | Caption + referencing text + in-figure labels (+ AI description if present) | dense + lexical |
| `table_view` | Linearized table + caption | lexical + dense |
| `summary` (optional) | AI summary of long sections for coarse retrieval ("small-to-big") | dense |

The **contextual header** (a prefix with the document and section path) is the cheap version of "contextual retrieval" and needs no LLM.
LLM-generated per-chunk context blurbs are a spike option (cost vs gain).

## 4. Candidate strategies for SPIKE-CHUNK (T-P6-09)

| Strategy | Description |
|---|---|
| C1 baseline | Fixed-token windows (e.g. 512 with overlap) over the page text. Baseline only |
| C2 KU-native | One chunk per KU, with long KUs split at sentence or equation boundaries (cap N tokens) |
| C3 KU + header | C2 plus a contextual header |
| C4 small-to-big | Index small units (sentences, equation cards); return the parent KU/section at context construction |
| C5 C3 + LLM context blurb | Per-chunk LLM context (expensive) |

Caps to test: N ∈ {256, 512, 1024} tokens. Metrics: recall@10/nDCG@10 on the retrieval gold set, answer grounding on the QA subset,
index size, and embedding time.

## 5. Parent context rule (HC-13, 10 §4)

At context construction, a chunk expands to its KU and then as needed to the parent section summary and neighbors (budgeted).
An equation always carries its context pack. Exercise chunks pull in their linked solution (and vice versa) when the query asks for solving.

## 6. Duplicates and versions at chunk level

Chunks are built **only for canonical representatives** of exact-duplicate groups. For near-duplicates and versions, chunks are built for
each version, but they carry a `version_group` id so dedup collapse (13) can fold them. Annotated variants are indexed separately,
with only the annotation-bearing KUs marked.
