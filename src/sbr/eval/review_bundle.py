"""Unified owner-review bundle for the Phase 3 gates (T-P3-02 math, T-P3-03 layout, T-P3-07 PPTX math, T-P5-06
taxonomy).

A *bundle* is a deterministic JSON document of review items. Each item keeps the **original** annotation verbatim,
separate from **machine proposals** (each labelled with its origin and confidence) and **machine checks** (flags). No
item carries a decision: decisions come only from the owner, through an exported decisions file that
:func:`validate_decisions` checks all-or-nothing against the exact bundle it was made from (fingerprint).

:class:`ReviewLedger` stores accepted decisions append-only. Re-importing an identical decision is a no-op; changing
a recorded decision needs an explicit ``allow_supersede`` and keeps the earlier record (``supersedes``). The reviewer
identity is always supplied by the person running the import, never inferred.

Content the sensitivity rules block (``restricted``, ``third_party_personal``) is never put in a bundle; only its count
is (docs/22 §3). Everything here is pure or file-local: no network, no model calls.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import random
import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Any, Final

from sbr.config import SbrConfig
from sbr.eval.extract.omml_latex import latex_compare_key, latex_text_signature, omml_xml_to_latex
from sbr.registry.sensitivity import LOCAL_PROCESSING_BLOCKED, automatic_sensitivity
from sbr.safety import assert_writable

BUNDLE_SCHEMA: Final = "sbr-review-bundle/1"
DECISIONS_SCHEMA: Final = "sbr-review-decisions/1"
ORIGIN: Final = "machine:review_bundle@1"
DECISIONS: Final = ("accept", "correct", "reject", "uncertain")
SECTIONS: Final = ("layout", "math", "math_double_check", "pptx", "taxonomy")
RISKY_LAYOUT_BUCKETS: Final = frozenset({"unusual_reading_order", "multi_column", "scanned"})
DOUBLE_CHECK_SEED: Final = 20_261_104  # deliberately different from the T-P3-02 selection seed
_REVIEWER_RE = re.compile(r"^user:[a-z][a-z0-9_.-]{0,63}$")

PathAllowed = Callable[[str], bool]


class ReviewError(ValueError):
    """A decisions file or ledger operation was refused; nothing was recorded."""


def default_path_allowed(relpath: str) -> bool:
    """Current automatic sensitivity rules (stricter than the registry, never looser)."""
    return automatic_sensitivity(relpath).sensitivity not in LOCAL_PROCESSING_BLOCKED


def _flag(check: str, severity: str, detail: str) -> dict[str, str]:
    return {"check": check, "severity": severity, "detail": detail}


def _proposal(pid: str, field: str, value: Any, rationale: str, confidence: str) -> dict[str, Any]:
    return {
        "proposal_id": pid,
        "field": field,
        "value": value,
        "rationale": rationale,
        "confidence": confidence,
        "origin": ORIGIN,
    }


def _item(
    item_id: str,
    kind: str,
    title: str,
    original: Mapping[str, Any],
    *,
    flags: Sequence[Mapping[str, str]] = (),
    proposals: Sequence[Mapping[str, Any]] = (),
    attachments: Sequence[str] = (),
    source: Mapping[str, Any] | None = None,
    prior_decision: Mapping[str, Any] | None = None,
    allowed: Sequence[str] = DECISIONS,
    priority: int = 1,
) -> dict[str, Any]:
    if any(f["severity"] == "error" for f in flags):
        priority = 0
    return {
        "item_id": item_id,
        "kind": kind,
        "title": title,
        "priority": priority,
        "original": dict(original),
        "flags": [dict(f) for f in flags],
        "proposals": [dict(p) for p in proposals],
        "attachments": list(attachments),
        "source": dict(source) if source else None,
        "prior_decision": dict(prior_decision) if prior_decision else None,
        "allowed_decisions": list(allowed),
    }


# -- layout (T-P3-03) --------------------------------------------------------------------------------------------

_MATHY = re.compile(r"[=∑∫∂√≤≥≈±∞]|[α-ωΑ-Ω]|\b[a-zA-Z]_[a-zA-Z0-9]|\^\d")


def layout_checks(entry: Mapping[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """Machine checks and proposals for one heuristic layout draft (no page image needed)."""
    gold = entry.get("gold", {}) or {}
    blocks: list[Mapping[str, Any]] = list(gold.get("blocks", []) or [])
    tables: list[Any] = list(gold.get("tables", []) or [])
    figures: list[Mapping[str, Any]] = list(gold.get("figures", []) or [])
    bucket = str(entry.get("bucket", ""))
    flags: list[dict[str, str]] = []
    proposals: list[dict[str, Any]] = []

    orders = [b.get("reading_order") for b in blocks]
    if sorted(o for o in orders if isinstance(o, int)) != list(range(len(blocks))) or len(set(orders)) != len(orders):
        flags.append(_flag("reading_order_invalid", "error", "reading_order is not a unique 0..n-1 sequence"))
    empty = sum(1 for b in blocks if not str(b.get("text", "")).strip())
    if empty:
        flags.append(_flag("empty_blocks", "warn", f"{empty} block(s) without text"))
    text_blocks = [b for b in blocks if b.get("kind") not in ("figure", "table")]
    if bucket == "scanned" and not text_blocks:
        flags.append(
            _flag("scanned_no_text", "warn", "scanned page without a text layer: blocks must be transcribed by hand")
        )
    if bucket == "multi_column":
        flags.append(_flag("column_heuristic", "info", "columns were split at 50% page width; verify reading order"))
    if bucket == "unusual_reading_order":
        flags.append(_flag("order_heuristic", "info", "order is top-to-bottom by line; verify it against the page"))
    positions = {id(b): i for i, b in enumerate(sorted(blocks, key=lambda b: b.get("reading_order", 0)))}
    inner_hf = [b for b in blocks if b.get("kind") == "header_footer" and 2 <= positions[id(b)] < len(blocks) - 2]
    if inner_hf:
        flags.append(
            _flag("header_footer_mid_page", "warn", f"{len(inner_hf)} header/footer block(s) in mid reading order")
        )
    for t_index, table in enumerate(tables):
        widths = {len(row) for row in table}
        if len(widths) > 1:
            flags.append(_flag("ragged_table", "warn", f"table {t_index}: rows have {sorted(widths)} cells"))
    if bucket == "table_heavy" and not tables:
        flags.append(_flag("table_missing", "warn", "table-heavy bucket but no table drafted"))
    if bucket == "figures_with_captions" and not any(f.get("caption") for f in figures):
        flags.append(_flag("caption_missing", "warn", "figure bucket but no figure-caption pair drafted"))
    captions = sum(1 for b in blocks if b.get("kind") == "caption")
    if captions > len(figures):
        flags.append(_flag("caption_without_figure", "warn", f"{captions} caption(s) for {len(figures)} figure(s)"))
    mathy = sum(1 for b in text_blocks if _MATHY.search(str(b.get("text", ""))))
    if mathy and not gold.get("equations"):
        flags.append(_flag("math_not_annotated", "info", f"{mathy} block(s) look like math; no equation annotated"))
    texts = Counter(str(b.get("text", "")).strip() for b in text_blocks if str(b.get("text", "")).strip())
    dup = sum(n - 1 for n in texts.values() if n > 1)
    if dup:
        flags.append(_flag("duplicate_text", "info", f"{dup} repeated block text(s)"))

    merged = merge_paragraph_lines(blocks)
    if len(merged) < len(blocks):
        flags.append(
            _flag(
                "line_level_paragraphs",
                "warn",
                f"draft has one block per text line; {len(blocks)} blocks would become {len(merged)} after merging "
                "consecutive paragraph lines",
            )
        )
        proposals.append(
            _proposal(
                "merge_paragraph_lines",
                "gold.blocks",
                merged,
                "consecutive 'paragraph' lines merged into one paragraph block; other kinds and order kept",
                "medium",
            )
        )
    return flags, proposals


def merge_paragraph_lines(blocks: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Merge runs of consecutive ``paragraph`` blocks (in reading order), joining hyphenated line breaks."""
    out: list[dict[str, Any]] = []
    for block in sorted(blocks, key=lambda b: b.get("reading_order", 0)):
        text = str(block.get("text", ""))
        if out and block.get("kind") == "paragraph" and out[-1]["kind"] == "paragraph":
            prev = out[-1]["text"]
            nxt = text.lstrip()
            # German line-end hyphen: "be-" + "steht" joins; "Sensor-" + "Aktor" is a real compound hyphen
            if prev.endswith("-") and prev[-2:-1].isalpha() and nxt[:1].islower():
                joined = prev[:-1] + nxt
            elif prev.endswith("-") and prev[-2:-1].isalpha():
                joined = prev + nxt
            else:
                joined = f"{prev} {text}"
            out[-1]["text"] = " ".join(joined.split())
            continue
        out.append({"kind": block.get("kind"), "reading_order": len(out), "text": text})
    return out


