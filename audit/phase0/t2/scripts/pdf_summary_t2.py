"""Summarize the T2 PDF census (FULL CORPUS page counts; 5-probe-page signals = SAMPLE within docs) and t0 coverage."""
import json, collections, csv, os
B = r"D:\AgenticAI\second-brain-rag\audit\phase0"
D = [json.loads(l) for l in open(os.path.join(B, "t2", "pdf_census_t2.jsonl"), encoding="utf-8")]
ok = [d for d in D if "pages" in d]; err = [d for d in D if "pages" not in d]
S = {"unique_pdfs": len(D), "opened": len(ok), "open_errors": len(err), "open_error_classes": dict(collections.Counter(d["error"][:45] for d in err)),
     "partial_errors": sum("partial_error" in d for d in ok), "needs_password": sum(d.get("needs_pass", False) for d in ok),
     "encrypted_flag": sum(d.get("is_encrypted", False) for d in ok), "zero_page": sum(d["pages"] == 0 for d in ok),
     "total_unique_pages": sum(d["pages"] for d in ok), "fallback_path_used": sum(d["paths_tried"] > 1 for d in ok)}
pr = [d for d in ok if d.get("probe_pages")]
S["probe_docs"] = len(pr)
S["docs_all_probe_pages_textless"] = sum(d["notext"] == d["probe_pages"] for d in pr)
S["docs_>=80pct_probe_textless"] = sum(d["notext"] >= 0.8 * d["probe_pages"] for d in pr)
S["docs_any_probe_textless"] = sum(d["notext"] > 0 for d in pr)
S["est_textless_pages_EXTRAPOLATION"] = round(sum(d["pages"] * d["notext"] / d["probe_pages"] for d in pr))
S["est_mathfont_pages_EXTRAPOLATION_upper_bound"] = round(sum(d["pages"] * d["mathpages"] / d["probe_pages"] for d in pr))
S["docs_with_mathfont_on_any_probe_page"] = sum(d["mathpages"] > 0 for d in pr)
S["docs_with_annotations_on_probe_pages"] = sum(d["annots"] > 0 for d in pr)
S["docs_landscape_first_page"] = sum(d.get("landscape", False) for d in pr)
S["docs_ge200p"] = sum(d["pages"] >= 200 for d in ok); S["pages_in_ge200p"] = sum(d["pages"] for d in ok if d["pages"] >= 200)
S["docs_le40p"] = sum(d["pages"] <= 40 for d in ok); S["pages_in_le40p"] = sum(d["pages"] for d in ok if d["pages"] <= 40)
pg = sorted(d["pages"] for d in ok); q = lambda p: pg[int(p * (len(pg) - 1))]
S["pages_p10_p25_p50_p75_p90_p99_max"] = [q(x) for x in (.1, .25, .5, .75, .9, .99, 1)]
# t0 coverage by content
c0 = {(json.loads(l).get("hash"), str(json.loads(l).get("size"))) for l in open(os.path.join(B, "pdf_unique_pages.jsonl"), encoding="utf-8") if "pages" in json.loads(l)}
p0 = {r["relpath"] for r in (json.loads(l) for l in open(os.path.join(B, "pdf_probe.jsonl"), encoding="utf-8")) if "error" not in r}
h0 = {r["relpath"]: (r["hash"], r["size"]) for r in csv.DictReader(open(os.path.join(B, "hashes.csv"), encoding="utf-8")) if r["mode"] == "full"}
probed0 = {h0[p] for p in p0 if p in h0}
new = [d for d in ok if (d["hash"], str(d["size"])) not in c0]
S["t2_unique_pdfs_censused_at_t0"] = len(ok) - len(new); S["t2_unique_pdfs_NOT_censused_at_t0"] = len(new)
S["pages_NOT_censused_at_t0"] = sum(d["pages"] for d in new)
S["t2_unique_pdfs_probed_at_t0(25p probe)"] = sum((d["hash"], str(d["size"])) in probed0 for d in ok)
S["new_vs_t0_by_L2"] = dict(collections.Counter(os.sep.join(d["relpath"].split(os.sep)[:2]) for d in new).most_common(20))
S["largest_new_vs_t0"] = [(d["pages"], d["relpath"]) for d in sorted(new, key=lambda d: -d["pages"])[:15]]
json.dump(S, open(os.path.join(B, "t2", "pdf_census_t2_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(S, ensure_ascii=False, indent=1))
