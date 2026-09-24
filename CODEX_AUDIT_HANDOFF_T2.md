# T2 Forensic Handoff

**Project:** `D:\AgenticAI\second-brain-rag`  
**Source corpus:** `D:\MBI-BRAIN`  
**Review date:** 2026-09-24  
**Purpose:** independent, read-only reconciliation of Claude's t2 re-audit with the raw artifacts, t0/t1 history, and current plan. The previous `CODEX_AUDIT_HANDOFF.md` remains the historical t0/t1 handoff. This report is the current handoff; neither report is an owner approval or an instruction to start implementation.

## Executive conclusion

The three t2 inventory files are byte-identical: **85,913 paths, 561,502,988,849 bytes** at the recorded 14:04:04, 14:21:33 and 14:49:27 snapshots. That is strong evidence for a stable *metadata snapshot during that 45-minute window*, not a permanent freeze or a full byte-for-byte rescan. The raw hash and census files substantiate most of Claude's core totals: **23,512 full-hash duplicate groups, 50,756 exact redundant paths, 99,027,606,279 exact redundant bytes; 27 separate partial-hash candidate groups accounting for 196,834,535,900 candidate redundant bytes; 4,660 hashable non-AppleDouble PDF contents and 361,061 counted pages.** The candidate bytes are not part of exact redundancy.

Several interpretations need correction before ChatGPT uses the numbers. The 4,660 PDF contents are **not all usable**: one is an empty PDF, 13 need passwords, two have zero pages, and six PDF paths could not be hashed. The claimed **136 unique new contents** counts only fully hashed D-category paths: two more D paths are unhashed and have distinct sizes, so the saved evidence supports **at least 138 distinct D-category contents**, subject to the lineage assumptions below. The t2 archive audit compares member **basename and size**, not bytes; it cannot prove that 360 ZIPs are redundant or that 342 ZIPs contain knowledge found nowhere else. The 65 presentation-mode PDFs contain **9,336 total pages**; ~8,770 is an extrapolated number of build-step pages across all landscape PDFs, not the page total of those 65. The proposed “final state only” treatment could discard transient content.

The architecture need not be replaced, and no new phase is demonstrated. t2 does warrant explicit reference-document policy, legacy equation-object extraction experiments, encrypted/ACL-restricted coverage, archive member verification, and safer build-step handling. `T-P0-08` is **technically ready for owner review**, with the qualifications in this report. The owner has not approved it: `T-P0-08` is `NOT_STARTED`, Q-B05 is open, and implementation must not start. Q-B01 is **technically resolvable subject to owner confirmation** of migration completion and a recorded freeze criterion; no status was changed here.

## Evidence model

- **[RAW]** Directly counted or inspected in `audit/phase0/t2/`, historical `audit/phase0/`, or formal state/validator output. A full-file xxh3-128 match with equal size is treated as exact for this audit, while recognizing the usual theoretical collision limit.
- **[CLAUDE]** A statement in `docs/37_T2_CORPUS_REAUDIT.md`, `docs/03_CORPUS_AUDIT.md`, `CLAUDE.md`, or other prose that the saved evidence does not fully establish.
- **[INFERENCE]** This review's interpretation, with its assumptions stated.
- **[UNKNOWN]** Not determined by the saved artifacts.

The t2 audit saved **69 files**: 23 top-level data/index/environment files, 20 scripts, 11 logs, and 15 sample files. The raw inventories are metadata scans; hashes cover document/web extensions and size collisions, **not every file**. A `full` hash covers all bytes; a `partial` hash combines size with three 4 MiB reads and is only a candidate match. The planned production ID is BLAKE3-256; these audit hashes are xxh3-128. PDF page counts are per fully hashed content key where possible; “textless” and math-font/annotation signals inspect at most five pages per PDF. Censuses report source paths and can contain personal information; this handoff gives only broad sensitive locations and counts.

### Artifact map and reproduction boundary

| Artifact group (all relative to `audit/phase0/t2/`) | What was checked | Limits |
|---|---|---|
| `README.md`, `requirements-audit-venv.txt`; `logs/inventory_t2.time`, `inventory_t2b.time`, `inventory_t2c.time`, `inventory_t2.err` | Run provenance and times, pinned audit packages; empty inventory stderr | A requirements list is not a frozen OS/environment image. |
| `inventory_t2.csv`, `inventory_t2b.csv`, `inventory_t2c.csv`, `stats_t2.json`, `org_junk_t2.json` | Three whole-tree metadata snapshots, formats, areas, junk, directories | Filename extension is not magic-byte validation. |
| `logs/stability_t2_vs_t2b.txt`, `stability_t2_vs_t2c.txt`, `compare_t0_t1.txt`, `compare_t0_t2.txt`, `compare_t1_t2.txt` | Saved path/size/mtime comparisons, independently recalculated | `compare_inventories.py` treats a size or mtime change as “changed”; no old bytes are retained. |
| `hashes_t2.csv`, `logs/hash_t2.log`, `dedup_t2_summary.json`, `dup_groups_exact_t2.json`, `dup_groups_candidate_partial_t2.json` | Hash modes, errors, exact/candidate group counts and bytes | 33,057 t0 hashes were reused only when path, size and mtime matched; 42 read errors; 76 partial rows. |
| `identity_t2.csv`, `identity_t2_summary.json`, `logs/removed_t0_fate.txt` | Per-path A/B/C/D/E classification and fate of old missing paths | Identity script's `C` and `D` labels are not a complete historical byte archive. Two D rows lack hashes. |
| `pdf_census_t2.jsonl`, `pdf_census_t2_meta.json`, `pdf_census_t2_summary.json`, `pdf_probe_new_t2.jsonl`, `logs/pdf_census_t2.log` | Unique-PDF counts/pages, encryption, errors, five-page signals, 293 newly selected PDFs probed to 25 pages | Passworded PDFs reveal page counts but not content; first-five distributed probes do not prove document-wide text quality. |
| `office_census_t2.jsonl`, `office_census_t2_summary.json` | OOXML XML tag counts and OLE signature signals, grouped by full-content hash | `<m:oMath>` counted by regex, not rendered validation; legacy OLE byte signatures do not parse the object or distinguish all variants. |
| `archive_census_t2.jsonl`, `html_census_t2.jsonl`, `build_steps_t2.jsonl`, `media_sensitive_t2.json` | ZIP central-directory entries; HTML header classification; first-25-page slide heuristic; media and sensitive filename signals | Archive member content was not hashed; RAR was not opened; HTML first 4 KiB only; sensitive counts are filename heuristics. |
| `samples/old_sample_recheck_t2.csv`, `samples/new_samples_t2.json`, six paired `.txt`/`.png` examples | Twelve old sample identity checks and six new render/text examples | Handpicked examples; no population prevalence inference. |
| `scripts/` (20 named Python scripts) | Read the actual selection, hashing, classification, census and summary logic | Running them anew would overwrite audit outputs and observe a later corpus state; they were read, not rerun. |
| Other logs: `logs/removed_t0_fate.txt`, `hash_t2.log`, `pdf_census_t2.log` | Run counts and completion messages | Logs are secondary to raw rows. |

