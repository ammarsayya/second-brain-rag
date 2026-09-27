# 39 — Backup and Restore

This document covers T-P13-02 only: portable backup and clean-path restore of the vault, curation ledger, registry
database, and trace database. It is not the general operations runbook planned by T-P13-10, and it does not cover
the source corpus, ingestion waves, indexes, caches, or the optional artifact store.

## 1. Durability scope

| State | Backup representation | Durability meaning |
|---|---|---|
| Independent Obsidian vault | `vault.bundle`, created with `git bundle create --all` | Full Git refs and commit history, including owner knowledge that is not rebuildable |
| `curation/*.yaml` | Validated byte-for-byte copies of all eight loader-owned files | Irreplaceable owner decisions; Git remains the primary version history |
| `var/db/registry.sqlite` | SQLite online-backup snapshot | Rebuildable by a corpus rescan, but expensive enough to preserve |
| `var/traces/traces.sqlite` | SQLite online-backup snapshot | Derived operational evidence; rebuildable only by re-running work |

The database files are never copied while live. `create_backup()` calls each open database's
`Migrator.backup("p13")`, which delegates to `sqlite3.Connection.backup()`, and only copies the completed snapshot
into the portable package. This is safe with WAL-mode writers. The original on-demand snapshots remain under
`var/backups/registry/` and `var/backups/traces/` as additional local recovery points.

The artifact store (`var/artifacts/`) is deliberately excluded in v1. It is rebuildable from sources and the
curation ledger, although that rebuild can take days or weeks. A later explicit, capacity-aware artifact backup
may be added without changing this manifest format's required durability set.

## 2. Create a backup

The vault must be an independent Git repository with at least one commit and a clean working tree. Both SQLite
databases and all curation files must exist and validate.

```powershell
uv run sbr backup --config config/sbr.toml
```

The default parent is `<var>/backups/system`. An external disk or other destination is always explicit:

```powershell
uv run sbr backup --dest E:\second-brain-backups --config config/sbr.toml
```

No drive letter is inferred. The destination is checked with the configured protected/source-root safety rules and
must not overlap the vault or curation root. The command prints one JSON summary containing the backup directory,
manifest, schema versions, vault HEAD, and file count.

One package has this layout:

```text
sbr-backup-<UTC timestamp>/
  manifest.json
  vault.bundle
  databases/
    registry-p13-<UTC timestamp>.sqlite
    traces-p13-<UTC timestamp>.sqlite
  curation/
    approvals.yaml
    canonical_overrides.yaml
    canonical_path_overrides.yaml
    concept_curation.yaml
    course_map.yaml
    exclusions.yaml
    sensitivity_overrides.yaml
    taxonomy.yaml
```

Every payload file has a size and SHA-256 digest in `manifest.json`. Creation happens in a sibling staging
directory and publishes the package with one rename only after database integrity checks, `git bundle verify`, and
curation-schema validation succeed.

## 3. Restore into a clean path

Restore is intentionally a Python API in v1; there is no `sbr restore` CLI verb. This keeps an infrequent,
high-consequence operation explicit while providing reusable, fully tested logic:

```python
from pathlib import Path

from sbr.config import load_config
from sbr.ops.backup import restore_backup

config = load_config("config/sbr.toml")
result = restore_backup(
    config,
    Path(r"E:\second-brain-backups\sbr-backup-20260927T120000000000Z"),
    Path(r"D:\restore-drill\second-brain"),
)
print(result)
```

The target must not exist and must not overlap the package or configured live `var`, vault, or curation roots.
Restore first verifies the manifest, every size and hash, SQLite integrity and schema versions, and bundle
readability. It stages a canonical layout under a fresh sibling path:

```text
<target>/
  var/db/registry.sqlite
  var/traces/traces.sqlite
  vault/                       # clean clone with full history
  curation/*.yaml
```

The staged vault is cloned from the bundle, its bundle is verified from inside the new repository, and its HEAD is
matched to the manifest. Every restored curation file is loaded through its production schema loader. Only then is
the staged tree renamed to the requested target. A failure leaves no published target.

To adopt a restored tree, point a reviewed configuration's `roots.var`, `roots.vault`, and `roots.curation` to the
three restored locations, then run normal health checks. Source roots are not part of this backup and must remain
configured separately.

## 4. Automated restore drill

`tests/ops/test_backup.py::test_restore_drill_reconstructs_functionally_usable_state_on_fresh_path` is the required
clean-machine drill. It:

1. writes a real note through `VaultWriter`, creating genuine vault history;
2. inserts and later reads a typed registry row;
3. writes and later reads a trace span;
4. writes all eight curation files, including a non-empty course map;
5. creates the portable backup;
6. deletes the original live `var`, vault, and curation trees, including Migrator's side snapshots;
7. restores into a target that did not exist;
8. opens the restored database through `RegistryDB.open()`, checks its schema version and row, opens the restored
   trace database, checks the vault HEAD/log/note, and round-trips the restored YAML through `load_course_map()`.

Focused tests also spy on both `Migrator.backup()` calls, round-trip and harden the manifest, reject tampering before
publishing a target, reject missing/corrupt databases and a dirty vault, and exercise the `sbr backup` JSON surface.

## 5. Failure handling

- **Dirty vault:** commit or intentionally discard the owner changes, then retry. A backup never silently omits
  working-tree content.
- **Corrupt or missing database:** restore the latest intact package or on-demand snapshot. If none exists, rebuild
  registry state from sources and curation; trace history may be lost.
- **Hash, size, bundle, or schema mismatch:** quarantine that package and use an earlier verified package. Restore
  never bypasses integrity checks.
- **Malformed curation:** repair through the normal reviewed Git workflow. Backup and restore both fail closed rather
  than preserve an un-loadable ledger as if it were healthy.
- **Interrupted create/restore:** no final backup or restore target is published; an exact staging directory may be
  cleaned after confirming no process is still using it.

Backups can contain filenames, metadata, derived registry state, and vault knowledge. Store them with access controls
appropriate to the original state. They do not add source-corpus content beyond information already legitimately
present in those stores.
