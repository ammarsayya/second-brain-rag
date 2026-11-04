"""Model gateway (T-P7-01, ADR-025, ADR-040): role routing, local-only providers, sensitivity gate, accounting.

Remote providers are not authorized (owner decisions Q-B03/Q-B04, 2026-11-04). See docs/17 §6.
"""

from sbr.models.errors import (
    AllCandidatesFailedError,
    CapabilityError,
    EgressDeniedError,
    ModelGatewayError,
    ModelNotConfiguredError,
    PolicyError,
    ProviderError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    SensitivityError,
    StructuredOutputError,
)
from sbr.models.gateway import Gateway, ResponseCache, build_provider
from sbr.models.mock import MockProvider
from sbr.models.openai_compat import OpenAICompatibleProvider
from sbr.models.provider import ModelProvider, ProbeResult
from sbr.models.types import (
    ROLE_CAPABILITY,
    CallRecord,
    Capability,
    EmbeddingRequest,
    EmbeddingResult,
    GenerationRequest,
    GenerationResult,
    Locality,
    Message,
)

__all__ = [
    "ROLE_CAPABILITY",
    "AllCandidatesFailedError",
    "CallRecord",
    "Capability",
    "CapabilityError",
    "EgressDeniedError",
    "EmbeddingRequest",
    "EmbeddingResult",
    "Gateway",
    "GenerationRequest",
    "GenerationResult",
    "Locality",
    "Message",
    "MockProvider",
    "ModelGatewayError",
    "ModelNotConfiguredError",
    "ModelProvider",
    "OpenAICompatibleProvider",
    "PolicyError",
    "ProbeResult",
    "ProviderError",
    "ProviderResponseError",
    "ProviderTimeoutError",
    "ProviderUnavailableError",
    "ResponseCache",
    "SensitivityError",
    "StructuredOutputError",
    "build_provider",
]
