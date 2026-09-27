from __future__ import annotations

import json
import shutil
import stat
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from sbr.cli.app import app
from sbr.config import SbrConfig, config_from_mapping
from sbr.curation import load_course_map
from sbr.db import registry as reg
from sbr.db.migrations import Migrator
from sbr.db.registry import RegistryDB
from sbr.ids import new_id
from sbr.obs.trace import TraceDB
from sbr.ops.backup import BackupError, BackupFile, BackupManifest, create_backup, restore_backup
from sbr.safety import SourceWriteError
from sbr.schemas import SourceRootRecord, SpanKind, SpanStatus
from sbr.schemas.provenance import ProvenanceClass
from sbr.schemas.registry import RootKind
from sbr.vault.writer import VaultMutation, VaultWriter

runner = CliRunner()


def _note() -> str:
    return (
        "---\n"
        "sbr_id: ai_backup_drill\n"
        "provenance_class: AI_GENERATED\n"
        "generated_by: backup-test@1\n"
        "---\n"
        "Durable restore-drill knowledge.\n"
    )


def _write_curation(config: SbrConfig) -> None:
    root = Path(config.roots.curation)
    root.mkdir(parents=True)
    files = {
        "approvals.yaml": "[]\n",
        "canonical_overrides.yaml": "overrides: []\n",
        "canonical_path_overrides.yaml": "overrides: []\n",
        "concept_curation.yaml": "entries: []\n",
        "course_map.yaml": (
            "courses:\n"
            "  - course_id: Restore101\n"
            "    name: Backup and Restore\n"
            "    aliases: [Durability]\n"
            "    folder_patterns: ['restore/**']\n"
        ),
        "exclusions.yaml": "exclusions: []\n",
        "sensitivity_overrides.yaml": "overrides: []\n",
        "taxonomy.yaml": "concepts: []\n",
    }
    for name, content in files.items():
        (root / name).write_text(content, encoding="utf-8")


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip()


def _remove_readonly(function: Callable[..., object], path: str, _exc: BaseException) -> None:
    Path(path).chmod(stat.S_IWRITE)
    function(path)


def _remove_tree(path: Path) -> None:
    shutil.rmtree(path, onexc=_remove_readonly)


@pytest.fixture
def populated_config(make_config: Callable[..., SbrConfig], tmp_path: Path) -> SbrConfig:
    config = make_config(vault=str(tmp_path / "vault"))
    _write_curation(config)
    with VaultWriter.open(config) as writer:
        writer.write_batch(
            [
                VaultMutation.write(
                    "ai/Backup Drill.md",
                    _note(),
                    ProvenanceClass.AI_GENERATED,
                )
            ],
            message="backup drill note",
        )
    with RegistryDB.open(config) as db:
        db.migrate()
        db.repo(reg.SOURCE_ROOT).insert(
            SourceRootRecord(
                root_id="drill",
                path="C:\\synthetic-backup-drill",
                kind=RootKind.UNIVERSITY,
                read_only=True,
                added_at=datetime(2026, 9, 27, tzinfo=UTC),
            )
        )
    with TraceDB.open(config) as trace:
        trace.migrate()
        span = trace.start_span(new_id("run"), SpanKind.NODE, "backup-drill")
        trace.finish_span(span.span_id, SpanStatus.OK)
    return config


def _restored_config(config: SbrConfig, target: Path) -> SbrConfig:
    return config_from_mapping(
        {
            "roots": {
                "sources": [{"id": "restored", "path": str(target / "source")}],
                "var": str(target / "var"),
                "curation": str(target / "curation"),
                "vault": str(target / "vault"),
                "protected": [str(target / "protected")],
            }
        }
    )


def test_restore_drill_reconstructs_functionally_usable_state_on_fresh_path(
    populated_config: SbrConfig, tmp_path: Path
) -> None:
    original_head = _git(populated_config.vault_path, "rev-parse", "HEAD")
    result = create_backup(populated_config, tmp_path / "portable-backups")

    # Prove restore depends only on the portable package, not any live state or Migrator side snapshot.
    _remove_tree(populated_config.var_path)
    _remove_tree(populated_config.vault_path)
    _remove_tree(Path(populated_config.roots.curation))

    target = tmp_path / "brand-new-machine"
    restored = restore_backup(populated_config, result.backup_dir, target)
    restored_config = _restored_config(populated_config, target)

    with RegistryDB.open(restored_config) as db:
        assert db.schema_version == result.manifest.registry_schema_version
        row = db.repo(reg.SOURCE_ROOT).get("drill")
        assert row is not None
        assert row.path == "C:\\synthetic-backup-drill"
    with TraceDB.open(restored_config) as trace:
        assert trace.schema_version == result.manifest.traces_schema_version
        assert trace.conn.execute("SELECT name, status FROM span").fetchall() == [("backup-drill", "ok")]

    assert restored.vault_head == original_head
    assert _git(restored.vault_path, "rev-parse", "HEAD") == original_head
    assert _git(restored.vault_path, "log", "--format=%s") == "backup drill note"
    assert "Durable restore-drill knowledge" in (restored.vault_path / "ai" / "Backup Drill.md").read_text(
        encoding="utf-8"
    )
    course_map = load_course_map(restored.curation_path / "course_map.yaml")
    assert [record.course_id for record in course_map.records] == ["Restore101"]


