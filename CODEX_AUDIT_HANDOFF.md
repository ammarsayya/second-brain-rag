# Phase 0 forensic handoff: Second Brain / Agentic RAG

**Prepared 2026-09-24.** Project: `D:\AgenticAI\second-brain-rag`. Source corpus: `D:\MBI-BRAIN`. This is a static review of the 35 files in `audit\`, all 31 files in `.remember\`, audit virtual-environment metadata, and the relevant formal project documents. No corpus or RAG artifact was executed or changed. The only new file is this report. The corpus itself was not rescanned, so no number below is a claim about its present state.

**Evidence notation:** **[RAW]** directly counted/read in supplied artifacts; **[CLAUDE]** statement in Claude's `docs/03_CORPUS_AUDIT.md`, `CLAUDE.md`, or plan, not independently demonstrated by the supplied raw artifacts; **[INFERENCE]** this reviewer's interpretation; **[UNKNOWN]** unresolved. Paths in inventory rows may disclose third-party personal information; keep the underlying artifacts private.

## Executive orientation and snapshot boundary

- **[RAW]** `inventory.csv` and `inventory_t0.csv` are byte-identical (SHA-256 `e04b383bbda0778a122e91373153ac3bb761599f744f257a3d3aa89fffea27e3`), 39,478 rows, 371,092,983,180 bytes. `inventory_t1.csv` has 73,441 rows, 561,049,965,168 bytes. Exactly 675 t0 paths are absent from t1; 34,638 t1 paths are new. Path differences alone do **not** prove moves versus deletions.
- **[RAW]** Only t0 has hashes, duplicates, PDF probing and unique-PDF page census. The later t1 is metadata only. Never apply t0 duplicate or textless percentages to t1 as measurements.
- **[RAW]** `hashes.csv`: 33,768 rows, 33,685 full hashes, 49 partial hashes and 34 errors. The error strings begin `Permission denied`; the written claim that all 34 were moved is **[CLAUDE]** interpretation, not established by the error text.
- **[RAW]** `dup_groups.json`: 8,220 groups containing 26,952 path entries, hence 18,732 redundant entries under this grouping. These are exact only for full-hash entries. At least some groups contain partial-hash entries and require full verification before calling them exact.
- **[RAW]** `pdf_probe.jsonl`: 1,702 rows, 14 errors, zero `encrypted=true` among successfully opened documents, 248 wholly textless in the inspected page window and 152 partly textless. `pdf_unique_pages.jsonl`: 3,555 rows, 217 errors, 3,339 opened, 328,418 counted pages. The 3,566 unique PDF hash pairs become 3,555 because `pagecount.py` excludes `._*` AppleDouble files (33 PDF paths, 11 unique pairs). The formal report instead says 3,337 opened and 328,409 pages; this is a small but real artifact/report discrepancy. The latter file contains one empty-file error and one `document closed or encrypted` error, so encryption cannot be ruled out corpus-wide.
- **[RAW]** `.remember` contains plugin logs, markers and temporary session state, **no** `core-memories.md`, `now.md`, `recent.md`, `today-2026-09-24.md`, `archive.md`, or project `config.json`. The manifest references these absent files. Summarization repeatedly failed (`WinError 2`), so it cannot serve as a record of Claude's decisions.
- **[CLAUDE/formal state]** `T-P0-08` (owner review) and `T-P1-01` are `NOT_STARTED` in `docs/35_EXECUTION_STATE.json`; Q-B01 through Q-B05 are open. `CLAUDE.md` calls Phase 0 complete in the sense of planning/audit work, **not** approved for implementation.

## 1. Artifact inventory and authority

All paths below are relative to `D:\AgenticAI\second-brain-rag`. Sizes are filesystem bytes at inspection. `audit\phase0` has 35 files: seven datasets, one README, seven Python scripts, ten PNG renders, nine text dumps, and one JSON sample index. Every item is project-created and important to reconstructing Phase 0, except that individual render/text pairs are repetitive examples rather than whole-corpus evidence. `.remember` has 31 files: two root markers, two principal logs, 17 small autonomous logs, and ten temporary files. Ordinary third-party contents of `.venv-audit\Lib` were excluded from file-by-file review.

| Path | Type / bytes | Purpose and scope | Importance |
|---|---:|---|---|
| `audit/phase0/README.md` | Markdown / 1,567 | Claude's artifact map and reproduction notes; generated overview | HIGH |
| `audit/phase0/inventory.csv` | CSV / 4,485,341 | Original t0 metadata inventory; read-only scan output | CRITICAL |
| `audit/phase0/inventory_t0.csv` | CSV / 4,485,341 | Byte-identical preserved t0 copy | CRITICAL |
| `audit/phase0/inventory_t1.csv` | CSV / 8,365,180 | Later metadata-only snapshot during migration | CRITICAL |
| `audit/phase0/hashes.csv` | CSV / 4,725,416 | t0 selected-file xxh3-128 hashes, hash mode/errors | CRITICAL |
| `audit/phase0/dup_groups.json` | JSON / 2,734,380 | t0 grouped duplicate path lists | CRITICAL |
| `audit/phase0/pdf_probe.jsonl` | JSONL / 1,036,795 | 1,702 stratified PDF probes | CRITICAL |
| `audit/phase0/pdf_unique_pages.jsonl` | JSONL / 767,498 | unique-PDF page census with five-page signals | CRITICAL |
| `audit/phase0/scripts/inventory.py` | Python / 1,052 | `os.scandir`/stat inventory writer | HIGH |
| `audit/phase0/scripts/dedup.py` | Python / 1,556 | xxh3-128 full/partial hash writer | HIGH |
| `audit/phase0/scripts/dedup_report.py` | Python / 3,709 | duplicate statistics, mirror heuristic, JSON writer | HIGH |
| `audit/phase0/scripts/stats.py` | Python / 1,577 | extension, top-level, level-2 and largest-file summaries | HIGH |
| `audit/phase0/scripts/pdf_probe.py` | Python / 2,363 | seeded stratified PDF probe | HIGH |
| `audit/phase0/scripts/pagecount.py` | Python / 1,335 | deduplicated PDF page count and five-page text/math signal | HIGH |
| `audit/phase0/scripts/deep_sample.py` | Python / 2,338 | handpicked document page text dumps and 90-dpi renders | HIGH |
| `audit/phase0/samples/deep_sample.json` | JSON / 1,815 | nine successful sample results, page, span count, character count, TOC | HIGH |
| `audit/phase0/samples/thesis_p22.txt` / `.png` | UTF-8 text / 2,970; PNG / 103,595 | thesis prose/math comparison | HIGH |
| `audit/phase0/samples/dynamics_p48.txt` / `.png` | UTF-8 text / 2,685; PNG / 120,853 | MathType extraction failure, visible red ink | HIGH |
| `audit/phase0/samples/modelling_p34.txt` / `.png` | UTF-8 text / 2,829; PNG / 108,388 | formula/table/plot layout | HIGH |
| `audit/phase0/samples/control_h2_p5.txt` / `.png` | UTF-8 text / 2,426; PNG / 95,263 | MathType-style control equations | HIGH |
| `audit/phase0/samples/fem_p37.txt` / `.png` | UTF-8 text / 2,325; PNG / 65,750 | matrix extraction | HIGH |
| `audit/phase0/samples/numerics_book_p27.txt` / `.png` | UTF-8 text / 2,028; PNG / 78,456 | LaTeX textbook display-math behavior | HIGH |
| `audit/phase0/samples/robotics_dh_p9.txt` / `.png` | UTF-8 text / 2,245; PNG / 133,004 | DH transformation matrix layout | HIGH |
| `audit/phase0/samples/cs_algdat_p4.txt` / `.png` | UTF-8 text / 975; PNG / 113,555 | CS lecture slide text and simple math | HIGH |
| `audit/phase0/samples/control_exam_p11.txt` / `.png` | UTF-8 text / 1,788; PNG / 62,433 | control exam math | HIGH |
| `audit/phase0/samples/scanned_statik_p3.png` | PNG / 79,857 | scanned truss diagrams; **no paired text or JSON entry** | HIGH |
| `.remember/.gitignore` | text / 2 | `*`: ignore plugin-local state | LOW |
| `.remember/.install-marker` | text / 116 | plugin bootstrap marker, mentions `scripts/doctor.sh` | LOW |
| `.remember/logs/hook-errors.log` | log / 3,622 | two initial failed session-end extractions | HIGH |
| `.remember/logs/memory-2026-09-24.log` | log / 11,269 | plugin save/extract/Haiku failure timeline | HIGH |
| `.remember/logs/autonomous/save-115939.log`, `save-121023.log`, `save-121559.log`, `save-121814.log`, `save-122106.log`, `save-122310.log`, `save-122708.log`, `save-122913.log`, `save-123116.log`, `save-123329.log`, `save-123531.log`, `save-124018.log`, `save-124229.log`, `save-124434.log`, `save-124650.log` | 15 logs / 36 each | each contains only a `post-tool save triggered` timestamp; no saved memory | LOW |
| `.remember/logs/autonomous/session-end-115549-2005.log`, `session-end-115550-2053.log` | 2 logs / 37 each | each says `flush started`; parent log shows failure | LOW |
| `.remember/tmp/capture-alive`, `capture-alive.d/7d2ed04e-193e-4591-bf6f-0ae9e849e179` | marker / 36; empty / 0 | session liveness marker and directory entry | LOW |
| `.remember/tmp/case-divergence` | text / 31 | `format=1`, `status=not-applicable` | LOW |
| `.remember/tmp/last-save-ts` | text / 11 | timestamp `1790246812` | LOW |
| `.remember/tmp/last-summary-failure` | text / 43 | failed session marker `7d2ed04e-193e-4591-bf6f-0ae9e849e179:945 1` | MEDIUM |
| `.remember/tmp/post-tool-ran`, `start-context.cache` | empty / 0 each | plugin flags/cache, no knowledge content | LOW |
| `.remember/tmp/save-session.pid` | text / 4 | transient PID `839`, not a current-process assertion | LOW |
| `.remember/tmp/session-slug` | text / 270 | plugin session/project path mapping, status `ok` | MEDIUM |
| `.remember/tmp/start-context.manifest` | text / 612 | configured context sources, including absent project memory files | MEDIUM |

**Environment inventory:** `.venv-audit/pyvenv.cfg` (200 bytes) is the Python environment's primary configuration. Eight `*.dist-info/METADATA` plus eight `INSTALLER` files were inspected via their directory names and installer/direct-url flags; no `direct_url.json` exists. `.venv-audit/Scripts` contains stock venv activation scripts, Python/pip executables, `pymupdf.exe`, and package-provided `vba_extract.py` (2,364 bytes); no project-authored script was evident there. `.venv-audit/.gitignore` is routine venv metadata. The environment has 1,998 files in total; ordinary installed library internals were grouped and not treated as project artifacts.

## 2. What `.remember` actually stored

The folder is operational state for the Claude `remember` plugin version `0.33.0`, **not** a Phase-0 knowledge base. The manifest names `core-memories.md`, `today-2026-09-24.md`, `now.md`, `recent.md`, `archive.md`, and `config.json`, but none exists under `.remember`. No task ID, ADR, corpus count, architectural decision, future-agent instruction, or durable progress record is stored there. The visible project-specific facts are only the project path `D:\AgenticAI\second-brain-rag`, `.remember` path, plugin path under `C:\Users\ammar\.claude\plugins\cache\claude-plugins-official\remember\0.33.0`, and session IDs.

The log sequence: two session-end extractions at 11:55:51–52 fail because no session files are found in `C:\Users\ammar/.claude/projects/d--AgenticAI-second-brain-rag`. Saves at 11:59, 12:10 and 12:16 skip because one human message is below the plugin's three-message threshold. At 12:18 the 41-exchange agentic exception starts a Haiku summary attempt. From 12:18 through 12:46, 12 repeated attempts log `[WinError 2] Das System kann die angegebene Datei nicht finden`; the span is marked for retry. **[INFERENCE]** no successful memory summary was committed in this folder. The visible hook errors do not establish that the whole audit failed; audit datasets plainly exist. Temporary files can be stale and must not be used as execution status. There is no conflict with formal decisions because the missing notes make no claims.

## 3. Dataset schemas, scope and measured findings

| Artifact | Schema / generation | Direct findings and limits |
|---|---|---|
| t0/t1 inventories | `relpath,ext,size,mtime,depth`; `inventory.py` uses `os.scandir`, `stat`, lowercased filename suffix; `mtime` integer epoch seconds; paths relative to `D:\MBI-BRAIN` | t0 39,478 files / 371.093 decimal GB; t1 73,441 / 561.050 GB. No MIME sniffing, readability test, symlink-following, file-content classification, archive expansion, or integrity verification. An `e.stat` error could abort the script; directory-open errors are printed to stderr, not retained in CSV. |
| `hashes.csv` | `relpath,ext,size,hash,mode`; `dedup.py` hashes all listed document types and positive-size size-collision candidates, not all files | 33,768 selected; 33,685 full, 49 partial, 34 errors. `mode=partial` uses file size and 4 MiB reads at head/middle/tail for non-documents above 512 MiB; it is a probabilistic equality signal. t0 inventory may have changed before hashing. xxh3-128 is the audit hash, **not** the planned production BLAKE3-256 content ID. |
| `dup_groups.json` | JSON array of arrays of relative paths; `dedup_report.py` groups `(hash,size)` | 8,220 groups, 18,732 redundant path entries; most groups have 2–4 paths, maximum group size 73. The JSON omits hash, mode and size, requiring `hashes.csv` to audit certainty. No normalized-text, perceptual, or revision matching. |
| `pdf_probe.jsonl` | Per-PDF `relpath,size,pages,encrypted,meta,toc,sampled,chars_per_page,notext_pages,imgs,draws_first8,annots,landscape,math_fonts,nfonts,fonts_top` or `error` | 1,702 sampled, 1,688 successful, 14 errors; 248/1,688 (14.7%) wholly textless in sampled first pages. Claude's **15.3%** figure uses a different or rounded rule; exact denominator/rule is not in the report. 910 successful rows have math-font matches; 182 have annotations; 503 are landscape. Font hits are an upper-bound math signal: `Symbol` may be bullets. Textless means `<30` stripped characters, not OCR diagnosis. `imgs` counts embedded references, not semantic figures; drawings count only first eight pages. |
| `pdf_unique_pages.jsonl` | `hash,relpath,size,pages,probe_pages,notext,mathpages` or `error`; one chosen path per unique full-hash PDF pair excluding `._*` files; probes first, quarter, half, three-quarter, last page | 3,555 rows; 3,339 opened, 217 errors, 328,418 pages. Only 12,648 pages were probed for text/math signals. 217 errors include 215 `no such file` paths, one empty file, and one `document closed or encrypted`; error messages may be truncated. The 11-pair gap from 3,566 is explained by the script's `._*` exclusion. |
| `samples/deep_sample.json` | keyed sample ID to `page,pages,math_spans,chars,toc`; `deep_sample.py` hand-selects ten paths, picks highest math-font span count in first 60 pages or page 4, renders at 90 dpi | Nine entries exist. The attempted `scanned_exam` is absent; no error log was preserved here. `scanned_statik_p3.png` was produced outside this script or a different run: it is not in `DOCS`, JSON, or paired with text. Representative examples, **not** a statistical sample. |

The direct t0 extension counts are `.pdf` 8,614, `.jpg` 7,862, `.png` 3,721, `.mat` 2,807, `.java` 2,592, `.m` 1,869, `.class` 1,404, `.mp4` 899, `.bmp` 856, `.txt` 734, `.fig` 658, `.xlsx` 449, `.zip` 367, `.doc` 174, `.docx` 164, `.xls` 129, `.avi` 107, `.exe` 73 and 777 extensionless files; 171 zero-byte files. At t1: `.pdf` 13,552, `.html` 12,277, `.java` 7,180, `.mp4` 1,595, `.zip` 755, `.doc` 355, `.docx` 221, and 1,647 extensionless files; 241 zero-byte files. The sudden `.html` increase is a major t1 classification/ingestion issue not discussed in the t0-focused audit. Extensions are filenames, not confirmed file formats.

Top-level t0 counts: `BachelorArbeit` 15,269; `Mechanical` 11,962; `Information` 10,623; `books` 1,604; `Betriebslehre` 18; two root PDF files. At t1: `Information` 40,978; `Mechanical` 15,280; `BachelorArbeit` 15,269; `books` 1,604; `Betriebslehre` 308; two root PDF files. **[CLAUDE]** Newly added areas include `Information\Informatikx` (29,375 files, 2,406 PDFs, 107.7 GB), `Betriebslehre\Managment` and `Mechanical\Automatisierungslabor`. These names are source spellings, not corrections.

**[CLAUDE]** t0 format classes: ~28.5 GB documents, ~300 GB video/audio; MP4 alone 283 GB, ZIP 26.4 GB. Archives are 367 ZIP plus 30 RAR; only 110/397 reportedly have a same-name extracted sibling. Images remain numerous (~12.8k), code and MATLAB data exist, and ANSYS/Eclipse/BlueJ scratch and executables are mixed with study material. The counts of 5,951 and 10,559 directories containing files, max depth 14, 5,874 paths with umlauts, 228 CP437-mojibake paths, 128 mirrored directory pairs and 253 cross-top-level duplicate groups are **Claude's derived results**, with source data and some script logic preserved but no serialized output tables for independent one-to-one review in this handoff.

**[CLAUDE]** Unique PDF blobs: 8,614 PDF paths to 3,566 unique full-hash blobs; 58.6% duplicate path copies; unique PDF bytes 17.5 GB. DOCX 164→138, PPTX 34→27, DOC 174→140, PPT 16→9. Video files 1,041→~617 unique and ~165 GB, partly based on partial hashes. Overall redundant copies are claimed as 163.7 GB, dominated by MP4 127 GB, ZIP 14 GB, PDF 9.6 GB. Because partial groups are included, use “duplicate candidates” for those large non-document files until fully hashed.

**[CLAUDE]** Probe percentiles for PDF length p10/25/50/75/90/99/max: 1/2/8/37/142/816/2,281. 303/1,688 (18%) have bookmarks. 874 (52%) have metadata title, 1,044 (62%) author; titles may be junk. Producer categories are other/unknown 440, LaTeX 378, Word 281, PowerPoint 269, publisher 179, no metadata 53, scanner/OCR 34, LibreOffice 23, handwriting apps 23. The sampled producer classes do not prove genre or language distribution corpus-wide.

**[CLAUDE]** Page census estimate: ~25,700 textless pages and ~65,700 math-font pages, both extrapolations from five-page probes; 501 long PDFs (≥200 pages) contain 264,189 pages (~80% of reported total), while 2,373 short PDFs (≤40 pages) contain 21,423 pages. These counts are snapshot-t0 claims and should be recomputed from raw rows before allocating compute. t1's “450–550k unique pages” is an extrapolation, not a page census.

## 4. Audit method and sample design

`inventory.py` traverses `D:\MBI-BRAIN` without following directory symlinks and records metadata. `stats.py` reads t0 inventory for top extensions, sizes, top-level/level-2 distribution and largest 30. `dedup.py` builds a size-frequency table; it fully hashes document extensions (`.pdf`, `.ppt`, `.pptx`, `.ppsx`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.txt`, `.md`, `.tex`, `.odt`, `.rtf`, `.csv`) and files of a size shared by another nonempty file. It uses xxh3-128, 8 MiB streaming chunks for full hashing, and a size plus head/middle/tail sample for non-document files over 512 MiB. `dedup_report.py` computes group statistics and mirrored folders from hashed blob sets; mirror rule is ≥90% overlap in both directions, ≥20 blobs and maximal pairs among prefixes to depth five. This is heuristic structural overlap, not a filesystem equality proof. No near-duplicate method ran.

