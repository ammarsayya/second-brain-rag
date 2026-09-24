# 11 — Visual Content

Standalone pictures were removed by the owner, and ~12.8k images still remain (t0), mostly lab and render photos. Knowledge-bearing visuals
live **inside documents**: block diagrams, Bode plots, step responses, trusses, FEM results, robot kinematic sketches, circuit schematics,
technical drawings, experimental setups and formula tables (03 §6). The average is 3.7 embedded images per page, and the median is ~10 vector drawing ops per page.
Many diagrams are **vector drawings**, not images.

## 1. Relationship model

```
SOURCE → PAGE → { TEXT BLOCKS, EQUATIONS, FIGURE(bbox, kind, caption, label "Bild 2.17"), TABLE(caption, label) }
FIGURE ←referenced_by── TEXT BLOCK ("siehe Bild 2.17", "Abb. 3")    [resolved by label matching]
FIGURE ──explains/depicts→ CONCEPT       [P8, evidence = caption + referencing text]
FIGURE ──visualizes→ EQUATION            [e.g. step response ↔ g(t) formula]
```

## 2. Knowledge-bearing vs decorative (SPIKE-FIGURE, T-P3-10)

Heuristic features (cheap, deterministic): the same image hash repeated on many pages (logos, templates → decorative); size relative to the page;
caption present or a label pattern nearby (`Bild`, `Abb.`, `Fig.`, `Tabelle`); referenced in text; vector drawing density; position (header/footer);
aspect ratio. A **small classifier** (rules first, optionally a tiny vision classifier) outputs `is_knowledge_bearing` with confidence.
Decorative figures are recorded (bbox) but never cropped, described or indexed.

## 3. Processing tiers

| Tier | Action | Cost | When |
|---|---|---|---|
| F0 | Detect regions (images + vector clusters), captions, labels, references | Low (CPU, deterministic + layout model) | All processed pages |
| F1 | Crop knowledge-bearing figures to `var/artifacts/.../fig_*.png` (and the vault `_assets` for W1/W2) | Low | Knowledge-bearing only |
| F2 | **Figure card**: caption + referencing text + OCR of labels inside the figure (axis labels, block names) | Medium | W1/W2 |
| F3 | **AI description** by a multimodal model (what the diagram shows, variables, relations), stored as AI_GENERATED and cited to the crop | High (API or local VLM) | On demand (JIT) or for high-value figures in core domains |
| F4 | Structured extraction (block diagram → signal-flow graph; plot → data series) | Very high | Future (P14 experiments) |

## 4. On-demand visual understanding (FR-20, SPIKE-MULTIMODAL)

The orchestrator calls `inspect_visual(locator, question)` when: the question refers to a figure ("Bild", "Diagramm", "Schaltplan", "Bode");
the evidence pack contains a figure card without an F3 description; or math validation is uncertain on the evidence page. The tool renders the region
(or page) at an adequate dpi and asks the configured `vision` role model. The result is cached as an F3 artifact with provenance.
SPIKE-MULTIMODAL measures when this improves answers versus cost.

## 5. Tables

Tables are extracted to structured cells (HTML/Markdown) with confidence. Formula tables (e.g. "Tabelle 2.7 Gewichtsfunktionen elementarer
Ü-Modelle") route their cells through the math tier. Low-confidence tables keep the crop plus the raw text layer.

## 6. Scanned pages

OCR (engine per SPIKE-OCR) produces text blocks. Figures on scanned pages are detected as image regions (the page is one image).
The truss diagrams in the Statik tutorials show that figure crops are essential evidence there.

## 7. Handwritten annotations (USER_ANNOTATION)

Detection: PDF annotation objects (10.8% of sampled documents), plus ink detection on rendered pages (strong saturated colors such as red or blue
on otherwise black-and-white pages, and freehand strokes) for annotated copies such as the dynamics script. Stored as Annotation regions linked
to the nearest block or equation. OCR of handwriting is optional (Q-I03). Annotated variants are protected from dedup collapse (see 14/ADR-032).
