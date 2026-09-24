"""Render JSON Schemas of the core models. Writing them to ``schemas/`` is done by ``tools/export_schemas.py``."""

from __future__ import annotations

import json
from typing import Any

from sbr.schemas import EXPORTED_MODELS, SCHEMA_VERSION


def render_schemas() -> dict[str, str]:
    """Return ``{filename: json_text}`` for every exported model (deterministic output)."""
    out: dict[str, str] = {}
    for model in EXPORTED_MODELS:
        schema: dict[str, Any] = model.model_json_schema(mode="validation")
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"sbr/{SCHEMA_VERSION}/{model.__name__}.json"
        schema["x-sbr-schema-version"] = SCHEMA_VERSION
        out[f"{model.__name__}.json"] = json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return out