`pdf_probe.py` groups PDFs by the first three path components, seeds random sampling with `42`, selects up to **12 per group**, and inspects up to the **first 25 pages** of each chosen PDF with PyMuPDF. This weights groups rather than documents and may overrepresent small folders. It tests `<30` characters for textless pages, matches a regular expression of math font names, gets image references and drawings, counts annotation objects, checks first-page landscape and PDF metadata. `pagecount.py` deduplicates by `(xxh3-128,size)` and selects the first observed path; if that path moved, it does not try another duplicate path. Its five-page probe is not a full-page OCR census. `deep_sample.py` hand-picks documents and chooses a math-rich page from the first 60; sample results cannot establish prevalence. No script in this folder does MIME/magic detection, archive unpacking, encoding repair, Office OMML census, DOCX/PPTX twin matching, language identification, corruption validation across all files, OCR, or formula recognition. Those claims are planning observations or analyses not fully reproducible from these seven scripts alone.

`audit/phase0/README.md` records a sequence: `python scripts/inventory.py [out.csv]`, `python scripts/dedup.py` (approximately 20 minutes), then `.venv-audit/Scripts/python scripts/pdf_probe.py`. The scripts themselves use hard-coded Windows paths. The README does not record exact commands for `stats.py`, `dedup_report.py`, `pagecount.py`, `deep_sample.py`, the t1 capture, or the separate `scanned_statik_p3.png`; outputs show they or equivalent steps were run. Re-running the scripts now would write/overwrite audit files and observe a new corpus state; this review did not do that.

