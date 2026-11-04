"""Provider adapter contract (T-P7-01, ADR-040).

An adapter turns gateway requests into calls on one backend. It does no policy work: sensitivity, egress, routing,
retries, fallbacks, caching and accounting all live in :class:`sbr.models.gateway.Gateway`, so a new adapter cannot
weaken them. Adapters declare their :class:`Locality` and the :class:`Capability` set they really implement.
"""

from __future__ import annotations

from abc import ABC
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sbr.models.errors import CapabilityError
from sbr.models.types import Capability, GenerationRequest, Locality, ProviderEmbedding, ProviderGeneration


@dataclass(frozen=True, slots=True)
class ProbeResult:
    ok: bool
    detail: str
    models: tuple[str, ...] = ()


class ModelProvider(ABC):  # noqa: B024 (no abstract methods by design: unimplemented capabilities raise)
    """Base adapter. Subclasses override the operations they support and list them in ``capabilities``."""

    kind: str = "abstract"
    locality: Locality = Locality.REMOTE  # fail closed: an adapter must declare itself local
    implemented: frozenset[Capability] = frozenset()

    def __init__(self, name: str, capabilities: Sequence[str] | None = None) -> None:
        self.name = name
        if capabilities is None:
            self.capabilities = self.implemented
        else:
            wanted = frozenset(Capability(c) for c in capabilities)
            extra = wanted - self.implemented
            if extra:
                raise CapabilityError(
                    f"provider {name!r} ({self.kind}) does not implement {sorted(c.value for c in extra)}; "
                    f"it implements {sorted(c.value for c in self.implemented)}"
                )
            self.capabilities = wanted

    def generate(
        self,
        model: str,
        request: GenerationRequest,
        *,
        timeout_s: float,
        json_schema: Mapping[str, Any] | None = None,
    ) -> ProviderGeneration:
        raise CapabilityError(f"provider {self.name!r} cannot generate")

    def embed(self, model: str, texts: Sequence[str], *, timeout_s: float) -> ProviderEmbedding:
        raise CapabilityError(f"provider {self.name!r} cannot embed")

    def probe(self, *, timeout_s: float) -> ProbeResult:
        return ProbeResult(ok=True, detail="no probe for this provider kind")
