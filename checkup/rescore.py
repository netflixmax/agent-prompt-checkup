#!/usr/bin/env python3
"""Re-apply the RULE checks from the current cases file to saved replies (no model needed).
Judge results already stored in the results file are kept as they are.
Use this after you correct a rule, so every run (before and after) is scored by the same rules.
python checkup/rescore.py cases.yaml results-a.json [results-b.json ...]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from checks import RULES
from run import load_cases

def main():
    cases_file, files = sys.argv[1], sys.argv[2:]
    defaults, cases, _ = load_cases(cases_file)
    byid = {c["id"]: c for c in cases}
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        old = d["score"]["passed"]
        for row in d["rows"]:
            c = byid[row["id"]]
            judged = [x for x in row["checks"] if x["type"] == "judge"]
            res = []
            for scope, checks in (("default", defaults.get("checks", {})), ("case", c.get("checks", {}))):
                for k, v in checks.items():
                    ok, detail = RULES[k](row["reply"], v)
                    res.append({"type": "rule", "name": k if scope == "case" else f"{k} (all cases)", "pass": ok, "detail": detail})
            row["checks"] = res + judged
            row["pass"] = all(x["pass"] for x in row["checks"])
        d["score"] = {"passed": sum(r["pass"] for r in d["rows"]), "total": len(d["rows"])}
        d["by_category"] = {}
        for r in d["rows"]:
            b = d["by_category"].setdefault(r["category"], {"passed": 0, "total": 0}); b["total"] += 1; b["passed"] += r["pass"]
        d.setdefault("rescored", []).append(f"rules re-applied from {os.path.basename(cases_file)}")
        json.dump(d, open(f, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"{os.path.basename(f)}: {old} -> {d['score']['passed']}/{d['score']['total']}")

if __name__ == "__main__":
    main()
