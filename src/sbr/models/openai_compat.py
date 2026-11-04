"""Adapter for a *local* OpenAI-compatible server (T-P7-01, ADR-040, docs/17 §2 "Local").

Ollama, llama.cpp ``llama-server``, LM Studio and vLLM all expose ``/v1/chat/completions``, ``/v1/embeddings`` and
``/v1/models``. This adapter speaks that subset with the standard library only (no new dependency).

Egress hardening enforced in code:

* the base URL must be loopback (checked at configuration time and again here);
* at every call the host must resolve to loopback addresses only;
* environment proxies (``HTTP(S)_PROXY``) are ignored, so a loopback call cannot be routed through a remote proxy;
* HTTP redirects are refused, never followed;
* a total deadline (not only the per-socket timeout) and a response-size cap bound every call.

No inference server is assumed to exist: a refused connection becomes a clear :class:`ProviderUnavailableError`, and
the gateway never falls back to anything remote. Vision input is **not** implemented here yet (untested against a
real server); configure ``vision``-type roles only with a provider that implements :attr:`Capability.VISION`.
"""

from __future__ import annotations

import http.client
import json
import os
import socket
import time
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn
from urllib.parse import urlsplit

from sbr.egress import local_url_problem, resolves_only_to_loopback
from sbr.models.errors import (
    EgressDeniedError,
    ModelNotConfiguredError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from sbr.models.provider import ModelProvider, ProbeResult
from sbr.models.types import (
    Capability,
    GenerationRequest,
    Locality,
    ProviderEmbedding,
    ProviderGeneration,
    Usage,
)

MAX_RESPONSE_BYTES = 32 * 1024 * 1024
_CHUNK = 64 * 1024


class _RefuseRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        raise EgressDeniedError(f"local model server answered HTTP {code} redirect; redirects are never followed")


class OpenAICompatibleProvider(ModelProvider):
    kind = "openai_compatible"
    locality = Locality.LOCAL
    implemented = frozenset({Capability.GENERATE, Capability.STRUCTURED, Capability.EMBED})

    def __init__(
        self,
        name: str,
        base_url: str,
        capabilities: Sequence[str] | None = None,
        *,
        api_key_env: str | None = None,
        max_response_bytes: int = MAX_RESPONSE_BYTES,
    ) -> None:
        default = [Capability.GENERATE.value, Capability.EMBED.value]
        super().__init__(name, capabilities if capabilities is not None else default)
        problem = local_url_problem(base_url)
        if problem:
            raise EgressDeniedError(f"provider {name!r}: {problem}")
        self.base_url = base_url.rstrip("/")
        parts = urlsplit(self.base_url)
        self._host = parts.hostname or ""
        self._port = parts.port or (443 if parts.scheme == "https" else 80)
        self._api_key_env = api_key_env
        self.max_response_bytes = max_response_bytes
        # ProxyHandler({}) disables environment proxies; _RefuseRedirects replaces the default redirect handler.
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _RefuseRedirects())

    # -- transport ------------------------------------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_key_env:
            token = os.environ.get(self._api_key_env)
            if not token:
                raise ModelNotConfiguredError(
                    f"provider {self.name!r}: environment variable {self._api_key_env} is not set"
                )
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _fail_unavailable(self, why: str, *, retryable: bool) -> NoReturn:
        raise ProviderUnavailableError(
            f"local model server {self.name!r} at {self.base_url} is not available ({why}). Start it or fix "
            f"[models.providers.{self.name}].base_url; sbr never falls back to a remote service.",
            provider=self.name,
            retryable=retryable,
        )

    def _request(self, method: str, path: str, payload: Mapping[str, Any] | None, timeout_s: float) -> Any:
        if not resolves_only_to_loopback(self._host, self._port):
            raise EgressDeniedError(f"provider {self.name!r}: host {self._host!r} does not resolve to loopback only")
        deadline = time.monotonic() + timeout_s
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(  # noqa: S310 (scheme and host validated above: http(s) on loopback only)
            self.base_url + path, data=data, method=method, headers=self._headers()
        )
        try:
            with self._opener.open(req, timeout=timeout_s) as resp:
                body = self._read_bounded(resp, deadline)
        except EgressDeniedError:
            raise
        except urllib.error.HTTPError as exc:
            exc.close()
            if exc.code == 429 or exc.code >= 500:
                self._fail_unavailable(f"HTTP {exc.code}", retryable=True)
            hint = " (unknown model or endpoint?)" if exc.code == 404 else ""
            raise ProviderResponseError(
                f"provider {self.name!r}: HTTP {exc.code}{hint} on {path}", provider=self.name
            ) from None
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, TimeoutError | socket.timeout):
                raise ProviderTimeoutError(
                    f"provider {self.name!r}: timed out after {timeout_s:g}s on {path}", provider=self.name
                ) from None
            if isinstance(reason, ConnectionRefusedError):
                self._fail_unavailable("connection refused: is the server running?", retryable=False)
            self._fail_unavailable(f"{type(reason).__name__}", retryable=False)
        except TimeoutError:
            raise ProviderTimeoutError(
                f"provider {self.name!r}: timed out after {timeout_s:g}s on {path}", provider=self.name
            ) from None
        except (ConnectionError, http.client.HTTPException) as exc:
            self._fail_unavailable(type(exc).__name__, retryable=True)
        try:
            return json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ProviderResponseError(f"provider {self.name!r}: response is not JSON", provider=self.name) from None

    def _read_bounded(self, resp: Any, deadline: float) -> bytes:
        chunks: list[bytes] = []
        total = 0
        while True:
            if time.monotonic() > deadline:
                raise ProviderTimeoutError(
                    f"provider {self.name!r}: response exceeded its deadline", provider=self.name
                )
            chunk = resp.read(_CHUNK)
            if not chunk:
                return b"".join(chunks)
            total += len(chunk)
            if total > self.max_response_bytes:
                raise ProviderResponseError(
                    f"provider {self.name!r}: response larger than {self.max_response_bytes} bytes", provider=self.name
                )
            chunks.append(chunk)

    # -- operations -----------------------------------------------------------------------------------------------

    def generate(
        self,
        model: str,
        request: GenerationRequest,
        *,
        timeout_s: float,
        json_schema: Mapping[str, Any] | None = None,
    ) -> ProviderGeneration:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "stream": False,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if json_schema is not None and Capability.STRUCTURED in self.capabilities:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": dict(json_schema), "strict": True},
            }
        body = self._request("POST", "/chat/completions", payload, timeout_s)
        try:
            choice = body["choices"][0]
            text = choice["message"]["content"]
        except (KeyError, IndexError, TypeError):
            text = None
        if not isinstance(text, str):
            raise ProviderResponseError(f"provider {self.name!r}: unexpected chat completion shape", provider=self.name)
        return ProviderGeneration(
            text=text,
            model_version=_str_or_none(body.get("model")),
            usage=_usage(body.get("usage")),
            finish_reason=_str_or_none(choice.get("finish_reason")),
        )

    def embed(self, model: str, texts: Sequence[str], *, timeout_s: float) -> ProviderEmbedding:
        body = self._request("POST", "/embeddings", {"model": model, "input": list(texts)}, timeout_s)
        try:
            rows = sorted(body["data"], key=lambda r: r["index"])
            vectors = tuple(tuple(float(x) for x in r["embedding"]) for r in rows)
        except (KeyError, TypeError, ValueError):
            raise ProviderResponseError(
                f"provider {self.name!r}: unexpected embeddings shape", provider=self.name
            ) from None
        return ProviderEmbedding(vectors=vectors, model_version=_str_or_none(body.get("model")), usage=_usage(None))

    def probe(self, *, timeout_s: float) -> ProbeResult:
        try:
            body = self._request("GET", "/models", None, timeout_s)
        except (ProviderUnavailableError, ProviderTimeoutError, ProviderResponseError, EgressDeniedError) as exc:
            return ProbeResult(ok=False, detail=str(exc))
        ids = (
            tuple(str(m.get("id")) for m in body.get("data", []) if isinstance(m, dict))
            if isinstance(body, dict)
            else ()
        )
        return ProbeResult(ok=True, detail=f"{len(ids)} model(s) listed", models=ids)


def _str_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _usage(raw: Any) -> Usage:
    if not isinstance(raw, dict):
        return Usage()
    p, c = raw.get("prompt_tokens"), raw.get("completion_tokens")
    return Usage(
        prompt_tokens=p if isinstance(p, int) and p >= 0 else None,
        completion_tokens=c if isinstance(c, int) and c >= 0 else None,
    )
