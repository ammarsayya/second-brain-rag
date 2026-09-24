# Phase-0 audit artifacts (read-only corpus audit, 2026-09-24)

These are derived, disposable planning artifacts. They are **not** the production registry.
Interpretation: `docs/03_CORPUS_AUDIT.md`.

> Sensitivity: these files contain file paths of personal and third-party documents (grade lists, contracts).
> Keep them local. Never publish them to a public remote (see docs/22_SECURITY_AND_SAFETY.md).

| File | Content |
|---|---|
| `inventory.csv` / `inventory_t0.csv` | t0 metadata inventory (39,478 files): relpath, ext, size, mtime, depth |
| `inventory_t1.csv` | t1 metadata inventory (73,441 files), taken while the owner was still migrating |
| `hashes.csv` | xxh3-128 hashes (t0): all document-type files plus all size-collision files. `mode=partial` = head/mid/tail sample for >512 MB non-documents |
| `dup_groups.json` | Exact duplicate groups (t0) |
| `pdf_probe.jsonl` | Stratified probe of 1,702 PDFs: pages, text presence, fonts, math fonts, producer, images, drawings, annotations |
| `pdf_unique_pages.jsonl` | Page census of every unique PDF blob (t0) |
| `samples/` | Text-layer dumps and 90-dpi renders of representative pages, plus `deep_sample.json` |
| `scripts/` | The exact scripts used (inventory, dedup, stats, pdf_probe, deep_sample, pagecount, dedup_report) |

Reproduce: `python scripts/inventory.py [out.csv]`, then `python scripts/dedup.py` (≈20 min),
then `.venv-audit/Scripts/python scripts/pdf_probe.py`. The `.venv-audit` virtual environment (PyMuPDF 1.28,
python-pptx, python-docx) is audit-only tooling and can be deleted.
