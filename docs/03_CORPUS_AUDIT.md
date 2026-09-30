# 03 — Corpus Audit (Phase 0, read-only)

> **SUPERSEDED FOR CURRENT STATE: see §0 below (T-P2-12, 2026-09-26) for the definitive, exact, registry-verified
> t3 numbers** — computed from the production registry after the full P2 pipeline (scan/hash/classify/
> sensitivity/dedup/archives/genre/courses/names) ran against the real corpus, plus one new exhaustive
> measurement (a real, unsampled unique-PDF page census). `37_T2_CORPUS_REAUDIT.md` (2026-09-24) is now itself
> a historical intermediate snapshot, same as t0/t1 below — it pre-dates the registry and used ad-hoc scripts
> over a moving corpus; §0 supersedes it for every number the registry can compute exactly.
> The rest of this document (t0/t1, §§1-8) is kept unchanged as the historical record except for these
> corrections (raw evidence in docs/37 §18):
> - The 34 hash errors were `Permission denied`, not moves. Of the 14 probe errors, 12 were moves and 2 were empty files.
> - The t0 unique-PDF census is **3,339 opened / 328,418 pages** (not 3,337 / 328,409).
> - "15.3% fully textless" uses the ≥80%-of-sampled-pages rule. "All sampled pages textless" gives 14.7%.
> - Of the 163.7 GB "redundant" bytes, only **57.3 GB were exact** (full hash). 106.5 GB were partial-hash **candidates**.
> - Thesis DOCX OMML equations: **422**, not 592. Exercise solution: 322, not 571 (the original counted `<m:oMathPara>` too).
> - t2 (final corpus): 85,913 files / 561.5 GB; 4,660 unique PDFs; 361,061 unique pages; stable over 45 min.

## 0. t3 registry-verified refresh (T-P2-12, 2026-09-26)

**Status:** Complete. **Method:** every number below is either a direct query against the production
`registry.sqlite` (after `sbr scan/hash/classify/sensitivity/dedup/archives/genre/courses/names` all ran
against `D:\MBI-BRAIN`, T-P2-01 through T-P2-13) or, for the one number the registry schema does not yet carry
(PDF page count), a new exhaustive read-only census (`tools/audit_pdf_pages_t3.py`) that opens every one of
the corpus's unique PDF blobs exactly once through `SourceFS` and reads its page count from pypdf — no
sampling, no estimation, no content decoded or rendered. Raw evidence: `reports/manifest.{md,csv}`,
`reports/mirrors.md` (both gitignored — real corpus paths, regenerable any time via `sbr report manifest`/
`sbr report mirrors`), `audit/phase0/t3/pdf_unique_pages_t3.jsonl` and
`audit/phase0/t3/pdf_page_census_t3_summary.json` (committed — no relpaths, blob-hash-keyed only).

**This confirms Q-B01's t3 baseline exactly**: 83,880 files, 558,752,407,625 bytes (558.75 GB) — matching
docs/38's post-quarantine figure byte-for-byte, closing the loop between "corpus frozen" and "registry sees
what was frozen".

