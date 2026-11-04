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

Every source file is opened read-only via SourceFS, addressed by its exact on-disk ``relpath_raw`` (the NFC
``relpath`` is only a display/identity key and can fail to resolve on a normalization-sensitive filesystem).
Tesseract runs against a private temp image file, never a source-tree path.

``--orientation-census`` (added 2026-11-04) answers a follow-up to this spike's own finding that one scanned page
is stored upside-down: it runs Tesseract orientation detection (``--psm 0``, OSD) on **every** scanned-page
candidate rather than a sample, and for each page OSD says needs rotating compares OCR with the default page
segmentation (``--psm 3``) against Tesseract's own OSD-corrected segmentation (``--psm 1``). A seeded control
sample of upright pages gets the same comparison, so a regression on normal pages would be visible. It writes its
own report and leaves the sampled-run report alone.
"""

from __future__ import annotations

import argparse
import functools
import io
import json
import os
import random
import subprocess
import tempfile
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pypdf
from PIL import Image

from sbr.config import load_config
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.eval.extract.ocr import (
    OsdResult,
    confident_word_count,
    mean_word_confidence,
    orientation_agreement,
    parse_tesseract_osd,
    parse_tesseract_tsv,
    pick_rotation,
    summarize_rotations,
)
from sbr.eval.gold_extract import representative_page
from sbr.eval.signals import is_scanned_page
from sbr.eval.spike_gate import processable_blobs
from sbr.sourcefs import SourceFS

# (blob_id, root_id, relpath_raw for opening, relpath for display, 1-based page number)
Candidate = tuple[str, str, str, str, int]

DEFAULT_OUTPUT = Path("eval/reports/spike_ocr.md")
DEFAULT_ORIENTATION_OUTPUT = Path("eval/reports/spike_ocr_orientation.md")
DEFAULT_ROTATION_ORACLE_OUTPUT = Path("eval/reports/spike_ocr_rotation_oracle.md")
DEFAULT_ORACLE_WORKERS = 8
ORACLE_ROTATIONS = (0, 90, 180, 270)
# OSD confidence cut-offs at which the "apply OSD" policy is scored; 0.0 means "always trust OSD".
ORACLE_OSD_THRESHOLDS = (0.0, 1.0, 2.0, 5.0, 10.0)
DEFAULT_CONTROL_SIZE = 15
# Reported alongside the raw distribution, never used to drop a page: Tesseract's orientation confidence is an
# unbounded score, and this spike's job is to show how the bucket counts move with the cut-off, not to pick one.
DEFAULT_MIN_ORIENTATION_CONFIDENCE = 2.0
DEFAULT_PAGE_CENSUS = Path("audit/phase0/t3/pdf_unique_pages_t3.jsonl")
DEFAULT_SAMPLE_SIZE = 25
DEFAULT_SEED = 20_260_926


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="T-P3-08 SPIKE-OCR: Tesseract deu evidence on scanned pages.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--page-census", type=Path, default=DEFAULT_PAGE_CENSUS)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--orientation-census",
        action="store_true",
        help="run OSD on every scanned candidate and compare --psm 3 vs --psm 1 OCR on rotated pages",
    )
    parser.add_argument(
        "--rotation-oracle",
        action="store_true",
        help="OCR every scanned candidate at 0/90/180/270 and score OSD, /Rotate and fixed policies against it",
    )
    parser.add_argument("--workers", type=int, default=DEFAULT_ORACLE_WORKERS)
    parser.add_argument("--control-size", type=int, default=DEFAULT_CONTROL_SIZE)
    parser.add_argument("--min-orientation-confidence", type=float, default=DEFAULT_MIN_ORIENTATION_CONFIDENCE)
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


def _run_osd(image_bytes: bytes) -> tuple[OsdResult | None, str | None]:
    """Returns (osd_result, error). A page Tesseract declines ("Too few characters") is ``(None, None)``."""
    with tempfile.TemporaryDirectory() as tmp:
        image_path = Path(tmp) / "page.png"
        image_path.write_bytes(image_bytes)
        try:
            result = subprocess.run(
                ["tesseract", str(image_path), "stdout", "--psm", "0"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return None, f"{type(exc).__name__}: {exc}"
        parsed = parse_tesseract_osd(result.stdout + "\n" + result.stderr)
        if parsed is None and "Too few characters" not in result.stderr and result.returncode != 0:
            return None, result.stderr.strip()[:300]
        return parsed, None


def _ocr_confidence(image_bytes: bytes, psm: int) -> tuple[int, float | None, str | None]:
    """Returns (word_count, mean_confidence, error) for ``tesseract -l deu --psm <psm> tsv``."""
    with tempfile.TemporaryDirectory() as tmp:
        image_path = Path(tmp) / "page.png"
        image_path.write_bytes(image_bytes)
        try:
            result = subprocess.run(
                ["tesseract", str(image_path), "stdout", "-l", "deu", "--psm", str(psm), "tsv"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return 0, None, f"{type(exc).__name__}: {exc}"
        if result.returncode != 0:
            return 0, None, result.stderr.strip()[:300]
        words = parse_tesseract_tsv(result.stdout)
        return len(words), mean_word_confidence(words), None


def _first_page_image(source_fs: SourceFS, root_id: str, relpath_raw: str, page: int) -> bytes | None:
    with source_fs.open_binary(root_id, relpath_raw) as stream:
        reader = pypdf.PdfReader(stream)
        index = min(page - 1, len(reader.pages) - 1)
        images = list(reader.pages[index].images)
    return images[0].data if images else None


def _find_scanned_candidates(config_path: Path, page_census: Path) -> tuple[SourceFS, list[Candidate]]:
    config = load_config(config_path)
    source_fs = SourceFS(config)
    pdf_pages = _load_pdf_page_counts(page_census)

    with RegistryDB.open(config) as db:
        observations = {o.obs_id: o for o in db.repo(reg.PATH_OBSERVATION).find()}
        blobs = processable_blobs(db, observations.values(), {"pdf"})

        scanned_candidates: list[Candidate] = []
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
                scanned_candidates.append((blob.blob_id, obs.root_id, obs.relpath_raw, obs.relpath, page))
    return source_fs, scanned_candidates


def _orientation_census(args: argparse.Namespace) -> int:
    source_fs, candidates = _find_scanned_candidates(args.config, args.page_census)
    output: Path = args.output or DEFAULT_ORIENTATION_OUTPUT

    rows: list[dict[str, Any]] = []
    for blob_id, root_id, relpath_raw, relpath, page in candidates:
        row: dict[str, Any] = {"blob_id": blob_id, "relpath": relpath, "page": page}
        try:
            image = _first_page_image(source_fs, root_id, relpath_raw, page)
        except Exception as exc:  # one unreadable PDF must not abort the census
            row["error"] = f"{type(exc).__name__}"
            rows.append(row)
            continue
        if image is None:
            row["error"] = "no embedded image found"
            rows.append(row)
            continue
        osd, error = _run_osd(image)
        row["osd"] = osd
        if error is not None:
            row["error"] = error
        row["image"] = image
        rows.append(row)

    imaged = [r for r in rows if "image" in r and "error" not in r]
    rotated = [r for r in imaged if r["osd"] is not None and r["osd"].rotate != 0]
    upright = [r for r in imaged if r["osd"] is not None and r["osd"].rotate == 0]
    rng = random.Random(args.seed)
    control = rng.sample(upright, min(args.control_size, len(upright)))
    for r in (*rotated, *control):
        r["psm3"] = _ocr_confidence(r["image"], 3)
        r["psm1"] = _ocr_confidence(r["image"], 1)

    osd_results: list[OsdResult | None] = [r["osd"] for r in imaged]
    all_counts = summarize_rotations(osd_results, min_confidence=float("-inf"))
    confident_counts = summarize_rotations(osd_results, min_confidence=args.min_orientation_confidence)

    def _fmt(value: float | None) -> str:
        return "-" if value is None else f"{value:.1f}"

    def _comparison_rows(selected: list[dict[str, Any]]) -> list[str]:
        out: list[str] = []
        for r in selected:
            osd = r["osd"]
            w3, c3, e3 = r["psm3"]
            w1, c1, e1 = r["psm1"]
            delta = (c1 - c3) if c1 is not None and c3 is not None else None
            out.append(
                f"| {r['relpath']} | {r['page']} | {osd.rotate} | {osd.orientation_confidence:.2f} | {w3} | "
                f"{_fmt(c3)} | {w1} | {_fmt(c1)} | {_fmt(delta)} | {e3 or e1 or ''} |"
            )
        return out

    def _mean_delta(selected: list[dict[str, Any]]) -> str:
        deltas = [
            r["psm1"][1] - r["psm3"][1] for r in selected if r["psm1"][1] is not None and r["psm3"][1] is not None
        ]
        return f"{sum(deltas) / len(deltas):+.1f} over {len(deltas)} pages" if deltas else "n/a"

    header = (
        "| relpath | page | OSD rotate | OSD confidence | words psm3 | mean conf psm3 | words psm1 | "
        "mean conf psm1 | delta conf | error |"
    )
    lines = [
        "# SPIKE-OCR follow-up: page-orientation census on scanned pages (T-P3-08)",
        "",
        "Tesseract 5 orientation and script detection (`--psm 0`) on **every** scanned-page candidate (the same "
        "discovery as the sampled run in `spike_ocr.md`), not a sample. Pages OSD says need rotating are then "
        "OCR'd twice with `-l deu`: default page segmentation (`--psm 3`, what `spike_ocr.md` measured) and "
        "Tesseract's own OSD-corrected segmentation (`--psm 1`). A seeded control sample of upright pages gets "
        "the same comparison.",
        "",
        "**Evidence, not a decision.** OSD confidence is Tesseract's unbounded score. The table gives the raw "
        f"distribution and the distribution at a reported cut-off of {args.min_orientation_confidence}, so the "
        "effect of the cut-off is visible. Mean word confidence is not CER: correctness still needs gold "
        "transcriptions (T-P3-03). Choosing an orientation step and threshold for the real pipeline belongs to "
        "ADR-010/T-P4.",
        "",
        f"- scanned-page candidates: {len(candidates)}",
        f"- pages with no embedded image: {sum(1 for r in rows if r.get('error') == 'no embedded image found')}",
        f"- pages with another read or OSD error: "
        f"{sum(1 for r in rows if 'error' in r and r['error'] != 'no embedded image found')}",
        f"- pages OSD declined (too few characters): {all_counts['undetected']}",
        f"- OSD rotate distribution, any confidence: 0={all_counts['0']}, 90={all_counts['90']}, "
        f"180={all_counts['180']}, 270={all_counts['270']}",
        f"- OSD rotate distribution, confidence >= {args.min_orientation_confidence}: 0={confident_counts['0']}, "
        f"90={confident_counts['90']}, 180={confident_counts['180']}, 270={confident_counts['270']}, "
        f"below cut-off={confident_counts['low_confidence']}",
        f"- mean word-confidence change psm1 - psm3, rotated pages: {_mean_delta(rotated)}",
        f"- mean word-confidence change psm1 - psm3, upright control: {_mean_delta(control)}",
        "",
        "## Pages OSD says need rotating",
        "",
        header,
        "|---|---|---|---|---|---|---|---|---|---|",
        *_comparison_rows(sorted(rotated, key=lambda r: -r["osd"].orientation_confidence)),
        "",
        f"## Upright control sample (seeded, {len(control)} pages)",
        "",
        header,
        "|---|---|---|---|---|---|---|---|---|---|",
        *_comparison_rows(control),
        "",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "scanned_candidates": len(candidates),
        "osd_rotate_any_confidence": all_counts,
        "osd_rotate_confident": confident_counts,
        "min_orientation_confidence": args.min_orientation_confidence,
        "rotated_pages_compared": len(rotated),
        "control_pages_compared": len(control),
        "mean_delta_rotated": _mean_delta(rotated),
        "mean_delta_control": _mean_delta(control),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"report written to {output}")
    return 0


def _page_image_and_rotate(source_fs: SourceFS, root_id: str, relpath_raw: str, page: int) -> tuple[bytes | None, int]:
    """The page's first embedded image and its ``/Rotate`` (normalized to 0/90/180/270, clockwise)."""
    with source_fs.open_binary(root_id, relpath_raw) as stream:
        reader = pypdf.PdfReader(stream)
        pdf_page = reader.pages[min(page - 1, len(reader.pages) - 1)]
        images = list(pdf_page.images)
        rotate = int(pdf_page.rotation) % 360
    return (images[0].data if images else None), rotate


