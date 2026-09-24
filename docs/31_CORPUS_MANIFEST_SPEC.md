# 31 — Corpus Manifest Specification

The manifest is the registry's authoritative view of what exists in the source roots. It is stored in `registry.sqlite` and exported by `sbr report manifest`.

## 1. Tables (logical; DDL in migrations)

### `source_root`
| Column | Type | Notes |
|---|---|---|
| root_id | TEXT PK | e.g. `mbi` |
| path | TEXT | `D:\MBI-BRAIN` |
| kind | TEXT | `university` \| `external_accepted` \| `personal` \| `quarantine` |
| read_only | INTEGER | must be 1 for all non-quarantine roots |
| added_at | TEXT | ISO timestamp |

### `scan`
scan_id (ULID) · root_id · started_at · finished_at · status · files_seen · bytes_seen · errors · code_version

### `blob`
| Column | Type | Notes |
|---|---|---|
| blob_id | TEXT PK | `b3:` + 64 hex (BLAKE3-256) |
| size | INTEGER | bytes |
| magic_type | TEXT | from content sniffing (`application/pdf` …) |
| format | TEXT | pdf, docx, pptx, ppsx, doc, ppt, xlsx, txt, md, zip, rar, mp4, … |
| knowledge_class | TEXT | document, office, spreadsheet, code, data, media, archive, image, tool_artifact, junk, executable, unknown |
| sensitivity | TEXT | normal, personal, third_party_personal, restricted |
| status | TEXT | active, orphaned (no current observation), excluded |
| first_seen_scan, last_seen_scan | TEXT | scan ids |
| hash_mode | TEXT | `full` (always for documents); `full_lowprio_pending` for media until hashed |
| canonical_obs_id | TEXT | canonical PathObservation (dedup) |

### `path_observation`
obs_id · root_id · relpath (NFC-normalized, original bytes preserved in `relpath_raw`) · display_name (repaired mojibake) ·
blob_id · size · mtime · first_seen_scan · last_seen_scan · state (`present`/`moved`/`deleted`) · in_archive (container obs id or null) ·
folder_tokens (JSON array) · is_mirror_candidate

### `archive_member`
container_blob · member_path · member_name_display · member_size · member_blob (hash of the streamed member) · status
(`already_present`/`extracted_new`/`skipped_limit`/`excluded`) · extracted_path (under `var/archive_extract`)

### `blob_classification`
blob_id · genre · genre_confidence · course_id · course_confidence · language_guess · semester · institution · isbn (from filename) · rules_version

### `blob_relation`
src_blob · dst_blob · type (`twin_candidate`, `twin_of`, `version_of`, `near_duplicate_of`, `contains_text_of`, `annotated_variant_of`, `solution_of`) ·
confidence · evidence (JSON) · producer_activity · status

## 2. Canonical selection (exact duplicates)

Order of preference: (1) curation override; (2) not inside a detected mirror subtree of a preferred folder; (3) folder mapped to a course
consistent with the blob's genre and course; (4) no copy markers (`(1)`, `Kopie`, `Copy`, `_1`); (5) shorter depth; (6) lexicographically stable tiebreak.
All other observations are **aliases**. Nothing is deleted.

## 3. Manifest report contents

Totals (files, bytes, blobs, unique bytes); by knowledge_class and format; by top-level and level-2 folder; duplicates (groups, redundant bytes, mirror pairs);
archives (members total, already present, new extracted); sensitivity counts (names listed only in the local report); genre and course distributions;
PDF page census (after the text tier); changes since the previous scan.

## 4. Change semantics

See 08 §3. Every scan records events in `change_event(scan_id, type, obs_id, blob_id, details)`.
