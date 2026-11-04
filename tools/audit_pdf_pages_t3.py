"""T-P2-12 corpus audit refresh: a real, exhaustive (not sampled) unique-PDF page census.

docs/03 §5.2's t0 page census opened every unique PDF blob once (5 probe pages each, xxh3-based dedup) to get
"328,409 total unique pages". This is that same measurement redone against the production registry's t3
baseline: every blob with ``format == "pdf"`` (dedup, T-P2-06, already established unique content identity),
opened exactly once through :class:`~sbr.sourcefs.SourceFS` (read-only, never any other path) at its current
canonical observation, with ``pypdf`` reading only the page count from the xref/trailer - no page content is
decoded or rendered, so this is fast even over several thousand PDFs.

Writes a raw per-blob JSONL (blob_id, relpath, page_count or error) plus a summary JSON to
``audit/phase0/t3/``, alongside this baseline's other t3 evidence (``inventory_t3.csv``,
``stats_t3.json``, ...) - append-only new evidence, never touching what is already there.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pypdf

from sbr.config import load_config
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.sourcefs import SourceFS

DEFAULT_JSONL = Path("audit/phase0/t3/pdf_unique_pages_t3.jsonl")
DEFAULT_SUMMARY = Path("audit/phase0/t3/pdf_page_census_t3_summary.json")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="T-P2-12: exhaustive unique-PDF page census against the registry.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--jsonl-output", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY)
    return parser.parse_args()


def _percentile(sorted_values: list[int], pct: float) -> int:
    if not sorted_values:
        return 0
    index = min(len(sorted_values) - 1, round(pct * (len(sorted_values) - 1)))
    return sorted_values[index]


def main() -> int:
    args = _arguments()
    config = load_config(args.config)
    source_fs = SourceFS(config)

    rows: list[dict[str, Any]] = []
    with RegistryDB.open(config) as db:
        pdf_blobs = [b for b in db.repo(reg.BLOB).find() if b.format == "pdf"]
        observations_by_id = {o.obs_id: o for o in db.repo(reg.PATH_OBSERVATION).find()}

        for blob in pdf_blobs:
            obs = observations_by_id.get(blob.canonical_obs_id) if blob.canonical_obs_id else None
            if obs is None:
                rows.append({"blob_id": blob.blob_id, "relpath": None, "error": "no canonical observation"})
                continue
            try:
                with source_fs.open_binary(obs.root_id, obs.relpath_raw) as stream:
                    reader = pypdf.PdfReader(stream)
                    page_count = len(reader.pages)
                rows.append({"blob_id": blob.blob_id, "relpath": obs.relpath, "page_count": page_count})
            except Exception as exc:  # a probe must never abort on one bad PDF
                rows.append({"blob_id": blob.blob_id, "relpath": obs.relpath, "error": f"{type(exc).__name__}: {exc}"})

    args.jsonl_output.parent.mkdir(parents=True, exist_ok=True)
    with args.jsonl_output.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    opened = [r for r in rows if "page_count" in r]
    errored = [r for r in rows if "error" in r]
    page_counts = sorted(r["page_count"] for r in opened)
    total_pages = sum(page_counts)
    long_docs = [c for c in page_counts if c >= 200]
    short_docs = [c for c in page_counts if c <= 40]

    summary = {
        "unique_pdf_blobs": len(pdf_blobs),
        "opened": len(opened),
        "errored": len(errored),
        "total_unique_pages": total_pages,
        "page_count_percentiles": {
            f"p{int(p * 100)}": _percentile(page_counts, p) for p in (0.10, 0.25, 0.50, 0.75, 0.90, 0.99)
        },
        "max_page_count": page_counts[-1] if page_counts else 0,
        "documents_ge_200_pages": {"count": len(long_docs), "pages": sum(long_docs)},
        "documents_le_40_pages": {"count": len(short_docs), "pages": sum(short_docs)},
        "errors_sample": [r["error"] for r in errored[:10]],
    }
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
