#!/usr/bin/env python3
"""The hard-tier dataset: each model's reasoning off and on, 104 tasks.

Reports the same shape as aggmac.py -- off, on, delta, per-category, flips,
tokens, think:answer ratio, empties -- plus the two numbers that matter most for
a NEW tier and are meaningless once it saturates:

  * SPREAD: the gap between the best and worst model. On the b3 tier this had
    collapsed to 11 points out of 600 across the top three models, which is
    inside twice the measured noise floor. A tier only discriminates while this
    number is large relative to that floor.

  * HEADROOM: how far the leader is from full marks. b3's leader was at 96.5%,
    so 97% of the suite was measuring nothing about the difference between
    models -- only the last 21 tasks carried any signal at all.

    aggb5.py [out.json]
"""
import json
import os
import sys

HERE = os.environ.get("B4_OUT", "/tmp/b5run")
CATS = ["Python", "JS", "TS", "SQL", "Bash", "Git"]
N_TASKS = 104

# key, label, params, notes
MODELS = [
    ("gemma26", "Gemma 4 26B A4B QAT", "26B MoE / 4B active", ""),
    ("q38", "Qwen3.8 27B", "27B dense", ""),
    ("q36", "Qwen3.6 27B", "27B dense", ""),
    ("q36moe", "Qwen3.6 35B A3B", "35B MoE / 3B active", ""),
    ("glm47", "GLM 4.7 Flash", "MoE lite, 6-bit", ""),
    ("qcn", "Qwen3-Coder-Next", "80B MoE / 3B active", ""),
    # Prompted through /v1/completions, not the chat template -- see
    # patch_rawchat.py. Its answers are coherent prose and syntactically
    # plausible code, so this is a capability floor and not a template artefact.
    ("dsvl2", "DeepSeek VL2", "27B MoE / 4B active, vision-language",
     "raw /v1/completions, broken chat template"),
]


def load(p):
    f = os.path.join(HERE, p)
    return json.load(open(f)) if os.path.exists(f) else None


def scores(g):
    return ({k: v["ok"] for k, v in g["results"].items()},
            {k: v["cat"] for k, v in g["results"].items()})


out = {"hard": {}, "meta": {"host": "Apple M2 Max 64GB", "server": "LM Studio / MLX",
                            "workers": 1, "off_mechanism": "reasoning_effort=none",
                            "tasks": N_TASKS, "grading": "execution only"}}

print("=" * 78)
print("HARD TIER -- %d execution-graded tasks, LM Studio / MLX on Apple M2 Max" % N_TASKS)
print("=" * 78)