**Representative sample IDs and reasons:** `thesis_p22` (73-page Word-produced thesis; flattened native equations); `dynamics_p48` (130-page MathType script and visible red handwritten derivation); `modelling_p34` (98-page formula tables/plots); `control_h2_p5` (8-page broken MathType); `fem_p37` (75-page matrix brackets); `numerics_book_p27` (426-page LaTeX textbook; display-math ordering); `robotics_dh_p9` (10-page transformation matrix); `cs_algdat_p4` (32-page PowerPoint-style slide, simple inline math); `control_exam_p11` (12-page exam); `scanned_statik_p3` (image-only truss diagrams, no paired text). The paired text files contain `SOURCE`, `PAGE`, `MATH_SPANS` headers; rendering and text were both inspected for the dynamics example, and the statics image was inspected. The rendered dynamics page visibly contains red annotations while the text dump does not encode them. The statics image carries truss geometry and labels that a text-only pipeline cannot recover. The deep sample does not itself include DOCX/PPTX/OMML files, old Office binaries, or a controlled duplicate/twin comparison. The proposed `scanned_exam` path in `deep_sample.py` produced no output.

**[CLAUDE]** A separate Office observation reports OMML in 32/161 DOCX, 18/34 PPTX and 1 PPSX; thesis DOCX has 592 equations, Praxisphase report 499, and exercise solutions 571. No raw Office-census artifact or script is in `audit`, so treat these as reported findings awaiting reproduction. The denominator 161 DOCX differs from t0's 164, possibly because three could not be opened; reason undocumented. Claude also reports text-PDF, scanned, annotations, German/English, MathType, and DOCX/PPTX/PDF twins; the samples demonstrate examples but do not measure corpus-wide twin or language rates.