def layout_items(
    annotations: Mapping[str, Any],
    decisions: Mapping[str, Mapping[str, Any]],
    *,
    path_allowed: PathAllowed = default_path_allowed,
) -> tuple[list[dict[str, Any]], int]:
    items: list[dict[str, Any]] = []
    withheld = 0
    for entry in annotations.get("samples", []) or []:
        relpath = str(entry.get("relpath", ""))
        if not path_allowed(relpath):
            withheld += 1
            continue
        sample_id = str(entry["sample_id"])
        flags, proposals = layout_checks(entry)
        bucket = str(entry.get("bucket", ""))
        items.append(
            _item(
                f"layout:{sample_id}",
                "layout",
                f"{sample_id} · {bucket}",
                {"bucket": bucket, "gold": entry.get("gold", {})},
                flags=flags,
                proposals=proposals,
                attachments=[f"../layout/review/{sample_id}.pdf"],
                source={"relpath": relpath, "page": entry.get("page")},
                prior_decision=decisions.get(sample_id),
                allowed=("accept", "correct", "reject", "uncertain"),
                priority=0 if bucket in RISKY_LAYOUT_BUCKETS else 1,
            )
        )
    return items, withheld


# -- math (T-P3-02) ----------------------------------------------------------------------------------------------


def _balanced(latex: str) -> bool:
    depth = 0
    escaped = False
    for ch in latex:
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def math_checks(
    entry: Mapping[str, Any], crop_bytes: bytes | None
) -> tuple[list[dict[str, str]], list[dict[str, Any]], tuple[str, ...]]:
    """Checks, proposals and allowed decisions for one MBI-Gold-Math entry."""
    latex = entry.get("latex")
    flags: list[dict[str, str]] = []
    proposals: list[dict[str, Any]] = []
    if latex is None:
        flags.append(
            _flag(
                "pending_transcription",
                "warn",
                "no LaTeX: no local formula model is configured (ADR-039/ADR-040). Transcribe by hand (correct), "
                "reject, mark uncertain, or leave pending",
            )
        )
        return flags, proposals, ("correct", "reject", "uncertain")
    latex = str(latex)
    if not latex.strip():
        flags.append(_flag("empty_latex", "error", "LaTeX is empty"))
    if not _balanced(latex):
        flags.append(_flag("unbalanced_braces", "error", "braces in the stored LaTeX do not balance"))
    if entry.get("source_kind") == "omml_exact":
        if crop_bytes is None:
            flags.append(_flag("crop_missing", "error", "OMML crop file not found; cannot cross-check"))
        else:
            converted = omml_xml_to_latex(crop_bytes)
            if converted is None:
                flags.append(_flag("crop_xml_invalid", "error", "OMML crop is not well-formed XML"))
            elif len(converted) != 1:
                flags.append(_flag("crop_equation_count", "error", f"crop holds {len(converted)} equations, not 1"))
            else:
                native = converted[0]
                if native.unsupported:
                    flags.append(
                        _flag("native_unsupported", "warn", f"OMML elements kept as text: {native.unsupported}")
                    )
                if latex_text_signature(native.latex) != latex_text_signature(latex):
                    flags.append(
                        _flag(
                            "mispaired",
                            "error",
                            "stored LaTeX has different letters/digits than the crop: it belongs to another equation",
                        )
                    )
                    proposals.append(
                        _proposal(
                            "native_latex",
                            "latex",
                            native.latex,
                            "native OMML->LaTeX of this entry's own crop (prototype converter; verify the render)",
                            "medium",
                        )
                    )
                elif latex_compare_key(native.latex) != latex_compare_key(latex):
                    flags.append(_flag("structure_differs", "warn", "same symbols, different structure than the crop"))
                    proposals.append(
                        _proposal("native_latex", "latex", native.latex, "native conversion of the crop", "low")
                    )
                else:
                    flags.append(_flag("crop_agrees", "info", "native conversion of the crop agrees after folding"))
    return flags, proposals, ("accept", "correct", "reject", "uncertain")


