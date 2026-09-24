# 05 — Provenance Model

Provenance is mandatory (HC-04, HC-17). The model is inspired by W3C PROV
(**Entity**, **Activity**, **Agent**), simplified for a local system.

## 1. Provenance classes (ADR-013)

| Class | Meaning | May be auto-created? | Permanent without approval? | Regenerable? |
|---|---|---|---|---|
| `SOURCE_DERIVED` | Extracted or normalized from a source blob by deterministic or model-based extraction | Yes | Yes (it *is* the evidence representation) | Yes, from source plus extractor version |
| `USER_AUTHORED` | Written or edited by the owner | Owner only | Yes | **No. Never overwritten** |
| `USER_ANNOTATION` | Owner's marks inside a source (highlights, handwriting) | Detected automatically | Yes | Yes (re-detectable), but never merged into lecturer content |
| `AI_GENERATED` | Synthesis from *accepted* knowledge (SOURCE_DERIVED, USER_*, EXTERNAL_RESEARCH) | Yes | Yes, auto-saved and versioned | Yes; history kept |
| `EXTERNAL_PENDING` | Research output not yet approved | Yes | **No**: quarantined, excluded from main indexes | — |
| `EXTERNAL_RESEARCH` | Externally researched knowledge after owner approval | Only via approval | Yes | Re-processable from the stored external source |
| `MODEL_KNOWLEDGE` | LLM pretrained knowledge used in an answer | Answer-time only | **Never stored as knowledge**; it may appear in answers with a label. Stored only inside AINotes as explicitly labeled claims |

Rule: **An AI_GENERATED artifact may only cite accepted knowledge.** If it uses model knowledge, those claims are labeled
`basis: MODEL` inside the note. If it uses pending external material, it is a ResearchProposal, not an AINote.

## 2. Entities, activities, agents

- **Entity:** any stored object (Blob, Page, Block, Equation, KU, Concept, Relation, AINote …) with an ID.
- **Activity:** a run of a producer: `activity_id`, `kind` (scan, hash, extract, ocr, math_recognize, segment, embed,
  extract_relations, synthesize, research, approve …), `producer` (tool/model name), `producer_version`, `params_hash`,
  `started/ended`, `run_id`, `status`, `inputs[]`, `outputs[]`.
- **Agent:** `system:<component>`, `model:<provider>/<model>@<version>` or `user:owner`.

Every write API in the system takes an `activity_id` (T-P1-07). Writes without one are rejected by the data layer.

## 3. Locators (how evidence points into sources)

```
Locator = {
  blob_id,                        # content hash → which exact bytes
  representation: pdf|docx|pptx|…,
  page_index, page_label,         # 0-based index + printed label ("S. 22", slide 7)
  bbox?: [x0,y0,x1,y1] (PDF points, page coords),
  block_id?, char_span?: [start,end] within block text,
  equation_label?, figure_label?  # "(3-114)", "Bild 2.17"
}
```

Human-facing citation rendering: `[Skript Maschinendynamik 1, S. 40 (PDF p. 48), Gl. (3-114)]`. It links to the Obsidian
source note anchor `^p48` and to the original file path (canonical PathObservation) with `#page=48`.

## 4. Provenance chains

**Source-derived answer claim**
```
AnswerSegment(basis=CORPUS)
  └─cites→ Evidence{ku_id, char_span, support=entails, judge=activity}
       └─ KU ──composed_of→ Block(s) ──produced_by→ Activity(extract, extractor@ver)
             └─ Locator(page, bbox) ──in→ Blob(hash) ──observed_at→ PathObservation(D:\MBI-BRAIN\…\file.pdf)
```

**Equation from a twin**
```
Equation(source_kind=omml_exact) ──from→ Blob(DOCX) ──twin_of→ Blob(PDF) ──aligned_at→ Locator(PDF page)
```

**Researched knowledge**
```
Claim(basis=EXTERNAL_RESEARCH) → ResearchSynthesis(proposal_id, approved_by=user:owner, approved_at)
  → Evidence(span in ExternalSource) → ExternalSource(url, retrieved_at, content_hash, stored copy path, license note)
```

**AI synthesis note**
```
AINote(version n, generated_by=Activity(synthesize, model@ver, prompt_version))
  → Claims → Evidence → KUs / UserNotes / ExternalSources(approved) → original sources
  input_fingerprint = hash(sorted evidence ids + their content hashes)  ⇒ staleness detection
```

**Graph edge**
```
Relation(type, src, dst, status, confidence) → Evidence span(s) that mention both ends
  → produced_by Activity(extract_relations, model@ver) | curated_by user:owner
```

## 5. Invariants (enforced by code and tests)

| ID | Invariant | Enforcement |
|---|---|---|
| PV-1 | Every stored derived entity has ≥1 `derived_from` link and a producing activity | DB constraint and data-layer check |
| PV-2 | Every CORPUS-basis answer segment has ≥1 evidence item whose span exists | Grounding validator (T-P7-05) |
| PV-3 | Locators resolve: blob exists and page index < page count | Periodic integrity job |
| PV-4 | EXTERNAL_PENDING entities never appear in main indexes | Index builder filter plus test TS-PROV-3 |
| PV-5 | USER_AUTHORED files are never written by the system | VaultWriter plus test TS-VAULT-* |
| PV-6 | Re-extraction creates new entities/versions; it never mutates old ones in place | Artifact store is append-only per (blob, extractor@ver) |
| PV-7 | KU anchors survive re-extraction or are tombstoned with a successor mapping | Anchor alignment (T-P5-05) |
| PV-8 | Uncertain extractions keep `validation_status != verified` until verified | Schema defaults; no auto-promotion |

## 6. Stable anchors (citation drift prevention)

A KU anchor = `(document_id, section_path_normalized, content_fingerprint)`, where the fingerprint is a SimHash of
normalized text plus equation LaTeX. On reprocessing (new parser version), new KUs are aligned to old ones by
section path and fingerprint similarity. The system then writes one of:
- `same` (id retained),
- `revised` (id retained, new version),
- `split`/`merged` (successor mapping),
- `removed` (tombstone kept, citations flagged for review).

AINotes and graph edges citing tombstoned anchors are marked **stale**.

## 7. Human decisions as provenance

Approvals, rejections, canonical overrides, taxonomy edits and concept curation are Activities with `agent=user:owner`.
They are persisted in the git-tracked **curation ledger** (ADR-029). Rebuilding `var/` replays the ledger, so human
decisions survive index deletion.
