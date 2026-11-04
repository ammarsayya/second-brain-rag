"""T-P3-07 SPIKE-OMML: real-corpus evidence for OMML->LaTeX conversion fidelity (ADR-009).

Finds every canonical DOCX/PPTX blob carrying at least one native OMML equation, converts each through
``pandoc -f docx|pptx -t latex`` (a real subprocess call - the primary candidate docs/36 already proposes for
this spike), extracts every equation pandoc's LaTeX writer emitted, and checks syntactic plausibility
(balanced braces, non-empty, no pandoc error marker).

**This script measures syntactic well-formedness, not correctness.** The acceptance criterion ("≥98% of
sampled OMML equations render correctly", docs/28 T-P3-07) needs a human to actually look at each equation
next to its source and judge whether it's right - that is the owner's manual review, not something this
script can substitute. What this script produces is the evidence for that review: a syntax-validity rate
across the whole corpus, and a reproducible 50-equation sample ready to review.

Also cross-references T-P2-09's twin_candidate relations: an OMML-bearing DOCX/PPTX with a PDF twin is where
"PDF<->DOCX equation alignment" (the task's other acceptance item) can eventually be tested once a math
recognizer exists to extract the PDF side (SPIKE-MATH, T-P3-06) - reported here as a candidate-pair list, not
an alignment score that doesn't have a PDF-side extraction to compare against yet.

Every source file is opened read-only via SourceFS, addressed by its exact on-disk ``relpath_raw`` (the NFC
``relpath`` is only a display/identity key); pandoc runs against a private temp copy, never a source-tree path.

``--pptx-inventory`` (added 2026-11-04) needs no pandoc. The first run found pandoc extracts **zero** equations from
PPTX files that do contain native OMML; this mode sizes that gap. It counts outermost native OMML equations in every
canonical DOCX/PPTX by XML part (slides, notes, layouts/masters, document body, other parts), display vs inline,
and writes its own report. Counts are structural facts about the files, not conversion results.
"""

from __future__ import annotations

import argparse
import io
import json
import random
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from sbr.config import load_config
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.eval.extract.omml import count_omml_equations, extract_latex_equations, is_syntactically_plausible_latex
from sbr.eval.signals import has_omml_equations
from sbr.eval.spike_gate import processable_blobs
from sbr.schemas.registry import RelationType
from sbr.sourcefs import SourceFS

