"""Deterministic in-process mock provider (T-P7-01).

Same request -> same output, across processes and machines (BLAKE2b of the canonical request, no randomness, no
clock). Never touches the network. Outputs are obviously synthetic (``mock:`` prefix) so they cannot be mistaken for
model knowledge. Tests can inject a ``responder`` and scripted failures.
"""

from __future__ import annotations

import hashlib
import math
import struct
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from sbr.models.errors import ProviderError
from sbr.models.provider import ModelProvider, ProbeResult
from sbr.models.types import (
    Capability,
    GenerationRequest,
    Locality,
    ProviderEmbedding,
    ProviderGeneration,
    Usage,
    canonical_json,
    request_fingerprint,
)

Responder = Callable[[str, GenerationRequest, Mapping[str, Any] | None], str]


def _digest(data: bytes, size: int = 32) -> bytes:
    return hashlib.blake2b(data, digest_size=size, person=b"sbr-mock-v1").digest()


class MockProvider(ModelProvider):
    kind = "mock"
    locality = Locality.LOCAL
    implemented = frozenset({Capability.GENERATE, Capability.STRUCTURED, Capability.EMBED, Capability.VISION})

    def __init__(
        self,
        name: str = "mock",
        capabilities: Sequence[str] | None = None,
        *,
        responder: Responder | None = None,
        failures: Sequence[ProviderError] = (),
        embedding_dim: int = 16,
    ) -> None:
        super().__init__(name, capabilities)
        self.responder = responder
        self._failures = list(failures)  # raised in order, one per call, before any normal answer
        self.embedding_dim = embedding_dim
        self.calls = 0

    def _maybe_fail(self) -> None:
        self.calls += 1
        if self._failures:
            raise self._failures.pop(0)

    def generate(
        self,
        model: str,
        request: GenerationRequest,
        *,
        timeout_s: float,
        json_schema: Mapping[str, Any] | None = None,
    ) -> ProviderGeneration:
        self._maybe_fail()
        if self.responder is not None:
            text = self.responder(model, request, json_schema)
        else:
            tag = _digest(canonical_json({"model": model, **request_fingerprint(request, json_schema)}), 8).hex()
            text = f'{{"mock": "{tag}"}}' if json_schema is not None else f"mock:{model}:{tag}"
        prompt_chars = sum(len(m.content) for m in request.messages)
        return ProviderGeneration(
            text=text,
            model_version=f"{model}@mock-v1",
            usage=Usage(prompt_tokens=math.ceil(prompt_chars / 4), completion_tokens=math.ceil(len(text) / 4)),
            finish_reason="stop",
        )

    def embed(self, model: str, texts: Sequence[str], *, timeout_s: float) -> ProviderEmbedding:
        self._maybe_fail()
        vectors = []
        for text in texts:
            raw = b""
            counter = 0
            while len(raw) < 4 * self.embedding_dim:
                raw += _digest(f"{model}\x00{counter}\x00{text}".encode("utf-8", "surrogatepass"))
                counter += 1
            ints = struct.unpack(f"<{self.embedding_dim}I", raw[: 4 * self.embedding_dim])
            vec = [(i / 0xFFFFFFFF) * 2.0 - 1.0 for i in ints]
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append(tuple(v / norm for v in vec))
        return ProviderEmbedding(vectors=tuple(vectors), model_version=f"{model}@mock-v1")

    def probe(self, *, timeout_s: float) -> ProbeResult:
        return ProbeResult(ok=True, detail="mock provider (in-process, deterministic)")