The 20 scripts are `inventory.py`, `compare_inventories.py`, `stats_t2.py`, `area_presence.py`, `hash_t2.py`, `classify_identity_t2.py`, `removed_t0_fate.py`, `dedup_report_t2.py`, `pdf_census_t2.py`, `pdf_summary_t2.py`, `pdf_probe_new_t2.py`, `build_steps_t2.py`, `office_census_t2.py`, `office_summary_t2.py`, `html_census_t2.py`, `archive_census_t2.py`, `org_junk_t2.py`, `media_sensitive_t2.py`, `sample_recheck_t2.py`, and `render_new_samples_t2.py`. The six new sample pairs are `bwl_skript_p31`, `ckurs_mutex_p1`, `ckurs_scan_p1`, `english_market_leader_p21`, `festigkeit_folien_p61`, and `math1_build_p5_p41`. The t2 requirements file pins `xxhash==4.0.1`, `pymupdf==1.28.2`, `python-docx==1.2.0`, `python-pptx==1.0.2`, `lxml==6.1.3`, `pillow==12.3.0`, `xlsxwriter==3.2.9`, and `typing_extensions==4.16.0`; the audit venv uses Python 3.14.7. The t0 venv had lacked `xxhash`; the t2 package list addresses that missing dependency but does not reproduce the moving t0 corpus.

## Snapshot history

| Metric | t0 (~11:55) | t1 (~12:35) | t2 (14:04) | Evidence quality |
|---|---:|---:|---:|---|
| Files | 39,478 | 73,441 | **85,913** | [RAW] CSV row counts |
| Bytes / decimal GB | 371,092,983,180 / 371.09 | 561,049,965,168 / 561.05 | **561,502,988,849 / 561.50** | [RAW] `size` sums |
| PDF paths | 8,614 | 13,552 | **13,695** | [RAW] extension counts |
| Unique PDF full-hash contents | 3,566 including 11 AppleDouble keys; 3,555 non-AppleDouble census keys | N/A | **4,660** non-AppleDouble hash keys; six unhashable paths | [RAW]; t1 not hashed |
| Unique-PDF pages counted | **328,418** on 3,339 opened t0 keys | N/A | **361,061** on 4,659 opened t2 keys | [RAW]; unreadable/empty/encrypted caveats |
| Image paths (`jpg`, `jpeg`, `png`, `bmp`, `gif`) | 12,847 | 13,766 | **13,766** | [RAW] filename extensions |
| `.html` paths | 12 | 12,277 | **24,516** (`.htm` adds 2) | [RAW] |
| ZIP / RAR paths | 367 / 30 | 755 / 57 | **755 / 57** | [RAW] |
| Office paths (`docx`, `doc`, `pptx`, `ppt`, `ppsx`, `pps`, `xlsx`, `xls`) | 983 | 1,384 | **1,391**; Office census also includes 2 `.dotx` | [RAW], defined extension set |
| Exact full-hash duplicate groups | **8,198** | N/A | **23,512** | [RAW] re-grouped hash rows |
| Exact redundant paths | **18,705** | N/A | **50,756** | [RAW] sum(group size − 1) |
| Exact redundant bytes | **57,253,304,529** | N/A | **99,027,606,279** | [RAW] full-hash groups only |
| Partial-hash candidate groups / candidate redundant bytes | 22 / 106,476,245,081 | N/A | **27 / 196,834,535,900** | [RAW] probabilistic, never added to exact |

The t0→t1 file increase was migration while the first audit ran. t1 was only an inventory and cannot supply unique-PDF, page, or exact-dedup statistics. t1→t2 added 12,472 paths, removed zero, and increased listed bytes by **453,023,681** (0.453 decimal GB). All three t2 inventories have identical SHA-256 `116e2784aea94cc05b9ebeccbbfbab9f90e050f6739bf5b30625ea7d9ec10955` and identical CSV rows including `relpath`, extension, size, integer mtime and depth. That supports **no observed metadata changes within the 45-minute window**. It cannot detect an in-place same-size rewrite with mtime restored, or prove no later changes. The owner’s reported migration completion is [CLAUDE/owner context], not a property of the CSVs.

## t2 authoritative statistics

