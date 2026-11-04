# Phase 3 Review Preparation (2026-11-04)

Status: **review tooling and evidence prepared. Nothing is owner-approved.** T-P3-02, T-P3-03, T-P3-07 and T-P5-06
stay IN_PROGRESS, and no task became eligible.

**Where this ran.** A Linux container with no corpus and no git-ignored gold files (`eval/gold/layout`,
`eval/gold/math*`, crops). Nothing in this report comes from looking at a real page, crop or slide. LibreOffice
24.2.7 and pandoc 3.1.3 were available here; they are not installed on the owner's Mac.

## 1. Unified review workflow (`tools/review_bundle.py`)

One local page for all four gates. Everything stays on the machine.

```bash
uv run --frozen python tools/review_bundle.py build --config config/sbr.toml
open eval/gold/review/index.html          # review in the browser; press "Export decisions"
uv run --frozen python tools/review_bundle.py import --config config/sbr.toml \
    --decisions ~/Downloads/review_decisions.json --reviewer user:owner --apply-gold-logs
uv run --frozen python tools/review_bundle.py status
```

- **Items:** each one shows the original annotation unchanged, then the machine checks, then any proposals. Each
  proposal names its origin and confidence. The decisions are accept, correct, reject and uncertain, and you can
  also adopt a proposal as your correction.
- **Navigation:** progress counters per section, filters (pending, flagged, decided) and the keys j/k and 1-4.
- **Privacy:** the page cannot reach the network. Its Content-Security-Policy blocks all requests, and the headless
  test recorded zero.
- **Decision handling:**
  - Decisions stay in the browser until you export them. The page records no identity.
  - The import checks the exported file against the exact bundle (by fingerprint) and accepts it whole or not at
    all.
  - It needs an explicit `--reviewer user:<name>`.
  - Re-importing an identical decision does nothing. Changing a recorded decision needs `--allow-supersede`, and the
    earlier record is kept.
- **Storage:** decisions are appended to `eval/gold/review/review_ledger.jsonl` (git-ignored).
  - `--apply-gold-logs` also writes them into the existing `layout_verification.yaml` and `math_verification.yaml`
    logs, in the format the verify tools already read.
  - `uncertain` stays pending in those logs.
  - Originals are never edited. A layout correction is stored as `corrected_annotation`.
- **Taxonomy approval:** `--write-curation-approval` appends an approval to `curation/approvals.yaml` only if the
  ledger holds an explicit `accept` of `taxonomy:approve-v0`, and only for `user:owner`.
- **Restricted content:** paths blocked by the sensitivity rules are left out of the bundle; only their count
  appears.

| Section | Items | Built here? | Source |
|---|---|---|---|
| layout | 40 | no (input on the Mac only) | `eval/gold/layout/layout_annotations.yaml` |
| math | 300 | no (Mac only) | `eval/gold/math_sample.yaml` + crops |
| math double-check | 30 (10%, separate seed, first-pass decision hidden) | no (Mac only) | derived from math |
| PPTX math | 50 | **yes** | `eval/reports/spike_omml_native.md` |
| taxonomy | 86 (43 concepts, 42 courses, 1 overall approval) | **yes** | `curation/*.yaml` + `eval/reviews/taxonomy_v0_ai_review.yaml` |

On the Mac, `build` produces all **506** items.

## 2. T-P3-03 layout: what the checks look for

These are deterministic checks on the draft annotations; the page itself is not needed:
- reading order is a valid unique sequence
- empty blocks
- scanned pages without text
- column and order heuristics
- header or footer blocks in the middle of the order
- ragged tables, and missing tables or captions where the bucket expects them
- lines that look like math but have no equation annotated
- repeated text

**Systematic finding (from the draft code):** `draft_gold_layout.py` writes one block per text *line*. A gold set
normally needs one block per paragraph. Every page with consecutive paragraph lines therefore gets a
`merge_paragraph_lines` proposal, at medium confidence. It joins the lines of each paragraph. It removes a line-end
hyphen only when the next line starts lowercase, so "Sensor-" + "Aktor" keeps its hyphen. The 14 pages in the
risky buckets (unusual reading order, multi-column, scanned) sort first. Nothing here compares against the page
images; that comparison is the owner's.

## 3. T-P3-02 math

- **OMML entries (180):** each crop is re-parsed and checked for well-formed XML and exactly one equation. Each
  entry is then compared with the native conversion of its own crop.
  - The earlier macOS run found **42 mis-paired entries** (23.3%, list in `eval/reports/spike_omml_native.md`); the
    stored LaTeX belongs to another equation. Each gets an error flag and a proposal holding the crop's own native
    LaTeX (medium confidence).
  - The other 138 agreed with the native conversion (notation folded).
- **PDF crops (120):** no local formula model is configured (ADR-039/ADR-040), so no transcription was invented.
  These entries can't be accepted. They can be corrected with a hand transcription, rejected, marked uncertain or
  left pending.
- **Double-check:** 30 entries with LaTeX, stratified by difficulty, drawn with their own seed, shown without the
  first-pass decision.

