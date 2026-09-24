"""Phase-0 read-only inventory of D:/MBI-BRAIN. Reads only directory metadata (os.scandir/stat).
Usage: python inventory.py [output.csv]"""
import os, csv, sys, time
ROOT = r"D:\MBI-BRAIN"
OUT = sys.argv[1] if len(sys.argv) > 1 else r"D:\AgenticAI\second-brain-rag\audit\phase0\inventory.csv"
t = time.time(); n = 0
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["relpath", "ext", "size", "mtime", "depth"])
    stack = [ROOT]
    while stack:
        d = stack.pop()
        try:
            it = os.scandir(d)
        except OSError as e:
            print("ERR", d, e, file=sys.stderr); continue
        with it:
            for e in it:
                if e.is_dir(follow_symlinks=False): stack.append(e.path); continue
                st = e.stat(follow_symlinks=False)
                rel = os.path.relpath(e.path, ROOT)
                w.writerow([rel, os.path.splitext(e.name)[1].lower(), st.st_size, int(st.st_mtime), rel.count(os.sep)]); n += 1
print("files", n, "secs", round(time.time() - t, 1))
