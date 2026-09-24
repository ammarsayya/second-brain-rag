"""TS-SAFE-2: static scan. No filesystem mutator is called outside the reviewed allow-list, and SourceFS has none.

Any new module that must write files (DB layer, artifact store, logs, vault writer) is added to ``ALLOW`` only after
review, and must call :func:`sbr.safety.assert_writable` on its targets.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "sbr"

MODULE_MUTATORS = {
    "os": {"remove", "unlink", "rmdir", "removedirs", "rename", "renames", "replace", "chmod", "chown", "lchmod",
           "lchown", "utime", "truncate", "link", "symlink", "mkdir", "makedirs", "open", "write"},
    "shutil": {"move", "rmtree", "copy", "copy2", "copyfile", "copytree", "copymode", "copystat", "make_archive",
               "unpack_archive"},
}  # fmt: skip
METHOD_MUTATORS = {"unlink", "rmdir", "rename", "touch", "write_text", "write_bytes", "chmod", "lchmod",
                   "symlink_to", "hardlink_to", "mkdir"}  # fmt: skip

# module (relative to src/sbr) -> reviewed reason
ALLOW: dict[str, str] = {
    "sourcefs.py": "os.open with read-only flags only (asserted below)",
    "safety.py": "the runtime guard wraps mutators; it never calls them itself on its own behalf",
    "db/connection.py": "creates var/db and backup directories after assert_outside(protected roots)",
}


def _is_write_open(call: ast.Call) -> bool:
    mode: ast.expr | None = call.args[1] if len(call.args) > 1 else None
    for kw in call.keywords:
        if kw.arg == "mode":
            mode = kw.value
    if mode is None:
        return False
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return any(c in mode.value for c in "wax+")
    return True  # a non-literal mode cannot be verified statically


def findings(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in MODULE_MUTATORS:
            bad = [a.name for a in node.names if a.name in MODULE_MUTATORS[node.module] or a.name == "*"]
            if bad:
                out.append(f"{path.name}:{node.lineno} from {node.module} import {bad}")
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if isinstance(f, ast.Attribute):
            if isinstance(f.value, ast.Name) and f.value.id in MODULE_MUTATORS:
                if f.attr in MODULE_MUTATORS[f.value.id]:
                    out.append(f"{path.name}:{node.lineno} {f.value.id}.{f.attr}")
            elif f.attr in METHOD_MUTATORS:
                out.append(f"{path.name}:{node.lineno} .{f.attr}()")
            elif f.attr == "open" and _is_write_open(node):
                out.append(f"{path.name}:{node.lineno} .open(write mode)")
        elif isinstance(f, ast.Name) and f.id == "open" and _is_write_open(node):
            out.append(f"{path.name}:{node.lineno} open(write mode)")
    return out


def test_no_mutators_outside_allow_list() -> None:
    problems: list[str] = []
    for py in sorted(SRC.rglob("*.py")):
        rel = py.relative_to(SRC).as_posix()
        if rel in ALLOW:
            continue
        problems += findings(py)
    assert problems == [], "filesystem mutators outside the reviewed allow-list:\n" + "\n".join(problems)


def test_allow_list_entries_exist() -> None:
    for rel in ALLOW:
        assert (SRC / rel).is_file(), rel


def test_sourcefs_only_opens_read_only() -> None:
    src = SRC / "sourcefs.py"
    issues = [f for f in findings(src) if not f.endswith("os.open")]
    assert issues == [], issues
    text = src.read_text(encoding="utf-8")
    assert "O_RDONLY" in text
    for flag in ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND"):
        assert flag not in text, flag


def test_scanner_detects_violations(tmp_path: Path) -> None:
    sample = tmp_path / "bad.py"
    sample.write_text(
        "import os, shutil\nfrom os import remove\nos.remove('x')\nshutil.move('a','b')\n"
        "p.write_text('x')\nopen('f', 'w')\nopen('f')\nq.open(mode='ab')\n",
        encoding="utf-8",
    )
    got = findings(sample)
    assert len(got) == 6, got
