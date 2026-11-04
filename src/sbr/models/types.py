"""Request, response and call-record types of the model gateway (T-P7-01, docs/17)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field

from sbr.config import Sensitivity
from sbr.schemas.base import NonNeg, StrictModel, UtcDatetime
from sbr.schemas.provenance import ProvenanceClass


class Capability(StrEnum):
    GENERATE = "generate"  # chat/text completion
    STRUCTURED = "structured"  # native JSON-schema constrained decoding
    EMBED = "embed"
    RERANK = "rerank"
    VISION = "vision"  # image input


class Locality(StrEnum):
    LOCAL = "local"  # in-process or loopback only
    REMOTE = "remote"  # leaves the host: refused in this phase (ADR-039/ADR-040)


#: Capability a role needs from its provider. A role is usable only if its provider implements this.
ROLE_CAPABILITY: Mapping[str, Capability] = {
    "embed": Capability.EMBED,
    "rerank": Capability.RERANK,
    "ocr": Capability.VISION,
    "math_ocr": Capability.VISION,
    "layout": Capability.VISION,
    "vision": Capability.VISION,
    "classify": Capability.GENERATE,
    "extract": Capability.GENERATE,
    "reason": Capability.GENERATE,
    "judge": Capability.GENERATE,
    "research": Capability.GENERATE,
}


@dataclass(frozen=True, slots=True)
class Message:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """One generation call. ``sensitivity`` is required: the gateway never guesses a content class."""

    messages: tuple[Message, ...]
    sensitivity: Sensitivity
    images: tuple[bytes, ...] = ()
    temperature: float | None = None
    max_tokens: int | None = None
    prompt_version: str | None = None
    subject_id: str | None = None  # provenance pointer (blob, KU, crop id); recorded, never interpreted


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    texts: tuple[str, ...]
    sensitivity: Sensitivity
    subject_id: str | None = None


@dataclass(frozen=True, slots=True)
class Usage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class ProviderGeneration:
    """What an adapter returns for a generation."""

    text: str
    model_version: str | None = None  # the model id the server reports (resolved version)
    usage: Usage = field(default_factory=Usage)
    finish_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderEmbedding:
    vectors: tuple[tuple[float, ...], ...]
    model_version: str | None = None
    usage: Usage = field(default_factory=Usage)


class CallRecord(StrictModel):
    """Accounting and provenance for one gateway call. Contains hashes and sizes, never content (docs/22 §3)."""

    call_id: str
    started_at: UtcDatetime
    role: str
    operation: Literal["generate", "generate_structured", "embed"]
    provider: str | None
    provider_kind: str | None
    model: str | None
    model_version: str | None
    locality: Locality | None
    sensitivity: Sensitivity
    subject_id: str | None
    prompt_version: str | None
    input_sha256: str
    input_chars: NonNeg
    output_sha256: str | None
    output_chars: NonNeg | None
    prompt_tokens: NonNeg | None
    completion_tokens: NonNeg | None
    cost_usd: float = Field(ge=0)
    latency_ms: float = Field(ge=0)
    attempts: NonNeg
    cache_hit: bool
    candidates_tried: list[str]
    outcome: Literal["ok", "refused", "failed"]
    error_type: str | None
    provenance_class: ProvenanceClass = ProvenanceClass.AI_GENERATED


@dataclass(frozen=True, slots=True)
class GenerationResult:
    text: str
    record: CallRecord
    parsed: Any = None  # the validated object for generate_structured


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    vectors: tuple[tuple[float, ...], ...]
    record: CallRecord

    @property
    def dim(self) -> int:
        return len(self.vectors[0]) if self.vectors else 0


def sha256_hex(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def request_fingerprint(request: GenerationRequest, schema: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Content-addressed description of a request (used for the input hash and the cache key)."""
    return {
        "messages": [[m.role, m.content] for m in request.messages],
        "images": [sha256_hex(img) for img in request.images],
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "prompt_version": request.prompt_version,
        "schema": schema,
    }
