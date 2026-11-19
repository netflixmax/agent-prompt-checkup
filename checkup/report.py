#!/usr/bin/env python3
"""One-page before/after report (HTML + 1600x1200 PNG).

python checkup/report.py --title "..." --before results-before.json --after results-after.json \
   [--holdout-before hb.json --holdout-after ha.json] --changes changes.txt --out report
"""
import argparse, html, json, os, shutil, subprocess

CATS = ["normal", "policy-edge", "manipulation", "escalate"]
CAT_LABEL = {"normal": "Normal questions", "policy-edge": "Policy edge cases", "manipulation": "Manipulation / injection", "escalate": "Must hand off to a human"}

def load(p): return json.load(open(p, encoding="utf-8")) if p else None

def first_fail(row):
    for c in row["checks"]:
        if not c["pass"]:
            if c["type"] == "judge":
                return f"judge check failed: {c['name']}"
            return f"{c['name']}: {c['detail']}"
    return ""

def pct(s): return round(100 * s["passed"] / s["total"]) if s["total"] else 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--before", required=True); ap.add_argument("--after", required=True)
    ap.add_argument("--holdout-before"); ap.add_argument("--holdout-after")
    ap.add_argument("--changes", required=True)
    ap.add_argument("--out", required=True, help="output path without extension")
    ap.add_argument("--note", default="", help="one line shown under the scores, e.g. a human audit")
    a = ap.parse_args()
    B, A = load(a.before), load(a.after)
    HB, HA = load(a.holdout_before), load(a.holdout_after)
    changes = [l.strip("-• \n") for l in open(a.changes, encoding="utf-8") if l.strip()][:5]

    bars = ""
    for c in CATS:
        b = B["by_category"].get(c); af = A["by_category"].get(c)
        if not b: continue
        bars += f"""<div class="cat"><div class="cl">{CAT_LABEL[c]}</div>
          <div class="bars"><div class="bar"><span class="b" style="width:{pct(b)}%"></span><em>{b['passed']}/{b['total']}</em></div>
          <div class="bar"><span class="a" style="width:{pct(af)}%"></span><em>{af['passed']}/{af['total']}</em></div></div></div>"""

    fails = [r for r in A["rows"] if not r["pass"]]
    if HA: fails += [dict(r, id=r["id"] + " (holdout)") for r in HA["rows"] if not r["pass"]]
    fail_html = "".join(f"<li><b>{html.escape(r['id'])}</b> {html.escape(r['input'][:60])}<br><span>{html.escape(first_fail(r)[:95])}</span></li>" for r in fails[:2])
    if len(fails) > 2: fail_html += f"<li class='more'>+ {len(fails)-2} more, each listed in test-set.md</li>"
    if not fails: fail_html = "<li>None on this test set.</li>"

    hold = ""
    if HB and HA:
        hold = f"""<div class="hold"><div class="k">Unseen holdout set<br><small>written before fixing, run once</small></div>
           <div class="v">{HB['score']['passed']}/{HB['score']['total']} → <b>{HA['score']['passed']}/{HA['score']['total']}</b></div></div>"""

    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{width:1600px;height:1200px;background:#eef1f5;font-family:'Inter','Helvetica Neue',Arial,sans-serif;color:#1b2430}}
    .card{{position:absolute;left:80px;top:70px;width:1440px;height:1060px;background:#fff;border-radius:28px;padding:46px 64px;box-shadow:0 8px 40px rgba(20,30,50,.08)}}
    .tag{{display:inline-block;background:#fff4d6;color:#8a5a00;font-weight:700;font-size:18px;padding:7px 16px;border-radius:99px;letter-spacing:.3px}}
    h1{{font-size:36px;margin:16px 0 4px;letter-spacing:-.5px}}
    .sub{{font-size:20px;color:#5b6677}}
    .top{{display:flex;gap:28px;margin:28px 0 26px;align-items:stretch}}
    .score{{flex:0 0 560px;background:#f6f8fb;border-radius:22px;padding:20px 30px}}
    .score .k{{font-size:18px;color:#5b6677;font-weight:600;text-transform:uppercase;letter-spacing:1px}}
    .score .v{{font-size:72px;font-weight:800;letter-spacing:-2px;margin-top:6px}}
    .score .v .bf{{color:#c0392b}} .score .v .af{{color:#16815a}} .score .v .ar{{color:#9aa4b2;font-size:60px;margin:0 10px}}
    .hold{{flex:1;background:#f6f8fb;border-radius:22px;padding:20px 30px}}
    .hold .k{{font-size:18px;color:#5b6677;font-weight:600;text-transform:uppercase;letter-spacing:1px}}
    .hold small{{text-transform:none;letter-spacing:0;font-weight:500}}
    .hold .v{{font-size:52px;font-weight:800;margin-top:10px;color:#334}}
    .hold .v b{{color:#16815a}}
    .note{{font-size:17px;color:#5b4a00;background:#fffaeb;border-left:5px solid #f0b429;padding:10px 16px;border-radius:8px;margin:-12px 0 24px}}
    .grid{{display:flex;gap:44px}}
    .col{{flex:1}}
    h2{{font-size:20px;margin-bottom:12px;color:#334}}
    .legend{{font-size:16px;color:#5b6677;margin:-8px 0 14px}} .legend i{{display:inline-block;width:14px;height:14px;border-radius:3px;margin:0 6px -2px 14px}}
    .cat{{margin-bottom:12px}} .cl{{font-size:17px;font-weight:600;margin-bottom:5px}}
    .bar{{position:relative;height:19px;background:#edf0f4;border-radius:6px;margin-bottom:5px}}
    .bar span{{position:absolute;left:0;top:0;bottom:0;border-radius:6px}} .b{{background:#e8a19a}} .a{{background:#2fb47c}}
    .bar em{{position:absolute;right:8px;top:0;font-style:normal;font-size:14px;font-weight:700;color:#334}}
    ul{{list-style:none}} li{{font-size:16px;line-height:1.35;margin-bottom:8px;padding-left:22px;position:relative}}
    .ch li:before{{content:'✓';position:absolute;left:0;color:#16815a;font-weight:800}}
    .fl li:before{{content:'✗';position:absolute;left:0;color:#c0392b;font-weight:800}}
    .fl li span{{color:#6b7585;font-size:14px}} .fl li.more:before{{content:''}}
    .foot{{position:absolute;left:64px;right:64px;bottom:28px;font-size:13.5px;color:#7b8594;border-top:1px solid #e6e9ee;padding-top:14px;line-height:1.5}}
    </style></head><body><div class="card">
    <span class="tag">SELF-INITIATED SAMPLE · fictional business</span>
    <h1>{html.escape(a.title)}</h1><div class="sub">{html.escape(a.subtitle)}</div>
    <div class="top"><div class="score"><div class="k">Cases passed, same set: before → after</div>
      <div class="v"><span class="bf">{B['score']['passed']}</span><span class="ar">/{B['score']['total']} →</span><span class="af">{A['score']['passed']}</span><span class="ar">/{A['score']['total']}</span></div></div>{hold}</div>
    {f'<div class="note">{html.escape(a.note)}</div>' if a.note else ''}<div class="grid"><div class="col"><h2>By category</h2><div class="legend"><i style="background:#e8a19a;margin-left:0"></i>before<i style="background:#2fb47c"></i>after</div>{bars}</div>
    <div class="col"><h2>What I changed</h2><ul class="ch">{''.join(f'<li>{html.escape(c)}</li>' for c in changes)}</ul>
    <h2 style="margin-top:16px">Still failing (reported as-is)</h2><ul class="fl">{fail_html}</ul></div></div>
    <div class="foot">Model under test: {A['model']} · greedy decoding, max {A['settings']['max_new_tokens']} new tokens, CPU · Judge: {A['judge_model']} (quote-then-verdict) + rule checks · a case passes only if every check passes · run {A['run_at']} · prompts {B['prompt_sha256']} → {A['prompt_sha256']} · tool: agent-prompt-checkup</div>
    </div></body></html>"""
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    open(a.out + ".html", "w", encoding="utf-8").write(page)
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if chrome:
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1600,1200",
                        f"--screenshot={os.path.abspath(a.out)}.png", "file://" + os.path.abspath(a.out + ".html")],
                       check=True, capture_output=True)
    print("wrote", a.out + ".html", "and .png" if chrome else "(no chrome: PNG skipped)")

if __name__ == "__main__":
    main()
