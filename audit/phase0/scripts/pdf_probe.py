"""Read-only stratified PDF probe: opens PDFs with PyMuPDF, inspects up to MAXP pages. Writes nothing to source."""
import csv, os, random, collections, json, sys, re, time
import pymupdf
pymupdf.TOOLS.mupdf_display_errors(False)
ROOT=r"D:\MBI-BRAIN"; BASE=r"D:\AgenticAI\second-brain-rag\audit\phase0"
MAXP=25; PER=12
MATHF=re.compile(r"CMMI|CMSY|CMEX|CMR|LMMath|LMRoman|Cambria.?Math|STIX|MathType|MT.?Extra|Symbol|Euclid|MTMI|MTSY|RMTMI|Asana|TeXGyre|XITS|MSBM|MSAM|rsfs|esint|Latin Modern Math|MathematicalPi|Mathematica",re.I)
rows=list(csv.DictReader(open(BASE+r"\inventory.csv",encoding="utf-8")))
pdf=[r for r in rows if r["ext"]==".pdf" and not os.path.basename(r["relpath"]).startswith("._")]
grp=collections.defaultdict(list)
for r in pdf: grp[os.sep.join(r["relpath"].split(os.sep)[:3])].append(r)
random.seed(42); sample=[]
for k,v in grp.items(): sample+=random.sample(v,min(PER,len(v)))
out=open(BASE+r"\pdf_probe.jsonl","w",encoding="utf-8"); t=time.time()
for r in sample:
    p=os.path.join(ROOT,r["relpath"]); d={"relpath":r["relpath"],"size":int(r["size"])}
    try:
        doc=pymupdf.open(p)
        d.update(pages=doc.page_count, encrypted=doc.is_encrypted, meta={k:(doc.metadata or {}).get(k) for k in ("title","author","creator","producer","creationDate")},
                 toc=len(doc.get_toc()))
        n=min(MAXP,doc.page_count); chars=[];imgs=0;draws=0;notext=0;fonts=collections.Counter();w=h=None;annots=0
        for i in range(n):
            pg=doc[i]; tx=pg.get_text("text"); chars.append(len(tx.strip()))
            if len(tx.strip())<30: notext+=1
            imgs+=len(pg.get_images(full=False)); draws+=len(pg.get_drawings()) if i<8 else 0
            annots+=len(list(pg.annots() or []))
            for f in pg.get_fonts(full=False): fonts[f[3]]+=1
            if i==0: w,h=pg.rect.width,pg.rect.height
        mf=[f for f in fonts if MATHF.search(f or "")]
        d.update(sampled=n, chars_per_page=round(sum(chars)/max(n,1)), notext_pages=notext, imgs=imgs, draws_first8=draws, annots=annots,
                 landscape=bool(w and w>h), math_fonts=mf[:8], nfonts=len(fonts), fonts_top=[f for f,_ in fonts.most_common(6)])
        doc.close()
    except Exception as e: d["error"]=str(e)[:120]
    out.write(json.dumps(d,ensure_ascii=False)+"\n")
out.close(); print("probed",len(sample),"secs",round(time.time()-t))
