#!/usr/bin/env python3
"""Two checks before committing hours to a prompted-CoT run.

1. REPRODUCIBILITY. The CoT arm is the one comparison here that can be clean:
   Mellum2 and Qwen2.5-Coder have no thinking mode, so nothing forces sampling off
   temperature 0 and only the prompt changes. That only holds if serving the model
   at a different --max-num-seqs does not change greedy output. Qwen2.5-Coder's
   baseline ran at 1, which would put a 600-task CoT run near 19 hours; this
   re-runs stored baseline prompts at the new concurrency and diffs against the
   answers already on disk. Identical means batching is not a variable and the
   speed-up is free. Different means it is, and the report has to say so.

2. TERMINATION. Whether prompted CoT at temperature 0 actually stops. Native
   thinking mode does not -- its traces grow to fill any budget -- but that is a
   trained mode, not a prompt, so it has to be measured separately rather than
   assumed to behave the same way.

    cotcheck.py <model> <baseline.json> [workers]
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
BASE = sys.argv[2]
WORKERS = int(sys.argv[3]) if len(sys.argv) > 3 else 4

TASKS = {t[0]: t for t in b3.all_tasks()}
prev = json.load(open(BASE))["items"]

# mix of short-answer and long-form, all present in the baseline
REPRO = [t for t in ["py-001", "sh-001", "git-001", "sql-001", "js-001",
                     "rag-001", "ssh-001", "doc-001"] if t in prev]
HARD = ["py-001", "dj-001", "sql-001", "ts-001", "sh-001", "doc-001"]


def ask(tid, cot, budget):
    _t, _c, _k, prompt, mt = TASKS[tid]
    if cot:
        prompt = b3.COT_PREFIX + prompt
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
               "max_tokens": budget if cot else mt, "temperature": 0}
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=3600).read())
    except Exception as e:  # noqa: BLE001
        return {"tid": tid, "err": type(e).__name__}
    ch, msg = d["choices"][0], d["choices"][0]["message"]
    return {"tid": tid, "text": msg.get("content") or "",
            "tok": d["usage"]["completion_tokens"], "finish": ch["finish_reason"]}


print("### %s   workers=%d" % (MODEL, WORKERS), flush=True)

print("\n-- 1. does batching change greedy output? (vs %s)" % BASE, flush=True)
t0 = time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    rows = list(ex.map(lambda t: ask(t, False, 0), REPRO))
same = 0
for r in rows:
    if r.get("err"):
        print("   %-9s ERROR %s" % (r["tid"], r["err"]), flush=True)
        continue
    old = (prev[r["tid"]].get("text") or "").strip()
    new = r["text"].strip()
    ok = old == new
    same += ok
    print("   %-9s %s" % (r["tid"], "identical" if ok else
                          "DIFFERS (old %d ch, new %d ch)" % (len(old), len(new))),
          flush=True)
print("   -> %d/%d identical in %.0fs" % (same, len(rows), time.time() - t0), flush=True)

print("\n-- 2. does prompted CoT terminate at temperature 0? (budget 8000)", flush=True)
t0 = time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    rows = list(ex.map(lambda t: ask(t, True, 8000), HARD))
answered = 0
for r in rows:
    if r.get("err"):
        print("   %-9s ERROR %s" % (r["tid"], r["err"]), flush=True)
        continue
    body = b3.strip_think(r["text"]).strip()
    tag = "<think>" in r["text"]
    closed = "</think>" in r["text"]
    answered += bool(body)
    print("   %-9s tok %5d  %-9s think-tag=%s closed=%s  answer %4d ch"
          % (r["tid"], r["tok"], r["finish"], tag, closed, len(body)), flush=True)
print("   -> %d/%d produced an answer after the trace, in %.0fs"
      % (answered, len(rows), time.time() - t0), flush=True)
