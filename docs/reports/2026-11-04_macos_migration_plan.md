# macOS Migration: Findings and Plan (2026-11-04)

Status: **plan + non-destructive fixes done; the registry rescan is an owner decision (not executed).**
Host: Apple M5 Max (arm64), 18 cores, 36 GB unified memory, macOS (Darwin 27), 1.2 TB free on the data volume.
Path mapping (global rule): `D:\` → `/Users/ammar/DriveD/`.

## 1. What was measured (read-only on production)

A metadata-only `scan_root` (it never opens files) was run against a **copy** of `var/db/registry.sqlite` in the session
scratchpad, with a macOS config. The production registry was opened only read-only (`mode=ro&immutable=1`) for the
comparison; its SHA-256 prefix before and after is `b3a99c3c2a5503ba`.

| Measure | Value |
|---|---|
| Scan duration / errors | 14 s / 0 |
| Files seen on macOS | 84,439 (35 are Finder `.DS_Store`, already junk by `config/classification.toml`) |
| Bytes seen on macOS | 462.63 GB (t3 registry: 558.75 GB) |
| Registry paths seen unchanged | 45,811 |
| Registry paths with **mtime-only** change | 37,856, all with \|Δ\| of tens of ns, **no size change** |
| Registry paths **absent** on macOS | 213 (96.2 GB) |
| ... of which content survives at another path | 27 |
| ... of which content is absent everywhere | 186 paths, 73.5 GB: 58 `.mp4`, 59 `.pdf`, 15 `.png`, 8 `.zip`, junk |
| ... of those, never hashed even on Windows | 96 (the known 72 `PermissionError` + 24 `FileNotFoundError`) |
| Active blobs with no surviving path | 9 (none referenced by `eval/`, `curation/` or tests) |
| New paths on macOS | 772 (0.10 GB; 528 `.png`, 220 `.jpg`, mostly under `Mechanical`) |
| Hash jobs a rescan would enqueue | 38,628 |

### Interpretation
- **mtime drift is a precision artifact.** NTFS stores 100 ns ticks; the copy rounded them. Change detection compares
  `(size, mtime_ns)` exactly, so a rescan re-hashes those 37,856 files. That is acceptable: it is also a free
  copy-integrity check. No tolerance was added to `scan` (it would weaken change detection for a one-off migration).
- **The macOS corpus is missing ~73.5 GB of unique content**, mostly lecture videos and 59 PDFs (33 of the hashed
  ones are `excluded`, 2 `active`). Either the migration did not copy them or they were dropped on purpose. Only the
  owner can say which; nothing in this repo depends on them.
- **The registry stores `source_root.path = 'D:\MBI-BRAIN'`.** A scan with the macOS config rewrites it (the copy now
  says `/Users/ammar/DriveD/MBI-BRAIN`). All relpaths stay in the canonical backslash form, so ids, dedup, curation
  globs and `PureWindowsPath` helpers keep working.

## 2. Fixed in this session (non-destructive, tested)

| Problem | Fix | Test |
|---|---|---|
| Governor read macOS `ru_maxrss` (bytes) as KiB: a 50 MB process looked like ~50 GB, so the default 40 GB ceiling refused every worker | `_maxrss_to_gb()` uses the platform unit | `tests/jobs/test_governor.py::test_peak_rss_units_follow_the_platform` |
| Process priority was Windows-only | POSIX niceness (below_normal = 10, idle = 19), never raised | `test_posix_priority_only_ever_lowers_the_process_priority` |
| `tools/check.ps1` needs PowerShell | `tools/check.py` runs the same six steps through `uv run --frozen` | run: CHECK GREEN |
| Config only had Windows paths | `config/sbr.macos.example.toml` (tracked; `max_ram_gb = 24` for 36 GB) | `tests/test_config.py::test_macos_example_config_is_valid_and_keeps_the_same_safety_settings` |
| `audit_crossrefs.py` crashed on a `docs/` subdirectory | recurses into subdirectories | run: CROSSREFS CLEAN |

The local, git-ignored `config/sbr.toml` was **not** changed: pointing it at macOS paths would let `sbr scan` rewrite
the production registry by accident.

## 3. Still missing on this host

| Tool | Needed by | Status |
|---|---|---|
| pandoc | T-P3-07 pandoc pass, `select_gold_math_sample.py` | absent; `brew install pandoc` is a user-level choice (no system-wide installs were made) |
| pdflatex (MacTeX/TeX Live) | 5 skipped fixture tests | absent; exact fixture bytes need TeX Live 2023 |
| LibreOffice | possible PPTX→DOCX/PDF route for T-P3-07 | absent |
| PowerShell | `check.ps1` only | not needed any more (`check.py`) |
| Tesseract 5.5.3 | T-P3-08 | present |

## 4. Migration plan (owner-gated steps marked)

1. **Owner:** confirm whether the 186 missing paths (73.5 GB, mostly videos) should be copied from the Windows drive
   or are intentionally dropped.
2. **Owner (registry write):** authorise the macOS rescan. Procedure: back up `var/db/registry.sqlite`
   (`sbr` backup, docs/39), `cp config/sbr.macos.example.toml config/sbr.toml`, then `sbr scan` → `sbr hash` →
   `sbr changes` → `sbr classify` → `sbr sensitivity` (now rules version 2) → `sbr archives` → `sbr dedup` →
   `sbr twins` → `sbr genre` → `sbr courses` → `sbr names`.
   Expected: 38,628 hash jobs (~462 GB read), 213 paths marked missing, 772 new.
3. After the rescan: re-run `tools/validate_plan.py`, the t3→t4 comparison, and regenerate the spike reports that
   cite blob counts.
4. Optional host tools: pandoc, LibreOffice and MacTeX as user installs (Homebrew), if the owner wants those spike
   paths re-run on macOS.
