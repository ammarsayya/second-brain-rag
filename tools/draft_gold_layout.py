"""Draft MBI-Gold-Layout annotations with deterministic pypdf heuristics (T-P3-03 prep).

No model or remote service is used.  Text position/font signals drive block kinds and reading order; aligned
text cells provide conservative table candidates; image XObject draw operations provide figure boxes and
nearby caption-like text.  Output is one aggregate YAML document in the exact ``load_gold_samples()`` schema.
It is a candidate draft only: the owner must review/correct/reject every page with
``tools/gold_verify_layout.py`` before T-P3-03 can be complete.
"""

from __future__ import annotations

import argparse
import io
import itertools
import json
import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pypdf
from ruamel.yaml import YAML

from sbr.config import load_config
from sbr.eval.extract.goldfile import load_gold_samples
from sbr.safety import assert_writable
from sbr.sourcefs import SourceFS

DEFAULT_SAMPLE = Path("eval/gold/layout_sample.yaml")
DEFAULT_OUTPUT = Path("eval/gold/layout/layout_annotations.yaml")
_CAPTION = re.compile(r"^(?:abb(?:ildung)?|bild|fig(?:ure|\.)?|table|tabelle)\s*[.:\-]?\s*\d*", re.IGNORECASE)
_LIST = re.compile(r"^(?:[\u2022\u2023\u25e6\u2043\-*]|\(?\d+[.)]|[a-z][.)])\s+", re.IGNORECASE)
_PAGE_NUMBER = re.compile(r"^(?:seite\s+)?(?:\d+|[ivxlcdm]+)(?:\s*/\s*\d+)?$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class TextSpan:
    text: str
    x: float
    y: float
    font_size: float
    font_name: str


@dataclass(frozen=True, slots=True)
class TextLine:
    spans: tuple[TextSpan, ...]
    text: str
    x: float
    y: float
    font_size: float


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Draft rule-based MBI-Gold-Layout annotations; no model calls.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--validate-only", action="store_true", help="Load an existing output through load_gold_samples()."
    )
    return parser.parse_args()


def _clean_text(text: str) -> str:
    return " ".join(text.replace("\x00", "").split())


def _extract_spans(page: pypdf._page.PageObject) -> list[TextSpan]:
    spans: list[TextSpan] = []

    def visit_text(text: str, _cm: list[float], tm: list[float], font: dict[str, Any] | None, size: float) -> None:
        lines = [_clean_text(line) for line in text.splitlines() if _clean_text(line)]
        font_name = str((font or {}).get("/BaseFont", ""))
        for offset, line in enumerate(lines):
            spans.append(
                TextSpan(line, float(tm[4]), float(tm[5]) - offset * float(size) * 1.15, float(size), font_name)
            )

    page.extract_text(visitor_text=visit_text)
    return spans


def _lines(spans: list[TextSpan]) -> list[TextLine]:
    groups: list[list[TextSpan]] = []
    for span in sorted(spans, key=lambda item: (-item.y, item.x, item.text)):
        group = next((row for row in groups if abs(row[0].y - span.y) <= max(2.5, span.font_size * 0.25)), None)
        if group is None:
            groups.append([span])
        else:
            group.append(span)
    result: list[TextLine] = []
    for group in groups:
        ordered = tuple(sorted(group, key=lambda item: item.x))
        text = " ".join(item.text for item in ordered)
        result.append(
            TextLine(
                ordered,
                text,
                ordered[0].x,
                statistics.mean(item.y for item in ordered),
                max(item.font_size for item in ordered),
            )
        )
    return result


def _image_boxes(page: pypdf._page.PageObject) -> list[tuple[float, float, float, float]]:
    resources = page.get("/Resources") or {}
    resources = resources.get_object() if hasattr(resources, "get_object") else resources
    xobjects = resources.get("/XObject") or {}
    xobjects = xobjects.get_object() if hasattr(xobjects, "get_object") else xobjects
    boxes: list[tuple[float, float, float, float]] = []

    def operand_before(operator: bytes, operands: list[Any], cm: list[float], _tm: list[float]) -> None:
        if operator != b"Do" or not operands:
            return
        obj = xobjects.get(operands[0]) if hasattr(xobjects, "get") else None
        obj = obj.get_object() if hasattr(obj, "get_object") else obj
        if not obj or str(obj.get("/Subtype")) != "/Image":
            return
        a, b, c, d, e, f = (float(value) for value in cm)
        corners = [(e, f), (a + e, b + f), (c + e, d + f), (a + c + e, b + d + f)]
        xs = [point[0] for point in corners]
        ys = [point[1] for point in corners]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))

    page.extract_text(visitor_operand_before=operand_before)
    return boxes


def _is_multi_column(lines: list[TextLine], width: float) -> bool:
    body = [line for line in lines if len(line.text) >= 12]
    left = sum(line.x < width * 0.42 for line in body)
    right = sum(line.x > width * 0.50 for line in body)
    return left >= 3 and right >= 3


def _table_rows(lines: list[TextLine], width: float) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in lines:
        cells = [span.text for span in line.spans if span.text]
        if len(cells) >= 2 and (max(span.x for span in line.spans) - min(span.x for span in line.spans)) > width * 0.22:
            rows.append(cells)
    return rows if len(rows) >= 2 else []