## 5. Reproducibility-relevant `.venv-audit` environment

**[RAW]** `pyvenv.cfg`: `home = C:\Python314`, `include-system-site-packages = false`, `version = 3.14.7`, `executable = C:\Python314\python.exe`, and `command = C:\Python314\python.exe -m venv D:\AgenticAI\second-brain-rag\.venv-audit`. Installed distributions shown by local `.dist-info`: `pymupdf 1.28.2` (PDF probe, pages, renders), `python-docx 1.2.0`, `python-pptx 1.0.2`, `lxml 6.1.3`, `Pillow 12.3.0`, `XlsxWriter 3.2.9`, `typing_extensions 4.16.0`, `pip 26.2.1`. Each reports installer `pip`; none has `direct_url.json`, so no editable/local install is evident. No OCR, math-recognition, deep-learning, MIME-detection, dataframe, archive or hashing package is installed here. **Important discrepancy:** the audit hash script imports `xxhash`, but `xxhash` is not in `.venv-audit`; the README uses system `python` for that step. Thus the venv alone cannot reproduce all audit scripts. Python standard-library `csv`, `json`, `collections`, `os`, `random`, `re`, `time` also matter. No `requirements.txt`/lockfile in the audit folder pins this environment.

## 6. Corpus understanding and architectural implications

