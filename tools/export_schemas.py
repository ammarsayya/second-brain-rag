"""Write the core JSON Schemas to schemas/ (T-P1-05). Usage: uv run python tools/export_schemas.py [--check]"""
from __future__ import annotations

import sys
from pathlib import Path

from sbr.schemas.export import render_schemas

OUT = Path(__file__).resolve().parent.parent / "schemas"


def main() -> int:
    rendered = render_schemas()
    if "--check" in sys.argv[1:]:
        stale = [n for n, t in rendered.items() if not (OUT / n).exists() or (OUT / n).read_text(encoding="utf-8") != t]
        extra = sorted(p.name for p in OUT.glob("*.json") if p.name not in rendered)
        for n in stale + extra:
            print("stale:", n)
        return 1 if stale or extra else 0
    OUT.mkdir(exist_ok=True)
    for name, text in rendered.items():
        (OUT / name).write_text(text, encoding="utf-8", newline="\n")
        print("wrote", f"schemas/{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