**[RAW]** t2 contains 85,913 inventory paths, 561.503 decimal GB, 241 zero-byte files, 10,606 directories with files beneath, and maximum recorded depth 14. Seven top-level directory areas plus two root PDFs are present: `Information` 53,266 paths, `Mechanical` 15,346, `BachelorArbeit` 15,269, `books` 1,604, `Betriebslehre` 315, `Ckurs` 108, `English` 3, plus `curriculum_mbi_ws2019.pdf` and `MBI-WS2019-Modulhandbuch.pdf`. By bytes, `Mechanical` is 358.87 GB, `Information` 162.82 GB, `BachelorArbeit` 24.09 GB, `books` 10.46 GB, `Betriebslehre` 5.15 GB, `Ckurs` 0.07 GB, `English` 0.05 GB. Top extension counts: `.html` 24,516; `.pdf` 13,695; `.jpg` 8,009; `.java` 7,180; `.png` 3,942; `.class` 3,930; `.mat` and `.exml` 2,807 each; `.m` 1,869; extensionless 1,665; `.mp4` 1,595; `.zip` 755. MP4 alone is 428.18 GB; all listed video extensions total **1,749 paths / 445,368,049,161 bytes**. These are extension-based categories.

**[RAW]** `hashes_t2.csv` has 80,264 selected paths: 80,146 `full`, 76 `partial`, 42 `err` (`PermissionError`), with 47,207 computed rows and 33,057 cached t0 rows. Hashing did not cover all 85,913 paths. Six PDF paths have no full hash and are among the unreadables. Cache reuse requires same path, size and integer mtime, so it is a pragmatic audit optimization, not a fresh t2 byte read for cached rows. `inventory_t2.err` is empty; this means no logged traversal error, not that every file could be read.

### Twenty core numerical claims, independently classified

| # | Claude claim | Finding | Status |
|---:|---|---|---|
| 1 | Three snapshots identical | CSVs byte-identical; 85,913 rows and same metadata | **VERIFIED** for recorded inventories |
| 2 | 85,913 files / 561.50 GB | 85,913; 561,502,988,849 bytes | **VERIFIED** |
| 3 | 13,695 PDF paths | 13,695 `.pdf` inventory rows | **VERIFIED** as extension count |
| 4 | 4,660 “unique usable PDFs” | 4,660 non-AppleDouble full-hash keys, including empty/passworded/zero-page contents | **PARTIALLY VERIFIED**; “usable” is wrong |
| 5 | 33 `._*` junk PDF paths | 33 PDF paths excluded by basename | **VERIFIED** |
| 6 | Six unreadable PDF paths | Six PDF hash rows lack full hash; PermissionError | **VERIFIED** as paths, unique contents unknown |
| 7 | 13 password-protected PDFs | 13 content-key rows with `needs_pass=true` and `is_encrypted=true` | **VERIFIED** for hashable keys |
| 8 | Two zero-page PDFs | Two opened key rows with `pages=0` | **VERIFIED** |
| 9 | One empty PDF | One zero-byte content key has `EmptyFileError` | **VERIFIED** |
| 10 | 361,061 unique-PDF pages | Sum of `pages` across 4,659 opened key rows | **VERIFIED** for counted keys |
| 11 | 1,320 previously uncounted unique PDFs | Content-key set difference from successful t0 census: 1,320 | **VERIFIED**; not synonymous with newly created |
| 12 | 32,643 pages in those keys | Raw page sum of the 1,320 set | **VERIFIED** |
| 13 | 17.7% fully textless | 820 / 4,644 probeable keys = 17.657%, rounded 17.7% | **VERIFIED** as five-page signal, not all-page OCR finding |
| 14 | 23,512 exact groups | Re-grouped `(full,hash,size)` rows | **VERIFIED** |
| 15 | 50,756 exact redundant paths | Sum of group extra paths | **VERIFIED** |
| 16 | 99.0 GB exact redundant bytes | 99,027,606,279 bytes | **VERIFIED** |
| 17 | 27 partial-hash candidate groups | Re-grouped `(partial,hash,size)` rows | **VERIFIED** as candidates |
| 18 | 196.8 GB candidate redundant bytes | 196,834,535,900 bytes | **VERIFIED** as probabilistic candidate bytes only |
| 19 | 152 genuinely new files since t1 | `D` contains 152 first-seen paths / 187,025,776 bytes; one changed old path lacks a t1 hash | **PARTIALLY VERIFIED** as classified new paths; not a complete byte-history proof |
| 20 | 136 unique contents among those 152 | 136 distinct full hashes across 150 D rows **plus two unhashed D rows of different, otherwise unmatched sizes** | **CONTRADICTED** as a complete unique-content count; at least 138 |

Thus, for these explicitly enumerated 20 claims: **17 VERIFIED, 2 PARTIALLY VERIFIED, 1 CONTRADICTED**. Status refers to the literal wording and measurement scope, not to the value of the t2 work as a whole.

## t0 corrections

**[RAW]** The previous `CODEX_AUDIT_HANDOFF.md` correctly identified the important t0 caveats. Re-grouping `audit/phase0/hashes.csv` by `(mode,hash,size)` gives **8,198 full-hash groups / 18,705 exact redundant paths / 57,253,304,529 exact redundant bytes**, and **22 partial-hash groups / 27 candidate redundant paths / 106,476,245,081 candidate bytes**. Their sum (163,729,549,610 bytes) produced the old “163.7 GB redundant” line, which incorrectly merged exact and candidate bytes. The 34 t0 hash errors say `Permission denied`; all 34 paths appear in the t1 and t2 inventories, while 28 remain hash errors at t2. The remaining six becoming readable does not establish why they were restricted originally.

