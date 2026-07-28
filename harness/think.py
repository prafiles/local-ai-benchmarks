#!/usr/bin/env python3
"""Shared reasoning-mode helpers + a calibration probe.

    think.py calib <model> [n_per_cat]

The switch is not the same across these models:
  Gemma 4    -- template defaults enable_thinking to FALSE; pass true to turn on
  Qwen3.5    -- template thinks unless enable_thinking is explicitly false
  Mellum2    -- no switch at all; the template only strips </think> out of history
  Qwen2.5    -- no thinking anywhere in the template; nothing to enable
so "enable reasoning on all models" is three models, not four.
"""
import json
import sys
import time
import urllib.request

URL = "http://localhost:8000/v1/chat/completions"

# model substring -> chat_template_kwargs needed to turn reasoning ON
THINK_ON = {
    "gemma-4": {"enable_thinking": True},
    "qwen3.5": {"enable_thinking": True},
    # Mellum2 and Qwen2.5-Coder have no switch; entries omitted deliberately
}

CAN_THINK = ("gemma-4", "qwen3.5", "mellum2")


def think_kwargs(model):
    m = model.lower()
    for k, v in THINK_ON.items():
        if k in m:
            return dict(v)
    return None


def ask(model, messages, max_tokens, thinking=True):
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens,
               "temperature": 0}
    if thinking:
        kw = think_kwargs(model)
        if kw:
            payload["chat_template_kwargs"] = kw
    else:
        m = model.lower()
        if "qwen3.5" in m or "gemma-4" in m:
            payload["chat_template_kwargs"] = {"enable_thinking": False}
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=3600) as r:
        d = json.loads(r.read())
    ch = d["choices"][0]
    msg = ch["message"]
    # with a reasoning parser active the chain of thought lands here, not in content
    reasoning = msg.get("reasoning_content") or ""
    return {"text": msg.get("content") or "", "reasoning": reasoning,
            "tok": d["usage"]["completion_tokens"], "ptok": d["usage"]["prompt_tokens"],
            "finish": ch.get("finish_reason", ""), "secs": round(time.time() - t0, 2)}


def calib(model, per_cat=2):
    sys.path.insert(0, "/root/bench2")
    import b3  # noqa: E402
    tasks = b3.all_tasks()
    seen, sample = {}, []
    for tid, cat, kind, prompt, mt in tasks:
        if seen.get(cat, 0) < per_cat:
            seen[cat] = seen.get(cat, 0) + 1
            sample.append((tid, cat, prompt, mt))
    print(f"calibrating {model} on {len(sample)} tasks, thinking ON, cap 4096")
    rows = []
    for tid, cat, prompt, mt in sample:
        try:
            r = ask(model, [{"role": "user", "content": prompt}], 4096, thinking=True)
        except Exception as e:  # noqa: BLE001
            print(f"  {tid:<9} ERROR {type(e).__name__}: {str(e)[:120]}")
            continue
        rt = len(r["reasoning"])
        rows.append((tid, cat, r["tok"], mt, r["finish"], rt, r["secs"]))
        print(f"  {tid:<9} {cat:<12} out={r['tok']:>5} (old cap {mt:>4}) "
              f"finish={r['finish']:<6} reasoning_chars={rt:>6} {r['secs']:>6.1f}s",
              flush=True)
    if not rows:
        return
    toks = sorted(x[2] for x in rows)
    over = [x for x in rows if x[2] > x[3]]
    trunc = [x for x in rows if x[4] == "length"]
    thought = [x for x in rows if x[5] > 0]
    print(f"\n  completion tokens: min {toks[0]}  median {toks[len(toks)//2]}  "
          f"p90 {toks[int(len(toks)*0.9)]}  max {toks[-1]}  mean {sum(toks)//len(toks)}")
    print(f"  would have blown the OLD budget: {len(over)}/{len(rows)}")
    print(f"  still truncated at 4096:         {len(trunc)}/{len(rows)}")
    print(f"  actually produced reasoning:     {len(thought)}/{len(rows)}")
    print(f"  total decode seconds for {len(rows)} tasks: {sum(x[6] for x in rows):.0f}")
    json.dump(rows, open(f"/root/bench2/calib_{model.split('/')[-1]}.json", "w"))


if __name__ == "__main__":
    if sys.argv[1] == "calib":
        calib(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 2)
