#!/usr/bin/env python3
"""Bound the squeeze loop. It converges, but far too slowly to be usable.

Observed on Gemma's deepest probes, 457 rejections in five minutes:

    requested 2537, prompt at least 128536   (total 131073)
    requested 2528, prompt at least 128545   (total 131073)
    requested 2519, prompt at least 128554   (total 131073)

The reported prompt size grows by exactly what the output shrinks by, holding the
total pinned one token above the window. That is the server telling us the PROMPT
ALONE does not fit -- no output budget rescues it. The loop still made progress,
9 tokens a round, so it needed ~275 rounds per attempt and 3 attempts per probe
to reach the bail-out it was always going to reach.

The bound is 3 iterations. Legitimate squeezes converge in one: every one of
Mellum2's six (161, 1997, 2996, 4823, 5579, 6929 tokens) resolved on the first
retry. So this is not an experimental change -- a probe that could be squeezed
still is, with the identical cap, and a probe that could not still ends as a
rejection. Only the number of round-trips to get there changes, from ~800 to 3.

The distinction is recorded: `no_room` marks a prompt that cannot fit the window
at all, which is a different fact from a model answering badly, and a different
fact again from Qwen2.5-Coder's ceiling where the server refuses outright.
"""
p = "/root/bench2/b4.py"
s = open(p).read()

if "SQUEEZE_MAX" in s:
    print("already patched")
    raise SystemExit(0)

old = '''    cap = budget(max_tokens)
    squeezed = 0
    t0 = time.time()
    while True:
        try:
            d = _post(model, msgs, cap)
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            hit = ctx_overflow(body)
            # The session plus a full reasoning budget does not fit the window.
            # Shrink the budget to exactly what is left instead of failing: the
            # probe is measuring the session, and how little room is left to think
            # in at this depth is the interesting part.
            if not hit:
                raise
            window, ptok = hit
            room = window - ptok - 8
            if room <= 64 or room >= cap:
                raise
            cap = room
            squeezed += 1'''

new = '''    cap = budget(max_tokens)
    squeezed = 0
    t0 = time.time()
    # A real squeeze resolves on the first retry. More than a couple of rounds
    # means the prompt itself does not fit, and the loop would otherwise crawl
    # toward that conclusion 9 tokens at a time.
    SQUEEZE_MAX = 3
    for _ in range(SQUEEZE_MAX + 1):
        try:
            d = _post(model, msgs, cap)
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            hit = ctx_overflow(body)
            # The session plus a full reasoning budget does not fit the window.
            # Shrink the budget to exactly what is left instead of failing: the
            # probe is measuring the session, and how little room is left to think
            # in at this depth is the interesting part.
            if not hit:
                raise
            window, ptok = hit
            room = window - ptok - 8
            if room <= 64 or room >= cap:
                raise NoRoom("prompt does not fit the window: %d in a %d window"
                             % (ptok, window))
            cap = room
            squeezed += 1
    else:
        raise NoRoom("prompt does not fit the window after %d squeezes (cap %d)"
                     % (SQUEEZE_MAX, cap))'''

assert old in s, "squeeze loop did not match"
s = s.replace(old, new, 1)

# a named exception so "the window could not hold this session" is distinguishable
# in the results from an ordinary transport failure
s = s.replace("RETRIES = int(os.environ.get(\"B4_RETRIES\", \"0\"))",
              "class NoRoom(Exception):\n"
              "    \"\"\"The prompt alone exceeds the context window.\"\"\"\n\n\n"
              "RETRIES = int(os.environ.get(\"B4_RETRIES\", \"0\"))", 1)

open(p, "w").write(s)
print("b4.py: squeeze bounded to 3 rounds; NoRoom raised when the prompt cannot fit")
