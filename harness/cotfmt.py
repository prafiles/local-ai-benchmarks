#!/usr/bin/env python3
"""Does a format-preserving CoT instruction stop the export regression?

Measured on Qwen2.5-Coder: adding the CoT instruction made 27 of 50 TypeScript
answers drop the `export` keyword, against 0 of 50 at baseline. The TS prompts
literally begin with the word "export", so failing them is correct grading -- but
the cause is my instruction, not the model's reasoning. Injecting export back
recovers 23 -> 36 of 50, so 13 of the 25-task TS drop is pure format compliance
and only 12 is quality.

The suspect phrase is "exactly the requested output and nothing else", which the
model appears to read as "bare declaration". This tests naming the format
requirements explicitly instead.

    cotfmt.py <model> [n]
"""
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b3  # noqa: E402
import b3_jsts as J  # noqa: E402

URL = os.environ.get("B4_URL",
                     "http://localhost:8000/v1/chat/completions")
MODEL = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 8

# TS and JS are the categories with an explicit export requirement in the prompt
PROBES = [t[0] for t in J.TS[:N]] + [t[0] for t in J.JS[:N]]

NEW = ("\n\nDo not answer immediately. First write at least two sentences "
       "explaining your approach and any edge cases. Then write ANSWER: on its "
       "own line, followed by the answer in exactly the format the task asked "
       "for -- keeping every keyword it specified, such as export or "
       "module.exports -- and nothing else.")

TASKS = {t[0]: t for t in b3.all_tasks()}


def one(job):
    tid, instr = job
    _t, _c, _k, prompt, _m = TASKS[tid]
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt + instr}],
               "max_tokens": 8000, "temperature": 0}
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=1800).read())
    except Exception:  # noqa: BLE001
        return (tid, False, False)
    text = d["choices"][0]["message"]["content"] or ""
    b3.COT_SPLIT = True
    code = b3.code_of(text)
    b3.COT_SPLIT = False
    exported = bool(re.search(r"^\s*export\b", code, re.M)
                    or "module.exports" in code)
    return (tid, exported, "ANSWER:" in text)


print("### export retention on %s, %d probes" % (MODEL, len(PROBES)), flush=True)
for name, instr in (("current", b3.COT_SUFFIX), ("format-preserving", NEW)):
    with ThreadPoolExecutor(max_workers=4) as ex:
        rows = list(ex.map(one, [(t, instr) for t in PROBES]))
    print("  %-18s kept export %2d/%d   used marker %2d/%d"
          % (name, sum(r[1] for r in rows), len(rows),
             sum(r[2] for r in rows), len(rows)), flush=True)
    bad = [r[0] for r in rows if not r[1]]
    if bad:
        print("       dropped export: %s" % bad[:8], flush=True)
