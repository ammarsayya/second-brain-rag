"""Render JSON Schemas of the core models. Writing them to ``schemas/`` is done by ``tools/export_schemas.py``."""

from __future__ import annotations

import json
from typing import Any

from sbr.docir import DocIR
from sbr.schemas import EXPORTED_MODELS, SCHEMA_VERSION
from sbr.schemas.base import StrictModel

# DocIR is combined here, not added to sbr.schemas.EXPORTED_MODELS itself: sbr.docir.models imports from
# sbr.schemas.base, so sbr/schemas/__init__.py importing sbr.docir at module scope would be a genuine import
# cycle (loading sbr.docir triggers sbr.schemas.base, which requires sbr/schemas/__init__.py to finish first).
# This module is a leaf that nothing in sbr.schemas imports, so it can safely depend on both.
ALL_EXPORTED_MODELS: tuple[type[StrictModel], ...] = (*EXPORTED_MODELS, DocIR)


def render_schemas() -> dict[str, str]:
    """Return ``{filename: json_text}`` for every exported model (deterministic output)."""
    out: dict[str, str] = {}
    for model in ALL_EXPORTED_MODELS:
        schema: dict[str, Any] = model.model_json_schema(mode="validation")
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"sbr/{SCHEMA_VERSION}/{model.__name__}.json"
        schema["x-sbr-schema-version"] = SCHEMA_VERSION
        out[f"{model.__name__}.json"] = json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return out
