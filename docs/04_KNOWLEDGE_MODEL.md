# 04 — Knowledge Model

The knowledge model defines **what the system knows about**. Physical schemas are in `32_DATA_AND_METADATA_SCHEMAS.md`.
The model is layered so that evidence, structure, meaning and interpretation stay separable.

```
EVIDENCE LAYER      SourceRoot ─ PathObservation ─ Blob ─ (ArchiveMember) ─ Page/Slide
STRUCTURE LAYER     Document ─ Section tree ─ Block (DocIR) ─ Equation / Figure / Table / Annotation / Reference
KNOWLEDGE LAYER     KnowledgeUnit ─ Concept ─ Relation ─ Claim ─ Evidence ─ Conflict
ORGANIZATION        Domain / Topic (taxonomy) ─ Course ─ Person ─ Institution
INTERPRETATION      AINote ─ Map ─ KnowledgeGap ─ ResearchProposal ─ ExternalSource ─ UserNote
RETRIEVAL (derived) RetrievalChunk ─ EmbeddingSet ─ IndexEntry            (never authoritative)
FUTURE              Idea ─ ProjectBrief                                    (P14 hooks)
```

## 1. Evidence layer

| Object | Definition | Key attributes |
|---|---|---|
| **SourceRoot** | A configured, read-only root (e.g. `D:\MBI-BRAIN`; later external-research-accepted, other corpora) | root_id, path, kind (`university`, `external_accepted`, `personal`), read_only=true |
| **Blob** | Unique byte content, identified by BLAKE3-256 | blob_id (hash), size, magic_type, first_seen, status |
| **PathObservation** | "Path P under root R had blob B during scans S1..Sn" | root_id, relpath, blob_id, mtime, first/last_seen_scan, state (present/moved/deleted) |
| **ArchiveMember** | A file inside an archive blob (not extracted to source) | container_blob, member_path, member_blob (hash of streamed bytes), encoding_repaired_name |
| **Page** | A physical page or slide of a blob in a given rendering | blob_id, page_index (0-based), page_label (printed number, e.g. "S. 22"), size, rotation, has_text_layer, triage signals |

A *file* is never the identity of knowledge. The **blob** is. Duplicates are several PathObservations of one blob.

## 2. Structure layer (DocIR, per blob × extractor version)

| Object | Definition |
|---|---|
| **Document** | The logical document a blob represents: title, genre (lecture_script, slides, exercise_sheet, solution, exam, exam_solution, lab_instructions, lab_report, textbook, paper, manual/datasheet, thesis, admin, other), language(s), course, institution, date/semester, authors (from source only). One blob → one Document. A Document can also represent a *twin set* (PDF + DOCX) as one logical document with several representations. |
| **Section** | A node in the decomposition tree (part, chapter, section, subsection, slide group) with number, title, page span and depth |
| **Block** | Atomic layout element: paragraph, heading, list, equation, figure, table, caption, code, footnote, page header/footer (flagged), annotation. Has bbox, page, reading order and text, and is produced by one extractor. |
| **Equation** | Display or inline math: `latex`, `latex_normalized`, `label` (e.g. "(3-114)"), `source_kind` (omml_exact, latex_source, vision_recognized, text_layer_linear), `confidence`, `validation_status` (verified, plausible, uncertain, failed), crop reference, variables[] |
| **Variable** | Symbol occurrence inside an equation, linked to a **SymbolDefinition** (meaning, unit, domain) when found in context ("wobei", "mit", "where") |
| **Figure** | Knowledge-bearing visual: kind (block_diagram, plot, schematic, technical_drawing, fem_result, robot_diagram, setup_photo, math_figure, table_image, decorative), caption, label ("Bild 2.17"), bbox, crop ref, is_knowledge_bearing (+confidence), optional AI description (AI_GENERATED) |
| **Table** | Structured table (cells, header), caption, label, extraction confidence; may contain equations |
| **Annotation** | Owner's marks on a source: PDF annotation objects, highlights, handwritten ink (detected). Provenance class **USER_ANNOTATION** |
| **Reference** | A bibliography entry or in-text citation; may resolve to a Document in the corpus (**cites** edge) |

## 3. Knowledge layer

