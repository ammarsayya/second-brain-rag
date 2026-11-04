# Next-Tasks Implementation Report: 2026-11-04

- **Date:** 2026-11-04
- **Implementer:** Claude (Opus 5.5), via the `do-the-next-ten-tasks` workflow
- **Repository:** `/Users/ammar/DriveD/AgenticAI/second-brain-rag`, branch `main` at `7d24c58`. The tree was clean at
  the start. Nothing has been committed.
- **Canonical state:** `docs/35_EXECUTION_STATE.json`; task register `docs/28_TASK_REGISTER.md`
- **Receipt:** this project has no RC numbering. Evidence is recorded as dated addenda in docs/28 (T-P3-07, T-P3-08)
  and two `implementation_log` entries in docs/35.
- **Platform:** macOS (Darwin 27), Python 3.12.14 via `uv --frozen --offline`, Tesseract 5.5.3. pandoc, pdflatex
  and PowerShell are absent.

## 1. Executive Summary

The batch target was ten tasks. Only **three honest slices** existed. The plan validator reports **zero eligible
tasks**, and all five IN_PROGRESS tasks are formally waiting on owner review. I did not pad the batch.

| | Count |
|---|---|
| Selected | 3 slices: T-P3-08 follow-up, T-P3-07 follow-up, `relpath_raw` hygiene |
| Implemented and verified | 3 |
| Formally completed (status changed) | **0**. T-P3-07 and T-P3-08 stay IN_PROGRESS because their acceptance needs owner review. |
| Not attempted | T-P3-02, T-P3-03, T-P5-06 (owner review only), and every NOT_STARTED task (dependencies not DONE) |

New real-corpus evidence:
- **Orientation (T-P3-08):** OSD on all 764 scanned candidates gives rotate 0/90/180/270 = 314/54/169/32.
  `--psm 1` recovers 90° pages (+28.3 mean word confidence) but does nothing for 180° pages (146 of 159 unchanged).
- **PPTX math gap (T-P3-07):** 497 native OMML equations in 13 PPTX files, which is what pandoc drops today. DOCX
  has 2,597 native equations, against pandoc's 2,608 (within 0.4%).

Tests went from 485 passed / 5 skipped to **503 passed / 5 skipped**, with no regressions.

## 2. Starting Project State

Phase "P3/P4/P5/P13". Task counts: 146 total, 45 DONE, 92 NOT_STARTED, 5 IN_PROGRESS, 1 BLOCKED, 3 DEFERRED.
Open blockers are Q-B03 (compute/privacy) and Q-B04 (model access).

| Check | Baseline |
|---|---|
| `ruff check src tests` | PASS |
| `ruff format --check src tests` | PASS |
| `mypy src` (strict, 69 files) | PASS |
| `pytest` | PASS: 485 passed, 5 skipped (pdflatex not installed) |
| `tools/validate_plan.py` | PASS: PLAN CONSISTENT, next eligible: none |
| `tools/check.ps1` | NOT RUN: PowerShell is not installed. Its steps were run individually instead. |

## 3. Selected Tasks

Selection rules: no NOT_STARTED task has all its dependencies DONE. Of the IN_PROGRESS tasks, only T-P3-07 and
T-P3-08 are `Human approval: none`, and each has a recorded technical gap that closes offline. For each, I confirmed
the gap still existed in code before starting.

| Order | Task | Title | Phase | Deps (status) | Why |
|---|---|---|---|---|---|
| 1 | T-P3-08 | SPIKE-OCR | P3 | T-P3-04 (DONE) | The recorded upside-down-page finding had no measurement. Tesseract is installed, so an OSD census was possible. |
| 2 | T-P3-07 | SPIKE-OMML | P3 | T-P3-04 (DONE) | Recorded gap: pandoc extracts 0 PPTX equations, and its size was unknown. Counting needs no pandoc. |
| 3 | (tools for T-P3-01/02/07/08) | Open sources by `relpath_raw` | P3 | n/a | Some tools opened sources by the NFC `relpath`, which can fail for NFD names on NTFS. |

## 4. Implementation Details

### T-P3-08: page-orientation census
- **Change:** `src/sbr/eval/extract/ocr.py` gains `OsdResult`, `parse_tesseract_osd()` and `summarize_rotations()`.
  These are pure functions. The parser returns `None` on "Too few characters" or malformed or impossible values, and
  never guesses 0. `tools/spike_ocr.py` gains `--orientation-census`, `--control-size` and
  `--min-orientation-confidence`. Discovery and image extraction are factored into `_find_scanned_candidates()` and
  `_first_page_image()`, which the sampled mode reuses. The sampled mode's candidate order and seed behaviour are
  unchanged.
