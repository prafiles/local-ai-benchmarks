#!/usr/bin/env python3
"""Null oracle for the long-context suite: every probe must fail on nothing.

The short-context version found sh-050, whose check was satisfied by its own
setup, so an empty answer scored a pass and the reference oracle could not see it
(the reference passes too). The long-context probes are graded by the same style
of executable check against a prepared working directory, so they can carry the
same defect -- and a long-context probe is the more likely place for it, because
the setup there is a whole conversation rather than a one-line shell command.

Any probe that passes here is one where a model can score by saying nothing.

    nulloracle4.py [out.json]
"""
import json
import os
import subprocess
import sys

HERE = "/root/bench2"
sys.path.insert(0, HERE)
os.chdir(HERE)
import b4  # noqa: E402

dst = sys.argv[1] if len(sys.argv) > 1 else "/tmp/nulloracle4.json"
ids = [p["id"] for _cat, p in b4.probes()]
empty = {i: {"text": "", "tok": 0, "secs": 0, "ptok": 0, "finish": "stop"} for i in ids}
json.dump({"model": "NULL-ORACLE4(empty answers)", "deep": dict(empty),
           "shallow": dict(empty)}, open(dst, "w"))
print("built %d empty answers x2 buckets -> %s" % (len(ids), dst), flush=True)

subprocess.run([sys.executable, os.path.join(HERE, "b4.py"), "grade", dst], check=True)

g = json.load(open(dst.replace(".json", ".graded.json")))["results"]
bad = sorted(k for k, v in g.items() if v["deep"] or v["shallow"])
print("\n===== NULL ORACLE (long context)")
print("  probes passing on an EMPTY answer: %d/%d" % (len(bad), len(g)))
for k in bad:
    print("    %-10s %-12s deep=%s shallow=%s"
          % (k, g[k]["cat"], g[k]["deep"], g[k]["shallow"]))
print("\n  %s" % ("clean -- no probe can be passed by saying nothing" if not bad
                  else "^ defective: check satisfied before the model acts"))
