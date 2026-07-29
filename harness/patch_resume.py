#!/usr/bin/env python3
"""Make the 600-task runner resumable.

With reasoning on, one model is roughly a day of decoding. Losing that to a
container restart, an OOM or a dropped connection is not acceptable, and the
existing runner starts from zero every time. This skips tasks already present in
the output file and keeps a live count so the ETA stays honest across restarts.
"""
old = '''def run(model, out_path):
    tasks = all_tasks()
    res = {"model": model, "items": {}}
    t0 = time.time()
    for i, (tid, cat, kind, prompt, mt) in enumerate(tasks, 1):
        try:
            r = ask(model, prompt, mt)
        except Exception as e:  # noqa: BLE001
            r = {"text": "", "tok": 0, "secs": 0, "error": f"{type(e).__name__}: {e}"}
        r.update(cat=cat, kind=kind)
        res["items"][tid] = r
        if i % 25 == 0 or i == len(tasks):'''

new = '''def run(model, out_path):
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
    t0 = time.time()
    done = 0
    for i, (tid, cat, kind, prompt, mt) in enumerate(tasks, 1):
        if tid in res["items"]:
            continue
        try:
            r = ask(model, prompt, mt)
        except Exception as e:  # noqa: BLE001
            r = {"text": "", "tok": 0, "secs": 0, "error": f"{type(e).__name__}: {e}"}
        r.update(cat=cat, kind=kind)
        res["items"][tid] = r
        done += 1
        if done % 10 == 0 or i == len(tasks):'''

path = "/root/bench2/b3.py"
s = open(path).read()
if "resuming:" in s:
    print("already patched")
    raise SystemExit(0)
assert old in s, "run() body did not match"
s = s.replace(old, new, 1)

# the ETA line counted every task; it has to count only the ones actually run
old_eta = '''            el = time.time() - t0
            print(f"  {i}/{len(tasks)}  {el/60:.1f}m elapsed, "
                  f"~{el/i*(len(tasks)-i)/60:.1f}m left", flush=True)'''
new_eta = '''            el = time.time() - t0
            left = len(tasks) - len(res["items"])
            rate = el / max(done, 1)
            print(f"  {len(res['items'])}/{len(tasks)}  {el/60:.1f}m elapsed, "
                  f"~{rate*left/3600:.1f}h left", flush=True)'''
assert old_eta in s, "progress line did not match"
s = s.replace(old_eta, new_eta, 1)

open(path, "w").write(s)
print("b3.py: runner is now resumable, progress every 10 tasks")