| Metric | t3 (registry-exact) | t0/t1 (docs/03 §§1-4, estimated/sampled) |
|---|---|---|
| Files | 83,880 | 39,478 / 73,441 |
| Total bytes | 558,752,407,625 (558.75 GB) | 371.1 GB / 561.0 GB |
| Distinct content blobs | 34,814 | not measured (files only) |
| Unique bytes (deduplicated) | 241,215,454,323 (241.2 GB) | not measured |
| Duplicate groups (blobs with >1 present path) | 23,326 | 8,220 (exact-hash subset of a larger sampled set) |
| Redundant bytes | 247,197,488,524 (247.2 GB) | 163.7 GB total "redundant" (only 57.3 GB confirmed exact, per the correction above) |
| Unique PDF blobs | 4,665 | 3,566 unique PDF blobs at t0 (of 8,614 files) |
| **Total unique PDF pages (exhaustive census, this task)** | **360,844** (4,638 of 4,665 opened; 27 permanently password-encrypted, unopenable without the password) | 328,409 at t0 (3,337/3,339 opened, sampled-era); a **~450–550k extrapolation from t1 growth was the prior planning number and is now superseded — the real count is substantially lower** |
| Documents ≥200 pages | 534 docs = 273,919 pages (**75.9%** of all unique pages) | 501 docs = 264,189 pages (80%) at t0 |
| Documents ≤40 pages | 3,499 docs = 29,066 pages (8.1%) | 2,373 docs = 21,423 pages at t0 |
| Mojibake paths (T-P2-13) | 306, **100% repaired** (all in an ancestor folder name, not the leaf; none in the leaf after T-P2-13's own 14 leaf-level repairs) | 228 at t0 |
| Mirror-directory pairs (T-P2-07 methodology: exact-hash overlap ≥50% AND ≥5 shared blobs, both sides) | 44 pairs, 91.7 GB reclaimable | 128 pairs at t0 (≥90% shared, no absolute-count floor — not directly comparable; see below) |
| Course-mapping coverage (T-P2-11) | 14,978 / 17,759 knowledge-bearing blobs (84.3%) | not measured (no course map existed) |
| Genre-classified blobs (T-P2-10) | 2,035 of 17,759 (11.5%) | filename-only genre hits, not blob-deduplicated (§2) |

**The 75.9% figure is an independent cross-check, not a coincidence to explain away**: docs/37 §"t2 re-audit"
separately reported "75.9% in ≥200-page PDFs" from its own (pre-registry, ad-hoc-script) methodology. This
task's registry-based, exhaustive, hash-deduplicated census landing on the *same* figure to three significant
digits is strong independent corroboration that both measurements are sound.

**Mirror-pair count is lower than t0's 128 by design, not by regression**: t0 used a ≥90% shared-blob
threshold with no minimum absolute overlap, over an approximate (xxh3, partially sampled for large files)
hash. T-P2-07's methodology is deliberately different — a lower ≥50% overlap threshold (catching more genuine
partial mirrors) but a hard ≥5-shared-blob floor (rejecting a tiny folder that merely happens to share one or
two files with something huge), over the *exact* BLAKE3 identity T-P2-06's dedup already established. The
two counts measure related but not identical things; the real qualifying-pair list is in `reports/mirrors.md`
(T-P2-07), not reproduced here.

