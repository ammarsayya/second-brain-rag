"""Load a hand/AI-authored extraction gold file (T-P3-01/02/03's eventual labeled output) into the harness's
:class:`~sbr.eval.extract.contracts.PageGold` contract, and fetch each sample's source bytes read-only via
SourceFS. A minimal YAML schema, deliberately not the final MBI-Gold-Extract/Math/Layout format (those need
T-P3-02/03's owner-approved labeling process, still gated) — this exists so the harness has something real to
run against today.

::

    samples:
      - relpath: "Some\\Real\\Path.pdf"   # relative to a configured source root
        root_id: mbi
        page: 1
        gold:
          blocks: [{kind: paragraph, reading_order: 0, text: "..."}]
          equations: [{latex_normalized: "x^2", source_kind: latex_source}]
          tables: [[["a", "b"], ["c", "d"]]]
          figures: [{bbox: [0, 0, 10, 10], caption: "Bild 1", is_knowledge_bearing: true}]
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from sbr.eval.extract.contracts import GoldBlock, GoldEquation, GoldFigure, PageGold
from sbr.sourcefs import SourceFS


def _parse_gold(raw: dict[str, Any]) -> PageGold:
    blocks = tuple(
        GoldBlock(kind=b["kind"], reading_order=b["reading_order"], text=b["text"]) for b in raw.get("blocks", [])
    )
    equations = tuple(
        GoldEquation(latex_normalized=e["latex_normalized"], source_kind=e["source_kind"])
        for e in raw.get("equations", [])
    )
    tables = tuple(tuple(tuple(row) for row in table) for table in raw.get("tables", []))
    figures = tuple(
        GoldFigure(bbox=tuple(f["bbox"]), caption=f.get("caption"), is_knowledge_bearing=f["is_knowledge_bearing"])
        for f in raw.get("figures", [])
    )
    return PageGold(page=raw["page"], blocks=blocks, equations=equations, tables=tables, figures=figures)


def load_gold_samples(source_fs: SourceFS, path: Path) -> list[tuple[bytes, int, PageGold]]:
    """Read the gold file at ``path`` and fetch every sample's source bytes read-only via SourceFS."""
    yaml = YAML(typ="safe")
    doc = yaml.load(path.read_text(encoding="utf-8"))
    samples: list[tuple[bytes, int, PageGold]] = []
    for entry in doc.get("samples", []):
        page = entry["page"]
        gold = _parse_gold({**entry["gold"], "page": page})
        pdf_bytes = source_fs.read_bytes(entry["root_id"], entry["relpath"])
        samples.append((pdf_bytes, page, gold))
    return samples


__all__ = ["load_gold_samples"]
