"""Reversible exact-copy quarantine. Run preflight, then execute, then verify.

Only file-by-file moves are performed. All source access is read-only except
os.rename(source, quarantine) after a complete, saved SHA-256 preflight.
Historical t2 artifacts are inputs and are never changed.
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
import time
from collections import Counter, defaultdict

ROOT = pathlib.Path(r"D:\MBI-BRAIN")
QUAR = pathlib.Path(r"D:\studium_duplicated")
BASE = pathlib.Path(r"D:\AgenticAI\second-brain-rag\audit\dedup_quarantine")
T2 = pathlib.Path(r"D:\AgenticAI\second-brain-rag\audit\phase0\t2")
PLAN = BASE / "DEDUP_MOVE_PLAN.csv"
KEEP = BASE / "DEDUP_KEEP_MANIFEST.csv"
EXCEPTIONS = BASE / "DEDUP_EXCEPTIONS.csv"
HASHES = BASE / "DEDUP_PREFLIGHT_HASHES.csv"
REPORT = BASE / "DEDUP_PREFLIGHT_REPORT.md"
STATE = BASE / "DEDUP_EXECUTION_STATE.json"
ROLLBACK = BASE / "DEDUP_ROLLBACK.csv"
EVENTS = BASE / "DEDUP_EVENTS.jsonl"
ALLOWED = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".ppsx", ".pps", ".xlsx", ".xls", ".zip", ".rar"}
SENSITIVE = ("ausweis", "reisepass", "personalausweis", "bewerbung", "lebenslauf", "zeugnis", "immatrikulation", "vertrag", "notenliste", "ergebnisliste", "labornoten")
STRUCTURAL = ("\\.metadata\\", "\\bin\\", "\\slprj\\", "\\node_modules\\", "\\__macosx\\", "\\.git\\", "\\src\\", "\\target\\", "\\build\\", "\\site-packages\\")
GENERIC = ("backup", "kopie", "copy", "old", "alt", "temp", "download", "dupl", "mirror")
SEMANTIC = ("vorlesung", "skript", "uebung", "übung", "klausur", "lecture", "semester", "thesis", "aufgaben", "prüfung")
PLAN_FIELDS = "group_id historical_hash historical_hash_mode execution_hash_algorithm execution_hash size_bytes canonical_path duplicate_path quarantine_path canonical_reason preflight_status move_status destination_hash verification_status rollback_status error timestamp".split()
KEEP_FIELDS = "group_id historical_hash execution_hash size_bytes retained_path retention_role reason".split()
EXC_FIELDS = "group_id relative_path category reason timestamp".split()
ROLL_FIELDS = "quarantine_path original_path canonical_path execution_hash size_bytes verified group_id".split()
HASH_FIELDS = "group_id relative_path size_bytes historical_hash historical_hash_mode execution_hash_algorithm execution_hash status error".split()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: pathlib.Path, fields: list[str], rows: list[dict]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
        f.flush()
        os.fsync(f.fileno())
    replace_with_retry(tmp, path)


def replace_with_retry(tmp: pathlib.Path, path: pathlib.Path) -> None:
    # Windows indexers/scanners can briefly hold the destination without delete sharing.
    # Keep the completed temp file and stop if the denial persists.
    for attempt in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.25)


def write_json(path: pathlib.Path, value: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    replace_with_retry(tmp, path)


def log_event(event: dict) -> None:
    with EVENTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"time": now(), **event}, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def check_root() -> None:
    for p in (ROOT, QUAR, BASE, T2):
        if not p.is_dir() or p.resolve() != p:
            raise RuntimeError(f"missing or redirected root: {p}")
        st = p.lstat()
        if getattr(st, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise RuntimeError(f"reparse root: {p}")
    if ROOT.stat().st_dev != QUAR.stat().st_dev:
        raise RuntimeError("source and quarantine are not on the same volume")


def checked_path(root: pathlib.Path, rel: str) -> pathlib.Path:
    # Historical relpaths are Windows paths; never accept an absolute or traversal path.
    if not rel or os.path.isabs(rel) or "/" in rel or any(x in ("", ".", "..") for x in rel.split("\\")):
        raise ValueError("unsafe relative path")
    p = root.joinpath(*rel.split("\\"))
    root_real = os.path.normcase(os.path.realpath(root))
    final_real = os.path.normcase(os.path.realpath(p))
    if os.path.commonpath((root_real, final_real)) != root_real:
        raise ValueError("resolved path outside intended root")
    # Detect junctions, symlinks and other reparse points in every existing component.
    q = root
    for part in rel.split("\\"):
        q = q / part
        if q.exists() or q.is_symlink():
            st = q.lstat()
            if getattr(st, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
                raise ValueError("reparse component")
    return p


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for buf in iter(lambda: f.read(8 << 20), b""):
            h.update(buf)
    return h.hexdigest()


def exclusion(rel: str) -> str:
    parts = rel.split("\\")
    low = rel.casefold()
    ext = os.path.splitext(rel)[1].casefold()
    if parts[0] not in {"BachelorArbeit", "Betriebslehre", "books", "Information", "Mechanical", "English", "Ckurs"}:
        return "unrecognized root/context"
    if parts[0] == "BachelorArbeit":
        return "project/thesis tree retained structurally"
    if ext in (".html", ".htm") or "\\man-pages\\" in low:
        return "reference HTML tree retained structurally"
    if ext not in ALLOWED:
        return "software/media/image or unsupported file class retained structurally"
    if os.path.basename(rel).startswith("._") or "\\__macosx\\" in low:
        return "AppleDouble or macOS sidecar retained"
    if any(token in low for token in STRUCTURAL):
        return "software/build/dependency subtree retained"
    if any(token in low for token in SENSITIVE):
        return "sensitive-name path retained under restricted policy"
    return ""


def bucket(rel: str) -> tuple[str, str]:
    parts = rel.split("\\")
    context = "\\".join(parts[:4]) if len(parts) > 4 else os.path.dirname(rel)
    return context.casefold(), os.path.basename(rel).casefold()


def rank(rel: str, identity: dict[str, str]) -> tuple[int, int, int, str]:
    parts = rel.split("\\")
    semantic = sum(any(token in part.casefold() for token in SEMANTIC) for part in parts[4:-1])
    generic = sum(any(token in part.casefold() for token in GENERIC) for part in parts[4:-1])
    historic = {"A": 3, "C": 2, "D": 1, "B_exact": 0}.get(identity.get(rel), 0)
    # The first priorities are contextual quality and historical continuity.
    # Depth/alphabetical order only resolve ties inside one context+basename bucket.
    return (semantic - 4 * generic, historic, -len(parts), rel.casefold())


def preflight() -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    check_root()
    if PLAN.exists() or STATE.exists() or ROLLBACK.exists():
        raise RuntimeError("existing transaction artifacts; resume/inspect instead of replacing them")
    groups = json.loads((T2 / "dup_groups_exact_t2.json").read_text(encoding="utf-8"))
    summary = json.loads((T2 / "dedup_t2_summary.json").read_text(encoding="utf-8"))
    if len(groups) != 23512 or len(groups) != summary["exact_groups"] or sum(len(g)-1 for g in groups) != summary["exact_redundant_files"]:
        raise RuntimeError("historical group summary mismatch")
    inventory = {r["relpath"]: r for r in load_csv(T2 / "inventory_t2.csv")}
    historical = {r["relpath"]: r for r in load_csv(T2 / "hashes_t2.csv")}
    identity = {r["relpath"]: r["category"] for r in load_csv(T2 / "identity_t2.csv")}
    partial = {r["relpath"] for r in historical.values() if r["mode"] == "partial"}
    hash_rows: list[dict] = []
    plan: list[dict] = []
    keep: list[dict] = []
    exceptions: list[dict] = []
    counts = Counter()
    errors = Counter()
    for index, members in enumerate(groups, 1):
        group_id = f"g{index:06d}"
        if index % 1000 == 0:
            print(f"preflight groups {index}/{len(groups)}; proposed {len(plan)}", flush=True)
        if len(members) != len(set(members)):
            raise RuntimeError(f"repeated path in {group_id}")
        hist_values = {(historical[p]["hash"], historical[p]["size"], historical[p]["mode"]) for p in members if p in historical}
        if len(hist_values) != 1 or len(members) != sum(p in historical for p in members) or next(iter(hist_values))[2] != "full":
            raise RuntimeError(f"group not exclusively historical full-hash: {group_id}")
        old_hash, old_size, _ = next(iter(hist_values))
        fresh: dict[str, str] = {}
        faults: dict[str, str] = {}
        for rel in members:
            try:
                if rel in partial:
                    raise ValueError("partial-hash path in exact group")
                row = inventory[rel]
                if row["size"] != old_size:
                    raise ValueError("inventory/hash size disagreement")
                src = checked_path(ROOT, rel)
                st_before = src.lstat()
                if not stat.S_ISREG(st_before.st_mode):
                    raise ValueError("not a regular file")
                if st_before.st_size != int(old_size):
                    raise ValueError("size changed since t2")
                if int(st_before.st_mtime) != int(row["mtime"]):
                    raise ValueError("mtime changed since t2")
                digest = sha256(src)
                st_after = src.lstat()
                if (st_before.st_size, st_before.st_mtime_ns) != (st_after.st_size, st_after.st_mtime_ns):
                    raise ValueError("file changed during preflight hash")
                fresh[rel] = digest
                status, error = "VERIFIED", ""
            except (OSError, ValueError, KeyError) as e:
                status, error = "EXCEPTION", f"{type(e).__name__}: {str(e)[:180]}"
                faults[rel] = error
                errors[type(e).__name__] += 1
            hash_rows.append({"group_id": group_id, "relative_path": rel, "size_bytes": old_size, "historical_hash": old_hash,
                              "historical_hash_mode": "full", "execution_hash_algorithm": "SHA-256", "execution_hash": fresh.get(rel, ""),
                              "status": status, "error": error})
        if faults or len(set(fresh.values())) != 1:
            counts["groups_failed_preflight"] += 1
            reason = "current group hash mismatch" if not faults else "current member missing/changed/unreadable"
            exceptions.append({"group_id": group_id, "relative_path": "", "category": "GROUP_PREFLIGHT_FAILURE", "reason": reason, "timestamp": now()})
            for rel, error in faults.items():
                exceptions.append({"group_id": group_id, "relative_path": rel, "category": "MEMBER_PREFLIGHT_FAILURE", "reason": error, "timestamp": now()})
            for rel in members:
                keep.append({"group_id": group_id, "historical_hash": old_hash, "execution_hash": fresh.get(rel, ""),
                             "size_bytes": old_size, "retained_path": rel, "retention_role": "EXCEPTION_RETAINED", "reason": reason})
            continue
        digest = next(iter(fresh.values()))
        counts["groups_fresh_verified"] += 1
        choices: dict[tuple[str,str], list[str]] = defaultdict(list)
        for rel in members:
            why = exclusion(rel)
            if why:
                counts["excluded_members"] += 1
                exceptions.append({"group_id": group_id, "relative_path": rel, "category": "STRUCTURAL_OR_POLICY_KEEP", "reason": why, "timestamp": now()})
                keep.append({"group_id": group_id, "historical_hash": old_hash, "execution_hash": digest,
                             "size_bytes": old_size, "retained_path": rel, "retention_role": "POLICY_RETAINED", "reason": why})
            else:
                choices[bucket(rel)].append(rel)
        for context, paths in choices.items():
            canonical = max(paths, key=lambda p: rank(p, identity))
            keep.append({"group_id": group_id, "historical_hash": old_hash, "execution_hash": digest,
                         "size_bytes": old_size, "retained_path": canonical, "retention_role": "CANONICAL", "reason": "same course-context prefix and filename; semantic/history ranking"})
            if len(paths) == 1:
                counts["single_context_members"] += 1
            for rel in paths:
                if rel == canonical:
                    continue
                try:
                    src = checked_path(ROOT, rel)
                    dest = checked_path(QUAR, rel)
                    if len(str(src)) >= 240 or len(str(dest)) >= 240:
                        raise ValueError("conservative Windows path-length limit")
                    if dest.exists():
                        dest_hash = sha256(dest)
                        raise ValueError("destination already exists (identical)" if dest_hash == digest else "destination collision (different bytes)")
                    if not os.access(src, os.R_OK | os.W_OK):
                        raise PermissionError("source lacks effective read/write access")
                    if not os.access(dest.parent if dest.parent.exists() else QUAR, os.W_OK):
                        raise PermissionError("destination parent lacks write access")
                except (OSError, ValueError) as e:
                    counts["candidate_move_exceptions"] += 1
                    reason = f"{type(e).__name__}: {str(e)[:180]}"
                    exceptions.append({"group_id": group_id, "relative_path": rel, "category": "MOVE_PREFLIGHT_SKIP", "reason": reason, "timestamp": now()})
                    keep.append({"group_id": group_id, "historical_hash": old_hash, "execution_hash": digest,
                                 "size_bytes": old_size, "retained_path": rel, "retention_role": "EXCEPTION_RETAINED", "reason": reason})
                    continue
                plan.append({"group_id": group_id, "historical_hash": old_hash, "historical_hash_mode": "full",
                             "execution_hash_algorithm": "SHA-256", "execution_hash": digest, "size_bytes": old_size,
                             "canonical_path": str(ROOT / pathlib.PureWindowsPath(canonical)),
                             "duplicate_path": str(src), "quarantine_path": str(dest),
                             "canonical_reason": "same 4-component course context and identical basename; semantic/history rank; retained source locations in KEEP manifest",
                             "preflight_status": "READY", "move_status": "PLANNED", "destination_hash": "",
                             "verification_status": "PENDING", "rollback_status": "NOT_NEEDED", "error": "", "timestamp": now()})
                counts["planned_bytes"] += int(old_size)
        if any(r["group_id"] == group_id for r in plan):
            counts["groups_with_moves"] += 1
        else:
            counts["groups_without_moves"] += 1
    if any(r["historical_hash_mode"] != "full" for r in plan):
        raise RuntimeError("partial-hash plan entry")
    if len({r["duplicate_path"] for r in plan}) != len(plan) or len({r["quarantine_path"] for r in plan}) != len(plan):
        raise RuntimeError("duplicate source/destination in plan")
    retained = {r["retained_path"] for r in keep}
    for r in plan:
        relcan = str(pathlib.PureWindowsPath(r["canonical_path"]).relative_to(pathlib.PureWindowsPath(ROOT)))
        if relcan not in retained:
            raise RuntimeError("planned group would lose canonical")
    write_csv(HASHES, HASH_FIELDS, hash_rows)
    write_csv(KEEP, KEEP_FIELDS, keep)
    write_csv(EXCEPTIONS, EXC_FIELDS, exceptions)
    write_csv(PLAN, PLAN_FIELDS, plan)
    write_csv(ROLLBACK, ROLL_FIELDS, [])
    state = {"phase": "PREFLIGHT_COMPLETE", "total_planned": len(plan), "processed": 0, "successfully_moved": 0,
             "verified": 0, "skipped": 0, "failed": 0, "restored_after_failure": 0, "remaining": len(plan),
             "bytes_moved": 0, "current_batch": 0, "last_successful_operation": None,
             "start_time": now(), "last_checkpoint_time": now(), "historical_exact_groups_considered": len(groups),
             "preflight_groups_with_moves": counts["groups_with_moves"], "preflight_groups_failed": counts["groups_failed_preflight"]}
    write_json(STATE, state)
    text = f"""# Exact-duplicate quarantine preflight