def math_items(
    sample: Mapping[str, Any],
    decisions: Mapping[str, Mapping[str, Any]],
    *,
    read_crop: Callable[[str], bytes | None],
    path_allowed: PathAllowed = default_path_allowed,
) -> tuple[list[dict[str, Any]], int]:
    items: list[dict[str, Any]] = []
    withheld = 0
    for entry in sample.get("samples", []) or []:
        relpath = str(entry.get("relpath", ""))
        if not path_allowed(relpath):
            withheld += 1
            continue
        sample_id = str(entry["sample_id"])
        crop = (entry.get("crop") or {}).get("path")
        crop_bytes = read_crop(str(crop)) if crop and entry.get("source_kind") == "omml_exact" else None
        flags, proposals, allowed = math_checks(entry, crop_bytes)
        crop_rel = PureWindowsPath(str(crop)).as_posix() if crop else ""
        items.append(
            _item(
                f"math:{sample_id}",
                "math",
                f"{sample_id} · {entry.get('source_group', entry.get('source_kind'))} · {entry.get('difficulty_tag')}",
                {
                    "latex": entry.get("latex"),
                    "source_kind": entry.get("source_kind"),
                    "source_group": entry.get("source_group"),
                    "difficulty_tag": entry.get("difficulty_tag"),
                    "status": entry.get("status"),
                    "crop_representation": (entry.get("crop") or {}).get("representation"),
                },
                flags=flags,
                proposals=proposals,
                attachments=[f"../../../{crop_rel}"] if crop_rel else [],
                source={"relpath": relpath, "page": entry.get("page")},
                prior_decision=decisions.get(sample_id),
                allowed=allowed,
            )
        )
    return items, withheld


