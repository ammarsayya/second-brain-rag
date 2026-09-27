"""Atomic, append-only artifact storage (T-P4-02, PV-6, TS-ART).

Published artifacts are addressed by the source ``blob_id`` and the exact
``extractor@version`` that produced them.  A complete version directory appears in one
rename; interrupted writes remain isolated under ``.staging`` until an explicit GC.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Final

from sbr.config import SbrConfig
from sbr.ids import hash_bytes, is_blob_id
from sbr.safety import assert_writable

MANIFEST_NAME: Final = "manifest.json"
MANIFEST_VERSION: Final = 1
_EXTRACTOR_VERSION_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}@[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
_CLOCK_SKEW_TOLERANCE_SECONDS: Final = 0.25


class ArtifactError(RuntimeError):
    """Base class for artifact-store failures."""


class ArtifactConflictError(ArtifactError):
    """A published immutable version exists with different content."""


@dataclass(frozen=True, slots=True)
class ArtifactFile:
    """Integrity metadata for one file in an artifact version."""

    blob_id: str
    size: int

    def to_dict(self) -> dict[str, str | int]:
        return {"blob_id": self.blob_id, "size": self.size}

    @classmethod
    def from_dict(cls, value: object) -> ArtifactFile:
        if not isinstance(value, dict) or set(value) != {"blob_id", "size"}:
            raise ArtifactError("invalid artifact-file manifest entry")
        blob_id = value["blob_id"]
        size = value["size"]
        if not isinstance(blob_id, str) or not is_blob_id(blob_id):
            raise ArtifactError("invalid artifact-file blob_id")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ArtifactError("invalid artifact-file size")
        return cls(blob_id=blob_id, size=size)


@dataclass(frozen=True, slots=True)
class ArtifactManifest:
    """Deterministic manifest for one immutable ``(blob, extractor@version)`` directory."""

    blob_id: str
    extractor_version: str
    files: dict[str, ArtifactFile]
    manifest_version: int = MANIFEST_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest_version": self.manifest_version,
            "blob_id": self.blob_id,
            "extractor_version": self.extractor_version,
            "files": {name: entry.to_dict() for name, entry in sorted(self.files.items())},
        }

    def to_json_bytes(self) -> bytes:
        return (json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()

    @classmethod
    def from_json_bytes(cls, raw: bytes) -> ArtifactManifest:
        try:
            value: Any = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ArtifactError("artifact manifest is not valid UTF-8 JSON") from exc
        if not isinstance(value, dict) or set(value) != {
            "manifest_version",
            "blob_id",
            "extractor_version",
            "files",
        }:
            raise ArtifactError("artifact manifest has unexpected fields")
        if value["manifest_version"] != MANIFEST_VERSION:
            raise ArtifactError(f"unsupported artifact manifest version {value['manifest_version']!r}")
        blob_id = value["blob_id"]
        extractor_version = value["extractor_version"]
        files = value["files"]
        _validate_blob_id(blob_id)
        _validate_extractor_version(extractor_version)
        if not isinstance(files, dict) or not files:
            raise ArtifactError("artifact manifest files must be a non-empty object")
        parsed: dict[str, ArtifactFile] = {}
        for name, entry in files.items():
            if not isinstance(name, str):
                raise ArtifactError("artifact manifest file names must be strings")
            _validate_artifact_name(name)
            parsed[name] = ArtifactFile.from_dict(entry)
        return cls(blob_id=blob_id, extractor_version=extractor_version, files=parsed)


def _validate_blob_id(blob_id: object) -> str:
    if not isinstance(blob_id, str) or not is_blob_id(blob_id):
        raise ValueError(f"not a BLAKE3 blob id: {blob_id!r}")
    return blob_id


def _validate_extractor_version(extractor_version: object) -> str:
    if not isinstance(extractor_version, str) or not _EXTRACTOR_VERSION_RE.fullmatch(extractor_version):
        raise ValueError("extractor version must be a safe ASCII 'extractor@version' path component")
    return extractor_version


def _validate_artifact_name(name: str) -> PurePosixPath:
    if "\\" in name:
        raise ValueError(f"artifact name must use '/' separators: {name!r}")
    path = PurePosixPath(name)
    if (
        not name
        or path.is_absolute()
        or str(path) != name
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.name == MANIFEST_NAME
    ):
        raise ValueError(f"unsafe or reserved artifact name: {name!r}")
    return path


class ArtifactStore:
    """Store immutable artifact versions below the configured rebuildable ``var`` root."""

    def __init__(self, config: SbrConfig) -> None:
        self.config = config
        self.root = config.var_path / "artifacts"
        self.staging_root = self.root / ".staging"

    def version_path(self, blob_id: str, extractor_version: str) -> Path:
        """Return the published path without creating it.

        The two-hex shard is the canonical layout in docs/18 and keeps a single
        directory from accumulating every source blob.
        """
        digest = _validate_blob_id(blob_id).removeprefix("b3:")
        version = _validate_extractor_version(extractor_version)
        return self.root / digest[:2] / digest / version

    def write(
        self,
        blob_id: str,
        extractor_version: str,
        files: Mapping[str, bytes],
    ) -> ArtifactManifest:
        """Publish a complete immutable version, or return an identical existing one.

        No exception path removes staging data: an interrupted or failed attempt is
        observable and recoverable, and only :meth:`gc_orphans` may collect it.
        """
        target = self.version_path(blob_id, extractor_version)
        if not files:
            raise ValueError("an artifact version must contain at least one file")

        normalized: dict[str, tuple[PurePosixPath, bytes]] = {}
        entries: dict[str, ArtifactFile] = {}
        for name, content in files.items():
            if not isinstance(name, str) or not isinstance(content, bytes):
                raise TypeError("artifact files must map string names to bytes")
            rel = _validate_artifact_name(name)
            normalized[name] = (rel, content)
            entries[name] = ArtifactFile(blob_id=hash_bytes(content), size=len(content))
        manifest = ArtifactManifest(blob_id=blob_id, extractor_version=extractor_version, files=entries)

        if target.exists():
            return self._match_existing(target, manifest)

        assert_writable(self.root, self.config)
        assert_writable(target, self.config)
        self.staging_root.mkdir(parents=True, exist_ok=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        stage = self._new_stage(target.parent.name, extractor_version)

        for _, (rel, content) in sorted(normalized.items()):
            destination = stage.joinpath(*rel.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            self._write_durable(destination, content)
        self._write_durable(stage / MANIFEST_NAME, manifest.to_json_bytes())

        try:
            stage.rename(target)
        except OSError:
            if target.exists():
                return self._match_existing(target, manifest)
            raise
        return manifest

    def read_manifest(self, blob_id: str, extractor_version: str) -> ArtifactManifest:
        return self._read_manifest_at(self.version_path(blob_id, extractor_version))

    def list_orphans(self, *, older_than_seconds: float = 0) -> list[Path]:
        """List abandoned staging directories without mutating the store.

        A small clock-skew tolerance is added to the cutoff: a directory's filesystem mtime and Python's
        ``time.time()`` can come from clocks with different resolution/rounding (observed on Windows NTFS),
        so a directory created microseconds ago could otherwise appear to be *after* a ``cutoff`` computed a
        moment later and be skipped by ``older_than_seconds=0`` - the whole point of that default (list
        everything currently orphaned, right now) being defeated by clock granularity rather than genuine age.
        """
        if older_than_seconds < 0:
            raise ValueError("older_than_seconds must be non-negative")
        if not self.staging_root.is_dir():
            return []
        cutoff = time.time() - older_than_seconds + _CLOCK_SKEW_TOLERANCE_SECONDS
        return sorted(
            (
                path
                for path in self.staging_root.iterdir()
                if path.is_dir() and not path.is_symlink() and path.stat().st_mtime <= cutoff
            ),
            key=lambda path: path.name,
        )

    def gc_orphans(self, *, apply: bool = False, older_than_seconds: float = 0) -> list[Path]:
        """List, or explicitly delete, abandoned staging directories.

        Dry-run is the default.  Published version directories are never candidates.
        """
        orphans = self.list_orphans(older_than_seconds=older_than_seconds)
        if apply:
            for orphan in orphans:
                assert_writable(orphan, self.config)
                shutil.rmtree(orphan)
        return orphans

    @staticmethod
    def _write_durable(path: Path, content: bytes) -> None:
        with path.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())

    def _new_stage(self, digest: str, extractor_version: str) -> Path:
        for _ in range(10):
            stage = self.staging_root / f"{digest}.{extractor_version}.{secrets.token_hex(12)}"
            try:
                stage.mkdir()
            except FileExistsError:
                continue
            return stage
        raise ArtifactError("could not allocate a unique artifact staging directory")

    @staticmethod
    def _read_manifest_at(version_dir: Path) -> ArtifactManifest:
        try:
            return ArtifactManifest.from_json_bytes((version_dir / MANIFEST_NAME).read_bytes())
        except FileNotFoundError as exc:
            raise ArtifactError(f"artifact version has no {MANIFEST_NAME}: {version_dir}") from exc

    def _match_existing(self, target: Path, expected: ArtifactManifest) -> ArtifactManifest:
        actual = self._read_manifest_at(target)
        if actual != expected:
            raise ArtifactConflictError(
                f"artifact version {expected.blob_id}/{expected.extractor_version} is immutable and differs"
            )
        return actual


__all__ = [
    "MANIFEST_NAME",
    "MANIFEST_VERSION",
    "ArtifactConflictError",
    "ArtifactError",
    "ArtifactFile",
    "ArtifactManifest",
    "ArtifactStore",
]
