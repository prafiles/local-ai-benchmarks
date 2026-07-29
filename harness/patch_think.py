#!/usr/bin/env python3
"""Add a reasoning mode to both runners, controlled by environment variables.

    B4_THINK=1        turn reasoning on for models that have it
    B4_BUDGET=6000    floor for max_tokens (reasoning needs room; the old caps
                      were sized for a direct answer and are hopeless here)
    B4_BUDGET_MULT=6  multiplier applied to each task's original cap
    B4_TEMP=0.6       sampling temperature (0 = greedy, as the baseline runs used)
    B4_TOPP=0.95      nucleus cutoff, only sent when temperature > 0

Applied to b3.py (600 short tasks) and b4.py (60 long-context probes) so the two
suites stay consistent with each other.
"""
import re
import sys

ASK_HELPERS = '''
# --------------------------------------------------------------- reasoning
# Only two of the four models have a reasoning mode at all: Gemma 4 defaults
# enable_thinking to false in its template, and Qwen3.5 thinks unless told not
# to. Mellum2's template merely strips </think> out of history and Qwen2.5-Coder
# has no thinking in its template whatsoever -- for those two this is a no-op,
# which is the honest outcome rather than a fabricated one.
THINK = os.environ.get("B4_THINK") == "1"
BUDGET_FLOOR = int(os.environ.get("B4_BUDGET", "0"))
BUDGET_MULT = float(os.environ.get("B4_BUDGET_MULT", "1"))
TEMP = float(os.environ.get("B4_TEMP", "0"))
TOPP = float(os.environ.get("B4_TOPP", "0.95"))

THINK_CAPABLE = ("gemma-4", "qwen3.5")


def can_think(model):
    m = model.lower()
    return any(k in m for k in THINK_CAPABLE)


def budget(mt):
    return max(int(mt * BUDGET_MULT), BUDGET_FLOOR) if THINK else mt


def sampling(payload, model):
    payload["temperature"] = TEMP
    if TEMP > 0:
        payload["top_p"] = TOPP
    if can_think(model):
        # explicit either way: the flag is what separates the two arms
        payload["chat_template_kwargs"] = {"enable_thinking": bool(THINK)}
    return payload
'''


def patch_b3(src):
    src = src.replace(
        '''def ask(model, prompt, max_tokens):
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "max_tokens": max_tokens, "temperature": 0}
    # Qwen3.5 thinks by default and burns the whole budget before answering
    # (finish_reason=length, content=None). The other three answer directly, so
    # disable thinking to keep the token budgets — and the comparison — valid.
    if "qwen3.5" in model.lower():
        payload["chat_template_kwargs"] = {"enable_thinking": False}''',
        '''def ask(model, prompt, max_tokens):
    payload = sampling({"model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": budget(max_tokens)}, model)''')
    src = src.replace(
        '''    return {"text": d["choices"][0]["message"]["content"] or "",
            "tok": d["usage"]["completion_tokens"], "secs": round(time.time() - t0, 2)}''',
        '''    ch = d["choices"][0]
    msg = ch["message"]
    # vLLM 0.22 puts the chain of thought in `reasoning`, NOT `reasoning_content`;
    # `content` is left holding the final answer only, so graders need no change
    think = msg.get("reasoning") or msg.get("reasoning_content") or ""
    return {"text": msg.get("content") or "",
            "tok": d["usage"]["completion_tokens"],
            "think_chars": len(think),
            "finish": ch.get("finish_reason", ""),
            "secs": round(time.time() - t0, 2)}''')
    return src


def patch_b4(src):
    src = src.replace(
        '''    payload = {"model": model, "messages": msgs, "max_tokens": max_tokens,
               "temperature": 0}
    if "qwen3.5" in model.lower():
        payload["chat_template_kwargs"] = {"enable_thinking": False}''',
        '''    payload = sampling({"model": model, "messages": msgs,
                        "max_tokens": budget(max_tokens)}, model)''')
    src = src.replace(
        '''    return {"text": ch["message"]["content"] or "",
            "tok": d["usage"]["completion_tokens"],
            "ptok": d["usage"]["prompt_tokens"],
            "finish": ch.get("finish_reason", ""),
            "secs": round(time.time() - t0, 2)}''',
        '''    msg = ch["message"]
    think = msg.get("reasoning") or msg.get("reasoning_content") or ""
    return {"text": msg.get("content") or "",
            "tok": d["usage"]["completion_tokens"],
            "ptok": d["usage"]["prompt_tokens"],
            "think_chars": len(think),
            "finish": ch.get("finish_reason", ""),
            "secs": round(time.time() - t0, 2)}''')
    return src


for path, fn, anchor in (("/root/bench2/b3.py", patch_b3, "# ------------------------------------------------------------------- runner"),
                         ("/root/bench2/b4.py", patch_b4, "# ------------------------------------------------------------------- runner")):
    s = open(path).read()
    if "B4_THINK" in s:
        print(f"{path}: already patched, skipping")
        continue
    before = s
    s = fn(s)
    if s == before:
        print(f"{path}: PATCH DID NOT APPLY -- ask() text did not match", file=sys.stderr)
        sys.exit(1)
    s = s.replace(anchor, ASK_HELPERS + "\n\n" + anchor, 1)
    open(path, "w").write(s)
    print(f"{path}: patched")