**[RAW]** The t0 unique-PDF census has 3,339 rows with a page count and **328,418 pages**, versus the old prose's 3,337 / 328,409. The t0 25-page probe has 1,688 successes: **248/1,688 = 14.7%** with *all inspected pages* below 30 text characters; **259/1,688 = 15.3%** with at least 80% of inspected pages below that threshold. The original wording “fully textless” blurred these definitions. Twelve of the 14 t0 probe errors were `no such file`, two were empty-file errors; the 34 hash errors were not proven moves. `docs/03_CORPUS_AUDIT.md` now begins with these corrections and labels itself historical, but its old body still contains the superseded `163.7 GB`, `592 OMML`, and original page totals; readers must use its correction banner plus `docs/37`.

The t0 math and visual sample findings remain valid: `samples/old_sample_recheck_t2.csv` records all 12 checked source paths as the same full-hash content at t2, including the thesis DOCX and the scanned-exam source whose original render was never produced. The older paired render/text examples still show broken MathType/Word/LaTeX display-math text, a scanned truss diagram and visible handwriting. **[RAW]** The old `scanned_exam` omission was due to a raw-string `\u00f6` path bug in the sample script, not a missing corpus file. The recheck does not independently repeat every extraction experiment.

## t1 → t2 reconciliation

**[RAW]** All 73,441 t1 paths remain at t2; 12,472 paths were added; three common paths changed integer mtime but kept the same size. Two of these three had t0 full hashes equal to their t2 full hashes. The third first appeared at t1 and has no saved t1 hash, so the statement that **all three bytes were unchanged** is not independently provable. The t0→t2 absent-path set has 675 paths; all 675 have a t0 full hash that occurs under another t2 path, which supports *content preservation for those hashed files*. It does not establish whether each path was moved, renamed or copied.

`identity_t2.csv` assigns A=38,801 (path/size/mtime same as t0), B_exact=30,870 (content match to t0-hashed or t1-era path), C=16,090 (first seen at t1, not matched to t0-hashed content), D=152 (first seen at t2 and classified novel), E=0. These are **classification rules**, not a complete proof of historical semantic novelty. B_exact includes content already present before t2 and spans both t1-added and t2-added paths; calling all 30,870 “moved/renamed since t1” is inaccurate. C means t1-era paths that were not deeply audited at t0; some could duplicate un-hashed t0 content. Hence the report's “C+D = genuinely new vs t0” is stronger than the data allows.

Of the 12,472 t2-added paths, **12,320** are B_exact and **152** are D under the saved classifier. The largest copy expansion is the second `man-pages` tree: 12,240 files of various extensions, including 12,239 `.html` files. Other additions include root `Ckurs` 108 files, `English` 3, seven `Betriebslehre` quality-management PPTX files, and course/code copies under existing areas. D is 187,025,776 bytes; 150 D rows have full hashes forming 136 distinct keys. The remaining two are `.c` files with no hash, each a different size seen nowhere else among D or the older inventories. **[INFERENCE]** at least 138 distinct file contents are represented by D, although their two un-hashed bytes cannot be directly matched. “Genuine new knowledge” is still a semantic judgment: newly visible files may be copies inside archives, vendor/reference material or material known from another source.

## Duplicate analysis

| Defined measure | t0 | t2 | Interpretation |
|---|---:|---:|---|
| PDF redundant **paths** / PDF full-hash paths | (8,614−3,566)/8,614 = **58.6%**, includes AppleDouble keys | (13,656−4,660)/13,656 = **65.9%** | t2 denominator excludes 33 AppleDouble and six unhashable PDF paths; 4,660 is hash-addressable contents, not necessarily readable. |
| All-file exact redundant **paths** / all inventory paths | N/A, t0 full-hash scope differed | 50,756/85,913 = **59.1%** | A path fraction; 5,649 t2 paths lack full hashes and could hide more duplicates. |
| Exact redundant **bytes** / all inventory bytes | 57,253,304,529/371,092,983,180 = **15.4%** | 99,027,606,279/561,502,988,849 = **17.6%** | Proven full-hash redundant bytes under the audit method. |
| Candidate partial-hash redundant bytes | **106.5 GB**, 22 groups | **196.8 GB**, 27 groups | Potential duplicate bytes in large non-document files, **not** an exact-byte rate and not added to 99.0 GB. |

**[RAW]** `dedup_t2_summary.json` groups only full hashes as exact and partial hashes separately. The t2 exact groups include **9,016 redundant `.pdf` paths** and 14,741,244,745 PDF bytes if AppleDouble files are included; the clean PDF path formula above yields 8,996 redundant non-AppleDouble fully hashed paths. HTML contributes **12,270 redundant paths** but only 189,381,291 bytes. MP4 contributes 65,148,408,490 exact redundant bytes, while some very large videos remain partial-hash candidates. The resulting **85,913−50,756 = 35,157 paths after removing proven extra copies** is an upper bound on content objects, not a confirmed unique-object count, because unhashed and partial-hash cases remain. Do not say “56% duplicates” without identifying the denominator and certainty.

The directory mirror figure (488 “maximal” pairs) comes from a heuristic over prefixes and exact shared hashes at ≥90% overlap in both directions; many nested/overlapping pairs are enumerated. It establishes substantial mirrored material, not 488 independent duplicate trees. Exact dedup remains a relation in the registry, never an instruction to delete source files (ADR-003/031). Normalized-text near-duplicates, annotated variants and intra-document slide states are separate, unmeasured problems.

## PDF analysis