def double_check_items(math: Sequence[Mapping[str, Any]], *, fraction: float = 0.10) -> list[dict[str, Any]]:
    """An independent second-pass sample: 10% of all math entries (rounded), drawn only from entries that have
    LaTeX, stratified by difficulty, with its own seed. Items show the LaTeX but not the first-pass decision."""
    eligible = [m for m in math if m["original"].get("latex") is not None]
    target = min(len(eligible), round(len(math) * fraction))
    rng = random.Random(DOUBLE_CHECK_SEED)  # noqa: S311 - reproducible sampling, not security
    by_tag: dict[str, list[Mapping[str, Any]]] = {}
    for m in sorted(eligible, key=lambda m: m["item_id"]):
        by_tag.setdefault(str(m["original"].get("difficulty_tag")), []).append(m)
    for group in by_tag.values():
        rng.shuffle(group)
    chosen: list[Mapping[str, Any]] = []
    while len(chosen) < target:
        for tag in sorted(by_tag):
            if by_tag[tag] and len(chosen) < target:
                chosen.append(by_tag[tag].pop())
    out = []
    for m in sorted(chosen, key=lambda m: m["item_id"]):
        sample_id = m["item_id"].split(":", 1)[1]
        out.append(
            _item(
                f"math_double_check:{sample_id}",
                "math_double_check",
                f"double-check {sample_id}",
                m["original"],
                attachments=m["attachments"],
                source=m["source"],
                allowed=("accept", "correct", "reject", "uncertain"),
            )
        )
    return out