**Top-level organization (t3, exact — compare with §2's t0 table)**:

| Top-level | Files | Bytes |
|---|---|---|
| `Information` | 52,595 | 162,084,185,177 (162.1 GB) |
| `Mechanical` | 13,984 | 356,847,292,328 (356.8 GB) |
| `BachelorArbeit` | 15,269 | 24,094,313,421 (24.1 GB) |
| `books` | 1,604 | 10,455,218,970 (10.5 GB) |
| `Betriebslehre` | 315 | 5,146,229,117 (5.1 GB) |
| `Ckurs` | 108 | 73,335,002 |
| `English` | 3 | 51,282,987 |
| root files | 2 | 550,623 |

`Mechanical`'s byte share grew sharply relative to t0 (281.2 GB → 356.8 GB) — consistent with §1's t0→t1
observation that video-heavy areas (`Bewegungstechnik`, `messundsteuerungstechnik`) kept growing after t0.
`Information` similarly grew (54.4 GB → 162.1 GB), matching the t1 note that `Information\Informatikx` alone
added 107.7 GB between t0 and t1.

**Knowledge-class distribution (t3, by distinct blob, from `sbr report manifest`)**: media 1,001 blobs /
179.8 GB (still the dominant byte share, as at t0); document 5,012 / 19.6 GB; archive 408 / 29.0 GB; image
7,343 / 2.8 GB; office 460 / 3.7 GB; the remainder (third_party_reference, tool_artifact, code, data, unknown,
spreadsheet, executable, junk) together under 6 GB. Full breakdown: `reports/manifest.md` §"By knowledge
class"/"By format".

**Workload/wave-estimate consequence (docs/08 §4's wave table)**: that table's "Est. unique pages (t0)"
column was built from t0/t1 extrapolation before any real page count existed. With the true total now known
exactly (360,844, not the ~450–550k planning assumption), every wave's absolute page estimate in docs/08 §4
should be read as **an upper bound that will shrink**, not a target — W3 ("Textbooks and manuals", previously
"~260k+") in particular, since documents ≥200 pages (mostly ISBN-named textbooks, per §5.2 below) total
273,919 pages here, not "260k+" of an assumed ~450–550k. Recomputing docs/08 §4's table itself (which needs
the course map, T-P2-11, cross-referenced with genre, T-P2-10, to assign per-wave content precisely — course
coverage is 84.3%, not yet 100%) is left to whichever task next revisits wave sizing (T-P13-01 per Q-B01's own
"blocked-by" list), rather than guessed here beyond this note.

**Status:** Complete for snapshot t0; partial (metadata only) for snapshot t1
**Date:** 2026-09-24
**Method:** Read-only. `os.scandir`/`stat` inventory, xxh3-128 content hashing, PyMuPDF
read-only probing and page rendering to the project `audit/` directory. Nothing in
`D:\MBI-BRAIN` was modified, moved, renamed, converted or embedded.
**Artifacts:** `audit/phase0/` (see `audit/phase0/README.md`). Scripts are in `audit/phase0/scripts/`.

> **CRITICAL: the corpus changed during the audit.** The owner was still migrating material
> into `D:\MBI-BRAIN` while this audit ran. The statistics below describe two snapshots.
> The detailed analyses (hashing, duplicates, PDF probing, page counts) cover **t0 only**.
> Blocking question **Q-B01** asks for a "corpus frozen" signal. After the freeze, task
> **T-P2-12** re-runs the audit with the production scanner.

## 1. Snapshots

| Metric | t0 (≈11:55) | t1 (≈12:35) |
|---|---|---|
| Files | 39,478 | 73,441 |
| Total size | 371.1 GB (345.6 GiB) | 561.0 GB |
| Directories (containing files) | 5,951 | 10,559 |
| Max depth | 14 | — |
| PDF files | 8,614 | 13,552 |
| MP4 files | 899 (283 GB) | 1,595 (428 GB) |
| ZIP files | 367 (26.4 GB) | 755 (58.2 GB) |
| DOCX / DOC | 164 / 174 | 221 / 355 |
| PPTX / PPT / PPSX | 34 / 16 / 14 | 54 / 43 / 114 |
| Java source files | 2,592 | 7,180 |

New top-level areas added between t0 and t1: `Information\Informatikx` (29,375 files, 2,406 PDFs,
107.7 GB), `Betriebslehre\Managment` (290 files, 4.1 GB), `Mechanical\Automatisierungslabor`
(154 files, 3.7 GB), and new subfolders such as `Mechanical\Mathematik\Mathe` and
`Mechanical\konstruktonsgrundlagen\MAE_3`. About 675 t0 paths disappeared (moved or reorganized),
for example `Mechanical\regelungstechnik\Reg3\REg3\…` and `Mechanical\messundsteuerungstechnik\Messtechnik\…`.
The owner's 530 GB estimate matches t1.

**Architectural consequence:** the registry must treat paths as observations of content-addressed blobs.
It must detect moves cheaply and must never assume a static tree (ADR-003, T-P2-03).

## 2. Top-level organization (t0)

| Top-level | Files | Size | Notes |
|---|---|---|---|
| `Mechanical` | 11,962 | 281.2 GB | 21 subject folders; the video lectures account for most of the size |
| `Information` | 10,623 | 54.4 GB | CS courses, with heavy mirroring (`Vorlesung`, `vorvorl`, `Java_1`) |
| `BachelorArbeit` | 15,269 | 24.1 GB | Thesis, MATLAB code, Praxisphase, semester project, ROBWork |
| `books` | 1,604 | 10.5 GB | `PhyBo`, `Studium` (programming, numerics, web and other books) |
| `Betriebslehre` | 18 | 1.0 GB | Business administration |
| root files | 2 | — | `curriculum_mbi_ws2019.pdf`, `MBI-WS2019-Modulhandbuch.pdf` (module handbook, a valuable taxonomy seed) |

`Mechanical` subfolders: Bewegungstechnik (118.9 GB, mostly video), Dynamik (48.5 GB), Elektrotechnik,
FEM, Foerdertechnik, Kolbenmaschinen, Maschinendynamik, Mathematik (incl. NumMat), Modellbildung_technischer_Systeme,
Prozessleittechnik, Robotertechnik, Simulationstechnik, Statik, kinematik, konstruktonsgrundlagen,
messundsteuerungstechnik (54 GB, incl. labs), physik, regelungstechnik (1,298 PDFs), werkstoffkunde.
At t1 `Automatisierungslabor` was added.

### Observations on the human organization
- **It is useful but not a taxonomy.** Folder names are course abbreviations (`Reg1`, `RGT`, `MSR2`, `ModellbTSys`,
  `GrdInf`, `AlgDat`, `BS1`, `MO`, `KONleh`, `KonstGrd`, `WISs`, `SMS`, `IRO`). A curated
  **abbreviation→course mapping** is required (T-P2-11), seeded from the module handbook.
- **Subjects are cross-filed.** Examples: `Information\Vorlesung\KonstGrd` holds design fundamentals (mechanical);
  `Information\MO\Num` and `Optim` hold numerics and optimization; `regelungstechnik\Reg\RegelungsTec\Modellbildung_technischer_Systeme`
  duplicates the modelling course; `Bewegungstechnik\Bewe\Bewe\Dyn` duplicates `Dynamik`; `Bewegungstechnik\...\Scharmann\Mathematik` holds math exercises.
- **Internal naming conventions** carry genre signals: `kl`/`Kla`/`Klausuren` (exams), `Lösung`/`Musterlösung`/`Kurzlösungen`
  (solutions), `sk`/`Skript` (lecture script), `Übung`/`Aufgabenblatt`/`Uebungsblatt` (exercises), `Labor`/`Versuch` (lab), `TutLos`.
  Filename genre hits among t0 PDFs: exercise 1,707; exam 1,116; lecture/script 811; solution 796; lab 180.
- **Semester and date signals** appear in names (`SS2010`, `WS2014`, `_SS20`, `2021-09-22`), which enables version chains.
- **Other-university material exists** (e.g. `TU Clausthal` under GrundlagenInformatik). The source institution is metadata.

## 3. Format distribution (t0)

| Class | Extensions (count) | Size | Knowledge value |
|---|---|---|---|
| Documents | .pdf 8,614; .docx 164; .doc 174; .pptx 34; .ppt 16; .ppsx 14; .txt 734; .md ~0; .tex 0 | ~28.5 GB | **Primary** |
| Spreadsheets | .xlsx 449; .xls 129; .csv 26 | small | Secondary (lab data) |
| Video/audio | .mp4 899 (283 GB); .avi 107 (10.2 GB); .mkv 13 (5.4 GB); .m4v, .webm, .mov, .mp3 | ~300 GB | Deferred media track (ADR-030) |
| Images | .jpg 7,862; .png 3,721; .bmp 856; .gif 302; .jpeg 106 | ~5 GB | Mostly project/lab renders and photos. **~12.8k images remain** despite the manual cleanup |
| Code | .java 2,592; .m 1,869; .c 147; .h 195; .ino 79; .py 17; .sh 130 | small | Secondary (thesis MATLAB is valuable) |
| MATLAB data/figures | .mat 2,807; .fig 658; .slx 26; .mlapp 20 | 5.2 GB | Low; `.fig` can be rendered later |
| CAE/tool artifacts | ANSYS (.wbjn, .mechdb, .agdb, .rst, .wbpz …), Eclipse `.metadata` (1,049 files), `_ProjectScratch` (201), `slprj`, .class 1,404, .exml/.ctxt (BlueJ) | ~2 GB | Noise / exclude |
| Archives | .zip 367; .rar 30 | 27.8 GB | Containers. Only 110 of 397 have a same-name extracted sibling folder |
| Executables | .exe 73; .jar 38; .bat 35 (mostly ANSYS scratch) | 1 GB | Never execute; exclude |
| Junk | `__MACOSX`/`._*` 81; thumbs.db/.DS_Store/desktop.ini 43; zero-byte 171 | — | Exclude |
| No extension | 777 | 0.2 GB | Classify by magic bytes |

**File-name encoding:** filenames are proper Unicode (5,874 paths contain umlauts). 228 paths contain
**CP437 mojibake from ZIP extraction** (e.g. `Fl├ñche` = `Fläche`). Repair it for display only and never rename (T-P2-13).

## 4. Duplicates (t0, exact, content-hash based)

Method: xxh3-128 of every document-type file plus every file that shares its size with another file.
Files above 512 MB that are not documents (videos, large ZIPs) were hashed by head/middle/tail samples
(`mode=partial`, which is probabilistic). In total 33,734 files were hashed (103.5 GB read fully) in 1,222 s.
34 files errored because they were moved during the run.

| Result | Value |
|---|---|
| Duplicate groups | 8,220 |
| Redundant copies | 18,732 files, **163.7 GB** |
| PDF files → unique PDF blobs | **8,614 → 3,566** (58.6% of PDF files are redundant); unique PDF bytes 17.5 GB |
| DOCX / PPTX / DOC / PPT | 164→138, 34→27, 174→140, 16→9 unique |
| Videos | 1,041 files → ~617 unique, ~165 GB unique |
| Largest redundancy by bytes | mp4 127 GB, zip 14 GB, pdf 9.6 GB |
| Duplicate groups spanning >1 top-level folder | 253 |
| Mirrored directory pairs (≥90% shared blobs, maximal) | **128** |

Examples of mirrored directories: `Information\Vorlesung\AlgDat` = `Information\Java_1\AlgDat` = `Information\vorvorl\AlgDat`;
`Information\Vorlesung\GrdInf` ≈ `Information\vorvorl\GrdInf` ≈ `Information\C\AlteDaten\GrundlagenInformatik`;
`Modellbildung_technischer_Systeme\ModellbTSys` = `ModellbTSys_1`; `messundsteuerungstechnik\Messt` ≈ `Messtechnik`;
`regelungstechnik\Reg1` = `Reg\1\Reg1`; `BachelorArbeit\MatlabBachelorArbeit\APP_Antriebs` ≈ `BachelorArbeit\Matlab\Bachelorarbeit\Prog`.
Full lists: `audit/phase0/dup_groups.json`.

**Not yet measured:** near-duplicates such as re-saved PDFs, revised lecture versions, the same script with and without solutions,
and **annotated copies** (see §6). This requires normalized text and is task T-P5-03.

## 5. PDF characteristics

### 5.1 Stratified probe (t0)
1,702 PDFs were sampled (up to 12 per level-3 folder), with up to 25 pages inspected each. Raw data: `audit/phase0/pdf_probe.jsonl`.

| Signal | Result |
|---|---|
| Open errors / encrypted | 14 (moved during run) / 0 |
| Page count p10/25/50/75/90/99/max | 1 / 2 / 8 / 37 / 142 / 816 / 2,281 |
| **Fully textless ("scanned-like")** | **15.3%** of documents; 1.7% partially textless |
| Documents using math fonts | **53.9%** |
| Landscape (slide-like) | 29.8% |
| With PDF bookmarks/TOC | 303 of 1,688 (18%) |
| With a title in metadata / author | 874 (52%) / 1,044 (62%). Titles are often junk ("Microsoft Word - …") |
| Documents with PDF annotations | 182 (10.8%) |
| Average embedded images per page | 3.7. Median vector drawing ops per page ≈ 10.5 (diagrams are often vector) |

Producer classes: other/unknown 440, **LaTeX 378**, **Word 281**, **PowerPoint 269**, publisher pipelines 179,
no metadata 53, scanner/OCR 34, LibreOffice 23, handwriting apps 23.
Math-font documents by producer: LaTeX 279, **Word 175**, **PowerPoint 162**, publisher 110.
Frequent math fonts: Symbol/SymbolMT, **CambriaMath** (Office equations), CMSY/CMMI/CMR/CMEX/MSAM (LaTeX), **MTExtra** (MathType).

Scanned share by area (probe): Robotertechnik 32%, Statik 32%, Regelungstechnik 29%, Mathematik 24%,
Modellbildung 24%, konstruktonsgrundlagen 38%, BachelorArbeit\MatlabBachelorArbeit 32%, Dynamik 38%.
Math share is highest in Informatik courses (76–91%, which includes Symbol-font bullets and is therefore **inflated**),
Elektrotechnik 74%, physik 74%, FEM 72% and messundsteuerungstechnik 69%.

> The owner's assumption that "~99% of PDFs contain searchable text" does **not** hold for this corpus.
> About 15% of documents in the sample, and an estimated **~26k of ~328k unique pages**, have no usable text layer.

### 5.2 Unique-blob page census (t0)
Every unique PDF blob was opened for page count, with 5 probe pages each. Data: `audit/phase0/pdf_unique_pages.jsonl`.

| Metric | Value |
|---|---|
| Unique PDFs opened | 3,337 (217 had been moved between hashing and census) |
| **Total unique pages** | **328,409** |
| Estimated textless pages | ~25,700 |
| Estimated pages carrying math fonts | ~65,700 (upper bound; Symbol-font bullets inflate it) |
| Documents ≥ 200 pages | 501 documents = **264,189 pages (80%)**. These are mostly ISBN-named Springer textbooks (`978-3-…pdf`) and manuals (LS-DYNA 2,281 p) |
| Documents ≤ 40 pages | 2,373 documents = only **21,423 pages**. These are lecture scripts, slides, exercises and exams: **the most personal course knowledge** |

At t1, PDFs grew from 8,614 to 13,552 files. Assuming a similar duplicate ratio, the unique-page total is
roughly **450–550k pages**. That figure is an estimate and must be confirmed by T-P2-12.

## 6. Representative document study

Rendered pages and text-layer dumps are in `audit/phase0/samples/`. The findings:

| Sample | Producer / type | Text layer | Math in text layer | Verdict |
|---|---|---|---|---|
| **Bachelor thesis** `BachelorArbeit\…\BA\Bachelorarbeit.pdf` (73 p), p.22 | Word (Cambria Math) | Good prose | Symbols present (Unicode math italic `𝑭`, `𝝎̃`) but **structure destroyed**: fractions, matrices, sub/superscript order and sums are flattened and interleaved | Unusable for math without reconstruction |
| **Thesis DOCX twins** `Bachelorarbeit.docx` (+ `BachelorarbeitCopy`, `Bachelorarbeit1`, parent-folder copy) | Word | — | **592 native OMML equations**, exactly convertible to LaTeX | **The best math source. Prefer it to PDF recognition** |
| Maschinendynamik 1 script (130 p), p.48 | Word + MathType (Symbol/MTExtra) | Good prose | **Catastrophic:** one glyph per line, unrecoverable order | Requires visual formula recognition |
| Same page, rendered | — | — | Shows the **owner's handwritten red-ink annotations** (derivation notes) | Annotated copy = user knowledge |
| Modellbildung technischer Systeme (98 p), p.34 | MathType | Prose OK | Broken | Also contains **formula tables** and **plots with captions** ("Bild 2.17") |
| Regelungstechnik H2 (8 p) | MathType | Prose OK | Broken (`)\n(\nj\n)…`) | Visual recognition needed |
| FEM-Grundlagen (75 p), p.37 | MathType | — | Matrix brackets as glyph soup | Visual recognition needed |
| NumMath5 (426 p, LaTeX book) | LaTeX | Good | Linearized: `x2+y2 / |xy|`, `Rn`. Simple inline math is readable; display math loses structure | Upgrade for display math |
| DH-transformation exercise (robotics) | Word | Good | Matrices flattened row-by-row (`cosi −sin i 0 0 …`) | Visual or twin recovery |
| AlgDat lecture slides (CS) | PowerPoint | Good | Simple inline math (`𝑏1 ≤𝑏2 ≤⋯`) acceptable | Text tier sufficient |
| Statik tutorial `tut\1\Kap 6.pdf` | Scanned typewriter (FH Hannover) | **None** | — | OCR required. **Diagrams (trusses) are essential**: the computations refer to them |

Additional findings:
- **DOCX/PPTX with OMML equations:** 32 of 161 DOCX, 18 of 34 PPTX, 1 PPSX. Thesis, Praxisphase report (499 equations),
  Kinematik/Gleichungen notes and exercise solutions (571). These are among the **owner's own authored documents**.
- The owner's own documents (thesis, Praxisphase report, semester project `AmmarSayyadiMBIProjekt.docx`,
  `Excitation_Trajectories_KR6_Robot.docx`) coexist with their **MATLAB implementations**
  (`BachelorArbeit\Matlab*`, 13.8 GB, inner forces/optimization/drives). Equations and code can be linked.
