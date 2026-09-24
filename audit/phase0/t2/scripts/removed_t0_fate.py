"""Fate of the 675 t0 paths absent at t1/t2: content present elsewhere in t2 (exact xxh3) or not."""
import csv, collections, os
B = r"D:\AgenticAI\second-brain-rag\audit\phase0"
t0 = {r["relpath"]: r for r in csv.DictReader(open(os.path.join(B, "inventory_t0.csv"), encoding="utf-8"))}
t2 = {r["relpath"]: r for r in csv.DictReader(open(os.path.join(B, "t2", "inventory_t2.csv"), encoding="utf-8"))}
h0 = {r["relpath"]: (r["hash"], r["size"]) for r in csv.DictReader(open(os.path.join(B, "hashes.csv"), encoding="utf-8")) if r["mode"] == "full"}
h2 = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(B, "t2", "hashes_t2.csv"), encoding="utf-8")):
    if r["mode"] == "full": h2[(r["hash"], r["size"])].append(r["relpath"])
t2n = {(os.path.basename(p).lower(), r["size"], r["mtime"]) for p, r in t2.items()}
gone = [p for p in t0 if p not in t2]; c = collections.Counter()
for p in gone:
    if p in h0: c["exact content present elsewhere" if h2.get(h0[p]) else "hashed at t0, content NOT in t2"] += 1
    else: c["probable move (same name,size,mtime)" if (os.path.basename(p).lower(), t0[p]["size"], t0[p]["mtime"]) in t2n else "unhashed, no match"] += 1
print(len(gone), dict(c))