# -- PPTX math (T-P3-07) -----------------------------------------------------------------------------------------

_FUNC = r"(?<![\\A-Za-z])(sin|cos|tan|exp|log|ln|lg|lim|max|min|sup|inf|det|dim|ker|deg|arg)(?![A-Za-z])"
_TILDE_PROSE = re.compile(r"(?:[A-Za-zÄÖÜäöüß]{2,}~+){1,}[A-Za-zÄÖÜäöüß]{2,}")
_TILDE_WORD = re.compile(r"~[A-Za-zÄÖÜäöüß]{3,}~")


def pptx_rows_from_report(markdown: str) -> list[dict[str, str]]:
    """Parse the 'PPTX review sample' table of ``eval/reports/spike_omml_native.md``."""
    _, _, tail = markdown.partition("## PPTX review sample")
    rows = []
    for line in tail.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        if len(cells) != 6 or cells[0] in ("relpath", "---") or set(cells[0]) <= {"-"}:
            continue
        relpath, slide, part, number, latex, exact = cells
        rows.append(
            {
                "relpath": relpath,
                "slide": slide,
                "part": part,
                "number": number,
                "latex": latex.strip("`"),
                "exact": exact,
            }
        )
    return rows


def pptx_checks(latex: str) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    flags: list[dict[str, str]] = []
    suggestion = latex
    if _TILDE_PROSE.search(latex) or _TILDE_WORD.search(latex):
        flags.append(_flag("prose_as_math", "warn", "words joined by '~' render as italic math, not text"))
        suggestion = _TILDE_PROSE.sub(lambda m: r"\text{" + m.group(0).replace("~", " ") + "}", suggestion)
    if re.search(_FUNC, latex):
        flags.append(_flag("function_not_operator", "warn", "function name typeset as variables (min, ln, det ...)"))
        suggestion = re.sub(_FUNC, lambda m: "\\" + m.group(1) + " ", suggestion)
    stripped = latex.replace("{", "").replace("}", "").replace("~", "").strip()
    if len(stripped) <= 2 or (stripped.startswith("\\") and " " not in stripped and len(stripped) < 8):
        flags.append(_flag("fragment", "info", "very short: possibly one piece of an equation split across objects"))
    if not _balanced(latex):
        flags.append(_flag("unbalanced_braces", "error", "braces do not balance"))
    proposals = []
    if suggestion != latex:
        proposals.append(
            _proposal(
                "converter_v2_rules",
                "latex",
                " ".join(suggestion.split()),
                "the converter's prose/function rules (2026-11-04) applied to this string; re-run "
                "tools/spike_omml.py --native-latex on the Mac for the authoritative output",
                "medium",
            )
        )
    return flags, proposals


def pptx_items(
    rows: Sequence[Mapping[str, str]], *, path_allowed: PathAllowed = default_path_allowed
) -> tuple[list[dict[str, Any]], int]:
    items: list[dict[str, Any]] = []
    withheld = 0
    seen: Counter[str] = Counter(r["latex"] for r in rows)
    for row in rows:
        if not path_allowed(row["relpath"]):
            withheld += 1
            continue
        key = f"{row['relpath']}|{row['slide']}|{row['part']}|{row['number']}"
        item_id = "pptx:" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
        flags, proposals = pptx_checks(row["latex"])
        if seen[row["latex"]] > 1:
            flags.append(_flag("repeated", "info", f"same LaTeX appears {seen[row['latex']]}x in the sample"))
        items.append(
            _item(
                item_id,
                "pptx",
                f"slide {row['slide']} · {row['part']} #{row['number']}",
                {"latex": row["latex"], "exact": row["exact"]},
                flags=flags,
                proposals=proposals,
                source={"relpath": row["relpath"], "slide": row["slide"], "part": row["part"]},
            )
        )
    return items, withheld


