#!/usr/bin/env python3
"""Let the temperature sweep test greedy, and stop it lying about how it asked.

Two problems when the sweep runs against LM Studio.

1. It hardcodes `chat_template_kwargs: {"enable_thinking": True}`, which this
   server drops on the floor. The sweep was still measuring thinking mode -- these
   models think by DEFAULT, so the trace was on regardless -- but the payload
   claims to be the reason and is not. Anyone reading the script would conclude
   the flag was doing the work.

2. Its three configs all have temperature > 0, because on the vLLM node greedy
   thinking was already known not to terminate. That conclusion was measured on
   Qwen3.5-9B and Gemma 4 12B, and it does not automatically hold for other
   models: this Gemma 4 26B answered 12/12 at every temperature tested, i.e. it
   never spiralled at all. If its thinking also terminates at temperature 0, then
   the off and on arms can be run at IDENTICAL sampling -- which is a strictly
   cleaner comparison than anything in the published report, where temperature had
   to change between arms and is named as a confound.

   That is worth testing rather than inheriting, so configs are now overridable:

       B4_HARD_CONFIGS='t0/greedy=0,-,-  t0.6/k20=0.6,0.95,20'

   Each entry is name=temperature,top_p,top_k with "-" to omit a field.

    patch_hardtemp_mac.py [target_dir]      # default /root/bench2
"""
import os
import sys

HERE = sys.argv[1] if len(sys.argv) > 1 else "/root/bench2"
p = os.path.join(HERE, "hardtemp.py")

OLD_CFG = '''CONFIGS = [
    ("t0.6/k20", {"temperature": 0.6, "top_p": 0.95, "top_k": 20}),
    ("t0.8/k20", {"temperature": 0.8, "top_p": 0.95, "top_k": 20}),
    ("t1.0/k64", {"temperature": 1.0, "top_p": 0.95, "top_k": 64}),
]'''

NEW_CFG = '''CONFIGS = [
    ("t0.6/k20", {"temperature": 0.6, "top_p": 0.95, "top_k": 20}),
    ("t0.8/k20", {"temperature": 0.8, "top_p": 0.95, "top_k": 20}),
    ("t1.0/k64", {"temperature": 1.0, "top_p": 0.95, "top_k": 64}),
]


def _parse_configs(spec):
    """'name=temp,top_p,top_k' entries, whitespace separated, '-' to omit."""
    cfgs = []
    for entry in spec.split():
        name, _, vals = entry.partition("=")
        parts = (vals.split(",") + ["-", "-", "-"])[:3]
        samp = {}
        for field, v in zip(("temperature", "top_p", "top_k"), parts):
            if v and v != "-":
                samp[field] = int(v) if field == "top_k" else float(v)
        cfgs.append((name, samp))
    return cfgs


# Greedy is excluded above because it was measured unusable in thinking mode on
# the two vLLM models -- a conclusion about those models, not a law. Override to
# retest it: if thinking terminates at temperature 0 on a given model, both arms
# can run at identical sampling and the temperature confound disappears.
if os.environ.get("B4_HARD_CONFIGS"):
    CONFIGS = _parse_configs(os.environ["B4_HARD_CONFIGS"])'''

OLD_PAY = '''    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
               "max_tokens": BUDGET, "chat_template_kwargs": {"enable_thinking": True}}'''

NEW_PAY = '''    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
               "max_tokens": BUDGET}
    # How thinking is requested is server-specific. vLLM honours the template
    # kwarg; LM Studio's MLX engine drops it silently and those models think by
    # default, so there the correct payload is one that says nothing at all.
    # Sending the kwarg anyway would still have measured thinking mode, but for
    # the wrong reason -- see patch_lmstudio.py.
    if os.environ.get("B4_OFF_MECH") != "reasoning_effort":
        payload["chat_template_kwargs"] = {"enable_thinking": True}'''

s = open(p).read()
if "B4_HARD_CONFIGS" in s:
    print("hardtemp.py: already patched")
else:
    assert OLD_CFG in s, "CONFIGS did not match"
    assert OLD_PAY in s, "payload did not match"
    s = s.replace(OLD_CFG, NEW_CFG, 1).replace(OLD_PAY, NEW_PAY, 1)
    open(p, "w").write(s)
    print("hardtemp.py: configs overridable, thinking request now stack-aware")
