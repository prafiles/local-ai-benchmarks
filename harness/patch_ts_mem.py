#!/usr/bin/env python3
"""Give the TypeScript grader room, and make it complain instead of failing silently.

50 sequential `tsc --strict` runs share one container. At the 2 GB default the
tail of the loop was being killed under contention, which the parser reports as a
contiguous block of BADs -- indistinguishable from the model getting them wrong.
That is the worst kind of harness bug, so it now warns when a case produces no
verdict at all.
"""
p = "/root/bench2/b3.py"
s = open(p).read()

old = '''    out, _e = container("bench-node:1", d, script, timeout=7200)
    return parse_okbad(out, ids)'''

new = '''    out, err = container("bench-node:1", d, script, timeout=7200, mem="6g")
    got = parse_okbad(out, ids)
    missing = [i for i in ids if (" " + i) not in out]
    if missing:
        print("    WARNING: %d ts cases produced NO verdict (container died?): %s"
              % (len(missing), missing[:5]), flush=True)
        print("    stderr tail: %r" % (err[-300:],), flush=True)
    return got'''

if "produced NO verdict" in s:
    print("already patched")
else:
    assert old in s, "grade_ts tail did not match"
    s = s.replace(old, new, 1)
    open(p, "w").write(s)
    print("grade_ts: memory 2g -> 6g, silent-death warning added")
