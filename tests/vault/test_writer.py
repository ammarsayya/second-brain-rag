from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path, PurePosixPath

import pytest

from sbr.config import SbrConfig
from sbr.schemas.provenance import ProvenanceClass
from sbr.vault.writer import (
    END_USER_SECTION,
    START_USER_SECTION,
    VAULT_STAGE_PREFIX,
    VaultDirtyError,
    VaultMutation,
    VaultOwnershipError,
    VaultWriter,
)


def _note(sbr_id: str, provenance: ProvenanceClass, body: str) -> str:
    return f"---\nsbr_id: {sbr_id}\nprovenance_class: {provenance.value}\ngenerated_by: test@1\n---\n{body}"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.fixture
def vault_config(make_config: Callable[..., SbrConfig], tmp_path: Path) -> SbrConfig:
    return make_config(vault=str(tmp_path / "vault"))


def test_notes_are_never_touched(vault_config: SbrConfig) -> None:
    notes = vault_config.vault_path / "notes"
    notes.mkdir(parents=True)
    existing = notes / "owner.md"
    existing.write_bytes(b"owner bytes\n")
    before = (existing.read_bytes(), existing.stat().st_mtime_ns)

    with VaultWriter.open(vault_config) as writer:
        for mutation in (
            VaultMutation.write(
                "notes/new.md",
                _note("note_new", ProvenanceClass.AI_GENERATED, "new\n"),
                ProvenanceClass.AI_GENERATED,
            ),
            VaultMutation.write(
                "notes/owner.md",
                _note("note_owner", ProvenanceClass.AI_GENERATED, "replace\n"),
                ProvenanceClass.AI_GENERATED,
            ),
            VaultMutation.delete("notes/owner.md"),
        ):
            with pytest.raises(VaultOwnershipError, match="never"):
                writer.write_batch([mutation], message="forbidden")

    assert (existing.read_bytes(), existing.stat().st_mtime_ns) == before
    assert not (notes / "new.md").exists()


def test_owner_edit_forks_and_reclassifies_original(vault_config: SbrConfig) -> None:
    path = vault_config.vault_path / "concepts" / "Control.md"
    with VaultWriter.open(vault_config) as writer:
        writer.write_batch(
            [
                VaultMutation.write(
                    "concepts/Control.md",
                    _note("concept_control", ProvenanceClass.AI_GENERATED, "generated v1\n"),
                    ProvenanceClass.AI_GENERATED,
                )
            ],
            message="create concept",
        )
        hand_edited = path.read_text(encoding="utf-8").replace("generated v1", "owner changed this")
        path.write_text(hand_edited, encoding="utf-8")
        _git(vault_config.vault_path, "add", ".")
        _git(
            vault_config.vault_path,
            "-c",
            "user.name=Owner",
            "-c",
            "user.email=owner@localhost",
            "commit",
            "-m",
            "owner edit",
        )

        result = writer.write_batch(
            [
                VaultMutation.write(
                    "concepts/Control.md",
                    _note("concept_control", ProvenanceClass.AI_GENERATED, "generated v2\n"),
                    ProvenanceClass.AI_GENERATED,
                )
            ],
            message="propose concept update",
        )

    original = path.read_text(encoding="utf-8")
    fork = vault_config.vault_path / "concepts" / "Control.sbr-update.md"
    assert "owner changed this" in original
    assert "provenance_class: USER_AUTHORED" in original
    assert "generated v2" in fork.read_text(encoding="utf-8")
    assert result.forked == (PurePosixPath("concepts/Control.sbr-update.md"),)


def test_file_without_sbr_id_is_owner_authored_and_only_forked(vault_config: SbrConfig) -> None:
    path = vault_config.vault_path / "concepts" / "Owner.md"
    path.parent.mkdir(parents=True)
    owner_bytes = b"# My note\nNever rewrite this.\n"
    path.write_bytes(owner_bytes)
    _git(vault_config.vault_path, "init")
    _git(vault_config.vault_path, "add", ".")
    _git(
        vault_config.vault_path,
        "-c",
        "user.name=Owner",
        "-c",
        "user.email=owner@localhost",
        "commit",
        "-m",
        "owner note",
    )

    with VaultWriter.open(vault_config) as writer:
        result = writer.write_batch(
            [
                VaultMutation.write(
                    "concepts/Owner.md",
                    _note("concept_owner", ProvenanceClass.AI_GENERATED, "system proposal\n"),
                    ProvenanceClass.AI_GENERATED,
                )
            ],
            message="fork around owner note",
        )

    assert path.read_bytes() == owner_bytes
    assert "system proposal" in (path.parent / "Owner.sbr-update.md").read_text(encoding="utf-8")
    assert result.forked == (PurePosixPath("concepts/Owner.sbr-update.md"),)


