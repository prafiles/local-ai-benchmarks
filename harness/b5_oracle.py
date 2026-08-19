#!/usr/bin/env python3
"""Oracle gate for the hard tier: every reference must pass its own tests.

A task whose own reference fails is a broken task, not a model failure, and it
must never reach a model. Runs in the same sandbox image the grader uses, so a
reference that only works on the host is caught here rather than showing up as a
mysterious zero for every model.

    b5_oracle.py python
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
TMP = os.environ.get("B4_TMP", "/tmp/b5oracle")

IMAGES = {"python": "bench-py:1", "js": "bench-node:1", "ts": "bench-node:1",
          "sql": "bench-py:1", "shell": "bench-sh:1", "django": "bench-py:1"}


def run_python():
    import b5_python as P
    d = os.path.join(TMP, "pyoracle")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "v.py"), "w").write(P.verify_source())
    p = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--memory", "4g",
         "--pids-limit", "512", "-e", "HOME=/tmp", "-v", f"{d}:/w", "-w", "/w",
         "bench-py:1", "python", "/w/v.py"],
        capture_output=True, text=True, timeout=3600)
    if p.returncode != 0:
        print("driver failed:\n" + p.stderr[-3000:])
        return 1
    bad = json.loads(p.stdout.strip().splitlines()[-1])
    n = len(P.T)
    print("python: %d/%d references pass" % (n - len(bad), n))
    for tid, err in bad:
        print("  BROKEN %s: %s" % (tid, err))
    return 1 if bad else 0


def _node(kind):
    """Run every reference through the same container script the grader uses."""
    import b5_jsts as J
    rows = J.JS if kind == "js" else J.TS
    d = os.path.join(TMP, kind + "oracle")
    shutil.rmtree(d, ignore_errors=True)
    ids = []
    for tid, _spec, tests, ref in rows:
        ids.append(tid)
        cd = os.path.join(d, "cases", tid)
        os.makedirs(cd, exist_ok=True)
        ext = "js" if kind == "js" else "ts"
        open(os.path.join(cd, "sol." + ext), "w").write(ref)
        open(os.path.join(cd, "t." + ext), "w").write(tests)
    if kind == "js":
        script = ("for id in $(ls /w/cases); do\n"
                  "  if (cd /w/cases/$id && timeout 60 node t.js >/tmp/$id.log 2>&1); "
                  "then echo \"OK $id\"; else echo \"BAD $id\"; "
                  "echo \"--- $id\"; tail -6 /tmp/$id.log; fi\ndone\n")
    else:
        script = ("for id in $(ls /w/cases); do\n"
                  "  if (cd /w/cases/$id && timeout 120 tsc --strict --module commonjs "
                  "--target es2020 --types node "
                  "--typeRoots /usr/local/lib/node_modules/@types --outDir out sol.ts t.ts "
                  ">/tmp/$id.log 2>&1 && timeout 60 node out/t.js >>/tmp/$id.log 2>&1); "
                  "then echo \"OK $id\"; else echo \"BAD $id\"; "
                  "echo \"--- $id\"; tail -8 /tmp/$id.log; fi\ndone\n")
    open(os.path.join(d, "_run.sh"), "w").write(script)
    p = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--memory", "6g",
         "--pids-limit", "512", "-e", "HOME=/tmp", "-v", f"{d}:/w", "-w", "/w",
         "bench-node:1", "sh", "/w/_run.sh"],
        capture_output=True, text=True, timeout=7200)
    out = p.stdout
    bad = [i for i in ids if ("OK " + i) not in out]
    print("%s: %d/%d references pass" % (kind, len(ids) - len(bad), len(ids)))
    if bad:
        print(out[-6000:])
    return 1 if bad else 0


def run_js():
    return _node("js")


def run_ts():
    return _node("ts")


def _shell(kind):
    """setup -> reference -> checker, in the same container the grader uses."""
    import b5_shell as S
    rows = S.SH if kind == "shell" else S.GIT
    d = os.path.join(TMP, kind + "oracle")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    ids = []
    for tid, setup, _p, chk, ref in rows:
        ids.append(tid)
        open(os.path.join(d, tid + ".setup"), "w").write(setup + "\n")
        open(os.path.join(d, tid + ".cmd"), "w").write(ref + "\n")
        open(os.path.join(d, tid + ".chk"), "w").write(chk + "\n")
    open(os.path.join(d, "ids"), "w").write("\n".join(ids) + "\n")
    script = ("mkdir -p /tmp/outs\n"
              "for id in $(cat /w/ids); do\n"
              "  rm -rf /tmp/b/$id; mkdir -p /tmp/b/$id; cd /tmp/b/$id\n"
              "  sh /w/$id.setup >/dev/null 2>&1\n"
              "  OUT=/tmp/outs/$id; export OUT\n"
              "  timeout 60 sh /w/$id.cmd > \"$OUT\" 2>/tmp/outs/$id.err\n"
              "  cd /tmp/b/$id\n"
              "  if OUT=/tmp/outs/$id sh /w/$id.chk >/dev/null 2>&1; "
              "then echo \"OK $id\"; else echo \"BAD $id\"; "
              "echo \"--- $id\"; tail -4 /tmp/outs/$id.err; fi\ndone\n")
    open(os.path.join(d, "_run.sh"), "w").write(script)
    p = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--memory", "2g",
         "--pids-limit", "512", "-e", "HOME=/tmp", "-v", f"{d}:/w", "-w", "/w",
         "bench-sh:1", "sh", "/w/_run.sh"],
        capture_output=True, text=True, timeout=3600)
    out = p.stdout
    bad = [i for i in ids if ("OK " + i) not in out]
    print("%s: %d/%d references pass" % (kind, len(ids) - len(bad), len(ids)))
    if bad:
        print(out[-5000:])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit({"python": run_python, "js": run_js, "ts": run_ts,
              "shell": lambda: _shell("shell"),
              "git": lambda: _shell("git")}[sys.argv[1]]())
