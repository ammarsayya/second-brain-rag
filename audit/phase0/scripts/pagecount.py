"""Read-only: page count + cheap text/math-font signal for every unique PDF blob."""
import csv,os,re,json,pymupdf
pymupdf.TOOLS.mupdf_display_errors(False)
B=r"D:\AgenticAI\second-brain-rag\audit\phase0"; ROOT=r"D:\MBI-BRAIN"
MATHF=re.compile(r"CMMI|CMSY|CMEX|Cambria.?Math|Symbol|MT.?Extra|MSAM|MSBM|Euclid|STIX|MathType|LMMath",re.I)
seen={}; 
for r in csv.DictReader(open(B+r"\hashes.csv",encoding="utf-8")):
    if r["ext"]==".pdf" and r["mode"]=="full" and (r["hash"],r["size"]) not in seen and not os.path.basename(r["relpath"]).startswith("._"): seen[(r["hash"],r["size"])]=r["relpath"]
out=open(B+r"\pdf_unique_pages.jsonl","w",encoding="utf-8"); tot=0
for (h,s),rel in seen.items():
    d={"hash":h,"relpath":rel,"size":int(s)}
    try:
        doc=pymupdf.open(os.path.join(ROOT,rel)); n=doc.page_count; d["pages"]=n
        idx=sorted({0,n//4,n//2,3*n//4,n-1}) if n>0 else []
        nt=0; mf=0
        for i in idx:
            pg=doc[i]
            if len(pg.get_text().strip())<30: nt+=1
            if any(MATHF.search(f[3] or "") for f in pg.get_fonts()): mf+=1
        d["probe_pages"]=len(idx); d["notext"]=nt; d["mathpages"]=mf; tot+=n; doc.close()
    except Exception as e: d["error"]=str(e)[:100]
    out.write(json.dumps(d,ensure_ascii=False)+"\n")
out.close(); print("unique pdfs",len(seen),"total pages",tot)
