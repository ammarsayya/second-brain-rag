"""T-P3-08 SPIKE-OCR: real-corpus evidence for OCR engine choice on scanned German pages (ADR-010).

Scope of this pass (see eval/reports/spike_ocr.md for the full reasoning): **Tesseract 5 + deu only**.
PaddleOCR PP-OCRv5 needs a large ML-framework install (paddlepaddle) this pass did not stand up, and a
remote VLM is a cloud-API policy decision still pending the owner (Q-B03) - both are recorded as
not-yet-benchmarked, not silently skipped. Handwriting-presence detection also has no dedicated tool/model
lined up yet and is explicitly deferred, rather than faked from a proxy signal that doesn't actually measure
it (e.g. low OCR confidence conflates "handwritten" with "just a bad scan").

**CER cannot be computed here**: it needs a gold transcription of each sampled page, which is MBI-Gold-
Layout's own job (T-P3-03) and requires owner-approved labeling this session correctly did not start. What
this script measures instead - real, honest evidence - is speed and Tesseract's own reported word confidence
across a real sample of this corpus's "scanned" pages (detected the same way T-P3-01's gold-set stratifier
does: a representative page with no usable text layer).

Every source file is opened once, read-only, via SourceFS. Tesseract runs against a private temp image file,
never a source-tree path.
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import pypdf

from sbr.config import load_config
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.eval.extract.ocr import mean_word_confidence, parse_tesseract_tsv
from sbr.eval.gold_extract import representative_page
from sbr.eval.signals import is_scanned_page
from sbr.sourcefs import SourceFS

DEFAULT_OUTPUT = Path("eval/reports/spike_ocr.md")
DEFAULT_PAGE_CENSUS = Path("audit/phase0/t3/pdf_unique_pages_t3.jsonl")
DEFAULT_SAMPLE_SIZE = 25
DEFAULT_SEED = 20_260_926


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="T-P3-08 SPIKE-OCR: Tesseract deu evidence on scanned pages.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--page-census", type=Path, default=DEFAULT_PAGE_CENSUS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def _load_pdf_page_counts(path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not path.exists():
        return counts
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if "page_count" in row:
            counts[row["blob_id"]] = row["page_count"]
    return counts


def _run_tesseract(image_bytes: bytes) -> tuple[str, str, str | None]:
    """Returns (plain_text, tsv_output, error)."""
    with tempfile.TemporaryDirectory() as tmp:
        image_path = Path(tmp) / "page.png"
        image_path.write_bytes(image_bytes)
        try:
            text_result = subprocess.run(
                ["tesseract", str(image_path), "stdout", "-l", "deu"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
                check=False,
            )
            tsv_result = subprocess.run(
                ["tesseract", str(image_path), "stdout", "-l", "deu", "tsv"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return "", "", f"{type(exc).__name__}: {exc}"
        if text_result.returncode != 0:
            return "", "", text_result.stderr.strip()[:300]
        return text_result.stdout, tsv_result.stdout, None


def main() -> int:
    args = _arguments()
    config = load_config(args.config)
    source_fs = SourceFS(config)
    pdf_pages = _load_pdf_page_counts(args.page_census)

    with RegistryDB.open(config) as db:
        blobs = {b.blob_id: b for b in db.repo(reg.BLOB).find() if b.format == "pdf"}
        observations = {o.obs_id: o for o in db.repo(reg.PATH_OBSERVATION).find()}

        scanned_candidates: list[tuple[str, str, str, int]] = []  # blob_id, root_id, relpath, page
        for blob in blobs.values():
            if blob.canonical_obs_id is None:
                continue
            page_count = pdf_pages.get(blob.blob_id)
            if page_count is None:
                continue
            obs = observations.get(blob.canonical_obs_id)
            if obs is None:
                continue
            page = representative_page(page_count)
            try:
                with source_fs.open_binary(obs.root_id, obs.relpath_raw) as stream:
                    reader = pypdf.PdfReader(stream)
                    index = min(page - 1, len(reader.pages) - 1)
                    text = reader.pages[index].extract_text() or ""
            except Exception:  # a single unreadable PDF must not abort candidate discovery
                continue
            if is_scanned_page(text):
                scanned_candidates.append((blob.blob_id, obs.root_id, obs.relpath, page))

    rng = random.Random(args.seed)
    sample = rng.sample(scanned_candidates, min(args.sample_size, len(scanned_candidates)))

    results: list[dict[str, Any]] = []
    for blob_id, root_id, relpath, page in sample:
        with source_fs.open_binary(root_id, relpath) as stream:
            reader = pypdf.PdfReader(stream)
            index = min(page - 1, len(reader.pages) - 1)
            pdf_page = reader.pages[index]
            embedded_images = list(pdf_page.images)
        if not embedded_images:
            results.append({"blob_id": blob_id, "relpath": relpath, "page": page, "error": "no embedded image found"})
            continue

        start = time.perf_counter()
        text, tsv, error = _run_tesseract(embedded_images[0].data)
        elapsed = time.perf_counter() - start
        if error is not None:
            results.append({"blob_id": blob_id, "relpath": relpath, "page": page, "error": error})
            continue
        words = parse_tesseract_tsv(tsv)
        results.append(
            {
                "blob_id": blob_id,
                "relpath": relpath,
                "page": page,
                "elapsed_seconds": round(elapsed, 3),
                "word_count": len(words),
                "mean_confidence": mean_word_confidence(words),
                "text_sample": text.strip().replace("\n", " ")[:200],
            }
        )

    ok_results = [r for r in results if "error" not in r]
    elapsed_values = [r["elapsed_seconds"] for r in ok_results]
    confidence_values = [r["mean_confidence"] for r in ok_results if r["mean_confidence"] is not None]

    lines = [
        "# SPIKE-OCR: Tesseract 5 (deu) Evidence on Scanned Pages (T-P3-08)",
        "",
        "Scope: Tesseract 5 + deu only this pass. PaddleOCR PP-OCRv5 (large ML-framework install, not stood "
        "up this pass) and remote VLM (cloud-API policy, Q-B03 pending) are recorded as not-yet-benchmarked, "
        "not silently skipped. Handwriting-presence detection has no dedicated tool/model lined up and is "
        "explicitly deferred rather than approximated from a signal (e.g. low confidence) that doesn't "
        "actually measure it.",
        "",
        "**CER is not computed here** - it needs a gold transcription of each page (MBI-Gold-Layout, "
        "T-P3-03), which requires owner-approved labeling this session correctly did not start. What follows "
        "is real speed and Tesseract's own reported word-confidence evidence instead.",
        "",
        f"- scanned-page candidates found in the corpus: {len(scanned_candidates)}",
        f"- sampled for this run (seeded): {len(sample)}",
        f"- pages with no embedded image to OCR: "
        f"{sum(1 for r in results if r.get('error') == 'no embedded image found')}",
        f"- pages OCR'd successfully: {len(ok_results)}",
        f"- mean time per page: {sum(elapsed_values) / len(elapsed_values):.2f}s" if elapsed_values else "",
        f"- mean word confidence (Tesseract's own 0-100 scale): {sum(confidence_values) / len(confidence_values):.1f}"
        if confidence_values
        else "",
        "",
        "## Per-page results",
        "",
        "| relpath | page | elapsed (s) | words recognized | mean confidence | text sample | error |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['relpath']} | {r['page']} | {r.get('elapsed_seconds', '-')} | {r.get('word_count', '-')} | "
            f"{r.get('mean_confidence', '-')} | {r.get('text_sample', '')} | {r.get('error', '')} |"
        )
    lines.append("")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "scanned_candidates": len(scanned_candidates),
        "sampled": len(sample),
        "ocred_successfully": len(ok_results),
        "mean_elapsed_seconds": (sum(elapsed_values) / len(elapsed_values)) if elapsed_values else None,
        "mean_confidence": (sum(confidence_values) / len(confidence_values)) if confidence_values else None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"report written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
