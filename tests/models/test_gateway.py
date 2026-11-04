"""T-P7-01: gateway routing, policy enforcement, reliability and accounting, using deterministic mock providers."""

from __future__ import annotations

import json
import logging
import socket
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

import pytest
from pydantic import BaseModel

from sbr.config import ModelsConfig, ProviderConfig, RoleConfig, Sensitivity
from sbr.models import (
    AllCandidatesFailedError,
    CapabilityError,
    EgressDeniedError,
    EmbeddingRequest,
    Gateway,
    GenerationRequest,
    Locality,
    Message,
    MockProvider,
    ModelNotConfiguredError,
    ModelProvider,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    SensitivityError,
    StructuredOutputError,
)
from sbr.models.types import ProviderGeneration

PRIVATE_TEXT = "Prüfungsnote von Max Mustermann: 1,3"  # stands in for corpus content that must never be logged


def req(text: str = "Was ist eine Übertragungsfunktion?", **kw: Any) -> GenerationRequest:
    kw.setdefault("sensitivity", Sensitivity.NORMAL)
    return GenerationRequest(messages=(Message("user", text),), **kw)


def models_config(roles: Mapping[str, RoleConfig], providers: Sequence[str] = ("a", "b")) -> ModelsConfig:
    return ModelsConfig(providers={p: ProviderConfig(kind="mock", max_retries=2) for p in providers}, roles=dict(roles))


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[Any]]:
    """Fail the test if anything opens a socket connection."""
    attempts: list[Any] = []

    def refuse(self: socket.socket, address: Any) -> None:
        attempts.append(address)
        raise AssertionError(f"network connection attempted to {address!r}")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    yield attempts


def gw(roles: Mapping[str, RoleConfig], **providers: ModelProvider) -> Gateway:
    names = tuple(providers) or ("a", "b")
    built = providers or {n: MockProvider(n) for n in names}
    return Gateway(models_config(roles, names), built, sleep=lambda _s: None)


# -- local-only default ---------------------------------------------------------------------------------------------


def test_default_gateway_has_no_models_and_refuses_every_role(no_network: list[Any]) -> None:
    g = Gateway(ModelsConfig())
    status = g.role_status()
    assert set(status) >= {"embed", "reason", "extract", "math_ocr", "vision"}
    assert not any(s["configured"] for s in status.values())
    with pytest.raises(ModelNotConfiguredError, match="has no model"):
        g.generate("reason", req())
    assert g.records[-1].outcome == "refused"
    assert no_network == []


def test_remote_provider_object_is_refused_at_construction() -> None:
    class Remote(MockProvider):
        locality = Locality.REMOTE

    with pytest.raises(EgressDeniedError, match="only local providers"):
        Gateway(models_config({"reason": RoleConfig(primary="a/x")}, ("a",)), {"a": Remote("a")})


def test_adapter_base_class_fails_closed_as_remote() -> None:
    class Undeclared(ModelProvider):
        kind = "custom"

    with pytest.raises(EgressDeniedError):
        Gateway(models_config({}, ("a",)), {"a": Undeclared("a")})


def test_unknown_role_rejected() -> None:
    with pytest.raises(ModelNotConfiguredError, match="unknown role"):
        gw({}).generate("chat", req())


# -- routing and determinism ----------------------------------------------------------------------------------------


def test_role_routes_to_primary_and_is_deterministic(no_network: list[Any]) -> None:
    roles = {"reason": RoleConfig(primary="a/m1"), "extract": RoleConfig(primary="b/m2")}
    one, two = gw(roles), gw(roles)
    r1 = one.generate("reason", req())
    assert r1.record.provider == "a" and r1.record.model == "m1"
    assert r1.text == two.generate("reason", req()).text  # same input -> same output across instances
    assert r1.text.startswith("mock:m1:")
    assert one.generate("extract", req()).record.provider == "b"
    assert one.generate("reason", req("other")).text != r1.text
    assert no_network == []


def test_embeddings_are_deterministic_unit_vectors() -> None:
    g = gw({"embed": RoleConfig(primary="a/e")})
    out = g.embed("embed", EmbeddingRequest(texts=("Regelkreis", "Laplace"), sensitivity=Sensitivity.NORMAL))
    again = gw({"embed": RoleConfig(primary="a/e")}).embed(
        "embed", EmbeddingRequest(texts=("Regelkreis", "Laplace"), sensitivity=Sensitivity.NORMAL)
    )
    assert out.vectors == again.vectors and out.dim == 16
    assert all(abs(sum(v * v for v in vec) - 1.0) < 1e-9 for vec in out.vectors)
    assert out.vectors[0] != out.vectors[1]


