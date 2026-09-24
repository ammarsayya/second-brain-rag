"""Content-lineage classification of every T2 file (read-only; uses inventories + hashes only).
Categories:
  A  path unchanged since t0 (same relpath, size, mtime)  -> covered by the t0 audit (inventory; hashed if doc/collision)
  B  new path, content already present before:            B_exact = full xxh3 match to t0-hashed content or to a
                                                          t2 file whose path existed at t1/t0; B_probable = same
                                                          (basename,size,mtime) as a t0/t1 file, no hash proof
  C  path first seen at t1 (not t0), unchanged at t2, content not matching t0-hashed content -> existed at t1, not deeply audited
  D  path first seen at t2 and content provably new: size occurs in no t0/t1 file, or full hash differs from every
     hashed t0/t1-era file of that size (all such files hashed)
  E  uncertain: identity cannot be proven either way (no full hash, or same-size counterparts unhashed)
Also reports C/D/E by content-unique objects."""
import csv, os, json, collections
B = r"D:\AgenticAI\second-brain-rag\audit\phase0"
rd = lambda f: {r["relpath"]: r for r in csv.DictReader(open(os.path.join(B, f), encoding="utf-8"))}
t0, t1, t2 = rd("inventory_t0.csv"), rd("inventory_t1.csv"), rd(os.path.join("t2", "inventory_t2.csv"))
h0 = {r["relpath"]: r for r in csv.DictReader(open(os.path.join(B, "hashes.csv"), encoding="utf-8")) if r["mode"] == "full"}
h2 = {r["relpath"]: r for r in csv.DictReader(open(os.path.join(B, "t2", "hashes_t2.csv"), encoding="utf-8"))}
t0_hash = {(r["hash"], r["size"]) for r in h0.values()}
old_paths = set(t0) | set(t1)
old_hash = set(t0_hash) | {(r["hash"], r["size"]) for p, r in h2.items() if r["mode"] == "full" and p in old_paths}
old_sizes = collections.defaultdict(list)
for p, r in list(t0.items()) + [(p, r) for p, r in t1.items() if p not in t0]: old_sizes[r["size"]].append(p)
old_nsm = {(os.path.basename(p).lower(), r["size"], r["mtime"]) for p, r in list(t0.items()) + list(t1.items())}
def hashed_old(p):  # is the old-era file at path p covered by a full hash?
    return p in h0 or (p in h2 and h2[p]["mode"] == "full")
rows = []; cat = collections.Counter(); catb = collections.Counter()
for p, r in t2.items():
    hr = h2.get(p); full = hr and hr["mode"] == "full"; key = (hr["hash"], r["size"]) if full else None
    same0 = p in t0 and (t0[p]["size"], t0[p]["mtime"]) == (r["size"], r["mtime"])
    same1 = p in t1 and (t1[p]["size"], t1[p]["mtime"]) == (r["size"], r["mtime"])
    if same0: c = "A"
    elif same1:
        c = "B_exact" if key in t0_hash else ("C" if (full or r["size"] not in {t0[x]["size"] for x in t0} ) else "C")
    else:
        if key and key in old_hash: c = "B_exact"
        elif (os.path.basename(p).lower(), r["size"], r["mtime"]) in old_nsm: c = "B_probable"
        elif r["size"] not in old_sizes: c = "D"
        elif full and all(hashed_old(x) for x in old_sizes[r["size"]]): c = "D"
        else: c = "E"
    cat[c] += 1; catb[c] += int(r["size"])
    rows.append((p, r["ext"], r["size"], c, hr["hash"] if full else "", "full" if full else (hr["mode"] if hr else "none")))
with open(os.path.join(B, "t2", "identity_t2.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["relpath", "ext", "size", "category", "xxh3_128", "hash_mode"]); w.writerows(rows)
S = {"files_by_category": dict(cat), "bytes_by_category": {k: v for k, v in catb.items()}}
for c in ("C", "D", "E", "B_exact", "B_probable"):
    sub = [x for x in rows if x[3] == c]
    S[c + "_by_ext"] = dict(collections.Counter(x[1] for x in sub).most_common(15))
    S[c + "_by_L3"] = dict(collections.Counter(os.sep.join(x[0].split(os.sep)[:3]) for x in sub).most_common(15))
    S[c + "_unique_contents_full_hash"] = len({x[4] for x in sub if x[4]})
json.dump(S, open(os.path.join(B, "t2", "identity_t2_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(S, ensure_ascii=False, indent=1)[:6000])
