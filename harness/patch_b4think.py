#!/usr/bin/env python3
"""Bring b4.py (long context) up to the same reasoning harness as b3.py.

b4.py only ever received the first, crude thinking patch: one global temperature,
no per-model profile, no retry, no CoT, sequential, and no resume. Everything
learned on the short-context arm has to be ported or the long-context reasoning
numbers would be measured with a harness known to be wrong.

Ported: per-model sampling profiles, resample-on-empty with temperature
escalation, the measured CoT suffix and ANSWER: marker, arm recording so graders
know which arm produced a file, unterminated-<think> stripping, per-bucket
concurrency, and resume.

NEW HERE, and specific to long context: the reasoning budget competes with the
session for the same window. Deep probes were calibrated to ~118K so that a
220-900 token answer fits inside 131,072. A reasoning budget of 8,000 does not
fit -- Gemma's deep prompts measure 129,249 tokens, leaving under 2K, and
Mellum2's 129,008. Rather than shrink the sessions (which would change the depth
being measured and break comparability with the published runs) or let the server
reject them, the budget adapts: ask for the full budget, and if the server refuses
on context length, parse its own arithmetic out of the error and retry with
exactly what remains.

That makes the squeeze visible rather than fatal. A probe that could only be given
1,800 tokens to think in is recorded as such, which is itself a finding: at the
deepest rung these models cannot both hold the session and reason about it.
"""
import re

p = "/root/bench2/b4.py"
s = open(p).read()

if "PROFILES" in s:
    print("already patched")
    raise SystemExit(0)

# ----------------------------------------------------------------- sampling
old = '''def sampling(payload, model):
    payload["temperature"] = TEMP
    if TEMP > 0:
        payload["top_p"] = TOPP
    if can_think(model):
        # explicit either way: the flag is what separates the two arms
        payload["chat_template_kwargs"] = {"enable_thinking": bool(THINK)}
    return payload'''

new = '''PROFILES = json.loads(os.environ.get("B4_PROFILES", "{}"))

DEFAULT_SAMP = {"temperature": TEMP}
if TEMP > 0:
    DEFAULT_SAMP["top_p"] = TOPP


def profile_for(model):
    m = model.lower()
    for key, prof in PROFILES.items():
        if key.lower() in m:
            return prof
    return DEFAULT_SAMP


def sampling(payload, model):
    prof = dict(profile_for(model))
    tmpl_extra = prof.pop("_tmpl", {})
    payload.update(prof)
    if can_think(model):
        # explicit either way: the flag is what separates the two arms
        tmpl = {"enable_thinking": bool(THINK)}
        tmpl.update(tmpl_extra)
        payload["chat_template_kwargs"] = tmpl
    return payload


# --------------------------------------------------------------- CoT arm
COT = os.environ.get("B4_COT") == "1"
COT_MARK = "ANSWER:"
COT_SUFFIX = (
    "\\n\\nDo not answer immediately. First write at least two sentences explaining "
    "your approach and any edge cases. Then write " + COT_MARK + " on its own line, "
    "followed by the answer in exactly the format the task asked for -- keeping "
    "every keyword it specified, such as export or module.exports -- and nothing "
    "else."
)
COT_SPLIT = False


def after_mark(t):
    i = t.rfind(COT_MARK)
    return t[i + len(COT_MARK):] if i >= 0 else t


def with_cot(model, msgs):
    """Append the reasoning instruction to the final user turn only.

    The session's earlier turns are context, not the question being asked; putting
    the instruction anywhere but last would ask the model to reason about history
    it has already been given the answers to.
    """
    if not (COT and not can_think(model)):
        return msgs
    out = [dict(m) for m in msgs]
    for m in reversed(out):
        if m.get("role") == "user":
            m["content"] = m["content"] + COT_SUFFIX
            break
    return out


RETRIES = int(os.environ.get("B4_RETRIES", "0"))
ESCALATE = [float(x) for x in
            os.environ.get("B4_ESCALATE", "0.9,1.0").split(",") if x.strip()]

# "maximum context length is N tokens. However, you requested M tokens (P in the
# messages, C in the completion)" -- the server has already done the arithmetic,
# so take its numbers rather than guessing at a tokenizer.
CTXERR = re.compile(r"maximum context length is (\\d+) tokens.*?"
                    r"(\\d+) in the messages", re.S)'''