def _score_rotation(image_bytes: bytes, rotation: int) -> tuple[int, float | None, str | None]:
    """(confident words, mean confidence, error) for ``tesseract -l deu --psm 3`` on the image turned ``rotation``
    degrees clockwise. ``--psm 3`` does no orientation correction of its own, so the rotation is the only variable."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.load()
            turned = img.rotate(-rotation, expand=True) if rotation else img.copy()
        buffer = io.BytesIO()
        turned.save(buffer, format="PNG")
    except Exception as exc:  # a corrupt or exotic image is one page's error, not the run's
        return 0, None, f"image: {type(exc).__name__}"
    with tempfile.TemporaryDirectory() as tmp:
        image_path = Path(tmp) / "page.png"
        image_path.write_bytes(buffer.getvalue())
        try:
            result = subprocess.run(
                ["tesseract", str(image_path), "stdout", "-l", "deu", "--psm", "3", "tsv"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
                check=False,
                env={**os.environ, "OMP_THREAD_LIMIT": "1"},
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return 0, None, f"{type(exc).__name__}: {exc}"
    if result.returncode != 0:
        return 0, None, result.stderr.strip()[:300]
    words = parse_tesseract_tsv(result.stdout)
    return confident_word_count(words), mean_word_confidence(words), None


def _oracle_row(source_fs: SourceFS, candidate: Candidate) -> dict[str, Any]:
    blob_id, root_id, relpath_raw, relpath, page = candidate
    row: dict[str, Any] = {"blob_id": blob_id, "relpath": relpath, "page": page}
    try:
        image, pdf_rotate = _page_image_and_rotate(source_fs, root_id, relpath_raw, page)
    except Exception as exc:  # one unreadable PDF must not abort the run
        row["error"] = type(exc).__name__
        return row
    row["pdf_rotate"] = pdf_rotate
    if image is None:
        row["error"] = "no embedded image found"
        return row
    osd, osd_error = _run_osd(image)
    row["osd"] = osd
    scores: dict[int, int] = {}
    for rotation in ORACLE_ROTATIONS:
        count, _mean, error = _score_rotation(image, rotation)
        if error is not None:
            row["error"] = error
            return row
        scores[rotation] = count
    row["scores"] = scores
    row["verdict"] = pick_rotation(scores)
    if osd_error is not None:
        row["osd_error"] = osd_error
    return row


def _safe_oracle_row(source_fs: SourceFS, candidate: Candidate) -> dict[str, Any]:
    """One page's unexpected failure becomes that page's error, never the run's (a 10-minute run once died on one)."""
    try:
        return _oracle_row(source_fs, candidate)
    except Exception as exc:  # recorded per page, counted in the report
        return {"blob_id": candidate[0], "relpath": candidate[3], "page": candidate[4], "error": type(exc).__name__}