# -- taxonomy (T-P5-06) ------------------------------------------------------------------------------------------


def taxonomy_items(taxonomy: Mapping[str, Any], course_map: Mapping[str, Any]) -> list[dict[str, Any]]:
    concepts = {c["concept_id"]: c for c in taxonomy.get("concepts", [])}
    courses = list(course_map.get("courses", []))
    used = Counter(d for c in courses for d in c.get("domains", []))
    items: list[dict[str, Any]] = []
    labels = {cid: str(c.get("label_de", "")) for cid, c in concepts.items()}
    for cid, concept in sorted(concepts.items()):
        flags: list[dict[str, str]] = []
        broader = concept.get("broader", []) or []
        if len(broader) > 1:
            flags.append(_flag("multiple_parents", "info", f"poly-hierarchy: {', '.join(broader)}"))
        if not broader and not used[cid]:
            flags.append(_flag("root_unused", "info", "root domain: no course maps to it directly (only via children)"))
        elif not used[cid] and not concept.get("narrower"):
            flags.append(_flag("leaf_unused", "warn", "leaf concept that no course uses"))
        de, en = str(concept.get("label_de", "")), str(concept.get("label_en", ""))
        if de.casefold() == en.casefold():
            flags.append(_flag("label_not_translated", "warn", "German and English labels are identical"))
        if de[:1].islower():
            flags.append(_flag("label_lowercase", "warn", "German label starts lowercase"))
        for other, other_label in labels.items():
            if other > cid and difflib.SequenceMatcher(None, de.casefold(), other_label.casefold()).ratio() >= 0.8:
                flags.append(_flag("similar_label", "warn", f"German label close to {other!r} ({other_label})"))
        items.append(
            _item(
                f"taxonomy:concept:{cid}",
                "taxonomy",
                f"concept {cid}",
                {k: concept.get(k) for k in ("label_de", "label_en", "broader", "narrower", "related")},
                flags=flags,
            )
        )
    for course in courses:
        flags = []
        domains = course.get("domains", []) or []
        if len(domains) > 1:
            flags.append(_flag("multiple_domains", "warn", f"mapped to {len(domains)} concepts: {', '.join(domains)}"))
        for d in domains:
            if concepts.get(d, {}).get("narrower"):
                flags.append(_flag("non_leaf_mapping", "warn", f"{d!r} has narrower concepts; is a leaf meant?"))
            if d not in concepts:
                flags.append(_flag("unknown_concept", "error", f"{d!r} is not in taxonomy.yaml"))
        items.append(
            _item(
                f"taxonomy:course:{course['course_id']}",
                "taxonomy",
                f"{course['course_id']} {course.get('name', '')}",
                {
                    "name": course.get("name"),
                    "domains": domains,
                    "domain_labels_de": [labels.get(d) for d in domains],
                },
                flags=flags,
            )
        )
    items.append(
        _item(
            "taxonomy:approve-v0",
            "taxonomy",
            "Approve Taxonomy v0 as a whole",
            {"concepts": len(concepts), "courses": len(courses)},
            flags=[_flag("gate", "info", "accept only after reviewing the concept and course items")],
            allowed=("accept", "reject", "uncertain"),
            priority=2,
        )
    )
    return items


