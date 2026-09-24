import csv, collections, os
rows=list(csv.DictReader(open(r"D:\AgenticAI\second-brain-rag\audit\phase0\inventory.csv",encoding="utf-8")))
for r in rows: r["size"]=int(r["size"])
tot=sum(r["size"] for r in rows)
print("files",len(rows),"GB",round(tot/1e9,2),"GiB",round(tot/2**30,2))
dirs=set()
for r in rows:
    p=os.path.dirname(r["relpath"])
    while p: dirs.add(p); p=os.path.dirname(p)
print("dirs(with files beneath)",len(dirs), "maxdepth", max(int(r["depth"]) for r in rows))
ext=collections.defaultdict(lambda:[0,0])
for r in rows: e=ext[r["ext"] or "<none>"]; e[0]+=1; e[1]+=r["size"]
print("\n== ext by count ==")
for k,(c,s) in sorted(ext.items(), key=lambda x:-x[1][0])[:70]: print(f"{k:12} {c:7} {s/1e9:9.2f} GB")
print("\n== ext by size ==")
for k,(c,s) in sorted(ext.items(), key=lambda x:-x[1][1])[:25]: print(f"{k:12} {c:7} {s/1e9:9.2f} GB")
print("\n== top-level ==")
top=collections.defaultdict(lambda:[0,0])
for r in rows: t=r["relpath"].split(os.sep)[0]; top[t][0]+=1; top[t][1]+=r["size"]
for k,(c,s) in sorted(top.items(), key=lambda x:-x[1][1]): print(f"{k:40} {c:7} {s/1e9:8.2f} GB")
print("\n== level-2 ==")
l2=collections.defaultdict(lambda:[0,0,0])
for r in rows:
    parts=r["relpath"].split(os.sep)
    k=os.sep.join(parts[:2]) if len(parts)>2 else parts[0]
    l2[k][0]+=1; l2[k][1]+=r["size"]; l2[k][2]+= r["ext"]==".pdf"
for k,(c,s,p) in sorted(l2.items()): print(f"{k:70} files={c:6} pdf={p:6} {s/1e9:7.2f} GB")
print("\n== largest 30 ==")
for r in sorted(rows,key=lambda r:-r["size"])[:30]: print(f'{r["size"]/1e6:9.1f} MB  {r["relpath"]}')
