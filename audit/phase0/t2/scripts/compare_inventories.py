"""Compare two inventory CSVs: added/removed paths, size/mtime changes, totals. Usage: compare_inventories.py a.csv b.csv"""
import csv, sys
L = lambda f: {r["relpath"]: r for r in csv.DictReader(open(f, encoding="utf-8"))}
a, b = L(sys.argv[1]), L(sys.argv[2])
add, rem = set(b) - set(a), set(a) - set(b)
ch = [p for p in set(a) & set(b) if (a[p]["size"], a[p]["mtime"]) != (b[p]["size"], b[p]["mtime"])]
tot = lambda x: sum(int(r["size"]) for r in x.values())
print(f"A files={len(a)} bytes={tot(a)} | B files={len(b)} bytes={tot(b)} | added={len(add)} removed={len(rem)} changed={len(ch)}")
for p in sorted(add)[:10]: print("  +", p)
for p in sorted(rem)[:10]: print("  -", p)
for p in sorted(ch)[:10]: print("  ~", p, a[p]["size"], a[p]["mtime"], "->", b[p]["size"], b[p]["mtime"])