def attach_proposals(items: Sequence[dict[str, Any]], notes: Mapping[str, Any]) -> list[str]:
    """Attach externally authored proposals (e.g. an AI review file) to their target items, keeping their own origin.
    Returns the targets that do not exist in ``items`` (reported, not silently dropped)."""
    by_id = {i["item_id"]: i for i in items}
    origin = str(notes.get("origin", "unknown"))
    missing = []
    for raw in notes.get("proposals", []) or []:
        item = by_id.get(str(raw["target"]))
        if item is None:
            missing.append(str(raw["target"]))
            continue
        proposal = _proposal(str(raw["proposal_id"]), str(raw["field"]), raw["value"], str(raw["rationale"]),
                             str(raw["confidence"]))  # fmt: skip
        proposal["origin"] = origin
        item["proposals"].append(proposal)
    return missing


# -- bundle ------------------------------------------------------------------------------------------------------


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def make_bundle(items: Iterable[Mapping[str, Any]], *, withheld: Mapping[str, int] | None = None) -> dict[str, Any]:
    ordered = sorted((dict(i) for i in items), key=lambda i: (SECTIONS.index(i["kind"]), i["priority"], i["item_id"]))
    ids = [i["item_id"] for i in ordered]
    if len(ids) != len(set(ids)):
        raise ReviewError("duplicate item ids in bundle")
    counts = Counter(i["kind"] for i in ordered)
    return {
        "schema": BUNDLE_SCHEMA,
        "fingerprint": "sha256:" + hashlib.sha256(_canonical(ordered)).hexdigest(),
        "sections": {s: counts.get(s, 0) for s in SECTIONS},
        "withheld_for_sensitivity": dict(withheld or {}),
        "items": ordered,
    }


@dataclass(frozen=True, slots=True)
class Decision:
    item_id: str
    decision: str
    corrected: Any
    note: str
    proposal_id: str | None


def validate_decisions(bundle: Mapping[str, Any], doc: Mapping[str, Any]) -> list[Decision]:
    """Validate an exported decisions file against ``bundle``. All-or-nothing: any problem raises."""
    if doc.get("schema") != DECISIONS_SCHEMA:
        raise ReviewError(f"not a decisions file (schema {doc.get('schema')!r})")
    if doc.get("bundle_fingerprint") != bundle.get("fingerprint"):
        raise ReviewError("decisions were made on a different bundle (fingerprint mismatch); rebuild and re-review")
    items = {i["item_id"]: i for i in bundle["items"]}
    problems: list[str] = []
    out: list[Decision] = []
    seen: set[str] = set()
    for raw in doc.get("decisions", []):
        item_id = str(raw.get("item_id", ""))
        decision = str(raw.get("decision", "")).strip()
        if item_id in seen:
            problems.append(f"{item_id}: duplicate decision")
            continue
        seen.add(item_id)
        item = items.get(item_id)
        if item is None:
            problems.append(f"{item_id}: unknown item")
            continue
        if decision not in item["allowed_decisions"]:
            problems.append(f"{item_id}: {decision!r} not allowed (allowed: {', '.join(item['allowed_decisions'])})")
            continue
        corrected = raw.get("corrected")
        proposal_id = raw.get("proposal_id") or None
        if proposal_id is not None:
            match = [p for p in item["proposals"] if p["proposal_id"] == proposal_id]
            if not match:
                problems.append(f"{item_id}: unknown proposal {proposal_id!r}")
                continue
            if decision != "correct":
                problems.append(f"{item_id}: adopting a proposal is a 'correct' decision")
                continue
            if corrected in (None, ""):
                corrected = match[0]["value"]
        if decision == "correct" and corrected in (None, ""):
            problems.append(f"{item_id}: 'correct' needs the corrected value")
            continue
        if decision != "correct" and corrected not in (None, ""):
            problems.append(f"{item_id}: a corrected value is only valid with 'correct'")
            continue
        out.append(Decision(item_id, decision, corrected, str(raw.get("note", "") or ""), proposal_id))
    if problems:
        raise ReviewError("decisions refused, nothing recorded: " + "; ".join(problems))
    return out