- **Decision:** the census writes its own report (`eval/reports/spike_ocr_orientation.md`) and leaves the Windows-run
  `spike_ocr.md` alone. The 2.0 confidence cut-off is only a reporting aid; no page is dropped because of it.
- **Real-corpus result:** 764 candidates. 119 pages have no embedded image, 3 had read or OSD errors, and OSD
  declined 73. Change in mean word confidence from `--psm 3` to `--psm 1`, by OSD rotate:

  | OSD rotate | Pages compared | Mean change | Unchanged (0.0) | Gain > 10 |
  |---|---|---|---|---|
  | 90° | 52 | **+28.3** | 9 | 40 |
  | 180° | 159 | −0.1 | 146 | 1 |
  | 270° | 32 | +1.1 | 23 | 2 |
  | upright control | 14 | −0.9 | n/a | n/a |

  The "Gescannt" scans that the first pass flagged are 90° in this census, and they recover to 83–87 confidence
  under `--psm 1`.
- **How to read it:** `--psm 1` is not a general orientation fix. Many 180°/270° OSD calls fall on pages that already
  OCR at high confidence, so they look like false positives. Caveat: OSD runs on the page's first embedded image,
  which ignores the page's `/Rotate` and content transform. Word confidence is not CER.
- **Tests:** 6 in `tests/test_eval_extract_ocr.py`, using captured real Tesseract 5.5.3 output. 3 in
  `tests/test_spike_ocr.py`: discovery over a real registry built from the fixture corpus, and the census with
  Tesseract replaced by canned real outputs, so the tests run without Tesseract instead of skipping.
- **Still open:** CER (needs gold transcriptions from T-P3-03), PaddleOCR or a remote VLM (owner policy), handwriting
  detection, and the orientation step and threshold (ADR-010/T-P4). **Final status:** IN_PROGRESS.

### T-P3-07: native OMML inventory
- **Change:** `src/sbr/eval/extract/omml.py` gains `count_omml_equations()` and `OmmlCount`. The counter matches
  outermost `m:oMath` elements by namespace URI, separates display (inside `m:oMathPara`) from inline, counts each
  `mc:AlternateContent` equation once, and returns `None` for unparseable XML. `tools/spike_omml.py` gains
  `--pptx-inventory`, `part_kind()` and `inventory_office_file()`. Its own report is
  `eval/reports/spike_omml_inventory.md`.
- **Real-corpus result:**
  - PPTX: 35 canonical files scanned, 13 with OMML, **497 equations** (484 on 53 slides, 5 in notes, 8 in other
    parts), 4 with a PDF twin.
  - DOCX: 158 scanned, 31 with OMML, 2,597 equations (934 display), 11 with a PDF twin, 3 not valid ZIPs.
  - Totals reconcile with the first run: 31 + 13 = 44 files and 11 + 4 = 15 twins.
  - **Discrepancy found:** the register's 2026-09-26 note says "14 PPTX", but that run's own table lists 13. I
    recorded the correction in a dated addendum and left the earlier text unchanged.
- **Tests:** 5 new in `tests/test_eval_extract_omml.py`: the fixture PPTX, nesting and display, prefix
  independence, malformed XML, and an entity-expansion/XXE refusal test. 4 in `tests/test_spike_omml.py`, including
  an end-to-end run over a registry.
- **Still open:** the owner's 50-equation review, and the ADR-009 choice of PPTX path (another converter, or routing
  PPTX math to SPIKE-MATH). The pandoc pass was not re-run because pandoc is absent on this host. **Final status:**
  IN_PROGRESS.

### Hygiene: open sources by `relpath_raw`
`tools/spike_ocr.py`, `tools/spike_omml.py`, `tools/select_gold_extract_sample.py` and
`tools/select_gold_math_sample.py` now open sources by the exact on-disk name and still report the NFC `relpath`.
Existing selector tests pass unchanged (19).

Remaining limit: `goldfile.py` and `draft_gold_layout.py` open sources by the `relpath` stored in gold YAML, which has
no raw form. Fixing that needs a schema change, so I left it.

## 5. Integration Improvements

| Before | After |
|---|---|
| The orientation defect was one anecdote | Orientation is measured on every scanned candidate, with a psm 1 vs psm 3 effect by rotation |
| The size of the PPTX equation gap was unknown | 497 equations are quantified, and the DOCX pandoc count has an independent cross-check |
| Spike tools mixed `relpath` and `relpath_raw` | All spike tools and selectors open by `relpath_raw` |

