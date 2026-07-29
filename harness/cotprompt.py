#!/usr/bin/env python3
"""Find a CoT instruction these models actually follow.

The first attempt prefixed the task with "work through this step by step inside
<think> tags" and Mellum2 ignored it completely -- bare answer, no tags, token
counts identical to baseline. The cause is a conflict the prefix could not win:
every task prompt ENDS with "Output only the code, no explanation." A prefix asks
for reasoning, the suffix forbids it, and the later instruction wins.

So the instruction has to come after the task and reconcile the contradiction
explicitly, scoping "output only" to what follows the reasoning. This measures
which phrasing actually produces reasoning, because an arm labelled "CoT" that
silently produced ordinary answers would be a fabricated column.

Success is not "the model rambled". It is BOTH: a non-trivial trace, AND a clean
answer left after the trace is stripped -- reasoning that eats the answer is the
same failure the native arm had.

    cotprompt.py <model> [workers]
"""
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "/root/bench2")
import b3  # noqa: E402

URL = "http://localhost:8000/v1/chat/completions"
MODEL = sys.argv[1]
WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 8
PROBES = ["py-001", "sql-001", "sh-001", "git-001", "ts-001", "doc-001",
          "js-001", "ssh-001"]

VARIANTS = [
    ("A prefix (current)", "prefix", b3.COT_PREFIX),
    ("B suffix, scoped", "suffix",
     "\n\nBefore answering, reason step by step inside <think> and </think> tags.\n"
     "The \"output only\" instruction above applies to what comes AFTER </think>: "
     "everything following the closing tag must be exactly the requested output "
     "and nothing else."),
    ("C suffix, plain", "suffix",
     "\n\nFirst think through this step by step inside <think> and </think> tags, "
     "then give the answer. Only the text after </think> counts as your answer, "
     "and it must follow the format asked for above exactly."),
    ("D suffix, no tags", "suffix",
     "\n\nWork through the problem step by step first. Then write the line "
     "ANSWER: on its own, and after it give exactly the requested output and "
     "nothing else."),
]

TASKS = {t[0]: t for t in b3.all_tasks()}


def split(text, mode):
    """Return (trace_chars, answer) the way the grader would see it."""
    if mode == "D":
        i = text.rfind("ANSWER:")
        return (i if i > 0 else 0), (text[i + 7:] if i >= 0 else text)
    body = b3.strip_think(text)
    return len(text) - len(body), body


def one(job):
    tid, kind, instr, letter = job
    _t, _c, _k, prompt, _mt = TASKS[tid]
    msg = instr + prompt if kind == "prefix" else prompt + instr
    payload = {"model": MODEL, "messages": [{"role": "user", "content": msg}],
               "max_tokens": 8000, "temperature": 0}
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=3600).read())
    except Exception as e:  # noqa: BLE001
        return {"tid": tid, "err": type(e).__name__}
    ch, m = d["choices"][0], d["choices"][0]["message"]
    text = m.get("content") or ""
    trace, ans = split(text, letter)
    return {"tid": tid, "trace": trace, "ans": len(ans.strip()),
            "tok": d["usage"]["completion_tokens"], "finish": ch["finish_reason"]}


print("### CoT instruction sweep on %s" % MODEL, flush=True)
best = None
for name, kind, instr in VARIANTS:
    letter = name[0]
    jobs = [(t, kind, instr, letter) for t in PROBES]
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        rows = list(ex.map(one, jobs))
    good = [r for r in rows if not r.get("err")]
    reasoned = sum(1 for r in good if r["trace"] > 200)
    answered = sum(1 for r in good if r["ans"] > 0)
    tok = sum(r.get("tok", 0) for r in rows)
    print("  %-20s reasoned %d/%d  answered %d/%d  tokens %6d"
          % (name, reasoned, len(PROBES), answered, len(PROBES), tok), flush=True)
    # both conditions matter: a trace that swallows the answer is not a win
    score = (min(reasoned, answered), -tok)
    if best is None or score > best[0]:
        best = (score, name, kind, instr)

print("\n-> %s" % best[1], flush=True)
json.dump({"name": best[1], "kind": best[2], "instr": best[3]},
          open("/root/bench2/cot_instr.json", "w"), indent=1)
print("saved -> /root/bench2/cot_instr.json", flush=True)
