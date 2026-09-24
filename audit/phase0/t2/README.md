# T2 re-audit artifacts (2026-09-24, read-only)

The t2 snapshot is the corpus after the owner finished migrating and reorganizing it. The interpretation is in `docs/37_T2_CORPUS_REAUDIT.md`.
The historical t0/t1 artifacts in `audit/phase0/` are untouched.

> Sensitivity: the inventories, identity table and censuses contain paths of personal documents (identity documents, CVs, grade lists).
> Local only. Never publish.

**Environment.** Audit hashing and PDF work ran in `.venv-audit` (Python 3.14.7). The pinned package list is in `requirements-audit-venv.txt`;
`xxhash` is now installed in the venv, which fixes the t0 reproducibility gap. The system `python` (3.14.7, stdlib only) ran the metadata-only scripts.
The audit hash is **xxh3-128**. It is not the planned production BLAKE3-256 content id.

| Artifact | Produced by | Content | Scope |
|---|---|---|---|
| `inventory_t2.csv` | `scripts/inventory.py` | T2 CURRENT CORPUS inventory taken 14:04:04: relpath, ext, size, mtime, depth | FULL CORPUS |
| `inventory_t2b.csv`, `inventory_t2c.csv` | `scripts/inventory.py` | Stability snapshots at 14:21:33 and 14:49:27 | FULL CORPUS |
| `logs/stability_t2_vs_t2b.txt`, `logs/stability_t2_vs_t2c.txt` | `scripts/compare_inventories.py` | 0 added / 0 removed / 0 changed | FULL CORPUS |
| `logs/compare_t0_t1.txt`, `compare_t1_t2.txt`, `compare_t0_t2.txt` | `scripts/compare_inventories.py` | Pairwise path diffs | FULL CORPUS (metadata) |
| `stats_t2.json` | `scripts/stats_t2.py` | Totals, extensions, top-level, level-2, largest files and dirs | FULL CORPUS |
| `hashes_t2.csv` | `scripts/hash_t2.py` | xxh3-128 of all document/web types and all size-collision files (80,264 rows): mode full/partial/err, source computed/cache_t0, verbatim error | FULL CORPUS (in scope) |
| `identity_t2.csv`, `identity_t2_summary.json` | `scripts/classify_identity_t2.py` | Per-file lineage category A/B_exact/B_probable/C/D/E | FULL CORPUS |
| `logs/removed_t0_fate.txt` | `scripts/removed_t0_fate.py` | Fate of the 675 t0 paths absent later | FULL CORPUS |
| `dedup_t2_summary.json`, `dup_groups_exact_t2.json`, `dup_groups_candidate_partial_t2.json` | `scripts/dedup_report_t2.py` | Exact (full-hash) groups vs probabilistic candidate groups; mirror pairs | FULL CORPUS |
| `pdf_census_t2.jsonl`, `pdf_census_t2_meta.json`, `pdf_census_t2_summary.json` | `scripts/pdf_census_t2.py`, `scripts/pdf_summary_t2.py` | One row per unique PDF: pages (FULL), encryption, errors, landscape, 5-probe-page signals (SAMPLE within each doc), t0 coverage | FULL CORPUS (unique PDFs) |
| `pdf_probe_new_t2.jsonl` | `scripts/pdf_probe_new_t2.py` | 25-page deep probe of 293 PDFs new since t0 (≤8 per level-3 group, seed 42) | SAMPLE |
| `build_steps_t2.jsonl` | `scripts/build_steps_t2.py` | Presentation build-step pages in the first 25 pages of every landscape unique PDF | FULL (slide-like PDFs), whole-doc EXTRAPOLATION |
| `office_census_t2.jsonl`, `office_census_t2_summary.json` | `scripts/office_census_t2.py`, `scripts/office_summary_t2.py` | OMML (`<m:oMath>`, `<m:oMathPara>`), Equation 3.0/MathType OLE in OOXML; byte signatures in legacy DOC/PPT/XLS | FULL CORPUS (Office files) |
| `html_census_t2.jsonl` | `scripts/html_census_t2.py` | Generator class and title of every HTML file (first 4 KiB) | FULL CORPUS (HTML) |
| `archive_census_t2.jsonl` | `scripts/archive_census_t2.py` | ZIP central directories: members, extraction status by (name, size); RAR listed only | FULL CORPUS (archives) |
| `org_junk_t2.json` | `scripts/org_junk_t2.py` | Mojibake, junk, tool noise, code and media counts, level-3 folders | FULL CORPUS (metadata) |
| `media_sensitive_t2.json` | `scripts/media_sensitive_t2.py` | Video uniqueness; sensitive filename signals (counts only) | FULL CORPUS |
| `samples/old_sample_recheck_t2.csv` | `scripts/sample_recheck_t2.py` | Fate of the Phase-0 deep samples | SAMPLE |
| `samples/*.png|*.txt`, `samples/new_samples_t2.json` | `scripts/render_new_samples_t2.py` | New-content renders (Ckurs, Math 1 build deck, Festigkeitslehre, BWL, English) | SAMPLE |
| `scripts/area_presence.py` | — | Presence of Ckurs, English, Information\C and root files per snapshot | FULL (metadata) |
| `logs/*` | — | Run logs, snapshot times, hash log | — |