- **Sensitive material exists:** lab grade lists (`Labornoten`, `Ergebnislisten` with other students' results), contracts
  (`Praxisphase\Vertrag`), personal names. A sensitivity gate is required (ADR-035).
- **The textbook share is large and mostly ISBN-named.** The ISBN in the filename is source-provided metadata; no external lookup is needed.
- Section numbering (`3.2`, `(3-114)`, `(2.62)`, `Bild 2.17`, `Tabelle 2.7`) is consistent within documents. It enables
  equation/figure/table labels and cross-references.
- Only 18% of PDFs have bookmarks, so the structure must usually be inferred from typography and numbering.

## 7. Hardware constraints (verified)

| Item | Value |
|---|---|
| CPU | Intel Core 7 150U (10 cores / 12 threads, mobile U-series) |
| RAM | 63.7 GB |
| GPU | Intel integrated graphics only. **No CUDA GPU** |
| Storage | Single 2 TB NVMe SSD (Patriot P400L). D: 977 GB, **377 GB free at t0** (less after t1 growth). C: 714 GB free |
| Python | System 3.14.7 (too new for much of the ML stack; pin 3.12 per ADR-005) |

**Consequence:** GPU-class document VLMs (MinerU2.5-VLM, PaddleOCR-VL, olmOCR, dots.ocr) run at roughly 30+ s/page on CPU.
Full visual parsing of ~330–550k pages locally would take **thousands of hours**. This drives ADR-007: tiered triage,
value-prioritized waves, lazy upgrade and optional external compute (Q-B03).

## 8. Summary of challenges

1. **Math extraction:** text layers corrupt math for Word, MathType and even LaTeX display math. Visual recognition or Office twins are required.
2. **Scale vs compute:** there is no GPU, and 80% of pages are textbooks.
3. **15% scanned documents**, including older typewriter scripts whose diagrams are essential.
4. **Massive exact duplication** (58.6% of PDFs; 128 mirrored folders). Near-duplicates and versions are unmeasured.
5. **Annotated copies** hold the owner's handwritten knowledge, so naive dedup would destroy it.
6. **The corpus is a moving target** during migration.
7. **Heterogeneous non-document material** (videos 76% of bytes, code, CAE scratch, archives, images).
8. **Sensitive personal and third-party data** is mixed into course folders.
9. **Bilingual (mostly German) technical vocabulary** and heavy abbreviation.
10. **Weak metadata:** junk PDF titles and few bookmarks.