The t0 corpus is a heterogeneous university engineering/computing archive, not merely PDFs. **[CLAUDE]** `Mechanical` has 21 subject folders and most video bytes; `Information` includes mirrored CS course trees; `BachelorArbeit` includes thesis, MATLAB, Praxisphase and ROBWork; `books` contains programming/numerics/web texts. Names such as `Reg1`, `RGT`, `MSR2`, `ModellbTSys`, `GrdInf`, `AlgDat`, `BS1`, `MO`, `KONleh`, `KonstGrd`, `WISs`, `SMS`, `IRO` require a curated abbreviation mapping. The two root PDFs are `curriculum_mbi_ws2019.pdf` and `MBI-WS2019-Modulhandbuch.pdf` (taxonomy seeds). Genre cues include `Klausuren`, `Lösung`, `Skript`, `Übung`, `Aufgabenblatt`, `Labor`, `Versuch`; reported t0 PDF filename hits: exercises 1,707; exams 1,116; lecture/script 811; solution 796; lab 180. Such filename hits can overlap and are not validated genre labels. German technical text is visible and English documents are reported, but no measured language distribution exists.

| Observed corpus fact → architectural consequence | Evidence status and plan link |
|---|---|
| Mutable paths (+34,638 new, 675 missing) → content identity with path observations and incremental change detection | [RAW] path sets; ADR-003, T-P2-03. “All missing paths moved” is unproven. |
| 8,220 hash groups; 8,614 PDFs vs claimed 3,566 blobs → exact dedup without deleting source files | [RAW]/[CLAUDE]; ADR-003/031. Production BLAKE3 differs from audit xxh3. |
| Read-only corpus requirement → SourceFS guard and derived output elsewhere | [CLAUDE/formal hard constraint], ADR-002, T-P1-03; not itself a statistical discovery. |
| Broken math text in paired sample dumps/renders → first-class formula extraction and uncertainty/provenance | [RAW sample], ADR-009/011/013, SPIKE-MATH. Specific recognizer remains unchosen. |
| Reported thesis DOCX OMML count → OMML-first twin fusion | [CLAUDE], ADR-009, SPIKE-OMML; exact count not independently stored here. |
| Textless sampled PDFs and visual statics trusses → OCR tiers plus figure extraction | [RAW sample/probe], ADR-007/010, SPIKE-OCR/FIGURE. |
| Annotated dynamics page → preserve annotated variants and `USER_ANNOTATION` provenance | [RAW render], ADR-013/032; annotations need not be PDF annotation objects. |
| Heavy textbook page tail, CPU-only machine → value-ranked waves, lazy upgrades, resumable jobs | [CLAUDE page/hardware report], ADR-007, T-P3-09; speed/cost requires measured spike. |
| Folder abbreviations, bilingual terminology, equation references → taxonomy, hybrid lexical/semantic and separate math retrieval | [CLAUDE] organizational observations; ADR-016/017 and SPIKE-HYBRID/MATHRET are proposed. The audit does not prove retrieval effectiveness. |
| Equation, code, section and figure labels → Knowledge Units with stable locators; DocIR and graph candidates | [CLAUDE]/[INFERENCE], ADR-011/012; graph and Graphify usefulness remain SPIKE-GRAPH/GRAPHIFY. |
| Mixed personal and third-party material → sensitivity gate and provider approval | [CLAUDE] path/content observation, ADR-035; scope/policy Q-I04/Q-B03. |
| User notes must survive rebuilds → independent Obsidian vault and curation ledger | [CLAUDE/formal requirement], ADR-001/014/029/037; vault location Q-B02 open. |

