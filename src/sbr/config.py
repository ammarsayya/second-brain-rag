"""Configuration system (T-P1-02, HC-02, docs/32 §6).

The configuration is the single source of filesystem roots, governor limits and the role-to-model map. No other module
hard-codes a path. Loading order (highest priority first): ``SBR_*`` environment variables, then the TOML file.

Invariants enforced here (they are also re-checked by SourceFS at runtime):

* Source roots are read-only. A source root cannot be configured writable (``read_only = false`` is rejected).
* Source roots, ``var``, ``vault`` and ``curation`` never overlap one another in a way that would let the system write
  inside a source root.
* Protected paths (for example the exact-duplicate quarantine ``D:\\studium_duplicated``) are neither a source root
  nor a writable root, and are never read or written by sbr.
* ``restricted`` content is never allowed for any model role (docs/22 §3, Q-I12 default).

Original path strings are preserved verbatim (provenance). Comparisons use a normalized key (see :func:`path_key`).
"""

from __future__ import annotations

import hashlib
import json
import ntpath
import os
import re
import tomllib
from enum import StrEnum
from pathlib import Path, PureWindowsPath
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from sbr.egress import local_url_problem

DEFAULT_CONFIG_PATH = Path("config") / "sbr.toml"
CONFIG_ENV_VAR = "SBR_CONFIG"

_ROOT_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_TIME_WINDOW_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-3]):[0-5]\d$")


class ConfigError(Exception):
    """Raised when a configuration cannot be loaded or is invalid. The message lists every problem."""


class Sensitivity(StrEnum):
    """Sensitivity classes (docs/22 §3, docs/31 ``blob.sensitivity``)."""

    NORMAL = "normal"
    PERSONAL = "personal"
    THIRD_PARTY_PERSONAL = "third_party_personal"
    RESTRICTED = "restricted"


class SourceKind(StrEnum):
    """Kinds of configured source roots (docs/31 ``source_root.kind``)."""

    UNIVERSITY = "university"
    EXTERNAL_ACCEPTED = "external_accepted"
    PERSONAL = "personal"


class ProcessPriority(StrEnum):
    """Worker process priority (docs/08 §5, NFR-06)."""

    IDLE = "idle"
    BELOW_NORMAL = "below_normal"
    NORMAL = "normal"


def path_key(path: str | os.PathLike[str]) -> str:
    """Return a normalized comparison key for a Windows or POSIX path.

    The key is absolute-normalized, case-folded and uses ``\\`` separators with no trailing separator. It is only used
    for containment and overlap checks. It is never stored in place of the original path.
    """
    raw = os.fspath(path)
    if raw.startswith("\\\\?\\"):
        raw = raw[4:]
    normalized = ntpath.normpath(raw.replace("/", "\\"))
    return normalized.rstrip("\\").casefold() if not normalized.endswith(":\\") else normalized.casefold()


def is_within(child: str | os.PathLike[str], parent: str | os.PathLike[str]) -> bool:
    """True if ``child`` equals ``parent`` or lies inside it (lexical check on normalized keys)."""
    c, p = path_key(child), path_key(parent)
    if c == p:
        return True
    prefix = p if p.endswith("\\") else p + "\\"
    return c.startswith(prefix)


def _require_absolute(value: str, field: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"{field} must not be empty")
    if not (PureWindowsPath(value).is_absolute() or Path(value).is_absolute()):
        raise ValueError(f"{field} must be an absolute path, got {value!r}")
    return value


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class SourceRootConfig(_Strict):
    """A read-only source root. ``read_only`` exists only so that an explicit ``false`` can be rejected loudly."""

    id: str
    path: str
    kind: SourceKind = SourceKind.UNIVERSITY
    read_only: Literal[True] = True

    @field_validator("id")
    @classmethod
    def _check_id(cls, v: str) -> str:
        if not _ROOT_ID_RE.match(v):
            raise ValueError(f"source root id {v!r} must match {_ROOT_ID_RE.pattern}")
        return v

    @field_validator("path")
    @classmethod
    def _check_path(cls, v: str) -> str:
        return _require_absolute(v, "source root path")

    @model_validator(mode="before")
    @classmethod
    def _reject_writable(cls, data: Any) -> Any:
        if isinstance(data, dict) and "read_only" in data and data["read_only"] is not True:
            raise ValueError("source roots are always read-only (HC-01/HC-03); remove 'read_only' or set it to true")
        return data


