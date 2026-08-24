#!/usr/bin/env python3
"""Every hard-tier run, both stacks, in one table.

aggb5.py reports the original seven MLX models and is left alone -- it is what
the tier's first write-up quotes. This is the superset: it also covers the GGUF
re-runs, the vLLM/CUDA node, and the thinking-only models.

Three things it does that aggb5.py does not:

  * It does not silently drop a model that has no off arm. aggb5.py does
    `if not complete(off_g): continue`, which is correct for an A/B table and
    wrong for a roster -- Muse and both Ornith models are thinking-only by
    design and vanished from the report without a line of explanation.

  * It prints per-category off -> on, not just off. On a reasoning tier the
    per-category *movement* is the finding; the off column alone hides it.

  * It marks which arms are single-variable. An arm is only a clean measurement
    of reasoning if it is greedy AND unresampled; anything else is reported with
    the reason it is confounded, because those numbers are not comparable to the
    clean ones no matter how much better they look.

    aggall.py
"""
import json
import os

CATS = ["Python", "JS", "TS", "SQL", "Bash", "Git"]
N = 104
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# key, label, note. THINK_ONLY models have no off arm by design.
MAC_MLX = [
    ("gemma26",   "Gemma 4 26B A4B QAT",   "MLX 4bit"),
    ("q38",       "Qwen3.8 27B",           "MLX; on arm inherited the model's xhigh default"),
    ("q38effort", "Qwen3.8 27B @ medium",  "MLX; effort=medium -- the corrected arm"),
    ("q36",       "Qwen3.6 27B",           "MLX"),
    ("q36moe",    "Qwen3.6 35B A3B",       "MLX"),
    ("glm47",     "GLM 4.7 Flash",         "MLX 6bit"),
    ("qcn",       "Qwen3-Coder-Next 80B",  "MLX; prompted CoT, no native thinking"),
    ("dsvl2",     "DeepSeek VL2",          "MLX; raw /v1/completions, broken chat template"),
]
MAC_GGUF = [
    ("gemma26gguf",  "Gemma 4 26B A4B",   "GGUF; MLX thinking arm is mlx-engine#337"),
    ("q36gguf",      "Qwen3.6 27B",       "GGUF Q4_K_S"),
    ("q36moegguf",   "Qwen3.6 35B A3B",   "GGUF UD-Q4_K_S"),
    ("glm47gguf",    "GLM 4.7 Flash",     "GGUF Q4_K_S"),
    ("q38gguf",      "Qwen3.8 27B",       "GGUF; reasoning_effort silently ignored here"),
    ("ornith35",     "Ornith 1.5 35B A3B","GGUF Q8_0, thinking-only"),
    ("muse",         "Muse Glimmer 30B",  "GGUF Q8_0, thinking-only"),
]
# Labels here are taken from the "model" field inside each result file, not
# from the run key. The keys are short ("qwen", "q35") and do not say which
# model they are: "qwen" is Qwen2.5-Coder-14B, not any Qwen3.x, and "q35" is a
# 9B, not a 32B. Guessing from the key produced a table that compared the Mac's
# Qwen3.6-27B against a completely different model on CUDA.
CUDA = [
    ("gemma",       "Gemma 4 12B QAT",          "vLLM w4a16"),
    ("gemmagreedy", "Gemma 4 12B QAT",          "vLLM, greedy -- does not terminate"),
    ("q35",         "Qwen3.5 9B FP8",           "vLLM"),
    ("qwen",        "Qwen2.5-Coder 14B AWQ",    "vLLM"),
    ("mellum",      "Mellum2 12B A2.5B FP8",    "vLLM"),
    ("ornith9",     "Ornith 1.5 9B",            "vLLM, thinking-only"),
]
THINK_ONLY = {"muse", "ornith35", "ornith9"}


def load(here, p):
    f = os.path.join(here, p)
    return json.load(open(f)) if os.path.exists(f) else None


def totals(g):
    r = g["results"]
    return ({k: v["ok"] for k, v in r.items()}, {k: v["cat"] for k, v in r.items()})


