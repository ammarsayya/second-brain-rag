# 29 — Dependency Map

The task-level dependencies in `28_TASK_REGISTER.md` are authoritative. This document gives the structure and the generated listing.
`python tools/validate_plan.py` checks existence, acyclicity and phase ordering.

## 1. Capability dependency chain (why the order is what it is)

```
read-only guard + ids + provenance + job queue (P1)
    → registry: scan → hash → classify → exact dedup → twins/genre/course (P2)
        → gold sample selection (needs canonical blobs + genres) (P3)
            → extraction harness → SPIKE-PARSER / SPIKE-MATH / SPIKE-OMML / SPIKE-OCR / SPIKE-FIGURE
                → SPIKE-COMPUTE → extraction stack decision (T-P3-11)  ◄── owner compute policy (Q-B03)
                    → text tier → triage → OCR / math / figure tiers → twin fusion → structure (P4)
                        → normalized Markdown + VaultWriter (◄── vault location Q-B02) → pilot W0
                            → KU segmentation → anchors / symbols / near-dedup / topics (P5)
                                → retrieval gold set → harness → chunk views
                                    → SPIKE-EMBED + SPIKE-HYBRID → SPIKE-CHUNK → indexes → fusion → SPIKE-RERANK → evidence packs (P6)
                                        → model gateway (◄── SPIKE-MODELGW ◄── Q-B04) → baseline grounded QA + validator (P7)
                                            → graph (P8) ─────────────┐
                                            → SPIKE-AGENTFW → orchestrator (P9) ─→ agentic eval
                                                → maps / AI notes / user notes (P10) → gap analysis (P11) → research + approval (P12)
full-corpus waves W1–W3 (P13) run in the background after the pilot (P4) and the compute policy (P3), feeding P5–P12 with more material.
```

## 2. External blockers (owner decisions)

| Blocker | Unblocks |
|---|---|
| Q-B05 plan approval | T-P0-08 (after T-P0-09 t2 re-audit, DONE) → everything |
| Q-B01 corpus frozen (recommended CLOSE, pending owner; docs/37 §24) | T-P2-12 → T-P13-01 |
| Q-B02 vault location | T-P4-13 (VaultWriter) |
| Q-B03 compute/privacy policy | **Answered 2026-11-04: local-only (ADR-039).** Still shapes T-P3-09 → T-P3-11 → P4 tiers; T-P13-01 |
| Q-B04 OpenCode model access | **Answered 2026-11-04 (architecture, ADR-040).** T-P7-02 stays blocked on credentials/activation; T-P7-01 no longer waits for it (mock/local backends only) |

## 3. Parallelizable streams

- **Stream A (critical):** P1 → P2 → P3 → P4 → P5 → P6 → P7.
- **Stream B (early, independent):** T-P7-02 SPIKE-MODELGW right after approval; T-P7-03 answer schema after T-P1-05.
- **Stream C:** T-P4-01/T-P4-02/T-P4-13 (DocIR, artifact store, VaultWriter) in parallel with the P3 spikes.
- **Stream D:** T-P5-06 taxonomy v0 as soon as the course map (T-P2-11) exists.
- **Stream E (background):** T-P13-01 waves after the pilot.

<!-- BEGIN GENERATED: task dependency listing -->

### Task dependency listing (generated from 28; validate with tools/validate_plan.py)

**P0 — Corpus Audit & Architecture Planning**

- `T-P0-01` ← —
- `T-P0-02` ← `T-P0-01`
- `T-P0-03` ← `T-P0-01`, `T-P0-02`
- `T-P0-04` ← `T-P0-03`
- `T-P0-05` ← `T-P0-04`
- `T-P0-06` ← `T-P0-05`
- `T-P0-07` ← `T-P0-06`
- `T-P0-08` ← `T-P0-06`, `T-P0-09`
- `T-P0-09` ← `T-P0-06`, `T-P0-07`

**P1 — Foundations**

- `T-P1-01` ← `T-P0-08`
- `T-P1-02` ← `T-P1-01`
- `T-P1-03` ← `T-P1-02`
- `T-P1-04` ← `T-P1-01`
- `T-P1-05` ← `T-P1-01`
- `T-P1-06` ← `T-P1-05`
- `T-P1-07` ← `T-P1-06`
- `T-P1-08` ← `T-P1-06`
- `T-P1-09` ← `T-P1-06`, `T-P1-07`
- `T-P1-10` ← `T-P1-09`
- `T-P1-11` ← `T-P1-02`, `T-P1-08`
- `T-P1-12` ← `T-P1-05`
- `T-P1-13` ← `T-P1-01`

**P2 — Source Registry, Manifest & Exact Dedup**

