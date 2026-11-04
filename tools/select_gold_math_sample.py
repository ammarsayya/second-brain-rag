"""Build the local MBI-Gold-Math candidate set without models or a corpus rescan (T-P3-02 prep).

Registry rows provide current canonical locations and privacy/status gates.  DOCX files with native OMML are
converted once through pandoc, then :func:`extract_latex_equations` supplies exact-source candidate LaTeX.
PDF-native candidates are bounded to pages already chosen by T-P3-01; their crops are selected with transparent
text-position/symbol heuristics, but LaTeX remains explicitly null and ``pending_ai_draft``.

All source reads use SourceFS.  Local crops and derived text live only below git-ignored ``eval/gold/``.
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import re
import subprocess
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import pypdf
from pypdf.generic import RectangleObject
from ruamel.yaml import YAML

from sbr.config import load_config
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.eval.extract.omml import extract_latex_equations, is_syntactically_plausible_latex
from sbr.eval.gold_math import (
    DEFAULT_SEED,
    DEFAULT_TARGET_EQUATIONS,
    MathCandidate,
    difficulty_tag,
    select_math_sample,
)
from sbr.eval.signals import has_omml_equations
from sbr.safety import assert_writable
from sbr.schemas.registry import BlobStatus, Sensitivity
from sbr.sourcefs import SourceFS

DEFAULT_EXTRACT_SAMPLE = Path("eval/gold/extract_sample.yaml")
DEFAULT_OUTPUT = Path("eval/gold/math_sample.yaml")
DEFAULT_CROP_DIR = Path("eval/gold/math/crops")
_BLOCKED_SENSITIVITY = {Sensitivity.RESTRICTED, Sensitivity.THIRD_PARTY_PERSONAL}
_MATH_NAMESPACE = "http://schemas.openxmlformats.org/officeDocument/2006/math"
_OMATH = f"{{{_MATH_NAMESPACE}}}oMath"
_OMATH_PARA = f"{{{_MATH_NAMESPACE}}}oMathPara"
_DISPLAY_MATH = re.compile(r"\\\[(.+?)\\\]", re.DOTALL)
_MATH_CHARS = frozenset("=+-−±×÷*/<>≤≥≈≠∫∑∏√∞∆∂^_()[]{}|%")
_ADVANCED_MATH = frozenset("∫∑∏√∞∆∂")
_PRIVATE_TEMP = Path("var/tmp/gold_math")


@dataclass(frozen=True, slots=True)
class PdfCandidateData:
    candidate: MathCandidate
    root_id: str
    relpath: str
    page: int
    bbox: tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class OmmlCandidateData:
    candidate: MathCandidate
    root_id: str
    relpath: str
    equation_ordinal: int
    latex: str
    xml: str
    display: bool


@dataclass(frozen=True, slots=True)
class _TextFragment:
    text: str
    x: float
    y: float
    size: float


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select and prepare local MBI-Gold-Math candidates.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--extract-sample", type=Path, default=DEFAULT_EXTRACT_SAMPLE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--crop-dir", type=Path, default=DEFAULT_CROP_DIR)
    parser.add_argument("--target-equations", type=int, default=DEFAULT_TARGET_EQUATIONS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def _load_yaml(path: Path) -> dict[str, Any]:
    doc = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise TypeError(f"expected a YAML mapping in {path}")
    return doc


def _pandoc_latex(data: bytes) -> tuple[str | None, str | None]:
    _PRIVATE_TEMP.mkdir(parents=True, exist_ok=True)
    path = _PRIVATE_TEMP / f"{uuid.uuid4().hex}.docx"
    try:
        path.write_bytes(data)
        try:
            result = subprocess.run(
                ["pandoc", "-f", "docx", "-t", "latex", str(path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return None, f"{type(exc).__name__}: {exc}"
    finally:
        path.unlink(missing_ok=True)
    if result.returncode != 0:
        return None, result.stderr.strip()[:300]
    return result.stdout, None


def _ordered_omml_xml(docx_bytes: bytes) -> list[tuple[str, bool]]:
    """Return main-document oMath subtrees in pandoc's display-first, then inline extraction order."""
    try:
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as archive:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
    except (KeyError, ElementTree.ParseError, zipfile.BadZipFile):
        return []
    found: list[tuple[str, bool]] = []

    def walk(node: ElementTree.Element, in_display: bool = False) -> None:
        display = in_display or node.tag == _OMATH_PARA
        if node.tag == _OMATH:
            found.append((ElementTree.tostring(node, encoding="unicode"), display))
            return
        for child in node:
            walk(child, display)

    walk(root)
    return [item for item in found if item[1]] + [item for item in found if not item[1]]


