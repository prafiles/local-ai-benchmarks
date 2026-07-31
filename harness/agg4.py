#!/usr/bin/env python3
"""Aggregate the short-context suite (600 tasks) with the long-context one (60
probes x2) into the numbers the report is built from."""
import json
import os
import sys

HERE = os.environ.get("B4_OUT", "/root/bench2")
MODELS = [("gemma", "Gemma 4 12B QAT"), ("qwen", "Qwen2.5-Coder-14B"),
          ("mellum", "Mellum2-12B-A2.5B"), ("q35", "Qwen3.5-9B FP8")]
CATS = ["Python", "Django", "SQL", "JS", "TS", "Bash", "Git", "SSH", "GitHub",
        "Docs", "ReactNative", "RAG"]
DEPTHS = [10000, 35000, 65000, 95000, 112000]


def load(p):
    return json.load(open(p)) if os.path.exists(p) else None


def main():
    short = {k: load(f"{HERE}/r_{k}.graded.json") for k, _ in MODELS}
    long_ = {k: load(f"{HERE}/c_{k}.graded.json") for k, _ in MODELS}
    out = {"models": [], "cats": {}, "depths": {}, "notes": []}

    for key, label in MODELS:
        s, L = short.get(key), long_.get(key)
        row = {"key": key, "label": label}
        if s:
            r = s["results"]
            row["short_ok"] = sum(1 for v in r.values() if v["ok"])
            row["short_n"] = len(r)
            tok = sum(v["tok"] for v in r.values())
            sec = sum(v["secs"] for v in r.values())
            row["short_tps"] = round(tok / max(sec, 1), 1)
        if L:
            r = L["results"]
            row["deep_ok"] = sum(1 for v in r.values() if v["deep"])
            row["shal_ok"] = sum(1 for v in r.values() if v["shallow"])
            row["long_n"] = len(r)
            row["retention"] = (round(100 * row["deep_ok"] / row["shal_ok"], 1)
                                if row["shal_ok"] else None)
            row["errors"] = sum(1 for v in r.values() if v["deep_finish"] == "error")
            row["truncated"] = sum(1 for v in r.values() if v["deep_finish"] == "length")
            dp = [v["deep_ptok"] for v in r.values() if v["depth"] == DEPTHS[-1]
                  and v["deep_ptok"]]
            row["max_ptok"] = max(dp) if dp else 0
            row["deep_secs"] = round(sum(v["deep_secs"] for v in r.values()))
        out["models"].append(row)

    for c in CATS:
        e = {}
        for key, _ in MODELS:
            s, L = short.get(key), long_.get(key)
            e[key] = {
                "short": sum(1 for v in s["results"].values()
                             if v["cat"] == c and v["ok"]) if s else None,
                "deep": sum(1 for v in L["results"].values()
                            if v["cat"] == c and v["deep"]) if L else None,
                "shal": sum(1 for v in L["results"].values()
                            if v["cat"] == c and v["shallow"]) if L else None}
        out["cats"][c] = e

    for d in DEPTHS:
        e = {}
        for key, _ in MODELS:
            L = long_.get(key)
            if not L:
                e[key] = None
                continue
            rs = [v for v in L["results"].values() if v["depth"] == d]
            pt = [v["deep_ptok"] for v in rs if v["deep_ptok"]]
            e[key] = {"deep": sum(1 for v in rs if v["deep"]),
                      "shal": sum(1 for v in rs if v["shallow"]),
                      "n": len(rs),
                      "avg_ptok": sum(pt) // len(pt) if pt else 0,
                      "errors": sum(1 for v in rs if v["deep_finish"] == "error")}
        out["depths"][d] = e

    # probes nobody got at depth, and probes only one model got
    have = [k for k, _ in MODELS if long_.get(k)]
    if have:
        ids = list(long_[have[0]]["results"].keys())
        allfail, solo = [], {k: [] for k in have}
        for tid in ids:
            got = [k for k in have if long_[k]["results"][tid]["deep"]]
            if not got:
                allfail.append(tid)
            elif len(got) == 1:
                solo[got[0]].append(tid)
        out["all_fail_deep"] = allfail
        out["solo_deep"] = solo
        # regressions: passed shallow, failed deep -- the pure context penalty
        out["context_loss"] = {
            k: [tid for tid in ids
                if long_[k]["results"][tid]["shallow"] and
                not long_[k]["results"][tid]["deep"]] for k in have}
        out["context_gain"] = {
            k: [tid for tid in ids
                if long_[k]["results"][tid]["deep"] and
                not long_[k]["results"][tid]["shallow"]] for k in have}

    json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "/root/bench2/agg4.json", "w"),
              indent=1)

    print(f"{'model':<22}{'short':>10}{'deep':>8}{'shallow':>9}{'retain':>8}{'errs':>6}")
    for r in out["models"]:
        print(f"{r['label']:<22}{r.get('short_ok','-'):>7}/600"
              f"{r.get('deep_ok','-'):>6}/60{r.get('shal_ok','-'):>7}/60"
              f"{str(r.get('retention','-')) + '%':>8}{r.get('errors','-'):>6}")
    print("\nby depth (deep / shallow, avg measured prompt tokens):")
    for d in DEPTHS:
        line = f"  ~{d//1000:>3}K "
        for key, _ in MODELS:
            e = out["depths"][d].get(key)
            line += (f"| {key}: {e['deep']}/{e['n']} ({e['avg_ptok']//1000}K) "
                     if e else f"| {key}: -- ")
        print(line)
    print("\nper category  short600 / deep60 / shallow60")
    for c in CATS:
        line = f"  {c:<13}"
        for key, _ in MODELS:
            e = out["cats"][c][key]
            line += f"{key}:{e['short']}/{e['deep']}/{e['shal']}  "
        print(line)
    # Qwen2.5-Coder tops out at ~85K, so the two deepest rungs are unreachable for
    # it. Comparing full totals would score it for a hardware limit rather than a
    # capability. This subset is the depths every model could actually attempt.
    sub = {}
    for key, label in MODELS:
        L = long_.get(key)
        if not L:
            continue
        rs = [v for v in L["results"].values() if v["depth"] in DEPTHS[:3]]
        att = [v for v in rs if v["deep_finish"] != "error"]
        sub[key] = {"label": label, "n": len(rs), "attempted": len(att),
                    "deep": sum(1 for v in rs if v["deep"]),
                    "shal": sum(1 for v in rs if v["shallow"])}
    out["matched_subset"] = sub
    print("\nmatched subset -- rungs every model could reach (~10K / 33K / 65K), n=36:")
    for key, e in sub.items():
        print(f"  {e['label']:<22} deep {e['deep']:>2}/{e['n']}   "
              f"shallow {e['shal']:>2}/{e['n']}   "
              f"delta {e['deep'] - e['shal']:+d}   attempted {e['attempted']}/{e['n']}")

    if "context_loss" in out:
        print("\nshallow-pass -> deep-fail (the context penalty itself):")
        for k, v in out["context_loss"].items():
            print(f"  {k:<8} {len(v):>2}  {v}")
        print("all four failed at depth:", out["all_fail_deep"])


if __name__ == "__main__":
    main()
