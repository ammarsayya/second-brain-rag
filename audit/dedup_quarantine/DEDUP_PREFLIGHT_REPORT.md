# Exact-duplicate quarantine preflight

Generated 2026-09-24T14:47:33.113872+00:00. Source `D:\MBI-BRAIN`; quarantine `D:\studium_duplicated`. No move had occurred when this report was written.

- Historical full-hash groups considered: **23,512** (all 74,268 group members were checked against t2 size/mtime and freshly SHA-256 hashed where readable).
- Groups with every current member freshly verified as identical: **23,501**; groups failed closed: **11**.
- Groups with at least one planned move: **1,051**; groups without a planned move: **22,450**.
- Files planned: **2,033**; planned bytes: **2,750,581,224** (2.751 decimal GB).
- Retained-file manifest entries: **72,235**, including every group canonical and contextual/policy retained copy.
- Policy/structural exclusions: **62,055** member occurrences; individual proposed-move preflight exceptions: **0**.
- Partial-hash candidates excluded: **27 groups / 49 redundant candidate paths / 196,834,535,900 candidate bytes**. No partial-hash path is in `DEDUP_MOVE_PLAN.csv`.
- Hash/read/metadata error types: **{'PermissionError': 11}**. Details are local in `DEDUP_EXCEPTIONS.csv` and `DEDUP_PREFLIGHT_HASHES.csv`.

Automatic moves are limited to exact-byte groups with an identical basename within the same four-component course-context prefix. `BachelorArbeit` project/thesis trees, software/build classes, images/media/code, HTML/man-page trees, sensitive-name paths and cross-context singleton occurrences remain in place. Full-hash-identical archives are eligible only as archive files, never by member resemblance. No group is reduced below one retained source copy. The retained locations and every planned destination are recorded before execution. Existing destinations, reparse points, length/permission issues and metadata/hash changes fail closed.

Execution may start only if the saved plan is internally consistent and there are no systemic failures. Preflight exceptions remain skipped, not silently repaired.