for key, label, params, note in MODELS:
    off_g = load("hb_%s.graded.json" % key)
    on_g = load("ht_%s.graded.json" % key)
    on_raw = load("ht_%s.json" % key)
    off_raw = load("hb_%s.json" % key)
    # An aborted arm leaves a short graded file behind, and a short file scores
    # like a catastrophe: GLM's 5-task partial graded 2/104, which read as a
    # collapse under reasoning rather than a run that stopped early. A score is
    # only a score when every task ran.
    def complete(g, what):
        if not g:
            return False
        # grade() pads an aborted arm to full length with zeros, so
        # len(results) is always 104 and cannot detect a short run. "ran"
        # is the count actually executed.
        n = g.get("ran", len(g.get("results", {})))
        if n < N_TASKS:
            print("  %-24s %s arm PARTIAL (%d/%d tasks) -- not scored"
                  % (label, what, n, N_TASKS))
            return False
        return True

    if not complete(off_g, "off"):
        continue
    if not complete(on_g, "on"):
        on_g = None
    offs, cats = scores(off_g)
    off_total = sum(offs.values())
    d = {"label": label, "params": params, "off": off_total, "on": None, "note": note}

    if on_g:
        ons = scores(on_g)[0]
        d["on"] = sum(ons.values())
        d["delta"] = d["on"] - d["off"]
        d["gained"] = sum(1 for i in offs if not offs[i] and ons[i])
        d["lost"] = sum(1 for i in offs if offs[i] and not ons[i])
        items = (on_raw or {}).get("items", {})
        d["tokens"] = sum(v.get("tok", 0) for v in items.values())
        d["empty"] = sum(1 for v in items.values() if not (v.get("text") or "").strip())
        think = sum(v.get("think_chars", 0) for v in items.values())
        answer = sum(len(v.get("text") or "") for v in items.values())
        d["think_answer"] = round(think / max(answer, 1), 1)
        # ask() resamples HOTTER than the profile when a trace leaves no answer,
        # so on a model that often returns no answer the reported score is not
        # the profile's decode while the off arm it is compared against is.
        # Gemma scores 82 that way and 52 on its own greedy profile -- one is a
        # tier lead, the other is two tasks WORSE than not thinking. Report both,
        # because only the second is a single-variable comparison.
        d["resampled"] = sum(1 for v in items.values() if v.get("attempts", 1) > 1)
        if items:
            d["on_greedy"] = sum(1 for i, ok in ons.items()
                                 if ok and items.get(i, {}).get("attempts", 1) == 1)
            d["greedy_delta"] = d["on_greedy"] - d["off"]

    d["percat"] = {}
    for c in CATS:
        ids = [i for i in cats if cats[i] == c]
        e = {"off": sum(1 for i in ids if offs[i]), "n": len(ids)}
        if on_g:
            e["on"] = sum(1 for i in ids if scores(on_g)[0][i])
        d["percat"][c] = e

    oi = (off_raw or {}).get("items", {})
    d["off_tokens"] = sum(v.get("tok", 0) for v in oi.values())
    # A task that hit the output cap did not fail on capability, it failed on
    # budget -- and this tier exists partly because b3 was hiding that.
    d["off_capped"] = sum(1 for v in oi.values() if v.get("finish") == "length")

    out["hard"][key] = d
    print("\n  %-24s %-22s off %d/%d%s"
          % (label, params, d["off"], N_TASKS,
             "  ->  on %d  (%+d)" % (d["on"], d["delta"]) if d["on"] is not None else
             "   (reasoning arm not run)"))
    print("     per category: " + "  ".join(
        "%s %d/%d" % (c, d["percat"][c]["off"], d["percat"][c]["n"]) for c in CATS))
    print("     off arm: %s tokens, %d answers hit the output cap"
          % (format(d["off_tokens"], ","), d["off_capped"]))
    if d["on"] is not None:
        print("     on arm: flips +%d / -%d | %s tokens | think:answer %.1fx | empty %d"
              % (d["gained"], d["lost"], format(d["tokens"], ","),
                 d["think_answer"], d["empty"]))
        # The other way an arm stops being single-variable: its profile is not
        # the greedy the off arm always uses. Every off arm runs B4_PROFILES='{}'
        # -> temperature 0, so a thinking arm with any other sampling differs
        # from it in two ways at once. Qwen3.6-MoE (t1.0/p0.95/k64) and GLM
        # (t1.0/p0.95) both do, and neither was visibly flagged before.
        chosen = os.path.join(os.environ.get("B4_CHOSEN_DIR", ""),
                              "chosen_%s.json" % key)
        try:
            samp = json.load(open(chosen)).get("sampling", {})
        except Exception:  # noqa: BLE001
            samp = None
        if samp is not None and samp != {"temperature": 0.0}:
            d["on_sampling"] = samp
            print("     CONFOUND: on arm sampled at %s, off arm at greedy -- the arms "
                  "differ in sampling as well as reasoning." % samp)
        if d.get("resampled"):
            # "greedy-only" is the wrong word when the profile is not greedy --
            # Qwen3.6-MoE runs t1.0/p0.95/k64, so its first-attempt score is
            # profile-only, not greedy-only. Say which one it actually is.
            word = ("greedy-only" if samp == {"temperature": 0.0}
                    else "profile-only")
            print("     CONFOUND: %d/%d answers came from a HOTTER resample, not the "
                  "profile. %s: %d/%d (%+d vs off) -- the resample-free number."
                  % (d["resampled"], N_TASKS, word.capitalize(), d["on_greedy"],
                     N_TASKS, d["greedy_delta"]))

ran = list(out["hard"].values())
if ran:
    # Rank on the comparable number. A score reached by resampling hotter than
    # the profile is not the same measurement as one decoded at the profile, and
    # ranking on the raw value crowned Gemma at 82 when its own greedy arm
    # scores 52 -- below its no-thinking result. Where an arm was resampled, its
    # greedy-only score is the one that is comparable to everyone else's.
    def cmp_score(x):
        if x["on"] is None:
            return x["off"]
        if x.get("resampled"):
            return x.get("on_greedy", x["on"])
        return x["on"]
    best_key = max(ran, key=cmp_score)
    best = cmp_score(best_key)
    worst_row = min(ran, key=cmp_score)
    worst = cmp_score(worst_row)
    print("\n" + "=" * 78)
    print("  models measured: %d" % len(ran))
    print("  leader: %s at %d/%d (%.0f%%) -- HEADROOM %d tasks%s"
          % (best_key["label"], best, N_TASKS, 100.0 * best / N_TASKS, N_TASKS - best,
             "  [greedy-only; raw resampled score %d]" % best_key["on"]
             if best_key.get("resampled") and best_key["on"] != best else ""))
    print("  SPREAD best to worst: %d tasks (%.0f%% of the suite)"
          % (best - worst, 100.0 * (best - worst) / N_TASKS))
    print("  for comparison, the b3 tier's leader scored 579/600 = 96.5%, and its")
    print("  top three models spanned 11 tasks against a ~6-task noise floor.")

p = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "aggb5.json")
json.dump(out, open(p, "w"), indent=1)
print("\nsaved -> %s" % p)
