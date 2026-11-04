"""Owner review workflow for heuristic MBI-Gold-Layout drafts (T-P3-03).

``--prepare`` validates the aggregate annotation file through the real ``load_gold_samples()`` loader, exports
each referenced page as a one-page PDF, and writes a Markdown index pairing that page with its draft fields.
After inspecting (and, for ``correct``, editing the aggregate YAML), the owner records one explicit decision
with ``--record SAMPLE_ID --decision accept|correct|reject``, or in bulk with ``--export-sheet``/``--record-sheet``.
Decisions never imply task completion; all 40 must be owner-verified and any rejection resolved before T-P3-03
can close.
"""

from __future__ import annotations

import argparse
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pypdf
from ruamel.yaml import YAML

from sbr.config import load_config
from sbr.eval.extract.goldfile import load_gold_samples
from sbr.eval.review_sheet import read_sheet_decisions, write_review_sheet
from sbr.safety import assert_writable
from sbr.sourcefs import SourceFS

DEFAULT_ANNOTATIONS = Path("eval/gold/layout/layout_annotations.yaml")
DEFAULT_REVIEW_DIR = Path("eval/gold/layout/review")
DEFAULT_DECISIONS = Path("eval/gold/layout/layout_verification.yaml")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare or record owner review of MBI-Gold-Layout drafts.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true", help="Export one-page PDFs and a Markdown review index.")
    mode.add_argument("--record", metavar="SAMPLE_ID", help="Record an owner decision for one sample.")
    mode.add_argument("--export-sheet", type=Path, metavar="CSV", help="Write a review sheet with blank decisions.")
    mode.add_argument("--record-sheet", type=Path, metavar="CSV", help="Record every decided row of a review sheet.")
    parser.add_argument("--decision", choices=("accept", "correct", "reject"))
    parser.add_argument("--note", default="", help="Optional owner note for --record.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS)
    parser.add_argument("--review-dir", type=Path, default=DEFAULT_REVIEW_DIR)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    return parser.parse_args()


def _load_yaml(path: Path) -> dict[str, Any]:
    doc = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise TypeError(f"expected a YAML mapping in {path}")
    return doc


def _dump_yaml(path: Path, doc: dict[str, Any]) -> None:
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.width = 120
    with path.open("w", encoding="utf-8") as stream:
        yaml.dump(doc, stream)


def _existing_decisions(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    doc = _load_yaml(path)
    return {str(row["sample_id"]): row for row in doc.get("decisions", [])}


def _write_page_pdf(pdf_bytes: bytes, page: int, destination: Path) -> None:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    if page < 1 or page > len(reader.pages):
        raise ValueError(f"page {page} outside PDF range 1..{len(reader.pages)}")
    writer = pypdf.PdfWriter()
    writer.add_page(reader.pages[page - 1])
    with destination.open("wb") as stream:
        writer.write(stream)


def _prepare(args: argparse.Namespace, source_fs: SourceFS, config: Any) -> dict[str, Any]:
    annotations = _load_yaml(args.annotations)
    loaded = load_gold_samples(source_fs, args.annotations)
    entries = annotations.get("samples", [])
    if len(loaded) != len(entries):
        raise ValueError("load_gold_samples() count disagrees with the annotation document")
    decisions = _existing_decisions(args.decisions)
    args.review_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        "# MBI-Gold-Layout owner review",
        "",
        "> Candidate heuristic annotations only. Compare every annotation with its linked PDF page, edit the",
        "> aggregate YAML when needed, then record exactly one owner decision per page.",
        "",
        f"- Annotation source: `{args.annotations}`",
        f"- Pages: {len(entries)}",
        "- Record: `python tools/gold_verify_layout.py --config config/sbr.toml --record layout-NNN "
        "--decision accept|correct|reject`",
        "",
    ]
    for entry, (pdf_bytes, page, gold) in zip(entries, loaded, strict=True):
        sample_id = str(entry["sample_id"])
        pdf_name = f"{sample_id}.pdf"
        pdf_path = args.review_dir / pdf_name
        assert_writable(pdf_path.resolve(), config)
        _write_page_pdf(pdf_bytes, page, pdf_path)
        decision = decisions.get(sample_id, {}).get("decision", "pending")
        lines.extend(
            [
                f"## {sample_id} — {entry.get('bucket', 'unknown')}",
                "",
                f"[Open actual PDF page]({pdf_name}) · source page {page} · decision: **{decision}**",
                "",
                "| order | kind | draft text |",
                "|---:|---|---|",
            ]
        )
        for block in gold.blocks:
            safe_text = block.text.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {block.reading_order} | {block.kind} | {safe_text} |")
        if not gold.blocks:
            lines.append("| - | - | *(no text blocks drafted)* |")
        figures = [
            {"bbox": figure.bbox, "caption": figure.caption, "is_knowledge_bearing": figure.is_knowledge_bearing}
            for figure in gold.figures
        ]
        lines.extend(
            [
                "",
                f"- Tables: `{json.dumps(gold.tables, ensure_ascii=False)}`",
                f"- Figures: `{json.dumps(figures, ensure_ascii=False)}`",
                "",
            ]
        )

    index_path = args.review_dir / "README.md"
    assert_writable(index_path.resolve(), config)
    index_path.write_text("\n".join(lines), encoding="utf-8")
    return {"schema_load_ok": True, "pages_exported": len(entries), "review_index": str(index_path)}


def _write_decisions(args: argparse.Namespace, config: Any, decisions: dict[str, dict[str, Any]]) -> dict[str, int]:
    output = {
        "purpose": "T-P3-03 owner verification log",
        "annotations": str(args.annotations),
        "decisions": [decisions[key] for key in sorted(decisions)],
    }
    assert_writable(args.decisions.resolve(), config)
    args.decisions.parent.mkdir(parents=True, exist_ok=True)
    _dump_yaml(args.decisions, output)
    return {
        name: sum(row["decision"] == name for row in decisions.values()) for name in ("accept", "correct", "reject")
    }


def _decision_row(sample_id: str, decision: str, note: str) -> dict[str, Any]:
    return {"sample_id": sample_id, "decision": decision, "note": note, "verified_at": datetime.now(UTC).isoformat()}


def _record(args: argparse.Namespace, source_fs: SourceFS, config: Any) -> dict[str, Any]:
    if args.decision is None:
        raise ValueError("--decision is required with --record")
    annotations = _load_yaml(args.annotations)
    load_gold_samples(source_fs, args.annotations)  # schema + SourceFS check after any owner correction
    valid_ids = {str(entry["sample_id"]) for entry in annotations.get("samples", [])}
    if args.record not in valid_ids:
        raise ValueError(f"unknown sample id: {args.record}")
    decisions = _existing_decisions(args.decisions)
    decisions[args.record] = _decision_row(args.record, args.decision, args.note)
    counts = _write_decisions(args, config, decisions)
    return {
        "recorded": args.record,
        "decision": args.decision,
        "counts": counts,
        "pending": len(valid_ids) - len(decisions),
    }


def _export_sheet(args: argparse.Namespace, config: Any) -> dict[str, Any]:
    annotations = _load_yaml(args.annotations)
    rows = []
    for entry in annotations.get("samples", []):
        blocks = entry.get("gold", {}).get("blocks", [])
        kinds: dict[str, int] = {}
        for block in blocks:
            kinds[str(block.get("kind"))] = kinds.get(str(block.get("kind")), 0) + 1
        rows.append(
            {
                "sample_id": entry["sample_id"],
                "bucket": entry.get("bucket", ""),
                "review_pdf": f"{entry['sample_id']}.pdf",
                "relpath": entry.get("relpath", ""),
                "page": entry.get("page", ""),
                "draft_blocks": " ".join(f"{kind}={n}" for kind, n in sorted(kinds.items())),
                "draft_tables": len(entry.get("gold", {}).get("tables", [])),
                "draft_figures": len(entry.get("gold", {}).get("figures", [])),
            }
        )
    assert_writable(args.export_sheet.resolve(), config)
    write_review_sheet(args.export_sheet, rows)
    return {"sheet": str(args.export_sheet), "rows": len(rows)}


def _record_sheet(args: argparse.Namespace, source_fs: SourceFS, config: Any) -> dict[str, Any]:
    annotations = _load_yaml(args.annotations)
    load_gold_samples(source_fs, args.annotations)  # schema + SourceFS check after any owner correction
    valid_ids = {str(entry["sample_id"]) for entry in annotations.get("samples", [])}
    decided = read_sheet_decisions(args.record_sheet)
    unknown = [d.sample_id for d in decided if d.sample_id not in valid_ids]
    if unknown:
        raise ValueError(f"unknown sample ids in sheet: {', '.join(unknown)}")
    decisions = _existing_decisions(args.decisions)
    decisions.update({d.sample_id: _decision_row(d.sample_id, d.decision, d.note) for d in decided})
    counts = _write_decisions(args, config, decisions)
    return {"recorded": len(decided), "counts": counts, "pending": len(valid_ids) - len(decisions)}


def main() -> int:
    args = _arguments()
    config = load_config(args.config)
    source_fs = SourceFS(config)
    if args.prepare:
        result = _prepare(args, source_fs, config)
    elif args.export_sheet:
        result = _export_sheet(args, config)
    elif args.record_sheet:
        result = _record_sheet(args, source_fs, config)
    else:
        result = _record(args, source_fs, config)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
