#!/usr/bin/env python3
"""The complement of the reference oracle: grade a run that answers nothing.

The reference oracle checks that the right answer passes. It cannot detect a task
whose check is already satisfied before the model does anything -- sh-050 sets up
arch/f containing "data", then checks that arch/f contains "data", so an empty
answer passes and the oracle still reports 50/50 because the reference passes too.

Every task here should FAIL on an empty answer. Any task that passes is one where
a model can score by emitting nothing, which silently inflates every run in the
repository -- and matters more now than it used to, because reasoning mode can
genuinely return an empty answer when a trace runs away.

    nulloracle.py [out.json]
"""
import json
import os
import subprocess
import sys

HERE = "/root/bench2"
sys.path.insert(0, HERE)
import b3  # noqa: E402

dst = sys.argv[1] if len(sys.argv) > 1 else "/tmp/nulloracle.json"
tasks = b3.all_tasks()
items = {tid: {"text": "", "tok": 0, "secs": 0, "cat": cat, "kind": kind}
         for tid, cat, kind, _p, _m in tasks}
json.dump({"model": "NULL-ORACLE(empty answers)", "items": items}, open(dst, "w"))
print("built %d empty answers -> %s" % (len(items), dst), flush=True)

subprocess.run([sys.executable, os.path.join(HERE, "b3.py"), "grade", dst], check=True)

g = json.load(open(dst.replace(".json", ".graded.json")))["results"]
passed = sorted(k for k, v in g.items() if v["ok"])
print("\n===== NULL ORACLE")
print("  tasks passing on an EMPTY answer: %d/%d" % (len(passed), len(g)))
for k in passed:
    print("    %-9s %s" % (k, g[k]["cat"]))
print("\n  %s" % ("clean -- no task can be passed by saying nothing"
                  if not passed else
                  "^ these tasks are defective: their check is satisfied before "
                  "the model acts"))
