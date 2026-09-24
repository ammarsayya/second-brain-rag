# 23 — Failure Recovery

| Failure | Detection | Recovery | Data at risk |
|---|---|---|---|
| Process crash or power loss mid-stage | Expired leases, run status `running` without heartbeat | Restart: expired leases re-leased; temp dirs cleaned; completed items untouched | In-flight items only (NFR-02) |
| Partial artifact write | Temp dir without manifest | Discarded on startup; item re-run | None |
| SQLite corruption | `PRAGMA integrity_check` in `sbr doctor`; open errors | Restore the latest `.backup` snapshot, or rebuild: registry from rescan, knowledge from artifacts + ledger | Work since the snapshot (rebuildable) |
| Artifact store loss | Missing artifact dirs referenced by the manifest | Re-extract (expensive tiers: queue by priority); restore from optional backup | Compute time |
| Index corruption | Query errors, count mismatch vs knowledge DB | `sbr rebuild index --set <id>` | None |
| Wrong extraction discovered | Owner flag, eval, validation | Flag → reprocess with a higher tier → new version; KU anchor alignment; stale AINotes regenerated | None (versions kept) |
| Bad parser/model upgrade | Eval gate regression | Keep the old stage_version active; roll back config; new artifacts stay side by side | None |
| Hallucinated graph edges found | Quality gate, owner reports | Mark `rejected` (curation ledger); fix rules/prompts; re-run extraction for affected types | None |
| User edits generated note | Hash mismatch | Fork semantics (19 §2) | None |
| Vault conflict (Obsidian sync, simultaneous edit) | git status non-clean before a batch | VaultWriter aborts the batch, reports, and never force-writes | None |
| Source file changed or removed externally | Scan diff | Change semantics (08 §3); knowledge flagged `source_missing`, never auto-deleted | None |
| Disk full | Governor floor check | Pause the queue; report; suggest `sbr gc` (render cache, orphan artifacts) | None |
| Provider outage or rate limit | Gateway errors | Fallback models; backoff; the queue continues other stages | None |
| Research run interrupted | Durable workflow state | Resume from the last checkpoint | None |
| Schema migration failure | Migration test + transaction | Migrations run in a transaction on a **copy-first** policy (backup before migrate); rollback script | None |

Principle: **no failure path deletes knowledge automatically.** Destructive clean-up (`sbr gc`) only touches rebuildable caches and requires explicit invocation.
