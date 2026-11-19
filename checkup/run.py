#!/usr/bin/env python3
"""Run a test set against a system prompt and score every reply.

Usage:
  python checkup/run.py --prompt my-prompt.txt --cases cases.yaml --out results.json \
      [--model Qwen/Qwen2.5-1.5B-Instruct] [--judge-model Qwen/Qwen2.5-3B-Instruct] [--split main|holdout|all]

A case passes only if EVERY check on it passes (rule checks + LLM-judge questions).
"""
import argparse, csv, hashlib, json, os, platform, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from checks import RULES

def load_cases(path):
    if path.endswith((".yaml", ".yml")):
        import yaml
        doc = yaml.safe_load(open(path, encoding="utf-8"))
        return doc.get("defaults", {}) or {}, doc["cases"], doc.get("meta", {})
    # CSV: id,category,split,input,must_include_any,must_not_include,must_not_match,max_chars,judge
    cases = []
    for r in csv.DictReader(open(path, encoding="utf-8")):
        c = {"id": r["id"], "category": r["category"], "split": r.get("split") or "main", "input": r["input"], "checks": {}}
        for k in ("must_include_any", "must_include_all", "must_not_include"):
            if r.get(k): c["checks"][k] = [x.strip() for x in r[k].split("|") if x.strip()]
        for k in ("must_match", "must_not_match"):
            if r.get(k): c["checks"][k] = r[k]
        if r.get("max_chars"): c["checks"]["max_chars"] = int(r["max_chars"])
        if r.get("judge"): c["judge"] = [q.strip() for q in r["judge"].split("|") if q.strip()]
        cases.append(c)
    return {}, cases, {}

class LocalModel:
    def __init__(self, name, threads=8):
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        torch.set_num_threads(threads)
        self.torch = torch
        self.name = name
        self.tok = AutoTokenizer.from_pretrained(name)
        self.model = AutoModelForCausalLM.from_pretrained(name, dtype=torch.bfloat16)
        self.model.eval()

    def chat(self, system, user, max_new_tokens):
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        kw = {"enable_thinking": False} if "qwen3" in self.name.lower() else {}  # Qwen3: answer directly, no <think> block
        enc = self.tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True, **kw)
        with self.torch.no_grad():
            out = self.model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False)
        return self.tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()

    def yes_prob(self, prompt):
        """Deterministic YES/NO judge: compare next-token probability of 'YES' vs 'NO'."""
        msgs = [{"role": "system", "content": "You are a strict QA reviewer for customer-facing AI assistants. Answer with exactly one word: YES or NO."},
                {"role": "user", "content": prompt}]
        enc = self.tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True)
        with self.torch.no_grad():
            logits = self.model(**enc).logits[0, -1]
        y = self.tok.encode("YES", add_special_tokens=False)[0]
        n = self.tok.encode("NO", add_special_tokens=False)[0]
        p = self.torch.softmax(logits[[y, n]].float(), dim=0)
        return float(p[0])

JUDGE_SYSTEM = "You are a careful QA reviewer of customer-support replies."
JUDGE_TEMPLATE = """Customer message: {input}

Assistant reply: {reply}

Question about the assistant reply: {question}

Judge only what the assistant reply literally says, even if it is factually wrong. First quote the most relevant sentence from the reply, then give a final line exactly "VERDICT: YES" or "VERDICT: NO"."""

def judge_check(judge, q, user_input, reply, facts=""):
    """LLM-judge check. Passes when the verdict is YES, or NO if the question starts with 'NO:'.
    The judge quotes the reply first (short reasoning), then gives a verdict; greedy decoding."""
    import re
    expect_yes = not q.startswith("NO:")
    question = q[3:].strip() if not expect_yes else q
    out = judge.chat(JUDGE_SYSTEM, JUDGE_TEMPLATE.format(input=user_input, reply=reply, question=question), 150)
    m = re.findall(r"VERDICT:\s*(YES|NO)", out)
    if not m:
        return False, "judge gave no verdict"
    said_yes = m[-1] == "YES"
    ok = said_yes if expect_yes else not said_yes
    why = re.sub(r"\s+", " ", out.split("VERDICT")[0]).strip()[:160]
    return ok, f"judge said {m[-1]} (expected {'YES' if expect_yes else 'NO'}): {why}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--judge-model", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--max-new-tokens", type=int, default=220)
    ap.add_argument("--split", default="main", choices=["main", "holdout", "all"])
    a = ap.parse_args()

    system = open(a.prompt, encoding="utf-8").read().strip()
    defaults, cases, meta = load_cases(a.cases)
    if a.split != "all":
        cases = [c for c in cases if c.get("split", "main") == a.split]
    facts = meta.get("reference_facts", "")

    bot = LocalModel(a.model)
    judge = None if a.no_judge else (bot if a.judge_model == a.model else LocalModel(a.judge_model))

    rows = []
    t0 = time.time()
    for c in cases:
        reply = bot.chat(system, c["input"], a.max_new_tokens)
        results = []
        for scope, checks in (("default", defaults.get("checks", {})), ("case", c.get("checks", {}))):
            for k, v in checks.items():
                ok, detail = RULES[k](reply, v)
                results.append({"type": "rule", "name": k if scope == "case" else f"{k} (all cases)", "pass": ok, "detail": detail})
        for q in list(defaults.get("judge", [])) + list(c.get("judge", [])):
            if judge is None: continue
            ok, detail = judge_check(judge, q, c["input"], reply, facts)
            results.append({"type": "judge", "name": q, "pass": ok, "detail": detail})
        passed = all(r["pass"] for r in results)
        rows.append({"id": c["id"], "category": c["category"], "split": c.get("split", "main"),
                     "input": c["input"], "reply": reply, "pass": passed, "checks": results})
        print(f"[{'PASS' if passed else 'FAIL'}] {c['id']:<8} {c['category']:<13} {reply[:90]!r}", flush=True)

    import transformers, torch
    out = {
        "label": a.label,
        "prompt_file": os.path.basename(a.prompt),
        "prompt_sha256": hashlib.sha256(system.encode()).hexdigest()[:12],
        "system_prompt": system,
        "cases_file": os.path.basename(a.cases),
        "split": a.split,
        "model": a.model,
        "judge_model": None if a.no_judge else a.judge_model,
        "settings": {"decoding": "greedy (do_sample=False)", "max_new_tokens": a.max_new_tokens, "dtype": "bfloat16",
                     "device": "cpu", "judge": "judge model quotes the reply then answers VERDICT: YES/NO (greedy, 150 tokens)",
                     "transformers": transformers.__version__, "torch": torch.__version__, "python": platform.python_version()},
        "run_at": time.strftime("%Y-%m-%d %H:%M %Z"),
        "runtime_sec": round(time.time() - t0, 1),
        "score": {"passed": sum(r["pass"] for r in rows), "total": len(rows)},
        "by_category": {},
        "rows": rows,
    }
    for r in rows:
        b = out["by_category"].setdefault(r["category"], {"passed": 0, "total": 0})
        b["total"] += 1; b["passed"] += r["pass"]
    json.dump(out, open(a.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\nSCORE {out['score']['passed']}/{out['score']['total']}  ->  {a.out}")
    for k, v in out["by_category"].items():
        print(f"  {k:<14} {v['passed']}/{v['total']}")

if __name__ == "__main__":
    main()
