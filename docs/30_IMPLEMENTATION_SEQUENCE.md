# 30 — Implementation Sequence

This is the recommended linear order. It is consistent with 29 and lets an agent always pick the next task without guesswork.
**Rule for agents:** pick the first task in this list whose status is `NOT_STARTED` and whose dependencies are all `DONE` (see `35_EXECUTION_STATE.json → next_eligible_tasks`).
Tasks with `human approval: required` stop and ask the owner.

## Step 0 — Gate
0. **T-P0-08** Owner approval + answers to the blocking questions. *(Nothing below starts before this.)* Precondition T-P0-09 (t2 re-audit, docs/37) is DONE. Q-B01 has a recommended resolution (close) pending owner confirmation.

## Step 1 — Foundations (P1), ≈ 1–2 weeks of agent work
1. T-P1-01 Repository bootstrap
2. T-P1-02 Configuration
3. T-P1-03 SourceFS read-only guard  ← **safety-critical: complete before any code touches D:\MBI-BRAIN**
4. T-P1-04 Ids and hashing
5. T-P1-05 Core schemas
6. T-P1-06 SQLite + migrations
7. T-P1-07 Provenance core
8. T-P1-08 Run ledger and logging
9. T-P1-09 Job queue (crash-resume)
10. T-P1-10 Resource governor
11. T-P1-11 CLI skeleton
12. T-P1-12 Curation ledger
13. T-P1-13 Synthetic fixtures
*(Parallel, once T-P1-05 is DONE: T-P7-03 answer schema. Once T-P0-08 is DONE: T-P7-02 SPIKE-MODELGW.)*

## Step 2 — Registry (P2)
14. T-P2-01 Scanner → 15. T-P2-02 Hashing → 16. T-P2-03 Change detection → 17. T-P2-04 Classification →
18. T-P2-05 Exclusions/sensitivity (owner review) → 19. T-P2-06 Exact dedup → 20. T-P2-08 Archives → 21. T-P2-09 Twins →
22. T-P2-10 Genre → 23. T-P2-11 Course map (owner review) → 24. T-P2-13 Name repair → 25. T-P2-14 Manifest report →
26. T-P2-07 Mirror report → 27. T-P2-12 Audit refresh (**after Q-B01**)

## Step 3 — Ground truth and spikes (P3)
28. T-P3-01 Gold sample selection (owner review) → 29. T-P3-04 Extraction harness →
30. T-P3-02 Gold math (**owner verification**) ∥ 31. T-P3-03 Gold layout (**owner verification**) ∥ 32. T-P3-07 SPIKE-OMML ∥ 33. T-P3-08 SPIKE-OCR →
34. T-P3-05 SPIKE-PARSER → 35. T-P3-06 SPIKE-MATH → 36. T-P3-10 SPIKE-FIGURE → 37. T-P3-09 SPIKE-COMPUTE (**owner policy**) →
38. T-P3-11 Extraction decision (**owner approval**)
*(Parallel during P3: T-P4-01 DocIR, T-P4-02 artifact store, T-P4-13 VaultWriter once Q-B02 is answered.)*

## Step 4 — Extraction (P4)
39. T-P4-03 Text tier → 40. T-P4-04 Triage → 41. T-P4-05 Office → 42. T-P4-06 OCR → 43. T-P4-07 Math →
44. T-P4-08 Figures/tables → 45. T-P4-09 Twin fusion → 46. T-P4-10 Annotations → 47. T-P4-11 Structure →
48. T-P4-12 Markdown → 49. T-P4-14 Reprocess queue → 50. T-P4-15 **Pilot W0 (owner acceptance)** → 51. T-P4-16 Quality report
*(Background after 50 and 37: T-P13-01 waves W1→W3, per the compute policy.)*

## Step 5 — Knowledge (P5)
52. T-P5-01 KUs → 53. T-P5-05 Anchors → 54. T-P5-02 Symbols → 55. T-P5-03 Near-dedup → 56. T-P5-04 Twins confirm →
57. T-P5-06 Taxonomy v0 (**owner approval**) → 58. T-P5-07 Topics → 59. T-P5-08 Concept candidates → 60. T-P5-09 References

## Step 6 — Retrieval (P6)
61. T-P6-01 Retrieval gold (**owner review**) → 62. T-P6-02 Harness → 63. T-P6-03 Chunk views → 64. T-P6-04 SPIKE-EMBED ∥ 65. T-P6-05 SPIKE-HYBRID →
66. T-P6-06 SPIKE-CHUNK → 67. T-P6-07 Embedding pipeline → 68. T-P6-08 Indexes → 69. T-P6-09 Math index/SPIKE-MATHRET → 70. T-P6-10 Fusion →
71. T-P6-11 SPIKE-RERANK → 72. T-P6-12 Evidence packs → 73. T-P6-13 `sbr search`

## Step 7 — Baseline QA (P7)
74. T-P7-01 Gateway → 75. T-P7-04 Baseline RAG → 76. T-P7-05 Validator → 77. T-P7-06 Citations → 78. T-P7-07 QA gold + eval (**owner**) → 79. T-P7-08 `sbr ask`

## Step 8 onward
P8 (T-P8-01 → 02 → 03 → 04 → 05 → 06 → 08 → 09; T-P8-07 any time after the pilot) →
P9 (T-P9-01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11) →
P10 (01 → 02 → 03 → 04 → 05 → 06 → 07 → 08) → P11 (01 → 05) → P12 (01 → 07) → P13 (02 → 03 → 04 → 05 → 06 → 07 → 10; 08/09 per scope) → P14 (deferred).

## The first implementation task after approval

**T-P1-01 — Repository bootstrap.** Initialize git in `D:\AgenticAI\second-brain-rag`; create a Python 3.12 uv project with the `src/sbr` layout, ruff, mypy, pytest and pre-commit (incl. a secret scan); add `.gitignore` for `var/`, `.venv*` and `audit/phase0/*.csv|*.jsonl|samples/`; add `tools/check.ps1`.
**Validation:** `uv run pytest` passes (empty suite), `uv run sbr --help` prints, and `tools/check.ps1` runs lint, types and tests.
The first task touching the corpus is T-P2-01. It must come after T-P1-03 (the SourceFS guard) is DONE.
