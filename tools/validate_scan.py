"""Read-only local validation of the S1 scanner against a real corpus.

JSON is written to stdout for automation; a one-line human summary is written to
stderr.  The temporary registry and logs live outside the corpus and are removed
automatically.  This script deliberately uses ``os.walk`` only for the independent
comparison; production scanning remains exclusively behind SourceFS.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from sbr.config import config_from_mapping, load_config, resolve_config_path
from sbr.db.registry import RegistryDB
from sbr.registry.scan import scan_root

MAX_SECONDS = 300.0


def _is_link_or_reparse(path: str) -> bool:
    st = os.lstat(path)
    attrs = getattr(st, "st_file_attributes", 0)
    return stat.S_ISLNK(st.st_mode) or bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _tree_signal(root: Path) -> list[tuple[str, str, int, int]]:
    """Cheap aggregate signal: root and immediate children metadata, never file content."""
    rows: list[tuple[str, str, int, int]] = []
    root_stat = root.stat()
    rows.append((".", "dir", 0, root_stat.st_mtime_ns))
    with os.scandir(root) as entries:
        for entry in entries:
            st = entry.stat(follow_symlinks=False)
            kind = (
                "link" if _is_link_or_reparse(entry.path) else "dir" if entry.is_dir(follow_symlinks=False) else "file"
            )
            rows.append((entry.name, kind, st.st_size, st.st_mtime_ns))
    return sorted(rows)


def _independent_count(root: Path) -> tuple[int, list[str]]:
    count = 0
    errors: list[str] = []

    def onerror(exc: OSError) -> None:
        errors.append(type(exc).__name__)

    for current, directories, files in os.walk(root, topdown=True, followlinks=False, onerror=onerror):
        kept: list[str] = []
        for name in directories:
            try:
                if not _is_link_or_reparse(os.path.join(current, name)):
                    kept.append(name)
            except OSError as exc:
                errors.append(type(exc).__name__)
        directories[:] = sorted(kept)
        for name in sorted(files):
            path = os.path.join(current, name)
            try:
                if not _is_link_or_reparse(path) and stat.S_ISREG(os.lstat(path).st_mode):
                    count += 1
            except OSError as exc:
                errors.append(type(exc).__name__)
    return count, errors


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the read-only scanner against an independent os.walk.")
    parser.add_argument("--corpus", type=Path, help="Corpus directory (otherwise use --config and a configured root).")
    parser.add_argument("--config", type=Path, help="sbr TOML config, used when --corpus is omitted.")
    parser.add_argument("--root", help="Configured source-root id (required when the config has multiple roots).")
    return parser.parse_args()


def _configured_target(args: argparse.Namespace, temp: Path) -> tuple[Any, str, Path]:
    if args.corpus is not None:
        # Lexical absolute form first: do not touch a candidate until config protected-root checks have accepted it.
        corpus = Path(os.path.abspath(args.corpus))
        safety_path = args.config or resolve_config_path()
        if not safety_path.is_file():
            safety_path = Path(__file__).resolve().parents[1] / "config" / "sbr.example.toml"
        safety_config = load_config(safety_path)
        config = config_from_mapping(
            {
                "roots": {
                    "sources": [{"id": "validation", "path": str(corpus)}],
                    "var": str(temp / "var"),
                    "curation": str(temp / "curation"),
                    "protected": safety_config.roots.protected,
                }
            },
            origin="validate_scan --corpus",
        )
        return config, "validation", corpus
    config = load_config(args.config)
    if args.root is None and len(config.roots.sources) != 1:
        raise ValueError("--root is required when the configuration has multiple source roots")
    root_id = args.root or config.roots.sources[0].id
    return config, root_id, Path(config.source_root(root_id).path)


def _require_directory(path: Path) -> None:
    if not path.is_dir():
        raise NotADirectoryError(str(path))


def main() -> int:
    args = _arguments()
    started = time.perf_counter()
    result: dict[str, object]
    try:
        with tempfile.TemporaryDirectory(prefix="sbr-scan-validation-") as raw_temp:
            config, root_id, corpus = _configured_target(args, Path(raw_temp))
            _require_directory(corpus)
            before = _tree_signal(corpus)
            with RegistryDB.open(config) as db:
                db.migrate()
                scan_started = time.perf_counter()
                record = scan_root(config, db, root_id)
                scan_elapsed = time.perf_counter() - scan_started
            independent_started = time.perf_counter()
            independent_count, independent_errors = _independent_count(corpus)
            independent_elapsed = time.perf_counter() - independent_started
            unchanged = before == _tree_signal(corpus)
            ok = (
                record.status.value == "completed"
                and record.errors == 0
                and not independent_errors
                and record.files_seen == independent_count
                and unchanged
                and scan_elapsed <= MAX_SECONDS
            )
            result = {
                "ok": ok,
                "exit_status": 0 if ok else 1,
                "root_id": root_id,
                "scan_id": record.scan_id,
                "scan_status": record.status.value,
                "scanner_files": record.files_seen,
                "independent_files": independent_count,
                "counts_match": record.files_seen == independent_count,
                "scan_errors": record.errors,
                "independent_errors": independent_errors,
                "source_aggregate_unchanged": unchanged,
                "scan_elapsed_seconds": round(scan_elapsed, 6),
                "independent_elapsed_seconds": round(independent_elapsed, 6),
                "elapsed_seconds": round(time.perf_counter() - started, 6),
                "limit_seconds": MAX_SECONDS,
            }
    except BaseException as exc:
        error = "KeyboardInterrupt" if isinstance(exc, KeyboardInterrupt) else type(exc).__name__
        result = {
            "ok": False,
            "exit_status": 1,
            "error": error,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "limit_seconds": MAX_SECONDS,
        }

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    print(
        "scan validation: "
        + ("PASS" if result["ok"] else "FAIL")
        + f"; scanner={result.get('scanner_files', '?')} independent={result.get('independent_files', '?')}"
        + f" elapsed={result['elapsed_seconds']}s",
        file=sys.stderr,
    )
    return int(result["exit_status"])


if __name__ == "__main__":
    raise SystemExit(main())
