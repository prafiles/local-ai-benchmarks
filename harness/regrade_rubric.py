#!/usr/bin/env python3
"""Recompute only the rubric grader and patch the graded files in place.

The rubric grader is pure regex over saved text, so re-running the whole suite
(tsc, docker, sqlite) to change one pattern would be 30 minutes of nothing.
"""
import json
import sys

sys.path.insert(0, "/root/bench2")
import b4  # noqa: E402

for key in ("gemma", "qwen", "mellum", "q35"):
    raw = f"/root/bench2/c_{key}.json"
    gp = f"/root/bench2/c_{key}.graded.json"
    try:
        data = json.load(open(raw))
        g = json.load(open(gp))
    except FileNotFoundError:
        continue
    deep = b4.g_rubricx(data["deep"], "re")
    shal = b4.g_rubricx(data["shallow"], "re")
    moved = []
    for tid, ok in deep.items():
        if g["results"][tid]["deep"] != ok:
            moved.append(f"{tid} deep {g['results'][tid]['deep']}->{ok}")
            g["results"][tid]["deep"] = ok
    for tid, ok in shal.items():
        if g["results"][tid]["shallow"] != ok:
            moved.append(f"{tid} shal {g['results'][tid]['shallow']}->{ok}")
            g["results"][tid]["shallow"] = ok
    json.dump(g, open(gp, "w"), indent=1)
    d = sum(1 for v in g["results"].values() if v["deep"])
    s = sum(1 for v in g["results"].values() if v["shallow"])
    print(f"{key:<8} deep {d}/60  shallow {s}/60   changed: {moved}")