Nothing was wired into a live pipeline path. These are spike or evidence tools only.

## 6. Security Review

- **Source access:** every corpus read went through SourceFS, read-only. `MBI-BRAIN` and `studium_duplicated` were
  not written. The macOS config used for the runs is a throwaway copy in the session scratchpad; the local
  `config/sbr.toml` is unchanged.
- **XML parsing:** `count_omml_equations()` uses stdlib ElementTree. Bundled expat 2.8.5 refuses entity amplification
  and does not resolve external entities, and `test_refuses_entity_expansion_and_external_entities` pins that. I
  used a justified `noqa: S314` instead of adding `defusedxml`, because a new dependency would need an ADR.
- **No model calls, no network, no token spend.**
- **Sensitivity:** all 328 files named in the three eval reports are `active`/`normal` in the registry. One
  orientation-report row is a filename that looks like a personal legal document, in `books\Studium\lernen\`, even
  though it is classified `normal`. I'd like the owner to review its sensitivity before these reports are
  committed.

## 7. Test Results

| Check | Baseline | Final |
|---|---|---|
| ruff check src tests | PASS | PASS |
| ruff format --check src tests | PASS | PASS (131 files) |
| mypy src (strict) | PASS (69 files) | PASS (69 files) |
| pytest | 485 passed, 5 skipped | **503 passed, 5 skipped** (+18 new, same 5 pdflatex skips) |
| validate_plan.py | PLAN CONSISTENT | PLAN CONSISTENT |
| audit_crossrefs.py | not run | CROSSREFS CLEAN |
| export_schemas.py --check | not run | no output (no schema change) |
| mypy on touched tools (outside the gate) | n/a | spike_ocr and spike_omml clean. `select_gold_math_sample.py` has 6 errors, identical on HEAD (pre-existing). |

No regressions. The two problems I introduced and fixed:
- I briefly added a `sort()` to OCR candidate discovery. It would have changed the seeded sample in the existing
  report, so I removed it before any run.
- A test expectation was wrong about the format of the per-part summary.

## 8. Task-State Changes

No status changed. Changes to the records:
- docs/28: dated addenda under T-P3-07 and T-P3-08.
- docs/35: `last_updated` set to 2026-11-04, `updated_by` updated, and two IN_PROGRESS `implementation_log`
  entries appended.
- Line endings preserved: CRLF, plus the one existing bare-LF line.

## 9. Remaining Blockers

1. **Owner reviews:** T-P3-02 (300 math entries plus a 10% double-check), T-P3-03 (40 layout pages), T-P3-07
   (50-equation review), T-P5-06 (approve Taxonomy v0). T-P3-08 needs a decision on PaddleOCR/VLM.
2. **Q-B04 (model access):** gates the 120 `pending_ai_draft` crops in T-P3-02, and T-P7-01/02.
3. **Q-B03 (compute/privacy):** gates T-P3-09, T-P3-11 and T-P13-01.
4. **Registry vs. live corpus drift:** 96 present observations were never hashed. 72 failed with `PermissionError`.
   The other 24 are NFD-named files that failed with `FileNotFoundError` on Windows and are absent from the live
   macOS corpus in either Unicode form. The live corpus has 84,439 files against the registry's 83,880. Fixing this
   needs a rescan, which would rewrite the registry's root path from `D:\` to a macOS path, so it is an owner
   decision.
5. **macOS host gaps:** `config/sbr.toml` still uses Windows paths, `tools/check.ps1` needs PowerShell, and pandoc
   and pdflatex are not installed.

## 10. Current Development Phase

The phase is unchanged: P3 is in progress, and P4, P5 and P13 are partly started. Evidence for ADR-009 (PPTX path)
and ADR-010 (orientation handling) is deeper than before.

## 11. Recommended Next Steps

There is no dependency-ready task. The owner actions that unlock the most:
- **T-P3-03 layout review** unlocks T-P3-05 and T-P3-10.
- **T-P3-02 math review** unlocks T-P3-06.
- Once T-P3-05 and T-P3-06 are DONE, T-P3-09 becomes reachable, though it is also gated on Q-B03.
- **Q-B04** unlocks T-P7-02.

Smaller items:
- Decide whether to rescan the registry on macOS (blocker 4).
- Optional engineering follow-up for T-P3-08: re-run OSD on images rendered with the page's `/Rotate` applied, to
  separate real 180° pages from false positives.

## 12. Final Assessment

This batch improved spike evidence. It did not move the system closer to a working agent. Progress is bound by owner
review gates and two open policy questions, not by engineering capacity. Ten tasks could not honestly be done; three
real slices were.