- `T-P2-01` ← `T-P1-03`, `T-P1-09`
- `T-P2-02` ← `T-P2-01`, `T-P1-04`
- `T-P2-03` ← `T-P2-02`
- `T-P2-04` ← `T-P2-02`
- `T-P2-05` ← `T-P2-04`, `T-P1-12`
- `T-P2-06` ← `T-P2-02`, `T-P1-12`
- `T-P2-07` ← `T-P2-06`
- `T-P2-08` ← `T-P2-02`
- `T-P2-09` ← `T-P2-04`
- `T-P2-10` ← `T-P2-04`
- `T-P2-11` ← `T-P2-04`, `T-P1-12`
- `T-P2-12` ← `T-P2-03`, `T-P2-06`, `T-P2-08`
- `T-P2-13` ← `T-P2-01`
- `T-P2-14` ← `T-P2-06`, `T-P2-04`

**P3 — Gold Set & Extraction Spikes (decision gate)**

- `T-P3-01` ← `T-P2-06`, `T-P2-10`
- `T-P3-02` ← `T-P3-01`
- `T-P3-03` ← `T-P3-01`
- `T-P3-04` ← `T-P3-01`, `T-P1-05`
- `T-P3-05` ← `T-P3-04`, `T-P3-03`
- `T-P3-06` ← `T-P3-04`, `T-P3-02`
- `T-P3-07` ← `T-P3-04`
- `T-P3-08` ← `T-P3-04`
- `T-P3-09` ← `T-P3-05`, `T-P3-06`, `T-P3-08`
- `T-P3-10` ← `T-P3-03`
- `T-P3-11` ← `T-P3-05`, `T-P3-06`, `T-P3-07`, `T-P3-08`, `T-P3-09`, `T-P3-10`

**P4 — Extraction & Normalization**

- `T-P4-01` ← `T-P1-05`
- `T-P4-02` ← `T-P4-01`, `T-P1-09`
- `T-P4-03` ← `T-P4-02`, `T-P3-11`
- `T-P4-04` ← `T-P4-03`
- `T-P4-05` ← `T-P4-02`, `T-P3-07`
- `T-P4-06` ← `T-P4-04`, `T-P3-11`
- `T-P4-07` ← `T-P4-04`, `T-P3-11`
- `T-P4-08` ← `T-P4-04`, `T-P3-10`
- `T-P4-09` ← `T-P4-05`, `T-P4-03`
- `T-P4-10` ← `T-P4-03`
- `T-P4-11` ← `T-P4-03`, `T-P4-05`
- `T-P4-12` ← `T-P4-11`, `T-P4-07`, `T-P4-08`
- `T-P4-13` ← `T-P1-07`, `T-P1-12`
- `T-P4-14` ← `T-P4-07`, `T-P4-02`
- `T-P4-15` ← `T-P4-12`, `T-P4-13`, `T-P4-09`, `T-P4-10`, `T-P4-06`, `T-P4-14`
- `T-P4-16` ← `T-P4-15`

**P5 — Knowledge Units, Near-Dedup & Taxonomy**

- `T-P5-01` ← `T-P4-15`
- `T-P5-02` ← `T-P5-01`
- `T-P5-03` ← `T-P5-01`, `T-P4-10`
- `T-P5-04` ← `T-P5-03`, `T-P2-09`
- `T-P5-05` ← `T-P5-01`
- `T-P5-06` ← `T-P2-11`, `T-P1-12`
- `T-P5-07` ← `T-P5-06`, `T-P5-01`
- `T-P5-08` ← `T-P5-01`
- `T-P5-09` ← `T-P4-11`

**P6 — Retrieval Infrastructure**

- `T-P6-01` ← `T-P5-01`, `T-P5-07`
- `T-P6-02` ← `T-P6-01`
- `T-P6-03` ← `T-P5-01`, `T-P5-02`
- `T-P6-04` ← `T-P6-02`, `T-P6-03`
- `T-P6-05` ← `T-P6-02`, `T-P6-03`
- `T-P6-06` ← `T-P6-04`, `T-P6-05`
- `T-P6-07` ← `T-P6-04`, `T-P1-09`
- `T-P6-08` ← `T-P6-05`, `T-P6-07`
- `T-P6-09` ← `T-P5-02`, `T-P6-02`
- `T-P6-10` ← `T-P6-08`
- `T-P6-11` ← `T-P6-10`
- `T-P6-12` ← `T-P6-10`, `T-P5-02`
- `T-P6-13` ← `T-P6-12`

**P7 — Baseline Grounded QA**

- `T-P7-01` ← `T-P1-02` (T-P7-02 edge removed 2026-11-04 by owner decision; mock/local backends only)
- `T-P7-02` ← `T-P0-08`
- `T-P7-03` ← `T-P1-05`
- `T-P7-04` ← `T-P7-01`, `T-P7-03`, `T-P6-13`
- `T-P7-05` ← `T-P7-04`
- `T-P7-06` ← `T-P7-04`
- `T-P7-07` ← `T-P7-05`
- `T-P7-08` ← `T-P7-05`, `T-P7-06`

