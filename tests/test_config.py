"""T-P1-02: configuration load, validation and environment overrides."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sbr.config import (
    ConfigError,
    Sensitivity,
    config_from_mapping,
    is_within,
    load_config,
    path_key,
)

EXAMPLE = Path(__file__).resolve().parent.parent / "config" / "sbr.example.toml"
MACOS_EXAMPLE = EXAMPLE.with_name("sbr.macos.example.toml")


def base(**over: Any) -> dict[str, Any]:
    roots: dict[str, Any] = {
        "sources": [{"id": "mbi", "path": "D:\\MBI-BRAIN"}],
        "var": "D:\\AgenticAI\\second-brain-rag\\var",
        "curation": "D:\\AgenticAI\\second-brain-rag\\curation",
        "protected": ["D:\\studium_duplicated"],
    }
    roots.update(over)
    return {"roots": roots}


def test_example_config_is_valid() -> None:
    cfg = load_config(EXAMPLE)
    assert cfg.roots.sources[0].id == "mbi"
    assert cfg.roots.sources[0].read_only is True
    assert cfg.roots.vault == r"D:\AgenticAI\second-brain-rag\vault"  # Q-B02 resolved by ADR-037
    assert cfg.models.roles["reason"].primary is None  # Q-B04 open
    assert cfg.config_hash().startswith("sha256:")


def test_macos_example_config_is_valid_and_keeps_the_same_safety_settings() -> None:
    windows, macos = load_config(EXAMPLE), load_config(MACOS_EXAMPLE)
    assert [(s.id, s.kind, s.read_only) for s in macos.roots.sources] == [
        (s.id, s.kind, s.read_only) for s in windows.roots.sources
    ]
    assert macos.roots.sources[0].path == "/Users/ammar/DriveD/MBI-BRAIN"
    assert macos.roots.protected == ["/Users/ammar/DriveD/studium_duplicated"]
    assert macos.models.roles["reason"].primary is None  # Q-B04 open
    assert macos.models.roles["reason"].allowed_sensitivity == windows.models.roles["reason"].allowed_sensitivity
    assert macos.governor.max_ram_gb < 36  # below the M5 Max's 36 GB of unified memory


def test_source_root_cannot_be_writable() -> None:
    data = base(sources=[{"id": "mbi", "path": "D:\\MBI-BRAIN", "read_only": False}])
    with pytest.raises(ConfigError, match="always read-only"):
        config_from_mapping(data)


@pytest.mark.parametrize("field", ["var", "curation", "vault"])
def test_writable_root_inside_source_rejected(field: str) -> None:
    with pytest.raises(ConfigError, match="overlaps read-only source root"):
        config_from_mapping(base(**{field: "D:\\MBI-BRAIN\\derived"}))


def test_source_inside_var_rejected() -> None:
    with pytest.raises(ConfigError, match="overlaps read-only source root"):
        config_from_mapping(base(sources=[{"id": "x", "path": "D:\\AgenticAI\\second-brain-rag\\var\\src"}]))


def test_overlap_check_is_case_and_separator_insensitive() -> None:
    with pytest.raises(ConfigError, match="overlaps"):
        config_from_mapping(base(var="d:/mbi-brain/var"))


def test_protected_path_cannot_be_source() -> None:
    data = base(sources=[{"id": "dup", "path": "D:\\studium_duplicated"}])
    with pytest.raises(ConfigError, match="protected path"):
        config_from_mapping(data)


def test_protected_path_cannot_be_writable_root() -> None:
    with pytest.raises(ConfigError, match="overlaps protected path"):
        config_from_mapping(base(var="D:\\studium_duplicated\\var"))


def test_overlapping_and_duplicate_sources_rejected() -> None:
    data = base(sources=[{"id": "a", "path": "D:\\MBI-BRAIN"}, {"id": "a", "path": "D:\\MBI-BRAIN\\books"}])
    with pytest.raises(ConfigError) as ei:
        config_from_mapping(data)
    assert "duplicate source root ids" in str(ei.value)
    assert "overlap" in str(ei.value)


def test_relative_paths_rejected() -> None:
    with pytest.raises(ConfigError, match="absolute path"):
        config_from_mapping(base(var="var"))


def test_unknown_keys_rejected() -> None:
    data = base()
    data["governer"] = {"max_workers": 2}
    with pytest.raises(ConfigError, match="governer"):
        config_from_mapping(data)


def test_restricted_never_allowed_for_models() -> None:
    data = base()
    data["models"] = {"roles": {"vision": {"allowed_sensitivity": ["normal", "restricted"]}}}
    with pytest.raises(ConfigError, match="restricted"):
        config_from_mapping(data)


def test_governor_limits_validated() -> None:
    data = base()
    data["governor"] = {"max_workers": 0, "time_windows": ["25:00-06:00"]}
    with pytest.raises(ConfigError) as ei:
        config_from_mapping(data)
    msg = str(ei.value)
    assert "governor.max_workers" in msg
    assert "governor.time_windows" in msg


def test_env_overrides_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SBR_GOVERNOR__MAX_WORKERS", "3")
    monkeypatch.setenv("SBR_LOGGING__LEVEL", "DEBUG")
    cfg = load_config(EXAMPLE)
    assert cfg.governor.max_workers == 3
    assert cfg.logging.level == "DEBUG"
    assert cfg.governor.disk_floor_gb == 50  # untouched file value survives the merge
    assert cfg.roots.sources[0].id == "mbi"


def test_env_override_is_validated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SBR_GOVERNOR__MAX_WORKERS", "-1")
    with pytest.raises(ConfigError, match="max_workers"):
        load_config(EXAMPLE)


def test_config_path_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SBR_CONFIG", str(EXAMPLE))
    assert load_config().roots.sources[0].path == "D:\\MBI-BRAIN"


def test_missing_and_malformed_files(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.toml")
    bad = tmp_path / "bad.toml"
    bad.write_text("[roots\nvar = 1", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid UTF-8 TOML"):
        load_config(bad)


def test_original_path_string_is_preserved() -> None:
    cfg = config_from_mapping(base(sources=[{"id": "mbi", "path": "D:\\MBI-BRAIN\\"}]))
    assert cfg.roots.sources[0].path == "D:\\MBI-BRAIN\\"


def test_config_hash_is_stable_and_sensitive() -> None:
    a = config_from_mapping(base())
    b = config_from_mapping(base())
    c = config_from_mapping(base(var="E:\\var"))
    assert a.config_hash() == b.config_hash() != c.config_hash()


def test_path_helpers() -> None:
    assert path_key("D:/MBI-BRAIN/") == path_key("d:\\mbi-brain")
    assert path_key("\\\\?\\D:\\MBI-BRAIN") == path_key("D:\\MBI-BRAIN")
    assert is_within("D:\\MBI-BRAIN\\a\\b.pdf", "D:\\MBI-BRAIN")
    assert not is_within("D:\\MBI-BRAIN-2\\a.pdf", "D:\\MBI-BRAIN")
    assert is_within("D:\\x", "D:\\")
    assert Sensitivity("restricted") is Sensitivity.RESTRICTED
