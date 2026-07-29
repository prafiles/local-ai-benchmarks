#!/usr/bin/env python3
"""Is the empty-answer problem budget or temperature?

The sampling sweep pointed at budget: failures clustered on two probes whose
traces ran 6000-7800 tokens against an 8000 cap that also had to hold the answer.
sql-001 spent 7450 tokens thinking and had 550 left to write in.

If that reading is right, the same probes at temperature 0 -- which the earlier
2-probe test wrongly convicted of never terminating -- will answer once the cap
stops cutting them off. Greedy is deterministic, so one run per cell settles it,
and if greedy works it is the sampling to use: the no-reasoning baseline was run
at temperature 0, so keeping it makes thinking the only variable that changed.

    budgettest.py <model> [budgets]
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
BUDGETS = [int(x) for x in (sys.argv[2].split(",") if len(sys.argv) > 2
                            else ["8000", "16000"])]
PROBES = ["sh-001", "sql-001", "py-001", "ts-001", "dj-001", "doc-001"]
TASKS = {t[0]: t for t in b3.all_tasks()}


def one(tid, bud):
    _t, cat, _k, prompt, _mt = TASKS[tid]
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
               "max_tokens": bud, "temperature": 0,
               "chat_template_kwargs": {"enable_thinking": True}}
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=3600).read())
    except Exception as e:  # noqa: BLE001
        return {"tid": tid, "bud": bud, "err": type(e).__name__}
    ch, msg = d["choices"][0], d["choices"][0]["message"]
    return {"tid": tid, "bud": bud,
            "think": len(msg.get("reasoning") or msg.get("reasoning_content") or "") // 4,
            "ans": len((msg.get("content") or "").strip()),
            "tok": d["usage"]["completion_tokens"],
            "finish": ch["finish_reason"], "secs": round(time.time() - t0, 1)}


print("### greedy (t=0), budgets %s" % BUDGETS, flush=True)
out = []
for bud in BUDGETS:
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        rows = list(ex.map(lambda t: one(t, bud), PROBES))
    out.extend(rows)
    ok = sum(1 for r in rows if r.get("ans", 0) > 0)
    tok = sum(r.get("tok", 0) for r in rows)
    print("\n budget %-6d answered %d/%d   tokens %6d   wall %.0fs"
          % (bud, ok, len(PROBES), tok, time.time() - t0), flush=True)
    for r in rows:
        if r.get("err"):
            print("   %-9s ERROR %s" % (r["tid"], r["err"]), flush=True)
        else:
            print("   %-9s think %5d  ans %5d  tok %5d  %s"
                  % (r["tid"], r["think"], r["ans"], r["tok"],
                     "TRUNCATED" if r["finish"] == "length" else "ok"), flush=True)
json.dump(out, open("/root/bench2/budgettest.json", "w"), indent=1)
print("\nsaved -> /root/bench2/budgettest.json", flush=True)