# -- sensitivity gate -----------------------------------------------------------------------------------------------


def test_restricted_content_is_refused_before_any_provider_call() -> None:
    a = MockProvider("a")
    g = gw({"reason": RoleConfig(primary="a/m")}, a=a)
    with pytest.raises(SensitivityError, match="never sent"):
        g.generate("reason", req(sensitivity=Sensitivity.RESTRICTED))
    with pytest.raises(SensitivityError):
        g.embed("reason", EmbeddingRequest(texts=("x",), sensitivity=Sensitivity.RESTRICTED))
    assert a.calls == 0
    assert g.records[-1].outcome == "refused" and g.records[-1].error_type == "SensitivityError"


def test_sensitivity_must_be_allowed_by_the_role() -> None:
    a = MockProvider("a")
    g = gw({"reason": RoleConfig(primary="a/m")}, a=a)  # default allowed_sensitivity = [normal]
    for s in (Sensitivity.PERSONAL, Sensitivity.THIRD_PARTY_PERSONAL):
        with pytest.raises(SensitivityError, match="not allowed"):
            g.generate("reason", req(sensitivity=s))
    assert a.calls == 0
    g2 = gw({"reason": RoleConfig(primary="a/m", allowed_sensitivity=[Sensitivity.NORMAL, Sensitivity.PERSONAL])})
    assert g2.generate("reason", req(sensitivity=Sensitivity.PERSONAL)).record.outcome == "ok"


# -- capability checks ----------------------------------------------------------------------------------------------


def test_role_needing_unimplemented_capability_fails_at_construction() -> None:
    with pytest.raises(ModelNotConfiguredError, match="does not implement 'rerank'"):
        gw({"rerank": RoleConfig(primary="a/r")})
    limited = MockProvider("a", capabilities=["generate"])
    with pytest.raises(ModelNotConfiguredError, match="does not implement 'embed'"):
        gw({"embed": RoleConfig(primary="a/e")}, a=limited)


def test_images_only_for_vision_roles() -> None:
    g = gw({"reason": RoleConfig(primary="a/m"), "math_ocr": RoleConfig(primary="b/v")})
    with pytest.raises(CapabilityError, match="does not take images"):
        g.generate("reason", req(images=(b"\x89PNG",)))
    assert g.generate("math_ocr", req("Transkribiere die Formel", images=(b"\x89PNG",))).record.outcome == "ok"


# -- reliability: retries, fallbacks, timeouts ----------------------------------------------------------------------


def test_timeouts_are_retried_with_bounded_backoff_then_fall_back() -> None:
    sleeps: list[float] = []
    a = MockProvider("a", failures=[ProviderTimeoutError("t", provider="a")] * 3)
    b = MockProvider("b")
    g = Gateway(
        models_config({"reason": RoleConfig(primary="a/m", fallbacks=["b/m"])}), {"a": a, "b": b}, sleep=sleeps.append
    )
    result = g.generate("reason", req())
    assert a.calls == 3  # 1 + max_retries(2)
    assert sleeps == [0.5, 1.0]
    assert result.record.provider == "b" and result.record.attempts == 4
    assert result.record.candidates_tried == ["a/m", "b/m"]


def test_non_retryable_failure_moves_straight_to_fallback() -> None:
    a = MockProvider("a", failures=[ProviderUnavailableError("down", provider="a")])
    g = gw({"reason": RoleConfig(primary="a/m", fallbacks=["b/m"])}, a=a, b=MockProvider("b"))
    assert g.generate("reason", req()).record.provider == "b"
    assert a.calls == 1


def test_all_candidates_failing_raises_with_every_cause() -> None:
    a = MockProvider("a", failures=[ProviderResponseError("bad", provider="a")])
    b = MockProvider("b", failures=[ProviderUnavailableError("down", provider="b")])
    g = gw({"reason": RoleConfig(primary="a/m", fallbacks=["b/m"])}, a=a, b=b)
    with pytest.raises(AllCandidatesFailedError) as ei:
        g.generate("reason", req())
    assert [ref for ref, _ in ei.value.errors] == ["a/m", "b/m"]
    assert g.records[-1].outcome == "failed"


