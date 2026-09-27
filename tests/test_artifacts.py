"""TS-ART: atomic, append-only, content-addressed artifact storage (T-P4-02)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sbr.artifacts import ArtifactConflictError, ArtifactStore
from sbr.cli.app import app
from sbr.config import SbrConfig
from sbr.ids import hash_bytes
from sbr.obs.logging import shutdown_logging


def make_store(make_config: Callable[..., SbrConfig]) -> tuple[ArtifactStore, SbrConfig]:
    config = make_config()
    return ArtifactStore(config), config


def test_write_publishes_a_manifest_and_verified_files_atomically(
    make_config: Callable[..., SbrConfig],
) -> None:
    store, _ = make_store(make_config)
    blob_id = hash_bytes(b"source")

    manifest = store.write(
        blob_id,
        "docir@1.0.0",
        {"docir.json": b'{"docir_version":"1.0"}', "figures/fig_1.png": b"PNG"},
    )

    version_dir = store.version_path(blob_id, "docir@1.0.0")
    digest = blob_id.removeprefix("b3:")
    assert version_dir == store.root / digest[:2] / digest / "docir@1.0.0"
    assert (version_dir / "docir.json").read_bytes() == b'{"docir_version":"1.0"}'
    assert (version_dir / "figures" / "fig_1.png").read_bytes() == b"PNG"
    assert store.read_manifest(blob_id, "docir@1.0.0") == manifest
    assert manifest.files["docir.json"].blob_id == hash_bytes(b'{"docir_version":"1.0"}')
    assert manifest.files["docir.json"].size == len(b'{"docir_version":"1.0"}')
    assert json.loads((version_dir / "manifest.json").read_text(encoding="utf-8"))["blob_id"] == blob_id


def test_two_extractor_versions_coexist_without_mutating_the_old_one(
    make_config: Callable[..., SbrConfig],
) -> None:
    store, _ = make_store(make_config)
    blob_id = hash_bytes(b"source")

    first = store.write(blob_id, "docir@1.0.0", {"docir.json": b"v1"})
    second = store.write(blob_id, "docir@2.0.0", {"docir.json": b"v2"})

    assert first.extractor_version == "docir@1.0.0"
    assert second.extractor_version == "docir@2.0.0"
    assert (store.version_path(blob_id, "docir@1.0.0") / "docir.json").read_bytes() == b"v1"
    assert (store.version_path(blob_id, "docir@2.0.0") / "docir.json").read_bytes() == b"v2"


def test_repeating_an_identical_write_is_idempotent_but_different_bytes_conflict(
    make_config: Callable[..., SbrConfig],
) -> None:
    store, _ = make_store(make_config)
    blob_id = hash_bytes(b"source")

    expected = store.write(blob_id, "docir@1.0.0", {"docir.json": b"same"})
    assert store.write(blob_id, "docir@1.0.0", {"docir.json": b"same"}) == expected

    with pytest.raises(ArtifactConflictError, match="immutable"):
        store.write(blob_id, "docir@1.0.0", {"docir.json": b"different"})
    assert (store.version_path(blob_id, "docir@1.0.0") / "docir.json").read_bytes() == b"same"


@pytest.mark.parametrize(
    ("extractor_version", "artifact_name"),
    [
        ("../docir@1", "docir.json"),
        ("docir/1@0", "docir.json"),
        ("docir@1", "../escape.json"),
        ("docir@1", "/absolute.json"),
        ("docir@1", "manifest.json"),
    ],
)
def test_untrusted_path_components_cannot_escape_the_store(
    make_config: Callable[..., SbrConfig], extractor_version: str, artifact_name: str
) -> None:
    store, config = make_store(make_config)

    with pytest.raises(ValueError):
        store.write(hash_bytes(b"source"), extractor_version, {artifact_name: b"x"})
    assert not config.var_path.exists()


def test_subprocess_crash_before_rename_leaves_no_partial_visible_artifact(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    store, config = make_store(make_config)
    blob_id = hash_bytes(b"source")
    code = """
import os
from sbr.artifacts import ArtifactStore
from sbr.config import SbrConfig

config = SbrConfig.model_validate_json(os.environ["SBR_TEST_CONFIG"])
store = ArtifactStore(config)
original = os.rename
def crash_at_publish(src, dst):
    os._exit(73)
os.rename = crash_at_publish
store.write(os.environ["SBR_TEST_BLOB"], "docir@crash", {"docir.json": b"complete-in-staging"})
"""
    env = os.environ.copy()
    env["SBR_TEST_CONFIG"] = config.model_dump_json()
    env["SBR_TEST_BLOB"] = blob_id
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env, check=False)

    assert result.returncode == 73
    assert not store.version_path(blob_id, "docir@crash").exists()
    orphans = store.list_orphans()
    assert len(orphans) == 1
    assert (orphans[0] / "manifest.json").is_file()

    assert store.gc_orphans(apply=False) == orphans
    assert orphans[0].exists()
    assert store.gc_orphans(apply=True) == orphans
    assert not orphans[0].exists()


def test_gc_only_considers_staging_directories_and_defaults_to_dry_run(
    make_config: Callable[..., SbrConfig],
) -> None:
    store, _ = make_store(make_config)
    blob_id = hash_bytes(b"source")
    store.write(blob_id, "docir@1", {"docir.json": b"published"})
    orphan = store.staging_root / "orphan"
    orphan.mkdir(parents=True)
    (orphan / "partial").write_bytes(b"partial")

    assert store.gc_orphans() == [orphan]
    assert orphan.exists()
    assert store.version_path(blob_id, "docir@1").exists()


def test_artifacts_gc_cli_is_dry_run_unless_apply_is_explicit(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    config = make_config()
    store = ArtifactStore(config)
    orphan = store.staging_root / "orphan"
    orphan.mkdir(parents=True)
    config_file = tmp_path / "sbr.toml"
    source = config.roots.sources[0].path
    config_file.write_text(
        "[roots]\n"
        f"sources = [{{ id = 'fx', path = '{source}' }}]\n"
        f"var = '{config.roots.var}'\n"
        f"curation = '{config.roots.curation}'\n"
        f"protected = ['{config.roots.protected[0]}']\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    try:
        dry_run = runner.invoke(app, ["artifacts", "gc", "--config", str(config_file)])
        assert dry_run.exit_code == 0, dry_run.output
        assert json.loads(dry_run.output) == {"apply": False, "orphans": 1}
        assert orphan.exists()

        applied = runner.invoke(app, ["artifacts", "gc", "--apply", "--config", str(config_file)])
        assert applied.exit_code == 0, applied.output
        assert json.loads(applied.output) == {"apply": True, "orphans": 1}
        assert not orphan.exists()
    finally:
        shutdown_logging()