def test_dirty_git_tree_aborts_without_touching_or_staging(vault_config: SbrConfig) -> None:
    target = vault_config.vault_path / "ai" / "Existing.md"
    with VaultWriter.open(vault_config) as writer:
        writer.write_batch(
            [
                VaultMutation.write(
                    "ai/Existing.md",
                    _note("ai_existing", ProvenanceClass.AI_GENERATED, "old\n"),
                    ProvenanceClass.AI_GENERATED,
                )
            ],
            message="initial",
        )
        before = target.read_bytes()
        dirty = vault_config.vault_path / "owner-uncommitted.txt"
        dirty.write_text("leave me alone", encoding="utf-8")
        status_before = _git(vault_config.vault_path, "status", "--porcelain").stdout

        with pytest.raises(VaultDirtyError):
            writer.write_batch(
                [
                    VaultMutation.write(
                        "ai/Existing.md",
                        _note("ai_existing", ProvenanceClass.AI_GENERATED, "new\n"),
                        ProvenanceClass.AI_GENERATED,
                    )
                ],
                message="must abort",
            )

    assert target.read_bytes() == before
    assert dirty.read_text(encoding="utf-8") == "leave me alone"
    assert _git(vault_config.vault_path, "status", "--porcelain").stdout == status_before


def test_map_user_sections_are_preserved_without_fork(vault_config: SbrConfig) -> None:
    path = vault_config.vault_path / "maps" / "Dynamics.md"
    old_body = f"generated old\n{START_USER_SECTION}\nowner old\n{END_USER_SECTION}\ntail old\n"
    new_body = f"generated new\n{START_USER_SECTION}\nplaceholder\n{END_USER_SECTION}\ntail new\n"
    with VaultWriter.open(vault_config) as writer:
        writer.write_batch(
            [
                VaultMutation.write(
                    "maps/Dynamics.md",
                    _note("map_dynamics", ProvenanceClass.AI_GENERATED, old_body),
                    ProvenanceClass.AI_GENERATED,
                )
            ],
            message="initial map",
        )
        path.write_text(
            path.read_text(encoding="utf-8").replace("owner old", "owner edited\nverbatim  "),
            encoding="utf-8",
        )
        _git(vault_config.vault_path, "add", ".")
        _git(
            vault_config.vault_path,
            "-c",
            "user.name=Owner",
            "-c",
            "user.email=owner@localhost",
            "commit",
            "-m",
            "owner section edit",
        )
        result = writer.write_batch(
            [
                VaultMutation.write(
                    "maps/Dynamics.md",
                    _note("map_dynamics", ProvenanceClass.AI_GENERATED, new_body),
                    ProvenanceClass.AI_GENERATED,
                )
            ],
            message="refresh map",
        )

    current = path.read_text(encoding="utf-8")
    assert "generated new" in current and "tail new" in current
    assert f"{START_USER_SECTION}\nowner edited\nverbatim  \n{END_USER_SECTION}" in current
    assert not result.forked
    assert not (path.parent / "Dynamics.sbr-update.md").exists()


@pytest.mark.parametrize(
    ("folder", "provenance"),
    [
        ("sources", ProvenanceClass.SOURCE_DERIVED),
        ("concepts", ProvenanceClass.AI_GENERATED),
        ("ai", ProvenanceClass.AI_GENERATED),
        ("maps", ProvenanceClass.AI_GENERATED),
        ("research", ProvenanceClass.EXTERNAL_RESEARCH),
        ("inbox", ProvenanceClass.EXTERNAL_PENDING),
    ],
)
def test_folder_tiers_allow_create_and_valid_update(
    vault_config: SbrConfig, folder: str, provenance: ProvenanceClass
) -> None:
    relpath = f"{folder}/Tier.md"
    with VaultWriter.open(vault_config) as writer:
        writer.write_batch(
            [VaultMutation.write(relpath, _note(f"{folder}_tier", provenance, "first\n"), provenance)],
            message=f"create {folder}",
        )
        second = "first\ncorrection appended\n" if folder == "research" else "second\n"
        result = writer.write_batch(
            [VaultMutation.write(relpath, _note(f"{folder}_tier", provenance, second), provenance)],
            message=f"update {folder}",
        )

    assert second in (vault_config.vault_path / relpath).read_text(encoding="utf-8")
    assert not result.forked


def test_delete_is_allowed_only_in_inbox(vault_config: SbrConfig) -> None:
    with VaultWriter.open(vault_config) as writer:
        writer.write_batch(
            [
                VaultMutation.write(
                    "inbox/proposal.md",
                    _note("proposal", ProvenanceClass.EXTERNAL_PENDING, "review\n"),
                    ProvenanceClass.EXTERNAL_PENDING,
                )
            ],
            message="proposal",
        )
        result = writer.write_batch([VaultMutation.delete("inbox/proposal.md")], message="resolve proposal")
        for folder in ("sources", "concepts", "ai", "maps", "research"):
            with pytest.raises(VaultOwnershipError, match="only in inbox"):
                writer.write_batch([VaultMutation.delete(f"{folder}/x.md")], message="forbidden delete")

    assert result.deleted == (PurePosixPath("inbox/proposal.md"),)
    assert not (vault_config.vault_path / "inbox" / "proposal.md").exists()


