#!/usr/bin/env python3
"""Resample a request whose budget was eaten by the reasoning trace.

Measured on Qwen3.5 at its recommended sampling: no trace cap is available.
reasoning_effort, max_thinking_tokens and the template's thinking_budget are all
accepted by the server and all silently ignored -- proof is that sh-001 produced a
6538-token trace under a "1500-token cap" while producing 3041 uncapped, which no
real cap could do.

What the measurement does show is that spiralling is stochastic, not a property
of the task: sql-001 at identical settings produced 7119 tokens in one run and
471 in the next. So the same prompt, sampled again, usually terminates.

That makes a retry the honest repair. A truncated trace yields an EMPTY answer,
and an empty answer grades as a wrong answer -- scoring it would report a
capability failure where the truth is that the harness cut the model off
mid-sentence. Retrying is not giving the model extra chances at correctness: the
retry is triggered by an empty/truncated response, never by a wrong one, and a
retried task can still fail on its merits.

The cost is recorded per task (`attempts`) so the retry rate is visible in the
results rather than hidden inside a pass count.
"""
p = "/root/bench2/b3.py"
s = open(p).read()

if "RETRIES" in s:
    print("already patched")
    raise SystemExit(0)

old = '''# ------------------------------------------------------------------- runner
def ask(model, prompt, max_tokens):
    payload = sampling({"model": model,
                        "messages": [{"role": "user",
                                      "content": with_cot(model, prompt)}],
                        "max_tokens": budget(max_tokens)}, model)
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as r:
        d = json.loads(r.read())
    ch = d["choices"][0]
    msg = ch["message"]
    # vLLM 0.22 puts the chain of thought in `reasoning`, NOT `reasoning_content`;
    # `content` is left holding the final answer only, so graders need no change
    think = msg.get("reasoning") or msg.get("reasoning_content") or ""
    return {"text": msg.get("content") or "",
            "tok": d["usage"]["completion_tokens"],
            "think_chars": len(think),
            "finish": ch.get("finish_reason", ""),
            "secs": round(time.time() - t0, 2)}'''

new = '''# ------------------------------------------------------------------- runner
# Only ever spent on an EMPTY answer, never on a wrong one.
RETRIES = int(os.environ.get("B4_RETRIES", "0"))


def _once(model, prompt, max_tokens):
    payload = sampling({"model": model,
                        "messages": [{"role": "user",
                                      "content": with_cot(model, prompt)}],
                        "max_tokens": budget(max_tokens)}, model)
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as r:
        d = json.loads(r.read())
    ch = d["choices"][0]
    msg = ch["message"]
    # vLLM 0.22 puts the chain of thought in `reasoning`, NOT `reasoning_content`;
    # `content` is left holding the final answer only, so graders need no change
    think = msg.get("reasoning") or msg.get("reasoning_content") or ""
    return {"text": msg.get("content") or "",
            "tok": d["usage"]["completion_tokens"],
            "think_chars": len(think),
            "finish": ch.get("finish_reason", ""),
            "secs": round(time.time() - t0, 2)}


def ask(model, prompt, max_tokens):
    """Resample only when the trace ate the whole budget and left no answer."""
    spent, tries = 0.0, 0
    r = None
    for attempt in range(RETRIES + 1):
        r = _once(model, prompt, max_tokens)
        spent += r["secs"]
        tries = attempt + 1
        if r["text"].strip():
            break
    r["attempts"] = tries
    r["secs"] = round(spent, 2)
    return r'''

assert old in s, "ask() did not match"
open(p, "w").write(s.replace(old, new, 1))
print("ask(): resample on empty answer, B4_RETRIES (attempts recorded per task)")
