#!/usr/bin/env python3
"""Per-model sampling profiles + a concurrent runner.

Two problems, one patch.

SAMPLING. `sampling()` applied one global temperature to every model. That is
wrong for a reasoning run: Qwen3.5 and Gemma 4 publish different recommended
settings for thinking mode, and the failure mode of using the wrong one is not
"slightly worse output" -- it is a trace that never terminates and an answer that
comes back empty. So the profile is keyed on the model.

CONCURRENCY. The runner asked for one completion at a time. Without thinking that
was merely slow; with thinking it is disqualifying -- measured decode is ~22 tok/s
and a reasoning trace runs thousands of tokens, which puts a 600-task run at
around 46 hours per model. Decode here is memory-bandwidth-bound, so the weights
are re-read for every token regardless of how many sequences are in flight;
running several concurrently amortises that read and is close to free. The server
is already started with --max-num-seqs 4.

What this costs: batched kernels are not bitwise identical to unbatched ones, so
concurrency makes the run non-reproducible at the token level. It already was --
these configs sample at temperature > 0 because greedy decoding does not
terminate. Nothing about a fixed seed survives that either way.
"""
import re

p = "/root/bench2/b3.py"
s = open(p).read()

if "PROFILES" in s:
    print("already patched")
    raise SystemExit(0)

old_sampling = '''def sampling(payload, model):
    payload["temperature"] = TEMP
    if TEMP > 0:
        payload["top_p"] = TOPP
    if can_think(model):
        # explicit either way: the flag is what separates the two arms
        payload["chat_template_kwargs"] = {"enable_thinking": bool(THINK)}
    return payload'''

new_sampling = '''# Measured per model by tune.py, not copied off a model card and hoped for.
# The entry that matters is the one for thinking mode: greedy decoding sends both
# reasoning models into a loop that eats the whole budget and returns no answer.
PROFILES = json.loads(os.environ.get("B4_PROFILES", "{}"))

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
    payload.update(profile_for(model))
    if can_think(model):
        # explicit either way: the flag is what separates the two arms
        payload["chat_template_kwargs"] = {"enable_thinking": bool(THINK)}
    return payload'''

assert old_sampling in s, "sampling() did not match"
s = s.replace(old_sampling, new_sampling, 1)

# ---------------------------------------------------------------- runner
old_run = s[s.index("def run(model, out_path):"):s.index("# ------------------------------------------------------------------ helpers")]

new_run = '''def run(model, out_path):
    tasks = all_tasks()
    res = {"model": model, "items": {}}
    if os.path.exists(out_path):
        try:
            prev = json.load(open(out_path))
            if prev.get("model") == model:
                # keep only clean results; anything that errored gets another go
                res["items"] = {k: v for k, v in prev.get("items", {}).items()
                                if not v.get("error")}
                print(f"  resuming: {len(res['items'])}/{len(tasks)} already done",
                      flush=True)
        except Exception:  # noqa: BLE001
            print("  existing output unreadable, starting fresh", flush=True)

    todo = [t for t in tasks if t[0] not in res["items"]]
    workers = int(os.environ.get("B4_WORKERS", "1"))
    print(f"  {len(todo)} to run, {workers} concurrent", flush=True)

    lock = threading.Lock()
    t0 = time.time()
    done = [0]

    def work(task):
        tid, cat, kind, prompt, mt = task
        try:
            r = ask(model, prompt, mt)
        except Exception as e:  # noqa: BLE001
            r = {"text": "", "tok": 0, "secs": 0, "error": f"{type(e).__name__}: {e}"}
        r.update(cat=cat, kind=kind)
        with lock:
            res["items"][tid] = r
            done[0] += 1
            n = done[0]
            if n % 10 == 0 or n == len(todo):
                el = time.time() - t0
                rate = el / n
                print(f"  {len(res['items'])}/{len(tasks)}  {el/60:.1f}m elapsed, "
                      f"~{rate*(len(todo)-n)/3600:.1f}h left", flush=True)
                with open(out_path + ".tmp", "w") as f:
                    json.dump(res, f)
                os.replace(out_path + ".tmp", out_path)

    if todo:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            list(ex.map(work, todo))

    with open(out_path + ".tmp", "w") as f:
        json.dump(res, f)
    os.replace(out_path + ".tmp", out_path)
    print(f"saved -> {out_path}")


'''

s = s.replace(old_run, new_run, 1)

# imports
s = s.replace("import json\nimport os\n",
              "import concurrent.futures\nimport json\nimport os\n", 1)
s = s.replace("import sys\nimport time\n", "import sys\nimport threading\nimport time\n", 1)
assert "import threading" in s and "import concurrent.futures" in s

open(p, "w").write(s)
print("b3.py: per-model PROFILES + concurrent resumable runner (B4_WORKERS)")
print("imports ok:", bool(re.search(r"^import threading$", s, re.M)))
