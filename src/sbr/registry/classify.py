"""Config-driven file classification (T-P2-04, ingestion stage S4).

Classification is a direct batch pass over hashed blobs that still have no
format or remain ``unknown``.  Exactly one current path observation is selected
per blob so source bytes are read only through :class:`sbr.sourcefs.SourceFS`.
Strong configured signatures override misleading extensions; configured path
rules then identify junk and tool-generated trees.  PDF encryption detection is
a bounded marker scan only: this stage never parses, opens, executes, or attempts
to decrypt source content.
"""

from __future__ import annotations

import logging
import re
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from typing import Any, BinaryIO, Final

from sbr import __version__
from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.connection import transaction
from sbr.db.registry import RegistryDB
from sbr.obs.logging import get_logger
from sbr.provenance import ProvenanceStore
from sbr.schemas import BlobRecord, PathObservation
from sbr.schemas.registry import KnowledgeClass, ObservationState
from sbr.sourcefs import SourceFS, SourceStat

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RULES_PATH: Final = REPO_ROOT / "config" / "classification.toml"
CLASSIFY_PRODUCER: Final = "sbr.registry.classify"
CLASSIFY_STAGE: Final = "classify"
_PDF_ENCRYPT = re.compile(rb"/Encrypt(?![A-Za-z0-9])")
_LOG = get_logger(__name__)


class ClassificationConfigError(ValueError):
    """The dedicated classification rules file is missing or invalid."""


class SourceChangedError(OSError):
    """A selected observation no longer describes the source file."""


@dataclass(frozen=True, slots=True)
class SignatureRule:
    prefix: bytes
    magic_type: str
    format: str
    knowledge_class: KnowledgeClass
    offset: int = 0
    preserve_extensions: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ClassificationRules:
    version: str
    header_bytes: int
    pdf_encryption_scan_bytes: int
    zero_byte_is_junk: bool
    extensions: Mapping[str, KnowledgeClass]
    junk_components: frozenset[str]
    junk_name_prefixes: tuple[str, ...]
    junk_names: frozenset[str]
    tool_artifact_components: frozenset[str]
    signatures: tuple[SignatureRule, ...]


@dataclass(frozen=True, slots=True)
class ClassificationDecision:
    magic_type: str | None
    format: str
    knowledge_class: KnowledgeClass
    encrypted: bool


@dataclass(frozen=True, slots=True)
class UnknownClassification:
    blob_id: str
    root_id: str
    relpath: str
    extension: str


@dataclass(frozen=True, slots=True)
class ClassificationFailure:
    blob_id: str
    error: str


@dataclass(frozen=True, slots=True)
class ClassificationRunResult:
    activity_id: str
    considered: int
    updated: int
    unknowns: tuple[UnknownClassification, ...]
    failures: tuple[ClassificationFailure, ...]


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ClassificationConfigError(f"{name} must be a TOML table")
    return value