**P8 — Knowledge Graph**

- `T-P8-01` ← `T-P5-08`
- `T-P8-02` ← `T-P8-01`, `T-P5-03`, `T-P5-09`
- `T-P8-03` ← `T-P8-01`, `T-P5-08`
- `T-P8-04` ← `T-P8-03`, `T-P7-01`
- `T-P8-05` ← `T-P8-04`
- `T-P8-06` ← `T-P8-05`, `T-P6-12`
- `T-P8-07` ← `T-P4-15`
- `T-P8-08` ← `T-P8-06`
- `T-P8-09` ← `T-P8-05`, `T-P4-13`

**P9 — Agentic Orchestration**

- `T-P9-01` ← `T-P7-04`
- `T-P9-02` ← `T-P1-08`
- `T-P9-03` ← `T-P9-01`, `T-P9-02`, `T-P7-05`
- `T-P9-04` ← `T-P9-03`
- `T-P9-05` ← `T-P9-04`, `T-P6-13`
- `T-P9-06` ← `T-P9-03`
- `T-P9-07` ← `T-P9-03`
- `T-P9-08` ← `T-P7-01`, `T-P4-08`
- `T-P9-09` ← `T-P9-08`, `T-P7-07`
- `T-P9-10` ← `T-P9-03`, `T-P4-14`
- `T-P9-11` ← `T-P9-06`, `T-P9-07`, `T-P9-05`

**P10 — Obsidian Curation & Living Knowledge**

- `T-P10-01` ← `T-P4-15`
- `T-P10-02` ← `T-P10-01`, `T-P5-01`
- `T-P10-03` ← `T-P10-01`, `T-P7-05`
- `T-P10-04` ← `T-P10-03`, `T-P8-05`
- `T-P10-05` ← `T-P10-04`, `T-P8-05`
- `T-P10-06` ← `T-P10-03`, `T-P5-05`
- `T-P10-07` ← `T-P4-13`, `T-P10-03`
- `T-P10-08` ← `T-P10-01`

**P11 — Gap Analysis**

- `T-P11-01` ← `T-P5-06`, `T-P7-01`
- `T-P11-02` ← `T-P11-01`, `T-P8-03`, `T-P5-07`
- `T-P11-03` ← `T-P11-02`
- `T-P11-04` ← `T-P11-03`, `T-P10-05`
- `T-P11-05` ← `T-P11-03`

**P12 — External Research & Approval**

- `T-P12-01` ← `T-P9-01`, `T-P11-03`
- `T-P12-02` ← `T-P12-01`
- `T-P12-03` ← `T-P12-02`
- `T-P12-04` ← `T-P12-01`, `T-P10-01`
- `T-P12-05` ← `T-P12-04`, `T-P4-15`
- `T-P12-06` ← `T-P12-05`, `T-P6-08`
- `T-P12-07` ← `T-P12-06`, `T-P12-03`

**P13 — Scale-out, Hardening & Operations**

- `T-P13-01` ← `T-P4-15`, `T-P3-09`, `T-P2-12`
- `T-P13-02` ← `T-P4-13`, `T-P1-12`
- `T-P13-03` ← `T-P6-08`, `T-P8-02`
- `T-P13-04` ← `T-P1-06`
- `T-P13-05` ← `T-P6-07`
- `T-P13-06` ← `T-P5-05`, `T-P4-14`
- `T-P13-07` ← `T-P7-08`
- `T-P13-08` ← `T-P13-01`
- `T-P13-09` ← `T-P13-01`
- `T-P13-10` ← `T-P13-01`

**P14 — Project/Idea Integration (future)**

- `T-P14-01` ← `T-P11-03`
- `T-P14-02` ← `T-P14-01`, `T-P9-11`
- `T-P14-03` ← `T-P10-03`

### Longest dependency chain (by task count)

`T-P0-01` → `T-P0-02` → `T-P0-03` → `T-P0-04` → `T-P0-05` → `T-P0-06` → `T-P0-07` → `T-P0-09` → `T-P0-08` → `T-P1-01` → `T-P1-05` → `T-P1-06` → `T-P1-07` → `T-P1-09` → `T-P2-01` → `T-P2-02` → `T-P2-04` → `T-P2-10` → `T-P3-01` → `T-P3-04` → `T-P3-08` → `T-P3-09` → `T-P3-11` → `T-P4-03` → `T-P4-04` → `T-P4-07` → `T-P4-14` → `T-P4-15` → `T-P5-01` → `T-P5-07` → `T-P6-01` → `T-P6-02` → `T-P6-04` → `T-P6-07` → `T-P6-08` → `T-P6-10` → `T-P6-12` → `T-P6-13` → `T-P7-04` → `T-P9-01` → `T-P12-01` → `T-P12-04` → `T-P12-05` → `T-P12-06` → `T-P12-07`

<!-- END GENERATED -->
