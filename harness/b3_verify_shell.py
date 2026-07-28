#!/usr/bin/env python3
"""Verify every Bash and Git reference command against its own checker.

Writes per-task setup/ref/chk files into a staging dir, then runs the whole
category inside ONE container instead of one container per task.
"""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b3_shell import BASH  # noqa: E402
from b3_git import GIT  # noqa: E402

STAGE = "/root/bench2/tmp/shv"

RUNNER = """
for id in $(cat /w/ids); do
  rm -rf /tmp/b/$id; mkdir -p /tmp/b/$id; cd /tmp/b/$id
  sh /w/$id.setup >/dev/null 2>&1
  mkdir -p /tmp/outs
  OUT=/tmp/outs/$id; export OUT
  sh /w/$id.ref  > "$OUT" 2>&1
  if OUT=/tmp/outs/$id sh /w/$id.chk >/dev/null 2>&1; then echo "OK $id"; else echo "BAD $id"; fi
done
"""


def run(name, rows):
    d = os.path.join(STAGE, name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    ids = []
    for tid, setup, _prompt, chk, ref in rows:
        ids.append(tid)
        for ext, body in (("setup", setup), ("ref", ref), ("chk", chk)):
            with open(os.path.join(d, f"{tid}.{ext}"), "w") as f:
                f.write(body + "\n")
    with open(os.path.join(d, "ids"), "w") as f:
        f.write("\n".join(ids) + "\n")
    with open(os.path.join(d, "_run.sh"), "w") as f:
        f.write(RUNNER)

    p = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--memory", "1g",
         "-e", "HOME=/tmp", "-v", f"{d}:/w", "-w", "/w", "bench-sh:1",
         "sh", "/w/_run.sh"],
        capture_output=True, text=True, timeout=900,
    )
    bad = [ln.split()[1] for ln in p.stdout.splitlines() if ln.startswith("BAD")]
    ok = len([ln for ln in p.stdout.splitlines() if ln.startswith("OK")])
    print(f"{name}: {ok}/{len(rows)} references pass")
    for b in bad:
        print(f"   BROKEN {b}")
    if p.stderr.strip():
        print("   stderr:", p.stderr.strip()[-300:])
    return bad


if __name__ == "__main__":
    os.makedirs(STAGE, exist_ok=True)
    run("bash", BASH)
    run("git", GIT)
