# 33 — Test Strategy

## 1. Layers

| Layer | Scope | Tooling | When |
|---|---|---|---|
| Unit | Pure functions (hashing, normalization, LaTeX normalization, anchors, fusion) | pytest, hypothesis (property tests) | Every commit |
| Component | Stages against synthetic fixtures (scan, dedup, archives, extraction adapters, VaultWriter) | pytest + fixture generator (T-P1-13) | Every commit |
| Safety | Source read-only, vault ownership, pending isolation, sensitivity gate | pytest + runtime guards + static checks | Every commit (never skipped) |
| Resilience | Crash-resume, lease expiry, atomic writes, migration upgrade and rollback | Subprocess kill tests, DB copies | Every commit (fast variants), nightly (full) |
| Quality benchmarks | Extraction, retrieval, QA, graph, agentic, gaps, research (20) | `sbr eval` | Per phase and on version bumps (gates) |
| Real-corpus smoke | Read-only scans and small pilot runs on `D:\MBI-BRAIN` | CLI | Manual / nightly |
| Drills | Rebuild, embedding swap, parser upgrade, restore | Scripts + reports | P13, then quarterly |

## 2. Named test suites (referenced by tasks)

| Suite | Asserts |
|---|---|
| TS-SAFE-1 | SourceFS refuses write, rename and delete under source roots |
| TS-SAFE-2 | Static scan: no forbidden filesystem mutators outside the allow-list |
| TS-SAFE-3 | A full pipeline run on fixtures with a monkeypatched FS makes zero mutating calls under source roots; source hashes are unchanged before and after |
| TS-PROV-1 | Writes without activity_id fail |
| TS-PROV-2 | Every derived row has derived_from; locators resolve |
| TS-PROV-3 | EXTERNAL_PENDING content never appears in main indexes or `ask` evidence |
| TS-QUEUE | Killed worker → restart → no lost or duplicate items; version bump re-enqueues exactly the affected subjects |
| TS-MIG | Fresh migrate to head; N-1→N upgrade with backup; rollback |
| TS-CHANGE | Move, rename, modify, delete and re-add scenarios produce the correct events; derived knowledge is never deleted |
| TS-ARCH | Zip-bomb and traversal guards; CP437 names; already-present detection |
| TS-ART | Atomic artifact writes; coexisting versions; no partial artifacts after a crash |
| TS-MATH | LaTeX normalization properties (idempotent, render-preserving); validator behavior; no `verified` below threshold |
| TS-VAULT | Never write `notes/`; edit detection → fork; dirty git tree → abort; user sections preserved in maps |
| TS-ANCHOR | Anchor stability under perturbation; tombstones and successor mappings |
| TS-GROUND | Injected unsupported claims are caught; citations must resolve; basis labels are enforced |
| TS-AGENT | Orchestrator transitions and stop reasons with fake models; budgets respected |
| TS-CONFLICT | Constructed contradictions detected; neither side erased |
| TS-RESEARCH | Durable resume; approval interrupt; rejection path |

## 3. Test data policy

- Synthetic fixtures are generated (LaTeX-compiled PDFs, python-docx/pptx with OMML, images rendered to PDF). They contain no copyrighted corpus content, so they are safe to commit.
- Only regenerating `skript.pdf` needs `pdflatex`. The generator tests reuse the committed, already-compiled `skript.pdf` (`generate(root, latex_pdf=...)` / `--reuse-latex-pdf`) and rebuild every other fixture from scratch. Real compilation is covered by tests marked `pdflatex`. They are reported as skipped when `pdflatex` is not on PATH. With `SBR_REQUIRE_PDFLATEX=1` they run and fail instead. Byte equality with the committed `skript.pdf` is only defined for the pdfTeX build recorded in its `/PTEX.Fullbanner` (currently TeX Live 2023, pdfTeX 1.40.25). The end-to-end test reports a different build as a skip with both banners.
- All stored fixture paths are NFC. Keep `core.precomposeunicode=true` on macOS checkouts so that Git never records NFD duplicates.
- Gold sets reference corpus content by `blob_id` + page. Crops and derived text for gold sets live in `eval/gold/` and are **excluded from any public remote** (22 §4).
- LLM-dependent tests use fake or recorded model responses. Live-model evals are separate commands.

## 4. Definition of done (every implementation task)

The acceptance criteria in 28 are met. Tests are added (safety tests are mandatory for any code touching sources or the vault). `tools/check.ps1` is green.
The docs are updated (decision log if a decision changed; the task status in 28 and 35). `python tools/validate_plan.py` passes.
