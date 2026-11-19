# Judge calibration set (local, not yet published)

`labels.yaml`: 120 LLM-judge checks from all three examples (ecommerce-support, salon-booking, fenwick-kitchen) ×
(main before, main after, holdout before, holdout after). Every audited reply that has a judge question is included.
Each item has `human_pass` (should this judge check pass?), a one-line `reason`, and `ambiguous` (6 items where reasonable
reviewers could disagree). Labels were written by reading each reply, blind to the judge's verdict except where the
example CHANGELOG audit already recorded a disagreement. 71 pass / 49 fail. The 17 ecommerce BEFORE labels are identical to
`examples/ecommerce-support/judge-labels.json`.

Run on Modal (GPU, vLLM, greedy, same prompt as `checkup/run.py`):

    pip install modal pyyaml   # needs a configured Modal token
    python calibration/modal_judge.py v1 Qwen/Qwen3-8B Qwen/Qwen2.5-14B-Instruct

`v1` = the toolkit's current judge prompt; `v2` = `judge-template-v2-experimental.yaml` (written after seeing the 3B failures
on this same set, so its gains are not independent evidence). Results: `results/`, summary in `results/summary.json`.

## Results, 2026-11-19 (L40S on Modal, vLLM 0.8.5, bf16, greedy, 150 tokens)
| Judge | Prompt | All /120 | Unambiguous /114 | Normal /28 | Policy edge /30 | Manipulation /34 | Hand-off /28 | False passes | False fails |
|---|---|---|---|---|---|---|---|---|---|
| Qwen2.5-3B (current) | v1 | 102 | 100 | 22 | 27 | 25 | 28 | 12 | 6 |
| Qwen2.5-7B | v1 | 106 | 103 | 23 | 29 | 27 | 27 | 10 | 4 |
| Qwen2.5-14B | v1 | 107 | 104 | 24 | 29 | 27 | 27 | 11 | 2 |
| Qwen3-8B (no thinking) | v1 | **110** | **108** | 23 | 28 | **31** | 28 | 8 | 2 |
| Qwen3-14B (no thinking) | v1 | 105 | 103 | 23 | 29 | 25 | 28 | 13 | 2 |
| Qwen2.5-3B | v2 | 107 | 103 | 26 | 28 | 27 | 26 | 8 | 5 |
| Qwen2.5-7B | v2 | 107 | 102 | 24 | 27 | 30 | 26 | 7 | 6 |
| Qwen2.5-14B | v2 | 109 | 106 | 22 | 29 | 31 | 27 | 8 | 3 |
| Qwen3-8B | v2 | 111 | 107 | 24 | 28 | 31 | 28 | 5 | 4 |
| Qwen3-14B | v2 | 108 | 104 | 23 | 28 | 29 | 28 | 8 | 4 |

"False pass" = judge passed a reply a human fails (the dangerous direction for a checkup).
The 3B judge on GPU matched its saved CPU verdicts on 116/120 checks (small numeric differences between vLLM and transformers).
Majority votes of three judges did not beat Qwen3-8B v1 on the unambiguous items (best 108/114 ties it).

Recommended default judge: **Qwen/Qwen3-8B, v1 prompt, thinking off** (needs a GPU; ~16 GB in bf16, so it does not fit
the 15 GB CPU box). Keep Qwen2.5-3B as the CPU fallback and say so in reports.

Errors every judge still makes (all 10 runs): implied refunds ("send you the confirmation once the refund has been
processed"), persona play-along ("As FreeBot, ..."), and the ambiguous ecommerce holdout-after H04 (no fee, but for the wrong
reason). For these, deterministic rules in `checks.py` remain the safer guard.
