# Exact-duplicate quarantine (t2 to t3)

## Objective

On 2026-09-24, move a conservative subset of proven whole-file exact copies from `D:\MBI-BRAIN` to `D:\studium_duplicated`, preserving each original relative path and a source copy for every moved content group. This was a reversible quarantine, with no deletion. The t2 audit and both `CODEX_AUDIT_HANDOFF*.md` files remain historical pre-quarantine evidence. t3 is the post-quarantine source baseline. No RAG implementation or ingestion began.

## Evidence used

- `CODEX_AUDIT_HANDOFF_T2.md` and `audit/phase0/t2/{inventory_t2.csv,hashes_t2.csv,identity_t2.csv,dedup_t2_summary.json,dup_groups_exact_t2.json,dup_groups_candidate_partial_t2.json}`; the generating t2 scripts were reviewed before the move.
- `audit/dedup_quarantine/DEDUP_PREFLIGHT_HASHES.csv` records a fresh SHA-256 result or exception for each of the 74,268 members of the 23,512 historical full-hash groups. The t2 xxh3-128 hash identified candidates; it did not authorize execution by itself.
- `audit/dedup_quarantine/{DEDUP_MOVE_PLAN.csv,DEDUP_KEEP_MANIFEST.csv,DEDUP_EXCEPTIONS.csv,DEDUP_PREFLIGHT_REPORT.md,DEDUP_EXECUTION_STATE.json,DEDUP_ROLLBACK.csv,DEDUP_EVENTS.jsonl}` record the decision, execution and recovery trail. These local manifests contain source paths and should be handled as owner data.
- `audit/phase0/t3/{inventory_t3.csv,stats_t3.json,t2_to_t3_comparison.json,quarantine_summary.json}` and `audit/dedup_quarantine/inventory_quarantine.csv` record the final re-inventory and reconciliation.

## Exact-duplicate definition

Only files within a t2 **full-content** xxh3-128 exact group were considered. Every group member had its current size and integer mtime checked against t2 and its full current bytes hashed with SHA-256. Any missing, unreadable, changed or differing member failed the whole group closed. Immediately before each move, the selected source and retained canonical source were SHA-256 checked again. The destination and canonical source were then hashed after the move. A shared filename, partial hash, document similarity, or archive-member resemblance was insufficient.

## Canonical-selection policy

Automatic moves were limited to eligible document/archive file extensions where paths had the same first four course-context components and identical basename. Within each such bucket, deterministic semantic-path and historical-identity ranking selected a retained copy. All other meaningful course-context copies stayed at their original paths and are listed in `DEDUP_KEEP_MANIFEST.csv`. This preserves taxonomy and avoids reducing a project or reference tree file by file. At least one source copy remains for each moved group; 1,051 groups had moves and 1,444 distinct canonical paths were reverified during final verification. The keep manifest has 72,235 retained path entries across all exact groups.

## Preflight results

| Measure | Result |
|---|---:|
| Historical full-hash groups considered | 23,512 |
| Current groups freshly verified identical | 23,501 |
| Groups failed closed | 11 |
| Groups with planned moves | 1,051 |
| Groups without planned moves | 22,450 |
| Files planned | 2,033 |
| Bytes planned | 2,750,581,224 |
| Policy/structural retained member occurrences | 62,055 |
| Individual move-path preflight exceptions | 0 |

All planned source and canonical paths existed; planned destinations were absent and unique; no planned path overlapped a t2 partial-hash path. Destination path length, reparse components, accessible permissions and same-volume roots were checked. The quarantine was empty before execution. The plan, keep/exception manifests, rollback CSV and state file were saved before the first move.

## Execution results

The script `audit/dedup_quarantine/quarantine_duplicates.py` moved individual files by same-volume rename in batches of at most 500. It never overwrote a destination. Every successful move had a full destination hash verification and a rollback CSV row. Execution completed with **2,033 moved**, **2,750,581,224 bytes moved**, **2,033 verified**, **0 execution skips**, **0 failed moves**, and **0 automatic restorations**. Four checkpoints were recorded.

