"""T-P7-01: local-only egress policy and model configuration validation (ADR-039/ADR-040)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from sbr.config import ConfigError, ModelsConfig, config_from_mapping
from sbr.egress import is_loopback_host, local_url_problem, resolves_only_to_loopback

_ROOT = Path(tempfile.gettempdir()) / "sbr-models-test"


def _cfg(models: dict[str, Any]) -> dict[str, Any]:
    roots = {
        "sources": [{"id": "fx", "path": str(_ROOT / "src")}],
        "var": str(_ROOT / "var"),
        "curation": str(_ROOT / "cur"),
    }
    return {"roots": roots, "models": models}


@pytest.mark.parametrize(
    "url", ["http://127.0.0.1:11434/v1", "http://localhost:8080/v1", "http://[::1]:1234/v1", "https://127.0.0.5/v1"]
)
def test_loopback_urls_accepted(url: str) -> None:
    assert local_url_problem(url) is None


@pytest.mark.parametrize(
    ("url", "why"),
    [
        ("https://api.openai.com/v1", "not a loopback"),
        ("https://api.anthropic.com", "not a loopback"),
        ("http://10.0.0.5:11434/v1", "not a loopback"),
        ("http://192.168.1.10/v1", "not a loopback"),
        ("http://0.0.0.0:11434/v1", "not a loopback"),
        ("http://localhost.evil.example/v1", "not a loopback"),
        ("http://127.0.0.1.nip.io/v1", "not a loopback"),
        ("http://user:pw@127.0.0.1/v1", "credentials"),
        ("http://127.0.0.1@evil.example/v1", "credentials"),
        ("ftp://127.0.0.1/v1", "scheme"),
        ("file:///etc/passwd", "scheme"),
        ("http:///v1", "no host"),
        ("http://127.0.0.1:99999/v1", "malformed"),
        ("http://127.0.0.1/v1?redirect=x", "query"),
    ],
)
def test_non_local_or_malformed_urls_rejected(url: str, why: str) -> None:
    problem = local_url_problem(url)
    assert problem is not None
    assert why in problem


def test_loopback_host_predicate_never_resolves_names() -> None:
    assert is_loopback_host("LOCALHOST.")
    assert not is_loopback_host("example.com")
    assert resolves_only_to_loopback("127.0.0.1", 80)
    assert not resolves_only_to_loopback("example.com", 80)  # rejected before any DNS lookup


def test_default_models_config_is_local_only_and_empty() -> None:
    cfg = config_from_mapping(_cfg({}))
    assert cfg.models.allow_remote is False
    assert cfg.models.providers == {}
    assert ModelsConfig().allow_remote is False


def test_allow_remote_cannot_be_enabled_by_file_or_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ConfigError, match="allow_remote"):
        config_from_mapping(_cfg({"allow_remote": True}))
    monkeypatch.setenv("SBR_MODELS__ALLOW_REMOTE", "true")
    with pytest.raises(ConfigError, match="allow_remote"):
        config_from_mapping(_cfg({}))


def test_remote_provider_url_rejected_at_config_time() -> None:
    models = {"providers": {"cloud": {"kind": "openai_compatible", "base_url": "https://api.openai.com/v1"}}}
    with pytest.raises(ConfigError, match="not a loopback"):
        config_from_mapping(_cfg(models))


@pytest.mark.parametrize(
    ("models", "match"),
    [
        ({"providers": {"local": {"kind": "openai_compatible"}}}, "need base_url"),
        ({"providers": {"m": {"kind": "mock", "base_url": "http://127.0.0.1/v1"}}}, "no base_url"),
        ({"providers": {"m": {"kind": "anthropic"}}}, "kind"),
        ({"providers": {"m": {"kind": "mock", "api_key": "sk-123"}}}, "api_key"),
        ({"providers": {"m": {"kind": "mock", "api_key_env": "sk-live-123"}}}, "NAME"),
        ({"providers": {"m": {"kind": "mock", "timeout_s": 0}}}, "timeout_s"),
        ({"providers": {"m": {"kind": "mock", "max_retries": 9}}}, "max_retries"),
        ({"providers": {"Bad Name": {"kind": "mock"}}}, "provider name"),
        ({"roles": {"reasoning": {"primary": "m/x"}}, "providers": {"m": {"kind": "mock"}}}, "unknown role"),
        ({"roles": {"reason": {"primary": "nowhere/x"}}}, "not defined"),
        ({"roles": {"reason": {"primary": "no-slash"}}, "providers": {"m": {"kind": "mock"}}}, "provider/model"),
        ({"roles": {"reason": {"fallbacks": ["m/x"]}}, "providers": {"m": {"kind": "mock"}}}, "without a primary"),
    ],
)
def test_invalid_model_configuration_is_reported(models: dict[str, Any], match: str) -> None:
    with pytest.raises(ConfigError, match=match):
        config_from_mapping(_cfg(models))


def test_valid_local_configuration_loads() -> None:
    cfg = config_from_mapping(
        _cfg(
            {
                "providers": {
                    "ollama": {"kind": "openai_compatible", "base_url": "http://127.0.0.1:11434/v1", "timeout_s": 300},
                    "mock": {"kind": "mock"},
                },
                "roles": {"reason": {"primary": "ollama/qwen2.5:7b-instruct", "fallbacks": ["mock/echo"]}},
            }
        )
    )
    assert cfg.models.roles["reason"].primary == "ollama/qwen2.5:7b-instruct"