def percat(ok, cat):
    return {c: (sum(1 for i in ok if cat[i] == c and ok[i]),
                sum(1 for i in cat if cat[i] == c)) for c in CATS}


def confounds(raw, key, profdir):
    """Why this arm is or is not a single-variable measurement of reasoning.

    profdir matters: the CUDA profiles live beside the CUDA results, not in
    results/mac. Looking in the wrong place finds no file, and "no file" must
    never be reported as "greedy" -- that turns an unchecked arm into a clean
    one on the strength of a missing path.
    """
    out = []
    items = (raw or {}).get("items", {})
    resampled = sum(1 for v in items.values() if v.get("attempts", 1) > 1)
    if resampled:
        out.append("%d/%d answers came from a HOTTER resample" % (resampled, N))
    prof = os.path.join(profdir, "chosen_%s.json" % key)
    if not os.path.exists(prof):
        out.append("no chosen_%s.json found -- sampling UNVERIFIED" % key)
    else:
        smp = json.load(open(prof)).get("sampling", {})
        if smp.get("temperature", 0.0) != 0.0:
            out.append("profile is t%.2f, not greedy" % smp["temperature"])
    return out


def report(title, here, models, profdir):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)
    for key, label, note in models:
        off_g, on_g = load(here, "hb_%s.graded.json" % key), load(here, "ht_%s.graded.json" % key)
        on_raw = load(here, "ht_%s.json" % key)
        for g, what in ((off_g, "off"), (on_g, "on")):
            if g and len(g.get("results", {})) < N:
                print("  %-24s %s arm PARTIAL (%d/%d) -- not scored"
                      % (label, what, len(g["results"]), N))
        off_g = off_g if off_g and len(off_g["results"]) == N else None
        on_g = on_g if on_g and len(on_g["results"]) == N else None

        if not off_g and not on_g:
            print("  %-24s not run" % label)
            continue

        if off_g and on_g:
            o, cat = totals(off_g)
            n_, _ = totals(on_g)
            ot, nt = sum(o.values()), sum(n_.values())
            arm = (on_raw or {}).get("arm", "?")
            armtag = {"native": "native", "cot": "prompted CoT", "plain": "PLAIN(!)"}.get(arm, arm)
            print("\n  %-24s off %3d  ->  on %3d  (%+d)   [%s]  %s"
                  % (label, ot, nt, nt - ot, armtag, note))
            po, pn = percat(o, cat), percat(n_, cat)
            print("     " + "  ".join("%s %d->%d/%d" % (c, po[c][0], pn[c][0], po[c][1])
                                      for c in CATS))
            gained = sum(1 for i in o if not o[i] and n_[i])
            lost = sum(1 for i in o if o[i] and not n_[i])
            print("     flips +%d / -%d" % (gained, lost), end="")
            cf = confounds(on_raw, key, profdir)
            print(" | CONFOUNDED: " + "; ".join(cf) if cf
                  else " | clean: greedy, unresampled")
        elif on_g and key in THINK_ONLY:
            n_, cat = totals(on_g)
            pn = percat(n_, cat)
            print("\n  %-24s      thinking-only %3d/%d      %s" % (label, sum(n_.values()), N, note))
            print("     " + "  ".join("%s %d/%d" % (c, pn[c][0], pn[c][1]) for c in CATS))
            print("     no off arm by design -- a standalone score, not a delta")
        else:
            g = off_g or on_g
            t, cat = totals(g)
            print("\n  %-24s %s arm only %3d/%d      %s"
                  % (label, "off" if off_g else "on", sum(t.values()), N, note))


MACOUT = os.path.join(REPO, "results", "hard")
MACPROF = os.path.join(REPO, "results", "mac")
CUOUT = os.path.join(REPO, "results", "cuda-hard")
report("MAC / LM STUDIO / MLX -- Apple M2 Max 64GB", MACOUT, MAC_MLX, MACPROF)
report("MAC / LM STUDIO / GGUF -- Apple M2 Max 64GB", MACOUT, MAC_GGUF, MACPROF)
report("CUDA / vLLM 0.22.1 -- RTX 4060 Ti 16GB", CUOUT, CUDA, CUOUT)
print()