During the third batch, Windows briefly denied atomic replacement of `DEDUP_ROLLBACK.csv`. Execution stopped. Reconciliation found 1,363 quarantine files, 1,362 committed rollback rows, and a complete temporary rollback CSV covering all 1,363. No source/destination pair was simultaneously present or absent. After bounded retry handling was added, the resumable executor verified existing destinations, completed their journal records, and finished the remaining moves. The final rollback CSV has 2,033 unique records, one for every moved file.

## Exceptions

Eleven full-hash groups failed closed because of `PermissionError: [Errno 13] Permission denied` on a member in `Mechanical`. None entered the move plan. Their group and member details are in `DEDUP_EXCEPTIONS.csv`; no source contents were opened for review. These were isolated preflight exceptions, not execution failures. Existing-destination collisions, path-length problems, hash mismatches and individual move-path permission exceptions were zero for planned paths. The report does not claim the excluded groups are currently identical.

## Project/reference-tree exclusions

The 62,055 policy/structural retained occurrences comprise 27,376 software/media/image or unsupported-class paths, 24,517 HTML/reference-tree paths, 10,101 project/thesis-tree paths, 33 AppleDouble/macOS sidecars and 28 sensitive-name paths. This selection deliberately leaves software/build structures and complete HTML/man-page reference trees intact. Archives were eligible only when the archive file itself was a fully verified exact duplicate; extracted-member resemblance did not authorize a move. Sensitive-name paths remained under their existing location and access policy.

## Verification

`audit/dedup_quarantine/finalize_quarantine.py` rehashed all 2,033 quarantine destinations and their canonical source paths, confirmed sizes, matched 2,033 rollback records, and reconciled source and quarantine path sets and bytes. It reported `postverification: PASS`. The source lost exactly the 2,033 planned moved paths and 2,750,581,224 planned bytes, with **zero unexpected added or missing paths**. The quarantine contains exactly those 2,033 paths and bytes. Every moved group retained a verified canonical copy. No source file was deleted; the source changes were recorded moves. The t2 historical artifacts were not overwritten.

## Rollback procedure

`audit/dedup_quarantine/restore_quarantined_duplicates.py` is a separate restore tool. It is dry-run by default and requires `--execute` plus exactly one of `--file <source-relative path>`, `--group <group ID>`, `--subtree <source-relative directory>`, or `--all` to restore. It reads `DEDUP_ROLLBACK.csv`, verifies the quarantine SHA-256 before restoring, never overwrites an occupied original path, verifies the restored SHA-256, and logs operations. **No restoration was run as part of this quarantine.** Review the selected dry run and ledger before an authorized future restoration.

## t2 → t3 comparison

| Baseline | Source files | Source bytes | PDF paths |
|---|---:|---:|---:|
| t2, before quarantine | 85,913 | 561,502,988,849 | see t2 audit |
| t3, after quarantine | 83,880 | 558,752,407,625 | 11,757 |
| Intentional moved difference | 2,033 | 2,750,581,224 | — |

The t3 inventory includes extension and top-level distributions in `stats_t3.json`. `t2_to_t3_comparison.json` records zero unexpected path additions or omissions. The 48,723 remaining exact redundant paths are measurable by applying t2 full-hash group identities to retained paths; this is a historical-identity count, **not** a fresh full-corpus t3 rehash.

## Remaining duplicate categories

The following remain untouched: **partial-hash candidates** (27 groups, 49 candidate redundant paths, 196,834,535,900 candidate bytes), **near duplicates**, **semantic duplicates**, **PDF/Office twins**, **archive-member duplicates**, and **presentation build steps**. Contextual and structural exact copies also remain where automatic removal would risk provenance or functionality. The 48,723 remaining exact redundant paths need separate review if further cleanup is desired. No approval of T-P0-08 or Phase 1 work is implied by this operation.
