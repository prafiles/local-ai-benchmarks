#!/usr/bin/env python3
"""Find sampling params that make thinking mode actually produce an answer.

The failure this exists to kill: at temperature 0 the reasoning trace never
terminates, so the whole token budget is spent inside <think> and the answer
comes back EMPTY. An empty answer grades as a failure, so an untuned reasoning
run would report "reasoning made the model worse" when what actually happened is
the harness truncated it mid-thought.

The metric here is therefore not quality -- it is: how often do we get a non-empty
answer, and what does it cost. Quality is what the 600-task run measures.

Phases, in decreasing order of how much they change the plan:

  1. CAPS. Can the trace be bounded at all? vLLM accepted reasoning_effort,
     max_thinking_tokens and a template thinking_budget without complaint, but
     accepting a field and honouring it are different things. If one of them
     works, the run gets several times cheaper and the answer rate goes to ~100%.
     Measured by trace length, not by whether the request 200s.
  2. SAMPLING. Which published profile actually terminates.
  3. CONCURRENCY. Decode is memory-bandwidth-bound, so several sequences in
     flight should be close to free. This sets the length of the real run.

    tune2.py <model> <label> [budget]
"""
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "/root/bench2")
import b3  # noqa: E402

URL = "http://localhost:8000/v1/chat/completions"
MODEL = sys.argv[1]
LABEL = sys.argv[2]
BUDGET = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
FAMILY = "gemma" if "gemma" in MODEL.lower() else "qwen"

# Mixed short-cap and long-cap. The short-cap categories are where an
# unterminated trace does the most damage: a 220-token answer sitting behind a
# 6000-token ramble is nearly all loss.
SMALL = ["sh-001", "git-001", "rag-001", "sql-001", "py-001", "rn-001"]
BIG = SMALL + ["dj-001", "js-001", "ts-001", "ssh-001", "gh-001", "doc-001"]

BASE = ({"temperature": 1.0, "top_p": 0.95, "top_k": 64} if FAMILY == "gemma"
        else {"temperature": 0.6, "top_p": 0.95, "top_k": 20})

CAPS = [
    ("cap-none", {}),
    ("cap-effort-low", {"reasoning_effort": "low"}),
    ("cap-maxthink-1500", {"max_thinking_tokens": 1500}),
    ("cap-tmplbudget-1500", {"_tmpl": {"thinking_budget": 1500}}),
]

# Each family's published thinking-mode profile, plus its documented
# anti-repetition variant for when a trace loops.
CONFIGS = [
    ("qwen-rec", {"temperature": 0.6, "top_p": 0.95, "top_k": 20}),
    ("qwen-pen", {"temperature": 0.7, "top_p": 0.8, "top_k": 20,
                  "presence_penalty": 1.0}),
    ("gemma-rec", {"temperature": 1.0, "top_p": 0.95, "top_k": 64}),
    ("gemma-pen", {"temperature": 1.0, "top_p": 0.95, "top_k": 64,
                   "presence_penalty": 1.0}),
    ("greedy", {"temperature": 0}),
]

TASKS = {t[0]: t for t in b3.all_tasks()}


def one(tid, samp, cap):
    _t, cat, _k, prompt, mt = TASKS[tid]
    tmpl = {"enable_thinking": True}
    tmpl.update(cap.get("_tmpl", {}))
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
               "max_tokens": BUDGET, "chat_template_kwargs": tmpl}
    payload.update(samp)
    payload.update({k: v for k, v in cap.items() if k != "_tmpl"})
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=3600).read())
    except Exception as e:  # noqa: BLE001
        return {"tid": tid, "cat": cat, "err": "%s: %s" % (type(e).__name__, e),
                "secs": round(time.time() - t0, 1)}
    ch = d["choices"][0]
    msg = ch["message"]
    return {"tid": tid, "cat": cat, "cap": mt,
            "ans": len((msg.get("content") or "").strip()),
            "think": len(msg.get("reasoning") or msg.get("reasoning_content") or ""),
            "tok": d["usage"]["completion_tokens"],
            "finish": ch["finish_reason"], "secs": round(time.time() - t0, 1)}


def sweep(name, samp, cap, probes, workers):
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(lambda t: one(t, samp, cap), probes))
    wall = time.time() - t0
    good = [r for r in rows if not r.get("err")]
    ok = [r for r in good if r["ans"] > 0]
    trunc = [r for r in good if r["finish"] == "length"]
    tok = sum(r.get("tok", 0) for r in rows)
    # think_chars/4 is a rough token count -- good enough to tell a cap that
    # works from one that is silently ignored.
    th = sorted(r["think"] // 4 for r in good) or [0]
    print("  %-22s answered %2d/%d  trunc %2d  err %d | tok %6d  "
          "think~ med %5d max %5d | wall %5.0fs  agg %5.1f tok/s"
          % (name, len(ok), len(probes), len(trunc), len(rows) - len(good), tok,
             th[len(th) // 2], th[-1], wall, tok / wall if wall else 0), flush=True)
    for r in rows:
        if r.get("err"):
            print("       ! %-9s %s" % (r["tid"], r["err"][:70]), flush=True)
    return {"name": name, "samp": samp, "cap": cap, "workers": workers,
            "probes": probes, "answered": len(ok), "truncated": len(trunc),
            "errors": len(rows) - len(good), "tokens": tok,
            "think_med": th[len(th) // 2], "think_max": th[-1],
            "wall": round(wall, 1), "rows": rows}


out = {"model": MODEL, "budget": BUDGET, "family": FAMILY, "base": BASE, "sweeps": []}
print("### tuning %s (%s family)  budget=%d" % (LABEL, FAMILY, BUDGET), flush=True)


def save():
    json.dump(out, open("/root/bench2/tune_%s.json" % LABEL, "w"), indent=1)


print("\n-- 1. can the trace be capped? (base=%s, %d probes, 4 concurrent)"
      % (BASE, len(SMALL)), flush=True)
for name, cap in CAPS:
    out["sweeps"].append(sweep(name, BASE, cap, SMALL, 4))
    save()

uncapped = out["sweeps"][0]["think_med"]
works = [s for s in out["sweeps"][1:] if s["think_med"] < uncapped * 0.7]
CAP = works[0]["cap"] if works else {}
print("   -> cap that works: %s" % (works[0]["name"] if works else
                                    "NONE, all ignored -- budget must absorb the full trace"),
      flush=True)

print("\n-- 2. sampling (with that cap, %d probes)" % len(SMALL), flush=True)
for name, samp in CONFIGS:
    out["sweeps"].append(sweep(name, samp, CAP, SMALL, 4))
    save()

best = max((s for s in out["sweeps"] if s["name"] in dict(CONFIGS) and s["name"] != "greedy"),
           key=lambda s: (s["answered"], -s["tokens"]))
print("   -> best sampling: %s" % best["name"], flush=True)

print("\n-- 3. concurrency (on %s, %d probes)" % (best["name"], len(BIG)), flush=True)
for w in (1, 4, 8):
    out["sweeps"].append(sweep("workers=%d" % w, best["samp"], CAP, BIG, w))
    save()

out["chosen"] = {"sampling": best["samp"], "cap": CAP, "name": best["name"]}
save()
print("\nchosen: %s + %s" % (best["samp"], CAP), flush=True)
print("saved -> /root/bench2/tune_%s.json" % LABEL, flush=True)
