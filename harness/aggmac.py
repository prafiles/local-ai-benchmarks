#!/usr/bin/env python3
"""The Apple Silicon dataset: each model's reasoning off and on, 600 tasks.

Differs from agg8.py in what the delta is measured against, and it is worth being
explicit about why this set is cleaner.

  * There is no published-vs-replica choice to make. Concurrency buys nothing on
    MLX (4 concurrent measured 84 tok/s against 79 single-stream), so every run
    here is at one worker. The batching effect that forced matched replicas on the
    vLLM node -- where re-running 8 stored prompts at a different --max-num-seqs
    reproduced 6 exactly and diverged on 2 -- cannot arise. The off arm is the
    baseline, captured at the same serving config as the on arm.

  * Whether SAMPLING is matched varies per model, and that is the single most
    important caveat attached to any delta here, so it is computed rather than
    described. The off arm is always greedy. If chosen_<key>.json also says
    temperature 0, the two arms differ in exactly one thing -- whether reasoning
    was suppressed -- and the delta is a genuine single-variable measurement, which
    nothing in the published vLLM report can claim. If the model needed heat to
    stop its traces spiralling, the delta carries a sampling confound and is
    labelled as such.

Reasoning is suppressed with reasoning_effort rather than the template flag,
because this server silently drops chat_template_kwargs -- see patch_lmstudio.py.

    aggmac.py [out.json]
"""
import json
import os
import sys

HERE = os.environ.get("B4_OUT", "/root/bench2")
CATS = ["Python", "Django", "SQL", "JS", "TS", "Bash", "Git", "SSH", "GitHub",
        "Docs", "ReactNative", "RAG"]

# key, label, params, notes
MODELS = [
    ("gemma26", "Gemma 4 26B A4B QAT", "26B MoE / 4B active", ""),
    ("q36", "Qwen3.6 27B", "27B dense", ""),
    ("q36moe", "Qwen3.6 35B A3B", "35B MoE / 3B active", ""),
    ("q38", "Qwen3.8 27B", "27B dense, vision-language",
     "24 traces never terminated and returned no answer; on the 576 it did answer, 535 -> 556 (+21)"),
    ("glm47", "GLM 4.7 Flash", "MoE lite, 6-bit", ""),
    ("qcn", "Qwen3-Coder-Next", "80B MoE / 3B active",
     "no native reasoning mode (confirmed on the model card); prompted-CoT arm, both sides greedy"),
    ("dsvl2", "DeepSeek VL2", "27B MoE / 4.5B active",
     "4096-token window: CoT budget capped near 3000, not the 8000 the others get"),
]


def load(p):
    f = os.path.join(HERE, p)
    return json.load(open(f)) if os.path.exists(f) else None


def scores(g):
    return ({k: v["ok"] for k, v in g["results"].items()},
            {k: v["cat"] for k, v in g["results"].items()})


out = {"short": {}, "meta": {"host": "Apple M2 Max 64GB", "server": "LM Studio / MLX",
                             "workers": 1, "off_mechanism": "reasoning_effort=none"}}

print("=" * 78)
print("SHORT CONTEXT -- 600 tasks, LM Studio / MLX on Apple M2 Max")
print("=" * 78)

for key, label, params, note in MODELS:
    off_g = load("b_%s.graded.json" % key)
    on_g = load("t_%s.graded.json" % key)
    on_raw = load("t_%s.json" % key)
    chosen = load("chosen_%s.json" % key)
    if not off_g:
        print("\n  %-24s no off arm" % label)
        continue
    offs, cats = scores(off_g)
    off_total = sum(offs.values())
    if not on_g:
        print("\n  %-24s off %d/600; reasoning arm not run" % (label, off_total))
        out["short"][key] = {"label": label, "params": params, "off": off_total,
                             "on": None, "note": note}
        continue
    ons = scores(on_g)[0]
    on_total = sum(ons.values())
    items = (on_raw or {}).get("items", {})

    samp = (chosen or {}).get("sampling", {})
    matched = float(samp.get("temperature", 1)) == 0.0
    arm = (on_raw or {}).get("arm", "?")

    percat = {}
    for c in CATS:
        ids = [i for i in cats if cats[i] == c]
        percat[c] = {"off": sum(1 for i in ids if offs[i]),
                     "on": sum(1 for i in ids if ons[i]), "n": len(ids)}
    lost = [i for i in offs if offs[i] and not ons[i]]
    gained = [i for i in offs if not offs[i] and ons[i]]

    # Native reasoning lands in its own think_chars field; prompted CoT has no
    # such field -- the reasoning is inline in the answer text, before the
    # ANSWER: marker. Counting only think_chars for a "cot" arm would report it
    # as having done no reasoning at all, which is what happened before this
    # branch existed (qcn showed think:answer 0.0x despite an 8/8 compliance
    # check that measured real explanations before the marker).
    if arm == "cot":
        think = sum(max((v.get("text") or "").rfind("ANSWER:"), 0)
                    for v in items.values())
        answer = sum(len((v.get("text") or "")[
                         (v.get("text") or "").rfind("ANSWER:") + 7:])
                     for v in items.values())
    else:
        think = sum(v.get("think_chars", 0) for v in items.values())
        answer = sum(len(v.get("text") or "") for v in items.values())
    d = {
        "label": label, "params": params, "arm": arm, "note": note,
        "off": off_total, "on": on_total, "delta": on_total - off_total,
        "percat": percat, "gained": len(gained), "lost": len(lost),
        "on_sampling": samp, "sampling_matched": matched,
        "tokens": sum(v.get("tok", 0) for v in items.values()),
        "think_chars": think, "answer_chars": answer,
        "empty": sum(1 for v in items.values() if not (v.get("text") or "").strip()),
        "retried": sum(1 for v in items.values() if v.get("attempts", 1) > 1),
    }
    out["short"][key] = d

    print("\n  %-24s %-22s %d -> %d  (%+d)" % (label, params, d["off"], d["on"],
                                               d["delta"]))
    print("     flips +%d / -%d | tokens %s | think:answer %.1fx | empty %d | retried %d"
          % (d["gained"], d["lost"], format(d["tokens"], ","),
             think / max(answer, 1), d["empty"], d["retried"]))
    print("     on-arm sampling %s -- %s"
          % (json.dumps(samp),
             "MATCHED to the off arm: single-variable delta"
             if matched else "hotter than the off arm: delta carries a sampling confound"))
    if note:
        print("     note: %s" % note)

ran = [d for d in out["short"].values() if d.get("on") is not None]
if ran:
    print("\n" + "=" * 78)
    print("  %d of %d models have both arms" % (len(ran), len(MODELS)))
    clean = [d for d in ran if d["sampling_matched"]]
    print("  single-variable (both arms greedy): %s"
          % (", ".join(d["label"] for d in clean) or "none"))
    print("  ranking by reasoning-on score: %s"
          % " > ".join("%s %d" % (d["label"], d["on"])
                       for d in sorted(ran, key=lambda x: -x["on"])))

p = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "aggmac.json")
json.dump(out, open(p, "w"), indent=1)
print("\nsaved -> %s" % p)
