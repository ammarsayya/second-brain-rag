"""Explicit model-gateway errors (T-P7-01).

Two families, handled differently by the gateway:

* :class:`PolicyError`: the call is not allowed (sensitivity, egress, missing configuration, unsupported capability).
  Never retried and never routed to a fallback: a policy refusal must not turn into "try somewhere else".
* :class:`ProviderError`: the call was allowed but the provider failed. ``retryable`` errors are retried a bounded
  number of times on the same provider; every provider error lets the gateway try the role's next *local* fallback.

Messages never contain prompt or response content (docs/22 §3).
"""

from __future__ import annotations


class ModelGatewayError(Exception):
    """Base class for every error raised by :mod:`sbr.models`."""


class PolicyError(ModelGatewayError):
    """The call is refused before any provider is contacted."""


class ModelNotConfiguredError(PolicyError):
    """The role has no primary model, or names a provider the gateway does not know."""


class SensitivityError(PolicyError):
    """The content's sensitivity class is not allowed for this role (``restricted`` is never allowed)."""


class EgressDeniedError(PolicyError):
    """The provider endpoint is not on this host, or a response tried to redirect elsewhere."""


class CapabilityError(PolicyError):
    """The routed provider does not implement what the role or request needs."""


class ProviderError(ModelGatewayError):
    """A permitted call failed at the provider."""

    retryable: bool = False

    def __init__(self, message: str, *, provider: str, retryable: bool | None = None) -> None:
        super().__init__(message)
        self.provider = provider
        if retryable is not None:
            self.retryable = retryable


class ProviderUnavailableError(ProviderError):
    """The local service is not reachable (not running, refused, overloaded)."""


class ProviderTimeoutError(ProviderError):
    """The call exceeded its deadline."""

    retryable = True


class ProviderResponseError(ProviderError):
    """The provider answered with an error status or a malformed or oversized body."""


class StructuredOutputError(ProviderError):
    """The model output does not parse as JSON or does not validate against the requested schema."""


class AllCandidatesFailedError(ModelGatewayError):
    """Every local candidate for a role failed. ``errors`` lists the per-candidate failures in order."""

    def __init__(self, role: str, errors: list[tuple[str, ProviderError]]) -> None:
        detail = "; ".join(f"{ref}: {type(e).__name__}: {e}" for ref, e in errors)
        super().__init__(f"role {role!r}: all {len(errors)} candidate(s) failed ({detail})")
        self.role = role
        self.errors = errors
