"""Deep 25-page probe (same method/fields as t0 pdf_probe.py) on a stratified SAMPLE of unique PDFs NOT censused at t0:
up to 8 per level-3 group, seed 42. Adds per-document near-duplicate page ratio among the first 25 pages
(consecutive pages whose text is a prefix/superset of the previous = presentation build steps)."""
import json, os, random, re, collections
import pymupdf
pymupdf.TOOLS.mupdf_display_errors(False)
ROOT = r"D:\MBI-BRAIN"; B = r"D:\AgenticAI\second-brain-rag\audit\phase0"
MATHF = re.compile(r"CMMI|CMSY|CMEX|CMR|LMMath|LMRoman|Cambria.?Math|STIX|MathType|MT.?Extra|Symbol|Euclid|MTMI|MTSY|MSBM|MSAM", re.I)
c0 = set()
for l in open(os.path.join(B, "pdf_unique_pages.jsonl"), encoding="utf-8"):
    d = json.loads(l)
    if "pages" in d: c0.add((d["hash"], str(d["size"])))
new = [d for d in map(json.loads, open(os.path.join(B, "t2", "pdf_census_t2.jsonl"), encoding="utf-8")) if d.get("pages") and (d["hash"], str(d["size"])) not in c0 and not d.get("needs_pass")]
grp = collections.defaultdict(list)
for d in new: grp[os.sep.join(d["relpath"].split(os.sep)[:3])].append(d)
random.seed(42); sample = []
for k in sorted(grp): sample += random.sample(grp[k], min(8, len(grp[k])))
out = open(os.path.join(B, "t2", "pdf_probe_new_t2.jsonl"), "w", encoding="utf-8")
for s in sample:
    d = {"relpath": s["relpath"], "hash": s["hash"], "pages": s["pages"]}
    try:
        doc = pymupdf.open(os.path.join(ROOT, s["relpath"])); n = min(25, doc.page_count)
        m = doc.metadata or {}; d["meta"] = {k: m.get(k) for k in ("creator", "producer")}
        chars = []; nt = im = an = 0; fonts = collections.Counter(); prev = None; build = 0
        for i in range(n):
            pg = doc[i]; tx = " ".join(pg.get_text().split()); chars.append(len(tx))
            if len(tx) < 30: nt += 1
            im += len(pg.get_images()); an += len(list(pg.annots() or []))
            for f in pg.get_fonts(): fonts[f[3]] += 1
            if prev and len(prev) > 30 and tx.startswith(prev[: max(30, int(len(prev) * .9))]): build += 1
            prev = tx
        d.update(sampled=n, chars_per_page=round(sum(chars) / max(n, 1)), notext_pages=nt, imgs=im, annots=an,
                 math_fonts=[f for f in fonts if MATHF.search(f or "")][:6], build_step_pages=build,
                 landscape=bool(doc[0].rect.width > doc[0].rect.height))
        doc.close()
    except Exception as e: d["error"] = str(e)[:100]
    out.write(json.dumps(d, ensure_ascii=False) + "\n")
out.close(); print("new unique PDFs", len(new), "groups", len(grp), "sampled", len(sample))
