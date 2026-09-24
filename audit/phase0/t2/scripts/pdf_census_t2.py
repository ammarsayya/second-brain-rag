"""T2 whole-corpus PDF census (read-only). One row per content-unique PDF (full xxh3-128 from hashes_t2.csv).
For each unique blob, candidate paths are tried in order until one opens (fixes the t0 flaw where a moved
representative path lost the blob). AppleDouble '._*' files are excluded and counted separately.
Per blob: page count (FULL), encryption flags, open-error class, first-page landscape (FULL), and signals on
5 probe pages (0, n/4, n/2, 3n/4, n-1; SAMPLE within the document): textless (<30 chars), math-font presence,
PDF annotation objects, embedded image refs, vector drawing ops.
Definitions are identical to the t0 page census so values are comparable."""
import csv, os, re, json, collections, time
import pymupdf
pymupdf.TOOLS.mupdf_display_errors(False)
ROOT = r"D:\MBI-BRAIN"; B = r"D:\AgenticAI\second-brain-rag\audit\phase0\t2"
MATHF = re.compile(r"CMMI|CMSY|CMEX|Cambria.?Math|Symbol|MT.?Extra|MSAM|MSBM|Euclid|STIX|MathType|LMMath", re.I)
groups = collections.OrderedDict(); apple = 0; nohash = []
for r in csv.DictReader(open(B + r"\hashes_t2.csv", encoding="utf-8")):
    if r["ext"] != ".pdf": continue
    if os.path.basename(r["relpath"]).startswith("._"): apple += 1; continue
    if r["mode"] != "full": nohash.append(r); continue
    groups.setdefault((r["hash"], r["size"]), []).append(r["relpath"])
out = open(B + r"\pdf_census_t2.jsonl", "w", encoding="utf-8"); t = time.time()
for (h, s), paths in groups.items():
    d = {"hash": h, "size": int(s), "n_paths": len(paths), "paths_tried": 0}
    for rel in paths:
        d["paths_tried"] += 1
        try:
            doc = pymupdf.open(os.path.join(ROOT, rel))
        except Exception as e:
            d["error"] = f"{type(e).__name__}: {str(e)[:100]}"; continue
        d.pop("error", None); d["relpath"] = rel
        try:
            d["needs_pass"] = bool(doc.needs_pass); d["is_encrypted"] = bool(doc.is_encrypted)
            n = doc.page_count; d["pages"] = n
            if n:
                r0 = doc[0].rect; d["landscape"] = bool(r0.width > r0.height)
                idx = sorted({0, n // 4, n // 2, 3 * n // 4, n - 1}); nt = mf = an = im = dr = 0
                for i in idx:
                    pg = doc[i]
                    if len(pg.get_text().strip()) < 30: nt += 1
                    if any(MATHF.search(f[3] or "") for f in pg.get_fonts()): mf += 1
                    an += len(list(pg.annots() or [])); im += len(pg.get_images()); dr += len(pg.get_drawings())
                d.update(probe_pages=len(idx), notext=nt, mathpages=mf, annots=an, imgs=im, drawings=dr)
        except Exception as e:
            d["partial_error"] = f"{type(e).__name__}: {str(e)[:100]}"
        finally:
            doc.close()
        break
    if "relpath" not in d: d["relpath"] = paths[0]
    out.write(json.dumps(d, ensure_ascii=False) + "\n")
out.close()
json.dump({"unique_pdf_blobs": len(groups), "appledouble_excluded_paths": apple, "pdf_paths_without_full_hash": len(nohash)},
          open(B + r"\pdf_census_t2_meta.json", "w"), indent=1)
print("unique", len(groups), "appledouble", apple, "no full hash", len(nohash), "secs", round(time.time() - t))