**Hardware report [CLAUDE, not re-probed here]:** Intel Core 7 150U, 10 cores/12 threads; 63.7 GB RAM; Intel integrated graphics, no CUDA GPU; 2 TB Patriot P400L NVMe; D: 977 GB with 377 GB free at t0, C: 714 GB free; system Python 3.14.7. The filesystem free space and machine configuration may since have changed. CPU VLM “30+ seconds/page” is literature/plan reasoning, not a measurement on this machine. No full visual parsing, embedding, retrieval, graph, or agentic pipeline was run.

## 7. Problems and risks, with plan coverage

| Class | Evidence / affected scope | Consequence and existing response |
|---|---|---|
| DATA / STRUCTURE | [RAW] 39,478→73,441 files; 675 t0 paths absent at t1; t1 adds 12,277 `.html` | Moving snapshot invalidates global sizing; Q-B01/T-P2-12 address refresh. t1 HTML source/value classification is not yet addressed explicitly. |
| DUPLICATION | [RAW] 8,220 groups/18,732 redundant entries; 49 partial hashes, and [CLAUDE] 128 mirrors | Duplicate indexing/cost and false “exact” claims for partial matches; ADR-003/031, T-P2-07. Near-duplicates still unmeasured (T-P5-03). |
| EXTRACTION / MATH | [RAW] sample text flattens equations/matrices; [CLAUDE] 53.9% probe math-font signal | Bad formula grounding; ADR-009, SPIKE-MATH/OMML. Font detection has false positives; recognizer quality unknown. |
| OCR / VISUAL | [RAW] 248/1,688 probe successes wholly textless; statics diagram PNG | Text-only indexing misses content; ADR-007/010, SPIKE-OCR/FIGURE. Textless threshold is a heuristic, not scanned-document proof. |
| PROVENANCE | [RAW] red handwritten annotations on dynamics render absent from text dump | Annotated knowledge could disappear in text conversion/dedup; ADR-013/032, provenance locators. |
| COMPUTE / STORAGE | [CLAUDE] 328k pages, 80% in long PDFs, t0 283 GB MP4, D: 377 GB free | Full CPU VLM pass and artifact storage costly; ADR-007/030, SPIKE-COMPUTE, Q-B03. Actual throughput/storage after t1 unknown. |
| PRIVACY | [CLAUDE] grade lists, contracts, personal names in corpus; [RAW] path inventory itself sensitive | External transmission and public artifact upload unsafe; ADR-035, Q-I04/Q-B03, docs/22. This report avoids those names. |
| OPERATIONS | [RAW] 34 hash permission errors, 14 probe errors, 217 page-census errors, 11 unique-PDF rows unaccounted for | Stale paths and incomplete census; reselect alternate duplicate paths, classify errors, rerun after freeze (T-P2-12). |
| OPERATIONS | [RAW] `.remember` failed summaries; no durable notes | Do not rely on plugin memory for Phase-0 state; formal `docs/` and raw audit artifacts are the evidence. |
| UNKNOWN | [RAW] filename suffix inventory only, no full MIME or archive crawl; encrypted page-census error ambiguous | Format, archive contents, corrupt/encrypted counts and unsupported files remain unknown; planned registry/classification/extraction must measure them. |
| RETRIEVAL | [CLAUDE] German abbreviations, cross-filed subjects, mixed book/course genres | Hybrid, math retrieval, taxonomy proposed; no retrieval benchmark result exists. SPIKE-HYBRID/MATHRET/EMBED and T-P2-11. |

