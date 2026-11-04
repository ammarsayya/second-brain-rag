"""T-P3-01: build MBI-Gold-Extract, a stratified ~120-page sample from the real corpus.

Real-corpus orchestrator around the pure logic in :mod:`sbr.eval.gold_extract` and :mod:`sbr.eval.signals`.
Read-only throughout: every source file is opened once, through :class:`~sbr.sourcefs.SourceFS`, only to read
cheap per-blob metadata (a PDF's producer string and one representative page's text/annotations/media-box; an
Office document's inner XML for a native OMML equation) - never to render, OCR or otherwise process content.

Output (``eval/gold/extract_sample.yaml``, git-ignored per docs/33 §41 and docs/22 §4 - most sources are
copyrighted lecture/textbook material used privately, so even a reference list stays local, never pushed to
a public remote) lists every selected ``(blob_id, page, bucket)`` alongside its current canonical relpath, for
the owner's own review and for whichever spike (T-P3-05 onward) reads the sample next. The selection itself
never copies any document content - it is references only, exactly per docs/33 §41's own framing.

Reuses T-P2-12's already-computed unique-PDF page census (``audit/phase0/t3/pdf_unique_pages_t3.jsonl``)
rather than re-opening every PDF a second time just for a page count.
"""

from __future__ import annotations

import argparse
import io
import json
import zipfile
from pathlib import Path
from typing import Any

import pypdf
from ruamel.yaml import YAML

from sbr.config import load_config
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.eval.gold_extract import (
    DEFAULT_SEED,
    DEFAULT_TARGET_PAGES,
    BlobDescriptor,
    representative_page,
    select_sample,
)
from sbr.eval.signals import classify_producer, has_omml_equations, is_landscape_page, is_scanned_page
from sbr.safety import assert_writable
from sbr.sourcefs import SourceFS

