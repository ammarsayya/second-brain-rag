"""Restore quarantined files from the verified rollback ledger.

Dry-run by default. Use exactly one selector with --execute to move files back.
No existing source file is overwritten. All operations are logged locally.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import pathlib
import stat
import sys

ROOT = pathlib.Path(r"D:\MBI-BRAIN")
QUAR = pathlib.Path(r"D:\studium_duplicated")
BASE = pathlib.Path(r"D:\AgenticAI\second-brain-rag\audit\dedup_quarantine")
LEDGER = BASE / "DEDUP_ROLLBACK.csv"
LOG = BASE / "DEDUP_RESTORE_LOG.jsonl"


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for buf in iter(lambda: f.read(8 << 20), b""):
            h.update(buf)
    return h.hexdigest()


def append_log(event: dict) -> None:
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"time": dt.datetime.now(dt.timezone.utc).isoformat(), **event}, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def checked(root: pathlib.Path, absolute: str) -> pathlib.Path:
    p = pathlib.Path(absolute)
    if not p.is_absolute():
        raise ValueError("ledger path is not absolute")
    rr = os.path.normcase(os.path.realpath(root))
    rp = os.path.normcase(os.path.realpath(p))
    if os.path.commonpath((rr, rp)) != rr or rp == rr:
        raise ValueError("ledger path resolves outside expected root")
    rel = p.relative_to(root)
    q = root
    for component in rel.parts:
        q = q / component
        if q.exists() or q.is_symlink():
            st = q.lstat()
            if getattr(st, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
                raise ValueError("reparse point in ledger path")
    return p


def select(rows: list[dict], args: argparse.Namespace) -> list[dict]:
    selectors = sum((args.file is not None, args.group is not None, args.subtree is not None, args.all))
    if selectors > 1 or (args.execute and selectors != 1):
        raise ValueError("choose exactly one of --file, --group, --subtree, --all for execution")
    if args.file:
        target = pathlib.PureWindowsPath(args.file)
        if target.is_absolute() or ".." in target.parts:
            raise ValueError("--file must be a safe source-relative path")
        return [r for r in rows if pathlib.PureWindowsPath(r["original_path"]).relative_to(pathlib.PureWindowsPath(ROOT)) == target]
    if args.group:
        return [r for r in rows if r["group_id"] == args.group]
    if args.subtree:
        target = pathlib.PureWindowsPath(args.subtree)
        if target.is_absolute() or ".." in target.parts:
            raise ValueError("--subtree must be a safe source-relative directory")
        return [r for r in rows if pathlib.PureWindowsPath(r["original_path"]).relative_to(pathlib.PureWindowsPath(ROOT)).parts[:len(target.parts)] == target.parts]
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execute", action="store_true", help="actually restore the selected files")
    sel = ap.add_mutually_exclusive_group()
    sel.add_argument("--file", help="one original source-relative file")
    sel.add_argument("--group", help="one group ID, e.g. g000001")
    sel.add_argument("--subtree", help="one original source-relative directory subtree")
    sel.add_argument("--all", action="store_true", help="all rollback-ledger rows")
    args = ap.parse_args()
    for root in (ROOT, QUAR, BASE):
        if not root.is_dir() or root.resolve() != root:
            raise RuntimeError(f"missing or redirected root: {root}")
    with LEDGER.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    rows = select(rows, args)
    if not args.execute:
        print(f"DRY RUN: selected {len(rows)} verified rollback records; no files moved")
        for r in rows:
            try:
                src = checked(ROOT, r["original_path"])
                dest = checked(QUAR, r["quarantine_path"])
                status = "READY" if dest.is_file() and not src.exists() else "CONFLICT_OR_MISSING"
            except (OSError, ValueError) as e:
                status = type(e).__name__
            append_log({"mode": "DRY_RUN", "group_id": r["group_id"], "status": status})
        return 0
    restored = skipped = failed = 0
    for r in rows:
        try:
            src = checked(ROOT, r["original_path"])
            dest = checked(QUAR, r["quarantine_path"])
            if src.exists():
                raise FileExistsError("original source path already exists; never overwrite")
            if not dest.is_file():
                raise FileNotFoundError("quarantine file missing")
            size = int(r["size_bytes"])
            digest = r["execution_hash"]
            if dest.stat().st_size != size or sha256(dest) != digest:
                raise ValueError("quarantine full hash/size mismatch")
            src.parent.mkdir(parents=True, exist_ok=True)
            src = checked(ROOT, r["original_path"])
            if src.exists():
                raise FileExistsError("original source path appeared; never overwrite")
            os.rename(dest, src)
            if src.stat().st_size != size or sha256(src) != digest:
                # File is now at its original location; preserve it and stop.
                append_log({"mode": "EXECUTE", "group_id": r["group_id"], "status": "POST_RESTORE_HASH_FAILED", "original_path": str(src)})
                raise RuntimeError("restored file hash mismatch; stop and investigate")
            restored += 1
            append_log({"mode": "EXECUTE", "group_id": r["group_id"], "status": "RESTORED_VERIFIED", "original_path": str(src)})
        except (OSError, ValueError) as e:
            skipped += 1
            append_log({"mode": "EXECUTE", "group_id": r["group_id"], "status": "SKIPPED", "error_type": type(e).__name__})
        except RuntimeError:
            failed += 1
            print(f"STOP after restore verification failure; restored={restored} skipped={skipped} failed={failed}", file=sys.stderr)
            return 2
    print(f"RESTORE COMPLETE restored={restored} skipped={skipped} failed={failed}")
    return 0 if not skipped and not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