def _policy_accuracy(rows: list[dict[str, Any]], choose: Callable[[dict[str, Any]], int]) -> tuple[int, int, int]:
    """(correct, made_worse, decided) over pages with a confident, unambiguous oracle verdict. ``made_worse``
    counts pages the oracle says were upright as stored (rotate 0) that the policy turns anyway."""
    decided = [r for r in rows if r["verdict"].rotate is not None and not r["verdict"].ambiguous]
    correct = sum(1 for r in decided if choose(r) == r["verdict"].rotate)
    worse = sum(1 for r in decided if r["verdict"].rotate == 0 and choose(r) != 0)
    return correct, worse, len(decided)


def _rotation_oracle(args: argparse.Namespace) -> int:
    source_fs, candidates = _find_scanned_candidates(args.config, args.page_census)
    output: Path = args.output or DEFAULT_ROTATION_ORACLE_OUTPUT
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = list(pool.map(lambda c: _safe_oracle_row(source_fs, c), candidates))
    elapsed = time.perf_counter() - started

    scored = [r for r in rows if "verdict" in r]
    verdicts = [r["verdict"] for r in scored]
    oracle_counts: dict[str, int] = {str(r): sum(1 for v in verdicts if v.rotate == r) for r in ORACLE_ROTATIONS}
    unreadable = sum(1 for v in verdicts if v.rotate is None)
    ambiguous = sum(1 for v in verdicts if v.rotate is not None and v.ambiguous)

    def _osd_rotate(r: dict[str, Any], threshold: float) -> int:
        osd = r["osd"]
        return osd.rotate if osd is not None and osd.orientation_confidence >= threshold else 0

    agreement = orientation_agreement(
        [
            (r["osd"].rotate if r["osd"] is not None else None, None if r["verdict"].ambiguous else r["verdict"].rotate)
            for r in scored
        ]
    )
    policies: list[tuple[str, Callable[[dict[str, Any]], int]]] = [
        ("never rotate", lambda r: 0),
        ("honour PDF /Rotate", lambda r: int(r["pdf_rotate"])),
    ]
    for threshold in ORACLE_OSD_THRESHOLDS:
        policies.append(
            (f"apply OSD at confidence >= {threshold}", functools.partial(_osd_rotate, threshold=threshold))
        )

    def _pct(part: int, whole: int) -> str:
        return f"{100 * part / whole:.1f}%" if whole else "n/a"

    policy_lines = []
    for name, choose in policies:
        correct, worse, decided = _policy_accuracy(scored, choose)
        policy_lines.append(f"| {name} | {correct}/{decided} ({_pct(correct, decided)}) | {worse} |")

    by_pdf_rotate: dict[int, dict[int | None, int]] = {}
    for r in scored:
        cell = by_pdf_rotate.setdefault(int(r["pdf_rotate"]), {})
        key = None if r["verdict"].ambiguous else r["verdict"].rotate
        cell[key] = cell.get(key, 0) + 1
    cross_lines = [
        f"| {pr} | " + " | ".join(str(cells.get(o, 0)) for o in (*ORACLE_ROTATIONS, None)) + " |"
        for pr, cells in sorted(by_pdf_rotate.items())
    ]

    disagreements = [
        r
        for r in scored
        if r["osd"] is not None
        and r["verdict"].rotate is not None
        and not r["verdict"].ambiguous
        and r["osd"].rotate != r["verdict"].rotate
    ]
    disagreement_lines = [
        f"| {r['relpath']} | {r['page']} | {r['pdf_rotate']} | {r['osd'].rotate} | "
        f"{r['osd'].orientation_confidence:.2f} | {r['verdict'].rotate} | "
        + " / ".join(str(r["scores"][x]) for x in ORACLE_ROTATIONS)
        + " |"
        for r in sorted(disagreements, key=lambda r: -r["osd"].orientation_confidence)
    ]
    by_osd = agreement["by_osd"]
    lines = [
        "# SPIKE-OCR follow-up: rotation oracle and correction policies (T-P3-08)",
        "",
        "Every scanned-page candidate's first embedded image is OCR'd with `tesseract -l deu --psm 3` four times, "
        "turned 0/90/180/270 degrees clockwise. `--psm 3` does no orientation correction itself, so the rotation "
        "is the only variable. The rotation with the most words at confidence >= 80 is the **readability oracle**; "
        "a leader within 15% of the runner-up is *ambiguous*, and a page with fewer than 5 such words in every "
        "rotation is *unreadable* (no verdict). OSD (`--psm 0`) and the page's PDF `/Rotate` are then scored "
        "against the oracle.",
        "",
        "**Evidence, not a decision.** The oracle is a proxy, not ground truth: it is only as good as Tesseract's "
        "own confidence, and it says nothing about CER (that needs T-P3-03 gold transcriptions). The orientation "
        "step and threshold for the pipeline stay with ADR-010/T-P4. Blobs the sensitivity gate rejects are not "
        "opened (counts on stderr only).",
        "",
        f"- scanned-page candidates: {len(candidates)}; scored at all four rotations: {len(scored)}; "
        f"no embedded image: {sum(1 for r in rows if r.get('error') == 'no embedded image found')}; "
        f"other errors: {sum(1 for r in rows if 'error' in r and r['error'] != 'no embedded image found')}",
        f"- oracle verdicts: 0={oracle_counts['0']}, 90={oracle_counts['90']}, 180={oracle_counts['180']}, "
        f"270={oracle_counts['270']}; ambiguous={ambiguous}; unreadable={unreadable}",
        f"- OSD vs oracle (both decided): {agreement['agree']}/{agreement['compared']} agree "
        f"({_pct(agreement['agree'], agreement['compared'])}); OSD declined {agreement['osd_abstained']}, "
        f"oracle abstained {agreement['oracle_abstained']}",
        "- OSD vs oracle by OSD call: "
        + ", ".join(
            f"{k}: {v['agree']}/{v['agree'] + v['disagree']} agree"
            for k, v in by_osd.items()
            if v["agree"] + v["disagree"]
        ),
        f"- wall time: {elapsed:.0f} s with {args.workers} workers",
        "",
        "## Correction policies scored against the oracle",
        "",
        "Only pages with a decided, unambiguous oracle verdict count. *Made worse* = pages the oracle reads best as "
        "stored that the policy rotates anyway.",
        "",
        "| policy | correct | made worse |",
        "|---|---|---|",
        *policy_lines,
        "",
        "## PDF /Rotate against the oracle",
        "",
        "| PDF /Rotate | oracle 0 | oracle 90 | oracle 180 | oracle 270 | ambiguous or unreadable |",
        "|---|---|---|---|---|---|",
        *cross_lines,
        "",
        f"## Pages where OSD and a decided oracle disagree ({len(disagreements)})",
        "",
        "| relpath | page | PDF /Rotate | OSD rotate | OSD confidence | oracle rotate | words>=80 at 0/90/180/270 |",
        "|---|---|---|---|---|---|---|",
        *disagreement_lines,
        "",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps({"scored": len(scored), "oracle": oracle_counts, "agreement": agreement}, indent=2, sort_keys=True)
    )
    print(f"report written to {output}")
    return 0


def main() -> int:
    args = _arguments()
    if args.rotation_oracle:
        return _rotation_oracle(args)
    if args.orientation_census:
        return _orientation_census(args)
    source_fs, scanned_candidates = _find_scanned_candidates(args.config, args.page_census)
    output: Path = args.output or DEFAULT_OUTPUT

    rng = random.Random(args.seed)
    sample = rng.sample(scanned_candidates, min(args.sample_size, len(scanned_candidates)))

    results: list[dict[str, Any]] = []
    for blob_id, root_id, relpath_raw, relpath, page in sample:
        image = _first_page_image(source_fs, root_id, relpath_raw, page)
        if image is None:
            results.append({"blob_id": blob_id, "relpath": relpath, "page": page, "error": "no embedded image found"})
            continue

        start = time.perf_counter()
        text, tsv, error = _run_tesseract(image)
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

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "scanned_candidates": len(scanned_candidates),
        "sampled": len(sample),
        "ocred_successfully": len(ok_results),
        "mean_elapsed_seconds": (sum(elapsed_values) / len(elapsed_values)) if elapsed_values else None,
        "mean_confidence": (sum(confidence_values) / len(confidence_values)) if confidence_values else None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"report written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
