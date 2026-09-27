"""Prepare and record owner review for the local MBI-Gold-Math candidate set.

``--prepare`` writes one offline HTML page pairing every local crop/source substitute with a rendered formula.
If a local KaTeX distribution is supplied, it is referenced directly; otherwise pandoc embeds MathML and the
page labels that fallback explicitly.  ``--record`` writes owner decisions to a separate YAML log.  A
``pending_ai_draft`` entry cannot be accepted because it has no LaTeX to verify.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from sbr.config import load_config
from sbr.safety import assert_writable

DEFAULT_SAMPLE = Path("eval/gold/math_sample.yaml")
DEFAULT_REVIEW_DIR = Path("eval/gold/math/review")
DEFAULT_DECISIONS = Path("eval/gold/math/math_verification.yaml")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare or record owner review of MBI-Gold-Math candidates.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--record", metavar="SAMPLE_ID")
    parser.add_argument("--decision", choices=("accept", "correct", "reject"))
    parser.add_argument("--note", default="")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--review-dir", type=Path, default=DEFAULT_REVIEW_DIR)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument(
        "--katex-dir",
        type=Path,
        help="Optional local KaTeX dist directory containing katex.min.js and katex.min.css; never fetched.",
    )
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
    return {str(row["sample_id"]): row for row in _load_yaml(path).get("decisions", [])}


def _mathml(latex: str, *, display: bool) -> str:
    delimiter = "$$" if display else "$"
    source = f"{delimiter}{latex}{delimiter}"
    try:
        result = subprocess.run(
            ["pandoc", "-f", "markdown", "-t", "html5", "--math-method=mathml"],
            input=source,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return f"<code>{html.escape(latex)}</code>"
    return result.stdout.strip() if result.returncode == 0 else f"<code>{html.escape(latex)}</code>"


def _relative_uri(target: Path, base: Path) -> str:
    return Path(os.path.relpath(target.resolve(), base.resolve())).as_posix()


def _prepare(args: argparse.Namespace, config: Any) -> dict[str, Any]:
    document = _load_yaml(args.sample)
    samples = document.get("samples", [])
    decisions = _existing_decisions(args.decisions)
    args.review_dir.mkdir(parents=True, exist_ok=True)
    use_katex = bool(
        args.katex_dir and (args.katex_dir / "katex.min.js").is_file() and (args.katex_dir / "katex.min.css").is_file()
    )
    renderer = "local KaTeX" if use_katex else "pandoc MathML offline fallback (local KaTeX assets unavailable)"

    katex_head = ""
    katex_script = ""
    if use_katex:
        css_uri = _relative_uri(args.katex_dir / "katex.min.css", args.review_dir)
        js_uri = _relative_uri(args.katex_dir / "katex.min.js", args.review_dir)
        katex_head = f'<link rel="stylesheet" href="{html.escape(css_uri)}">'
        katex_script = f"""
<script src="{html.escape(js_uri)}"></script>
<script>
for (const node of document.querySelectorAll('[data-latex]')) {{
  katex.render(node.dataset.latex, node, {{displayMode: node.dataset.display === 'true', throwOnError: false}});
}}
</script>"""

    cards: list[str] = []
    for entry in samples:
        sample_id = str(entry["sample_id"])
        status = str(entry["status"])
        decision = str(decisions.get(sample_id, {}).get("decision", "pending"))
        crop_path = Path(str(entry["crop"]["path"]))
        if entry["crop"]["representation"] == "cropped_pdf":
            crop_uri = _relative_uri(crop_path, args.review_dir)
            source_view = f'<object class="crop-pdf" data="{html.escape(crop_uri)}" type="application/pdf"></object>'
        else:
            source_view = f"<pre>{html.escape(crop_path.read_text(encoding='utf-8'))}</pre>"

        latex = entry.get("latex")
        if latex is None:
            rendered = '<div class="pending">No LaTeX exists: pending_ai_draft (Q-B04/model gateway).</div>'
        elif use_katex:
            display = str(entry["difficulty_tag"]).startswith("display_")
            rendered = (
                f'<div class="latex-render" data-latex="{html.escape(str(latex), quote=True)}" '
                f'data-display="{str(display).lower()}"></div>'
            )
        else:
            rendered = _mathml(str(latex), display=str(entry["difficulty_tag"]).startswith("display_"))

        command = (
            f"python tools/gold_verify_math.py --config config/sbr.toml --record {sample_id} "
            "--decision accept|correct|reject"
        )
        difficulty = html.escape(str(entry["difficulty_tag"]))
        source_group = html.escape(str(entry["source_group"]))
        latex_text = html.escape(str(latex)) if latex is not None else "null"
        crop_note = html.escape(str(entry["crop"]["note"]))
        cards.append(
            f"""