**[RAW]** The inventory has 13,695 `.pdf` paths. `pdf_census_t2.py` excludes 33 `._*` AppleDouble paths and records six non-AppleDouble PDF paths with no full hash (`PermissionError`). The other **13,656 paths map to 4,660 full-hash `(hash,size)` keys**. The census tried a representative path and had a fallback mechanism, but no fallback was used. It opened 4,659 keys, counted **361,061 pages**, and recorded one empty-file open error. Thirteen opened keys have both `needs_pass` and `is_encrypted`; page count is available, text/visual probe fails with `ValueError`. Two more report zero pages. Thus **4,644 keys produced probe signals**. “4,660 unique usable PDFs” should be replaced with “4,660 hash-addressable non-AppleDouble PDF contents, 4,659 openable, 4,644 probed.” The six unreadable paths could contain zero to six further unique contents; the saved data cannot resolve them. “Zero corrupt-unopenable” ignores the empty file; it is fair only if corruption excludes empty files by definition.

Among 4,644 probeable PDFs, 820 have all five sampled pages below 30 stripped text characters (**17.7%**), 846 have at least 80% of sampled pages below that threshold (**18.2%**), 1,229 have any sampled page below it (**26.5%**). Five pages are chosen at start, quarter, middle, three-quarter and end, with duplicates removed for short PDFs. The estimate of ~27,346 textless pages and ~81,785 math-font pages is **[INFERENCE/EXTRAPOLATION]**, not a full-page scan. `Symbol` can indicate bullets, so math-font pages are an upper-bound signal. 2,128 probeable PDFs show math fonts on at least one sampled page; 310 show PDF annotation objects on sampled pages. 534 PDFs with ≥200 pages contain 273,919 pages (**75.9%** of the counted page total). First-page landscape flags 1,442 PDFs, but landscape is only a slide-like heuristic.

The t2 set has **1,320 full-hash PDF keys / 32,643 pages absent from the successful t0 page census**. This includes new additions and previously uncounted old content; it is not 1,320 newly created documents. A stratified `pdf_probe_new_t2.jsonl` sample has 293 documents (seed 42, at most eight per level-3 path group), of which 128 are wholly textless over the first 25 pages, 84 show math fonts, and 16 show annotations. The 108 root `Ckurs` PDFs are a visible image-only English teaching-content class; they inflate that particular sample's textless share. Six new paired render/text examples show an empty text layer for `Ckurs` images, readable BWL/English text, a Math 1 build-step slide and engineering force diagrams whose visual semantics exceed plain text.

**Presentation-mode caveat [RAW + INFERENCE]:** `build_steps_t2.py` scans only the first 25 pages of each of 1,442 first-page-landscape unique PDFs. A page is called a build step when its normalized text starts with 90% of the preceding page's text and the predecessor has at least 30 characters. Exactly **65 PDFs** cross a ≥30%-of-checked-pages threshold. Those 65 contain **9,336 pages in total**. Summing per-document whole-length extrapolations across **all** landscape PDFs gives **8,770 estimated build-step pages**. That number is neither an exact page count nor confined to the 65. The detector misses image-only and reordered builds and can flag simple repeated slide text. Keeping only the final page of a run could erase intermediate-only annotations, diagrams, questions, or formula stages. Preserve every source page and locator; select final-state processing only after proving earlier information is contained in it, with fallback to retaining noncontained states. The current T-P4-04 wording “route only the final build state” needs this semantic safeguard before implementation.

## Office/math analysis

**[RAW]** `office_census_t2.jsonl` contains 1,393 Office-path rows including two `.dotx` paths; three `.docx` paths produce `BadZipFile` errors. Joining by full `(hash,size)` leaves 844 content keys (including failed keys). The script opens OOXML ZIP parts and counts XML byte patterns `<m:oMath[ >]` as individual Office Math expressions and `<m:oMathPara[ >]` as display wrappers, avoiding the t0 substring error that counted `oMathPara` and `oMathParaPr` as equations. Across unique content: **31/158 DOCX with 2,597 `oMath`**, **13/35 PPTX with 489**, and **5/53 PPSX with 174**. Hence **49 unique OOXML files, 3,260 counted `oMath` elements**. `oMathPara` wrappers total 934 DOCX, 234 PPTX, 111 PPSX and are not added to 3,260. This is an element count; it is not a conversion-quality or rendered-equation validation.

The specific `BachelorArbeit\...\BA\Bachelorarbeit.docx` content has **422** `oMath` elements. Different thesis-named variants have **419, 424 and 432**; they must not be collapsed into a single “the thesis” count. The Praxisphase document has 388 and the cited exercise deck 322 in this census. Two unique DOCX files have 17 `ProgID="Equation.3"` OLE references. Among **141 unique legacy `.doc` contents**, **70 contain the `Equation.3` byte signature**, and seven contain a `MathType` signature; these sets may overlap. The legacy method reads bytes and counts strings, not OLE streams or MTEF objects, so “70 files contain Equation Editor 3.0 objects” is **partially verified** as a signature signal. It cannot prove object integrity or distinguish all Equation Editor/MathType payloads. The three failed OOXML paths are 162-byte `.docx` files; their content is not parsed.

The evidence supports extending ADR-009 and SPIKE-OMML to **test** legacy Office equation extraction; it does not accept a specific converter or guarantee exact conversion. OMML-first for genuine Office twins remains sensible, while PDF formulas without usable Office originals still need a visual/math tier. **Planning inconsistency:** ADR-009's original status sentence still cites “592 OMML equations in the thesis” as evidence, even though its new scope note correctly says 422. `docs/10_MATHEMATICAL_CONTENT.md` has the corrected 422/388/322 values.

## Archive analysis

