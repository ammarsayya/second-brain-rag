# 37 — T2 Corpus Re-audit and Phase-0 Reconciliation

**Date:** 2026-09-24 (t2 inventory 14:04:04; stability snapshots 14:21:33 and 14:49:27)
**Status:** Complete. Read-only toward `D:\MBI-BRAIN`. Artifacts are in `audit/phase0/t2/` (index: `audit/phase0/t2/README.md`).
**Scope labels:** **[FULL]** measured on the whole T2 corpus (or on the whole class stated) · **[SAMPLE]** measured on a sample ·
**[EXTRAP]** extrapolated from samples · **[HIST]** historical t0/t1 evidence.
**Audit hash:** xxh3-128 (not the planned production BLAKE3-256 id). "Exact" means a full-file hash match. "Candidate" means a partial-hash match, which is probabilistic.

## 1. Executive summary

- **The corpus is stable.** Three inventories over 45 minutes were identical: 0 added, 0 removed, 0 changed [FULL]. The migration is no longer in progress. **Recommended resolution of Q-B01: close.** Owner confirmation is still required.
- **T2 CURRENT CORPUS: 85,913 files, 561.50 GB, 10,606 directories** [FULL]. Size is almost identical to t1 (561.05 GB). The +12,472 files are almost entirely one extracted man-page archive.
- **The "reorganization" did not move t1 content.** t1→t2 removed 0 paths and changed 3 (mtime only; content identical by hash) [FULL]. All 675 paths that disappeared t0→t1 have exact content elsewhere in t2, so **no content was lost since t0** [FULL].
- **Genuinely new content since t1 is small:** 152 files / 136 unique contents / 0.19 GB (root `Ckurs`, `English`, 7 Betriebslehre QM decks, some SAB/Regelungstechnik PDFs, C sources) [FULL].
  **Never deeply audited since t0:** 16,090 files present at t1 (C), plus the 152 new ones (D). This includes **1,320 unique PDFs = 32,643 pages** that were never page-censused [FULL].
- **PDF baseline:** 13,695 PDF paths → **4,660 unique PDFs, 361,061 unique pages** [FULL]. 1 empty file, **13 password-protected**, 2 zero-page, 0 corrupt-unopenable. Textless (all probe pages): **17.7%** of unique PDFs [FULL doc count; SAMPLE pages within docs].
- **Duplicates:** **23,512 exact groups, 50,756 redundant paths, 99.0 GB exact redundancy** [FULL]. There are 27 further large-file groups (196.8 GB) that are **candidates only** (partial hash).
- **Cleanup claims measured:** images **13,766, unchanged since t1**. Archives **812, unchanged since t1** (755 ZIP + 57 RAR, 59.6 GB). 360 ZIPs are fully extracted (redundant containers); **342 ZIPs (16,102 members) are not extracted anywhere** [FULL, name+size match].
- **HTML: 24,516 files, 99.8% Linux man-pages** in two identical trees plus a zip copy (12,246 unique contents). This is third-party generated reference documentation, not course knowledge [FULL].
- **Office math reproduced with a saved census:** 49 unique OOXML files carry **3,260 native OMML equations**. **Correction:** the thesis has **422** equations, not 592. 70 unique legacy `.doc` files carry Equation Editor 3.0 objects, an equation source not covered by the original OMML-first scope [FULL].
- **The architecture holds.** No structural change is needed. Six precise gaps get scoped plan updates (§22): third-party reference HTML, legacy equation objects, password-protected PDFs, presentation build-step pages, archive-only content, and identity documents.
- **Phase 0 is ready for owner review.** No implementation was started, and T-P0-08 and Q-B05 remain open.

## 2. Why t2 was required

The corpus changed from 39,478 files / 371.1 GB (t0) to 73,441 / 561.0 GB (t1) during the original audit, and only t0 was audited in depth [HIST].
The owner then finished reorganizing. The independent forensic review (`CODEX_AUDIT_HANDOFF.md`) also found reporting discrepancies. t2 establishes the authoritative baseline and corrects the record.

## 3. Snapshot comparison t0 → t1 → t2

