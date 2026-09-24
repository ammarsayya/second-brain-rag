"""Build-step (presentation-mode) page detection over ALL unique PDFs whose first page is landscape (slide-like).
First 25 pages per doc: a page is a build step if its normalized text starts with >=90% of the previous page's text
(previous text >=30 chars). Whole-document build pages are EXTRAPOLATED from the first-25-page ratio."""
import json, os
import pymupdf
pymupdf.TOOLS.mupdf_display_errors(False)
ROOT = r"D:\MBI-BRAIN"; B = r"D:\AgenticAI\second-brain-rag\audit\phase0\t2"
D = [json.loads(l) for l in open(os.path.join(B, "pdf_census_t2.jsonl"), encoding="utf-8")]
out = open(os.path.join(B, "build_steps_t2.jsonl"), "w", encoding="utf-8")
for d in D:
    if not d.get("landscape") or d.get("needs_pass") or not d.get("pages"): continue
    r = {"hash": d["hash"], "relpath": d["relpath"], "pages": d["pages"]}
    try:
        doc = pymupdf.open(os.path.join(ROOT, d["relpath"])); n = min(25, doc.page_count); prev = None; b = 0
        for i in range(n):
            tx = " ".join(doc[i].get_text().split())
            if prev and len(prev) >= 30 and tx.startswith(prev[: int(len(prev) * .9)]): b += 1
            prev = tx
        doc.close(); r.update(checked=n, build_pages=b, est_build_pages_EXTRAPOLATION=round(d["pages"] * b / n))
    except Exception as e: r["error"] = str(e)[:80]
    out.write(json.dumps(r, ensure_ascii=False) + "\n")
out.close()
R = [json.loads(l) for l in open(os.path.join(B, "build_steps_t2.jsonl"), encoding="utf-8")]; ok = [r for r in R if "checked" in r]
heavy = [r for r in ok if r["build_pages"] >= 0.3 * r["checked"]]
print("landscape unique PDFs", len(R), "checked", len(ok), "docs >=30% build pages", len(heavy),
      "their pages", sum(r["pages"] for r in heavy), "est build pages (extrapolated, all landscape docs)", sum(r["est_build_pages_EXTRAPOLATION"] for r in ok))