class RootsConfig(_Strict):
    """Filesystem roots (ADR-001). ``vault`` is optional for commands that never use the VaultWriter."""

    sources: Annotated[list[SourceRootConfig], Field(min_length=1)]
    var: str
    curation: str
    vault: str | None = None
    protected: list[str] = Field(
        default_factory=list,
        description="Paths sbr never reads or writes (e.g. the duplicate quarantine). Not source roots.",
    )

    @field_validator("var", "curation")
    @classmethod
    def _abs(cls, v: str) -> str:
        return _require_absolute(v, "root")

    @field_validator("vault")
    @classmethod
    def _abs_vault(cls, v: str | None) -> str | None:
        return None if v is None else _require_absolute(v, "vault")

    @field_validator("protected")
    @classmethod
    def _abs_protected(cls, v: list[str]) -> list[str]:
        return [_require_absolute(p, "protected path") for p in v]

    @model_validator(mode="after")
    def _check_layout(self) -> Self:
        problems: list[str] = []
        ids = [s.id for s in self.sources]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            problems.append(f"duplicate source root ids: {dupes}")
        for i, a in enumerate(self.sources):
            for b in self.sources[i + 1 :]:
                if is_within(a.path, b.path) or is_within(b.path, a.path):
                    problems.append(f"source roots {a.id!r} and {b.id!r} overlap")
        writable = {"var": self.var, "curation": self.curation}
        if self.vault is not None:
            writable["vault"] = self.vault
        for name, wpath in writable.items():
            for s in self.sources:
                if is_within(wpath, s.path) or is_within(s.path, wpath):
                    problems.append(f"{name} ({wpath}) overlaps read-only source root {s.id!r} ({s.path})")
        for prot in self.protected:
            for s in self.sources:
                if is_within(prot, s.path) or is_within(s.path, prot):
                    problems.append(f"protected path {prot} overlaps source root {s.id!r}; it must not be ingested")
            for name, wpath in writable.items():
                if is_within(wpath, prot) or is_within(prot, wpath):
                    problems.append(f"{name} ({wpath}) overlaps protected path {prot}")
        if problems:
            raise ValueError("; ".join(problems))
        return self


class GovernorConfig(_Strict):
    """Resource governor limits (NFR-06). Enforcement is T-P1-10."""

    max_workers: Annotated[int, Field(ge=1, le=64)] = 6
    max_ram_gb: Annotated[float, Field(gt=0)] = 40.0
    disk_floor_gb: Annotated[float, Field(ge=0)] = 50.0
    priority: ProcessPriority = ProcessPriority.BELOW_NORMAL
    time_windows: list[str] = Field(default_factory=list, description="Allowed run windows 'HH:MM-HH:MM' (local time)")
    stage_concurrency: dict[str, Annotated[int, Field(ge=1)]] = Field(default_factory=dict)

    @field_validator("time_windows")
    @classmethod
    def _check_windows(cls, v: list[str]) -> list[str]:
        bad = [w for w in v if not _TIME_WINDOW_RE.match(w)]
        if bad:
            raise ValueError(f"time windows must look like 'HH:MM-HH:MM', got {bad}")
        return v


class RoleConfig(_Strict):
    """A model role (docs/17 §1). ``primary``/``fallbacks`` are ``provider/model`` references into
    ``[models.providers]``; a role without ``primary`` is unconfigured and the gateway refuses it."""

    primary: str | None = None
    fallbacks: list[str] = Field(default_factory=list)
    allowed_sensitivity: list[Sensitivity] = Field(default_factory=lambda: [Sensitivity.NORMAL])
    max_cost_per_call: Annotated[float, Field(ge=0)] | None = None
    temperature: Annotated[float, Field(ge=0, le=2)] | None = None
    cache: bool = True

    @field_validator("allowed_sensitivity")
    @classmethod
    def _no_restricted(cls, v: list[Sensitivity]) -> list[Sensitivity]:
        if Sensitivity.RESTRICTED in v:
            raise ValueError("'restricted' content may never be sent to any model role (docs/22 §3)")
        return v


MODEL_ROLES = frozenset(
    {"embed", "rerank", "ocr", "math_ocr", "layout", "classify", "extract", "reason", "judge", "vision", "research"}
)  # docs/17 §1
_PROVIDER_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_ENV_NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]{0,127}$")


class ProviderKind(StrEnum):
    """Adapter kinds implemented by :mod:`sbr.models` (ADR-040). No remote kind exists in this phase."""

    MOCK = "mock"  # deterministic, in-process; for tests and dry runs
    OPENAI_COMPATIBLE = "openai_compatible"  # a local server (Ollama, llama.cpp server, LM Studio, vLLM) on loopback


class ProviderConfig(_Strict):
    """One model provider. Remote endpoints are rejected (ADR-039/ADR-040); credentials are never stored here."""

    kind: ProviderKind
    base_url: str | None = Field(default=None, description="Loopback endpoint, e.g. http://127.0.0.1:11434/v1")
    timeout_s: Annotated[float, Field(gt=0, le=3600)] = 120.0
    max_retries: Annotated[int, Field(ge=0, le=5)] = 1
    capabilities: list[str] | None = Field(
        default=None, description="Restrict the adapter's capabilities (cannot add any it does not implement)"
    )
    api_key_env: str | None = Field(
        default=None, description="Name of an environment variable holding a token for a local server (never the token)"
    )

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.kind is ProviderKind.OPENAI_COMPATIBLE:
            if not self.base_url:
                raise ValueError("openai_compatible providers need base_url (a loopback URL)")
            problem = local_url_problem(self.base_url)
            if problem:
                raise ValueError(f"base_url {self.base_url!r}: {problem}")
        elif self.base_url is not None:
            raise ValueError("mock providers take no base_url")
        if self.api_key_env is not None and not _ENV_NAME_RE.match(self.api_key_env):
            raise ValueError("api_key_env must be an environment variable NAME (A-Z, 0-9, _), not a key")
        return self


