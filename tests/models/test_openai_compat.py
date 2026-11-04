"""T-P7-01: the local OpenAI-compatible adapter against a real HTTP server on 127.0.0.1 (no external network)."""

from __future__ import annotations

import contextlib
import json
import socket
import threading
import time
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from sbr.config import ModelsConfig, ProviderConfig, RoleConfig, Sensitivity
from sbr.models import (
    AllCandidatesFailedError,
    EgressDeniedError,
    EmbeddingRequest,
    Gateway,
    GenerationRequest,
    Message,
    ModelNotConfiguredError,
    OpenAICompatibleProvider,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

Handler = Callable[[BaseHTTPRequestHandler, dict[str, Any] | None], tuple[int, dict[str, str], bytes]]


class FakeServer:
    def __init__(self, handler: Handler) -> None:
        self.requests: list[tuple[str, str, dict[str, Any] | None, dict[str, str]]] = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def _serve(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length)) if length else None
                outer.requests.append((self.command, self.path, body, dict(self.headers)))
                status, headers, payload = handler(self, body)
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                    self.wfile.write(payload)

            do_GET = do_POST = _serve  # noqa: N815

            def log_message(self, *args: Any) -> None:
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.httpd.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/v1"
        threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def serve() -> Iterator[Callable[[Handler], FakeServer]]:
    servers: list[FakeServer] = []

    def start(handler: Handler) -> FakeServer:
        servers.append(FakeServer(handler))
        return servers[-1]

    yield start
    for s in servers:
        s.close()


def ok_json(payload: dict[str, Any]) -> tuple[int, dict[str, str], bytes]:
    return 200, {"Content-Type": "application/json"}, json.dumps(payload).encode()


def chat_reply(text: str = "Eine Übertragungsfunktion ist G(s) = Y(s)/U(s).") -> Handler:
    def h(req: BaseHTTPRequestHandler, body: dict[str, Any] | None) -> tuple[int, dict[str, str], bytes]:
        if req.path.endswith("/models"):
            return ok_json({"data": [{"id": "qwen2.5:7b"}]})
        if req.path.endswith("/embeddings"):
            assert body is not None
            data = [{"index": i, "embedding": [float(i), 1.0]} for i, _ in enumerate(body["input"])]
            return ok_json({"model": body["model"], "data": list(reversed(data))})
        return ok_json(
            {
                "model": "qwen2.5:7b-instruct-q4_K_M",
                "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 9},
            }
        )

    return h


def req(**kw: Any) -> GenerationRequest:
    return GenerationRequest(messages=(Message("user", "Was ist G(s)?"),), sensitivity=Sensitivity.NORMAL, **kw)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_chat_embeddings_and_probe_against_local_server(serve: Callable[[Handler], FakeServer]) -> None:
    srv = serve(chat_reply())
    p = OpenAICompatibleProvider("ollama", srv.url)
    out = p.generate("qwen2.5:7b", req(temperature=0.0, max_tokens=64), timeout_s=5)
    assert out.text.startswith("Eine Übertragungsfunktion")
    assert out.model_version == "qwen2.5:7b-instruct-q4_K_M"
    assert (out.usage.prompt_tokens, out.usage.completion_tokens, out.finish_reason) == (12, 9, "stop")
    method, path, body, _ = srv.requests[-1]
    assert (method, path) == ("POST", "/v1/chat/completions")
    assert body == {
        "model": "qwen2.5:7b",
        "messages": [{"role": "user", "content": "Was ist G(s)?"}],
        "stream": False,
        "temperature": 0.0,
        "max_tokens": 64,
    }
    emb = p.embed("nomic", ["a", "b", "c"], timeout_s=5)
    assert emb.vectors == ((0.0, 1.0), (1.0, 1.0), (2.0, 1.0))  # reordered by index
    probe = p.probe(timeout_s=5)
    assert probe.ok and probe.models == ("qwen2.5:7b",)


def test_gateway_end_to_end_over_loopback(serve: Callable[[Handler], FakeServer]) -> None:
    srv = serve(chat_reply())
    cfg = ModelsConfig(
        providers={"local": ProviderConfig(kind="openai_compatible", base_url=srv.url)},
        roles={"reason": RoleConfig(primary="local/qwen2.5:7b"), "embed": RoleConfig(primary="local/nomic")},
    )
    g = Gateway(cfg)
    result = g.generate("reason", req())
    assert result.record.provider_kind == "openai_compatible" and result.record.prompt_tokens == 12
    e = g.embed("embed", EmbeddingRequest(texts=("x", "y"), sensitivity=Sensitivity.NORMAL))
    assert e.dim == 2


def test_missing_local_server_gives_a_clear_error_and_no_fallback() -> None:
    url = f"http://127.0.0.1:{free_port()}/v1"
    p = OpenAICompatibleProvider("ollama", url)
    with pytest.raises(ProviderUnavailableError, match="connection refused") as ei:
        p.generate("m", req(), timeout_s=2)
    assert "never falls back to a remote service" in str(ei.value)
    assert ei.value.retryable is False
    assert not p.probe(timeout_s=2).ok
    g = Gateway(
        ModelsConfig(
            providers={"local": ProviderConfig(kind="openai_compatible", base_url=url)},
            roles={"reason": RoleConfig(primary="local/m")},
        )
    )
    with pytest.raises(AllCandidatesFailedError, match="ProviderUnavailableError"):
        g.generate("reason", req())
    assert g.records[-1].attempts == 1  # refused connection is not retried