def _has_native_omml(data: bytes) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return any(has_omml_equations(archive.read(name)) for name in archive.namelist() if name.endswith(".xml"))
    except zipfile.BadZipFile:
        return False


def _omml_candidates(
    source_fs: SourceFS, eligible: list[tuple[str, str, str, str]]
) -> tuple[list[OmmlCandidateData], list[dict[str, Any]], list[dict[str, Any]]]:
    candidates: list[OmmlCandidateData] = []
    failures: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    for blob_id, root_id, relpath_raw, relpath in eligible:  # open by the exact OS name, report the NFC one
        data = source_fs.read_bytes(root_id, relpath_raw)
        if not _has_native_omml(data):
            continue
        latex_output, error = _pandoc_latex(data)
        if error is not None:
            failures.append({"blob_id": blob_id, "error": error})
            continue
        equations = extract_latex_equations(latex_output or "")
        xml_sources = _ordered_omml_xml(data)
        if len(equations) != len(xml_sources):
            mismatches.append(
                {"blob_id": blob_id, "pandoc_equations": len(equations), "main_document_omml": len(xml_sources)}
            )
            continue  # ordinal alignment is not defensible when the two independently counted streams differ
        paired_count = min(len(equations), len(xml_sources))
        display_count = len(_DISPLAY_MATH.findall(latex_output or ""))
        for index in range(paired_count):
            latex = equations[index]
            if not is_syntactically_plausible_latex(latex) or latex.rstrip().endswith("\\"):
                continue
            xml, xml_display = xml_sources[index]
            display = index < display_count
            if display != xml_display:
                mismatches.append({"blob_id": blob_id, "equation_ordinal": index + 1, "display_kind_mismatch": True})
                continue
            candidate_id = f"omml-{blob_id.removeprefix('b3:')[:16]}-{index + 1:04d}"
            candidate = MathCandidate(candidate_id, blob_id, "omml_exact", difficulty_tag(latex, display=display))
            candidates.append(OmmlCandidateData(candidate, root_id, relpath, index + 1, latex, xml, display))
    return candidates, failures, mismatches


def _pdf_math_score(text: str) -> int:
    compact = " ".join(text.split())
    if not 2 <= len(compact) <= 260:
        return 0
    chars = [char for char in compact if not char.isspace()]
    math_count = sum(char in _MATH_CHARS for char in chars)
    score = 0
    score += 3 if "=" in compact else 0
    score += 3 if any(char in _ADVANCED_MATH for char in compact) else 0
    score += 2 if any(char in "≤≥≈≠±×÷" for char in compact) else 0
    score += 1 if math_count >= 2 else 0
    score += 1 if re.search(r"[A-Za-zΑ-Ωα-ω]\s*[_^]?[0-9A-Za-z]?\s*[=<>≈]", compact) else 0
    score += 1 if re.search(r"\d\s*[/^*+-]\s*\d", compact) else 0
    score += 1 if chars and math_count / len(chars) >= 0.12 else 0
    return score


def _pdf_candidates_for_page(
    pdf_bytes: bytes, *, blob_id: str, root_id: str, relpath: str, page_number: int
) -> list[PdfCandidateData]:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    if page_number < 1 or page_number > len(reader.pages):
        return []
    page = reader.pages[page_number - 1]
    fragments: list[_TextFragment] = []

    def visit(text: str, _cm: list[float], tm: list[float], _font: dict[str, Any] | None, size: float) -> None:
        for offset, row in enumerate(text.splitlines()):
            cleaned = " ".join(row.replace("\x00", "").split())
            if cleaned:
                fragments.append(_TextFragment(cleaned, float(tm[4]), float(tm[5]) - offset * float(size), float(size)))

    page.extract_text(visitor_text=visit)
    lines: list[list[_TextFragment]] = []
    for fragment in sorted(fragments, key=lambda item: (-item.y, item.x, item.text)):
        line = next((row for row in lines if abs(row[0].y - fragment.y) <= max(2.5, fragment.size * 0.3)), None)
        if line is None:
            lines.append([fragment])
        else:
            line.append(fragment)

    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    results: list[PdfCandidateData] = []
    for line_index, line in enumerate(lines, start=1):
        ordered = sorted(line, key=lambda item: item.x)
        text = " ".join(item.text for item in ordered)
        score = _pdf_math_score(text)
        if score < 4:
            continue
        x0 = max(0.0, min(item.x for item in ordered) - 8.0)
        x1_estimated = max(item.x + max(12.0, len(item.text) * item.size * 0.56) for item in ordered) + 8.0
        x1 = min(width, max(x0 + 20.0, x1_estimated))
        y_center = sum(item.y for item in ordered) / len(ordered)
        font_size = max(item.size for item in ordered)
        y0 = max(0.0, y_center - font_size * 0.55 - 7.0)
        y1 = min(height, y_center + font_size * 1.25 + 7.0)
        math_chars = sum(char in _MATH_CHARS for char in text)
        display = len(text) <= 100 and math_chars / max(1, len(text.replace(" ", ""))) >= 0.10
        proxy = text + (r" \int" if any(char in _ADVANCED_MATH for char in text) else "")
        tag = difficulty_tag(proxy, display=display)
        candidate_id = f"pdf-{blob_id.removeprefix('b3:')[:12]}-p{page_number:04d}-l{line_index:03d}"
        results.append(
            PdfCandidateData(
                MathCandidate(candidate_id, blob_id, "pdf_native", tag), root_id, relpath, page_number, (x0, y0, x1, y1)
            )
        )
    return results