| Snapshot | Files | Bytes | Evidence depth |
|---|---|---|---|
| t0 (≈11:55) | 39,478 | 371,092,983,180 | [HIST] full inventory, hashes (docs + size collisions), PDF probe, page census |
| t1 (≈12:35) | 73,441 | 561,049,965,168 | [HIST] metadata only |
| **t2 (14:04)** | **85,913** | **561,502,988,849** | [FULL] inventory, hashes, identity, PDF census, Office, HTML, archives |

| Transition | Added | Removed | Unchanged paths | Size/mtime changed | Added bytes | Removed bytes |
|---|---|---|---|---|---|---|
| t0→t1 | 34,638 | 675 | 38,803 | 0 | 190.76 GB | 0.80 GB |
| **t1→t2** | **12,472** | **0** | **73,441** | **3** (same size, new mtime; content identical) | **0.45 GB** | 0 |
| t0→t2 | 47,110 | 675 | 38,803 | 2 | 191.21 GB | 0.80 GB |

**t1→t2 additions:** `Information\C\man-pages` 12,240 (HTML); `Ckurs` 108 (new root); `English` 3 (new root); 7 `Betriebslehre\QM_*.pptx`; `SAB_Teil2_neu` and `SAB_Teil2_neu_1` (17+17);
`regelungstechnik\Alte_Klausuren_2020` 11; small C code folders; extensions: .html 12,239, .pdf 143, .h 29, .c 23, .pptx 7, .ino 6.
**t0→t1 additions [HIST, identities now resolved]:** `Information\Informatikx` (29,375 files, 107.7 GB), `Mechanical\konstruktonsgrundlagen\MAE_3`, `Mechanical\Mathematik\Mathe`, `Betriebslehre\Managment`, `Mechanical\Automatisierungslabor`, among others.
**Removed t0 paths (675):** all 675 have exact-hash content elsewhere in t2 [FULL]. Examples: `regelungstechnik\Reg2` → `Reg22`, `Reg3` → `Reg33`, `messundsteuerungstechnik\Messtechnik` → `Messtechnik1`.

## 4. Current t2 corpus statistics [FULL]

| Metric | Value |
|---|---|
| Files / bytes / dirs with files beneath / max depth | 85,913 / 561.50 GB / 10,606 / 14 |
| Zero-byte files | 241 |
| AppleDouble/`__MACOSX` · OS junk (thumbs.db etc.) | 81 · 53 |
| CP437 mojibake paths | 306 (228 at t0) |
| Paths unreadable (Permission denied on read) | 42 (34 at t0, same class: ACL-restricted files, not moves) |

**Top-level:** Mechanical 15,346 / 358.87 GB · Information 53,266 / 162.82 GB · BachelorArbeit 15,269 / 24.09 GB · books 1,604 / 10.46 GB ·
Betriebslehre 315 / 5.15 GB · Ckurs 108 / 0.07 GB · English 3 / 0.05 GB · 2 root PDFs (curriculum, module handbook).

**Extensions by count:** .html 24,516 · .pdf 13,695 · .jpg 8,009 · .java 7,180 · .png 3,942 · .class 3,930 · .mat 2,807 · .exml 2,807 · .m 1,869 · (none) 1,665 ·
.mp4 1,595 · .txt 1,524 · .ctxt 1,508 · .bmp 1,128 · .zip 755 · .fig 658 · .gif 558 · .xlsx 457 · .doc 355 · .docx 221 · .ppsx 114 · .pptx 61 · .rar 57 · .ppt 43.
**By bytes:** .mp4 428.18 GB · .zip 58.23 GB · .pdf 34.34 GB · .avi 10.23 GB · .mkv 5.38 GB · .ppsx 4.77 GB · .fig 2.79 GB · .jpg 2.47 GB · .mat 2.42 GB.
**Largest directories:** see `stats_t2.json` (`largest_dirs_depth1to4`). Mechanical\Bewegungstechnik (119.1 GB) and Information\Informatikx (107.7 GB) are dominated by video.

## 5. Current directory organization