class ModelsConfig(_Strict):
    """Role-to-model map and providers (docs/17, ADR-025/ADR-040).

    ``allow_remote`` can only be ``false``: the owner has not authorized remote providers (Q-B03/Q-B04, 2026-11-04).
    Enabling one needs a new owner authorization and a reviewed code change, not a configuration flag.
    """

    allow_remote: Literal[False] = False
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    roles: dict[str, RoleConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_references(self) -> Self:
        problems: list[str] = []
        for name in self.providers:
            if not _PROVIDER_NAME_RE.match(name):
                problems.append(f"provider name {name!r} must match {_PROVIDER_NAME_RE.pattern}")
        for role, rc in self.roles.items():
            if role not in MODEL_ROLES:
                problems.append(f"unknown role {role!r} (known: {', '.join(sorted(MODEL_ROLES))})")
            for ref in ([rc.primary] if rc.primary else []) + rc.fallbacks:
                provider, sep, model = ref.partition("/")
                if not sep or not provider or not model:
                    problems.append(f"role {role!r}: model reference {ref!r} must look like 'provider/model'")
                elif provider not in self.providers:
                    problems.append(f"role {role!r}: provider {provider!r} is not defined in [models.providers]")
            if rc.fallbacks and not rc.primary:
                problems.append(f"role {role!r}: fallbacks without a primary")
        if problems:
            raise ValueError("; ".join(problems))
        return self


class LoggingConfig(_Strict):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    max_bytes: Annotated[int, Field(ge=1024)] = 10 * 1024 * 1024
    backup_count: Annotated[int, Field(ge=0)] = 10


class SbrConfig(BaseSettings):
    """Validated sbr configuration. Build it with :func:`load_config`."""

    model_config = SettingsConfigDict(
        env_prefix="SBR_",
        env_nested_delimiter="__",
        extra="forbid",
        frozen=True,
    )

    roots: RootsConfig
    governor: GovernorConfig = Field(default_factory=GovernorConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # File values arrive as init kwargs; environment variables override them. No .env or secret-dir sources.
        return (env_settings, init_settings)

    @property
    def var_path(self) -> Path:
        return Path(self.roots.var)

    @property
    def db_dir(self) -> Path:
        return self.var_path / "db"

    @property
    def logs_dir(self) -> Path:
        return self.var_path / "logs"

    @property
    def traces_dir(self) -> Path:
        return self.var_path / "traces"

    @property
    def vault_path(self) -> Path:
        """Configured Obsidian vault root; unavailable until the owner selects one."""
        if self.roots.vault is None:
            raise ConfigError("roots.vault must be configured before opening the VaultWriter")
        return Path(self.roots.vault)

    def source_root(self, root_id: str) -> SourceRootConfig:
        for s in self.roots.sources:
            if s.id == root_id:
                return s
        raise KeyError(f"unknown source root id {root_id!r}")

    def config_hash(self) -> str:
        """Stable hash of the effective configuration (recorded in the run ledger)."""
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _format_validation_error(exc: ValidationError, origin: str) -> str:
    lines = [f"invalid configuration ({origin}):"]
    for e in exc.errors():
        loc = ".".join(str(p) for p in e["loc"]) or "<root>"
        lines.append(f"  - {loc}: {e['msg']}")
    return "\n".join(lines)


def resolve_config_path(path: str | os.PathLike[str] | None = None) -> Path:
    """Explicit path > ``SBR_CONFIG`` > ``config/sbr.toml`` relative to the working directory."""
    if path is not None:
        return Path(path)
    env = os.environ.get(CONFIG_ENV_VAR)
    return Path(env) if env else DEFAULT_CONFIG_PATH


def load_config(path: str | os.PathLike[str] | None = None) -> SbrConfig:
    """Load and validate the configuration. Raises :class:`ConfigError` with every problem listed."""
    cfg_path = resolve_config_path(path)
    try:
        raw = cfg_path.read_bytes()
    except FileNotFoundError:
        raise ConfigError(
            f"configuration file not found: {cfg_path} (copy config/sbr.example.toml to config/sbr.toml "
            f"or set {CONFIG_ENV_VAR})"
        ) from None
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise ConfigError(f"configuration file {cfg_path} is not valid UTF-8 TOML: {exc}") from exc
    return config_from_mapping(data, origin=str(cfg_path))


def config_from_mapping(data: dict[str, Any], origin: str = "<mapping>") -> SbrConfig:
    """Validate an already-parsed mapping (environment overrides still apply)."""
    try:
        return SbrConfig(**data)
    except ValidationError as exc:
        raise ConfigError(_format_validation_error(exc, origin)) from exc
