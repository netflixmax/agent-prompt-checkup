import json, os, re, sys, time, yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modal_judge_app import app, run_judge
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL + "/checkup")
import run as R
variant = sys.argv[1]; models = sys.argv[2:]
items = yaml.safe_load(open(TOOL + "/calibration/labels.yaml"))["items"]
if variant == "v1":
    SYSTEM, TEMPLATE = R.JUDGE_SYSTEM, R.JUDGE_TEMPLATE
else:
    T = yaml.safe_load(open(os.path.join(TOOL, "calibration", f"judge-template-{variant}-experimental.yaml")))
    SYSTEM, TEMPLATE = T["system"], T["template"]
prompts = []
for it in items:
    q = it["question"]; question = q[3:].strip() if q.startswith("NO:") else q
    prompts.append(TEMPLATE.format(input=it["input"], reply=it["reply"], question=question))
with app.run():
    calls = [(m, run_judge.spawn(m, prompts, SYSTEM, 150, "Qwen3" in m)) for m in models]
    for m, c in calls:
        t = time.time()
        r = c.get()
        rows = []
        for it, out in zip(items, r["outputs"]):
            v = re.findall(r"VERDICT:\s*(YES|NO)", out)
            expect_yes = not it["question"].startswith("NO:")
            ok = (v[-1] == "YES") == expect_yes if v else False
            rows.append({"uid": it["uid"], "category": it["category"], "human": it["human_pass"], "judge": ok,
                         "ambiguous": it["ambiguous"], "verdict": v[-1] if v else None, "raw": out})
        res = {"model": m, "variant": variant, "load_sec": r["load_sec"], "gen_sec": r["gen_sec"], "rows": rows}
        fn = os.path.join(TOOL, "calibration", "results", f"res-{variant}-{m.split('/')[-1]}.json")
        json.dump(res, open(fn, "w"), indent=1, ensure_ascii=False)
        agree = sum(x["human"] == x["judge"] for x in rows)
        print(f"{m} {variant}: {agree}/{len(rows)} load {r['load_sec']}s gen {r['gen_sec']}s", flush=True)