The new root layout (7 top-level areas + 2 curriculum PDFs) is **cleaner at the root**: `Ckurs` and `English` are separated, and `Betriebslehre` collects management material.
Inside the subject trees, **little changed** [FULL]:
- **Mirrors persist:** 488 maximal mirror pairs (≥90% shared exact blobs both ways). The biggest are `Information\C\man-pages` ≡ `Informatikx\1\Sys.prog2\man-pages` (12,240);
  `Information\vorvorl` ≡ `Informatikx\vorvorl` ≡ `Informatikx\1\vorvorl` (3,741 shared); the SoftEng variants (`SoftEng2`, `Softeng`, `vorvorl\SoftEnge`, `…\SoftEng`: 583); `Informatikx\Programmieren` ≡ `Information\MO` (530);
  `Messt` ≡ `Messtechnik1` (463); and BachelorArbeit `APP_Antriebs` ≡ `Matlab\Bachelorarbeit\Prog` (1,188).
- **Abbreviations persist** (`Reg22`, `Reg33`, `MSR2`, `MAE_3`, `GrdInf`, `AlOp`, `KONleh`, `WISs`, `SMS`). Spellings `konstruktonsgrundlagen`, `Managment`, `Vorleungsfolien`, `Thrrads9` are source spellings and are kept as metadata.
- **Cross-filing persists:** CS material under `Mechanical\Mathematik\...\Arduino`; `Informatikx` holds numerics (`NumMath`); `Information\MO` holds numerics and optimization.
- The **module handbook and curriculum PDFs are present at the root** and remain the canonical taxonomy seed. The folder tree is useful metadata and should not become the taxonomy (unchanged position, ADR-001 and 12).

## 6. New content since t0 (identity categories) [FULL]

Classification per file by path, size, mtime and xxh3 (`identity_t2.csv`; method in the script docstring):

| Category | Meaning | Files | Bytes | Unique contents (full hash) |
|---|---|---|---|---|
| **A** | Path unchanged since t0: covered by the t0 audit | 38,801 | 370.29 GB | — |
| **B (exact)** | New path, content already present (t0-hashed or t1-era) | 30,870 | 27.39 GB | 17,445 |
| B (probable) | Same name, size and mtime only | 0 | 0 | — |
| **C** | Appeared at t1, never deeply audited | 16,090 | 163.63 GB | 14,140 (plus unhashed unique-size files) |
| **D** | Genuinely new after t1 (provably: new size or new hash) | **152** | 0.19 GB | **136** |
| **E** | Identity uncertain | **0** | 0 | 0 |

C by extension: .html 12,240 · .pdf 1,496 · .mp4 559 · .class 344 · .java 259 · .zip 169 · .ppsx 86. Mainly `Informatikx\1`, `MAE_3`, `Mathematik\Mathe`, `Betriebslehre\Managment`.
D by extension: .pdf 115 · .h 17 · .pptx 7 · .ino 6 · .c 4. Mainly `Ckurs` 108, `SAB_Teil2_neu*` 22, `Betriebslehre\QM_*` 7, `English` 2, and single PDFs (a Diplom thesis, physics reports, `Numerik.pdf`).

## 7. New content since t1

Only **D = 152 files (136 unique contents, 187 MB)** is new content. The other 12,320 new paths since t1 are **exact copies** of content that already existed
(12,240 man-page files plus the SAB/Regelungstechnik copies). `Ckurs` (root) is new content. It is *not* a copy of `Informatikx\Ckurs` [FULL].

## 8. Moved/renamed vs genuinely new

- **Moved/renamed or copied (B_exact): 30,870 files.** All 675 vanished t0 paths reappear by exact content [FULL].
- **Genuinely new vs t0: C + D = 16,242 files.** Only 152 of these are new since t1.
- **Uncertain (E): 0.** Every new-path file was either hash-matched or provably new by size.

## 9. PDF findings