def test_timeout_is_enforced(serve: Callable[[Handler], FakeServer]) -> None:
    def slow(req_: BaseHTTPRequestHandler, body: Any) -> tuple[int, dict[str, str], bytes]:
        time.sleep(1.0)
        return ok_json({})

    srv = serve(slow)
    p = OpenAICompatibleProvider("slow", srv.url)
    t0 = time.monotonic()
    with pytest.raises(ProviderTimeoutError):
        p.generate("m", req(), timeout_s=0.2)
    assert time.monotonic() - t0 < 0.9


@pytest.mark.parametrize(
    ("status", "error", "retryable"),
    [(503, ProviderUnavailableError, True), (429, ProviderUnavailableError, True), (404, ProviderResponseError, False)],
)
def test_http_errors_are_classified(
    serve: Callable[[Handler], FakeServer], status: int, error: type[Exception], retryable: bool
) -> None:
    srv = serve(lambda r, b: (status, {}, b'{"error": "Pr\xc3\xbcfungsnote echoed back"}'))
    with pytest.raises(error) as ei:
        OpenAICompatibleProvider("x", srv.url).generate("m", req(), timeout_s=5)
    assert getattr(ei.value, "retryable") is retryable  # noqa: B009
    assert "Prüfungsnote" not in str(ei.value)  # server body (could echo content) is not surfaced


@pytest.mark.parametrize(
    "payload",
    [b"not json", b'{"choices": []}', b'{"choices": [{"message": {"content": 5}}]}', b"[]"],
)
def test_malformed_responses_are_rejected(serve: Callable[[Handler], FakeServer], payload: bytes) -> None:
    srv = serve(lambda r, b: (200, {}, payload))
    with pytest.raises(ProviderResponseError):
        OpenAICompatibleProvider("x", srv.url).generate("m", req(), timeout_s=5)


def test_oversized_response_is_rejected(serve: Callable[[Handler], FakeServer]) -> None:
    srv = serve(lambda r, b: (200, {}, b"x" * 200_000))
    with pytest.raises(ProviderResponseError, match="larger than"):
        OpenAICompatibleProvider("x", srv.url, max_response_bytes=100_000).generate("m", req(), timeout_s=5)


def test_redirects_are_never_followed(serve: Callable[[Handler], FakeServer]) -> None:
    target = serve(chat_reply())
    srv = serve(lambda r, b: (307, {"Location": target.url + "/chat/completions"}, b""))
    with pytest.raises(EgressDeniedError, match="redirect"):
        OpenAICompatibleProvider("x", srv.url).generate("m", req(), timeout_s=5)
    assert target.requests == []


def test_environment_proxies_are_ignored(
    serve: Callable[[Handler], FakeServer], monkeypatch: pytest.MonkeyPatch
) -> None:
    srv = serve(chat_reply())
    dead_proxy = f"http://127.0.0.1:{free_port()}"
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY"):
        monkeypatch.setenv(var, dead_proxy)
    for var in ("NO_PROXY", "no_proxy"):
        monkeypatch.delenv(var, raising=False)
    out = OpenAICompatibleProvider("x", srv.url).generate("m", req(), timeout_s=5)
    assert out.text  # reached the loopback server directly, not via the proxy
    assert srv.requests[-1][1] == "/v1/chat/completions"


def test_remote_base_url_refused_even_when_constructed_in_code() -> None:
    with pytest.raises(EgressDeniedError, match="not a loopback"):
        OpenAICompatibleProvider("cloud", "https://api.openai.com/v1")


def test_capabilities_cannot_be_extended_beyond_the_adapter() -> None:
    with pytest.raises(Exception, match="does not implement"):
        OpenAICompatibleProvider("x", "http://127.0.0.1:1/v1", capabilities=["generate", "vision"])


def test_structured_request_uses_json_schema_only_when_enabled(serve: Callable[[Handler], FakeServer]) -> None:
    srv = serve(chat_reply('{"a": 1}'))
    schema = {"type": "object", "properties": {"a": {"type": "integer"}}}
    OpenAICompatibleProvider("x", srv.url).generate("m", req(), timeout_s=5, json_schema=schema)
    assert "response_format" not in (srv.requests[-1][2] or {})
    OpenAICompatibleProvider("x", srv.url, capabilities=["generate", "structured"]).generate(
        "m", req(), timeout_s=5, json_schema=schema
    )
    assert (srv.requests[-1][2] or {})["response_format"]["json_schema"]["schema"] == schema


def test_token_comes_from_named_env_var(
    serve: Callable[[Handler], FakeServer], monkeypatch: pytest.MonkeyPatch
) -> None:
    srv = serve(chat_reply())
    p = OpenAICompatibleProvider("x", srv.url, api_key_env="SBR_TEST_LOCAL_TOKEN")
    monkeypatch.delenv("SBR_TEST_LOCAL_TOKEN", raising=False)
    with pytest.raises(ModelNotConfiguredError, match="SBR_TEST_LOCAL_TOKEN"):
        p.generate("m", req(), timeout_s=5)
    monkeypatch.setenv("SBR_TEST_LOCAL_TOKEN", "local-dev-token")
    p.generate("m", req(), timeout_s=5)
    assert srv.requests[-1][3].get("Authorization") == "Bearer local-dev-token"
