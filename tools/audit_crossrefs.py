"""Cross-document ID reference audit: every ADR/task/question/risk/test-suite/requirement/spike ID referenced in docs
or CLAUDE.md must be defined in its register. Also checks that the implementation sequence respects dependencies.
Usage: python tools/audit_crossrefs.py   (exit 0 = clean)"""
import glob, os, re, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "docs")
# Keys are paths relative to docs/ (plain file names at the top level); subdirectories such as docs/reports/ are
# audited too, so dated reports cannot cite an undefined ID.
txt = {os.path.relpath(f, D): open(f, encoding="utf-8").read()
       for f in glob.glob(os.path.join(D, "**", "*"), recursive=True) if os.path.isfile(f)}
txt["CLAUDE.md"] = open(os.path.join(ROOT, "CLAUDE.md"), encoding="utf-8").read()
defs = {
    "ADR": set(re.findall(r"^### (ADR-\d+)", txt["24_DECISION_LOG.md"], re.M)),
    "T": set(re.findall(r"^### (T-P\d+-\d+)", txt["28_TASK_REGISTER.md"], re.M)),
    "Q": set(re.findall(r"^\| (Q-[BIN]\d+) ", txt["25_OPEN_QUESTIONS.md"], re.M)),
    "R": set(re.findall(r"^\| (R-\d+) ", txt["26_RISK_REGISTER.md"], re.M)),
    "TS": set(re.findall(r"^\| (TS-[A-Z]+(?:-\d)?) ", txt["33_TEST_STRATEGY.md"], re.M)),
    "REQ": set(re.findall(r"^\| ((?:HC|FR|NFR)-\d+) ", txt["02_REQUIREMENTS.md"], re.M)),
    "SPIKE": set(re.findall(r"^\| \*\*(SPIKE-[A-Z]+)\*\*", txt["34_RESEARCH_AND_SPIKE_REGISTER.md"], re.M)),
}
pats = {"ADR": r"ADR-\d+", "T": r"T-P\d+-\d+", "Q": r"Q-[BIN]\d+", "R": r"\bR-\d+\b", "REQ": r"\b(?:HC|FR|NFR)-\d+\b", "SPIKE": r"SPIKE-[A-Z]+"}
bad = collections.defaultdict(set)
for f, s in txt.items():
    for k, p in pats.items():
        for m in re.findall(p, s):
            if m not in defs[k]: bad[k].add((m, f))
    for m in re.findall(r"TS-[A-Z]+(?:-\d)?", s):
        if not any(d == m or d.startswith(m + "-") or m.startswith(d) for d in defs["TS"]): bad["TS"].add((m, f))
deps = {}
for b in re.split(r"^### ", txt["28_TASK_REGISTER.md"], flags=re.M)[1:]:
    m = re.match(r"(T-P\d+-\d+)", b)
    if m:
        d = re.search(r"- \*\*Dependencies:\*\* (.*)", b).group(1)
        deps[m.group(1)] = [] if d == "none" else [x.strip() for x in d.split(",")]
seq = txt["30_IMPLEMENTATION_SEQUENCE.md"].split("## Step 8 onward")[0]
order = list(dict.fromkeys(re.findall(r"T-P\d+-\d+", seq)))
pos = {x: i for i, x in enumerate(order)}
viol = [(x, d) for x in order for d in deps.get(x, []) if d in pos and pos[d] > pos[x] and not x.startswith("T-P0")]
ok = not any(bad.values()) and not viol
for k in defs: print(f"{k}: {len(defs[k])} defined, undefined refs: {sorted(bad[k])}")
print("sequence order violations:", viol)
print("CROSSREFS CLEAN" if ok else "CROSSREFS PROBLEMS")
sys.exit(0 if ok else 1)