| Metric | Value | Scope |
|---|---|---|
| PDF paths | 13,695 | FULL |
| AppleDouble `._*.pdf` (excluded) | 33 | FULL |
| PDF paths unreadable (Permission denied) | 6 | FULL |
| **Content-unique PDFs** | **4,660** (+11 AppleDouble uniques excluded) | FULL |
| Duplicate PDF paths (exact) | 8,996 redundant non-AppleDouble paths (65.9%); 2,227 exact PDF groups, 14.74 GB redundant (groups include AppleDouble files) | FULL |
| Opened / open errors | 4,659 / 1 (empty file) | FULL |
| Password-protected | 13 (12 Betriebslehre QualMan lectures, 1 language exam). Page count readable, content not | FULL |
| Zero-page (unreadable structure) | 2 | FULL |
| Corrupt (cannot open) | 0 | FULL |
| **Total unique pages** | **361,061** | FULL |
| Representative-path fallback needed | 0 (the mechanism was used and not needed; t2 is stable) | FULL |
| Pages p10/25/50/75/90/99/max | 1 / 2 / 7 / 39 / 250 / 919 / 2,281 | FULL |
| Docs ≥200 pages | 534 docs, 273,919 pages (75.9%) | FULL |
| Docs ≤40 pages | 3,520 docs, 29,438 pages | FULL |
| All 5 probe pages textless | 820 docs (17.7%). t0 census, same definition: 14.4% | FULL docs / SAMPLE pages |
| ≥80% of probe pages textless | 846 (18.2%) | same |
| Any probe page textless | 1,229 (26.5%) | same |
| Estimated textless pages | ~27,300 | EXTRAP |
| Docs with math fonts on any probe page | 2,128 (45.8%; t0: 43.8%). Upper bound, because Symbol bullets also match | FULL docs / SAMPLE pages |
| Estimated math-font pages | ~81,800 (upper bound) | EXTRAP |
| Docs with PDF annotation objects on probe pages | 310 (6.7%) | SAMPLE (5 pages/doc) |
| Landscape (slide-like) first page | 1,442 (31.0%) | FULL |
| **Unique PDFs never censused at t0** | **1,320 PDFs / 32,643 pages** | FULL |
| Unique PDFs deep-probed (25 pages) at t0 | 1,388 | HIST |
| New-content deep probe | 293 PDFs (stratified); all-textless 128 (43.7%, dominated by the 108 image-only `Ckurs` PDFs); math fonts 84; annotations 16 | SAMPLE |

**Presentation build steps (new characteristic).** Some slide PDFs export every animation step as a page. For example, Math 1 `Vorlesung_14_Matrizen…Praesentation.pdf` has 332 pages, and its pages 37–46 are one slide growing by a few characters each.
Of 1,442 landscape unique PDFs, **65 docs (9,336 pages) have ≥30% build-step pages** in their first 25 pages [FULL for slide-like PDFs]. The estimated total is ~8,800 build-step pages (~2.4% of unique pages) [EXTRAP].

## 10. Math / OMML findings [FULL, `office_census_t2*.json*`]

| Office type | Unique contents | With OMML | OMML equations (`<m:oMath>`) | Display groups (`<m:oMathPara>`) | Other equation objects |
|---|---|---|---|---|---|
| DOCX | 158 (3 corrupt) | 31 | 2,597 | 934 | 2 files with Equation 3.0 OLE (17 objects) |
| PPTX | 35 | 13 | 489 | 234 | — |
| PPSX | 53 | 5 | 174 | 111 | — |
| XLSX | 358 | 0 | 0 | — | — |
| DOC (legacy) | 141 | n/a | n/a | n/a | **70 files with Equation 3.0 signature**, 7 with MathType signature |
| PPT / PPS | 9 / 1 | n/a | n/a | n/a | 1 / 1 with MathType signature |

- **49 unique OOXML files, 3,260 native equations.** Distribution: 7 files with ≥100, 15 with 20–99, 27 with 1–19.
- Top: thesis variants (`BachelorarbeitCopy` 432, `Bachelorarbeit` in the parent folder 424, `BA\Bachelorarbeit` 422, `Bachelorarbeit1` 419), `Praxisphase.docx` 388, `Übung11_lösung.pptx` 322, `Kinematik.docx` 100,
  `Gleichungen.docx` 67, `SS-2019_Kinematik_Kap2_1_V2.ppsx` 65, `Symbolverzeichnis.docx` 50.
- **Correction:** the original "592 equations in the thesis" and "571 in the exercise solution" counted `<m:oMath` as a substring. That also matched `<m:oMathPara` and `<m:oMathParaPr>`. The correct values are 422 and 322.
- **New:** legacy Word files with **Equation Editor 3.0** objects (MTEF payloads) concentrate in `physik\KLa` exams, `Mathematik\Math 3`, Informatik exercises and Messtechnik.
  These are also native (non-image) equations. The original ADR-009 OMML-first scope did not mention them.
