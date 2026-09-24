"""Read-only deep sample: for each doc, pick the page with most math-font spans; dump text layer + render PNG to audit dir."""
import pymupdf, re, os, json, sys
pymupdf.TOOLS.mupdf_display_errors(False)
ROOT=r"D:\MBI-BRAIN"; OUT=r"D:\AgenticAI\second-brain-rag\audit\phase0\samples"
MATHF=re.compile(r"CMMI|CMSY|CMEX|Cambria.?Math|Symbol|MT.?Extra|MSAM|MSBM|Euclid|STIX|Math",re.I)
DOCS={
 "thesis":r"BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit.pdf",
 "dynamics":r"Mechanical\Dynamik\Dyn\Skript Maschinendynamik 1.pdf",
 "modelling":r"Mechanical\Modellbildung_technischer_Systeme\MTS_Vers_03-2006.pdf",
 "control_h2":r"Mechanical\regelungstechnik\Regelungstechnik\H2-Arbeiten mit linearen Modellen.pdf",
 "fem":r"Mechanical\FEM\Rust\FEM_1\FEM-Grdlg.pdf",
 "numerics_book":r"BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Boocks\Mat\NumMath5.pdf",
 "robotics_dh":r"Mechanical\Robotertechnik\Rob_1\Rob2\Roboter\uebung_dh-trafo_300dpi.pdf",
 "cs_algdat":r"Information\vorvorl\AlgDat\Vor\1\Vorlesung_1_Stack.pdf",
 "scanned_exam":r"Mechanical\Robotertechnik\Rob_1\Rob1\Kla\Klausur Robotik WS2014 mit L\u00f6sung.pdf",
 "control_exam":r"Mechanical\regelungstechnik\Regelungstechnik\Klausuren\RT2_2010-01-08.pdf",
}
res={}
for key,rel in DOCS.items():
    p=os.path.join(ROOT,rel)
    try: doc=pymupdf.open(p)
    except Exception as e: print(key,"ERR",e); continue
    best=(-1,0)
    for i in range(min(doc.page_count,60)):
        n=0
        for b in doc[i].get_text("dict")["blocks"]:
            for l in b.get("lines",[]):
                for s in l["spans"]:
                    if MATHF.search(s["font"]): n+=1
        best=max(best,(n,i))
    i=best[1] if best[0]>0 else min(3,doc.page_count-1); pg=doc[i]
    txt=pg.get_text("text")
    open(os.path.join(OUT,f"{key}_p{i+1}.txt"),"w",encoding="utf-8").write(f"SOURCE: {rel}\nPAGE: {i+1}/{doc.page_count}\nMATH_SPANS: {best[0]}\n\n{txt}")
    pg.get_pixmap(dpi=90).save(os.path.join(OUT,f"{key}_p{i+1}.png"))
    res[key]={"page":i+1,"pages":doc.page_count,"math_spans":best[0],"chars":len(txt),"toc":doc.get_toc()[:12]}
    doc.close()
json.dump(res,open(OUT+r"\deep_sample.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
for k,v in res.items(): print(k,v["page"],"/",v["pages"],"mathspans",v["math_spans"],"chars",v["chars"],"toc",len(v["toc"]))