DEFAULT_OUTPUT = Path("eval/gold/extract_sample.yaml")
DEFAULT_PAGE_CENSUS = Path("audit/phase0/t3/pdf_unique_pages_t3.jsonl")
_OFFICE_ZIP_FORMATS = {"docx", "pptx"}
_OFFICE_LEGACY_FORMATS = {"doc", "ppt", "ppsx"}
_KNOWLEDGE_DOCUMENT_FORMATS = {"pdf"} | _OFFICE_ZIP_FORMATS | _OFFICE_LEGACY_FORMATS


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="T-P3-01: build the MBI-Gold-Extract stratified sample.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--page-census", type=Path, default=DEFAULT_PAGE_CENSUS)
    parser.add_argument("--target-pages", type=int, default=DEFAULT_TARGET_PAGES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def _load_pdf_page_counts(path: Path) -> dict[str, int]:
    """blob_id -> page_count, from T-P2-12's already-computed census. Blobs the census errored on (mostly
    permanently password-encrypted PDFs) are simply absent - they cannot be probed further and are excluded."""
    counts: dict[str, int] = {}
    if not path.exists():
        return counts
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if "page_count" in row:
            counts[row["blob_id"]] = row["page_count"]
    return counts


def _probe_pdf(source_fs: SourceFS, root_id: str, relpath: str, page_count: int) -> tuple[str | None, bool, bool, bool]:
    """Producer string, scanned, annotated, landscape - for exactly the page :func:`representative_page` picks."""
    with source_fs.open_binary(root_id, relpath) as stream:
        reader = pypdf.PdfReader(stream)
        producer = reader.metadata.producer if reader.metadata is not None else None
        index = min(representative_page(page_count) - 1, len(reader.pages) - 1)
        page = reader.pages[index]
        text = page.extract_text() or ""
        annotated = bool(page.get("/Annots"))
        box = page.mediabox
        landscape = is_landscape_page(float(box.width), float(box.height))
    return producer, is_scanned_page(text), annotated, landscape


def _probe_office_zip(source_fs: SourceFS, root_id: str, relpath: str, fmt: str) -> tuple[int | None, bool]:
    """slide/page count (pptx only; None for docx - no cheap page concept without rendering) and OMML presence
    (checked across every XML part in the package, not just the obvious slide/document one - a formula can
    live in a header, footnote or embedded object part too)."""
    data = source_fs.read_bytes(root_id, relpath)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            has_omml = any(has_omml_equations(zf.read(name)) for name in names if name.endswith(".xml"))
            slide_count = sum(1 for n in names if n.startswith("ppt/slides/slide") and n.endswith(".xml"))
            return (slide_count if fmt == "pptx" and slide_count else None), has_omml
    except zipfile.BadZipFile:
        return None, False


def main() -> int:
    args = _arguments()
    config = load_config(args.config)
    source_fs = SourceFS(config)
    pdf_pages = _load_pdf_page_counts(args.page_census)

    with RegistryDB.open(config) as db:
        blobs = {b.blob_id: b for b in db.repo(reg.BLOB).find() if b.format in _KNOWLEDGE_DOCUMENT_FORMATS}
        observations = {o.obs_id: o for o in db.repo(reg.PATH_OBSERVATION).find()}
        classifications = {c.blob_id: c for c in db.repo(reg.BLOB_CLASSIFICATION).find()}

        descriptors: list[BlobDescriptor] = []
        canonical_relpath: dict[str, tuple[str, str]] = {}
        for blob in blobs.values():
            if blob.canonical_obs_id is None or blob.format is None:
                continue
            obs = observations.get(blob.canonical_obs_id)
            if obs is None:
                continue
            classification = classifications.get(blob.blob_id)
            genre = classification.genre if classification else None
            course_id = classification.course_id if classification else None

            if blob.format == "pdf":
                page_count = pdf_pages.get(blob.blob_id)
                if page_count is None:
                    continue  # census error (e.g. permanently encrypted) - cannot probe further
                producer, scanned, annotated, landscape = _probe_pdf(
                    source_fs, obs.root_id, obs.relpath_raw, page_count
                )
                descriptors.append(
                    BlobDescriptor(
                        blob_id=blob.blob_id,
                        format=blob.format,
                        page_count=page_count,
                        genre=genre,
                        course_id=course_id,
                        producer_class=classify_producer(producer),
                        scanned=scanned,
                        annotated=annotated,
                        landscape=landscape,
                        has_omml=False,
                    )
                )
            elif blob.format in _OFFICE_ZIP_FORMATS:
                page_count, has_omml = _probe_office_zip(source_fs, obs.root_id, obs.relpath_raw, blob.format)
                descriptors.append(
                    BlobDescriptor(
                        blob_id=blob.blob_id,
                        format=blob.format,
                        page_count=page_count,
                        genre=genre,
                        course_id=course_id,
                        producer_class=None,
                        scanned=False,
                        annotated=False,
                        landscape=blob.format == "pptx",
                        has_omml=has_omml,
                    )
                )
            else:  # legacy binary .doc/.ppt/.ppsx - OMML/OLE-equation detection is T-P3-07's own job, not here
                descriptors.append(
                    BlobDescriptor(
                        blob_id=blob.blob_id,
                        format=blob.format,
                        page_count=None,
                        genre=genre,
                        course_id=course_id,
                        producer_class=None,
                        scanned=False,
                        annotated=False,
                        landscape=False,
                        has_omml=False,
                    )
                )
            canonical_relpath[blob.blob_id] = (obs.root_id, obs.relpath)

    entries, coverage = select_sample(descriptors, target_pages=args.target_pages, seed=args.seed)

    output_doc: dict[str, Any] = {
        "seed": args.seed,
        "target_pages": args.target_pages,
        "descriptors_considered": len(descriptors),
        "selected": len(entries),
        "coverage": coverage,
        "sample": [
            {
                "blob_id": e.blob_id,
                "page": e.page,
                "bucket": e.bucket,
                "root_id": canonical_relpath[e.blob_id][0],
                "relpath": canonical_relpath[e.blob_id][1],
            }
            for e in entries
        ],
    }

    assert_writable(args.output.resolve(), config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    yaml = YAML(typ="safe")
    yaml.default_flow_style = False
    with args.output.open("w", encoding="utf-8") as f:
        yaml.dump(output_doc, f)

    summary = {"descriptors_considered": len(descriptors), "selected": len(entries), "coverage": coverage}
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"gold sample written to {args.output} (git-ignored, local only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
