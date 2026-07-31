#!/usr/bin/env python3
"""Allow a model to be prompted through /v1/completions with a hand-built turn
format, for when the server's chat template is broken.

WHY THIS EXISTS. LM Studio's chat template for the deepseek_vl_v2 architecture
destroys generation. Measured on the same loaded weights:

    /v1/chat/completions   "Say hello."          -> '前辈\\n\\n"Hello I'm a man"...'
    /v1/chat/completions   a real task prompt    -> 'OOOOOOOOOOOO...' (300 tokens)
    /v1/completions        "The capital of France is" -> 'Paris.'
    /v1/completions        "User: ...\\n\\nAssistant:"  -> correct Python

So the weights decode fine and the template is what breaks. Sending
`<|User|>...<|Assistant|>` (DeepSeek-V2's special tokens) as a raw completion is
ALSO degenerate, which identifies the specific bug: those tokens are wrong for
VL2, whose documented turn format is the plain `User:`/`Assistant:` role prefix.

Benchmarking through the broken template would have produced a near-zero score and
charged it to the model. That is the failure this patch prevents -- it is not a
performance tweak.

WHAT IT COSTS. Every other model reaches the sampler through its own working chat
template; this one reaches it through a format written here. The runs are therefore
not template-identical, and that is reported rather than smoothed over. It is still
the closest available approximation to a correct run: the format is the model's own
documented one, which is what a working template would have produced.

Single-turn only, by design. b3's prompts are single-turn, and this model's
4096-token window puts every long-context rung (shallowest 10K) out of reach
anyway, so the multi-turn b4 path is deliberately not given a raw mode.

    B4_RAW_FMT='User: {prompt}\\n\\nAssistant:'
    B4_RAW_STOP='<|User|>,\\nUser:,### Instruction'      # optional

    patch_rawchat.py [target_dir]      # default /root/bench2
"""
import os
import sys

HERE = sys.argv[1] if len(sys.argv) > 1 else "/root/bench2"
p = os.path.join(HERE, "b3.py")

ANCHOR = '''def _once(model, prompt, max_tokens, temp=None):'''

NEW = '''# ------------------------------------------------- broken-chat-template escape
# Set only for a model whose server-side chat template is known broken; see
# patch_rawchat.py for the evidence that this is a template fault and not the
# model. Empty means every model goes through /v1/chat/completions as normal.
RAW_FMT = os.environ.get("B4_RAW_FMT", "")
RAW_STOP = [s for s in os.environ.get("B4_RAW_STOP", "").split(",") if s]
COMPLETIONS_URL = URL.replace("/chat/completions", "/completions")


def _once_raw(model, prompt, max_tokens, temp=None):
    """One generation through /v1/completions, formatting the turn ourselves."""
    payload = sampling({"model": model,
                        "prompt": RAW_FMT.format(prompt=with_cot(model, prompt)),
                        "max_tokens": budget(max_tokens)}, model)
    # A chat endpoint stops at the turn boundary for us; a raw completion will
    # happily begin a new user turn and answer itself, so the boundary has to be
    # supplied or the graded text ends up containing a whole invented dialogue.
    if RAW_STOP:
        payload["stop"] = RAW_STOP
    payload.pop("chat_template_kwargs", None)
    payload.pop("reasoning_effort", None)
    if temp is not None:
        payload["temperature"] = temp
    req = urllib.request.Request(COMPLETIONS_URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=REQ_TIMEOUT) as r:
        d = json.loads(r.read())
    ch = d["choices"][0]
    return {"text": ch.get("text") or "", "think": "", "think_chars": 0,
            "tok": d.get("usage", {}).get("completion_tokens", 0),
            "secs": round(time.time() - t0, 2),
            "finish": ch.get("finish_reason", "")}


def _once(model, prompt, max_tokens, temp=None):'''

s = open(p).read()
if "B4_RAW_FMT" in s:
    print("b3.py: already patched")
    raise SystemExit

assert ANCHOR in s, "could not find _once definition"
s = s.replace(ANCHOR, NEW, 1)

# Route through the raw path when a format is configured. Done inside _once so
# retries, escalation and the empty-answer logic are all unchanged.
OLD_BODY = '''def _once(model, prompt, max_tokens, temp=None):
    payload = sampling({"model": model,'''
NEW_BODY = '''def _once(model, prompt, max_tokens, temp=None):
    if RAW_FMT:
        return _once_raw(model, prompt, max_tokens, temp)
    payload = sampling({"model": model,'''
assert OLD_BODY in s, "could not find _once body"
s = s.replace(OLD_BODY, NEW_BODY, 1)

open(p, "w").write(s)
print("b3.py: raw-completions escape added (B4_RAW_FMT), chat path unchanged")