**[RAW]** The inventory and `archive_census_t2.jsonl` contain **812 archive paths: 755 ZIP, 57 RAR**, totalling **59,580,609,250 bytes**. ZIP central directories were read without extracting or changing `D:\MBI-BRAIN`; RAR contents were not read. Of the ZIPs, **360 nonempty** have every member's **lowercased basename and uncompressed size** found somewhere among t2 inventory files (49,595,117,101 compressed bytes, 7,811 members). **One empty ZIP** also satisfies the script's equality condition vacuously. **52** have some but not all member name+size matches (13,783 members); **342** have none (7,317,516,544 compressed bytes, **16,102 member entries**). The script also counts **265 nested-archive member occurrences**, not 265 confirmed unique accessible inner archives. Same-stem sibling directories exist for 228 archive paths, a weak separate signal.

This is a *name-and-size presence census*, not extracted-content verification. A match can be a different file with the same basename and size; a nonmatch can still be byte-identical to a renamed file. ZIP members may include directories (excluded from member counts), unsupported formats, encrypted data, or duplicate archive copies; no member bytes were hashed. Therefore “360 fully extracted/redundant containers” and “342 contain knowledge only inside archives” are **[CLAUDE] interpretations, not proven facts**. The measured statement is “360 nonempty ZIPs have all member basenames and sizes matched somewhere in the t2 path inventory; 342 have no such matches.” `T-P2-08` correctly plans streamed member hashing and RAR/7z handling, but its acceptance criterion currently calls the 342 “not extracted anywhere”; it should be interpreted as an audit baseline requiring content reconciliation, not an established truth.

Archives and images are unchanged in path count from t1 to t2: 755 ZIP, 57 RAR, 13,766 image paths. The HTML second tree is consistent with extracted/copy-expanded material while retaining the source archive, but the audit does not prove exact extraction chronology merely from t1/t2 snapshots. Archive ingestion must preserve container/member provenance, enforce traversal and size limits, and write derived material only under project `var/`.

## HTML/reference-material analysis

**[RAW]** There are **24,516 `.html` plus two `.htm`** files. The classifier reads only each file's first 4 KiB and reports 22,338 `man_page_html`, 30 `javadoc`, seven `eclipse_help`, and 2,143 `other` across both suffixes. The two `man-pages` trees together contain **24,478 files = 99.845% of `.html` count** (22,338 marker-classified man pages plus 2,140 `other` pages under those trees, many with copyright/license titles). Thus “99.8% Linux man pages” is defensible **by tree membership**, not by the `man_page_html` classifier alone. The remaining 40 HTML/HTM paths include Javadoc, Eclipse help and three other pages. `hashes_t2.csv` gives **24,516 full-hashed `.html` paths → 12,246 unique `(hash,size)` contents**. The two large trees have equal full-hash content multisets of 12,240 files each; they are content-equivalent, though not every relative filename matches (11,823 do). A source ZIP is also present, but member bytes were not matched to the HTML trees.

These are strongly evidenced as generated/third-party **reference** material, and indexing all of them in the main lexical collection would likely skew coverage and retrieval. They may still be relevant to systems-programming course work. ADR-038 is appropriately **PROPOSED** as a default policy with an optional labeled reference collection and owner override; “not course knowledge” is too absolute. The t2 `Ckurs` images and external vendor manuals likewise require authority/genre labels rather than blanket deletion. HTML, ZIP and media are never source-cleanup instructions.

## Organization/taxonomy

**[RAW]** The t2 root has seven areas plus two curriculum PDFs, as listed above. The increase is concentrated in `Information` (40,978 t1 → 53,266 t2) because of the man-page copy, while `BachelorArbeit` and `books` remain at 15,269 and 1,604. t0/t1/t2 paths still exhibit course abbreviations, legacy spelling, mirrors and cross-filed subject material. The new root `English` (3 files) and `Ckurs` (108) add explicit English teaching material. `Information\C\man-pages` and the `Information\Informatikx\1\Sys.prog2\man-pages` content trees match by hashes; older `vorvorl`, course and MATLAB mirrors persist. The two root curriculum/module-handbook PDFs remain useful taxonomy seeds. The tree is location evidence, **not** a semantic taxonomy, and the abbreviation mapping and owner curation tasks remain necessary. A filename/producer rule cannot decide whether a book, vendor manual, slide or external course should be indexed as owner, lecture or reference knowledge.

## Sensitive-material findings

