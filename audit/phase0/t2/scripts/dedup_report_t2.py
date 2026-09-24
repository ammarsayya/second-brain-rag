"""T2 duplicate report. EXACT groups = identical full xxh3-128 + size. CANDIDATE groups = partial-hash matches
(size + 3 samples; probabilistic, NOT proven). Also directory mirror pairs (>=90% shared exact blobs both ways)."""
import csv, collections, os, json
B = r"D:\AgenticAI\second-brain-rag\audit\phase0\t2"
H = [r for r in csv.DictReader(open(B + r"\hashes_t2.csv", encoding="utf-8")) if r["mode"] in ("full", "partial")]
g = collections.defaultdict(list)
for r in H: g[(r["mode"], r["hash"], r["size"])].append(r)
ex = {k: v for k, v in g.items() if k[0] == "full" and len(v) > 1}
ca = {k: v for k, v in g.items() if k[0] == "partial" and len(v) > 1}
red = lambda G: (sum(len(v) - 1 for v in G.values()), sum((len(v) - 1) * int(k[2]) for k, v in G.items()))
S = {"exact_groups": len(ex), "exact_redundant_files": red(ex)[0], "exact_redundant_bytes": red(ex)[1],
     "candidate_groups_partial": len(ca), "candidate_redundant_files": red(ca)[0], "candidate_redundant_bytes": red(ca)[1],
     "exact_by_ext": {}}
be = collections.defaultdict(lambda: [0, 0, 0])
for k, v in ex.items():
    e = v[0]["ext"]; be[e][0] += 1; be[e][1] += len(v) - 1; be[e][2] += (len(v) - 1) * int(k[2])
S["exact_by_ext"] = {e: {"groups": a, "redundant_files": b, "redundant_bytes": c} for e, (a, b, c) in sorted(be.items(), key=lambda x: -x[1][2])[:20]}
for e in (".pdf", ".docx", ".doc", ".pptx", ".ppt", ".ppsx", ".xlsx", ".html", ".zip", ".mp4"):
    rows = [r for r in H if r["ext"] == e and r["mode"] == "full"]
    S.setdefault("unique_by_ext", {})[e] = {"paths_full_hashed": len(rows), "unique_contents": len({(r["hash"], r["size"]) for r in rows})}
# mirrors
dirblobs = collections.defaultdict(set)
for k, v in ex.items():
    for r in v:
        parts = r["relpath"].split(os.sep)
        for d in range(2, min(7, len(parts))): dirblobs[os.sep.join(parts[:d])].add(k)
allblobs = collections.defaultdict(set)
for r in H:
    if r["mode"] == "full":
        parts = r["relpath"].split(os.sep)
        for d in range(2, min(7, len(parts))): allblobs[os.sep.join(parts[:d])].add((r["mode"], r["hash"], r["size"]))
bd = collections.defaultdict(set)
for d, bs in allblobs.items():
    if len(bs) >= 20:
        for b in bs & set(ex): bd[b].add(d)
pair = collections.Counter()
for b, ds in bd.items():
    ds = sorted(ds)
    if len(ds) < 40:
        for i in range(len(ds)):
            for j in range(i + 1, len(ds)):
                if not ds[j].startswith(ds[i] + os.sep) and not ds[i].startswith(ds[j] + os.sep): pair[(ds[i], ds[j])] += 1
mir = [(n, a, b) for (a, b), n in pair.items() if n / len(allblobs[a]) >= .9 and n / len(allblobs[b]) >= .9]
ms = {(a, b) for _, a, b in mir}
top = sorted([m for m in mir if (os.path.dirname(m[1]), os.path.dirname(m[2])) not in ms], reverse=True)
S["mirror_pairs_maximal"] = len(top); S["mirror_pairs_top"] = top[:40]
json.dump(S, open(B + r"\dedup_t2_summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump([[r["relpath"] for r in v] for v in ex.values()], open(B + r"\dup_groups_exact_t2.json", "w", encoding="utf-8"), ensure_ascii=False)
json.dump([[r["relpath"] for r in v] for v in ca.values()], open(B + r"\dup_groups_candidate_partial_t2.json", "w", encoding="utf-8"), ensure_ascii=False)
print({k: v for k, v in S.items() if k not in ("mirror_pairs_top", "exact_by_ext")})
for e, v in list(S["exact_by_ext"].items())[:10]: print("  ", e, v)
for n, a, b in top[:25]: print(f"  {n:5} {a[:60]:60} <-> {b[:60]}")
