"""Verify a completed quarantine and write the lightweight t3 baseline.

This script reads source/quarantine files and writes only audit outputs.
It does not move, restore, delete, or modify source files.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import pathlib
import stat
from collections import Counter, defaultdict

PROJECT = pathlib.Path(r"D:\AgenticAI\second-brain-rag")
BASE = PROJECT / "audit" / "dedup_quarantine"
T2 = PROJECT / "audit" / "phase0" / "t2"
T3 = PROJECT / "audit" / "phase0" / "t3"
ROOT = pathlib.Path(r"D:\MBI-BRAIN")
QUAR = pathlib.Path(r"D:\studium_duplicated")


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(8 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_csv(p: pathlib.Path) -> list[dict[str, str]]:
    with p.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def inventory(root: pathlib.Path) -> list[dict]:
    rows = []
    stack = [root]
    while stack:
        directory = stack.pop()
        with os.scandir(directory) as entries:
            for e in entries:
                if e.is_dir(follow_symlinks=False):
                    stack.append(pathlib.Path(e.path))
                    continue
                s = e.stat(follow_symlinks=False)
                rel = os.path.relpath(e.path, root)
                rows.append({"relpath": rel, "ext": os.path.splitext(e.name)[1].lower(), "size": s.st_size,
                             "mtime": int(s.st_mtime), "depth": rel.count(os.sep)})
    rows.sort(key=lambda r: r["relpath"])
    return rows


def save_csv(p: pathlib.Path, rows: list[dict], fields: list[str]) -> None:
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def stats(rows: list[dict]) -> dict:
    byext = defaultdict(lambda: [0, 0])
    top = defaultdict(lambda: [0, 0])
    for r in rows:
        byext[r["ext"]][0] += 1; byext[r["ext"]][1] += int(r["size"])
        key = r["relpath"].split("\\")[0]
        top[key][0] += 1; top[key][1] += int(r["size"])
    return {"files": len(rows), "bytes": sum(int(r["size"]) for r in rows),
            "pdf_paths": byext[".pdf"][0],
            "by_ext": {k: {"files": v[0], "bytes": v[1]} for k,v in sorted(byext.items())},
            "top_level": {k: {"files": v[0], "bytes": v[1]} for k,v in sorted(top.items())}}


def main() -> None:
    state = json.loads((BASE / "DEDUP_EXECUTION_STATE.json").read_text(encoding="utf-8"))
    if state["phase"] != "EXECUTION_COMPLETE":
        raise RuntimeError("execution is not complete; refusing t3 baseline")
    plan = load_csv(BASE / "DEDUP_MOVE_PLAN.csv")
    rollback = load_csv(BASE / "DEDUP_ROLLBACK.csv")
    moved = [r for r in plan if r["move_status"] == "MOVED" and r["verification_status"] == "VERIFIED"]
    if len(moved) != state["successfully_moved"] or len(moved) != len(rollback):
        raise RuntimeError("move/rollback/state counts disagree")
    rollpaths = {r["original_path"] for r in rollback}
    if len(rollpaths) != len(rollback) or {r["duplicate_path"] for r in moved} != rollpaths:
        raise RuntimeError("rollback coverage is incomplete")
    canhash = {}
    for i, r in enumerate(moved, 1):
        original = pathlib.Path(r["duplicate_path"])
        dest = pathlib.Path(r["quarantine_path"])
        canonical = pathlib.Path(r["canonical_path"])
        for base, p in ((QUAR,dest),(ROOT,original),(ROOT,canonical)):
            realbase = os.path.normcase(os.path.realpath(base))
            realp = os.path.normcase(os.path.realpath(p))
            if os.path.commonpath((realbase,realp)) != realbase or realp == realbase:
                raise RuntimeError("out-of-root plan path")
        if original.exists() or not dest.is_file() or not canonical.is_file():
            raise RuntimeError("source/destination/canonical existence mismatch")
        sz = int(r["size_bytes"])
        if dest.stat().st_size != sz or canonical.stat().st_size != sz or sha256(dest) != r["execution_hash"]:
            raise RuntimeError("destination size/hash mismatch")
        if r["canonical_path"] not in canhash:
            canhash[r["canonical_path"]] = sha256(canonical)
        if canhash[r["canonical_path"]] != r["execution_hash"]:
            raise RuntimeError("canonical hash mismatch")
        if i % 500 == 0:
            print(f"postverify {i}/{len(moved)}", flush=True)
    source_rows = inventory(ROOT)
    quarantine_rows = inventory(QUAR)
    old = load_csv(T2 / "inventory_t2.csv")
    oldset = {r["relpath"] for r in old}
    newset = {r["relpath"] for r in source_rows}
    movedrel = {str(pathlib.PureWindowsPath(r["duplicate_path"]).relative_to(pathlib.PureWindowsPath(ROOT))) for r in moved}
    quarset = {r["relpath"] for r in quarantine_rows}
    if newset != oldset - movedrel:
        raise RuntimeError(f"unexpected source path changes: extra={len(newset-(oldset-movedrel))}, missing={len((oldset-movedrel)-newset)}")
    if quarset != movedrel:
        raise RuntimeError(f"quarantine path set differs from moved manifest: extra={len(quarset-movedrel)}, missing={len(movedrel-quarset)}")
    newsize = sum(r["size"] for r in source_rows)
    oldsize = sum(int(r["size"]) for r in old)
    movedbytes = sum(int(r["size_bytes"]) for r in moved)
    if oldsize - newsize != movedbytes or sum(r["size"] for r in quarantine_rows) != movedbytes:
        raise RuntimeError("source/quarantine byte reconciliation failed")
    T3.mkdir(parents=True, exist_ok=True)
    save_csv(T3 / "inventory_t3.csv", source_rows, ["relpath", "ext", "size", "mtime", "depth"])
    save_csv(BASE / "inventory_quarantine.csv", quarantine_rows, ["relpath", "ext", "size", "mtime", "depth"])
    s3 = stats(source_rows)
    (T3 / "stats_t3.json").write_text(json.dumps(s3, ensure_ascii=False, indent=2), encoding="utf-8")
    hs = load_csv(T2 / "hashes_t2.csv")
    groups = defaultdict(int)
    for r in hs:
        if r["mode"] == "full" and r["relpath"] in newset:
            groups[(r["hash"],r["size"])] += 1
    remaining_exact = sum(n-1 for n in groups.values() if n>1)
    comparison = {"t2_files": len(old), "t2_bytes": oldsize, "t3_files":len(source_rows), "t3_bytes":newsize,
                  "intentional_moved_files":len(moved), "intentional_moved_bytes":movedbytes,
                  "added_paths_unexpected":0, "missing_paths_unexpected":0,
                  "remaining_exact_redundant_paths_from_t2_full_hashes": remaining_exact,
                  "method_note":"Remaining exact count reuses t2 full hashes for retained paths; moved-group canonical bytes were reverified."}
    (T3 / "t2_to_t3_comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {"planned":len(plan), "moved":len(moved), "bytes_moved":movedbytes, "verified_after_move":len(moved),
               "rollback_records":len(rollback), "canonical_paths_reverified":len(canhash),
               "skipped":state["skipped"], "failed":state["failed"], "restored_after_failure":state["restored_after_failure"],
               "quarantine_files":len(quarantine_rows), "quarantine_bytes":sum(r["size"] for r in quarantine_rows),
               "partial_hash_candidates_moved":0, "source_files_deleted":0,
               "postverification":"PASS"}
    (T3 / "quarantine_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    state["phase"] = "POSTVERIFIED_COMPLETE"
    (BASE / "DEDUP_EXECUTION_STATE.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"t3_files":len(source_rows), "t3_bytes":newsize, "moved":len(moved), "bytes_moved":movedbytes,
                      "remaining_exact_redundant_paths":remaining_exact, "postverification":"PASS"}))


if __name__ == "__main__":
    main()
