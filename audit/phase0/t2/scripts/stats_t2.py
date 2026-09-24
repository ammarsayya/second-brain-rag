"""T2 CURRENT CORPUS statistics from an inventory CSV (metadata only). Usage: python stats_t2.py inventory.csv out_prefix"""
import csv, collections, os, sys, json
inv, out = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(inv, encoding="utf-8")))
for r in rows: r["size"] = int(r["size"])
S = {"files": len(rows), "bytes": sum(r["size"] for r in rows), "zero_byte": sum(r["size"] == 0 for r in rows)}
dirs = set()
for r in rows:
    d = os.path.dirname(r["relpath"])
    while d: dirs.add(d); d = os.path.dirname(d)
S["dirs_with_files_beneath"] = len(dirs); S["max_depth"] = max(int(r["depth"]) for r in rows)
def agg(key):
    a = collections.defaultdict(lambda: [0, 0])
    for r in rows: k = key(r); a[k][0] += 1; a[k][1] += r["size"]
    return {k: {"files": c, "bytes": b} for k, (c, b) in sorted(a.items(), key=lambda x: -x[1][1])}
S["by_ext"] = agg(lambda r: r["ext"] or "<none>")
S["top_level"] = agg(lambda r: r["relpath"].split(os.sep)[0])
S["level2"] = agg(lambda r: os.sep.join(r["relpath"].split(os.sep)[:2]))
S["largest_files"] = [(r["relpath"], r["size"]) for r in sorted(rows, key=lambda r: -r["size"])[:40]]
dsz = collections.Counter()
for r in rows:
    p = r["relpath"].split(os.sep)
    for i in range(1, min(len(p), 5)): dsz[os.sep.join(p[:i])] += r["size"]
S["largest_dirs_depth1to4"] = dsz.most_common(40)
json.dump(S, open(out + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("T2 CURRENT CORPUS: files", S["files"], "GB", round(S["bytes"]/1e9, 2), "dirs", S["dirs_with_files_beneath"], "zero", S["zero_byte"], "maxdepth", S["max_depth"])
for k, v in list(S["by_ext"].items())[:25]: print(f"  {k:8} {v['files']:7} {v['bytes']/1e9:8.2f} GB")
print("by count:", sorted(((v['files'], k) for k, v in S["by_ext"].items()), reverse=True)[:30])
print("TOP:"); [print(f"  {k:30} {v['files']:7} {v['bytes']/1e9:8.2f} GB") for k, v in S["top_level"].items()]
print("L2:"); [print(f"  {k[:60]:60} {v['files']:7} {v['bytes']/1e9:8.2f} GB") for k, v in sorted(S["level2"].items())]
