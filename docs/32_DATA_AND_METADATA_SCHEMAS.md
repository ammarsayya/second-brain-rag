# 32 — Data and Metadata Schemas

Logical schemas (Pydantic models in `src/sbr/schemas/`, JSON Schemas exported to `schemas/`). The registry tables are in 31.
Conventions: ids are ULIDs with type prefixes (`doc_`, `sec_`, `blk_`, `ku_`, `eq_`, `fig_`, `tbl_`, `ann_`, `con_`, `rel_`, `clm_`, `evd_`, `cfl_`, `gap_`, `rp_`, `act_`, `run_`).
Blob ids use `b3:<hex>`. Timestamps are ISO-8601 UTC. Every derived record has `activity_id` and `derived_from[]` (PV-1).

## 1. Provenance core
```yaml
Activity: {activity_id, kind, producer, producer_version, params_hash, agent: "system:<c>|model:<p>/<m>@<v>|user:owner",
           run_id, started_at, ended_at, status, inputs: [entity_id], outputs: [entity_id], notes}
DerivedFrom: {entity_id, source_entity_id, locator?: Locator, role: "primary|context|twin|evidence"}
Locator: {blob_id, representation, page_index?, page_label?, bbox?: [x0,y0,x1,y1], block_id?, char_span?: [s,e],
          equation_label?, figure_label?, timestamp_s?}   # timestamp for future media
ProvenanceClass: SOURCE_DERIVED | USER_AUTHORED | USER_ANNOTATION | AI_GENERATED | EXTERNAL_PENDING | EXTERNAL_RESEARCH | MODEL_KNOWLEDGE
```

## 2. Document structure (knowledge.sqlite + DocIR artifacts)
```yaml
Document: {document_id, representations: [{blob_id, role: primary|twin, format}], title, title_source: metadata|first_page|filename|owner,
           genre, languages[], course_ids[], institution?, semester?, authors_from_source[], isbn_from_filename?, page_count,
           decomposition: {policy_version, files: [vault_path]}, extraction_status: {text, ocr, math, figures, tables}, provenance_class: SOURCE_DERIVED}
Section: {section_id, document_id, parent_id?, number?, title, level, page_span: [a,b], order, anchor}
Block: {block_id, document_id, extraction_id, type, page_index, bbox, order, text, lang, confidence, source: text_layer|ocr|office|vision, refs{}}
Equation: {equation_id, document_id, page_index, bbox, display: bool, label?, readings: [Reading], preferred: int,
           latex_normalized, math_tokens[], structure_signature, variables: [symbol], symbol_defs: [SymbolDefinition.id],
           context: {before_block?, after_block?, section_id, figure_refs[], table_ref?}, validation_status, crop_ref?}
Reading: {latex, source_kind: omml_exact|latex_source|vision_recognized|text_layer_linear|none, engine, engine_version, confidence,
          validations: {syntax, render_similarity, textlayer_overlap, twin_agreement, label_consistency}}
SymbolDefinition: {id, symbol, meaning, unit?, scope: document|section, evidence: Locator, confidence}
Figure: {figure_id, document_id, page_index, bbox, kind, label?, caption?, referenced_by: [block_id], knowledge_bearing: bool,
         kb_confidence, crop_ref?, card_text?, ai_description_ref?}
Table: {table_id, document_id, page_index, bbox, label?, caption?, cells: [[...]] | html, confidence, crop_ref?}
Annotation: {annotation_id, document_id, page_index, bbox, kind: pdf_annot|ink_detected|highlight, text?, color?, linked_block?, provenance_class: USER_ANNOTATION}
Reference: {reference_id, document_id, raw_text, parsed: {authors?, title?, year?, isbn?, doi?}, in_text_markers[], resolved_document_id?, match_confidence}
```

## 3. Knowledge layer
```yaml
KnowledgeUnit: {ku_id, anchor: {document_id, section_path_norm, fingerprint}, version, type, document_id, section_id,
                block_ids[], equation_ids[], figure_ids[], table_ids[], text (rendered), lang, provenance_class,
                topics: [{taxonomy_id, confidence}], concepts: [{concept_id, relation: mentions|defines|uses}],
                version_group?, dup_canonical: bool, status: current|superseded|tombstoned, successor_ids[]}
Concept: {concept_id, pref_label_en, pref_label_de?, aliases[], definition_ku_ids[], taxonomy_ids[], status: candidate|curated|rejected}
Relation: {relation_id, type, src, dst, evidence: [Locator|ku_id+span], confidence, status: inferred|extracted|validated|curated|rejected, activity_id}
Claim: {claim_id, text, basis: CORPUS|USER|EXTERNAL_APPROVED|EXTERNAL_PENDING|MODEL, evidence: [Evidence], context: answer|ai_note|proposal}
Evidence: {evidence_id, target: ku_id|equation_id|figure_id|external_span, span?: [s,e], quote?, support: entails|partial|contradicts, judge_activity?}
Conflict: {conflict_id, claims|evidence: [...], kind: real|apparent|definitional|contextual, analysis, resolution: a_better|b_newer|both_valid|insufficient, status}
```

## 4. Interpretation layer
```yaml
AINoteMeta (frontmatter): {sbr_id, provenance_class: AI_GENERATED, note_type: synthesis|concept|map|equation_card, version, generated_by,
            generated_at, model, prompt_version, input_fingerprint, citations: [...], status: current|stale|superseded, content_hash}
SourceNoteMeta (frontmatter): see 09 §5
KnowledgeGap: {gap_id, domain_id, concept_ref, type, severity, evidence_of_absence, status, research_proposal_ids[]}
ResearchProposal: {rp_id, gap_id, status: pending_review|approved|approved_with_edits|rejected|needs_more, claims[], sources: [ExternalSource],
                   evaluation: [...], conflicts[], budget_used, decided_at?, decided_by?, decision_note?}
ExternalSource: {ext_id, url, title, source_type, retrieved_at, content_hash, stored_path, license_note, authority_score, evaluation_rationale}
```

## 5. Retrieval layer
```yaml
ChunkView: {chunk_id, policy_version, kind: text|equation_card|figure_card|table_view|summary, ku_ids[], text, header, lang,
            filters: {course_ids, genre, provenance_class, sensitivity, document_id, version_group}}
EmbeddingSet: {set_id, model_id, model_version, dims, chunk_policy_version, created_at, status: building|active|retired}
AnswerSegment: {text, basis, citations: [{ku_id|external_id, locator, quote?}], confidence}
OrchestratorRun: see 07 §3
```

## 6. Configuration schema (excerpt)
```toml
[roots]
sources = [{ id="mbi", path='D:\MBI-BRAIN', kind="university" }]   # read_only is implicit and enforced
vault = 'D:\MBI-VAULT'          # Q-B02
var = 'D:\AgenticAI\second-brain-rag\var'
curation = 'D:\AgenticAI\second-brain-rag\curation'
[governor]
max_workers = 6
max_ram_gb = 40
disk_floor_gb = 50
priority = "below_normal"
[models.roles.reason]
primary = "<provider>/<model>"
fallbacks = []
allowed_sensitivity = ["normal"]
```

## 7. Versioning

`docir_version`, `chunk_policy_version`, `rules_version`, `prompt_version`, `embedding set_id` and DB `schema_version` are all explicit. Stage versions in the job
queue combine the code version, config hash and model version (08 §2).
