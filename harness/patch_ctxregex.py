#!/usr/bin/env python3
"""Match the context-overflow message this vLLM build actually emits.

The adaptive-budget retry never fired: `squeezed: 0` alongside 3 hard errors. The
regex was written for the older OpenAI/vLLM wording ("N in the messages"), while
this build says:

    This model's maximum context length is 131072 tokens. However, you requested
    8000 output tokens and your prompt contains at least 123073 input tokens, for
    a total of at least 131073 tokens.

Silent-no-match is the dangerous failure here. The probe comes back as an error,
which the runner records and moves past, so a whole rung could quietly become
"rejected" when it was actually answerable in the room that was left -- the exact
mistake that would misreport a model's depth limit as a capability limit.

Both wordings are accepted now, and the parse is verified against a live 400
rather than assumed.
"""
p = "/root/bench2/b4.py"
s = open(p).read()

old = '''CTXERR = re.compile(r"maximum context length is (\\d+) tokens.*?"
                    r"(\\d+) in the messages", re.S)'''

new = '''CTXMAX = re.compile(r"maximum context length is (\\d+) tokens", re.S)
# two wordings in the wild: "N in the messages" (older) and "your prompt contains
# at least N input tokens" (this build)
CTXPROMPT = re.compile(r"(?:(\\d+) in the messages"
                       r"|prompt contains at least (\\d+) input tokens)", re.S)


def ctx_overflow(body):
    """(window, prompt_tokens) if this is a context-length refusal, else None."""
    m, n = CTXMAX.search(body), CTXPROMPT.search(body)
    if not (m and n):
        return None
    return int(m.group(1)), int(n.group(1) or n.group(2))'''

assert old in s, "CTXERR did not match"
s = s.replace(old, new, 1)

old_use = '''            body = e.read().decode("utf-8", "replace")
            m = CTXERR.search(body)
            # The session plus a full reasoning budget does not fit the window.
            # Shrink the budget to exactly what is left instead of failing: the
            # probe is measuring the session, and how little room is left to think
            # in at this depth is the interesting part.
            if not m:
                raise
            window, ptok = int(m.group(1)), int(m.group(2))
            room = window - ptok - 8'''

new_use = '''            body = e.read().decode("utf-8", "replace")
            hit = ctx_overflow(body)
            # The session plus a full reasoning budget does not fit the window.
            # Shrink the budget to exactly what is left instead of failing: the
            # probe is measuring the session, and how little room is left to think
            # in at this depth is the interesting part.
            if not hit:
                raise
            window, ptok = hit
            room = window - ptok - 8'''

assert old_use in s, "overflow handler did not match"
s = s.replace(old_use, new_use, 1)
open(p, "w").write(s)
print("b4.py: context-overflow parse now covers both server wordings")
