"""CI-like local check, cross-platform twin of tools/check.ps1 (T-P1-01): lint, format, types, tests, plan, crossrefs.

Usage: python tools/check.py [--offline]     (exit 0 = CHECK GREEN)
Runs the same steps as check.ps1 through `uv run --frozen`, so it works on macOS/Linux hosts without PowerShell.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STEPS: list[tuple[str, list[str]]] = [
    ("ruff check", ["ruff", "check", "src", "tests"]),
    ("ruff format", ["ruff", "format", "--check", "src", "tests"]),
    ("mypy", ["mypy"]),
    ("pytest", ["pytest", "-q"]),
    ("validate_plan", ["python", "tools/validate_plan.py"]),
    ("audit_crossrefs", ["python", "tools/audit_crossrefs.py"]),
]


def _uv() -> str:
    found = shutil.which("uv")
    if found:
        return found
    if os.name == "nt":  # the Windows user-site install documented in CLAUDE.md
        candidate = Path(os.environ.get("APPDATA", "")) / "Python" / "Python314" / "Scripts" / "uv.exe"
        if candidate.is_file():
            return str(candidate)
    raise SystemExit("uv not found (install: python -m pip install --user uv)")


def main(argv: list[str]) -> int:
    uv = _uv()
    run = [uv, "run", "--frozen", *(["--offline"] if "--offline" in argv else [])]
    failed = []
    for name, args in STEPS:
        print(f"==> {name}", flush=True)
        if subprocess.run([*run, *args], cwd=ROOT, check=False).returncode != 0:
            failed.append(name)
    if failed:
        print(f"CHECK FAILED: {', '.join(failed)}")
        return 1
    print("CHECK GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