def _write_pdf_crop(pdf_bytes: bytes, page_number: int, bbox: tuple[float, float, float, float], path: Path) -> None:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    page = reader.pages[page_number - 1]
    box = RectangleObject(bbox)
    page.cropbox = box
    page.mediabox = box
    writer = pypdf.PdfWriter()
    writer.add_page(page)
    with path.open("wb") as stream:
        writer.write(stream)


def _safe_blob(blob: Any) -> bool:
    return blob.status is BlobStatus.ACTIVE and blob.sensitivity not in _BLOCKED_SENSITIVITY


def _clear_generated_crops(crop_dir: Path, config: Any) -> None:
    """Remove only this tool's prior numbered outputs so a rerun cannot leave ambiguous stale crops."""
    assert_writable(crop_dir.resolve(), config)
    for pattern in ("math-*.pdf", "math-*.omml.xml"):
        for path in crop_dir.glob(pattern):
            assert_writable(path.resolve(), config)
            path.unlink()


def main() -> int:
    args = _arguments()
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    config = load_config(args.config)
    source_fs = SourceFS(config)
    extract_sample = _load_yaml(args.extract_sample)

    with RegistryDB.open(config) as db:
        blobs = {blob.blob_id: blob for blob in db.repo(reg.BLOB).find()}
        observations = {obs.obs_id: obs for obs in db.repo(reg.PATH_OBSERVATION).find()}

    eligible_docx: list[tuple[str, str, str, str]] = []
    for blob in blobs.values():
        if blob.format != "docx" or not _safe_blob(blob) or blob.canonical_obs_id not in observations:
            continue
        observation = observations[blob.canonical_obs_id]
        eligible_docx.append((blob.blob_id, observation.root_id, observation.relpath_raw, observation.relpath))

    omml_data, omml_failures, omml_mismatches = _omml_candidates(source_fs, sorted(eligible_docx))
    pdf_data: list[PdfCandidateData] = []
    pdf_bytes_by_blob: dict[str, bytes] = {}
    pdf_failures: list[dict[str, Any]] = []
    for entry in extract_sample.get("sample", []):
        blob_id = str(entry["blob_id"])
        blob = blobs.get(blob_id)
        if blob is None or blob.format != "pdf" or not _safe_blob(blob) or blob.canonical_obs_id not in observations:
            continue
        observation = observations[blob.canonical_obs_id]
        page_number = int(entry["page"])
        try:
            pdf_bytes = source_fs.read_bytes(observation.root_id, observation.relpath_raw)
            pdf_bytes_by_blob[blob_id] = pdf_bytes
            pdf_data.extend(
                _pdf_candidates_for_page(
                    pdf_bytes,
                    blob_id=blob_id,
                    root_id=observation.root_id,
                    relpath=observation.relpath,
                    page_number=page_number,
                )
            )
        except Exception as exc:
            pdf_failures.append({"blob_id": blob_id, "page": page_number, "error": type(exc).__name__})

    all_candidates = [item.candidate for item in omml_data] + [item.candidate for item in pdf_data]
    selected, coverage = select_math_sample(all_candidates, target_equations=args.target_equations, seed=args.seed)
    omml_by_id = {item.candidate.candidate_id: item for item in omml_data}
    pdf_by_id = {item.candidate.candidate_id: item for item in pdf_data}

    assert_writable(args.crop_dir.resolve(), config)
    args.crop_dir.mkdir(parents=True, exist_ok=True)
    _clear_generated_crops(args.crop_dir, config)
    samples: list[dict[str, Any]] = []
    for index, candidate in enumerate(selected, start=1):
        sample_id = f"math-{index:03d}"
        if candidate.source_group == "omml_exact":
            item = omml_by_id[candidate.candidate_id]
            crop_path = args.crop_dir / f"{sample_id}.omml.xml"
            assert_writable(crop_path.resolve(), config)
            crop_path.write_text(item.xml, encoding="utf-8")
            samples.append(
                {
                    "sample_id": sample_id,
                    "candidate_id": candidate.candidate_id,
                    "blob_id": candidate.blob_id,
                    "root_id": item.root_id,
                    "relpath": item.relpath,
                    "page": 1,
                    "equation_ordinal": item.equation_ordinal,
                    "source_group": "omml_exact",
                    "source_kind": "omml_exact",
                    "difficulty_tag": candidate.difficulty_tag,
                    "status": "candidate_exact_unverified",
                    "latex": item.latex,
                    "crop": {
                        "path": str(crop_path),
                        "representation": "omml_xml_source_substitute",
                        "note": "Exact source OMML subtree; not a pixel crop because no DOCX renderer is available.",
                    },
                    "gold": {
                        "blocks": [],
                        "equations": [{"latex_normalized": item.latex, "source_kind": "omml_exact"}],
                        "tables": [],
                        "figures": [],
                    },
                }
            )
        else:
            item = pdf_by_id[candidate.candidate_id]
            crop_path = args.crop_dir / f"{sample_id}.pdf"
            assert_writable(crop_path.resolve(), config)
            _write_pdf_crop(pdf_bytes_by_blob[candidate.blob_id], item.page, item.bbox, crop_path)
            samples.append(
                {
                    "sample_id": sample_id,
                    "candidate_id": candidate.candidate_id,
                    "blob_id": candidate.blob_id,
                    "root_id": item.root_id,
                    "relpath": item.relpath,
                    "page": item.page,
                    "bbox": [round(value, 3) for value in item.bbox],
                    "source_group": "pdf_native",
                    "source_kind": None,
                    "difficulty_tag": candidate.difficulty_tag,
                    "status": "pending_ai_draft",
                    "latex": None,
                    "crop": {
                        "path": str(crop_path),
                        "representation": "cropped_pdf",
                        "note": "Original PDF content clipped to the detected equation-line bounds.",
                    },
                    "gold": {"blocks": [], "equations": [], "tables": [], "figures": []},
                }
            )

    exact_count = sum(item["status"] == "candidate_exact_unverified" for item in samples)
    pending_count = sum(item["status"] == "pending_ai_draft" for item in samples)
    output_doc = {
        "purpose": "T-P3-02 prep candidate set; not owner-verified and not task completion",
        "seed": args.seed,
        "target_equations": args.target_equations,
        "selected": len(samples),
        "owner_verified": False,
        "gates": {
            "owner_verification": "open: every equation plus a 10 percent double-check needs owner judgment",
            "q_b04_model_gateway": f"open: {pending_count} PDF-native crops have null LaTeX and pending_ai_draft",
        },
        "difficulty_heuristic": (
            "inline/display presentation plus complex when an environment/high-order operator, >=2 fractions, "
            ">=3 scripts, explicit line break, or >=80 characters is observed; PDF text is used only for tagging"
        ),
        "counts": {"omml_exact": exact_count, "pending_ai_draft": pending_count, "total": len(samples)},
        "candidate_pools": {"omml_exact": len(omml_data), "pdf_native": len(pdf_data)},
        "coverage": coverage,
        "probe_failures": {"omml": omml_failures, "pdf": pdf_failures},
        "omml_pairing_mismatches": omml_mismatches,
        "samples": samples,
    }
    assert_writable(args.output.resolve(), config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.width = 120
    with args.output.open("w", encoding="utf-8") as stream:
        yaml.dump(output_doc, stream)

    summary = {
        "candidate_pools": output_doc["candidate_pools"],
        "counts": output_doc["counts"],
        "coverage": coverage,
        "omml_conversion_failures": len(omml_failures),
        "omml_pairing_mismatches": len(omml_mismatches),
        "pdf_probe_failures": len(pdf_failures),
        "output": str(args.output),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print("All output is local under eval/gold/; pending PDF LaTeX is explicitly null.")
    return 0 if len(samples) == args.target_equations else 2


if __name__ == "__main__":
    raise SystemExit(main())
