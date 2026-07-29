#!/usr/bin/env python3
"""Grade what is present instead of crashing on what is not.

Every grade_* helper indexes items[tid] directly, so a single missing task takes
the whole grader down with a KeyError -- at the END of a multi-hour run, after
all the expensive work is done. It also blocks grading a run in progress, which
is the cheapest way to catch a grader that mishandles reasoning-mode output
before hours of it accumulate.

Missing tasks are reported rather than passed over silently: a task absent from
the file scores 0 in the totals either way, and the difference between "the model
got it wrong" and "the task never ran" has to stay visible.
"""
p = "/root/bench2/b3.py"
s = open(p).read()

if "MISSING_OK" in s:
    print("already patched")
    raise SystemExit(0)

old = '''def grade(path):
    data = json.load(open(path))
    items = data["items"]
    ok = {}'''

new = '''MISSING_OK = True


def grade(path):
    data = json.load(open(path))
    items = data["items"]
    # A grader that dies on the first absent id cannot grade a partial run, and
    # dies at the worst possible moment on a complete one. Stub the gaps and say
    # so; they score 0 regardless, but "never ran" must not read as "got it wrong".
    have = set(items)
    want = [t[0] for t in all_tasks()]
    missing = [t for t in want if t not in have]
    if missing:
        print("  NOTE: %d/%d tasks absent from %s -- scored 0, not graded: %s"
              % (len(missing), len(want), os.path.basename(path),
                 missing[:6] + (["..."] if len(missing) > 6 else [])), flush=True)
        for tid in missing:
            items[tid] = {"text": "", "tok": 0, "secs": 0, "absent": True}
    ok = {}'''

assert old in s, "grade() head did not match"
s = s.replace(old, new, 1)

# carry the flag into the graded file so a partial grade is never mistaken for a
# complete one downstream
old_row = '''        out["results"][tid] = {"ok": bool(ok.get(tid, False)), "cat": cat,
                               "secs": it.get("secs", 0), "tok": it.get("tok", 0)}'''
new_row = '''        out["results"][tid] = {"ok": bool(ok.get(tid, False)), "cat": cat,
                               "secs": it.get("secs", 0), "tok": it.get("tok", 0)}
        if it.get("absent"):
            out["results"][tid]["absent"] = True'''
assert old_row in s, "result row did not match"
s = s.replace(old_row, new_row, 1)

open(p, "w").write(s)
print("grade(): absent tasks stubbed + reported instead of KeyError")
