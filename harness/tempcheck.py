#!/usr/bin/env python3
"""Is temperature 0 making the reasoning loop?

Qwen recommends temp 0.6 / top_p 0.95 for thinking mode; greedy decoding is known
to send reasoning models into repetition. If the truncations vanish at the
recommended sampling, then temp 0 -- not the task -- was burning the budget.
"""
import json
import sys
import urllib.request

URL = "http://localhost:8000/v1/chat/completions"
sys.path.insert(0, "/root/bench2")
import b3  # noqa: E402

model = sys.argv[1]
ids = sys.argv[2].split(",")
tasks = {t[0]: t for t in b3.all_tasks()}

MODES = [("greedy  t=0", {"temperature": 0}),
         ("qwen-rec t=0.6", {"temperature": 0.6, "top_p": 0.95, "top_k": 20})]

for tid in ids:
    _t, cat, _k, prompt, mt = tasks[tid]
    print(f"\n=== {tid} ({cat})  old cap {mt}")
    for label, samp in MODES:
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
                   "max_tokens": 6000, "chat_template_kwargs": {"enable_thinking": True}}
        payload.update(samp)
        req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=1800).read())
        except Exception as e:  # noqa: BLE001
            print(f"  {label:<16} ERROR {type(e).__name__}")
            continue
        ch = d["choices"][0]
        msg = ch["message"]
        content = msg.get("content") or ""
        think = msg.get("reasoning") or msg.get("reasoning_content") or ""
        print(f"  {label:<16} tok={d['usage']['completion_tokens']:<5} "
              f"finish={ch['finish_reason']:<7} think={len(think):>6}ch "
              f"answer={len(content):>5}ch")
