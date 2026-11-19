# agent-prompt-checkup

**Test your support bot and get a before/after score.** Write down what real users will ask, say what a good answer must and must not contain, and see whether a prompt change actually helps — including on cases you never looked at while fixing.

- Runs a fixed test set (YAML or CSV) against a system prompt.
- Scores each reply with deterministic rule checks plus an LLM judge.
- Keeps a **holdout** set you never look at while fixing, so you can see whether a fix generalises or just fits the test set.
- Makes a one-page before/after report (HTML + 1600×1200 PNG) and a full test-set table.
- Runs on a laptop CPU with open models (Qwen2.5 1.5B as the bot, Qwen2.5 3B as the judge), so anyone can reproduce the numbers for free.

## Quick start
```bash
pip install -r requirements.txt          # torch, transformers, pyyaml

# 1. score the current prompt
python checkup/run.py --prompt examples/ecommerce-support/prompt-before.txt \
  --cases examples/ecommerce-support/cases.yaml --out before.json

# 2. edit the prompt, score it again on the same cases
python checkup/run.py --prompt my-new-prompt.txt \
  --cases examples/ecommerce-support/cases.yaml --out after.json

# 3. when you are done fixing: run the unseen holdout cases once, for both prompts
python checkup/run.py --prompt examples/ecommerce-support/prompt-before.txt --cases examples/ecommerce-support/cases.yaml --split holdout --out holdout-before.json
python checkup/run.py --prompt my-new-prompt.txt --cases examples/ecommerce-support/cases.yaml --split holdout --out holdout-after.json

# 4. report + table
python checkup/report.py --title "My bot checkup" --before before.json --after after.json \
  --holdout-before holdout-before.json --holdout-after holdout-after.json --changes changes.txt --out report
python checkup/table.py examples/ecommerce-support/cases.yaml before.json after.json > test-set.md
```
Options: `--model`, `--judge-model` (any Hugging Face chat model), `--no-judge` (rules only), `--max-new-tokens`.
Writing a test set: start from `templates/cases-template.yaml` or `templates/cases-template.csv`.

## How to read the score
- **A case passes only if every check on it passes.** Score = passed cases / all cases, also shown per category: normal questions, policy edge cases, manipulation/injection, and must-hand-off-to-a-human.
- **Main set vs holdout.** The main set is what you fix against, so its gain is partly fitted. The holdout set was written before fixing and run once, so it is the more honest number.
- **The judge is a small model and makes mistakes.** Read the failing cases, not just the total. Each case study includes a human audit of every reply.
- **Which judge?** Recommended: Qwen3-8B (thinking off) on a GPU, which agreed with human labels on 110/120 checks in our calibration; Qwen2.5-3B is the CPU fallback (102/120). Reports should say which judge was used. Details: [`calibration/README.md`](calibration/README.md).
- Full method and known limits: [`scoring.md`](scoring.md).

## Example case studies (self-initiated samples, fictional businesses)
All three use the same tool, model and judge. All numbers are real outputs from the files in each folder.

| Case study | Main set before → after | Holdout before → after | Human audit (main / holdout) |
|---|---|---|---|
| [E-commerce support bot](examples/ecommerce-support/) (returns, shipping, sizing) | 14/30 → 19/30 | 7/10 → 8/10 | 15→19 / 6→6 |
| [Hair salon SMS booking assistant](examples/salon-booking/) | 9/25 → 20/25 | 4/8 → 6/8 | 9→22 / 3→7 |
| [Restaurant takeout and delivery assistant](examples/fenwick-kitchen/) | 12/25 → 22/25 | 4/8 → 5/8 | 13→22 / 3→5 |

Each folder has `prompt-before.txt`, `prompt-after.txt` (and earlier versions), `cases.yaml`, every `results-*.json` (each reply, each check), `report.png`, `test-set.md` and `CHANGELOG.md`.

What these examples show honestly: on a 1.5B model, prompt changes fixed most everyday questions and most must-hand-off failures, but they also moved failures around. Injection and fake-authority cases did not always improve. In the e-commerce case the holdout did not improve after the human audit. In the restaurant case the holdout only rose by one automated case, and one hours question got worse. The change logs explain what I would change outside the prompt (a hand-off router, lookups done in code) for a real deployment.

## Files
```
checkup/run.py             run a test set, score every reply, save results JSON
checkup/checks.py          rule checks
checkup/report.py          one-page before/after report (HTML + PNG via headless Chrome)
checkup/table.py           markdown table of every case with before/after
checkup/rescore.py         re-apply corrected rules to saved replies (no model needed)
checkup/calibrate_judge.py measure judge agreement with your own labels
templates/                 YAML and CSV test-set templates
examples/                  three case studies
scoring.md                 scoring method and limits
```

## License
MIT
