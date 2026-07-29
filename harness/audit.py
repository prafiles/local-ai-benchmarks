#!/usr/bin/env python3
"""What has actually been run, counted from the artifacts on disk."""
import json
import os
import sys

sys.path.insert(0, "/root/bench2")
os.chdir("/root/bench2")
import b4  # noqa: E402

N4 = len(list(b4.probes()))
MODELS = [("gemma", "Gemma 4 12B QAT"), ("qwen", "Qwen2.5-Coder-14B"),
          ("mellum", "Mellum2-12B"), ("q35", "Qwen3.5-9B")]

print("LONG-CONTEXT (%d probes, deep + shallow)" % N4)
for k, lab in MODELS:
    p = "c_%s.json" % k
    if not os.path.exists(p):
        print("  %-20s MISSING" % lab)
        continue
    d = json.load(open(p))
    deep, shal = d["deep"], d["shallow"]
    rej = sum(1 for v in deep.values() if v.get("finish") == "error")
    retried = sum(1 for v in deep.values() if v.get("retried_scale"))
    g = json.load(open("c_%s.graded.json" % k))["results"]
    dok = sum(1 for v in g.values() if v["deep"])
    sok = sum(1 for v in g.values() if v["shallow"])
    print("  %-20s deep %d/%d  shallow %d/%d  | server-rejected %d  re-run %d "
          "| scored deep %d shallow %d"
          % (lab, len(deep), N4, len(shal), N4, rej, retried, dok, sok))

    if rej:
        by_depth = {}
        for tid, v in deep.items():
            if v.get("finish") == "error":
                by_depth[g[tid]["depth"]] = by_depth.get(g[tid]["depth"], 0) + 1
        print("      %s -> rejected at depths: %s"
              % (lab, {("~%dK" % (dd // 1000)): c for dd, c in sorted(by_depth.items())}))

print()
print("REASONING ARM")
t = sorted(f for f in os.listdir(".") if f.startswith("t_") and f.endswith(".json"))
print("  output files: %s" % (t if t else "NONE -- never launched"))
print("  calibration probes present: %s"
      % sorted(f for f in os.listdir(".") if f.startswith("calib_")))
