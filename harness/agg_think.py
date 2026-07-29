#!/usr/bin/env python3
"""Reasoning arm vs the no-reasoning baseline, per category and per task.

Reads r_<m>.graded.json (baseline) and t_<m>.graded.json (reasoning) plus the raw
t_<m>.json for cost, and reports:

  * per-category pass counts and the delta
  * how much the reasoning cost -- tokens, trace length, wall clock
  * how many answers came back EMPTY, which is the failure mode that makes an
    untuned reasoning run look like a capability regression
  * the flips, both directions, so a delta of zero is not mistaken for "nothing
    happened" when it is really equal numbers of gains and losses

    agg_think.py [out.json]
"""
import json
import os
import sys

HERE = "/root/bench2"
MODELS = [("gemma", "Gemma 4 12B QAT"), ("q35", "Qwen3.5-9B FP8"),
          ("mellum", "Mellum2-12B-A2.5B"), ("qwen", "Qwen2.5-Coder-14B")]
CATS = ["Python", "Django", "SQL", "JS", "TS", "Bash", "Git", "SSH", "GitHub",
        "Docs", "ReactNative", "RAG"]


def load(p):
    return json.load(open(p)) if os.path.exists(p) else None


out = {"models": {}}
for key, label in MODELS:
    base = load(os.path.join(HERE, "r_%s.graded.json" % key))
    think = load(os.path.join(HERE, "t_%s.graded.json" % key))
    raw = load(os.path.join(HERE, "t_%s.json" % key))
    if not base or not think:
        print("== %-22s reasoning arm: %s" % (label, "not run" if not think else "no baseline"))
        continue

    b, t = base["results"], think["results"]
    items = (raw or {}).get("items", {})
    shared = [k for k in b if k in t]

    percat = {}
    for c in CATS:
        ids = [k for k in shared if b[k]["cat"] == c]
        bp = sum(1 for k in ids if b[k]["ok"])
        tp = sum(1 for k in ids if t[k]["ok"])
        percat[c] = {"n": len(ids), "base": bp, "think": tp, "delta": tp - bp}

    gained = sorted(k for k in shared if t[k]["ok"] and not b[k]["ok"])
    lost = sorted(k for k in shared if b[k]["ok"] and not t[k]["ok"])

    # Cost + the honesty checks. An empty answer or a `length` finish means the
    # budget ran out inside the trace; those are harness failures, not model ones,
    # and they have to be visible or the score is a lie.
    empty = [k for k, v in items.items() if not (v.get("text") or "").strip()]
    trunc = [k for k, v in items.items() if v.get("finish") == "length"]
    errs = [k for k, v in items.items() if v.get("error")]
    tok = sum(v.get("tok", 0) for v in items.values())
    thk = sum(v.get("think_chars", 0) for v in items.values())
    secs = sum(v.get("secs", 0) for v in items.values())
    nthink = sum(1 for v in items.values() if v.get("think_chars", 0) > 0)

    bt, tt = sum(1 for k in shared if b[k]["ok"]), sum(1 for k in shared if t[k]["ok"])
    out["models"][key] = {"label": label, "n": len(shared), "base": bt, "think": tt,
                          "delta": tt - bt, "percat": percat,
                          "gained": gained, "lost": lost,
                          "empty": len(empty), "truncated": len(trunc),
                          "errors": len(errs), "traced": nthink,
                          "tokens": tok, "think_chars": thk, "secs": round(secs, 1)}

    print("\n== %s   %d/%d -> %d/%d   (%+d)" % (label, bt, len(shared), tt, len(shared), tt - bt))
    print("   traced %d/%d tasks | %d empty answers | %d truncated | %d errors"
          % (nthink, len(items), len(empty), len(trunc), len(errs)))
    print("   cost: %s completion tokens, %.1f h wall, %.0f think-chars/task"
          % ("{:,}".format(tok), secs / 3600, thk / max(len(items), 1)))
    print("   flips: +%d gained, -%d lost" % (len(gained), len(lost)))
    print("   %-13s %5s %6s %6s" % ("category", "n", "base", "think"))
    for c in CATS:
        d = percat[c]
        mark = "" if d["delta"] == 0 else ("  %+d" % d["delta"])
        print("   %-13s %5d %6d %6d%s" % (c, d["n"], d["base"], d["think"], mark))

dst = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "agg_think.json")
json.dump(out, open(dst, "w"), indent=1)
print("\nsaved -> %s" % dst)
