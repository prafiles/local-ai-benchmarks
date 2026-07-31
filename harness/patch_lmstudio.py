#!/usr/bin/env python3
"""Teach the runners the LM Studio serving stack, without touching vLLM behaviour.

Two things differ, and both would have produced a quietly wrong report.

1. THINK_CAPABLE is a substring list written when four models existed. On LM
   Studio the models are gemma-4-26b-a4b-qat and qwen3.6-*: "gemma-4" still
   matches, "qwen3.6" does not match "qwen3.5". Left alone, both Qwen3.6 models
   would be classed as having no reasoning mode and routed to the prompted-CoT
   arm -- while in fact they think by default, so the CoT arm's own baseline
   would ALSO have been thinking. Every entry for them would have been a
   reasoning run wearing a different label.

2. chat_template_kwargs never reaches the template. Measured: enable_thinking
   absent / False / True return byte-identical output on qwen3.6-35b-a3b (904
   completion tokens, 899 reasoning tokens, 2442 trace chars, all three). So the
   flag that separates the two arms on vLLM is a no-op here, and the off arm has
   to come from somewhere else.

   Of four candidates only reasoning_effort worked. On all three models
   `reasoning_effort: "none"` took reasoning_tokens to 0 and left the answer
   correct. `/no_think` merely shortened the trace (899 -> 699 tokens) without
   stopping it, and LM Studio's own {"reasoning": {"enabled": false}} was
   ignored like the template kwarg. Seeding a closed `<think></think>` did
   suppress the trace, but changed the answers to 24, 10 and 60 on a question
   whose answer is 30 -- it suppresses thinking by derailing generation, which is
   not an off arm.

   These models think BY DEFAULT, so the on arm sends nothing at all and the off
   arm is the one that carries a flag. That is the opposite of the vLLM arms, and
   the reason this is a switch rather than an edit.

Both changes are opt-in via env, so every published number keeps its meaning:

    B4_THINK_CAPABLE=qwen3.6      extra substrings, comma-separated
    B4_OFF_MECH=reasoning_effort  default "template" = existing vLLM behaviour

    patch_lmstudio.py [target_dir]      # default /root/bench2
"""
import os
import sys

HERE = sys.argv[1] if len(sys.argv) > 1 else "/root/bench2"

OLD_CAP = 'THINK_CAPABLE = ("gemma-4", "qwen3.5")'
NEW_CAP = '''THINK_CAPABLE = ("gemma-4", "qwen3.5")
# Extra substrings for models this list predates -- e.g. qwen3.6, whose name does
# not match "qwen3.5" but which thinks by default. Misclassifying a thinking model
# as non-thinking is the worst failure available here: it routes the model to the
# prompted-CoT arm, whose baseline would then also be thinking, and every entry
# for that model becomes a reasoning run with a baseline label.
THINK_CAPABLE += tuple(x.strip().lower() for x in
                       os.environ.get("B4_THINK_CAPABLE", "").split(",") if x.strip())

# How the two arms are separated. "template" is chat_template_kwargs, which is
# what vLLM honours and what every published number used. "reasoning_effort" is
# for servers that silently drop chat_template_kwargs (measured on LM Studio's
# MLX engine) and where the model thinks by default -- there the ON arm sends
# nothing and the OFF arm is the one carrying the flag.
OFF_MECH = os.environ.get("B4_OFF_MECH", "template")'''

OLD_SAMP = '''    if can_think(model):
        # explicit either way: the flag is what separates the two arms
        tmpl = {"enable_thinking": bool(THINK)}
        tmpl.update(tmpl_extra)
        payload["chat_template_kwargs"] = tmpl
    return payload'''

NEW_SAMP = '''    if can_think(model):
        if OFF_MECH == "reasoning_effort":
            # This server ignores chat_template_kwargs, and the model thinks by
            # default, so only the OFF arm needs to say anything. Sending nothing
            # on the ON arm is deliberate: it is the model's own default mode.
            if not THINK:
                payload["reasoning_effort"] = "none"
        else:
            # explicit either way: the flag is what separates the two arms
            tmpl = {"enable_thinking": bool(THINK)}
            tmpl.update(tmpl_extra)
            payload["chat_template_kwargs"] = tmpl
    return payload'''

for fname in ("b3.py", "b4.py"):
    p = os.path.join(HERE, fname)
    if not os.path.exists(p):
        print(f"{fname}: absent, skipped")
        continue
    s = open(p).read()
    if "B4_OFF_MECH" in s:
        print(f"{fname}: already patched")
        continue
    assert OLD_CAP in s, f"{fname}: THINK_CAPABLE did not match"
    assert OLD_SAMP in s, f"{fname}: sampling() thinking block did not match"
    s = s.replace(OLD_CAP, NEW_CAP, 1).replace(OLD_SAMP, NEW_SAMP, 1)
    open(p, "w").write(s)
    print(f"{fname}: THINK_CAPABLE extendable, off-arm mechanism switchable")
