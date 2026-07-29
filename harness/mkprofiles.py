#!/usr/bin/env python3
"""Emit B4_PROFILES from the recorded per-model decision.

Reads chosen_<label>.json -- written deliberately, with the evidence for the
choice in its `why` field -- rather than a heuristic pick over aggregate stats.
The tuner's own auto-pick was wrong here: it chose a "trace cap" on the strength
of a halved median, when the paired per-probe view showed the cap was ignored and
the median had moved because a different probe happened to spiral that round.

Keeping the decision in a file the runner reads means the params in the results
are the params that were measured, not ones retyped into a shell script.

    mkprofiles.py q35=qwen3.5 gemma=gemma-4
"""
import json
import os
import sys

prof = {}
for arg in sys.argv[1:]:
    label, key = arg.split("=", 1)
    p = "/root/bench2/chosen_%s.json" % label
    if not os.path.exists(p):
        sys.stderr.write("no chosen_%s.json -- refusing to guess sampling params\n" % label)
        raise SystemExit(1)
    d = json.load(open(p))
    prof[key] = d["sampling"]
    sys.stderr.write("%-9s -> %s\n" % (key, d["sampling"]))
    if d.get("why"):
        sys.stderr.write("            %s\n" % d["why"])

print(json.dumps(prof))
