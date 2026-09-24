# 09 — Document Normalization

## 1. Two representations, one truth

```
ORIGINAL SOURCE (blob)            = authoritative evidence (never replaced)
DocIR (JSON, var/artifacts)       = machine representation, parser-independent, with confidence
NORMALIZED MARKDOWN (vault)       = human/LLM-friendly view of DocIR; regenerable (SOURCE_DERIVED)
```

Markdown is a *rendering* of DocIR, not a second extraction. Regenerating Markdown never needs re-parsing.

## 2. DocIR (T-P4-01)

Per `(blob_id, extractor_set_version)`:
```json
{ "docir_version": "1.0", "blob_id": "b3:…", "document": {"title":…, "genre":…, "lang":["de"], "pages":130},
  "extractors": [{"name":"pymupdf","version":"1.28.2","params_hash":"…"}, {"name":"<math-engine>", …}],
  "pages": [{"index":47, "label":"40", "width":595, "height":842, "triage":{…}, "blocks":["blk_…"]}],
  "blocks": [{"id":"blk_…","type":"paragraph|heading|equation|figure|table|caption|list|code|footnote|header|footer|annotation",
              "page":47,"bbox":[…],"order":12,"text":"…","lang":"de","confidence":0.97,"source":"text_layer|ocr|office|vision",
              "equation_ref":"eq_…","figure_ref":"fig_…"}],
  "equations": [ … see 10 … ], "figures": [ … see 11 … ], "tables": [ … ],
  "sections": [{"id":"sec_…","number":"3.2","title":"Innere Kräfte und Momente","level":2,"page_span":[21,24],"children":[…],"blocks":[…]}],
  "annotations": [{"kind":"pdf_annot|ink_detected|highlight","page":47,"bbox":[…],"text?":…,"class":"USER_ANNOTATION"}],
  "references": [ … ], "quality": {"text_coverage":…, "math_status_counts":{…}, "warnings":[…]} }
```
Headers and footers (e.g. `Ammar Sayyadi · HSH 26.04.2023 · Bachelorarbeit`) are detected by cross-page repetition and flagged, not deleted.

## 3. Structure inference (T-P4-11)

Signal priority: (1) Office heading styles or slide titles; (2) PDF bookmarks (18% of PDFs); (3) numbering patterns
(`3.2`, `Kapitel 4`, `(3-114)` for equations, `Bild 2.17` and `Tabelle 2.7` for figures and tables); (4) font-size and weight clusters;
(5) LLM-assisted outline repair only for documents that fail (1)–(4) (logged, confidence-marked).
Slides: slide = page. Consecutive slides with the same title are grouped into a section.

## 4. Decomposition policy (ADR-012)

Decomposition decides **which Markdown files exist** for humans and Obsidian. It is independent of retrieval chunking.

| Document | Rule (initial; tuned in P4 pilot) |
|---|---|
| ≤ 60 pages, or slides, or exam/exercise | One Markdown file |
| Lecture script > 60 pages with chapters | One file per chapter, plus an index note |
| Textbook (≥ 200 pages) | Index note (TOC, metadata, coverage status) plus one file per chapter. Very long chapters (> 40 pages) are split per section |
| Thesis / reports | One file per chapter plus an index note |
| Twin set (PDF + DOCX) | One logical note set. Content comes from the best representation; page anchors come from the PDF |

## 5. Normalized Markdown format (T-P4-12)

```markdown
---
sbr_id: doc_01J…            # Document id
provenance_class: SOURCE_DERIVED
generated_by: sbr normalize@0.3.0 / docir@1.0
source_blob: b3:9f2c…       # BLAKE3
source_path: "D:\\MBI-BRAIN\\Mechanical\\Dynamik\\Dyn\\Skript Maschinendynamik 1.pdf"
source_aliases: 2
title: Skript Maschinendynamik 1
genre: lecture_script
course: [[Maschinendynamik]]
domains: [[Dynamics]]
language: de
pages: 130
extraction_quality: {text: good, math: partial, figures: detected}
content_hash: …             # hash of this generated body (for user-edit detection)
do_not_edit: true           # banner; edits are detected and preserved, see 19
---
> [!info] Source-derived note. Original: [[pdf link]]. Edits here are preserved as a user fork (see Second Brain rules).

## 3.2 Innere Kräfte und Momente ^sec-3-2
Mit dem Prinzip der virtuellen Leistung können … ^p22

$$
{}_{(k)}\boldsymbol{F}_k = \begin{bmatrix}F_k\\ M_k\end{bmatrix} = \sum_{i=k}^{n_k} \Big[ \dots \Big] \tag{42}
$$
%% eq_01J…  source: omml_exact (twin: Bachelorarbeit.docx) | confidence 1.00 | validated %%

![[fig_01J… .png]]  **Bild 2.17** Zerlegung einer unstetigen Übertragungsfunktion  ^fig-2-17
%% figure: plot | knowledge_bearing 0.93 | page 34 bbox … %%
```
- Page anchors `^pN` use the **PDF page index + 1**. The printed page label is in the metadata.
- Uncertain equations render as `$$ … $$` followed by a visible callout `> [!warning] Equation uncertain (0.62)`.
  A link to the crop lets the owner verify it (HC-18).
- Figures are stored as crops under `vault/_assets/` **only for knowledge-bearing figures**. Otherwise they are referenced by page and bbox.

## 6. Language

Content stays in the source language (mostly German). Concept notes and maps carry bilingual labels (Q-I02).
Retrieval is cross-lingual (13).
