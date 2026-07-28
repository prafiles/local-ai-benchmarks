#!/usr/bin/env python3
"""Convention adherence, measured independently of whether the task passed.

A pass/fail score says a probe went wrong; it doesn't say *how*. This counts two
things directly in the text:

  KEPT     -- the answer uses the value the session established up front
  REVERTED -- the answer uses the generic default the session explicitly overrode

The second is the interesting one. `ubuntu-latest`, `main`, `checkout@v3`,
hardcoded hex colours and `StyleSheet.create` are all things the intro turns ruled
out by name. An answer containing one didn't slip on the task; it stopped using
the conversation.
"""
import json
import os
import re
import sys

MODELS = [("gemma", "Gemma 4 12B QAT"), ("qwen", "Qwen2.5-Coder-14B"),
          ("mellum", "Mellum2-12B-A2.5B"), ("q35", "Qwen3.5-9B FP8")]
DEPTHS = [10000, 35000, 65000, 95000, 112000]

# probe-id prefix -> (kept marker, reverted marker)
RULES = {
    "x-py":  (r"aerelith\.core\.result|Result\(ok=|Result\(True|Result\(False",
              r"^\s*(import|from)\s+itertools"),
    "x-js":  (r"module\.exports\s*=\s*\{", r"module\.exports\s*=\s*(function|\w+\s*;)"),
    "x-ts":  (r"from\s+'\./result'|Result<", r"\bany\b"),
    "x-sh":  (r"ops/bin/aer(log|purge)|AER_LOG_DIR", r"\brm\s+-rf\s+var/spool"),
    "x-git": (r"\btrunk\b|rel/2026\.07", r"\b(main|master)\b"),
    "x-ssh": (r"edge\.aerelith\.internal", r"StrictHostKeyChecking\s+no|ForwardAgent\s+yes"),
    "x-gh":  (r"aer-linux-x64", r"ubuntu-latest|actions/checkout@v[123]\b"),
    "x-doc": (r"\baerctl\b", r"\bwill\b"),
    "x-rn":  (r"useAerTheme", r"StyleSheet\.create|#[0-9a-fA-F]{3,8}\b"),
}


def strip_think(t):
    return re.sub(r"<think>.*?</think>", "", t, flags=re.S)


def scan(items):
    """-> {depth: [kept, reverted, n]}"""
    out = {}
    for tid, v in items.items():
        pre = tid.rsplit("-", 1)[0]
        if pre not in RULES:
            continue
        body = strip_think(v.get("text", ""))
        if not body.strip():
            continue
        keep, rev = RULES[pre]
        d = v.get("_depth")
        e = out.setdefault(d, [0, 0, 0])
        e[2] += 1
        e[0] += 1 if re.search(keep, body, re.I | re.M) else 0
        e[1] += 1 if re.search(rev, body, re.M) else 0
    return out


def main():
    here = "/root/bench2"
    sys.path.insert(0, here)
    import b4  # noqa: E402
    depth_of = {p["id"]: p["depth"] for _c, p in b4.probes()}
    report = {}
    for key, label in MODELS:
        p = f"{here}/c_{key}.json"
        if not os.path.exists(p):
            continue
        data = json.load(open(p))
        row = {}
        for bucket in ("deep", "shallow"):
            items = {k: dict(v, _depth=depth_of[k]) for k, v in data[bucket].items()
                     if k in depth_of}
            row[bucket] = scan(items)
        report[key] = row
        print(f"\n===== {label}")
        print(f"  {'rung':<8}{'kept (deep)':>14}{'reverted (deep)':>18}"
              f"{'kept (shal)':>14}{'reverted (shal)':>18}")
        for d in DEPTHS:
            dd = row["deep"].get(d, [0, 0, 0])
            ss = row["shallow"].get(d, [0, 0, 0])
            print(f"  ~{d//1000:>3}K   {dd[0]:>6}/{dd[2]:<7}{dd[1]:>10}/{dd[2]:<7}"
                  f"{ss[0]:>8}/{ss[2]:<7}{ss[1]:>10}/{ss[2]}")
    json.dump(report, open(f"{here}/conv.json", "w"), indent=1)
    print("\nwrote conv.json")


if __name__ == "__main__":
    main()
