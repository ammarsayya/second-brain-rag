"""T2 read-only hashing (audit hash = xxh3-128, NOT the production BLAKE3 id).
Scope: all document/web types + every file whose size collides with another t2 file.
Mode 'full' = whole-file xxh3-128 (exact). Mode 'partial' = size + 3x4MiB samples for non-document files >512MiB
(PROBABILISTIC duplicate candidate only). Hashes are reused from t0 hashes.csv only when relpath, size and mtime
are identical in t0 and t2 (source=cache_t0). Errors are recorded verbatim."""
import csv, os, collections, xxhash, time, sys
ROOT = r"D:\MBI-BRAIN"; B = r"D:\AgenticAI\second-brain-rag\audit\phase0"
DOC = {".pdf",".ppt",".pptx",".ppsx",".pps",".doc",".docx",".xls",".xlsx",".txt",".md",".tex",".odt",".rtf",".csv",".html",".htm"}
t2 = list(csv.DictReader(open(B + r"\t2\inventory_t2.csv", encoding="utf-8")))
t0 = {r["relpath"]: r for r in csv.DictReader(open(B + r"\inventory_t0.csv", encoding="utf-8"))}
cache = {}
for r in csv.DictReader(open(B + r"\hashes.csv", encoding="utf-8")):
    if r["mode"] in ("full", "partial"): cache[r["relpath"]] = (r["size"], r["hash"], r["mode"])
bysize = collections.Counter(int(r["size"]) for r in t2)
def full(p):
    h = xxhash.xxh3_128()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(8 << 20), b""): h.update(b)
    return h.hexdigest()
def part(p, sz):
    h = xxhash.xxh3_128(); h.update(str(sz).encode())
    with open(p, "rb") as f:
        for off in (0, sz // 2, max(0, sz - (4 << 20))): f.seek(off); h.update(f.read(4 << 20))
    return h.hexdigest()
out = open(B + r"\t2\hashes_t2.csv", "w", newline="", encoding="utf-8"); w = csv.writer(out)
w.writerow(["relpath", "ext", "size", "hash", "mode", "source", "error"])
t = time.time(); n = nb = nc = 0
for r in t2:
    sz = int(r["size"]); ext = r["ext"]
    if not (ext in DOC or (bysize[sz] > 1 and sz > 0)): continue
    rp = r["relpath"]; c = cache.get(rp); o = t0.get(rp)
    if c and o and o["size"] == r["size"] and o["mtime"] == r["mtime"] and c[0] == r["size"]:
        w.writerow([rp, ext, sz, c[1], c[2], "cache_t0", ""]); nc += 1; continue
    p = os.path.join(ROOT, rp)
    try:
        if sz > (512 << 20) and ext not in DOC: hv, m = part(p, sz), "partial"
        else: hv, m = full(p), "full"; nb += sz
        w.writerow([rp, ext, sz, hv, m, "computed", ""])
    except OSError as e:
        w.writerow([rp, ext, sz, "", "err", "computed", f"{type(e).__name__}: {e}"])
    n += 1
    if n % 2000 == 0: print(n, "computed", round(nb / 1e9, 1), "GB", round(time.time() - t), "s", flush=True)
out.close(); print("DONE computed", n, "cached", nc, "fullGB", round(nb / 1e9, 1), "secs", round(time.time() - t))
