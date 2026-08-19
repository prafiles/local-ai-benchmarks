#!/usr/bin/env python3
"""Sandwich gate for the hard tier, run through the REAL grader.

    b5_gate.py ref     -> must be 104/104
    b5_gate.py null    -> must be 0/104

b5_oracle.py checks each reference against its own tests directly. This checks
something different and equally necessary: that the GRADER can see a correct
answer. Those are not the same claim -- a grader whose sandbox image is missing
scores a perfect answer zero, silently, which is exactly how six b3 categories
once reported 0/50 and were believed.

The null arm is the other half. A grader that scores empty strings above zero is
rewarding something other than the answer, and every number it produces is
inflated by that amount.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import b5             # noqa: E402
import b5_jsts as JSTS  # noqa: E402
import b5_python as PY  # noqa: E402
import b5_shell as SH   # noqa: E402
import b5_sql as SQL    # noqa: E402


def refs():
    out = {}
    for tid, _s, _t, r in PY.T:
        out[tid] = r
    for tid, _s, _t, r in JSTS.JS:
        out[tid] = r
    for tid, _s, _t, r in JSTS.TS:
        out[tid] = r
    for tid, _a, r in SQL.T:
        out[tid] = r
    for tid, _st, _p, _c, r in SH.SH:
        out[tid] = r
    for tid, _st, _p, _c, r in SH.GIT:
        out[tid] = r
    return out


def main(mode):
    r = refs()
    items = {}
    for tid, _cat, _kind, _p, _mt in b5.all_tasks():
        items[tid] = {"text": (r[tid] if mode == "ref" else ""),
                      "tok": 0, "secs": 0}
    path = os.path.join(b5.TMP, "gate_%s.json" % mode)
    os.makedirs(b5.TMP, exist_ok=True)
    json.dump({"model": "oracle/" + mode, "arm": "plain", "items": items}, open(path, "w"))
    b5.grade(path)
    got = json.load(open(path.replace(".json", ".graded.json")))
    score = sum(1 for v in got["results"].values() if v["ok"])
    n = len(got["results"])
    want = n if mode == "ref" else 0
    print("\nGATE %s: %d/%d, expected %d -- %s"
          % (mode, score, n, want, "PASS" if score == want else "FAIL"))
    if score != want:
        bad = [k for k, v in got["results"].items() if v["ok"] != (mode == "ref")]
        print("  offending: %s" % bad)
    return 0 if score == want else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