Generated {now()}. Source `D:\\MBI-BRAIN`; quarantine `D:\\studium_duplicated`. No move had occurred when this report was written.

- Historical full-hash groups considered: **{len(groups):,}** (all {sum(map(len, groups)):,} group members were checked against t2 size/mtime and freshly SHA-256 hashed where readable).
- Groups with every current member freshly verified as identical: **{counts['groups_fresh_verified']:,}**; groups failed closed: **{counts['groups_failed_preflight']:,}**.
- Groups with at least one planned move: **{counts['groups_with_moves']:,}**; groups without a planned move: **{counts['groups_without_moves']:,}**.
- Files planned: **{len(plan):,}**; planned bytes: **{counts['planned_bytes']:,}** ({counts['planned_bytes']/1e9:.3f} decimal GB).
- Retained-file manifest entries: **{len(keep):,}**, including every group canonical and contextual/policy retained copy.
- Policy/structural exclusions: **{counts['excluded_members']:,}** member occurrences; individual proposed-move preflight exceptions: **{counts['candidate_move_exceptions']:,}**.
- Partial-hash candidates excluded: **27 groups / 49 redundant candidate paths / 196,834,535,900 candidate bytes**. No partial-hash path is in `DEDUP_MOVE_PLAN.csv`.
- Hash/read/metadata error types: **{dict(errors)}**. Details are local in `DEDUP_EXCEPTIONS.csv` and `DEDUP_PREFLIGHT_HASHES.csv`.