- **PDF math:** see §9 (45.8% of unique PDFs carry math fonts). The t0 rendered samples showing broken text-layer math are unchanged and still valid (§17).

## 11. OCR / scanned-content findings

- Textless unique PDFs rose from 14.4% (t0 census) to 17.7% (t2) on the same definition [FULL docs]. About 27k textless pages [EXTRAP].
- **New textless classes:** `Ckurs` (108 PDFs, image-only **photos or screen captures of an English third-party online course**, "LearnProgramming academy") and `Gescannt_*` scans.
  The new-content sample also shows scanned Regelungstechnik and Elektrotechnik material [SAMPLE].
- **English content** is now clearly present: `English` (Market Leader textbooks, 2 new plus 1 copy), Ckurs, and many vendor manuals (Wonderware, CoDeSys, NI). The language share was **not measured** (UNKNOWN).

## 12. Figures and annotations

- PDF annotation objects on probe pages: 310 unique PDFs (6.7%) [SAMPLE within docs]. The handwritten-ink example (dynamics script) still exists at the same path [FULL].
- New samples confirm **math embedded in diagrams** (Festigkeitslehre: force decomposition with F·sin φ, A_φ = A / cos φ) and slide-heavy courses [SAMPLE]. The existing figure/math tier design (11, 10) already covers this.
- Images: 13,766 files / 5.6 GB, **identical to t1** (t0: 12,847) [FULL]. No image removal happened between t1 and t2.

## 13. Duplicate findings [FULL, `dedup_t2_summary.json`]

| | Groups | Redundant paths | Redundant bytes |
|---|---|---|---|
| **Exact** (full xxh3 match) | 23,512 | 50,756 | **99.03 GB** |
| **Candidates** (partial hash, >512 MiB non-documents) | 27 | 49 | 196.83 GB (**not proven**) |

Exact redundancy by type: .mp4 65.1 GB · .pdf 14.7 GB · .avi 4.5 GB · .mkv 2.7 GB · .ppsx 2.5 GB · .zip 2.0 GB · .mat 1.2 GB · .bmp 1.1 GB · .jpg 1.1 GB.
Unique-to-path ratios: PDF 13,689→4,671; DOCX 221→158; DOC 355→141; PPTX 61→35; PPT 43→9; PPSX 114→53; XLSX 457→358; HTML 24,516→12,246.
**Video:** 1,749 files / 445.4 GB → ~1,019 unique objects / ~204.1 GB (exact where fully hashed; probabilistic for partial; provably unique by size otherwise) [FULL].

## 14. Archives [FULL, `archive_census_t2.jsonl`]

- **812 archives remain (755 ZIP, 57 RAR; 59.6 GB), identical to t1.** Archive binaries were **retained**, not removed. 228 have a same-stem sibling directory.
- By ZIP members (name + size present anywhere in t2): **360 ZIPs fully extracted** (49.6 GB compressed, 7,811 members). These are redundant containers.
  **52 partially extracted** (13,783 members). **342 ZIPs with no member present** (7.3 GB, 16,102 members). Examples: `Vorlesungsfolien im Präsentationsmodus` (22 PDFs, Math 2), `mathe.zip`,
  a Grammatik book, `hf_java.zip`, ABB Freelance tutorials (4 copies), an Android video course. 265 nested archives exist.
- Archive duplication remains: ZIP exact redundancy is 412 paths / 2.0 GB.
- The corpus did **not** grow from extraction between t1 and t2 (+0.45 GB only). The man-page extraction (`offlineManpagesHtml.zip` → 12,638 of 12,657 members present) is the visible case.
- RAR membership was not inspected (no RAR reader in the audit environment): UNKNOWN.

## 15. HTML findings [FULL, `html_census_t2.jsonl`]

24,516 `.html` files (t1: ~12,277; t0: ~12). Classification by generator markers and titles:
**man-page HTML 22,338 + man-page license stubs ~2,140 (99.8%)**, Javadoc 30, Eclipse help 7. They form **two identical trees** (`Informatikx\1\Sys.prog2\man-pages` ≡ `Information\C\man-pages`) plus the source ZIP.
Unique contents: 12,246.
**Verdict:** generated **third-party reference documentation** (the Linux man-pages project). It's relevant as a reference for the systems-programming course, but it isn't owner or lecture knowledge.
Indexed naively it would dominate lexical retrieval (12k near-template pages). Policy is needed: see §22 and ADR-038.

