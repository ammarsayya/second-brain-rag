"""T2 organization and junk metrics from inventory metadata (FULL CORPUS, metadata only)."""
import csv, os, collections, json
B = r"D:\AgenticAI\second-brain-rag\audit\phase0"
R = list(csv.DictReader(open(os.path.join(B, "t2", "inventory_t2.csv"), encoding="utf-8")))
S = {}
S["mojibake_paths"] = sum(1 for r in R if any(c in r["relpath"] for c in "├Ã¤¶¼"))
S["umlaut_paths"] = sum(1 for r in R if any(c in r["relpath"] for c in "äöüÄÖÜß"))
S["macosx_or_appledouble"] = sum(1 for r in R if "__MACOSX" in r["relpath"] or os.path.basename(r["relpath"]).startswith("._"))
S["os_junk"] = sum(1 for r in R if os.path.basename(r["relpath"]).lower() in ("thumbs.db", ".ds_store", "desktop.ini"))
S["zero_byte"] = sum(1 for r in R if r["size"] == "0")
noise = collections.Counter()
for r in R:
    p = r["relpath"].lower()
    for k in (r"\.metadata" + "\\", "_projectscratch", r"\.git" + "\\", r"\slprj" + "\\", r"\bin" + "\\", r"\__pycache__" + "\\", r"\node_modules" + "\\", r"_files\dp0"):
        if k in p: noise[k] += 1
S["tool_noise_paths"] = dict(noise)
S["code_files"] = dict(collections.Counter(r["ext"] for r in R if r["ext"] in (".java", ".class", ".m", ".c", ".h", ".cpp", ".py", ".ino", ".sh", ".js", ".css", ".make", ".exml", ".ctxt", ".bluej")))
S["media"] = {e: [sum(1 for r in R if r["ext"] == e), round(sum(int(r["size"]) for r in R if r["ext"] == e) / 1e9, 2)] for e in (".mp4", ".avi", ".mkv", ".m4v", ".mov", ".webm", ".wmv", ".mp3", ".wav")}
L3 = collections.Counter(os.sep.join(r["relpath"].split(os.sep)[:3]) for r in R if r["relpath"].count(os.sep) >= 2)
S["level3_folders"] = len(L3)
S["level3_top"] = L3.most_common(60)
json.dump(S, open(os.path.join(B, "t2", "org_junk_t2.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print({k: v for k, v in S.items() if k != "level3_top"})
for k, v in S["level3_top"][:60]: print(f"  {v:6} {k}")