def analyze_pdf_page(pdf_bytes: bytes, page_number: int) -> tuple[dict[str, Any], dict[str, bool]]:
    """Return (gold draft, layout signals) for one 1-based PDF page."""
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    if page_number < 1 or page_number > len(reader.pages):
        raise ValueError(f"page {page_number} outside PDF range 1..{len(reader.pages)}")
    page = reader.pages[page_number - 1]
    width, height = float(page.mediabox.width), float(page.mediabox.height)
    spans = _extract_spans(page)
    lines = _lines(spans)
    image_boxes = _image_boxes(page)
    extracted_text = " ".join(line.text for line in lines)
    scanned = len(extracted_text.strip()) < 20
    if scanned and not image_boxes and list(page.images):
        image_boxes = [(0.0, 0.0, width, height)]

    body_sizes = [line.font_size for line in lines if len(line.text) >= 8]
    median_size = statistics.median(body_sizes) if body_sizes else 10.0
    multi_column = _is_multi_column(lines, width)

    def column(line: TextLine) -> int:
        return int(multi_column and line.x >= width * 0.50)

    ordered_lines = sorted(lines, key=lambda line: (column(line), -line.y, line.x, line.text))
    blocks: list[dict[str, Any]] = []
    heading_count = 0
    paragraph_count = 0
    caption_lines: list[TextLine] = []
    for order, line in enumerate(ordered_lines):
        low = line.y <= height * 0.08
        high = line.y >= height * 0.92
        bold = "bold" in " ".join(span.font_name for span in line.spans).casefold()
        if low or high or _PAGE_NUMBER.fullmatch(line.text.strip()):
            kind = "header_footer"
        elif _CAPTION.match(line.text.strip()):
            kind = "caption"
            caption_lines.append(line)
        elif _LIST.match(line.text.strip()):
            kind = "list"
        elif line.font_size >= median_size * 1.22 or (bold and len(line.text) <= 100 and line.font_size >= median_size):
            kind = "heading"
            heading_count += 1
        else:
            kind = "paragraph"
            paragraph_count += 1
        blocks.append({"kind": kind, "reading_order": order, "text": line.text})

    table_rows = _table_rows(lines, width)
    tables = [table_rows] if table_rows else []
    if table_rows:
        blocks.append(
            {
                "kind": "table",
                "reading_order": len(blocks),
                "text": " | ".join(" | ".join(row) for row in table_rows),
            }
        )

    figures: list[dict[str, Any]] = []
    for box in image_boxes:
        nearby = sorted(caption_lines, key=lambda line: min(abs(line.y - box[1]), abs(line.y - box[3])))
        caption = (
            nearby[0].text
            if nearby and min(abs(nearby[0].y - box[1]), abs(nearby[0].y - box[3])) <= height * 0.12
            else None
        )
        area = max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])
        knowledge_bearing = caption is not None or area >= width * height * 0.05
        figures.append(
            {
                "bbox": [round(value, 3) for value in box],
                "caption": caption,
                "is_knowledge_bearing": knowledge_bearing,
            }
        )
        blocks.append({"kind": "figure", "reading_order": len(blocks), "text": caption or "[figure]"})

    vertical_sequence = [line.y for line in lines]
    unusual = multi_column or any(a + median_size * 0.5 < b for a, b in itertools.pairwise(vertical_sequence))
    has_header_footer = any(block["kind"] == "header_footer" for block in blocks)
    signals = {
        "multi_column": multi_column,
        "headings_paragraphs": heading_count > 0 and paragraph_count >= 2,
        "table_heavy": len(table_rows) >= 3,
        "figures_with_captions": any(figure["caption"] for figure in figures),
        "lists": any(block["kind"] == "list" for block in blocks),
        "headers_footers_page_numbers": has_header_footer,
        "unusual_reading_order": unusual,
        "scanned": scanned,
        "annotated": bool(page.get("/Annots")),
        "slide_like": width > height,
        "plain_text_control": paragraph_count >= 5 and not multi_column and not tables and not figures,
    }
    return {"blocks": blocks, "tables": tables, "figures": figures}, signals


def _load_yaml(path: Path) -> dict[str, Any]:
    result = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise TypeError(f"expected a YAML mapping in {path}")
    return result


def _dump_yaml(path: Path, doc: dict[str, Any]) -> None:
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.width = 120
    with path.open("w", encoding="utf-8") as stream:
        yaml.dump(doc, stream)


def main() -> int:
    args = _arguments()
    config = load_config(args.config)
    source_fs = SourceFS(config)
    if args.validate_only:
        samples = load_gold_samples(source_fs, args.output)
        print(json.dumps({"schema_load_ok": True, "loaded": len(samples), "path": str(args.output)}, indent=2))
        return 0

    sample_doc = _load_yaml(args.sample)
    drafted: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for index, entry in enumerate(sample_doc.get("sample", []), start=1):
        sample_id = f"layout-{index:03d}"
        try:
            pdf_bytes = source_fs.read_bytes(entry["root_id"], entry["relpath"])
            gold, observed_signals = analyze_pdf_page(pdf_bytes, int(entry["page"]))
            drafted.append(
                {
                    "sample_id": sample_id,
                    "blob_id": entry["blob_id"],
                    "bucket": entry["bucket"],
                    "signals": observed_signals,
                    "root_id": entry["root_id"],
                    "relpath": entry["relpath"],
                    "page": int(entry["page"]),
                    "gold": gold,
                }
            )
        except Exception as exc:  # one bad source page must not discard the other drafts
            failures.append({"sample_id": sample_id, "blob_id": entry.get("blob_id"), "error": type(exc).__name__})

    output_doc = {
        "purpose": "T-P3-03 heuristic candidate drafts; not owner-verified",
        "annotation_method": "deterministic pypdf font/position/image-XObject rules; no model calls",
        "owner_verified": False,
        "samples": drafted,
        "failures": failures,
    }
    assert_writable(args.output.resolve(), config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    _dump_yaml(args.output, output_doc)
    print(
        json.dumps(
            {"selected": len(sample_doc.get("sample", [])), "drafted": len(drafted), "failed": failures}, indent=2
        )
    )
    print(f"candidate annotations written to {args.output} (git-ignored, local only; owner verification required)")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
