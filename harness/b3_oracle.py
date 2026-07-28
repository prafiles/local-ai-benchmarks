#!/usr/bin/env python3
"""Build a synthetic 'perfect model' run from every reference solution.

Grading this must yield 600/600. Anything less is a grader bug, and would have
been charged to the models as a failure.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import b3 as B3          # noqa: E402
import b3_django as DJ   # noqa: E402
import b3_git as GITM    # noqa: E402
import b3_jsts as JSTS   # noqa: E402
import b3_misc as M1     # noqa: E402
import b3_python as PY   # noqa: E402
import b3_rag as RAG     # noqa: E402
import b3_shell as SH    # noqa: E402
import b3_sql as SQL     # noqa: E402

items = {}


def put(tid, text):
    items[tid] = {"text": text, "tok": 0, "secs": 0}


for tid, _s, _t, ref in PY.T:
    put(tid, ref)
for tid, _s, _t, ref in DJ.T:
    put(tid, ref)
for tid, _ask, ref in SQL.T:
    put(tid, ref)
for tid, _s, _t, ref in JSTS.JS:
    put(tid, ref)
for tid, _s, _t, ref in JSTS.TS:
    put(tid, ref)
for tid, _s, _p, _c, ref in SH.BASH:
    put(tid, ref)
for tid, _s, _p, _c, ref in GITM.GIT:
    put(tid, ref)
for tid, _p, _a, _spec, ref in M1.SSH_CFG:
    put(tid, ref)
for tid, _p, _pat, ref in M1.SSH_CMD:
    put(tid, ref)
for tid, _s, _chk, ref in M1.GH_WF:
    put(tid, ref)
for tid, _p, _pat, ref in M1.GH_CLI:
    put(tid, ref)
for tid, _p, _pat, ref in B3.DOCS_ALL:
    put(tid, ref)
for tid, _s, _pat, ref in B3.RN_ALL:
    put(tid, ref)
# RAG: the document itself contains every answerable fact; decline the rest.
for tid, _q, _pats in RAG.ANSWERABLE:
    put(tid, RAG.DOC)
for tid, _q, _w in RAG.UNANSWERABLE:
    put(tid, "That is not specified in the document.")

missing = [t[0] for t in B3.all_tasks() if t[0] not in items]
assert not missing, f"no reference for: {missing[:10]}"

out = {"model": "ORACLE(reference solutions)", "items": items}
p = sys.argv[1] if len(sys.argv) > 1 else "/root/bench2/oracle.json"
json.dump(out, open(p, "w"))
print(f"oracle run written: {len(items)} items -> {p}")
