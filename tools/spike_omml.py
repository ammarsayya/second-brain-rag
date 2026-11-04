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
import posixpath
import random
import subprocess
import tempfile
import zipfile
from collections import Counter
from pathlib import Path, PureWindowsPath
from typing import Any
from xml.etree import ElementTree

from ruamel.yaml import YAML

from sbr.config import load_config
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.eval.extract.omml import count_omml_equations, extract_latex_equations, is_syntactically_plausible_latex
from sbr.eval.extract.omml_latex import latex_compare_key, latex_text_signature, omml_xml_to_latex
from sbr.eval.signals import has_omml_equations
from sbr.eval.spike_gate import processable_blobs
from sbr.schemas.registry import RelationType
from sbr.sourcefs import SourceFS

DEFAULT_OUTPUT = Path("eval/reports/spike_omml.md")
DEFAULT_INVENTORY_OUTPUT = Path("eval/reports/spike_omml_inventory.md")
DEFAULT_NATIVE_OUTPUT = Path("eval/reports/spike_omml_native.md")
DEFAULT_GOLD_MATH = Path("eval/gold/math_sample.yaml")
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
    parser.add_argument(
        "--native-latex",
        action="store_true",
        help="convert every native OMML equation with the stdlib prototype (no pandoc) and score it",
    )
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD_MATH, help="T-P3-02 math sample for comparison")
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


_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_PML_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"


def _parse_xml(data: bytes) -> ElementTree.Element | None:
    try:
        return ElementTree.fromstring(data)  # same expat protections as count_omml_equations
    except ElementTree.ParseError:
        return None


def _rels(archive: zipfile.ZipFile, rels_name: str) -> dict[str, tuple[str, str]]:
    """``rId -> (type, target part name)`` for one ``_rels/*.rels`` member; empty when absent or unreadable."""
    if rels_name not in archive.namelist():
        return {}
    root = _parse_xml(archive.read(rels_name))
    if root is None:
        return {}
    base = posixpath.dirname(posixpath.dirname(rels_name))  # ppt/_rels/presentation.xml.rels -> ppt
    out: dict[str, tuple[str, str]] = {}
    for rel in root.iter(f"{{{_PKG_REL_NS}}}Relationship"):
        target = rel.get("Target", "")
        name = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(base, target))
        out[rel.get("Id", "")] = (rel.get("Type", ""), name)
    return out


def pptx_slide_order(archive: zipfile.ZipFile) -> dict[str, int]:
    """Slide part name -> 1-based position in the deck, from ``presentation.xml``'s ``sldIdLst`` (the file
    number in ``slideN.xml`` is not the presentation order once slides have been moved)."""
    if "ppt/presentation.xml" not in archive.namelist():
        return {}
    root = _parse_xml(archive.read("ppt/presentation.xml"))
    if root is None:
        return {}
    rels = _rels(archive, "ppt/_rels/presentation.xml.rels")
    order: dict[str, int] = {}
    for position, slide_id in enumerate(root.iter(f"{{{_PML_NS}}}sldId"), start=1):
        target = rels.get(slide_id.get(f"{{{_REL_NS}}}id", ""))
        if target is not None:
            order[target[1]] = position
    return order


_SLIDE_SCAFFOLDING = ("/slideLayout", "/slideMaster", "/notesMaster", "/theme", "/image", "/media", "/tags")


def pptx_part_owner(archive: zipfile.ZipFile) -> dict[str, str]:
    """Part name -> the slide part that references it (notes, SmartArt diagram data/drawings, charts), from each
    slide's relationships. Layouts, masters, themes and media are shared scaffolding, not slide content."""
    owners: dict[str, str] = {}
    for name in archive.namelist():
        if name.startswith("ppt/slides/slide") and name.endswith(".xml"):
            rels_name = posixpath.join("ppt/slides/_rels", posixpath.basename(name) + ".rels")
            for rel_type, target in _rels(archive, rels_name).values():
                if not rel_type.endswith(_SLIDE_SCAFFOLDING):
                    owners.setdefault(target, name)
    return owners


