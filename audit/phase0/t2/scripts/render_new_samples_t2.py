"""Render selected T2 new-content pages (90 dpi) + text dumps into audit/phase0/t2/samples (read-only)."""
import os, json, pymupdf
pymupdf.TOOLS.mupdf_display_errors(False)
ROOT = r"D:\MBI-BRAIN"; OUT = r"D:\AgenticAI\second-brain-rag\audit\phase0\t2\samples"
S = {"ckurs_mutex": (r"Ckurs\Mutex.pdf", 0),
     "math1_build_p5": (r"Mechanical\Mathematik\Mathe\Math1\Vorleungsfolien im Präsentationsmodus-20200504\Vorlesung_14_Matrizen_Matrixoperationen_Praesentation.pdf", 40),
     "festigkeit_folien": (r"Mechanical\konstruktonsgrundlagen\MAE_3\Festigkeit\Folien Festigkeitslehre.pdf", 60),
     "bwl_skript": (r"Betriebslehre\Managment\Skript Betriebslehre.pdf", 30),
     "english_market_leader": (r"English\Market leader upper intermediate (3rd ed.) SB.pdf", 20),
     "ckurs_scan": (r"Ckurs\Gescannt_20211104-1823.pdf", 0)}
res = {}
for k, (rel, pi) in S.items():
    try:
        doc = pymupdf.open(os.path.join(ROOT, rel)); pi = min(pi, doc.page_count - 1); pg = doc[pi]
        tx = pg.get_text(); pg.get_pixmap(dpi=90).save(os.path.join(OUT, f"{k}_p{pi+1}.png"))
        open(os.path.join(OUT, f"{k}_p{pi+1}.txt"), "w", encoding="utf-8").write(f"SOURCE: {rel}\nPAGE: {pi+1}/{doc.page_count}\n\n{tx}")
        res[k] = {"relpath": rel, "page": pi + 1, "pages": doc.page_count, "chars": len(tx.strip()), "images": len(pg.get_images())}
    except Exception as e: res[k] = {"relpath": rel, "error": str(e)[:100]}
json.dump(res, open(os.path.join(OUT, "new_samples_t2.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
