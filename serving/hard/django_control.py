#!/usr/bin/env python3
"""How much of Nemotron's Django score is lost to the reasoning channel?

Nemotron's b3 thinking arm scores Django 22/50 against its own off arm's 39 --
the only category that moves down, while Bash/SQL/Python move +12/+9/+6. The
cause is not capability: 21 Django tasks returned finish_reason=stop with EMPTY
content, and 19 of those traces end with a closing code fence. The model wrote
the answer inside the reasoning channel and closed cleanly.

Only a 400-char tail of each trace is stored, so the answers cannot be recovered
from the results file. This re-runs exactly those tasks with the same profile and
budget, keeps reasoning_content, and grades the arm again with those answers
substituted in. It changes nothing about the published number: it measures what
the published number is missing.

Nothing here touches the graders. The substituted text goes through the same
b3.py grade path as any other answer.
"""
import json
import os
import subprocess
import sys
import urllib.request

REPO = "/Volumes/Store/Developer/AER/local-ai-benchmarks"
sys.path.insert(0, REPO + "/harness")
import b3  # noqa: E402

MODEL = "nvidia-nemotron-3.5-lightning-30b-a3b"
URL = "http://localhost:1234/v1/chat/completions"
SRC = REPO + "/results/mac/t_nemotron.json"
OUT = REPO + "/results/mac/t_nemotron.djctl.json"

raw = json.load(open(SRC))
items = raw["items"]
targets = [k for k, v in items.items()
           if v["cat"] == "Django" and not (v.get("text") or "").strip()
           and v.get("finish") == "stop"]
print(f"{len(targets)} Django tasks to re-run: {targets}", flush=True)

prompts = {t[0]: t for t in b3.all_tasks()} if hasattr(b3, "all_tasks") else {}
recovered = 0
for i, tid in enumerate(targets, 1):
    task = prompts.get(tid)
    if not task:
        print(f"  {tid}: not found in task list", flush=True)
        continue
    prompt = task[3]
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
               "max_tokens": 8000, "temperature": 0}
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=1800).read())
    except Exception as e:  # noqa: BLE001
        print(f"  [{i}/{len(targets)}] {tid}: ERROR {type(e).__name__}", flush=True)
        continue
    msg = d["choices"][0]["message"]
    content = (msg.get("content") or "").strip()
    trace = msg.get("reasoning_content") or msg.get("reasoning") or ""
    # Prefer a real answer if one arrived this time; otherwise take the trace and
    # let b3's own extractor find the fenced block, exactly as it would in content.
    text = content or trace
    if text:
        items[tid]["text"] = text
        items[tid]["_djctl"] = "recovered from reasoning_content" if not content else "answered normally"
        recovered += 1
    print(f"  [{i}/{len(targets)}] {tid}: content={len(content)}ch trace={len(trace)}ch "
          f"-> {'recovered' if text else 'still empty'}", flush=True)

json.dump(raw, open(OUT, "w"))
print(f"\n{recovered}/{len(targets)} recovered -> {OUT}", flush=True)

env = dict(os.environ, B4_TMP=REPO + "/results/mac/tmp/grade")
subprocess.run([sys.executable, "-u", "b3.py", "grade", OUT],
               cwd=REPO + "/harness", env=env)