def convert_office_file(data: bytes) -> dict[str, Any]:
    """Every native OMML equation of one DOCX/PPTX converted by the stdlib prototype, with its location.

    Each equation records its part kind and, for PPTX, the deck position of its slide (notes are attributed to
    the slide they annotate). ``count_mismatch`` reports parts where converting and counting disagree.
    """
    result: dict[str, Any] = {"equations": [], "unreadable_parts": 0, "count_mismatch": 0}
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        result["error"] = "BadZipFile"
        return result
    with archive:
        order = pptx_slide_order(archive)
        part_owner = pptx_part_owner(archive)
        for name in archive.namelist():
            kind = part_kind(name)
            if kind is None:
                continue
            xml = archive.read(name)
            converted = omml_xml_to_latex(xml)
            counted = count_omml_equations(xml)
            if converted is None or counted is None:
                result["unreadable_parts"] += 1
                continue
            if len(converted) != counted.total:
                result["count_mismatch"] += 1
            slide_part = part_owner.get(name, name)
            for ordinal, equation in enumerate(converted, start=1):
                result["equations"].append(
                    {
                        "part": name,
                        "kind": kind,
                        "slide": order.get(slide_part),
                        "ordinal": ordinal,
                        "latex": equation.latex,
                        "unsupported": list(equation.unsupported),
                        "valid": is_syntactically_plausible_latex(equation.latex),
                    }
                )
    return result


def compare_with_gold(gold_path: Path) -> dict[str, Any] | None:
    """Score the prototype on the T-P3-02 OMML gold candidates: each sample's exact OMML crop is converted and
    compared with the pandoc LaTeX the selector paired with it by ordinal. ``None`` if the local gold is absent."""
    if not gold_path.is_file():
        return None
    data = YAML(typ="safe").load(gold_path.read_text(encoding="utf-8"))
    base = gold_path.parent.parent.parent  # eval/gold/math_sample.yaml -> repository root (crop paths are relative)
    result: dict[str, Any] = {"compared": 0, "equal": 0, "differs": [], "mispaired": [], "missing_crop": 0}
    for sample in data.get("samples", []):
        if sample.get("source_kind") != "omml_exact":
            continue
        crop = base / PureWindowsPath(sample["crop"]["path"]).as_posix()
        if not crop.is_file():
            result["missing_crop"] += 1
            continue
        converted = omml_xml_to_latex(crop.read_bytes())
        native = converted[0].latex if converted else ""
        pandoc = sample.get("latex") or ""
        result["compared"] += 1
        if latex_text_signature(native) != latex_text_signature(pandoc):
            result["mispaired"].append({"sample_id": sample["sample_id"], "relpath": sample["relpath"]})
        elif latex_compare_key(native) == latex_compare_key(pandoc):
            result["equal"] += 1
        else:
            result["differs"].append({"sample_id": sample["sample_id"], "pandoc": pandoc, "native": native})
    return result