**[RAW, path signals only]** `media_sensitive_t2.json` records filename-pattern hits: grades 105, contracts 5, applications/certificates 21, and identity-document terms 2. These categories can overlap and are not confirmed counts of actual sensitive documents. Broad locations include `books\` and study/administrative subfolders; no names, identifiers, addresses, certificate numbers or document images are reproduced here. **[CLAUDE]** The corpus contains identity scans, CVs/applications, matriculation/certificates and at least one certificate of another person. The specific third-party ownership was not independently verified from private content during this handoff.

The current formal policy in `docs/22_SECURITY_AND_SAFETY.md`, `T-P2-05`, ADR-035, Q-I04 and Q-I12 directs identity/CV/certificate/grade-list material to **`restricted` by default: metadata registration only, no content processing or external transmission, counts-only reporting**, with owner curation override. This is a necessary boundary and should be applied before any ingestion. Filename/path rules can miss mislabeled scans and can overrestrict unrelated files, so the later classifier and owner review still need evaluation. No source file was moved or deleted.

## Architectural impact

| Question | Evidence-based assessment |
|---|---|
| Does t2 invalidate the architecture? | **No.** Read-only SourceFS, content identity, DocIR, provenance, tiered extraction and scoped agents still fit the observed corpus. |
| Require a new phase? | **No.** Existing P2/P3/P4/P5/P6 work can absorb the six scoped additions; this is a plan assessment, not approval. |
| New extraction capabilities? | **Yes, scoped:** HTML/reference classification, encrypted/ACL coverage, legacy equation-object experiment, archive member verification, and build-step-aware per-page handling. |
| Change math strategy? | **Extend** OMML-first twin fusion to test Equation Editor 3.0/MathType OLE, and preserve visual recognition for unmatched PDF math. Do not presume conversion quality. |
| Change deduplication? | **Clarify** full-hash exact versus partial candidates and intra-document near-duplicates. Do not delete source copies. |
| Change archive handling? | **Measure with member hashes** and provenance rather than treating name+size as extracted-content proof; read RAR/7z in the planned task. |
| Change sensitivity/privacy? | **Yes:** restricted-by-default identity and third-party material, counts-only reports, and model-gateway blocking. |
| Change taxonomy assumptions? | **No replacement**, but add reference/authority and English-course labels; filesystem folders remain only signals. |
| Resolve Q-B01? | **Technically supportable** after the owner confirms migration completion and records the answer; 45-minute stability alone cannot authorize closure. |
| Reason to withhold owner review T-P0-08? | **No technical blocker to review.** Owner should see the archive/build-step/identity qualifications and stale governance text before approval. |

## Updated ADRs/tasks/questions/risks

**[RAW/formal plan]** `ADR-038` exists once and is **PROPOSED** for `third_party_reference`, deduped/registered but excluded from default main indexes. `ADR-009` adds a legacy Equation Editor/MathType scope note, though its older status evidence still says 592. `T-P0-09` exists, is `DONE`, and is a dependency of `T-P0-08`; `T-P0-08` remains `NOT_STARTED`, `Human approval: required`, and gates `T-P1-01`. T-P2-04 adds `encrypted` and reference classes; T-P2-05 defaults sensitive identities to restricted; T-P2-08 adds the archive baseline; T-P3-07/SPIKE-OMML adds legacy equation testing; T-P4-04 adds build-step triage; T-P5-03 adds intra-document near duplicates. `R-27` through `R-31`, `Q-I12`, `Q-I13`, and `Q-N07` through `Q-N09` all exist. Q-B05 is still open. No spike is marked complete by this audit.

**Plan wording risks:** (1) ADR-009 still cites 592 in its original evidence line; (2) `R-27`/T-P4-04 assume final-state-only processing, which has an untested semantic-loss risk; (3) `R-30`/T-P2-08 phrase 342 ZIPs as “not extracted anywhere,” stronger than the name+size census; (4) `docs/37` calls 70 legacy signatures objects; and (5) its C+D “genuinely new vs t0” statement exceeds the saved hash coverage. These are review annotations, not edits to plan state.

**Governance paths [RAW]:** The user-supplied AGENTS.md names `C:\Users\ammar\.claude\brain`; that path does **not** exist in this filesystem view. `D:\AgenticAI\My-Knowledge\brain` exists, contains `CLAUDE.md`, `BRAIN_GOVERNANCE.md`, and registry record `11_Indexes\Projects\PRJ-0030.md`; the project `CLAUDE.md` points there. The Brain's own `CLAUDE.md` still states the absent C: path. Q-N09 captures this stale-path issue but says “global instructions use D:\AgenticAI\My-Knowledge\brain,” which conflicts with the supplied AGENTS.md text. `PRJ-0030.md` still says 36 Markdown docs plus `35_EXECUTION_STATE.json`, 37 decisions and 145 tasks; the current project has **37 Markdown docs plus one JSON, 38 decisions and 146 tasks**. It also describes the corpus as still growing. These are governance/documentation inconsistencies, not corpus-statistics faults. No Brain record or governance file was changed.

## Validation results

**[RAW]** `python tools/validate_plan.py` exited 0: `PLAN CONSISTENT: 146 tasks, 8 done, next eligible: T-P0-08; 38 decisions; 18 spikes`. `python tools/audit_crossrefs.py` exited 0: 38 ADRs, 146 tasks, 27 questions, 31 risks, 18 test-suite IDs, 64 requirement IDs and 18 spikes defined; no undefined references or sequence-order violations. Direct counts found 38 unique ADR IDs, 146 unique task IDs, 18 unique spike IDs and `T-P0-09` `DONE` in both task register and execution state. These scripts are read-only and were inspected before execution. They validate syntax, dependencies and cross-references; they **do not validate the empirical truth of numeric prose or policy semantics**. No plan file or status was modified.

## Discrepancy and qualification register (12)

1. **PDF “usable” wording:** 4,660 includes empty, passworded and zero-page hash keys, and six unhashable paths are outside the count.
2. **D unique count:** 136 is only the distinct full-hash count; two more D paths have unmatched, distinct sizes, implying at least 138 contents.
3. **Historical novelty wording:** `C` is not proven novel relative to all t0 bytes; B_exact cannot distinguish move from copy; 30,870 is not the t1→t2 move count.
4. **Three changed t1 paths:** two have t0/t2 hash equality, while the third lacks a t1 hash, so all-three byte identity is unproved.
5. **ZIP “fully extracted” wording:** 360 nonempty ZIPs have name+size matches, not verified byte matches; one empty ZIP satisfies the code's equality test too.
6. **Archive-only knowledge:** 342 ZIPs/16,102 members have no name+size match; unseen content/knowledge is not proved, and RAR contents remain unexamined.
7. **HTML 99.8%:** true by `man-pages` path membership (24,478/24,516), not the 22,338 header-marker class alone; the trees are content-equivalent, not path-identical.
8. **Legacy equations:** 70 `.doc` keys have an Equation.3 byte signature, not parsed/validated equation objects; conversion remains a spike.
9. **Presentation pages:** 65 flagged decks total 9,336 pages; ~8,770 is a whole-landscape extrapolation. Final-state-only processing can lose transient information.
10. **Sensitive ownership:** path patterns support broad categories, while the asserted third-party certificate owner was not independently verified; exact sensitive-document counts are unknown.
11. **Historical prose:** ADR-009 still cites the superseded 592; `docs/03` retains old body figures beneath its correction banner.
12. **Brain registry/path:** Q-N09 conflicts with the supplied AGENTS.md path, and PRJ-0030 retains stale document, task and decision counts.

## Remaining uncertainties

- Current corpus state after the 14:49:27 snapshot and exact owner-defined “frozen enough” criterion.
- Content of six unreadable PDF paths and 42 hash-error paths; whether access policy, ACLs, locks or another reason caused denial.
- t1 bytes for the one common path whose mtime changed without a t0/t1 hash; semantic novelty of C-category contents and the two unhashed D files.
- Contents of RAR archives and hash-based ZIP member equivalence; encrypted/truncated archive members and extracted-source chronology.
- Full-page OCR/math/layout quality, actual language proportions, near duplicates, PDF/Office twin prevalence, presentation build-step semantics, and recognition/conversion throughput and accuracy.
- Exact count and ownership of restricted personal material beyond filename signals; current free disk space and CPU/GPU state were not re-probed here.
- Owner answers to Q-B01–Q-B05, including plan approval, vault location, compute/privacy policy and model access. A green validator does not answer these questions.

## Q-B01 assessment

The three inventory snapshots have exactly equal rows and hashes over 45 minutes; t1→t2 added paths but removed none, and the owner is reported to have finished migration. **[INFERENCE] Q-B01 is technically ready for an owner-recorded answer that treats t2 as the baseline.** A finite metadata stability window cannot prove perpetual content immutability or replace incremental detection. Keep T-P2-12's production-scanner refresh and change detection as planned. This review did **not** close Q-B01 or change the execution state.

## T-P0-08 technical readiness

The source-traced t2 baseline, corrected t0 history, saved scripts and raw outputs, and passing plan/cross-reference checks make the plan **ready to present to the owner for T-P0-08 review**. The owner should explicitly see the measured-versus-inferred archive distinction, the build-step semantic-loss risk, the incomplete “136 unique” claim, and the sensitivity default. These issues can be resolved in owner review or the specified spikes/tasks; they do not require beginning P1 now. `T-P0-08` and Q-B05 remain open, and this reviewer made no approval decision.

## What ChatGPT must know

Use **t2** for current corpus sizing, **t0** only as historical evidence, and **N/A** for t1 analyses never performed. Quote duplicate rates only with denominators: t0 PDF redundant paths **58.6% of 8,614 PDF paths**; t2 PDF redundant paths **65.9% of 13,656 non-AppleDouble full-hashed PDF paths**; t2 all-file exact redundant paths **59.1% of 85,913 inventory paths**; t2 exact redundant bytes **17.6% of 561.503 GB**. Keep **196.8 GB partial-hash candidate bytes** entirely separate. Treat 4,660 PDFs as hashable content keys, not 4,660 readable/processable documents. The ~27k textless and ~81.8k math-font page totals are extrapolations from sparse within-document probes. Never ingest identity material by default or transmit it to external models. Neither `T-P0-08` nor Q-B05 has owner approval. The plan's technology options remain proposed until their spikes; t2 did not build a RAG system.

## Files that must be preserved

Keep the old `CODEX_AUDIT_HANDOFF.md` unchanged as the t0/t1 historical review. Preserve the t0/t1 inventories, hashes, probe/page JSONL, sample renders/text and original scripts; t2's three inventories, `hashes_t2.csv`, both duplicate group JSON files, `identity_t2.csv`, PDF/Office/HTML/archive/build-step JSONL files, summaries, logs, samples, scripts, `README.md`, and `requirements-audit-venv.txt`. Keep current `docs/03` as corrected history and `docs/37` as Claude's t2 interpretation alongside the formal ADR/question/risk/task/spike/state documents. These files provide traceability; the raw path inventories and censuses are private because they contain sensitive names. This report is an additional interpretation, not a replacement for the evidence.

## Confidence by category

| Category | Confidence | Why |
|---|---|---|
| t2 inventory size/stability, extension and root counts | **HIGH** | Three byte-identical CSVs and independent row/byte counts. |
| Exact full-hash duplicate counts and rates | **HIGH** within hash scope | Raw regrouping matches summary; cached t0 hashes and 42 errors limit absolute whole-corpus completeness. |
| Partial-hash candidate bytes | **HIGH** as candidate arithmetic, **LOW** as exact duplicate proof | Three-sample hashes cannot establish byte identity. |
| PDF content keys/pages/encryption | **HIGH** for opened/hashable keys, **MEDIUM** for complete corpus | Six unreadable paths and one empty key; text/math estimates use five-page probes. |
| t1→t2 identity/new knowledge | **MEDIUM** for path/hash categories, **LOW** for semantic novelty | No t1 byte archive; two un-hashed D files; ambiguous move/copy and old archive content. |
| Office OMML tags | **HIGH** for regex-counted tags, **MEDIUM** for rendered equations | No parser/converter-quality validation; legacy OLE is signature-only. |
| ZIP extraction status and archive-only knowledge | **LOW** | Basename+size matches, no member hashes; RAR not read. |
| HTML tree dominance | **HIGH** for path/hash structure, **MEDIUM** for knowledge-value policy | 4 KiB header classifier and path membership; course relevance is contextual. |
| Presentation build-step volume/triage | **MEDIUM** for first-25-page heuristic, **LOW** for whole-document extrapolation/final-only safety | Visual/semantic containment untested. |
| Plan state and ID consistency | **HIGH** | Both validators pass; formal statuses agree. |
| Sensitive categories | **MEDIUM** as path signals, **LOW** for precise counts/ownership | Private document contents intentionally not exposed or fully inspected. |
