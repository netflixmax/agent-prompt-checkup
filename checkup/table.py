#!/usr/bin/env python3
"""Markdown test-set table: every case, what it checks, and before/after result.
python checkup/table.py cases.yaml results-before.json results-after.json [holdout-before.json holdout-after.json] > test-set.md"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from run import load_cases

def checks_text(c):
    parts = []
    for k, v in (c.get("checks") or {}).items():
        if isinstance(v, list): v = " / ".join(v)
        parts.append(f"{k}: `{v}`")
    for q in c.get("judge", []):
        parts.append(f"judge: {q}")
    return "<br>".join(parts).replace("|", "\\|")

def main():
    defaults, cases, meta = load_cases(sys.argv[1])
    res = {}
    for f in sys.argv[2:]:
        d = json.load(open(f))
        tag = "before" if "before" in os.path.basename(f) else "after"
        for r in d["rows"]: res[(r["id"], tag)] = r
    print(f"# Test set: {meta.get('name','')}\n")
    dc = defaults.get("checks", {})
    if dc: print("Checks applied to every case: " + "; ".join(f"{k}: `{v}`" for k, v in dc.items()) + "\n")
    print("A case passes only if every check passes. ✅ pass · ❌ fail\n")
    print("| ID | Category | Split | Customer message | Checks | Before | After |")
    print("|---|---|---|---|---|---|---|")
    for c in cases:
        b = res.get((c["id"], "before")); a = res.get((c["id"], "after"))
        mark = lambda r: "—" if r is None else ("✅" if r["pass"] else "❌")
        print(f"| {c['id']} | {c['category']} | {c.get('split','main')} | {c['input'].replace('|','/')} | {checks_text(c)} | {mark(b)} | {mark(a)} |")

if __name__ == "__main__":
    main()