DEFAULT_OUTPUT = Path("eval/reports/spike_omml.md")
DEFAULT_INVENTORY_OUTPUT = Path("eval/reports/spike_omml_inventory.md")
DEFAULT_REVIEW_SAMPLE_SIZE = 50
DEFAULT_SEED = 20_260_926
_OFFICE_ZIP_FORMATS = {"docx", "pptx"}


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="T-P3-07 SPIKE-OMML: OMML->LaTeX conversion evidence.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--pptx-inventory",
        action="store_true",
        help="count native OMML per DOCX/PPTX part without pandoc (sizes the PPTX gap pandoc leaves)",
    )
    parser.add_argument("--review-sample-size", type=int, default=DEFAULT_REVIEW_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def _has_omml(source_fs: SourceFS, root_id: str, relpath: str) -> bool:
    data = source_fs.read_bytes(root_id, relpath)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            return any(has_omml_equations(zf.read(n)) for n in zf.namelist() if n.endswith(".xml"))
    except zipfile.BadZipFile:
        return False


def _convert_via_pandoc(source_fs: SourceFS, root_id: str, relpath: str, fmt: str) -> tuple[str | None, str | None]:
    """Returns (latex_output, error). Writes to a private temp file - pandoc needs a real path for OOXML."""
    data = source_fs.read_bytes(root_id, relpath)
    with tempfile.TemporaryDirectory() as tmp:
        input_path = Path(tmp) / f"input.{fmt}"
        input_path.write_bytes(data)
        try:
            result = subprocess.run(
                ["pandoc", "-f", fmt, "-t", "latex", str(input_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return None, f"{type(exc).__name__}: {exc}"
        if result.returncode != 0:
            return None, result.stderr.strip()[:300]
        return result.stdout, None


def part_kind(name: str) -> str | None:
    """Coarse OOXML part class for an XML member name, or ``None`` for parts that never carry content math."""
    if not name.endswith(".xml"):
        return None
    if name.startswith("ppt/slides/slide"):
        return "pptx_slide"
    if name.startswith("ppt/notesSlides/"):
        return "pptx_notes"
    if name.startswith(("ppt/slideLayouts/", "ppt/slideMasters/", "ppt/notesMasters/")):
        return "pptx_layout_or_master"
    if name == "word/document.xml":
        return "docx_body"
    if name.startswith(("word/", "ppt/")):
        return "other_part"
    return None


def inventory_office_file(data: bytes) -> dict[str, Any]:
    """Per-part-kind OMML counts for one DOCX/PPTX. Unreadable archives and parts are counted, never guessed."""
    result: dict[str, Any] = {"parts": {}, "unreadable_parts": 0, "slides_with_omml": 0, "slides": 0}
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        result["error"] = "BadZipFile"
        return result
    with archive:
        for name in archive.namelist():
            kind = part_kind(name)
            if kind is None:
                continue
            count = count_omml_equations(archive.read(name))
            if kind == "pptx_slide":
                result["slides"] += 1
            if count is None:
                result["unreadable_parts"] += 1
                continue
            bucket = result["parts"].setdefault(kind, {"total": 0, "display": 0})
            bucket["total"] += count.total
            bucket["display"] += count.display
            if kind == "pptx_slide" and count.total:
                result["slides_with_omml"] += 1
    result["total"] = sum(b["total"] for b in result["parts"].values())
    return result


def _pptx_inventory(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    source_fs = SourceFS(config)
    output: Path = args.output or DEFAULT_INVENTORY_OUTPUT

    with RegistryDB.open(config) as db:
        observations = {o.obs_id: o for o in db.repo(reg.PATH_OBSERVATION).find()}
        blobs = processable_blobs(db, observations.values(), _OFFICE_ZIP_FORMATS)
        twin_relations = [r for r in db.repo(reg.BLOB_RELATION).find() if r.type is RelationType.TWIN_CANDIDATE]
    twins = {b for r in twin_relations for b in (r.src_blob, r.dst_blob)}

    rows: list[dict[str, Any]] = []
    read_errors = 0
    for blob in blobs.values():
        obs = observations.get(blob.canonical_obs_id) if blob.canonical_obs_id else None
        if obs is None or blob.format is None:
            continue
        try:
            data = source_fs.read_bytes(obs.root_id, obs.relpath_raw)
        except OSError:
            read_errors += 1
            continue
        inventory = inventory_office_file(data)
        inventory.update(fmt=blob.format, relpath=obs.relpath, has_pdf_twin=blob.blob_id in twins)
        rows.append(inventory)

    def _totals(fmt: str) -> dict[str, Any]:
        selected = [r for r in rows if r["fmt"] == fmt]
        with_math = [r for r in selected if r.get("total", 0) > 0]
        kinds: dict[str, dict[str, int]] = {}
        for r in with_math:
            for kind, bucket in r["parts"].items():
                k = kinds.setdefault(kind, {"total": 0, "display": 0})
                k["total"] += bucket["total"]
                k["display"] += bucket["display"]
        return {
            "files_scanned": len(selected),
            "files_with_omml": len(with_math),
            "equations": sum(r["total"] for r in with_math),
            "by_part": kinds,
            "slides_with_omml": sum(r["slides_with_omml"] for r in with_math),
            "files_with_pdf_twin": sum(1 for r in with_math if r["has_pdf_twin"]),
            "bad_zip": sum(1 for r in selected if "error" in r),
            "unreadable_parts": sum(r["unreadable_parts"] for r in selected),
        }

    totals = {fmt: _totals(fmt) for fmt in sorted(_OFFICE_ZIP_FORMATS)}
    lines = [
        "# SPIKE-OMML follow-up: native OMML inventory without pandoc (T-P3-07)",
        "",
        "Counts outermost native OMML equations (`m:oMath`, by namespace URI) in every canonical DOCX/PPTX, per "
        "XML part. `mc:Fallback` pictures are not counted, so each PPTX equation counts once. These are "
        "structural counts, not conversion results. They size what a PPTX conversion path would have to cover, "
        "since the pandoc run in `spike_omml.md` extracted zero equations from PPTX. Choosing that path "
        "(another converter, or routing PPTX math to the SPIKE-MATH recognizer) is an ADR-009 decision, not "
        "made here.",
        "",
        f"- files that could not be read from the source: {read_errors}",
    ]
    for fmt, t in totals.items():
        by_part = ", ".join(
            f"{kind}={b['total']} ({b['display']} display)" for kind, b in sorted(t["by_part"].items()) if b["total"]
        )
        lines += [
            "",
            f"## {fmt.upper()}",
            "",
            f"- canonical files scanned: {t['files_scanned']} (not a zip: {t['bad_zip']}, "
            f"unparseable XML parts: {t['unreadable_parts']})",
            f"- files with native OMML: {t['files_with_omml']}",
            f"- native OMML equations: {t['equations']}" + (f" - {by_part}" if by_part else ""),
            f"- files with native OMML and a PDF twin candidate (T-P2-09): {t['files_with_pdf_twin']}",
        ]
        if fmt == "pptx":
            lines.append(f"- slides carrying native OMML: {t['slides_with_omml']}")
    lines += [
        "",
        "## Per-file counts (files with native OMML)",
        "",
        "| format | relpath | equations | display | slides with OMML / slides | has PDF twin |",
        "|---|---|---|---|---|---|",
    ]
    for r in sorted((r for r in rows if r.get("total", 0) > 0), key=lambda r: (r["fmt"], -r["total"], r["relpath"])):
        display = sum(b["display"] for b in r["parts"].values())
        slides = f"{r['slides_with_omml']} / {r['slides']}" if r["fmt"] == "pptx" else "-"
        lines.append(f"| {r['fmt']} | {r['relpath']} | {r['total']} | {display} | {slides} | {r['has_pdf_twin']} |")
    lines.append("")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"read_errors": read_errors, **totals}, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"report written to {output}")
    return 0


def main() -> int:
    args = _arguments()
    if args.pptx_inventory:
        return _pptx_inventory(args)
    output: Path = args.output or DEFAULT_OUTPUT
    config = load_config(args.config)
    source_fs = SourceFS(config)

    with RegistryDB.open(config) as db:
        observations = {o.obs_id: o for o in db.repo(reg.PATH_OBSERVATION).find()}
        blobs = processable_blobs(db, observations.values(), _OFFICE_ZIP_FORMATS)
        twin_relations = [r for r in db.repo(reg.BLOB_RELATION).find() if r.type is RelationType.TWIN_CANDIDATE]

        candidates: list[tuple[str, str, str, str, str]] = []  # blob_id, fmt, root_id, relpath_raw, relpath
        for blob in blobs.values():
            if blob.canonical_obs_id is None or blob.format is None:
                continue
            obs = observations.get(blob.canonical_obs_id)
            if obs is None:
                continue
            if _has_omml(source_fs, obs.root_id, obs.relpath_raw):
                candidates.append((blob.blob_id, blob.format, obs.root_id, obs.relpath_raw, obs.relpath))

        twin_partners = {
            blob_id: partner
            for src, dst in ((r.src_blob, r.dst_blob) for r in twin_relations)
            for blob_id, partner in ((src, dst), (dst, src))
        }

        per_file: list[dict[str, Any]] = []
        all_equations: list[dict[str, Any]] = []
        for blob_id, fmt, root_id, relpath_raw, relpath in candidates:
            latex_output, error = _convert_via_pandoc(source_fs, root_id, relpath_raw, fmt)
            if error is not None:
                per_file.append({"blob_id": blob_id, "relpath": relpath, "error": error, "equations": 0})
                continue
            equations = extract_latex_equations(latex_output or "")
            valid = [eq for eq in equations if is_syntactically_plausible_latex(eq)]
            per_file.append(
                {
                    "blob_id": blob_id,
                    "relpath": relpath,
                    "equations": len(equations),
                    "syntactically_valid": len(valid),
                    "has_pdf_twin": blob_id in twin_partners,
                }
            )
            for eq in equations:
                all_equations.append(
                    {
                        "blob_id": blob_id,
                        "relpath": relpath,
                        "latex": eq,
                        "syntactically_valid": is_syntactically_plausible_latex(eq),
                    }
                )

    total_equations = len(all_equations)
    valid_equations = sum(1 for e in all_equations if e["syntactically_valid"])
    syntax_valid_rate = (valid_equations / total_equations) if total_equations else None
    files_with_errors = sum(1 for f in per_file if "error" in f)
    files_with_twin = sum(1 for f in per_file if f.get("has_pdf_twin"))

    rng = random.Random(args.seed)
    review_sample = rng.sample(all_equations, min(args.review_sample_size, len(all_equations)))

    lines: list[str] = [
        "# SPIKE-OMML: OMML -> LaTeX Conversion Evidence (T-P3-07)",
        "",
        "Tool: pandoc (the primary candidate docs/36 proposes for this spike).",
        "",
        f"- OMML-bearing DOCX/PPTX files found: {len(candidates)}",
        f"- files pandoc failed to convert: {files_with_errors}",
        f"- total equations extracted: {total_equations}",
        f"- syntactically valid (balanced braces, non-empty, no pandoc error marker): {valid_equations}"
        f" ({syntax_valid_rate:.1%} of extracted)"
        if syntax_valid_rate is not None
        else "",
        f"- files with a PDF twin candidate (T-P2-09) for future PDF<->DOCX alignment: {files_with_twin}",
        "",
        "**This is syntactic well-formedness, not correctness.** The task's acceptance criterion needs a "
        "human to compare each equation against its source - that is the owner's review of the 50-sample "
        "table below, not something measured here.",
        "",
        "## Per-file results",
        "",
        "| relpath | equations | syntactically valid | has PDF twin | error |",
        "|---|---|---|---|---|",
    ]
    for f in per_file:
        lines.append(
            f"| {f['relpath']} | {f.get('equations', 0)} | {f.get('syntactically_valid', '-')} | "
            f"{f.get('has_pdf_twin', '-')} | {f.get('error', '')} |"
        )
    lines += [
        "",
        "## 50-equation sample for owner manual review",
        "",
        "| relpath | LaTeX | syntactically valid |",
        "|---|---|---|",
    ]
    for item in review_sample:
        latex_escaped = item["latex"].replace("|", "\\|")
        lines.append(f"| {item['relpath']} | `{latex_escaped}` | {item['syntactically_valid']} |")
    lines.append("")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "candidates": len(candidates),
        "files_with_errors": files_with_errors,
        "total_equations": total_equations,
        "syntactically_valid": valid_equations,
        "syntax_valid_rate": syntax_valid_rate,
        "files_with_pdf_twin": files_with_twin,
        "review_sample_size": len(review_sample),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"report written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
