"""T2 media uniqueness (exact where fully hashed, candidates where partial) and sensitive-name signals (counts only)."""
import csv, collections, os, json, re
B = r"D:\AgenticAI\second-brain-rag\audit\phase0\t2"
inv = list(csv.DictReader(open(os.path.join(B, "inventory_t2.csv"), encoding="utf-8")))
H = {r["relpath"]: r for r in csv.DictReader(open(os.path.join(B, "hashes_t2.csv"), encoding="utf-8"))}
V = {".mp4", ".avi", ".mkv", ".m4v", ".mov", ".webm", ".wmv"}
vid = [r for r in inv if r["ext"] in V]
keys = set(); exact = cand = unhashed_unique = 0
for r in vid:
    h = H.get(r["relpath"])
    if h and h["mode"] in ("full", "partial"): keys.add((h["mode"], h["hash"], h["size"]))
    else: keys.add(("size-unique", r["relpath"], r["size"]))
ub = sum(int(k[2]) for k in keys)
S = {"video_files": len(vid), "video_bytes": sum(int(r["size"]) for r in vid), "video_unique_objects": len(keys), "video_unique_bytes": ub,
     "note": "unique = distinct full hash, distinct partial hash (probabilistic), or size unique in corpus (provably unique)"}
PAT = {"grades": r"noten|ergebnisliste|notenliste|punkteliste", "contracts": r"vertrag", "applications_certificates": r"bewerbung|zeugnis|lebenslauf|immatrikulation", "ids": r"ausweis|reisepass|personalausweis"}
S["sensitive_name_signals"] = {k: sum(1 for r in inv if re.search(p, r["relpath"], re.I)) for k, p in PAT.items()}
json.dump(S, open(os.path.join(B, "media_sensitive_t2.json"), "w", encoding="utf-8"), indent=1)
print(S)
