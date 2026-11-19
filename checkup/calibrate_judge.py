#!/usr/bin/env python3
"""Measure how often the LLM judge agrees with human labels on existing replies.
python checkup/calibrate_judge.py results.json labels.json --cases cases.yaml [--judge-model ...]
labels.json maps case id -> true/false (should the judge check on that reply pass?)."""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import run as R

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results"); ap.add_argument("labels"); ap.add_argument("--cases", required=True)
    ap.add_argument("--judge-model", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--out")
    a = ap.parse_args()
    res = json.load(open(a.results)); lab = json.load(open(a.labels))
    _, cases, meta = R.load_cases(a.cases)
    byid = {c["id"]: c for c in cases}
    j = R.LocalModel(a.judge_model)
    agree = n = 0; rows = []
    for row in res["rows"]:
        if row["id"] not in lab: continue
        for q in byid[row["id"]].get("judge", []):
            ok, detail = R.judge_check(j, q, row["input"], row["reply"], meta.get("reference_facts", ""))
            n += 1; good = ok == lab[row["id"]]; agree += good
            rows.append({"id": row["id"], "question": q, "human": lab[row["id"]], "judge": ok, "detail": detail, "agree": good})
            print(f"{'agree   ' if good else 'DISAGREE'} {row['id']} human={lab[row['id']]} judge={ok} {detail}", flush=True)
    print(f"\nJUDGE AGREEMENT {agree}/{n}")
    if a.out: json.dump({"judge_model": a.judge_model, "agreement": [agree, n], "rows": rows}, open(a.out, "w"), indent=1)

if __name__ == "__main__":
    main()
