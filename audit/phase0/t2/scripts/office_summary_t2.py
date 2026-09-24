"""Summarize Office census by content-unique files (joins office_census_t2.jsonl with hashes_t2.csv)."""
import json, csv, collections, os
B = r"D:\AgenticAI\second-brain-rag\audit\phase0\t2"
H = {r["relpath"]: (r["hash"], r["size"]) for r in csv.DictReader(open(os.path.join(B, "hashes_t2.csv"), encoding="utf-8")) if r["mode"] == "full"}
D = [json.loads(l) for l in open(os.path.join(B, "office_census_t2.jsonl"), encoding="utf-8")]
u = {}
for d in D:
    k = H.get(d["relpath"], ("nohash:" + d["relpath"], ""))
    u.setdefault(k, d)
U = list(u.values()); S = {"paths": len(D), "unique_contents": len(U), "errors_paths": sum("error" in d for d in D)}
for e in sorted({d["ext"] for d in U}):
    s = [d for d in U if d["ext"] == e]
    if s[0].get("kind") == "ooxml" or e in (".docx", ".pptx", ".ppsx", ".xlsx", ".dotx"):
        S[e] = {"unique": len(s), "with_omml": sum(d.get("omath", 0) > 0 for d in s), "omath_total": sum(d.get("omath", 0) for d in s),
                "omathpara_total": sum(d.get("omathpara", 0) for d in s), "with_eq3_ole": sum(d.get("ole_equation_editor", 0) > 0 for d in s),
                "eq3_ole_total": sum(d.get("ole_equation_editor", 0) for d in s), "with_mathtype_ole": sum(d.get("ole_mathtype", 0) > 0 for d in s), "errors": sum("error" in d for d in s)}
    else:
        S[e] = {"unique": len(s), "sig_equation3_files": sum(d.get("sig_equation3", 0) > 0 for d in s), "sig_mathtype_files": sum(d.get("sig_mathtype", 0) > 0 for d in s),
                "sig_dsmt_files": sum(d.get("sig_dsmt", 0) > 0 for d in s), "not_ole2_header": sum(d.get("is_ole2") is False for d in s)}
dist = [d.get("omath", 0) for d in U if d.get("omath", 0) > 0]
S["omml_files_distribution"] = {">=100": sum(x >= 100 for x in dist), "20-99": sum(20 <= x < 100 for x in dist), "1-19": sum(x < 20 for x in dist)}
S["top_unique_omml"] = [(d["omath"], d.get("omathpara"), d["relpath"]) for d in sorted(U, key=lambda d: -d.get("omath", 0))[:12]]
json.dump(S, open(os.path.join(B, "office_census_t2_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(S, ensure_ascii=False, indent=1))