## 4. T-P3-07 PPTX math: options (evidence, not a decision)

Measured with `tools/spike_pptx_math.py` (`eval/reports/spike_pptx_math_options.md`): a synthetic 14-equation deck
stored the way PowerPoint stores math. Each equation's fallback carries a unique marker, so an output that contains
the marker read the fallback, not the equation.

| Criterion | A native OMML->LaTeX | B LibreOffice 24.2.7 | C render + recognize | pandoc 3.1.3 |
|---|---|---|---|---|
| Equations kept as math | 14/14 synthetic. Real corpus (earlier Mac run): 497/497 converted, 0 fallbacks | **0/14**: imports the fallback (14/14 markers); real fallbacks are pictures | no local recognizer yet (T-P3-06) | no PPTX reader |
| Structure | LaTeX tree (fractions, scripts, n-ary operators, matrices) | none | approximate, from pixels | n/a |
| Notes | yes, attributed to their slide | not in PDF export | via rendered notes only | n/a |
| Slide reading order | deck order from `presentation.xml`; document order within a slide | layout order | visual | n/a |
| CPU / memory | about 16 ms per 14 equations, under 1 MB | about 2.3 s cold start per file, up to 216 MB RSS | GPU or slow CPU model | n/a |
| Dependencies / licence | stdlib, own code | LibreOffice (MPL-2.0), large install | model weights, licence varies | GPL |
| Portability | pure Python on all three OSes | all three, heavy | depends on the model | all three |
| Integration | already in the repo; the same code path covers DOCX | subprocess plus a profile directory | new pipeline stage | n/a |

**Recommendation:**
- Use A for PPTX OMML. Consider A for DOCX too, since it agreed with pandoc on 138/138 correctly paired equations.
- Keep C only as a fallback for picture-only math, such as legacy Equation 3.0/OLE objects.
- Use B for legacy `.ppt`/`.doc` container conversion only (T-P4-05), never for math.

**Owner decision still needed:** the ADR-009 PPTX path and the ≥98% check on the 50 real equations.

**Converter changes this session** (`omml_latex.py`, from patterns visible in the real 50-sample):
- Function names inside a longer run become operators: `f=min` → `f=\min`, and `-ln`, `det` likewise.
- Prose typed in a math zone becomes `\text{}`, while the math around it stays math: `\{P\}\rightarrow\{\text{Term
  nach Zuweisungen}\}`.
- A scoring-key bug is fixed: a matrix row break `\\` followed by a space was read as a spacing command.

These change the real outputs, so **re-run `tools/spike_omml.py --native-latex` on the Mac before the 50-equation
review**. The bundle's PPTX items show the stored LaTeX plus a preview of the new rules (5 of 50 change); after the
re-run, rebuild the bundle.

**Circularity caveat.** The prose and function benchmark cases were written from the same patterns as the converter
fix, so the synthetic 14/14 is a regression check, not independent evidence.

## 5. T-P5-06 taxonomy

The structure is consistent: every reference resolves, and the links are reciprocal (existing tests). The machine
checks flag 14 items:
- 7 courses with two domains
- 7 courses mapped to non-leaf concepts
- 4 poly-hierarchies, which are informational
- 8 roots used only through their children
- one label close to another ("Programmierung" / "Systemprogrammierung"), which are distinct concepts, not
  duplicates

An AI review (`eval/reviews/taxonomy_v0_ai_review.yaml`; proposals only, nothing applied) adds 8 proposals. The
substantive ones:
- **MBI-204 and MBI-273-01 (Bewegungslehre) → Maschinendynamik:** probably mechanism kinematics (Getriebelehre)
  instead. Check the Modulhandbuch; low confidence.
- **MBI-221 (Technische Mechanik 4) → the non-leaf engineering_mechanics:** a `strength_of_materials`
  (Festigkeitslehre) leaf is missing (medium).
- **MBI-127 (Physik 2) also → scientific_communication:** likely spurious (medium).
- **"Sensor-Aktor-Bus-Systeme":** align it with the Modulhandbuch name "Sensor-Aktor-Bus-Technik" (medium).
- **Smaller points:** "Projektarbeit" instead of "Ingenieurprojektarbeit"; the single-child pair Werkstofftechnik ⊃
  Werkstoffkunde; MBI-110 mapped to the root computer_science.

## 6. Owner actions, in unlock order

1. On the Mac: `tools/gold_verify_layout.py --prepare`, then `tools/spike_omml.py --native-latex`, then
   `tools/review_bundle.py build`.
2. Review the 40 layout pages. Then T-P3-05 (SPIKE-PARSER) and T-P3-10 (SPIKE-FIGURE) can start.
3. Review the 180 OMML math entries (42 flagged mis-paired), decide the 120 PDF crops (transcribe, reject or leave
   pending), and do the 30-entry double-check. Then T-P3-06 (SPIKE-MATH) can start.
4. Review the 50 PPTX equations and choose the ADR-009 PPTX path. That closes T-P3-07 and frees T-P4-05.
5. Decide the taxonomy items, then accept or reject `taxonomy:approve-v0`.
