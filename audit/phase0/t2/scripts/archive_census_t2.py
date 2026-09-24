"""Read-only archive census: reads ZIP central directories only (no extraction).
For each ZIP: member count/uncompressed size, whether a same-stem sibling directory exists, and how many file members
have a (basename, size) match somewhere in the T2 inventory (= content very likely already extracted; not a hash proof).
RAR/7z: listed only (no reader installed in the audit env)."""
import csv, os, json, zipfile, collections
ROOT = r"D:\MBI-BRAIN"; B = r"D:\AgenticAI\second-brain-rag\audit\phase0\t2"
inv = list(csv.DictReader(open(B + r"\inventory_t2.csv", encoding="utf-8")))
key = collections.Counter((os.path.basename(r["relpath"]).lower(), r["size"]) for r in inv)
dirs = set()
for r in inv:
    d = os.path.dirname(r["relpath"])
    while d: dirs.add(d.lower()); d = os.path.dirname(d)
out = open(B + r"\archive_census_t2.jsonl", "w", encoding="utf-8")
for r in inv:
    if r["ext"] not in (".zip", ".rar", ".7z", ".tar", ".gz", ".tgz"): continue
    rel = r["relpath"]; d = {"relpath": rel, "ext": r["ext"], "size": int(r["size"]),
                             "sibling_dir": os.path.splitext(rel)[0].lower() in dirs}
    if r["ext"] == ".zip":
        try:
            z = zipfile.ZipFile(os.path.join(ROOT, rel)); files = [i for i in z.infolist() if not i.is_dir()]
            def nm(i):
                n = i.filename
                if not i.flag_bits & 0x800:
                    try: n = n.encode("cp437").decode("utf-8")
                    except Exception: pass
                return os.path.basename(n).lower()
            present = sum(1 for i in files if key[(nm(i), str(i.file_size))] > 0)
            d.update(members=len(files), uncompressed=sum(i.file_size for i in files), members_present_by_name_size=present,
                     nested_archives=sum(1 for i in files if i.filename.lower().endswith((".zip", ".rar", ".7z"))),
                     member_exts=dict(collections.Counter(os.path.splitext(i.filename)[1].lower() for i in files).most_common(6)))
        except Exception as e: d["error"] = f"{type(e).__name__}: {str(e)[:100]}"
    out.write(json.dumps(d, ensure_ascii=False) + "\n")
out.close(); print("done")
