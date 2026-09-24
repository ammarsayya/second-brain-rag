"""Recheck the Phase-0 deep samples in T2: SAME PATH / MOVED-OR-RENAMED / MISSING / CONTENT CHANGED / UNKNOWN (by xxh3 identity)."""
import csv, os, collections
B = r"D:\AgenticAI\second-brain-rag\audit\phase0"
S = {"thesis": r"BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit.pdf",
     "dynamics": r"Mechanical\Dynamik\Dyn\Skript Maschinendynamik 1.pdf",
     "modelling": r"Mechanical\Modellbildung_technischer_Systeme\MTS_Vers_03-2006.pdf",
     "control_h2": r"Mechanical\regelungstechnik\Regelungstechnik\H2-Arbeiten mit linearen Modellen.pdf",
     "fem": r"Mechanical\FEM\Rust\FEM_1\FEM-Grdlg.pdf",
     "numerics_book": r"BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\Boocks\Mat\NumMath5.pdf",
     "robotics_dh": r"Mechanical\Robotertechnik\Rob_1\Rob2\Roboter\uebung_dh-trafo_300dpi.pdf",
     "cs_algdat": r"Information\vorvorl\AlgDat\Vor\1\Vorlesung_1_Stack.pdf",
     "control_exam": r"Mechanical\regelungstechnik\Regelungstechnik\Klausuren\RT2_2010-01-08.pdf",
     "scanned_statik": r"Mechanical\Statik\tut\1\Kap 6.pdf",
     "scanned_exam(never produced)": "Mechanical\\Robotertechnik\\Rob_1\\Rob1\\Kla\\Klausur Robotik WS2014 mit L\u00f6sung.pdf",
     "thesis_docx": r"BachelorArbeit\MatlabBachelorArbeit\Bacelorarbeit\BA\Bachelorarbeit.docx"}
h0 = {r["relpath"]: r for r in csv.DictReader(open(B + r"\hashes.csv", encoding="utf-8"))}
h2 = collections.defaultdict(list); p2 = {}
for r in csv.DictReader(open(B + r"\t2\hashes_t2.csv", encoding="utf-8")):
    p2[r["relpath"]] = r
    if r["mode"] == "full": h2[(r["hash"], r["size"])].append(r["relpath"])
with open(B + r"\t2\samples\old_sample_recheck_t2.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["sample", "t0_path", "status", "t2_paths_with_same_content"])
    for k, p in S.items():
        o = h0.get(p)
        if not o or o["mode"] != "full": st, same = "UNKNOWN (no t0 full hash)", []
        else:
            same = h2.get((o["hash"], o["size"]), [])
            if p in same: st = "SAME PATH"
            elif same: st = "MOVED/RENAMED (content identical)"
            elif p in p2: st = "CONTENT CHANGED"
            else: st = "MISSING"
        w.writerow([k, p, st, " | ".join(same[:5]) + (f" (+{len(same)-5})" if len(same) > 5 else "")])
        print(f"{k:30} {st:35} copies_in_t2={len(same)}")