def test_sources_are_orphaned_with_note_instead_of_deleted(vault_config: SbrConfig) -> None:
    with VaultWriter.open(vault_config) as writer:
        writer.write_batch(
            [
                VaultMutation.write(
                    "sources/course/Source.md",
                    _note("source_note", ProvenanceClass.SOURCE_DERIVED, "source body\n"),
                    ProvenanceClass.SOURCE_DERIVED,
                )
            ],
            message="source note",
        )
        result = writer.write_batch(
            [VaultMutation.orphan("sources/course/Source.md", reason="source disappeared")],
            message="orphan source",
        )

    old = vault_config.vault_path / "sources" / "course" / "Source.md"
    moved = vault_config.vault_path / "_system" / "orphaned" / "course" / "Source.md"
    assert not old.exists()
    assert "source disappeared" in moved.read_text(encoding="utf-8")
    assert result.orphaned == (PurePosixPath("_system/orphaned/course/Source.md"),)


def test_failure_after_staging_leaves_no_partial_file_or_git_state(vault_config: SbrConfig) -> None:
    with VaultWriter.open(vault_config) as writer:

        def crash() -> None:
            raise RuntimeError("simulated crash")

        with pytest.raises(RuntimeError, match="simulated"):
            writer.write_batch(
                [
                    VaultMutation.write(
                        "concepts/Crash.md",
                        _note("concept_crash", ProvenanceClass.AI_GENERATED, "complete content\n"),
                        ProvenanceClass.AI_GENERATED,
                    )
                ],
                message="will fail",
                before_publish=crash,
            )

        assert not (vault_config.vault_path / "concepts" / "Crash.md").exists()
        assert not list(vault_config.vault_path.rglob(f"{VAULT_STAGE_PREFIX}*"))
        assert _git(vault_config.vault_path, "status", "--porcelain").stdout == ""
        writer.write_batch(
            [
                VaultMutation.write(
                    "concepts/After.md",
                    _note("concept_after", ProvenanceClass.AI_GENERATED, "works\n"),
                    ProvenanceClass.AI_GENERATED,
                )
            ],
            message="next write succeeds",
        )


def test_stale_stage_file_from_a_real_process_kill_self_heals_instead_of_wedging(
    vault_config: SbrConfig,
) -> None:
    """A hard crash (not a Python exception) can leave a ``.sbr-stage-*`` file behind: it was
    written but never renamed over its target, and it was never ``git add``ed. That file must
    not be mistaken for an owner edit on the next call — the writer must sweep it before it
    checks cleanliness, not after, or every future batch is refused forever.
    """
    concepts = vault_config.vault_path / "concepts"
    with VaultWriter.open(vault_config) as writer:
        writer.write_batch(
            [
                VaultMutation.write(
                    "concepts/A.md",
                    _note("concept_a", ProvenanceClass.AI_GENERATED, "first\n"),
                    ProvenanceClass.AI_GENERATED,
                )
            ],
            message="first",
        )

    # Simulate what a real process kill leaves behind: a stage file that was fsynced but never
    # reached its target rename, sitting untracked in the vault's working tree.
    stale = concepts / f"{VAULT_STAGE_PREFIX}A.md-deadbeefdeadbeef"
    stale.write_bytes(b"partial content from a killed process")
    assert _git(vault_config.vault_path, "status", "--porcelain").stdout.strip()

    with VaultWriter.open(vault_config) as writer:
        result = writer.write_batch(
            [
                VaultMutation.write(
                    "concepts/B.md",
                    _note("concept_b", ProvenanceClass.AI_GENERATED, "second\n"),
                    ProvenanceClass.AI_GENERATED,
                )
            ],
            message="second",
        )

    assert result.written == (PurePosixPath("concepts/B.md"),)
    assert not stale.exists()
    assert _git(vault_config.vault_path, "status", "--porcelain").stdout == ""


def test_vault_git_repository_is_independent_and_activity_is_recorded(
    make_config: Callable[..., SbrConfig], tmp_path: Path
) -> None:
    code = tmp_path / "code"
    code.mkdir()
    (code / ".gitignore").write_text("/vault/\n", encoding="utf-8")
    _git(code, "init")
    _git(code, "add", ".gitignore")
    _git(code, "-c", "user.name=Test", "-c", "user.email=test@localhost", "commit", "-m", "code initial")
    code_head = _git(code, "rev-parse", "HEAD").stdout.strip()
    config = make_config(vault=str(code / "vault"))

    with VaultWriter.open(config) as writer:
        result = writer.write_batch(
            [
                VaultMutation.write(
                    "ai/Independent.md",
                    _note("ai_independent", ProvenanceClass.AI_GENERATED, "vault only\n"),
                    ProvenanceClass.AI_GENERATED,
                )
            ],
            message="vault initial",
        )
        activity = writer.db.conn.execute(
            "SELECT status FROM activity WHERE activity_id = ?", (result.activity_id,)
        ).fetchone()

    assert _git(code, "rev-parse", "HEAD").stdout.strip() == code_head
    assert _git(code, "status", "--porcelain").stdout == ""
    assert (
        _git(code / "vault", "rev-parse", "--show-toplevel").stdout.strip().replace("\\", "/").endswith("/code/vault")
    )
    assert _git(code / "vault", "log", "--format=%s").stdout.splitlines() == ["vault initial"]
    assert activity == ("succeeded",)
