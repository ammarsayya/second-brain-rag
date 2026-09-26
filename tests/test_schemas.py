"""T-P1-05: core models round-trip JSON, reject invalid records, and match the exported JSON Schemas."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from sbr.docir import DocIR, DocumentInfo, ExtractorRef, Page
from sbr.ids import hash_bytes, new_id
from sbr.schemas import (
    Activity,
    ActivityStatus,
    ArchiveMember,
    BlobClassification,
    BlobRecord,
    BlobRelation,
    ChangeEvent,
    DerivedFrom,
    Locator,
    PathObservation,
    ProvenanceClass,
    RunRecord,
    RunStatus,
    ScanRecord,
    SourceRootRecord,
    WorkItem,
    WorkItemState,
    WorkOutput,
)
from sbr.schemas.export import ALL_EXPORTED_MODELS, render_schemas
from sbr.schemas.registry import ArchiveMemberStatus, ChangeType, RelationType, RootKind

ROOT = Path(__file__).resolve().parent.parent
T0 = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
B1, B2 = hash_bytes(b"one"), hash_bytes(b"two")
ACT, SCAN, OBS = new_id("act"), new_id("scan"), new_id("obs")


def samples() -> list[BaseModel]:
    loc = Locator(
        blob_id=B1,
        representation="pdf",
        page_index=47,
        page_label="S. 40",
        bbox=(10.0, 20.0, 300.0, 80.5),
        block_id=new_id("blk"),
        char_span=(3, 17),
        equation_label="(3-114)",
    )
    return [
        Activity(
            activity_id=ACT,
            kind="scan",
            producer="sbr.scan",
            producer_version="0.1.0",
            agent="system:scanner",
            run_id=new_id("run"),
            started_at=T0,
            ended_at=T0 + timedelta(seconds=5),
            status=ActivityStatus.SUCCEEDED,
            inputs=[B1],
            outputs=[OBS],
        ),
        Activity(
            activity_id=new_id("act"),
            kind="approve",
            producer="owner",
            producer_version="n/a",
            agent="user:owner",
            started_at=T0,
        ),
        Activity(
            activity_id=new_id("act"),
            kind="extract",
            producer="layout",
            producer_version="2.0",
            agent="model:local/layout@1",
            started_at=T0,
        ),
        loc,
        DerivedFrom(entity_id=new_id("ku"), source_entity_id=B1, locator=loc),
        SourceRootRecord(root_id="mbi", path="D:\\MBI-BRAIN", kind=RootKind.UNIVERSITY, read_only=True, added_at=T0),
        ScanRecord(scan_id=SCAN, root_id="mbi", started_at=T0, code_version="0.1.0", activity_id=ACT),
        BlobRecord(blob_id=B1, size=3, first_seen_scan=SCAN, last_seen_scan=SCAN, activity_id=ACT),
        PathObservation(
            obs_id=OBS,
            root_id="mbi",
            relpath="\u00dcbung\\blatt.pdf",
            relpath_raw="U\u0308bung\\blatt.pdf",
            display_name="blatt.pdf",
            blob_id=B1,
            size=3,
            mtime_ns=1,
            first_seen_scan=SCAN,
            last_seen_scan=SCAN,
            folder_tokens=["\u00fcbung"],
            activity_id=ACT,
        ),
        ArchiveMember(
            container_blob=B1,
            member_path="a/b.pdf",
            member_name_display="b.pdf",
            member_size=9,
            member_blob=B2,
            status=ArchiveMemberStatus.EXTRACTED_NEW,
            activity_id=ACT,
        ),
        BlobClassification(
            blob_id=B1, genre="lecture_script", genre_confidence=0.8, rules_version="r1", activity_id=ACT
        ),
        BlobRelation(
            src_blob=B1,
            dst_blob=B2,
            type=RelationType.TWIN_CANDIDATE,
            confidence=0.6,
            evidence={"name_similarity": 0.9},
            activity_id=ACT,
        ),
        ChangeEvent(scan_id=SCAN, type=ChangeType.MOVED, obs_id=OBS, blob_id=B1, activity_id=ACT),
        WorkItem(
            job_id=new_id("job"),
            subject_id=B1,
            stage="extract_text",
            stage_version="0.1.0+cfg.abc123",
            state=WorkItemState.LEASED,
            priority=1,
            wave="wave1",
            attempts=1,
            max_attempts=5,
            not_before_ms=0,
            lease_owner="system:worker-1",
            lease_token="lt_deadbeef",  # noqa: S106 - not a credential, a lease fencing token
            lease_expires_ms=1_700_000_000_000,
            created_at=T0,
            updated_at=T0,
        ),
        WorkOutput(manifest_id=new_id("man"), job_id=new_id("job"), artifacts={"docir": B2}, created_at=T0),
        RunRecord(
            run_id=new_id("run"),
            command="scan",
            config_hash="sha256:" + "0" * 64,
            code_version="0.1.0",
            git_sha="abcdef1+dirty",
            pid=1,
            started_at=T0,
            ended_at=T0 + timedelta(seconds=1),
            status=RunStatus.SUCCEEDED,
            exit_code=0,
            counts={"files": 3},
        ),
        DocIR(
            blob_id=B1,
            document=DocumentInfo(title="Skript", genre="lecture_script", lang=["de"], pages=1),
            extractors=[ExtractorRef(name="pymupdf", version="1.28.2")],
            pages=[Page(index=0, label="1", width=595.0, height=842.0)],
        ),
    ]


@pytest.mark.parametrize("obj", samples(), ids=lambda o: type(o).__name__)
def test_json_round_trip(obj: BaseModel) -> None:
    text = obj.model_dump_json()
    again = type(obj).model_validate_json(text)
    assert again == obj
    assert again.model_dump_json() == text


def test_every_exported_model_has_a_sample() -> None:
    assert {type(o) for o in samples()} == set(ALL_EXPORTED_MODELS)


def test_timestamps_serialize_as_utc() -> None:
    act = samples()[0]
    assert json.loads(act.model_dump_json())["started_at"].endswith("Z")


def _act(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "activity_id": ACT,
        "kind": "scan",
        "producer": "p",
        "producer_version": "1",
        "agent": "system:x",
        "started_at": T0,
    }
    base.update(over)
    return base


@pytest.mark.parametrize(
    ("over", "needle"),
    [
        ({"unexpected": 1}, "Extra inputs"),
        ({"activity_id": "act_123"}, "pattern"),
        ({"activity_id": new_id("run")}, "pattern"),
        ({"agent": "somebody"}, "pattern"),
        ({"kind": "Scan Stage"}, "pattern"),
        ({"started_at": datetime(2026, 9, 24, 12, 0)}, "timezone"),
        ({"started_at": datetime(2026, 9, 24, 12, 0, tzinfo=timezone(timedelta(hours=2)))}, "UTC"),
        ({"ended_at": T0 - timedelta(seconds=1), "status": ActivityStatus.FAILED}, "precedes"),
        ({"ended_at": T0}, "running activity"),
        ({"status": ActivityStatus.SUCCEEDED}, "needs ended_at"),
        ({"inputs": ["not-an-entity"]}, "pattern"),
    ],
)
def test_activity_rejects_invalid(over: dict[str, Any], needle: str) -> None:
    with pytest.raises(ValidationError, match=needle):
        Activity(**_act(**over))


def test_strict_types_do_not_coerce() -> None:
    with pytest.raises(ValidationError):
        BlobRecord(blob_id=B1, size="3", first_seen_scan=SCAN, last_seen_scan=SCAN, activity_id=ACT)  # type: ignore[arg-type]


def test_models_are_immutable() -> None:
    blob = BlobRecord(blob_id=B1, size=3, first_seen_scan=SCAN, last_seen_scan=SCAN, activity_id=ACT)
    with pytest.raises(ValidationError):
        blob.size = 4  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "needle"),
    [
        ({"bbox": (10.0, 20.0, 5.0, 30.0), "page_index": 1}, "x0 <= x1"),
        ({"bbox": (0.0, 0.0, 1.0, 1.0)}, "requires page_index"),
        ({"char_span": (5, 2), "block_id": new_id("blk")}, "end precedes"),
        ({"char_span": (1, 2)}, "requires block_id"),
        ({"page_index": -1}, "greater than or equal"),
        ({"blob_id": "sha:abc"}, "pattern"),
    ],
)
def test_locator_rejects_invalid(kwargs: dict[str, Any], needle: str) -> None:
    base: dict[str, Any] = {"blob_id": B1, "representation": "pdf"}
    base.update(kwargs)
    with pytest.raises(ValidationError, match=needle):
        Locator(**base)


def test_registry_invariants() -> None:
    with pytest.raises(ValidationError, match="read_only must be true"):
        SourceRootRecord(root_id="mbi", path="D:\\x", kind=RootKind.UNIVERSITY, read_only=False, added_at=T0)
    with pytest.raises(ValidationError, match="NFC"):
        PathObservation(
            obs_id=OBS,
            root_id="mbi",
            relpath="U\u0308bung",
            relpath_raw="U\u0308bung",
            display_name="x",
            size=0,
            mtime_ns=0,
            first_seen_scan=SCAN,
            last_seen_scan=SCAN,
            activity_id=ACT,
        )
    with pytest.raises(ValidationError, match="distinct"):
        BlobRelation(src_blob=B1, dst_blob=B1, type=RelationType.TWIN_OF, confidence=1.0, activity_id=ACT)
    with pytest.raises(ValidationError, match="derived from itself"):
        DerivedFrom(entity_id=B1, source_entity_id=B1)


def test_provenance_classes_are_the_documented_seven() -> None:
    assert {c.value for c in ProvenanceClass} == {
        "SOURCE_DERIVED",
        "USER_AUTHORED",
        "USER_ANNOTATION",
        "AI_GENERATED",
        "EXTERNAL_PENDING",
        "EXTERNAL_RESEARCH",
        "MODEL_KNOWLEDGE",
    }


def test_exported_schemas_are_current() -> None:
    """Snapshot: schemas/*.json must equal the rendered models. Regenerate: uv run python tools/export_schemas.py."""
    rendered = render_schemas()
    on_disk = {p.name: p.read_text(encoding="utf-8") for p in (ROOT / "schemas").glob("*.json")}
    assert on_disk == rendered


def test_export_tool_check_mode() -> None:
    res = subprocess.run(
        [sys.executable, "tools/export_schemas.py", "--check"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    assert res.returncode == 0, res.stdout + res.stderr
