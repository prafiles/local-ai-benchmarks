#!/usr/bin/env python3
"""Let a profile carry chat-template kwargs, not just sampling fields.

If the trace cap that works turns out to be a template variable (thinking_budget)
rather than a sampling field, it has to end up inside chat_template_kwargs. Under
the plain `payload.update(profile)` it would instead be posted as a top-level
`_tmpl` field, which vLLM ignores silently -- the run would look tuned and be
uncapped. Same class of bug as reasoning_content vs reasoning.
"""
p = "/root/bench2/b3.py"
s = open(p).read()

old = '''def sampling(payload, model):
    payload.update(profile_for(model))
    if can_think(model):
        # explicit either way: the flag is what separates the two arms
        payload["chat_template_kwargs"] = {"enable_thinking": bool(THINK)}
    return payload'''

new = '''def sampling(payload, model):
    prof = dict(profile_for(model))
    tmpl_extra = prof.pop("_tmpl", {})
    payload.update(prof)
    if can_think(model):
        # explicit either way: the flag is what separates the two arms
        tmpl = {"enable_thinking": bool(THINK)}
        tmpl.update(tmpl_extra)
        payload["chat_template_kwargs"] = tmpl
    return payload'''

if "_tmpl" in s:
    print("already patched")
else:
    assert old in s, "sampling() did not match"
    open(p, "w").write(s.replace(old, new, 1))
    print("sampling(): profile _tmpl now merges into chat_template_kwargs")