assert old in s, "sampling() did not match"
s = s.replace(old, new, 1)

# --------------------------------------------------------------------- ask
old_ask = '''def ask(model, msgs, max_tokens):
    payload = sampling({"model": model, "messages": msgs,
                        "max_tokens": budget(max_tokens)}, model)
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=3600) as r:
        d = json.loads(r.read())
    ch = d["choices"][0]
    msg = ch["message"]
    think = msg.get("reasoning") or msg.get("reasoning_content") or ""
    return {"text": msg.get("content") or "",
            "tok": d["usage"]["completion_tokens"],
            "ptok": d["usage"]["prompt_tokens"],
            "think_chars": len(think),
            "finish": ch.get("finish_reason", ""),
            "secs": round(time.time() - t0, 2)}'''

new_ask = '''def _post(model, msgs, cap):
    payload = sampling({"model": model, "messages": with_cot(model, msgs),
                        "max_tokens": cap}, model)
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3600) as r:
        return json.loads(r.read())


def _once(model, msgs, max_tokens, temp=None):
    cap = budget(max_tokens)
    squeezed = 0
    t0 = time.time()
    while True:
        try:
            d = _post(model, msgs, cap)
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            m = CTXERR.search(body)
            # The session plus a full reasoning budget does not fit the window.
            # Shrink the budget to exactly what is left instead of failing: the
            # probe is measuring the session, and how little room is left to think
            # in at this depth is the interesting part.
            if not m:
                raise
            window, ptok = int(m.group(1)), int(m.group(2))
            room = window - ptok - 8
            if room <= 64 or room >= cap:
                raise
            cap = room
            squeezed += 1
    ch = d["choices"][0]
    msg = ch["message"]
    think = msg.get("reasoning") or msg.get("reasoning_content") or ""
    return {"text": msg.get("content") or "",
            "tok": d["usage"]["completion_tokens"],
            "ptok": d["usage"]["prompt_tokens"],
            "think_chars": len(think),
            "finish": ch.get("finish_reason", ""),
            "cap": cap, "squeezed": squeezed,
            "secs": round(time.time() - t0, 2)}


def ask(model, msgs, max_tokens):
    """Resample -- hotter each time -- only when the answer came back empty."""
    spent, used = 0.0, []
    r = None
    for attempt in range(RETRIES + 1):
        temp = None if attempt == 0 else ESCALATE[min(attempt - 1, len(ESCALATE) - 1)]
        r = _once(model, msgs, max_tokens, temp)
        spent += r["secs"]
        used.append(temp)
        if r["text"].strip():
            break
    r["attempts"] = len(used)
    r["secs"] = round(spent, 2)
    return r'''

assert old_ask in s, "ask() did not match"
s = s.replace(old_ask, new_ask, 1)

# --------------------------------------------------------------------- run
old_run = s[s.index("def run(model, out_path, mode=\"both\"):"):
            s.index("# ------------------------------------------------------------------ helpers")]