<section id="{html.escape(sample_id)}">
  <h2>{html.escape(sample_id)} <span>{difficulty}</span></h2>
  <p><b>Status:</b> {html.escape(status)} · <b>owner decision:</b> {html.escape(decision)} ·
     <b>source:</b> {source_group}</p>
  <div class="pair"><div><h3>Source crop/substitute</h3>{source_view}</div>
  <div><h3>Candidate render</h3>{rendered}<pre>{latex_text}</pre></div></div>
  <p class="note">{crop_note}</p>
  <code>{html.escape(command)}</code>
</section>"""
        )

    output = args.review_dir / "index.html"
    assert_writable(output.resolve(), config)
    output.write_text(
        f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>MBI-Gold-Math owner review</title>{katex_head}
<style>
body{{font:16px system-ui,sans-serif;max-width:1500px;margin:auto;padding:2rem;background:#f6f7f9;color:#172033}}
.warning,.pending{{padding:1rem;background:#fff2c7;border-left:5px solid #c48a00}}
section{{background:white;margin:2rem 0;padding:1.2rem;border-radius:10px}}
h2 span{{font-size:.65em;color:#526070}}
.pair{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}
pre{{white-space:pre-wrap;overflow:auto;background:#f1f3f5;padding:1rem}}
.crop-pdf{{width:100%;height:250px;border:1px solid #ccd3db}}
math,.latex-render{{font-size:1.35rem;min-height:4rem;padding:1rem;display:block}}
@media(max-width:900px){{.pair{{grid-template-columns:1fr}}}}
</style></head><body><h1>MBI-Gold-Math owner review</h1>
<div class="warning"><b>Not verified.</b> Review every candidate and separately double-check 10%.
Renderer: {html.escape(renderer)}.
PDF entries with null LaTeX cannot be accepted until the Q-B04/model-gateway draft exists.</div>
{"".join(cards)}{katex_script}</body></html>""",
        encoding="utf-8",
    )
    return {"entries": len(samples), "renderer": renderer, "review_page": str(output)}


def _record(args: argparse.Namespace, config: Any) -> dict[str, Any]:
    if args.decision is None:
        raise ValueError("--decision is required with --record")
    document = _load_yaml(args.sample)
    entries = {str(entry["sample_id"]): entry for entry in document.get("samples", [])}
    if args.record not in entries:
        raise ValueError(f"unknown sample id: {args.record}")
    entry = entries[args.record]
    if entry.get("latex") is None:
        raise ValueError(f"{args.record} is pending_ai_draft and has no LaTeX to verify")
    decisions = _existing_decisions(args.decisions)
    decisions[args.record] = {
        "sample_id": args.record,
        "decision": args.decision,
        "note": args.note,
        "verified_at": datetime.now(UTC).isoformat(),
    }
    output = {
        "purpose": "T-P3-02 owner verification log; completion also requires a separate 10 percent double-check",
        "sample": str(args.sample),
        "decisions": [decisions[key] for key in sorted(decisions)],
    }
    assert_writable(args.decisions.resolve(), config)
    args.decisions.parent.mkdir(parents=True, exist_ok=True)
    _dump_yaml(args.decisions, output)
    counts = {
        decision: sum(row["decision"] == decision for row in decisions.values())
        for decision in ("accept", "correct", "reject")
    }
    return {"recorded": args.record, "decision": args.decision, "counts": counts, "total_entries": len(entries)}


def main() -> int:
    args = _arguments()
    config = load_config(args.config)
    result = _prepare(args, config) if args.prepare else _record(args, config)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
