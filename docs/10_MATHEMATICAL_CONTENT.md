# 10 — Mathematical Content

Formula preservation is a **hard requirement** (HC-05). The audit shows that text layers destroy math structure for Word/Cambria Math,
MathType/Symbol **and** LaTeX display math (03 §6). ~54% of sampled documents carry math fonts, with ~66k unique pages (upper bound) at t0.

## 1. Sources of mathematical truth, in priority order

| Priority | Source kind (`source_kind`) | When | Expected fidelity |
|---|---|---|---|
| 1 | `omml_exact`: Office Math (OMML) in DOCX/PPTX → LaTeX via deterministic conversion (pandoc or equivalent, SPIKE-OMML) | An Office original or twin exists (thesis: 422 equations; Praxisphase: 388; exercise solutions: 322; t2 census, docs/37 §10) | Exact (conversion bugs aside) |
| 1b | `office_ole_equation`: Equation Editor 3.0 / MathType OLE objects (MTEF) in legacy `.doc` and in OOXML, converted via LibreOffice or an MTEF converter (SPIKE-OMML) | 70 unique legacy `.doc` files at t2 (physics exams, Math 3, Messtechnik) | Exact if the conversion succeeds; validated like OMML |
| 2 | `latex_source`: LaTeX source files | None found in the corpus yet (.tex = 0). Kept for future sources | Exact |
| 3 | `vision_recognized`: formula region → recognizer → LaTeX | Any PDF page with math (MathType, scanned, LaTeX display math) | Model-dependent. **Measured by SPIKE-MATH** |
| 4 | `text_layer_linear`: Unicode math from the text layer | Simple inline math (`a₁ ≤ a₂`, `x ∈ ℝⁿ`) with high structural confidence | Acceptable only for flat expressions |
| 5 | `none`: image placeholder with crop | Recognition failed | The crop is still cited; no LaTeX claimed |

Several readings can coexist for one equation (for example, a text-layer reading and a vision reading). The **preferred reading** is chosen by
priority and validation score. The others remain stored.

## 2. Pipeline

```
page triage (math-font spans, glyph-soup ratio, Symbol/MTExtra/CMEX fonts, OCR needed?)
  → formula detection (layout model: display + inline regions)               [engine: SPIKE-PARSER/MATH]
  → crop @ 200–300 dpi → recognizer → LaTeX candidate(s)                      [engine: SPIKE-MATH]
  → validation:
      V1 syntax: parse with KaTeX/MathJax-compatible parser (compiles?)
      V2 render-compare: render LaTeX → image; compare to crop (structural similarity after binarization + size normalization)
      V3 text-layer consistency: symbols in the text-layer glyph soup ⊆ symbols in LaTeX (multiset overlap)
      V4 twin agreement: if an OMML twin exists, compare normalized LaTeX (tree edit distance)
      V5 label/number consistency: equation number "(3-114)" matches the detected label position
  → confidence = calibrated combination (calibrated on MBI-Gold math set, T-P3-02)
  → status: verified (≥ τ_high or twin-exact) | plausible | uncertain (< τ_low) | failed
  → uncertain/failed → reprocess queue (better engine / remote tier / owner verification)
```
Thresholds τ are calibrated in P3, not guessed.

## 3. Representation (Equation record)

```
equation_id, document_id, blob_id, page_index, bbox, display|inline, label "(3-114)",
readings: [{latex, source_kind, engine@ver, confidence, validations{V1..V5}}], preferred_reading,
latex_normalized, symbols[] (normalized tokens), structure_signature, variables[] → SymbolDefinition,
context: {preceding_text_block, following_text_block (wobei/mit/where), section_path, figure_refs[], table_ref},
units[], assumptions[] (extracted from context), validation_status, crop_ref
```

**Normalization (`latex_normalized`)** removes presentational noise (`\left`/`\right`, spacing, `\mathrm` vs roman variants,
`\boldsymbol` vs `\mathbf` → a canonical bold). It canonicalizes `\cdot` versus juxtaposition and orders commutative operands where safe.
It keeps the original. This is a deterministic library with property tests (TS-MATH-*).

## 4. Linking equations to meaning (T-P5-02)

- **Variable definitions:** patterns such as "wobei X …", "mit X: …", "Dabei ist …", "where X denotes …", symbol tables
  ("Formelzeichen"), plus LLM-assisted extraction with span evidence. Output: `SymbolDefinition{symbol, meaning, unit, scope: document|section}`.
- **Context window rule (for retrieval and answers):** an equation is never served alone. The minimum evidence pack is
  the equation, the preceding sentence(s) introducing it, the following variable definitions, the section title path, the equation label,
  referenced figures or tables, and the page locator.
- **Equation cards (AI_GENERATED, cached):** a short natural-language description in German and English ("Bewegungsgleichung
  eines Starrkörpersystems nach dem Prinzip der virtuellen Arbeit …"), names ("Lagrange equations of the second kind"), and variables.
  These are used for dense and lexical retrieval. They are labeled AI-generated and cite the equation.

## 5. Mathematical retrieval (see 13 §5)

Queries may use names ("Lagrange 2. Art"), symbols ("ẋ = Ax + Bu"), concepts ("Zustandsraum"), structures ("2x2 Matrix mit cos/sin")
or equivalent notations. Plan: **math-aware lexical** (symbol and structure n-grams over `latex_normalized`) + **equation-card dense
retrieval** + **name/concept lookup via the graph**, with fusion. Research basis: the ARQMath evaluations (CLEF 2020–2022) found that combining
formula-structure retrieval (symbol-layout or operator-tree approaches such as Tangent-CFT and Approach0) with text context works better
than either alone. Pure text embeddings of raw LaTeX are weak. *(This is model knowledge, to be verified by SPIKE-MATHRET on MBI queries.)*

## 6. Comparison and equivalence

Symbolic equivalence (for example `ẋ=Ax+Bu` vs `\frac{dx}{dt} = A x + B u`) uses normalization first, then optional SymPy parsing
(latex2sympy) for simple algebraic forms, then a structural signature match. Equivalence claims are `Relation(equivalent_to)` with evidence
and confidence. They are never asserted without validation.

## 7. Compute strategy for math (ties to ADR-007, Q-B03)

- W1/W2 (course material, ~55–90k pages): all math regions are recognized.
- W3 (textbooks): recognition is JIT for pages hit by retrieval with uncertain math, plus scheduled background batches ordered by domain priority.
- Optional remote acceleration (rented GPU running an open model, or an API) only if the owner allows it (Q-B03). The sensitivity gate applies.

## 8. Unknowns (spikes)

SPIKE-MATH (recognizer accuracy and CPU speed on MBI crops: MathType, Word, LaTeX, scanned typewriter, handwritten),
SPIKE-OMML (conversion fidelity), SPIKE-MATHRET (retrieval approach), SPIKE-COMPUTE (throughput and cost).
Candidate recognizers to test: UniRec-0.1B, PP-FormulaNet (PaddleOCR), UniMERNet, MinerU2.5 (formula submodule), Docling formula enrichment,
texify/Surya (Marker), pix2tex (baseline), and a multimodal LLM via the gateway (reference or upper bound). **No recognizer is chosen yet.**