Automatic moves are limited to exact-byte groups with an identical basename within the same four-component course-context prefix. `BachelorArbeit` project/thesis trees, software/build classes, images/media/code, HTML/man-page trees, sensitive-name paths and cross-context singleton occurrences remain in place. Full-hash-identical archives are eligible only as archive files, never by member resemblance. No group is reduced below one retained source copy. The retained locations and every planned destination are recorded before execution. Existing destinations, reparse points, length/permission issues and metadata/hash changes fail closed.

Execution may start only if the saved plan is internally consistent and there are no systemic failures. Preflight exceptions remain skipped, not silently repaired.
"""
    REPORT.write_text(text, encoding="utf-8")
    print(f"PREFLIGHT COMPLETE groups={len(groups)} ready_groups={counts['groups_with_moves']} planned={len(plan)} bytes={counts['planned_bytes']} failed_groups={counts['groups_failed_preflight']}")


def checkpoint(rows: list[dict], state: dict) -> None:
    state["remaining"] = sum(r["move_status"] == "PLANNED" for r in rows)
    state["last_checkpoint_time"] = now()
    write_csv(PLAN, PLAN_FIELDS, rows)
    write_json(STATE, state)


def execute(batch_size: int) -> None:
    check_root()
    rows = load_csv(PLAN)
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if state["phase"] not in ("PREFLIGHT_COMPLETE", "EXECUTING", "EXECUTION_INTERRUPTED"):
        raise RuntimeError(f"execution not allowed in phase {state['phase']}")
    keep = {r["retained_path"]: r for r in load_csv(KEEP)}
    hist = {r["relpath"]: r for r in load_csv(T2 / "inventory_t2.csv")}
    rollback = load_csv(ROLLBACK)
    rolled_paths = {r["original_path"] for r in rollback}
    state["phase"] = "EXECUTING"
    checkpoint(rows, state)
    batch_count = 0
    for row in rows:
        if row["move_status"] != "PLANNED":
            continue
        rel = str(pathlib.PureWindowsPath(row["duplicate_path"]).relative_to(pathlib.PureWindowsPath(ROOT)))
        canrel = str(pathlib.PureWindowsPath(row["canonical_path"]).relative_to(pathlib.PureWindowsPath(ROOT)))
        move_in_quarantine = False
        try:
            src = checked_path(ROOT, rel)
            can = checked_path(ROOT, canrel)
            dest = checked_path(QUAR, rel)
            digest = row["execution_hash"]
            size = int(row["size_bytes"])
            if canrel not in keep or canrel == rel or not can.is_file() or can.stat().st_size != size or sha256(can) != digest:
                raise ValueError("canonical missing/changed")
            if dest.exists():
                if not src.exists() and sha256(dest) == digest and dest.stat().st_size == size:
                    # Crash after atomic rename: recover journal state without repeating the move.
                    move_in_quarantine = True
                    row.update(move_status="MOVED", destination_hash=digest, verification_status="VERIFIED", error="recovered after interrupted checkpoint", timestamp=now())
                    if row["duplicate_path"] not in rolled_paths:
                        rollback.append({"quarantine_path": str(dest), "original_path": str(src), "canonical_path": str(can),
                                         "execution_hash": digest, "size_bytes": size, "verified": "YES", "group_id": row["group_id"]})
                        write_csv(ROLLBACK, ROLL_FIELDS, rollback)
                        rolled_paths.add(row["duplicate_path"])
                    state["successfully_moved"] += 1; state["verified"] += 1; state["bytes_moved"] += size
                    state["processed"] += 1
                    log_event({"event":"RECOVERED_VERIFIED_MOVE", "group_id": row["group_id"], "path": rel})
                    continue
                raise ValueError("destination already exists; no overwrite")
            if not src.is_file():
                raise FileNotFoundError("source missing")
            st = src.lstat()
            if st.st_size != size or int(st.st_mtime) != int(hist[rel]["mtime"]):
                raise ValueError("source size/mtime changed after preflight")
            if sha256(src) != digest:
                raise ValueError("source full hash changed after preflight")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest = checked_path(QUAR, rel)
            if dest.exists():
                raise ValueError("destination collision after directory creation")
            os.rename(src, dest)
            move_in_quarantine = True
            row["move_status"] = "MOVED_UNVERIFIED"
            try:
                if dest.stat().st_size != size or sha256(dest) != digest:
                    raise ValueError("destination full hash mismatch")
                if not can.is_file() or can.stat().st_size != size or sha256(can) != digest:
                    raise ValueError("canonical changed during move")
            except Exception:
                if src.exists():
                    raise RuntimeError("restore blocked: original path occupied")
                os.rename(dest, src)
                move_in_quarantine = False
                row.update(move_status="RESTORED_AFTER_FAILURE", verification_status="FAILED", rollback_status="RESTORED", error="destination or canonical verification failed; restored", timestamp=now())
                state["restored_after_failure"] += 1
                state["failed"] += 1; state["processed"] += 1
                log_event({"event":"AUTO_RESTORED", "group_id": row["group_id"], "path": rel})
                continue
            row.update(move_status="MOVED", destination_hash=digest, verification_status="VERIFIED", timestamp=now())
            rollback.append({"quarantine_path": str(dest), "original_path": str(src), "canonical_path": str(can),
                             "execution_hash": digest, "size_bytes": size, "verified": "YES", "group_id": row["group_id"]})
            write_csv(ROLLBACK, ROLL_FIELDS, rollback)
            rolled_paths.add(row["duplicate_path"])
            state["successfully_moved"] += 1; state["verified"] += 1; state["bytes_moved"] += size
            state["processed"] += 1
            state["last_successful_operation"] = {"group_id": row["group_id"], "relative_path": rel, "time": now()}
            log_event({"event":"MOVED_VERIFIED", "group_id": row["group_id"], "path": rel, "size": size})
        except (OSError, ValueError) as e:
            if move_in_quarantine:
                raise RuntimeError("move is in quarantine but transaction recording failed; inspect and resume") from e
            row.update(move_status="SKIPPED", verification_status="NOT_MOVED", error=f"{type(e).__name__}: {str(e)[:180]}", timestamp=now())
            state["skipped"] += 1; state["processed"] += 1
            log_event({"event":"SKIPPED", "group_id": row["group_id"], "path": rel, "error_type": type(e).__name__})
        batch_count += 1
        if batch_count >= batch_size:
            state["current_batch"] += 1
            checkpoint(rows, state)
            print(f"batch={state['current_batch']} processed={state['processed']} moved={state['successfully_moved']} skipped={state['skipped']} remaining={state['remaining']}", flush=True)
            batch_count = 0
    if batch_count:
        state["current_batch"] += 1
        checkpoint(rows, state)
    state["phase"] = "EXECUTION_COMPLETE"
    checkpoint(rows, state)
    print(f"EXECUTION COMPLETE moved={state['successfully_moved']} bytes={state['bytes_moved']} skipped={state['skipped']} failed={state['failed']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=("preflight", "execute"))
    ap.add_argument("--batch-size", type=int, default=500)
    args = ap.parse_args()
    if args.phase == "preflight":
        preflight()
    else:
        execute(args.batch_size)


if __name__ == "__main__":
    main()
