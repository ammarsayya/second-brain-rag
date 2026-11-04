# Owner Review Index (2026-11-04)

Status: **prepared for review. Nothing here is owner-approved.** Every item below stays IN_PROGRESS until the owner
records decisions. Agent-generated drafts, heuristics and recommendations are inputs, not approvals.

All four reviews are **unblocked for the owner now**. They gate the whole critical path: no engineering task is
eligible until they are done (`tools/validate_plan.py`: *next eligible: none*).

## Unlock order (what each review frees)

| Review | Effort (est.) | Directly unlocks |
|---|---|---|
| T-P3-03 Layout gold (40 pages) | ~1-2 h | T-P3-05 (SPIKE-PARSER) and T-P3-10 (SPIKE-FIGURE) |
| T-P3-02 Math gold (180 OMML + 120 drafts) | ~3-5 h for OMML part | T-P3-06 (SPIKE-MATH). The 120 PDF-native entries also need Q-B04 |
| T-P3-07 Office-math sample (50 equations) + ADR-009 choice | ~1 h | closes T-P3-07, input to T-P3-11 |
| T-P5-06 Taxonomy v0 | ~30-60 min | one of two dependencies of T-P5-07 (the other, T-P5-01, is NOT_STARTED); also a dependency of the task at docs/28 line ~2124 (which also needs T-P7-01) |

Effort figures are rough estimates, not measurements. T-P3-09 additionally needs T-P3-05/06/08 and Q-B03.

The gold artifacts live under git-ignored `eval/gold/` **on the macOS host**. The commands below were not run in the
Linux session that wrote this index (the corpus is not present there); they are the documented interfaces
(`--help` was checked).

---

## 1. T-P3-03 MBI-Gold-Layout (40 pages)

- **Draft:** 40 of 40 pages selected over 11 layout buckets (unusual reading order 4, multi-column 5, scanned 4,
  annotated 4, slide-like 4, table-heavy 4, figures-with-captions 4, lists 3, header/footer/page-number 3,
  headings/paragraphs 3, plain-text controls 2). Labels are **deterministic heuristics, no model**.
- **Highest-risk (uncertain) cases to look at first:** the *unusual reading order*, *multi-column* and *scanned* buckets
  (14 pages). Heuristic reading order and table rows are least reliable there. The *scanned* pages have no text layer,
  so their draft text is expected to be empty or poor.
- **Review:**
  ```bash
  uv run --frozen python tools/gold_verify_layout.py --prepare --config <config>   # exports 40 one-page PDFs + index
  uv run --frozen python tools/gold_verify_layout.py --export-sheet layout_review.csv --config <config>
  # fill the decision column (accept/correct/reject), correct the aggregate annotation YAML for "correct" rows, then:
  uv run --frozen python tools/gold_verify_layout.py --record-sheet layout_review.csv --config <config>
  ```
- **Acceptance (docs/28):** 40 pages labeled and verified; every rejection resolved.
- **Decisions needed:** none beyond per-page accept/correct/reject. Whether 40 pages is enough to compare engines is
  an owner judgment.

## 2. T-P3-02 MBI-Gold-Math (300 entries)

- **Draft:** 300 selected = **180 OMML-exact** (real pandoc-derived LaTeX; raw OMML subtree shown as the source
  substitute because no DOCX renderer exists) + **120 PDF-native crops** (`latex: null`, `status: pending_ai_draft`).
- **Exclusions already applied (for transparency):** 9 DOCX files whose OMML count differed from pandoc's were dropped
  wholesale; 52 equations with display/inline disagreement were dropped individually.
- **Provenance/confidence:** OMML entries are the closest thing to ground truth (author-typed equations) but the LaTeX
  is a pandoc conversion, so structure errors are possible. PDF entries have **no transcription at all**; there is no
  confidence figure and none should be invented.
- **Review:** `tools/gold_verify_math.py --prepare | --export-sheet | --record-sheet` (same pattern as layout). The
  page uses an offline pandoc-MathML fallback, **not KaTeX** (no local KaTeX assets). Supply `--katex-dir` for a true
  KaTeX render.
- **Double-check requirement:** an independent second pass over 10% (30 entries). Pick them with a different seed than
  the review order so they are not the same entries you already skimmed.
