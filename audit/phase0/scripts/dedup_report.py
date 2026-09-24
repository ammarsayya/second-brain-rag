import csv,collections,os,json
B=r"D:\AgenticAI\second-brain-rag\audit\phase0"
inv={r["relpath"]:r for r in csv.DictReader(open(B+r"\inventory.csv",encoding="utf-8"))}
H=[r for r in csv.DictReader(open(B+r"\hashes.csv",encoding="utf-8")) if r["mode"]!="err"]
g=collections.defaultdict(list)
for r in H: g[(r["hash"],r["size"])].append(r)
dup={k:v for k,v in g.items() if len(v)>1}
red_files=sum(len(v)-1 for v in dup.values()); red_bytes=sum((len(v)-1)*int(k[1]) for k,v in dup.items())
print("hashed",len(H),"dup groups",len(dup),"redundant copies",red_files,"redundant GB",round(red_bytes/1e9,1))
print("errors",sum(1 for r in csv.DictReader(open(B+r"\hashes.csv",encoding="utf-8")) if r["mode"]=="err"))
byext=collections.defaultdict(lambda:[0,0,0])
for (h,s),v in dup.items():
    e=v[0]["ext"]; byext[e][0]+=1; byext[e][1]+=len(v)-1; byext[e][2]+=(len(v)-1)*int(s)
for e,(gc,rc,rb) in sorted(byext.items(),key=lambda x:-x[1][2])[:12]: print(f"  {e:8} groups={gc:6} redundant={rc:6} {rb/1e9:7.1f} GB")
# PDFs: unique vs total
pdf_all=[r for r in inv.values() if r["ext"]==".pdf"]
pdf_hash={(r["hash"],r["size"]) for r in H if r["ext"]==".pdf"}
print("PDF files",len(pdf_all),"unique PDF blobs",len(pdf_hash),"unique GB",round(sum(int(s) for _,s in pdf_hash)/1e9,1))
for e in (".docx",".pptx",".doc",".ppt",".xlsx",".txt"):
    n=sum(1 for r in inv.values() if r["ext"]==e); u=len({(r["hash"],r["size"]) for r in H if r["ext"]==e}); print(f"  {e}: files {n} unique {u}")
# mp4 unique (partial hash, size-collision only; singletons unique by size)
mp4=[r for r in inv.values() if r["ext"] in (".mp4",".avi",".mkv",".m4v",".mov",".webm")]
mh={(r["hash"],r["size"]) for r in H if r["ext"] in (".mp4",".avi",".mkv",".m4v",".mov",".webm")}
single=[r for r in mp4 if not any(True for _ in [0]) ] 
hashed_paths={r["relpath"] for r in H}
uniq_v=len(mh)+sum(1 for r in mp4 if r["relpath"] not in hashed_paths)
uvb=sum(int(s) for _,s in mh)+sum(int(r["size"]) for r in mp4 if r["relpath"] not in hashed_paths)
print("video files",len(mp4),"unique",uniq_v,"unique GB",round(uvb/1e9,1))
# folder-level mirror detection: pairs of directories sharing many blobs
dirblobs=collections.defaultdict(set)
for r in H:
    parts=r["relpath"].split(os.sep)
    for d in range(2,min(6,len(parts))): dirblobs[os.sep.join(parts[:d])].add((r["hash"],r["size"]))
blobdirs=collections.defaultdict(set)
for d,bs in dirblobs.items():
    if len(bs)>=10:
        for b in bs: blobdirs[b].add(d)
pair=collections.Counter()
for b,ds in blobdirs.items():
    ds=sorted(ds)
    if len(ds)<30:
        for i in range(len(ds)):
            for j in range(i+1,len(ds)):
                if not ds[j].startswith(ds[i]+os.sep) and not ds[i].startswith(ds[j]+os.sep): pair[(ds[i],ds[j])]+=1
mir=[]
for (a,b),n in pair.most_common(4000):
    ja=n/len(dirblobs[a]); jb=n/len(dirblobs[b])
    if ja>=0.9 and jb>=0.9 and len(dirblobs[a])>=20: mir.append((n,a,b,round(ja,2),round(jb,2)))
# keep maximal pairs (drop pairs whose parents are also mirrored)
mset={(a,b) for _,a,b,_,_ in mir}
top=[m for m in mir if (os.path.dirname(m[1]),os.path.dirname(m[2])) not in mset]
print("\nmirrored directory pairs (>=90% shared blobs, maximal):",len(top))
for n,a,b,ja,jb in sorted(top,reverse=True)[:30]: print(f"  {n:5} {a[:62]:62} <-> {b[:62]}")
# cross-top-level duplicates
cross=sum(1 for v in dup.values() if len({x['relpath'].split(os.sep)[0] for x in v})>1)
print("dup groups spanning >1 top-level folder",cross)
biggest=sorted(dup.values(),key=len,reverse=True)[:5]
for v in biggest: print("  x",len(v),v[0]["relpath"][:90])
json.dump([[x["relpath"] for x in v] for v in dup.values()],open(B+r"\dup_groups.json","w",encoding="utf-8"),ensure_ascii=False)
