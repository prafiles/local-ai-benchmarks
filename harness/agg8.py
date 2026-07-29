#!/usr/bin/env python3
"""The full eight-entry dataset: four models x reasoning off/on, both suites.

Which baseline each arm is differenced against is not uniform, and that is
deliberate rather than sloppy:

  * Native arms (Gemma, Qwen3.5) are compared to the PUBLISHED baseline. Their
    sampling had to change anyway -- thinking mode does not terminate at
    temperature 0 -- so a batching-matched replica would not have bought a clean
    comparison, only a different confound.
  * CoT arms (Mellum2, Qwen2.5-Coder) are compared to a REPLICA baseline captured
    at the same concurrency and temperature. Batching perturbs greedy decoding
    (measured: 6 of 8 prompts reproduced exactly, 2 diverged), so differencing
    against the published run would fold a batching effect into the result. With
    the replica, the prompt is the only thing that changed.

Both baselines are reported per model so the choice is auditable rather than
buried, and the replica-vs-published gap is itself the noise floor every delta in
this report has to clear.

    agg8.py [out.json]
"""
import json
import os
import sys

HERE = "/root/bench2"
CATS = ["Python", "Django", "SQL", "JS", "TS", "Bash", "Git", "SSH", "GitHub",
        "Docs", "ReactNative", "RAG"]

# key, label, reasoning kind, baseline-for-delta
MODELS = [
    ("gemma", "Gemma 4 12B QAT", "native", "r_gemma"),
    ("qwen", "Qwen2.5-Coder-14B", "cot", "b_qwen"),
    ("mellum", "Mellum2-12B-A2.5B", "cot", "b_mellum"),
    ("q35", "Qwen3.5-9B FP8", "native", "r_q35"),
]


def load(p):
    p = os.path.join(HERE, p)
    return json.load(open(p)) if os.path.exists(p) else None


def scores(g):
    return {k: v["ok"] for k, v in g["results"].items()}, \
           {k: v["cat"] for k, v in g["results"].items()}


out = {"short": {}, "long": {}}

print("=" * 74)
print("SHORT CONTEXT -- 600 tasks")
print("=" * 74)
for key, label, kind, basefile in MODELS:
    pub = load("r_%s.graded.json" % key)
    rep = load("%s.graded.json" % basefile)
    th = load("t_%s.graded.json" % key)
    raw = load("t_%s.json" % key)
    if not (pub and th):
        print("  %-22s reasoning arm missing" % label)
        continue
    pubs, cats = scores(pub)
    reps = scores(rep)[0] if rep else pubs
    ths = scores(th)[0]
    items = (raw or {}).get("items", {})

    base_total = sum(reps.values())
    th_total = sum(ths.values())
    percat = {}
    for c in CATS:
        ids = [i for i in cats if cats[i] == c]
        percat[c] = {"off": sum(1 for i in ids if reps[i]),
                     "on": sum(1 for i in ids if ths[i]), "n": len(ids)}
    lost = [i for i in reps if reps[i] and not ths[i]]
    gained = [i for i in reps if not reps[i] and ths[i]]
    churn_base = sum(1 for i in pubs if pubs[i] != reps[i]) if rep else None

    out["short"][key] = {
        "label": label, "kind": kind,
        "published": sum(pubs.values()), "off": base_total, "on": th_total,
        "delta": th_total - base_total, "percat": percat,
        "gained": len(gained), "lost": len(lost),
        "baseline_used": "replica" if rep else "published",
        "batching_churn": churn_base,
        "tokens": sum(v.get("tok", 0) for v in items.values()),
        # Native reasoning is returned in its own field; prompted CoT is inline in
        # the answer text, before the marker. Counting only think_chars would
        # report the CoT arms as having done no reasoning at all.
        "think_chars": (
            sum(v.get("think_chars", 0) for v in items.values()) if kind == "native"
            else sum(max((v.get("text") or "").rfind("ANSWER:"), 0)
                     for v in items.values())),
        "answer_chars": (
            sum(len(v.get("text") or "") for v in items.values()) if kind == "native"
            else sum(len((v.get("text") or "")[
                         (v.get("text") or "").rfind("ANSWER:") + 7:])
                     for v in items.values())),
        "empty": sum(1 for v in items.values() if not (v.get("text") or "").strip()),
        "retried": sum(1 for v in items.values() if v.get("attempts", 1) > 1),
    }
    d = out["short"][key]
    note = ""
    if rep and d["published"] != d["off"]:
        note = "  [published %d; replica used, %s tasks churned by batching]" % (
            d["published"], churn_base)
    print("\n  %-22s %s   %d -> %d  (%+d)%s"
          % (label, kind, d["off"], d["on"], d["delta"], note))
    print("     flips +%d / -%d | tokens %s | think:answer %.1fx | empty %d | retried %d"
          % (d["gained"], d["lost"], format(d["tokens"], ","),
             d["think_chars"] / max(d["answer_chars"], 1), d["empty"], d["retried"]))

print()
print("=" * 74)
print("LONG CONTEXT -- 60 probes, deep and shallow")
print("=" * 74)
for key, label, kind, _b in MODELS:
    base = load("c_%s.graded.json" % key)
    th = load("ct_%s.graded.json" % key)
    raw = load("ct_%s.json" % key)
    if not base:
        continue
    if not th:
        print("  %-22s reasoning arm not run" % label)
        continue
    bd = sum(1 for v in base["results"].values() if v["deep"])
    bs = sum(1 for v in base["results"].values() if v["shallow"])
    td = sum(1 for v in th["results"].values() if v["deep"])
    ts = sum(1 for v in th["results"].values() if v["shallow"])
    deep = (raw or {}).get("deep", {})
    rej = sum(1 for v in deep.values() if v.get("error"))
    sq = [v.get("cap") for v in deep.values() if v.get("squeezed")]

    # A probe the reasoning arm could not even attempt scores 0, which silently
    # charges a window limit to the model as a wrong answer. Gemma's raw deep
    # numbers read 46 -> 46 for exactly that reason; on the 53 probes it could
    # actually run it is 43 -> 46. So the comparable figure is the subset where
    # BOTH arms got a response out of the server.
    braw = load("c_%s.json" % key) or {}
    comparable = [i for i in base["results"]
                  if not deep.get(i, {}).get("error")
                  and not braw.get("deep", {}).get(i, {}).get("error")]
    mb = sum(1 for i in comparable if base["results"][i]["deep"])
    mt = sum(1 for i in comparable if th["results"][i]["deep"])

    out["long"][key] = {"label": label, "kind": kind,
                        "deep_off": bd, "deep_on": td,
                        "shal_off": bs, "shal_on": ts,
                        "matched_n": len(comparable),
                        "matched_off": mb, "matched_on": mt,
                        "rejected": rej, "squeezed": len(sq),
                        "tightest": min(sq) if sq else None}
    extra = ""
    if rej:
        extra += "  %d unrunnable" % rej
    if sq:
        extra += "  %d squeezed (tightest %d tok to think in)" % (len(sq), min(sq))
    print("  %-22s deep %2d -> %2d (%+d)   shallow %2d -> %2d (%+d)%s"
          % (label, bd, td, td - bd, bs, ts, ts - bs, extra))
    print("  %-22s matched deep subset n=%d: %d -> %d (%+d)"
          % ("", len(comparable), mb, mt, mt - mb))

dst = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "agg8.json")
json.dump(out, open(dst, "w"), indent=1)
print("\nsaved -> %s" % dst)
