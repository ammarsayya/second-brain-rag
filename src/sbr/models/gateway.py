"""The model gateway: the only path from sbr code to any model (T-P7-01, ADR-025, ADR-040, HC-20).

Order of checks for every call (each one fails closed, before any provider is contacted):

1. the role exists and has a primary model (:class:`ModelNotConfiguredError`);
2. the request's sensitivity is allowed: ``restricted`` never, otherwise only the role's ``allowed_sensitivity``
   (:class:`SensitivityError`);
3. the request fits the role's capability (images only for vision-type roles) (:class:`CapabilityError`);
4. per candidate: the provider is LOCAL (:class:`EgressDeniedError`), then its capability.

Then candidates are tried in order (primary, then fallbacks). A :class:`ProviderError` with ``retryable`` is retried
up to the provider's ``max_retries`` with bounded exponential backoff; any provider error moves on to the next
candidate. Policy errors stop the call immediately. There is no remote fallback: remote providers cannot be
configured (:mod:`sbr.config`) and a remote provider object passed in by code is refused at construction.

Every call yields a :class:`CallRecord` (hashes, sizes, tokens, latency, cost, outcome; no content), logged on the
``sbr.models`` logger and kept in :attr:`Gateway.records`.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from sbr.config import ModelsConfig, ProviderConfig, ProviderKind, RoleConfig, Sensitivity
from sbr.models.errors import (
    AllCandidatesFailedError,
    CapabilityError,
    EgressDeniedError,
    ModelNotConfiguredError,
    PolicyError,
    ProviderError,
    SensitivityError,
    StructuredOutputError,
)
from sbr.models.mock import MockProvider
from sbr.models.openai_compat import OpenAICompatibleProvider
from sbr.models.provider import ModelProvider
from sbr.models.types import (
    ROLE_CAPABILITY,
    CallRecord,
    Capability,
    EmbeddingRequest,
    EmbeddingResult,
    GenerationRequest,
    GenerationResult,
    Locality,
    ProviderEmbedding,
    ProviderGeneration,
    canonical_json,
    request_fingerprint,
    sha256_hex,
)

LOGGER = logging.getLogger("sbr.models")
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*\n(.*?)\n\s*```\s*$", re.S)
MAX_BACKOFF_S = 4.0


class ResponseCache:
    """In-memory, content-addressed response cache (docs/17 §5). Keys include role, provider, model and prompt."""

    def __init__(self, max_entries: int = 10_000) -> None:
        self.max_entries = max_entries
        self._data: dict[str, ProviderGeneration | ProviderEmbedding] = {}

    def get(self, key: str) -> ProviderGeneration | ProviderEmbedding | None:
        return self._data.get(key)

    def put(self, key: str, value: ProviderGeneration | ProviderEmbedding) -> None:
        if len(self._data) >= self.max_entries:
            self._data.pop(next(iter(self._data)))
        self._data[key] = value

    def __len__(self) -> int:
        return len(self._data)


@dataclass(frozen=True, slots=True)
class _Candidate:
    ref: str
    provider: ModelProvider
    model: str
    timeout_s: float
    max_retries: int


def build_provider(name: str, cfg: ProviderConfig) -> ModelProvider:
    """Instantiate the adapter for one ``[models.providers.<name>]`` entry."""
    if cfg.kind is ProviderKind.MOCK:
        return MockProvider(name, cfg.capabilities)
    if cfg.kind is ProviderKind.OPENAI_COMPATIBLE:
        assert cfg.base_url is not None  # noqa: S101 (guaranteed by ProviderConfig validation)
        return OpenAICompatibleProvider(name, cfg.base_url, cfg.capabilities, api_key_env=cfg.api_key_env)
    raise ModelNotConfiguredError(f"provider {name!r}: unsupported kind {cfg.kind!r}")


class Gateway:
    """Role-routed, policy-enforcing access to local models."""

    def __init__(
        self,
        config: ModelsConfig,
        providers: Mapping[str, ModelProvider] | None = None,
        *,
        cache: ResponseCache | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        if config.allow_remote:  # unreachable through validated config; guards hand-built objects
            raise EgressDeniedError("remote model providers are not authorized (ADR-039/ADR-040)")
        built = (
            dict(providers) if providers is not None else {n: build_provider(n, c) for n, c in config.providers.items()}
        )
        for name, provider in built.items():
            if provider.locality is not Locality.LOCAL:
                raise EgressDeniedError(
                    f"provider {name!r} is {provider.locality.value}; only local providers are authorized "
                    "(owner decisions Q-B03/Q-B04, ADR-039/ADR-040)"
                )
        self.providers = built
        self.cache = cache if cache is not None else ResponseCache()
        self._sleep = sleep
        self._clock = clock
        self.records: list[CallRecord] = []
        problems = self.validate_roles()
        if problems:
            raise ModelNotConfiguredError("model configuration problems: " + "; ".join(problems))

    # -- configuration ------------------------------------------------------------------------------------------

    def validate_roles(self) -> list[str]:
        """Problems that make a configured role unusable (unknown provider, missing capability)."""
        problems = []
        for role, rc in self.config.roles.items():
            need = ROLE_CAPABILITY[role]
            for ref in ([rc.primary] if rc.primary else []) + rc.fallbacks:
                pname, _, _ = ref.partition("/")
                provider = self.providers.get(pname)
                if provider is None:
                    problems.append(f"role {role!r}: provider {pname!r} unknown")
                elif need not in provider.capabilities:
                    problems.append(
                        f"role {role!r}: provider {pname!r} ({provider.kind}) does not implement {need.value!r}"
                    )
        return problems

    def role_status(self) -> dict[str, dict[str, Any]]:
        """Configured roles, the capability each needs and its candidates (no network access)."""
        out: dict[str, dict[str, Any]] = {}
        for role in sorted(ROLE_CAPABILITY):
            rc = self.config.roles.get(role)
            out[role] = {
                "requires": ROLE_CAPABILITY[role].value,
                "configured": bool(rc and rc.primary),
                "candidates": ([rc.primary] if rc and rc.primary else []) + (rc.fallbacks if rc else []),
                "allowed_sensitivity": [s.value for s in rc.allowed_sensitivity] if rc else [],
            }
        return out

    def _role(self, role: str) -> RoleConfig:
        if role not in ROLE_CAPABILITY:
            raise ModelNotConfiguredError(f"unknown role {role!r}")
        rc = self.config.roles.get(role)
        if rc is None or not rc.primary:
            raise ModelNotConfiguredError(
                f"role {role!r} has no model: set [models.roles.{role}].primary = '<provider>/<model>' "
                "with a local provider"
            )
        return rc

    def _candidates(self, role: str, rc: RoleConfig, need: Capability) -> list[_Candidate]:
        out = []
        for ref in [rc.primary or "", *rc.fallbacks]:
            pname, _, model = ref.partition("/")
            provider = self.providers.get(pname)
            if provider is None:
                raise ModelNotConfiguredError(f"role {role!r}: provider {pname!r} unknown")
            if provider.locality is not Locality.LOCAL:  # defence in depth; also checked in __init__
                raise EgressDeniedError(f"role {role!r}: provider {pname!r} is not local")
            if need not in provider.capabilities:
                raise CapabilityError(f"role {role!r}: provider {pname!r} does not implement {need.value!r}")
            pc = self.config.providers.get(pname)
            out.append(
                _Candidate(
                    ref=ref,
                    provider=provider,
                    model=model,
                    timeout_s=pc.timeout_s if pc else 120.0,
                    max_retries=pc.max_retries if pc else 0,
                )
            )
        return out

    @staticmethod
    def _check_sensitivity(role: str, rc: RoleConfig, sensitivity: Sensitivity) -> None:
        if sensitivity is Sensitivity.RESTRICTED:
            raise SensitivityError(f"role {role!r}: 'restricted' content is never sent to any model (docs/22 §3)")
        if sensitivity not in rc.allowed_sensitivity:
            allowed = ", ".join(s.value for s in rc.allowed_sensitivity)
            raise SensitivityError(f"role {role!r}: {sensitivity.value!r} content not allowed (allowed: {allowed})")

    # -- operations ---------------------------------------------------------------------------------------------

    def generate(self, role: str, request: GenerationRequest) -> GenerationResult:
        return self._generate(role, request, None, "generate")

    def generate_structured(self, role: str, request: GenerationRequest, schema: type[BaseModel]) -> GenerationResult:
        """Generate JSON that validates against ``schema``; ``result.parsed`` is the validated instance."""
        return self._generate(role, request, schema, "generate_structured")

    def embed(self, role: str, request: EmbeddingRequest) -> EmbeddingResult:
        fingerprint = {"texts": list(request.texts)}
        input_bytes = canonical_json(fingerprint)
        record_base = self._record_base(role, "embed", request.sensitivity, request.subject_id, None, input_bytes)
        record_base["input_chars"] = sum(len(t) for t in request.texts)

        def call(c: _Candidate) -> ProviderEmbedding:
            out = c.provider.embed(c.model, request.texts, timeout_s=c.timeout_s)
            if len(out.vectors) != len(request.texts) or len({len(v) for v in out.vectors}) > 1:
                raise StructuredOutputError(
                    f"provider {c.provider.name!r}: {len(out.vectors)} vectors for {len(request.texts)} texts "
                    "or inconsistent dimensions",
                    provider=c.provider.name,
                )
            return out

        result, record = self._run(role, Capability.EMBED, request.sensitivity, record_base, input_bytes, call)
        assert isinstance(result, ProviderEmbedding)  # noqa: S101
        return EmbeddingResult(vectors=result.vectors, record=record)

    def _generate(
        self,
        role: str,
        request: GenerationRequest,
        schema: type[BaseModel] | None,
        operation: Literal["generate", "generate_structured"],
    ) -> GenerationResult:
        json_schema = schema.model_json_schema() if schema is not None else None
        input_bytes = canonical_json(request_fingerprint(request, json_schema))
        record_base = self._record_base(
            role, operation, request.sensitivity, request.subject_id, request.prompt_version, input_bytes
        )
        record_base["input_chars"] = sum(len(m.content) for m in request.messages)
        parsed: list[Any] = []

        def call(c: _Candidate) -> ProviderGeneration:
            if request.images and Capability.VISION not in c.provider.capabilities:
                raise CapabilityError(f"provider {c.provider.name!r} does not accept images")
            out = c.provider.generate(c.model, request, timeout_s=c.timeout_s, json_schema=json_schema)
            if schema is not None:
                parsed[:] = [_parse_structured(out.text, schema, c.provider.name)]
            return out

        need = ROLE_CAPABILITY.get(role, Capability.GENERATE)
        if request.images and need is not Capability.VISION:
            raise CapabilityError(f"role {role!r} does not take images")
        result, record = self._run(role, need, request.sensitivity, record_base, input_bytes, call)
        assert isinstance(result, ProviderGeneration)  # noqa: S101
        if schema is not None and not parsed:  # cache hit: re-validate the cached text
            parsed = [_parse_structured(result.text, schema, record.provider or "?")]
        return GenerationResult(text=result.text, record=record, parsed=parsed[0] if parsed else None)

    # -- shared execution ---------------------------------------------------------------------------------------

    def _record_base(
        self,
        role: str,
        operation: str,
        sensitivity: Sensitivity,
        subject_id: str | None,
        prompt_version: str | None,
        input_bytes: bytes,
    ) -> dict[str, Any]:
        return {
            "call_id": uuid.uuid4().hex,
            "started_at": datetime.now(UTC),
            "role": role,
            "operation": operation,
            "sensitivity": sensitivity,
            "subject_id": subject_id,
            "prompt_version": prompt_version,
            "input_sha256": sha256_hex(input_bytes),
        }

    def _run(
        self,
        role: str,
        need: Capability,
        sensitivity: Sensitivity,
        base: dict[str, Any],
        input_bytes: bytes,
        call: Callable[[_Candidate], ProviderGeneration | ProviderEmbedding],
    ) -> tuple[ProviderGeneration | ProviderEmbedding, CallRecord]:
        t0 = self._clock()
        tried: list[str] = []
        attempts = 0
        try:
            rc = self._role(role)
            self._check_sensitivity(role, rc, sensitivity)
            candidates = self._candidates(role, rc, need)
        except PolicyError as exc:
            self._emit(base, None, None, t0, attempts, tried, False, "refused", exc)
            raise
        failures: list[tuple[str, ProviderError]] = []
        for c in candidates:
            tried.append(c.ref)
            key = sha256_hex(canonical_json([role, base["operation"], c.ref]) + b"\x00" + input_bytes)
            cached = self.cache.get(key) if rc.cache else None
            if cached is not None:
                return cached, self._emit(base, c, cached, t0, attempts, tried, True, "ok", None)
            for attempt in range(c.max_retries + 1):
                attempts += 1
                try:
                    out = call(c)
                except PolicyError as exc:
                    self._emit(base, c, None, t0, attempts, tried, False, "refused", exc)
                    raise
                except ProviderError as exc:
                    if exc.retryable and attempt < c.max_retries:
                        self._sleep(min(MAX_BACKOFF_S, 0.5 * 2**attempt))
                        continue
                    failures.append((c.ref, exc))
                    break
                if rc.cache:
                    self.cache.put(key, out)
                return out, self._emit(base, c, out, t0, attempts, tried, False, "ok", None)
        error = AllCandidatesFailedError(role, failures)
        self._emit(base, candidates[-1] if candidates else None, None, t0, attempts, tried, False, "failed", error)
        raise error

    def _emit(
        self,
        base: dict[str, Any],
        cand: _Candidate | None,
        out: ProviderGeneration | ProviderEmbedding | None,
        t0: float,
        attempts: int,
        tried: list[str],
        cache_hit: bool,
        outcome: Literal["ok", "refused", "failed"],
        error: Exception | None,
    ) -> CallRecord:
        text = out.text if isinstance(out, ProviderGeneration) else None
        if isinstance(out, ProviderEmbedding):
            out_bytes: bytes | None = canonical_json([list(v) for v in out.vectors])
        else:
            out_bytes = text.encode("utf-8", "surrogatepass") if text is not None else None
        usage = out.usage if out is not None else None
        record = CallRecord(
            **base,
            provider=cand.provider.name if cand else None,
            provider_kind=cand.provider.kind if cand else None,
            model=cand.model if cand else None,
            model_version=out.model_version if out is not None else None,
            locality=cand.provider.locality if cand else None,
            output_sha256=sha256_hex(out_bytes) if out_bytes is not None else None,
            output_chars=len(text) if text is not None else None,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            cost_usd=0.0,  # local execution only (ADR-039); remote pricing arrives with remote adapters
            latency_ms=max(0.0, (self._clock() - t0) * 1000.0),
            attempts=attempts,
            cache_hit=cache_hit,
            candidates_tried=list(tried),
            outcome=outcome,
            error_type=type(error).__name__ if error is not None else None,
        )
        self.records.append(record)
        level = logging.INFO if outcome == "ok" else logging.WARNING
        LOGGER.log(level, "model call %s", outcome, extra={"sbr": {"model_call": record.model_dump(mode="json")}})
        return record


def _parse_structured[M: BaseModel](text: str, schema: type[M], provider: str) -> M:
    match = _FENCE_RE.match(text)
    raw = match.group(1) if match else text
    try:
        return schema.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise StructuredOutputError(
            f"provider {provider!r}: output does not validate against {schema.__name__} ({type(exc).__name__})",
            provider=provider,
        ) from None