new_run = '''def run(model, out_path, mode="both"):
    res = {"model": model, "deep": {}, "shallow": {},
           "arm": ("native" if (THINK and can_think(model))
                   else "cot" if (COT and not can_think(model)) else "plain")}
    if os.path.exists(out_path):
        try:
            prev = json.load(open(out_path))
            if prev.get("model") == model and prev.get("arm") == res["arm"]:
                for b in ("deep", "shallow"):
                    res[b] = {k: v for k, v in prev.get(b, {}).items()
                              if not v.get("error")}
                print("  resuming: deep %d, shallow %d already done"
                      % (len(res["deep"]), len(res["shallow"])), flush=True)
        except Exception:  # noqa: BLE001
            print("  existing output unreadable, starting fresh", flush=True)

    plan = []
    for cat in ORDER:
        if mode in ("both", "deep"):
            plan += [("deep", cat, m, p) for m, p in build_deep(cat)]
        if mode in ("both", "shallow"):
            plan += [("shallow", cat, m, p) for m, p in build_shallow(cat)]
    plan = [x for x in plan if x[3]["id"] not in res[x[0]]]

    # Deep probes carry ~118K-token prompts, so only one or two fit the KV pool at
    # once; shallow ones are small and parallelise freely. One worker count for
    # both would either crawl through the shallow half or thrash the deep one.
    wd = int(os.environ.get("B4_WORKERS_DEEP", "1"))
    ws = int(os.environ.get("B4_WORKERS_SHALLOW", "4"))
    print("  %d to run (deep x%d, shallow x%d)" % (len(plan), wd, ws), flush=True)

    lock = threading.Lock()
    t0 = time.time()
    done = [0]

    def work(item):
        bucket, cat, msgs, p = item
        try:
            r = ask(model, msgs, p["max_tokens"])
        except Exception as e:  # noqa: BLE001
            r = {"text": "", "tok": 0, "ptok": 0, "secs": 0, "finish": "error",
                 "error": f"{type(e).__name__}: {str(e)[:200]}"}
        r["cat"] = cat
        with lock:
            res[bucket][p["id"]] = r
            done[0] += 1
            n = done[0]
            el = time.time() - t0
            sq = (" squeezed->%d" % r.get("cap")) if r.get("squeezed") else ""
            print(f"  {n}/{len(plan)} {bucket:<7} {p['id']:<10} "
                  f"ptok={r.get('ptok', 0):>6} {r['secs']:>6.1f}s{sq}  "
                  f"[{el/60:.1f}m, ~{el/n*(len(plan)-n)/60:.0f}m left]", flush=True)
            with open(out_path + ".tmp", "w") as f:
                json.dump(res, f)
            os.replace(out_path + ".tmp", out_path)

    for bucket, workers in (("shallow", ws), ("deep", wd)):
        items = [x for x in plan if x[0] == bucket]
        if not items:
            continue
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            list(ex.map(work, items))

    with open(out_path + ".tmp", "w") as f:
        json.dump(res, f)
    os.replace(out_path + ".tmp", out_path)
    print(f"saved -> {out_path}")


'''

s = s.replace(old_run, new_run, 1)

# ------------------------------------------------------------- strip_think
old_strip = '''def strip_think(t):
    return re.sub(r"<think>.*?</think>", "", t, flags=re.S)'''
new_strip = '''def strip_think(t):
    if COT_SPLIT:
        t = after_mark(t)
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.S)
    # unclosed <think> means the cap landed mid-thought; everything after it is
    # deliberation and must not be graded as if it were the answer
    return re.sub(r"<think>.*\\Z", "", t, flags=re.S)'''
assert old_strip in s, "strip_think did not match"
s = s.replace(old_strip, new_strip, 1)

# ------------------------------------------------------------------ grade
old_grade = '''def grade(path):
    data = json.load(open(path))'''
new_grade = '''def grade(path):
    global COT_SPLIT
    data = json.load(open(path))
    COT_SPLIT = data.get("arm") == "cot"
    if COT_SPLIT:
        n = sum(1 for b in ("deep", "shallow")
                for v in data.get(b, {}).values()
                if COT_MARK in (v.get("text") or ""))
        tot = sum(len(data.get(b, {})) for b in ("deep", "shallow"))
        print("  CoT arm: %d/%d answers used the %s marker" % (n, tot, COT_MARK),
              flush=True)'''
assert old_grade in s, "grade() did not match"
s = s.replace(old_grade, new_grade, 1)

# imports
s = s.replace("import json\nimport os\n",
              "import concurrent.futures\nimport json\nimport os\n", 1)
s = s.replace("import sys\nimport time\n", "import sys\nimport threading\nimport time\n", 1)
assert "import threading" in s and "import concurrent.futures" in s
if "import urllib.error" not in s:
    s = s.replace("import urllib.request", "import urllib.error\nimport urllib.request", 1)

open(p, "w").write(s)
print("b4.py: profiles, CoT, retry/escalate, adaptive budget, concurrency, resume, arm")