def _string_list(value: object, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ClassificationConfigError(f"{name} must be an array of strings")
    return value


def _positive_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ClassificationConfigError(f"{name} must be a positive integer")
    return value


def _extension(value: str, name: str) -> str:
    normalized = value.casefold()
    if not normalized.startswith(".") or len(normalized) == 1 or "/" in normalized or "\\" in normalized:
        raise ClassificationConfigError(f"{name} contains invalid extension {value!r}")
    return normalized


def load_classification_rules(path: Path = DEFAULT_RULES_PATH) -> ClassificationRules:
    """Load and validate the standalone TOML classification rules."""
    try:
        with path.open("rb") as stream:
            raw = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ClassificationConfigError(f"could not load classification rules: {type(exc).__name__}") from exc

    version = raw.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ClassificationConfigError("version must be a non-empty string")
    header_bytes = _positive_int(raw.get("header_bytes"), "header_bytes")
    pdf_scan_bytes = _positive_int(raw.get("pdf_encryption_scan_bytes"), "pdf_encryption_scan_bytes")
    zero_byte = raw.get("zero_byte_is_junk")
    if not isinstance(zero_byte, bool):
        raise ClassificationConfigError("zero_byte_is_junk must be a boolean")

    extension_classes: dict[str, KnowledgeClass] = {}
    for class_name, configured in _mapping(raw.get("extensions"), "extensions").items():
        try:
            knowledge_class = KnowledgeClass(class_name)
        except ValueError as exc:
            raise ClassificationConfigError(f"extensions has unknown knowledge class {class_name!r}") from exc
        for value in _string_list(configured, f"extensions.{class_name}"):
            ext = _extension(value, f"extensions.{class_name}")
            if ext in extension_classes:
                raise ClassificationConfigError(f"extension {ext!r} is assigned more than once")
            extension_classes[ext] = knowledge_class

    path_rules = _mapping(raw.get("path_rules"), "path_rules")

    signatures_raw = raw.get("signatures")
    if not isinstance(signatures_raw, list):
        raise ClassificationConfigError("signatures must be an array of tables")
    signatures: list[SignatureRule] = []
    for index, item in enumerate(signatures_raw):
        sig = _mapping(item, f"signatures[{index}]")
        prefix_hex = sig.get("prefix_hex")
        if not isinstance(prefix_hex, str):
            raise ClassificationConfigError(f"signatures[{index}].prefix_hex must be a string")
        try:
            prefix = bytes.fromhex(prefix_hex)
        except ValueError as exc:
            raise ClassificationConfigError(f"signatures[{index}].prefix_hex is not valid hex") from exc
        if not prefix:
            raise ClassificationConfigError(f"signatures[{index}].prefix_hex must not be empty")
        offset = sig.get("offset", 0)
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise ClassificationConfigError(f"signatures[{index}].offset must be a non-negative integer")
        if offset + len(prefix) > header_bytes:
            raise ClassificationConfigError(f"signatures[{index}] exceeds header_bytes")
        magic_type = sig.get("magic_type")
        format_name = sig.get("format")
        signature_class_name = sig.get("knowledge_class")
        if (
            not isinstance(magic_type, str)
            or not magic_type
            or not isinstance(format_name, str)
            or not format_name
            or not isinstance(signature_class_name, str)
            or not signature_class_name
        ):
            raise ClassificationConfigError(f"signatures[{index}] needs magic_type, format, and knowledge_class")
        try:
            knowledge_class = KnowledgeClass(signature_class_name)
        except ValueError as exc:
            raise ClassificationConfigError(
                f"signatures[{index}] has unknown knowledge class {signature_class_name!r}"
            ) from exc
        preserved = frozenset(
            _extension(value, f"signatures[{index}].preserve_extensions")
            for value in _string_list(sig.get("preserve_extensions", []), "preserve_extensions")
        )
        signatures.append(SignatureRule(prefix, magic_type, format_name, knowledge_class, offset, preserved))

    def folded_set(key: str) -> frozenset[str]:
        return frozenset(value.casefold() for value in _string_list(path_rules.get(key), f"path_rules.{key}"))

    return ClassificationRules(
        version=version,
        header_bytes=header_bytes,
        pdf_encryption_scan_bytes=pdf_scan_bytes,
        zero_byte_is_junk=zero_byte,
        extensions=extension_classes,
        junk_components=folded_set("junk_components"),
        junk_name_prefixes=tuple(folded_set("junk_name_prefixes")),
        junk_names=folded_set("junk_names"),
        tool_artifact_components=folded_set("tool_artifact_components"),
        signatures=tuple(signatures),
    )


def _suffix(relpath: str) -> str:
    return PureWindowsPath(relpath).suffix.casefold()


def _signature(header: bytes, rules: ClassificationRules) -> SignatureRule | None:
    return next(
        (signature for signature in rules.signatures if header[signature.offset :].startswith(signature.prefix)),
        None,
    )


def _path_override(relpath: str, rules: ClassificationRules) -> KnowledgeClass | None:
    path = PureWindowsPath(relpath)
    components = {part.casefold() for part in path.parts[:-1]}
    name = path.name.casefold()
    if (
        components & rules.junk_components
        or name in rules.junk_names
        or any(name.startswith(prefix) for prefix in rules.junk_name_prefixes)
    ):
        return KnowledgeClass.JUNK
    if components & rules.tool_artifact_components:
        return KnowledgeClass.TOOL_ARTIFACT
    return None


def _matches_observation(stat: SourceStat, observation: PathObservation, blob: BlobRecord) -> bool:
    return (
        stat.is_file
        and not stat.is_link
        and stat.size == observation.size == blob.size
        and stat.mtime_ns == observation.mtime_ns
    )


def _classify_stream(
    stream: BinaryIO,
    blob: BlobRecord,
    observation: PathObservation,
    rules: ClassificationRules,
) -> ClassificationDecision:
    header = stream.read(rules.header_bytes)
    extension = _suffix(observation.relpath)
    extension_class = rules.extensions.get(extension, KnowledgeClass.UNKNOWN)
    signature = _signature(header, rules)

    if blob.size == 0 and rules.zero_byte_is_junk:
        magic_type = "application/x-empty"
        format_name = "empty"
        knowledge_class = KnowledgeClass.JUNK
    elif signature is not None:
        magic_type = signature.magic_type
        if extension in signature.preserve_extensions and extension_class is not KnowledgeClass.UNKNOWN:
            format_name = extension.removeprefix(".")
            knowledge_class = extension_class
        else:
            format_name = signature.format
            knowledge_class = signature.knowledge_class
    else:
        magic_type = None
        format_name = extension.removeprefix(".") or "unknown"
        knowledge_class = extension_class

    override = _path_override(observation.relpath, rules)
    if override is not None:
        knowledge_class = override

    encrypted = False
    if signature is not None and signature.format == "pdf" and knowledge_class is KnowledgeClass.DOCUMENT:
        scan_bytes = min(blob.size, rules.pdf_encryption_scan_bytes)
        stream.seek(blob.size - scan_bytes)
        encrypted = _PDF_ENCRYPT.search(stream.read(scan_bytes)) is not None

    return ClassificationDecision(magic_type, format_name, knowledge_class, encrypted)


def _classify_blob(
    fs: SourceFS,
    blob: BlobRecord,
    observation: PathObservation,
    rules: ClassificationRules,
) -> ClassificationDecision:
    before = fs.stat(observation.root_id, observation.relpath)
    if not _matches_observation(before, observation, blob):
        raise SourceChangedError("source metadata changed before classification")
    with fs.open_binary(observation.root_id, observation.relpath) as stream:
        decision = _classify_stream(stream, blob, observation, rules)
    after = fs.stat(observation.root_id, observation.relpath)
    if not _matches_observation(after, observation, blob):
        raise SourceChangedError("source metadata changed during classification")
    return decision


def _error_label(exc: Exception) -> str:
    if isinstance(exc, OSError):
        return f"{type(exc).__name__}: errno={exc.errno} winerror={getattr(exc, 'winerror', None)}"
    return type(exc).__name__


def classify_pending(
    config: SbrConfig,
    db: RegistryDB,
    *,
    rules_path: Path = DEFAULT_RULES_PATH,
    source_fs: SourceFS | None = None,
    owner: str = "system:classifier",
    clock: Callable[[], datetime] = _utcnow,
    logger: logging.Logger = _LOG,
) -> ClassificationRunResult:
    """Classify every hashed blob that has no format or still has class ``unknown``."""
    rules = load_classification_rules(rules_path)
    fs = source_fs or SourceFS(config)
    blobs = db.repo(reg.BLOB)
    observations = db.repo(reg.PATH_OBSERVATION)
    candidates = sorted(
        (blob for blob in blobs.find() if blob.format is None or blob.knowledge_class is KnowledgeClass.UNKNOWN),
        key=lambda blob: blob.blob_id,
    )
    current_by_blob: dict[str, list[PathObservation]] = {}
    for observation in observations.find({"state": ObservationState.PRESENT}):
        if observation.blob_id is not None:
            current_by_blob.setdefault(observation.blob_id, []).append(observation)
    for rows in current_by_blob.values():
        rows.sort(key=lambda row: (row.root_id, row.relpath))

    unknowns: list[UnknownClassification] = []
    failures: list[ClassificationFailure] = []
    updated = 0
    provenance = ProvenanceStore(db.conn, clock=clock)
    with provenance.activity(
        kind=CLASSIFY_STAGE,
        producer=CLASSIFY_PRODUCER,
        producer_version=__version__,
        agent=owner,
        params={"rules_version": rules.version, "rules_file": rules_path.name},
    ) as activity:
        for blob in candidates:
            observed_paths = current_by_blob.get(blob.blob_id)
            if not observed_paths:
                failures.append(ClassificationFailure(blob.blob_id, "NoCurrentObservation"))
                continue
            observation = observed_paths[0]
            try:
                decision = _classify_blob(fs, blob, observation, rules)
                classified = blob.model_copy(
                    update={
                        "magic_type": decision.magic_type,
                        "format": decision.format,
                        "knowledge_class": decision.knowledge_class,
                        "encrypted": decision.encrypted,
                        "activity_id": activity.activity_id,
                    }
                )
                with transaction(db.conn):
                    blobs.upsert(classified)
                activity.outputs.append(blob.blob_id)
                updated += 1
                if decision.knowledge_class is KnowledgeClass.UNKNOWN:
                    unknowns.append(
                        UnknownClassification(
                            blob.blob_id,
                            observation.root_id,
                            observation.relpath,
                            _suffix(observation.relpath) or "<none>",
                        )
                    )
            except Exception as exc:  # noqa: BLE001 - one unreadable source must not stop the batch
                label = _error_label(exc)
                failures.append(ClassificationFailure(blob.blob_id, label))
                logger.warning(
                    "source content could not be classified",
                    extra={"sbr": {"stage": CLASSIFY_STAGE, "subject_id": blob.blob_id, "error": label}},
                )

    return ClassificationRunResult(
        activity_id=activity.activity_id,
        considered=len(candidates),
        updated=updated,
        unknowns=tuple(unknowns),
        failures=tuple(failures),
    )


__all__ = [
    "CLASSIFY_PRODUCER",
    "CLASSIFY_STAGE",
    "DEFAULT_RULES_PATH",
    "ClassificationConfigError",
    "ClassificationDecision",
    "ClassificationFailure",
    "ClassificationRules",
    "ClassificationRunResult",
    "SignatureRule",
    "SourceChangedError",
    "UnknownClassification",
    "classify_pending",
    "load_classification_rules",
]