## 8. Cross-checks and discrepancies that ChatGPT must retain

1. `inventory.csv`=`inventory_t0.csv` exactly; `inventory_t1.csv` is a different snapshot, not a duplicate with conflicting values. T0 detailed metrics cannot be silently mixed with t1 totals.
2. Formal audit says 3,337 opened unique PDFs / 328,409 pages, while raw `pdf_unique_pages.jsonl` yields 3,339 / 328,418. The 3,555 versus 3,566 row difference is explained by excluding 11 unique `._*` AppleDouble PDF hash pairs. The remaining two-opened-PDF/nine-page prose discrepancy is unresolved. One empty and one encrypted/closed error are present in the raw file.
3. Formal audit says 34 hash errors were moved files; raw error text says `Permission denied`. Movement is plausible for many page-census failures (`no such file`), not proven for the hash failures.
4. Formal “15.3% fully textless” differs from raw `notext_pages == sampled` on successful rows (248/1,688 = 14.7%). This may be a distinct definition; none is documented beyond the script's `<30` characters/page rule.
5. “Exact duplicate” groups can include `mode=partial` for large non-documents. The 163.7 GB redundant-byte claim is therefore partly probabilistic until those groups are fully verified.
6. The README describes PyMuPDF as “1.28”; installed metadata says `1.28.2`. System Python executes hash scripts because `xxhash` is absent from the audit venv. The documented environment is not a complete locked reproduction environment.
7. `deep_sample.py` requests ten documents including `scanned_exam`; nine are in the JSON and paired render/text sets. `scanned_statik_p3.png` is extra with unknown generation command. It should be retained but not attributed to that script.
8. Formal Office OMML numbers, genre counts, CP437 count, hardware and free-space facts have no corresponding script/output under `audit`; retain as **[CLAUDE]** findings until recreated. The audit folder also contains no direct evidence that old Office formats, archives, MIME or language detection were comprehensively inspected.
9. `CLAUDE.md` says “Phase 0 complete,” while execution state and questions still require owner approval. These statements refer to different gates: audit/planning prepared versus plan approved. The snapshot itself is still moving.
10. The user-provided AGENTS.md names `C:\Users\ammar\.claude\brain` as the canonical Brain, while this repo's `CLAUDE.md` says `D:\AgenticAI\My-Knowledge\brain`. This review did not change Brain metadata. The project-specific docs/registry path should be verified against current owner governance before any Brain write; it does not affect the corpus audit statistics.

## CRITICAL CONTEXT FOR CHATGPT

**Verified from artifacts:** t0/t1 file counts and bytes; raw extension distribution; 675 absent and 34,638 added paths; 33,768 hash attempts by mode; 8,220 duplicate groups; 1,702 PDF probes; 3,555 page-census rows and raw page sum; sample text/render failures; audit environment packages; absent `.remember` memory notes. The source is intended to remain read-only. `audit/phase0` itself contains sensitive filenames.

