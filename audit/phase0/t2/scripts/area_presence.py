"""Presence of selected areas across t0/t1/t2 inventories (metadata only)."""
import csv, os
B = r"D:\AgenticAI\second-brain-rag\audit\phase0"
SEP = os.sep
for f in ("inventory_t0.csv", "inventory_t1.csv", os.path.join("t2", "inventory_t2.csv")):
    R = [r["relpath"] for r in csv.DictReader(open(os.path.join(B, f), encoding="utf-8"))]
    top = lambda name: sum(p.startswith(name + SEP) for p in R)
    print(f, "| Ckurs", top("Ckurs"), "| English", top("English"),
          "| Information\\C", top("Information" + SEP + "C"),
          "| Information root files", sum(p.startswith("Information" + SEP) and p.count(SEP) == 1 for p in R),
          "| Betriebslehre root files", sum(p.startswith("Betriebslehre" + SEP) and p.count(SEP) == 1 for p in R))