- **Decisions needed:** (a) review/correct/reject the 180 OMML entries now; (b) the 120 PDF crops can only be drafted
  after Q-B04 (see decision package) or be transcribed by hand; (c) accept a lower target than 300 verified entries
  if the 120 stay unresolved (this would be a plan change, not an agent decision).

## 3. T-P3-07 SPIKE-OMML (Office math) and the ADR-009 choice

- **Measured evidence (macOS host, real corpus):**
  - PPTX: 35 files scanned, 13 with OMML, **497 native equations** (484 on 53 slides, 5 in notes, 8 elsewhere); pandoc
    extracts 0 of them. Only 4 of the 13 files have a PDF twin.
  - DOCX: 2,597 native equations vs pandoc 2,608 (within 0.4%); pandoc is adequate for DOCX.
  - A stdlib native OMML->LaTeX prototype exists (`src/sbr/eval/extract/omml_latex.py`, report
    `eval/reports/spike_omml_native.md`); `tools/spike_omml.py --native-latex` runs it.
- **Options for PPTX math (no choice made):**

  | Option | For | Against / unknown |
  |---|---|---|
  | A. Extend native OMML->LaTeX to PPTX | deterministic, no new dependency, keeps slide/notes locator | converter coverage unproven on exotic constructs; owner review of the 50-sample is the fidelity evidence |
  | B. Convert PPTX->DOCX/PDF (LibreOffice) then reuse existing paths | reuses pandoc/PDF paths | LibreOffice absent; OMML survival through conversion untested |
  | C. Route PPTX slide math to SPIKE-MATH (image path) | engine-agnostic | loses exactness; needs the math engine and possibly Q-B04 |
- **50-equation validation sample:** `uv run --frozen python tools/spike_omml.py --native-latex --config <config> --review-sample-size 50 --seed <n>`.
  Compare each LaTeX against the rendered slide/equation.
- **Decision needed (owner/ADR-009):** pick A, B or C for PPTX, or request further evidence. The agent must not
  choose. Relevant data: 497 equations in 13 files is a small, finite set; hand-review of all of them is feasible.

## 4. T-P5-06 Taxonomy v0 (43 concepts, 42 courses)

Computed from the tracked `curation/taxonomy.yaml` and `curation/course_map.yaml` on 2026-11-04:

- 43 concepts under **10 root domains**; 4 deliberate poly-hierarchies: `sensor_actuator_bus_systems` (automation +
  electrical), `robotics` (automation + mechanical), `finite_element_methods` (computational + engineering mechanics),
  `simulation_technology` (computational + systems modeling).
- **7 courses carry two domains** (candidates for ambiguity review): MBI-127 Physik 2 (physics / scientific
  communication), MBI-206, MBI-210 (measurement / control), MBI-271 (control / sensor-actuator-bus), MBI-274
  Prozessleittechnik (industrial automation / control), MAB-232-01 C/C++ (programming / systems programming), MBI-276
  Maschinenelemente 2 + Kolbenmaschinen (machine elements / piston machinery).
- **7 courses map to a non-leaf concept** (a broader node): MBI-105, MAB-205-01 -> machine_design; MBI-124 ->
  electrical_engineering; MBI-110 -> computer_science; MBI-221 -> engineering_mechanics; MBI-232 and MAB-232-01 ->
  systems_programming. The owner should confirm that mapping to a parent is intended rather than a missing leaf.
- **8 of the 10 roots are used by no course directly** (only via their children); 24 concepts are used by exactly one
  course, i.e. the taxonomy is currently as granular as the course list. Judge whether it needs more depth from the
  textbooks later (expected, not a defect).
- 22 concepts have no `related` edge. Fine for v0, but the knowledge graph gains little from them until edges exist.
- **Review:** open `eval/gold/taxonomy/review/index.html` (regenerate with
  `python tools/render_taxonomy_review.py --prepare`). German labels were drafted by the agent and need native-speaker
  review.
- **Approval criteria (docs/28):** owner approves v0; every course maps to at least one domain (already true: 42/42).
- **Decisions needed:** approve, or list corrections to structure, labels, edges, and the 7 + 7 cases above.

---

## What stays unresolved regardless of review

- Q-B03 and Q-B04 (see `2026-11-04_decision_packages_QB03_QB04.md`).
- Registry rescan on macOS and the 186 corpus paths missing there (see the macOS migration plan, section 4).
- ADR-009 (math engine) and ADR-010 (OCR/orientation handling) remain PROPOSED until T-P3-11.
