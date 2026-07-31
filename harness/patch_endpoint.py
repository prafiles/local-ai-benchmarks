#!/usr/bin/env python3
"""Make the endpoint and scratch directory overridable instead of hardcoded.

Both runners pinned `URL` to localhost:8000 (the vLLM container) and `TMP` under
/root/bench2 (the node's filesystem). That was fine while the node was the only
place the suite ever ran. Running the same suite against LM Studio on a Mac needs
a different port and a writable scratch path, and editing the constants per host
is exactly the kind of drift that makes two runs incomparable for a reason nobody
recorded.

Defaults are unchanged, so every existing script and published number keeps its
meaning; only the override is new.

    patch_endpoint.py [target_dir]      # default /root/bench2
"""
import os
import sys

HERE = sys.argv[1] if len(sys.argv) > 1 else "/root/bench2"

SUBS = {
    "b3.py": [
        ('URL = "http://localhost:8000/v1/chat/completions"',
         'URL = os.environ.get("B4_URL", "http://localhost:8000/v1/chat/completions")'),
        ('TMP = "/root/bench2/tmp/run"',
         'TMP = os.environ.get("B4_TMP", "/root/bench2/tmp/run")'),
    ],
    "b4.py": [
        ('URL = "http://localhost:8000/v1/chat/completions"',
         'URL = os.environ.get("B4_URL", "http://localhost:8000/v1/chat/completions")'),
        ('TMP = "/root/bench2/tmp/b4"',
         'TMP = os.environ.get("B4_TMP", "/root/bench2/tmp/b4")'),
    ],
}

for fname, pairs in SUBS.items():
    p = os.path.join(HERE, fname)
    if not os.path.exists(p):
        print(f"{fname}: absent, skipped")
        continue
    s = open(p).read()
    done = []
    for old, new in pairs:
        if new in s:
            done.append("already")
            continue
        assert old in s, f"{fname}: did not match -- {old}"
        s = s.replace(old, new, 1)
        done.append("patched")
    open(p, "w").write(s)
    print(f"{fname}: URL/TMP {'/'.join(done)}")