def _native_latex(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    source_fs = SourceFS(config)
    output: Path = args.output or DEFAULT_NATIVE_OUTPUT
    with RegistryDB.open(config) as db:
        observations = {o.obs_id: o for o in db.repo(reg.PATH_OBSERVATION).find()}
        blobs = processable_blobs(db, observations.values(), _OFFICE_ZIP_FORMATS)

    files: list[dict[str, Any]] = []
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
        converted = convert_office_file(data)
        if converted["equations"] or converted.get("error"):
            files.append({"fmt": blob.format, "relpath": obs.relpath, **converted})

    def _fmt_totals(fmt: str) -> dict[str, Any]:
        equations = [e for f in files if f["fmt"] == fmt for e in f["equations"]]
        unsupported = Counter(tag for e in equations for tag in e["unsupported"])
        return {
            "files": sum(1 for f in files if f["fmt"] == fmt and f["equations"]),
            "equations": len(equations),
            "valid": sum(1 for e in equations if e["valid"]),
            "empty": sum(1 for e in equations if not e["latex"].strip()),
            "exact": sum(1 for e in equations if not e["unsupported"]),
            "unsupported": unsupported,
            "by_kind": Counter(e["kind"] for e in equations),
            "count_mismatch": sum(f["count_mismatch"] for f in files if f["fmt"] == fmt),
            "unreadable_parts": sum(f["unreadable_parts"] for f in files if f["fmt"] == fmt),
        }

    totals = {fmt: _fmt_totals(fmt) for fmt in ("docx", "pptx")}
    pptx_equations = [
        {"relpath": f["relpath"], **e}
        for f in sorted(files, key=lambda f: f["relpath"])
        if f["fmt"] == "pptx"
        for e in f["equations"]
    ]
    rng = random.Random(args.seed)
    sample = sorted(
        rng.sample(pptx_equations, min(args.review_sample_size, len(pptx_equations))),
        key=lambda e: (e["relpath"], e["slide"] or 0, e["part"], e["ordinal"]),
    )
    gold = compare_with_gold(args.gold)

    def _pct(part: int, whole: int) -> str:
        return f"{100 * part / whole:.1f}%" if whole else "n/a"

    lines = [
        "# SPIKE-OMML follow-up: native OMML -> LaTeX prototype (T-P3-07)",
        "",
        "`sbr.eval.extract.omml_latex` converts OMML with the Python standard library, so DOCX and PPTX math share "
        "one path and pandoc is not needed. Every equation `count_omml_equations` counts is converted; PPTX slide "
        "positions come from `presentation.xml` (deck order), and notes are attributed to the slide they annotate.",
        "",
        "**Evidence, not a decision.** *Valid* is syntactic plausibility (balanced braces, non-empty), not "
        "correctness. *Exact* means no OMML element fell back to plain text. Choosing the ADR-009 Office-math path "
        "and accepting any converter needs the owner's review of the sample below. Blobs the sensitivity gate "
        "rejects are not opened.",
        "",
        f"- files that could not be read from the source: {read_errors}",
    ]
    for fmt, t in totals.items():
        unsupported = ", ".join(f"{tag} {n}" for tag, n in t["unsupported"].most_common()) or "none"
        kinds = ", ".join(f"{kind} {n}" for kind, n in sorted(t["by_kind"].items()))
        lines += [
            "",
            f"## {fmt.upper()}",
            "",
            f"- files with native OMML: {t['files']}; equations converted: {t['equations']} ({kinds})",
            f"- syntactically valid: {t['valid']} ({_pct(t['valid'], t['equations'])}); exact (no fallback): "
            f"{t['exact']} ({_pct(t['exact'], t['equations'])}); empty `m:oMath` placeholders (count as not valid): "
            f"{t['empty']}",
            f"- elements that fell back to plain text: {unsupported}",
            f"- parts where converted and counted equations differ: {t['count_mismatch']}; unreadable parts: "
            f"{t['unreadable_parts']}",
        ]
    if gold is None:
        lines += ["", "## Comparison with pandoc on the T-P3-02 gold candidates", "", "- local gold set not found"]
    else:
        aligned = gold["compared"] - len(gold["mispaired"])
        lines += [
            "",
            "## Comparison with pandoc on the T-P3-02 OMML gold candidates",
            "",
            "Each candidate's exact OMML crop is converted and compared with the pandoc LaTeX the T-P3-02 selector "
            "paired with it **by ordinal**. A different letter/digit content means the pair is not the same "
            "equation (*mis-paired*); otherwise the two are compared after folding notation (`latex_compare_key`).",
            "",
            f"- candidates compared: {gold['compared']} (crops missing: {gold['missing_crop']})",
            f"- **mis-paired** (pandoc LaTeX belongs to another equation): {len(gold['mispaired'])} "
            f"({_pct(len(gold['mispaired']), gold['compared'])})",
            f"- correctly paired and equal after notation folding: {gold['equal']}/{aligned} "
            f"({_pct(gold['equal'], aligned)})",
            f"- correctly paired but different: {len(gold['differs'])}",
            "",
            "Mis-paired sample ids by file: "
            + "; ".join(
                f"{PureWindowsPath(relpath).name}: {', '.join(ids)}"
                for relpath, ids in sorted(_group_ids(gold["mispaired"]).items())
            ),
            "",
        ]
    if gold is not None and gold["differs"]:
        lines += [
            "",
            "| sample | pandoc | native |",
            "|---|---|---|",
            *(f"| {d['sample_id']} | `{_cell(d['pandoc'])}` | `{_cell(d['native'])}` |" for d in gold["differs"]),
        ]
    lines += [
        "",
        f"## PPTX review sample ({len(sample)} of {len(pptx_equations)}, seed {args.seed})",
        "",
        "| relpath | slide | part | # | LaTeX | exact |",
        "|---|---|---|---|---|---|",
        *(
            f"| {e['relpath']} | {e['slide'] or '-'} | {posixpath.basename(e['part'])} | {e['ordinal']} | "
            f"`{_cell(e['latex'])}` | {not e['unsupported']} |"
            for e in sample
        ),
        "",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    summary = {fmt: {k: v for k, v in t.items() if not isinstance(v, Counter)} for fmt, t in totals.items()}
    if gold is not None:
        summary["gold"] = {"compared": gold["compared"], "equal": gold["equal"], "mispaired": len(gold["mispaired"])}
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"report written to {output}")
    return 0


def _group_ids(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for row in rows:
        grouped.setdefault(row["relpath"], []).append(row["sample_id"])
    return grouped


def _cell(latex: str) -> str:
    return latex.replace("|", "\\vert ").replace("`", "'")


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
    if args.native_latex:
        return _native_latex(args)
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
