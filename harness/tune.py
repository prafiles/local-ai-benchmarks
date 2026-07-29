#!/usr/bin/env python3
"""Find sampling params that make thinking mode actually produce an answer.

The failure this exists to kill: at temperature 0 the reasoning trace never
terminates, so the token budget is spent entirely inside <think> and the answer
comes back EMPTY. An empty answer grades as a failure, so an untuned reasoning
run would report "reasoning made the model worse" when what actually happened is
that the harness truncated it mid-thought.

So the metric here is not quality. It is: how often do we get a non-empty answer,
and how many tokens does that cost. Quality is what the 600-task run measures.

    tune.py <model> <label> [budget]

Runs every config over the same probe set, concurrently, and prints per-config
answer rate + token cost. Concurrency is also the throughput measurement: the
runner is sequential today and a 46h/model sequential run is not viable.
"""
import json
import os
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

# One per category, biased toward the short-cap categories -- those are where an
# unterminated trace does the most damage, because a 220-token answer sitting
# behind a 6000-token ramble is pure loss.
PROBES = ["py-001", "dj-001", "sql-001", "js-001", "ts-001", "sh-001",
          "git-001", "ssh-001", "gh-001", "doc-001", "rn-001", "rag-001"]

# Qwen publishes 0.6/0.95/20 for thinking and warns explicitly against greedy.
# Gemma's card gives 1.0/0.95/64. The rest are anti-repetition variants: if a
# trace loops, presence_penalty is the documented lever for both families.
CONFIGS = [
    ("greedy",      {"temperature": 0}),
    ("qwen-rec",    {"temperature": 0.6, "top_p": 0.95, "top_k": 20}),
    ("qwen-pen",    {"temperature": 0.7, "top_p": 0.8, "top_k": 20,
                     "presence_penalty": 1.0}),
    ("gemma-rec",   {"temperature": 1.0, "top_p": 0.95, "top_k": 64}),
    ("gemma-pen",   {"temperature": 1.0, "top_p": 0.95, "top_k": 64,
                     "presence_penalty": 1.0}),
]

# Does anything actually cap the trace? vLLM accepted all of these without
# complaint, but accepting a field and honouring it are different things -- the
# only way to tell is to send it and look at the trace length.
CAPS = [
    ("cap-none",   {}),
    ("cap-effort", {"reasoning_effort": "low"}),
    ("cap-maxthink", {"max_thinking_tokens": 1500}),
    ("cap-tmplbudget", {"_tmpl": {"thinking_budget": 1500}}),
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


def sweep(name, samp, cap, workers):
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(lambda t: one(t, samp, cap), PROBES))
    wall = time.time() - t0
    ok = [r for r in rows if not r.get("err") and r["ans"] > 0]
    trunc = [r for r in rows if not r.get("err") and r.get("finish") == "length"]
    errs = [r for r in rows if r.get("err")]
    tok = sum(r.get("tok", 0) for r in rows)
    print("  %-26s answered %2d/%d  truncated %2d  err %d  | tok %6d  "
          "wall %5.1fs  agg %5.1f tok/s"
          % (name, len(ok), len(PROBES), len(trunc), len(errs), tok, wall,
             tok / wall if wall else 0), flush=True)
    for r in rows:
        if r.get("err"):
            print("       ! %-9s %s" % (r["tid"], r["err"][:70]), flush=True)
    return {"name": name, "samp": samp, "cap": cap, "workers": workers,
            "answered": len(ok), "truncated": len(trunc), "errors": len(errs),
            "tokens": tok, "wall": round(wall, 1), "rows": rows}


out = {"model": MODEL, "budget": BUDGET, "sweeps": []}
print("### tuning %s  budget=%d  probes=%d" % (LABEL, BUDGET, len(PROBES)), flush=True)

print("\n-- sampling (4 concurrent)", flush=True)
for name, samp in CONFIGS:
    out["sweeps"].append(sweep(name, samp, {}, 4))

# Only worth testing trace caps against a config that already answers.
best = max((s for s in out["sweeps"] if s["name"] != "greedy"),
           key=lambda s: (s["answered"], -s["tokens"]))
print("\n-- trace caps, on top of %s" % best["name"], flush=True)
for name, cap in CAPS:
    out["sweeps"].append(sweep(name, best["samp"], cap, 4))

print("\n-- concurrency, on %s" % best["name"], flush=True)
for w in (1, 2, 4, 8):
    out["sweeps"].append(sweep("workers=%d" % w, best["samp"], {}, w))

p = "/root/bench2/tune_%s.json" % LABEL
json.dump(out, open(p, "w"), indent=1)
print("\nsaved -> %s" % p, flush=True)
