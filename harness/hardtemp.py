#!/usr/bin/env python3
"""Pick the first-attempt temperature, measured on the probes that actually fail.

Established so far, on Qwen3.5:

  * No trace cap exists -- reasoning_effort, max_thinking_tokens and the
    template's thinking_budget are accepted and ignored.
  * Budget is not the lever. Doubling 8000 -> 16000 doubled five of six traces
    (sh-001 6025 -> 12432, dj-001 7204 -> 15336) instead of letting them finish.
    They do not want more room; they never stop.
  * So the trace is a genuine repetition loop at temperature 0, and temperature
    is what escapes it.

The earlier sampling sweep ranked configs on a probe set that was mostly trivial
(git/rag/rn finish in ~300 tokens), so it was ranking noise. This runs the same
comparison on the six probes that actually spiral, twice per config, because a
single pass at temperature > 0 cannot separate 4/6 from 6/6.

The winner becomes the FIRST attempt only. Anything that still comes back empty is
resampled hotter by ask(). So the goal is not "never spirals" -- it is the
coolest setting with a decent first-pass rate, since cooler is better for code
and every spiral costs a full budget in wasted tokens.

    hardtemp.py <model> [budget] [passes]
"""
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b3  # noqa: E402

URL = os.environ.get("B4_URL",
                     "http://localhost:8000/v1/chat/completions")
MODEL = sys.argv[1]
BUDGET = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
PASSES = int(sys.argv[3]) if len(sys.argv) > 3 else 2

HARD = ["sh-001", "sql-001", "ts-001", "dj-001", "doc-001", "py-001"]

CONFIGS = [
    ("t0.6/k20", {"temperature": 0.6, "top_p": 0.95, "top_k": 20}),
    ("t0.8/k20", {"temperature": 0.8, "top_p": 0.95, "top_k": 20}),
    ("t1.0/k64", {"temperature": 1.0, "top_p": 0.95, "top_k": 64}),
]


def _parse_configs(spec):
    """'name=temp,top_p,top_k' entries, whitespace separated, '-' to omit."""
    cfgs = []
    for entry in spec.split():
        name, _, vals = entry.partition("=")
        parts = (vals.split(",") + ["-", "-", "-"])[:3]
        samp = {}
        for field, v in zip(("temperature", "top_p", "top_k"), parts):
            if v and v != "-":
                samp[field] = int(v) if field == "top_k" else float(v)
        cfgs.append((name, samp))
    return cfgs


# Greedy is excluded above because it was measured unusable in thinking mode on
# the two vLLM models -- a conclusion about those models, not a law. Override to
# retest it: if thinking terminates at temperature 0 on a given model, both arms
# can run at identical sampling and the temperature confound disappears.
if os.environ.get("B4_HARD_CONFIGS"):
    CONFIGS = _parse_configs(os.environ["B4_HARD_CONFIGS"])

TASKS = {t[0]: t for t in b3.all_tasks()}


def one(job):
    tid, samp = job
    _t, _c, _k, prompt, _mt = TASKS[tid]
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
               "max_tokens": BUDGET}
    # How thinking is requested is server-specific. vLLM honours the template
    # kwarg; LM Studio's MLX engine drops it silently and those models think by
    # default, so there the correct payload is one that says nothing at all.
    # Sending the kwarg anyway would still have measured thinking mode, but for
    # the wrong reason -- see patch_lmstudio.py.
    if os.environ.get("B4_OFF_MECH") != "reasoning_effort":
        payload["chat_template_kwargs"] = {"enable_thinking": True}
    payload.update(samp)
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=3600).read())
    except Exception as e:  # noqa: BLE001
        return {"tid": tid, "err": type(e).__name__, "ans": 0, "tok": 0}
    ch, msg = d["choices"][0], d["choices"][0]["message"]
    return {"tid": tid,
            "think": len(msg.get("reasoning") or msg.get("reasoning_content") or "") // 4,
            "ans": len((msg.get("content") or "").strip()),
            "tok": d["usage"]["completion_tokens"], "finish": ch["finish_reason"]}


print("### first-attempt temperature on the hard probes, budget=%d, %d passes"
      % (BUDGET, PASSES), flush=True)
out = {}
for name, samp in CONFIGS:
    jobs = [(t, samp) for _ in range(PASSES) for t in HARD]
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        rows = list(ex.map(one, jobs))
    n = len(jobs)
    ok = sum(1 for r in rows if r["ans"] > 0)
    tok = sum(r["tok"] for r in rows)
    per = {}
    for r in rows:
        per.setdefault(r["tid"], []).append(1 if r["ans"] > 0 else 0)
    print("\n %-10s answered %2d/%d   tokens %6d   wall %4.0fs" % (name, ok, n, tok, time.time() - t0),
          flush=True)
    print("   " + "  ".join("%s %d/%d" % (t, sum(v), len(v)) for t, v in sorted(per.items())),
          flush=True)
    out[name] = {"samp": samp, "answered": ok, "n": n, "tokens": tok, "per": per,
                 "rows": rows}
    json.dump(out, open(os.path.join(os.environ.get("B4_OUT", "/root/bench2"), "hardtemp.json"), "w"), indent=1)

best = max(out.items(), key=lambda kv: (kv[1]["answered"], -kv[1]["tokens"]))
print("\n-> first attempt: %s  %s" % (best[0], best[1]["samp"]), flush=True)
print("saved -> %s" % os.path.join(os.environ.get("B4_OUT", "/root/bench2"),
                                   "hardtemp.json"), flush=True)