## 16. Code / data / media findings [FULL]

- Code: .java 7,180 · .class 3,930 · BlueJ .exml 2,807 / .ctxt 1,508 / .bluej 314 · .m 1,869 · .c 344 · .h 239 · .sh 303 · .ino 85 · .py 22. The Eclipse `.metadata` noise grew to 2,561 paths; `\bin\` 2,186.
- MATLAB data: .mat 2,807, .fig 658 (unchanged).
- Media: .mp4 1,595 (428.18 GB), .avi 107, .mkv 13, .wmv 12, .m4v 15, .webm 3, .mov 4, .mp3 22. About 204 GB unique.
- The architecture already covers these as registered but deferred tracks (ADR-030 media, ADR-036 code). No change is needed.

## 17. Sample findings

**Old Phase-0 samples** (`samples/old_sample_recheck_t2.csv`): **all 12 are SAME PATH with identical content** (thesis PDF and DOCX, dynamics, modelling, control H2,
FEM, numerics book, robotics DH, AlgDat, control exam, scanned Statik). Their extraction observations remain valid for t2.
The t0 "scanned_exam" sample was never produced because of a script bug (a raw-string `\u00f6` escape). The file existed all along and exists now (19 copies).
**New samples** (`samples/`): Ckurs Mutex (image-only English course slide), Math 1 build-step deck (p.41), Festigkeitslehre (diagram with embedded math),
BWL Skript (text layer OK), English Market Leader (text layer OK), Ckurs scan (image-only).

## 18. Corrections to the original Phase-0 report (`03_CORPUS_AUDIT.md`)

| Original statement | Correction (raw evidence) |
|---|---|
| "34 files errored (moved during run)" | The 34 hash errors were **`Permission denied`**. All 34 paths still exist at t1 and t2. They are ACL-restricted files, not moves. At t2: 42 such files |
| "14 probe errors (moved)" | 12 were `no such file` (moved) and 2 were empty files |
| "3,337 opened unique PDFs, 328,409 pages" | Raw: **3,339 opened, 328,418 pages**. The summary silently dropped a 0-page LS-DYNA manual and a 9-page PDF that failed after its page count was read |
| "15.3% fully textless" | 15.3% = ≥80% of sampled pages textless. With "all sampled pages textless" it is 14.7%. Both definitions are now stated |
| "163.7 GB redundant copies" (t0) | Only **57.3 GB was exact** (8,198 groups, 18,705 files). 106.5 GB rested on **22 partial-hash groups (probabilistic)** |
| "Thesis DOCX: 592 OMML equations; exercise solution 571" | **422** and **322** `<m:oMath>` equations (the original counted `<m:oMathPara>` too). Now backed by a saved census |
| "OMML in 32/161 DOCX, 18/34 PPTX" | t2 unique contents: 31/158 DOCX, 13/35 PPTX, 5/53 PPSX (path counts at t2: 32/218 DOCX, 26/61 PPTX, 7/114 PPSX) |
| "The owner removed pictures / extracted ZIPs" (implied cleanup in t2) | Images and archives are **unchanged since t1**. 342 ZIPs remain unextracted anywhere |
| t1 "HTML" not discussed | 24,516 HTML files at t2, 99.8% man-pages (§15) |
| The audit venv reproduces the audit | It did not (xxhash was missing). It does now: `audit/phase0/t2/requirements-audit-venv.txt` |
| Scanned-exam sample "missing" | Script bug; the file exists |

## 19. Findings that remain valid

**CONFIRMED FOR t2:** read-only corpus; content-identity architecture needed (paths moved, content preserved); heavy exact duplication; mirrored course trees;
filename mojibake (306 paths); sensitive material present; math-bearing PDFs are about half; textless PDFs are a substantial minority; long textbook tail dominates pages (75.9% in ≥200-page PDFs);
video dominates bytes (445 GB of 561 GB); CPU-only hardware (not re-probed; no change reported).
**STILL VALID AS CONTENT CHARACTERISTICS:** broken text-layer math (Word, MathType, LaTeX display math); owner annotations in sources; diagrams on scanned pages; OMML twins of owner documents
(all old samples unchanged).

## 20. Findings that became stale

**HISTORICAL t0 ONLY:** t0 totals (39,478 / 371.1 GB), t0 duplicate groups (8,220), t0 page census (328,418 raw pages), 128 mirror pairs.
**STALE:** "~450–550k unique pages at t1" (EXTRAP) is superseded by **361,061 measured**. "58.6% PDF duplication" is now **65.9%** of PDF paths redundant (8,996 of 13,656 non-AppleDouble fully hashed paths → 4,660 unique). The t0 image and archive counts are superseded.
**CORRECTED:** see §18. **NEEDS NEW MEASUREMENT:** language shares; near-duplicates and versions (T-P5-03); RAR contents; text-layer quality beyond 5 probe pages; Office twin prevalence (T-P2-09).

## 21. Architectural impact

The t2 corpus is **handled by the existing architecture**: content identity (ADR-003), tiered extraction (ADR-007), DocIR (ADR-011), sensitivity gate (ADR-035), archives as containers (08 §6),
deferred media and code tracks. **No component must be redesigned. No spike is resolved or pre-empted.** Six precise gaps get scoped updates:

| # | t2 characteristic | Gap | Plan update |
|---|---|---|---|
| G1 | 24.5k third-party man-page HTML (+Javadoc) | No policy for generated third-party reference documentation; HTML is not in the extractor list | **ADR-038 (PROPOSED):** classify as `third_party_reference`; registered, excluded from default knowledge ingestion; optional separate "reference" collection later. T-P2-04/05 updated; 08 §7 |
| G2 | Equation Editor 3.0 / MathType OLE in 70 legacy `.doc` (+ OOXML) | ADR-009 names only OMML | ADR-009 scope note (**no status change**): "Office-native equation objects" includes Equation 3.0 and MathType. SPIKE-OMML and T-P3-07 scope extended |
| G3 | 13 password-protected PDFs | Not modelled | T-P2-04: an `encrypted` flag; never attempt cracking; the owner may supply passwords via the curation ledger (Q-N07) |
| G4 | Presentation build-step pages (65 docs, ~8.8k pages) | Would multiply math/OCR cost and flood retrieval with near-identical pages | T-P4-04 (triage): detect build-step runs and process the final state, keeping a page mapping; T-P5-03 includes intra-document near-duplicate pages |
| G5 | 342 ZIPs (16,102 members) not extracted anywhere | Already covered by 08 §6 / T-P2-08, but the scale is now measured | T-P2-08 acceptance criteria reference these numbers |
| G6 | Owner identity documents, CVs, applications, third-party certificates in `books\` | `restricted` class exists but no default rule | T-P2-05: path/name rules default these to **restricted = registered, never processed** (Q-I04 extended; Q-I12 new) |

## 22. Risks discovered

R-27 build-step pages inflate cost and duplicate retrieval hits · R-28 password-protected PDFs silently missing from the knowledge base · R-29 personal identity documents in the corpus ·
R-30 knowledge that exists only inside unextracted archives · R-31 third-party reference HTML flooding lexical retrieval. See 26.

## 23. Remaining unknowns

Language distribution; RAR contents; near-duplicate/version prevalence; Office-twin prevalence; true math-page count (only 5 probe pages per PDF); per-page annotation prevalence;
the reason for the 42 `Permission denied` files (ACLs; the owner may want to fix read permissions so these can be processed); current free disk space and hardware were not re-probed.

## 24. Q-B01 recommendation

**Recommended resolution: CLOSE Q-B01.** Evidence: three identical inventories over 45 minutes (14:04 → 14:49); t1→t2 showed 0 removals and 3 metadata-only changes;
the owner states the migration is finished. **Status: recommended, pending owner confirmation** (25 requires owner-recorded answers). If the owner confirms,
T-P2-12 (audit refresh with the production scanner) proceeds against the t2 baseline, and this document provides its comparison baseline.

## 25. Phase-0 readiness

Phase-0 evidence is now reconciled, reproducible (scripts, raw outputs and pinned environment saved) and consistent with the plan. Remaining gates are owner decisions only:
Q-B05 (plan approval, T-P0-08), Q-B01 confirmation, Q-B02 (vault), Q-B03 (compute/privacy), Q-B04 (model access). **No implementation has started.**