| Object | Definition |
|---|---|
| **KnowledgeUnit (KU)** | The smallest *self-contained unit of meaning* derived from blocks: definition, theorem/law, derivation, method/procedure, example, exercise, solution, figure_explanation, table_explanation, code_explanation, summary, other. It has a parent section path, member blocks, equations, figures, language, and a stable **anchor**. **KUs are the unit of citation.** |
| **Concept** | A named idea independent of any document ("State-Space Representation", "Zustandsraumdarstellung", "Denavit–Hartenberg Convention"). Bilingual labels, aliases, definition KUs, status (candidate/curated/rejected) |
| **Relation** | A typed edge between concepts, KUs, equations, documents or domains, with evidence and confidence (see 12) |
| **Claim** | An atomic proposition used in answers, AI notes and research, with a basis (CORPUS, MODEL, EXTERNAL_APPROVED, EXTERNAL_PENDING, USER) and supporting or contradicting Evidence |
| **Evidence** | A pointer to a span (KU plus char span or equation or figure) that supports or contradicts a claim, with a support strength |
| **Conflict** | A recorded disagreement between evidence items, with its analysis (real vs apparent, assumptions, resolution status). Never deletes either side |

## 4. Organization layer

| Object | Definition |
|---|---|
| **Domain / Topic** | Taxonomy nodes (SKOS-like: broader/narrower/related; poly-hierarchy allowed), bilingual labels. Stored in the curation ledger |
| **Course** | A university module (from the module handbook and folder mapping): name, abbreviations (`RGT`, `Reg1`, `MSR2` …), semester, institution |
| **Person** | Authors and lecturers appearing *in sources* (e.g. lecturer names on slides). Only as source metadata, no enrichment. Sensitive handling applies to non-public persons (students in grade lists → excluded) |
| **Institution** | e.g. Hochschule Hannover, TU Clausthal (from source content and paths) |

## 5. Interpretation layer

| Object | Provenance class | Definition |
|---|---|---|
| **UserNote** | USER_AUTHORED | Any Markdown note the owner writes or edits in the vault. First-class; never overwritten |
| **AINote** | AI_GENERATED | Synthesis, concept note or explanation produced by the system from *accepted* knowledge; cited, versioned, may regenerate |
| **Map** | AI_GENERATED (with USER sections allowed) | Living overview per domain (see 19, 15) |
| **KnowledgeGap** | AI_GENERATED | Detected gap with type, domain, severity, evidence of absence/weakness, status |
| **ResearchProposal** | EXTERNAL_PENDING | Output of a research run awaiting approval: claims, sources, evaluation, conflicts |
| **ExternalSource** | EXTERNAL_RESEARCH (after approval) | A fetched external document, stored in a quarantine root until approved, then in the accepted-external root |

## 6. Retrieval layer (derived, never authoritative)

| Object | Definition |
|---|---|
| **RetrievalChunk** | A *view* of one or more KUs for indexing: text view, equation card, figure card, table view, summary view. Version-keyed by chunk policy |
| **EmbeddingSet** | (model id, model version, chunk policy hash, dims). Several can coexist |
| **IndexEntry** | Lexical, dense or math index row pointing back to a chunk → KU(s) |

## 7. Core relationships (cardinalities)

```
SourceRoot 1─* PathObservation *─1 Blob 1─* Page
Blob 1─* ExtractionRun (extractor@version) 1─* Block
Blob *─1 Document  (twins: Document 1─* Blob with role primary|twin)
Document 1─* Section (tree) 1─* Block ; Block 0..1─ Equation|Figure|Table|Annotation|Reference
Block *─* KnowledgeUnit (KU composed of blocks; KU belongs to exactly one Section)
KU *─* Concept (mentions / defines / uses)
Equation *─* Variable *─0..1 SymbolDefinition
Concept *─* Concept (typed Relation with Evidence)
Document *─* Document (duplicate_of | version_of | contains | twin_of | cites | solution_of)
Document *─* Course ; Course *─* Domain ; Concept *─* Domain
Claim *─* Evidence ─1 KU|Equation|Figure|ExternalSource span
AINote *─* Claim ; Map 1─1 Domain ; KnowledgeGap *─1 Domain ; ResearchProposal *─1 KnowledgeGap
```

## 8. Design notes and trade-offs

- **Why the KU is the unit of citation, not the chunk:** chunks change with chunking policy and embedding model.
  KUs are anchored to source spans and survive re-chunking (prevents citation drift, R-15).
- **Why the Document is separate from the Blob:** twins (PDF + DOCX) and versions need one logical identity with several representations.
- **Why annotations get their own provenance class (USER_ANNOTATION):** the owner's handwriting on a script is user knowledge
  inside a source. It must neither be deduplicated away nor mistaken for the lecturer's content.
- **Why Concepts are curated with status:** LLM-extracted concept graphs are noisy (R-05/R-06). Candidates become curated only
  after passing evidence and quality gates (12).
- **Future-proofing (P14):** `Idea` and `ProjectBrief` objects will link to Concepts, Gaps and Claims. No current object needs changing for them.