def test_create_backup_routes_both_databases_through_migrator_online_backup(
    populated_config: SbrConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str]] = []
    original = Migrator.backup

    def spy(self: Migrator, label: str) -> Path:
        calls.append((self.db_path.name, label))
        return original(self, label)

    monkeypatch.setattr(Migrator, "backup", spy)
    result = create_backup(populated_config, tmp_path / "online-api-backups")

    assert calls == [("registry.sqlite", "p13"), ("traces.sqlite", "p13")]
    snapshots = {entry.purpose: entry.relative_path.name for entry in result.manifest.files}
    assert snapshots["registry"].startswith("registry-p13-")
    assert snapshots["traces"].startswith("traces-p13-")
    assert snapshots["registry"].endswith(".sqlite")
    assert snapshots["traces"].endswith(".sqlite")


def test_manifest_round_trips_and_rejects_path_traversal(populated_config: SbrConfig, tmp_path: Path) -> None:
    result = create_backup(populated_config, tmp_path / "manifest-backups")
    assert BackupManifest.read(result.manifest_path) == result.manifest

    with pytest.raises(BackupError, match="unsafe backup manifest path"):
        BackupFile.from_dict(
            {
                "purpose": "registry",
                "relative_path": "../registry.sqlite",
                "size": 1,
                "sha256": "sha256:" + "0" * 64,
            }
        )


def test_restore_rejects_tampered_package_without_publishing_target(
    populated_config: SbrConfig, tmp_path: Path
) -> None:
    result = create_backup(populated_config, tmp_path / "tamper-backups")
    vault_bundle = result.backup_dir / "vault.bundle"
    vault_bundle.write_bytes(vault_bundle.read_bytes() + b"tamper")
    target = tmp_path / "must-not-exist"

    with pytest.raises(BackupError, match="integrity verification"):
        restore_backup(populated_config, result.backup_dir, target)

    assert not target.exists()


def test_create_backup_rejects_missing_and_corrupt_database_sources(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    missing = make_config(vault=str(tmp_path / "missing-vault"))
    with pytest.raises(BackupError, match="registry database not found"):
        create_backup(missing, tmp_path / "missing-backups")

    corrupt = make_config(vault=str(tmp_path / "corrupt-vault"))
    registry_path = corrupt.db_dir / "registry.sqlite"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_bytes(b"not sqlite")
    with TraceDB.open(corrupt) as trace:
        trace.migrate()
    with pytest.raises(BackupError, match="backup creation failed"):
        create_backup(corrupt, tmp_path / "corrupt-backups")


def test_create_backup_rejects_dirty_vault(populated_config: SbrConfig, tmp_path: Path) -> None:
    (populated_config.vault_path / "owner-uncommitted.md").write_text("owner draft\n", encoding="utf-8")

    with pytest.raises(BackupError, match="dirty"):
        create_backup(populated_config, tmp_path / "dirty-vault-backups")


def test_backup_and_restore_refuse_protected_destinations(populated_config: SbrConfig, tmp_path: Path) -> None:
    protected = Path(populated_config.roots.protected[0])
    with pytest.raises(SourceWriteError, match="read-only source or protected root"):
        create_backup(populated_config, protected / "backups")

    result = create_backup(populated_config, tmp_path / "safe-backups")
    with pytest.raises(SourceWriteError, match="read-only source or protected root"):
        restore_backup(populated_config, result.backup_dir, protected / "restore")


def test_backup_cli_prints_json_summary(populated_config: SbrConfig, tmp_path: Path) -> None:
    config_path = tmp_path / "backup.toml"
    source = populated_config.roots.sources[0]
    config_path.write_text(
        "[roots]\n"
        f"sources = [{{ id = '{source.id}', path = '{source.path}' }}]\n"
        f"var = '{populated_config.roots.var}'\n"
        f"curation = '{populated_config.roots.curation}'\n"
        f"vault = '{populated_config.roots.vault}'\n"
        f"protected = ['{populated_config.roots.protected[0]}']\n",
        encoding="utf-8",
    )
    destination = tmp_path / "cli-backups"

    invocation = runner.invoke(
        app,
        ["backup", "--dest", str(destination), "--config", str(config_path)],
    )

    assert invocation.exit_code == 0, invocation.output
    payload: dict[str, Any] = json.loads(invocation.output)
    assert payload["backup_id"].startswith("sbr-backup-")
    assert payload["files"] == 11
    assert Path(payload["manifest"]).is_file()
