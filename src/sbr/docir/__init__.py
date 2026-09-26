"""DocIR: the parser-independent extraction contract (T-P4-01, docs/09 §2, ADR-011)."""

from __future__ import annotations

from sbr.docir.models import (
    DOCIR_VERSION,
    Annotation,
    Block,
    BlockKind,
    DocIR,
    DocumentInfo,
    Equation,
    EquationReading,
    EquationSourceKind,
    ExtractorRef,
    Figure,
    FigureKind,
    Page,
    Quality,
    Reference,
    Section,
    Table,
    ValidationStatus,
)

__all__ = [
    "DOCIR_VERSION",
    "Annotation",
    "Block",
    "BlockKind",
    "DocIR",
    "DocumentInfo",
    "Equation",
    "EquationReading",
    "EquationSourceKind",
    "ExtractorRef",
    "Figure",
    "FigureKind",
    "Page",
    "Quality",
    "Reference",
    "Section",
    "Table",
    "ValidationStatus",
]
