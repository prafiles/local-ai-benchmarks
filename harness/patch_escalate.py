#!/usr/bin/env python3
"""Retry a spiralled request hotter, instead of running everything hot.

Measured on Qwen3.5, 6 probes per config, no trace cap available:

    t=0.6 top_p .95 top_k 20  (Qwen's own recommendation)   4/6 answered
    t=0.7 top_p .80 top_k 20 + presence_penalty 1.0         4/6 answered
    t=1.0 top_p .95 top_k 64                                6/6 answered

So temperature is what decides whether the trace terminates -- hotter sampling
escapes the repetition loop that eats the budget. The naive fix is to run the
whole suite at 1.0, but that trades accuracy on all 600 tasks to rescue the ~1 in
4 that spiral, and 1.0 is well above what Qwen recommends for correctness.

Escalating instead gets both: every task is first attempted at the recommended
setting, and only a task that came back with an EMPTY answer is resampled hotter.
A task that answers on the first try is scored on the vendor-recommended
sampling, which is the number worth reporting.

`temps` is recorded per task so the report can say how many answers came from a
hot retry rather than burying it.
"""
p = "/root/bench2/b3.py"
s = open(p).read()

if "ESCALATE" in s:
    print("already patched")
    raise SystemExit(0)

old = '''def _once(model, prompt, max_tokens):
    payload = sampling({"model": model,
                        "messages": [{"role": "user",
                                      "content": with_cot(model, prompt)}],
                        "max_tokens": budget(max_tokens)}, model)'''

new = '''# Temperature to use on each retry, hottest last. Only reached after an empty
# answer, so a task that works normally never sees these.
ESCALATE = [float(x) for x in
            os.environ.get("B4_ESCALATE", "0.9,1.0").split(",") if x.strip()]


def _once(model, prompt, max_tokens, temp=None):
    payload = sampling({"model": model,
                        "messages": [{"role": "user",
                                      "content": with_cot(model, prompt)}],
                        "max_tokens": budget(max_tokens)}, model)
    if temp is not None:
        payload["temperature"] = temp'''

assert old in s, "_once() head did not match"
s = s.replace(old, new, 1)

old_ask = '''def ask(model, prompt, max_tokens):
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

new_ask = '''def ask(model, prompt, max_tokens):
    """Resample -- hotter each time -- only when the trace left no answer."""
    spent, used = 0.0, []
    r = None
    for attempt in range(RETRIES + 1):
        # attempt 0 uses the profile's own temperature; retries climb ESCALATE
        temp = None if attempt == 0 else ESCALATE[min(attempt - 1, len(ESCALATE) - 1)]
        r = _once(model, prompt, max_tokens, temp)
        spent += r["secs"]
        used.append(temp)
        if r["text"].strip():
            break
    r["attempts"] = len(used)
    r["temps"] = used
    r["secs"] = round(spent, 2)
    return r'''

assert old_ask in s, "ask() did not match"
s = s.replace(old_ask, new_ask, 1)
open(p, "w").write(s)
print("ask(): empty answers now resample at B4_ESCALATE temperatures")