**Plan and gate status:** `docs/35_EXECUTION_STATE.json` marks `T-P0-08` and first implementation task `T-P1-01` `NOT_STARTED`. Q-B01 migration/freeze, Q-B02 vault location, Q-B03 compute/privacy/budget, Q-B04 model access, Q-B05 owner plan approval are open. The plan says Q-B01 blocks final corpus refresh/full ingestion rather than all P1/P2, while Q-B05 blocks implementation. Do not infer owner approval from Claude's “complete” wording. No production RAG code, retrieval benchmark, corpus-wide OCR, math recognizer, graph, embedding, or model gateway was demonstrated by these artifacts.

**Supported strategy:** source immutability, provenance, exact-content identity with path observations, preserving annotation variants, tiered extraction and OMML-first experimentation are motivated by Phase-0 examples and scale. **Decisions still needing spikes:** parser, formula recognizer, OCR, compute throughput, figure detection, embeddings/hybrid/math retrieval, reranker, graph/Graphify and model access (see `docs/34_RESEARCH_AND_SPIKE_REGISTER.md`). A documented planned BLAKE3 content ID is not the xxh3 audit hash. The t1 page load, current disk free space, exact archive contents, file magic types, near-duplicates, encrypted/corrupt totals, language proportions, and PDF/Office twin prevalence are unmeasured here.

## What Claude actually did

Created two metadata inventories; hashed a selected t0 subset; generated duplicate groups and mirror statistics; probed a stratified t0 PDF sample; made a unique-PDF page census; rendered/dumped selected pages; documented corpus findings, architecture, task/ADR/question/spike registers and execution state. The audit was static/read-only toward the source, with derived outputs under the project. The artifacts do not show production RAG implementation or a complete scan of every file's content.

## What Claude learned

The collection expanded sharply during migration, is heterogeneous and heavily duplicated, has math-heavy PDFs with unreliable equation text, has a meaningful textless/scanned subset, carries essential figures and handwritten annotations, contains personal/third-party material, and has a long textbook tail that dominates pages. These are strongest where supported by raw counters and visual/text samples; Office OMML counts and some summary statistics rest on Claude's report without saved extraction data.

## What remains unknown

Final frozen-corpus totals; why formal page totals differ from raw data; exact cause of permission errors; near-duplicate/version/twin prevalence; full MIME and archive-content distribution; full corruption/encryption counts; language shares; textless/math page counts beyond five-page estimates; throughput, quality and cost of candidate parsers/OCR/formula models; approval of plan, vault, compute/privacy policy and model access.

## What should be preserved

Preserve `inventory_t0.csv`, `inventory_t1.csv`, `hashes.csv`, `dup_groups.json`, both PDF JSONL files, sample text/render pairs and `scanned_statik_p3.png`, seven scripts, and `audit/phase0/README.md` as historical evidence. Keep `inventory.csv` to reproduce the exact t0 script input even though it equals `inventory_t0.csv`. Preserve relevant formal docs, especially `docs/03_CORPUS_AUDIT.md`, `24_DECISION_LOG.md`, `25_OPEN_QUESTIONS.md`, `28_TASK_REGISTER.md`, `34_RESEARCH_AND_SPIKE_REGISTER.md`, and `35_EXECUTION_STATE.json`. `.remember` logs are operational diagnostics, not authoritative project decisions.

## What is reproducible

The inventory schema, hash selection/algorithm, duplicate report, stratified PDF probe, page census and nine deep samples are largely described by preserved scripts and data. Exact re-run numbers depend on restoring t0 bytes/paths, Python/system packages (including `xxhash` outside the venv), script order and any undocumented commands. The OMML census, filename repair count, hardware measurements, archive matching and t1 capture command are not fully reproducible from the seven saved scripts. Re-running against today's corpus would be a new snapshot, not a validation of t0.

## Confidence

| Category | Confidence | Reason |
|---|---|---|
| Artifact inventory, schemas, t0/t1 metadata counts | HIGH | Direct file enumeration and CSV reads; t0 copy hash verified. |
| Selected hashes and duplicate grouping | HIGH for stored rows/group counts; MEDIUM for exact redundancy bytes | 49 partial hashes and 34 permission errors limit certainty. |
| Sampled PDF properties and visual examples | HIGH for recorded samples; LOW for corpus-wide extrapolation | First-page windows, folder weighting and handpicked pages. |
| Unique page total | MEDIUM | Raw 328,418 from successful rows; 217 errors and discrepancy with written 328,409. |
| Office/OMML, language, genre, mirrors, hardware | MEDIUM to LOW | Claude reports them, but not every underlying measurement is saved here. |
| `.remember` contents | HIGH | Every file inspected; no substantive memory notes present. |
| Architecture readiness | MEDIUM | Formal gates/ADRs are explicit; technology spikes and owner approvals remain open. |
