"""Read-only Office math census over the T2 inventory.
OOXML (.docx/.docm/.dotx/.pptx/.pptm/.ppsx/.xlsx): counts native Office Math per file:
  omath = number of <m:oMath> elements (each equation, inline or display), omathpara = <m:oMathPara> elements only (display groups; excludes <m:oMathParaPr>),
  ole_equation_editor = embedded OLE equations with ProgID Equation.3 (legacy MS Equation Editor),
  ole_mathtype = embedded OLE with ProgID Equation.DSMT* (MathType), media = embedded media files.
Legacy OLE2 (.doc/.ppt/.pps/.xls): byte-signature SIGNALS only (not equation counts): 'Equation.3', 'Equation.DSMT', 'MathType'.
Nothing is written to the source tree."""
import csv, os, re, json, zipfile, time
ROOT = r"D:\MBI-BRAIN"; B = r"D:\AgenticAI\second-brain-rag\audit\phase0\t2"
OOXML = {".docx", ".docm", ".dotx", ".pptx", ".pptm", ".ppsx", ".xlsx", ".xlsm"}
LEGACY = {".doc", ".ppt", ".pps", ".xls", ".dot"}
PARTS = re.compile(r"^(word/(document|footnotes|endnotes|header\d*|footer\d*)\.xml|ppt/(slides/slide|notesSlides/notesSlide)\d+\.xml|xl/worksheets/sheet\d+\.xml)$")
rows = list(csv.DictReader(open(B + r"\inventory_t2.csv", encoding="utf-8")))
out = open(B + r"\office_census_t2.jsonl", "w", encoding="utf-8"); t = time.time(); n = 0
for r in rows:
    ext = r["ext"]
    if ext not in OOXML | LEGACY: continue
    p = os.path.join(ROOT, r["relpath"]); d = {"relpath": r["relpath"], "ext": ext, "size": int(r["size"])}
    try:
        if ext in OOXML:
            z = zipfile.ZipFile(p); names = z.namelist(); om = omp = eq3 = mt = 0; parts = 0
            for nm in names:
                if PARTS.match(nm):
                    x = z.read(nm); parts += 1
                    om += len(re.findall(rb"<m:oMath[ >]", x)); omp += len(re.findall(rb"<m:oMathPara[ >]", x))
                    eq3 += x.count(b'ProgID="Equation.3"'); mt += len(re.findall(rb'ProgID="Equation\.DSMT', x))
            d.update(kind="ooxml", parts=parts, omath=om, omathpara=omp, ole_equation_editor=eq3, ole_mathtype=mt,
                     media=sum(1 for nm in names if "/media/" in nm), slides=sum(1 for nm in names if re.match(r"ppt/slides/slide\d+\.xml$", nm)))
        else:
            b = open(p, "rb").read()
            d.update(kind="ole2", is_ole2=b[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",
                     sig_equation3=b.count(b"Equation.3"), sig_dsmt=b.count(b"Equation.DSMT"), sig_mathtype=b.count(b"MathType"))
    except Exception as e:
        d["error"] = f"{type(e).__name__}: {str(e)[:120]}"
    out.write(json.dumps(d, ensure_ascii=False) + "\n"); n += 1
out.close(); print("office files", n, "secs", round(time.time() - t))
