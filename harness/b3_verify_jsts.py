#!/usr/bin/env python3
"""Verify every JS and TS reference against its own tests, in one container each."""
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b3_jsts import JS, TS  # noqa: E402

STAGE = "/root/bench2/tmp/jsv"

JS_RUN = """
cd /w
for id in $(cat ids); do
  mkdir -p /tmp/$id && cp cases/$id/sol.js cases/$id/t.js /tmp/$id/
  if (cd /tmp/$id && timeout 30 node t.js >/dev/null 2>&1); then echo "OK $id"; else echo "BAD $id"; fi
done
"""

TS_RUN = """
cd /w
for id in $(cat ids); do
  mkdir -p /tmp/$id && cp cases/$id/sol.ts cases/$id/t.ts /tmp/$id/
  if (cd /tmp/$id && timeout 90 tsc --strict --module commonjs --target es2020 \
        --types node --typeRoots /usr/local/lib/node_modules/@types \
        --outDir out sol.ts t.ts >/dev/null 2>&1 && timeout 30 node out/t.js >/dev/null 2>&1); \
  then echo "OK $id"; else echo "BAD $id"; fi
done
"""


def run(name, rows, ext, script):
    d = os.path.join(STAGE, name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(os.path.join(d, "cases"), exist_ok=True)
    ids = []
    for tid, _spec, tests, ref in rows:
        ids.append(tid)
        cd = os.path.join(d, "cases", tid)
        os.makedirs(cd, exist_ok=True)
        open(os.path.join(cd, f"sol.{ext}"), "w").write(ref)
        open(os.path.join(cd, f"t.{ext}"), "w").write(tests)
    open(os.path.join(d, "ids"), "w").write("\n".join(ids) + "\n")
    open(os.path.join(d, "_run.sh"), "w").write(script)

    p = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--memory", "2g",
         "-v", f"{d}:/w", "-w", "/w", "bench-node:1", "sh", "/w/_run.sh"],
        capture_output=True, text=True, timeout=3600)
    bad = [ln.split()[1] for ln in p.stdout.splitlines() if ln.startswith("BAD")]
    ok = len([ln for ln in p.stdout.splitlines() if ln.startswith("OK")])
    print(f"{name}: {ok}/{len(rows)} references pass")
    for b in bad:
        print(f"   BROKEN {b}")
    if not p.stdout.strip():
        print("   stderr:", (p.stderr or "")[-400:])
    return bad


if __name__ == "__main__":
    os.makedirs(STAGE, exist_ok=True)
    run("js", JS, "js", JS_RUN)
    run("ts", TS, "ts", TS_RUN)
