#!/usr/bin/env python3
"""Verify every Django reference solution against its own tests.

Each task needs a fresh process (settings.configure runs once per process), so
this stages all 50 and runs them as subprocesses inside ONE container.
"""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b3_django import HARNESS, MODELS, SEED, T  # noqa: E402

STAGE = "/root/bench2/tmp/djv"

DRIVER = """
import json, os, subprocess
bad = []
for tid in sorted(os.listdir("/w/cases")):
    d = "/w/cases/" + tid
    r = subprocess.run(["python", "/w/h.py"], capture_output=True, text=True,
                       timeout=120, env={**os.environ, "CASE": d})
    if r.returncode != 0:
        tail = (r.stderr or "").strip().splitlines()
        bad.append((tid, tail[-1][:130] if tail else "nonzero"))
print(json.dumps(bad))
"""

# harness reads the case dir from $CASE instead of fixed /w paths
HARNESS_CASE = HARNESS.replace('open("/w/sol.py")', 'open(os.environ["CASE"]+"/sol.py")') \
                      .replace('open("/w/test.py")', 'open(os.environ["CASE"]+"/test.py")') \
                      .replace('open("/w/seed.py")', 'open("/w/seed.py")') \
                      .replace("import django, datetime", "import django, datetime, os")


def main():
    shutil.rmtree(STAGE, ignore_errors=True)
    os.makedirs(os.path.join(STAGE, "bench_app"), exist_ok=True)
    os.makedirs(os.path.join(STAGE, "cases"), exist_ok=True)
    open(os.path.join(STAGE, "bench_app", "__init__.py"), "w").close()
    open(os.path.join(STAGE, "bench_app", "models.py"), "w").write(MODELS)
    open(os.path.join(STAGE, "seed.py"), "w").write(SEED)
    open(os.path.join(STAGE, "h.py"), "w").write(HARNESS_CASE)
    open(os.path.join(STAGE, "_run.sh"), "w").write("cd /w && python /w/driver.py\n")
    open(os.path.join(STAGE, "driver.py"), "w").write(DRIVER)
    for tid, _spec, tests, ref in T:
        d = os.path.join(STAGE, "cases", tid)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "sol.py"), "w").write(ref)
        open(os.path.join(d, "test.py"), "w").write(tests)

    p = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--memory", "2g",
         "-v", f"{STAGE}:/w", "-w", "/w", "bench-py:1", "sh", "/w/_run.sh"],
        capture_output=True, text=True, timeout=1800)
    out = (p.stdout or "").strip().splitlines()
    if not out:
        print("no output; stderr:", (p.stderr or "")[-500:])
        return
    import json
    bad = json.loads(out[-1])
    print(f"django: {len(T)-len(bad)}/{len(T)} references pass")
    for tid, why in bad:
        print(f"   BROKEN {tid}: {why}")


if __name__ == "__main__":
    main()
