"""Read-only exact-duplicate detection. Full xxh3_128 for all document-type files and for
size-collision candidates <=512MB; head/mid/tail sampled hash (flagged 'partial') for larger collision candidates."""
import csv, os, collections, xxhash, time
ROOT=r"D:\MBI-BRAIN"; BASE=r"D:\AgenticAI\second-brain-rag\audit\phase0"
DOC={".pdf",".ppt",".pptx",".ppsx",".doc",".docx",".xls",".xlsx",".txt",".md",".tex",".odt",".rtf",".csv"}
rows=list(csv.DictReader(open(BASE+r"\inventory.csv",encoding="utf-8")))
bysize=collections.Counter(int(r["size"]) for r in rows)
def full(p):
    h=xxhash.xxh3_128()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(8<<20),b""): h.update(b)
    return h.hexdigest()
def part(p,sz):
    h=xxhash.xxh3_128(); h.update(str(sz).encode())
    with open(p,"rb") as f:
        for off in (0, sz//2, max(0,sz-(4<<20))):
            f.seek(off); h.update(f.read(4<<20))
    return h.hexdigest()
t=time.time(); out=open(BASE+r"\hashes.csv","w",newline="",encoding="utf-8"); w=csv.writer(out)
w.writerow(["relpath","ext","size","hash","mode"]); n=0; nb=0
for r in rows:
    sz=int(r["size"]); coll=bysize[sz]>1 and sz>0
    if not (r["ext"] in DOC or coll): continue
    p=os.path.join(ROOT,r["relpath"])
    try:
        if sz>512<<20 and r["ext"] not in DOC: hv,m=part(p,sz),"partial"
        else: hv,m=full(p),"full"; nb+=sz
    except OSError as e: hv,m="ERR:"+str(e)[:60],"err"
    w.writerow([r["relpath"],r["ext"],sz,hv,m]); n+=1
out.close(); print("hashed",n,"fullGB",round(nb/1e9,1),"secs",round(time.time()-t))