def test_policy_errors_never_fall_back() -> None:
    a, b = MockProvider("a", capabilities=["generate"]), MockProvider("b")
    g = gw({"vision": RoleConfig(primary="b/v", fallbacks=["b/w"])}, a=a, b=b)
    b._failures = [EgressDeniedError("redirect refused")]  # type: ignore[list-item]  # a policy error mid-call
    with pytest.raises(EgressDeniedError):
        g.generate("vision", req())
    assert b.calls == 1  # the fallback b/w was not tried


# -- structured output ----------------------------------------------------------------------------------------------


class Symbol(BaseModel):
    symbol: str
    meaning: str


def test_structured_output_is_validated() -> None:
    def respond(model: str, request: GenerationRequest, schema: Mapping[str, Any] | None) -> str:
        assert schema is not None and "symbol" in schema["properties"]
        return '```json\n{"symbol": "K_p", "meaning": "Proportionalbeiwert"}\n```'

    g = gw({"extract": RoleConfig(primary="a/m")}, a=MockProvider("a", responder=respond))
    out = g.generate_structured("extract", req(), Symbol)
    assert out.parsed == Symbol(symbol="K_p", meaning="Proportionalbeiwert")
    assert out.record.operation == "generate_structured"


def test_invalid_structured_output_raises() -> None:
    bad = MockProvider("a", responder=lambda *_: json.dumps({"symbol": "K_p"}))
    g = gw({"extract": RoleConfig(primary="a/m")}, a=bad)
    with pytest.raises(AllCandidatesFailedError) as ei:
        g.generate_structured("extract", req(), Symbol)
    assert isinstance(ei.value.errors[0][1], StructuredOutputError)


# -- cache and accounting -------------------------------------------------------------------------------------------


def test_cache_serves_repeat_calls_without_the_provider() -> None:
    a = MockProvider("a")
    g = gw({"reason": RoleConfig(primary="a/m")}, a=a)
    first, second = g.generate("reason", req()), g.generate("reason", req())
    assert a.calls == 1 and second.text == first.text and second.record.cache_hit
    g_nocache = gw({"reason": RoleConfig(primary="a/m", cache=False)}, a=(a2 := MockProvider("a")))
    g_nocache.generate("reason", req())
    g_nocache.generate("reason", req())
    assert a2.calls == 2


def test_call_records_carry_provenance_but_no_content(caplog: pytest.LogCaptureFixture) -> None:
    g = gw({"reason": RoleConfig(primary="a/m", allowed_sensitivity=[Sensitivity.NORMAL, Sensitivity.PERSONAL])})
    with caplog.at_level(logging.INFO, logger="sbr.models"):
        out = g.generate(
            "reason", req(PRIVATE_TEXT, sensitivity=Sensitivity.PERSONAL, subject_id="ku_1", prompt_version="1.0")
        )
        with pytest.raises(SensitivityError):
            g.generate("reason", req(PRIVATE_TEXT, sensitivity=Sensitivity.RESTRICTED))
    rec = out.record
    assert rec.input_sha256.startswith("sha256:") and rec.output_sha256 and rec.output_chars == len(out.text)
    assert (rec.subject_id, rec.prompt_version, rec.model_version) == ("ku_1", "1.0", "m@mock-v1")
    assert rec.cost_usd == 0.0 and rec.locality is Locality.LOCAL and rec.provenance_class == "AI_GENERATED"
    assert rec.prompt_tokens and rec.completion_tokens
    dumped = json.dumps([r.model_dump(mode="json") for r in g.records], ensure_ascii=False)
    logged = " ".join(r.getMessage() + json.dumps(getattr(r, "sbr", {}), ensure_ascii=False) for r in caplog.records)
    for blob in (dumped, logged):
        assert "Mustermann" not in blob and out.text not in blob
    assert len(caplog.records) == 2


def test_provider_generation_type_is_what_cache_stores() -> None:
    g = gw({"reason": RoleConfig(primary="a/m")})
    g.generate("reason", req())
    assert len(g.cache) == 1
    assert all(isinstance(v, ProviderGeneration) for v in g.cache._data.values())