class ReviewLedger:
    """Append-only JSONL ledger of owner review decisions (one file, git-ignored, corpus-derived)."""

    def __init__(self, path: Path, config: SbrConfig | None = None) -> None:
        self.path = path
        self.config = config  # when given, every write target passes assert_writable (docs/22 §1)

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def latest(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for record in self.records():
            out[record["item_id"]] = record
        return out

    def record(
        self,
        bundle: Mapping[str, Any],
        decisions: Sequence[Decision],
        *,
        reviewer: str,
        decided_at: datetime,
        allow_supersede: bool = False,
    ) -> dict[str, int]:
        """Append validated decisions. Identical re-imports are skipped; changes need ``allow_supersede``."""
        if not _REVIEWER_RE.match(reviewer):
            raise ReviewError("reviewer must be given explicitly as 'user:<name>' (e.g. user:owner)")
        latest = self.latest()
        new: list[dict[str, Any]] = []
        unchanged = 0
        conflicts = []
        for d in decisions:
            prev = latest.get(d.item_id)
            if prev and prev["decision"] == d.decision and prev.get("corrected") == d.corrected:
                unchanged += 1
                continue
            if prev and not allow_supersede:
                conflicts.append(f"{d.item_id} ({prev['decision']} -> {d.decision})")
                continue
            body = {
                "item_id": d.item_id,
                "decision": d.decision,
                "corrected": d.corrected,
                "note": d.note,
                "proposal_id": d.proposal_id,
                "reviewer": reviewer,
                "decided_at": decided_at.isoformat(),
                "bundle_fingerprint": bundle["fingerprint"],
                "supersedes": prev["record_id"] if prev else None,
            }
            body["record_id"] = "rev_" + hashlib.sha256(_canonical(body)).hexdigest()[:16]
            new.append(body)
        if conflicts:
            raise ReviewError("already decided differently (pass allow_supersede to change): " + ", ".join(conflicts))
        if self.config is not None:
            assert_writable(self.path.resolve(), self.config)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            for body in new:
                stream.write(json.dumps(body, sort_keys=True, ensure_ascii=False) + "\n")
        return {"recorded": len(new), "unchanged": unchanged}


def progress(bundle: Mapping[str, Any], ledger: ReviewLedger) -> dict[str, dict[str, int]]:
    latest = ledger.latest()
    out: dict[str, dict[str, int]] = {}
    for item in bundle["items"]:
        section = out.setdefault(item["kind"], {"items": 0, "pending": 0, **{d: 0 for d in DECISIONS}})
        section["items"] += 1
        record = latest.get(item["item_id"])
        section[record["decision"] if record else "pending"] += 1
    return out


def gold_log_rows(ledger: ReviewLedger, kind: str) -> dict[str, dict[str, Any]]:
    """Rows in the existing verify-tool log format (``sample_id``, ``decision``, ``note``, ``verified_at`` …) for
    ``kind`` in {"layout", "math"}. ``uncertain`` stays pending there (the existing logs have no such state)."""
    rows: dict[str, dict[str, Any]] = {}
    for item_id, record in ledger.latest().items():
        prefix, _, sample_id = item_id.partition(":")
        if prefix != kind or record["decision"] == "uncertain":
            continue
        row: dict[str, Any] = {
            "sample_id": sample_id,
            "decision": record["decision"],
            "note": record["note"],
            "verified_at": record["decided_at"],
            "reviewer": record["reviewer"],
            "review_record": record["record_id"],
        }
        if record["decision"] == "correct":
            row["corrected_latex" if kind == "math" else "corrected_annotation"] = record["corrected"]
        rows[sample_id] = row
    return rows


def read_crop_under(base: Path) -> Callable[[str], bytes | None]:
    """Crop reader for gold-file crop paths (stored Windows-style, relative to the repository root)."""

    def read(crop: str) -> bytes | None:
        path = base / PureWindowsPath(crop).as_posix()
        return path.read_bytes() if path.is_file() else None

    return read
