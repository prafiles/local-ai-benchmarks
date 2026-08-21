#!/usr/bin/env python3
"""Hard tier: 104 execution-graded tasks. Runner + batched grader.

    b5.py count
    b5.py run <model> <out.json>
    b5.py grade <out.json>

Why this exists alongside b3.py rather than replacing it: the 600-task tier is
saturated. Across the six Apple Silicon models its per-category pass rates run
84-98%, the top three models sit within 11 points of each other, and the noise
floor measured on re-runs is about 6 tasks. At that point the suite is no longer
measuring anything -- it is reporting which model got lucky on the last dozen.

Three things are different here.

  * ONLY EXECUTION-GRADED WORK. The b3 tier's Docs, ReactNative, SSH-command,
    GitHub-CLI and RAG categories are graded by regex, and they are exactly the
    categories sitting at 96-98%. A regex rewards using the right vocabulary. All
    250 of those tasks are gone; every task here is run, typechecked or executed
    against a real fixture.

  * THE TASKS ARE HARDER ON PURPOSE, along three axes -- spec-exact rules from a
    real specification, near-miss traps on famous problems, and scale gates where
    the quadratic answer cannot finish in the grader's timeout. See the module
    docstrings for which task uses which.

  * MUCH LARGER BUDGETS. b3 gave Python 900 tokens and Bash 220; here they are
    3000 and 700, because several answers are legitimately 100+ lines. The
    reasoning arm's floor moves from 8000 to 32000 for the same reason: on the b3
    tier Qwen3.8 spent its whole 8000-token budget on 24 tasks and returned no
    answer at all, and capping a model mid-thought measures the cap.

The serving layer is b3's, imported rather than copied, so every patch already
applied to it -- the endpoint override, the LM Studio reasoning_effort switch,
the raw-completions escape, retry-on-empty -- applies here unchanged.
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import concurrent.futures

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import b3                       # noqa: E402  -- serving layer, reused wholesale
import b5_jsts as JSTS          # noqa: E402
import b5_python as PY          # noqa: E402
import b5_shell as SH           # noqa: E402
import b5_sql as SQL            # noqa: E402

TMP = os.environ.get("B4_TMP", "/tmp/b5run")

SQL_TASKS, SQL_BROKEN = SQL.build()
assert not SQL_BROKEN, SQL_BROKEN

# Per-task output budgets, 4-6x the b3 tier, because these answers are genuinely
# longer: a streaming RFC 4180 parser, a cron expression evaluator and a
# recursive template-literal type are each well past what 900 tokens holds.
#
# These are the SECOND set of numbers. The first pass used 3000/1200/700 and
# Gemma 4 26B hit the cap on 8 of its 52 failures -- 15% of them were the budget
# running out mid-answer, not the model getting it wrong, which is precisely the
# artefact this tier exists to remove. Raised until no answer is truncated;
# grade() reports `off_capped` so the next model to strain them is visible
# rather than silently mis-scored.
BUDGET = {"py": 5000, "js": 5000, "ts": 5000, "sql": 1500, "sh": 800, "git": 1000}


def all_tasks():
    """[(id, category, kind, prompt, max_tokens)]"""
    t = []
    for tid, spec, _tests, _r in PY.T:
        t.append((tid, "Python", "py",
                  "Write a Python " + spec +
                  "\n\nOutput only the code, no explanation.", BUDGET["py"]))
    for tid, spec, _tests, _r in JSTS.JS:
        t.append((tid, "JS", "js", "Write JavaScript defining " + spec +
                  " Export it with module.exports. Output only the code, no explanation.",
                  BUDGET["js"]))
    for tid, spec, _tests, _r in JSTS.TS:
        t.append((tid, "TS", "ts", "Write TypeScript in a single module that will be " +
                  "imported as './sol'. It must " + spec +
                  " It must typecheck under --strict."
                  " Output only the code, no explanation.", BUDGET["ts"]))
    for tid, prompt, _rows in SQL_TASKS:
        t.append((tid, "SQL", "sql", prompt, BUDGET["sql"]))
    for tid, _s, prompt, _c, _r in SH.SH:
        t.append((tid, "Bash", "sh", prompt +
                  " Reply with a single POSIX sh command line only -- the container has no bash --"
                  " no explanation, no markdown.", BUDGET["sh"]))
    for tid, _s, prompt, _c, _r in SH.GIT:
        t.append((tid, "Git", "git", prompt +
                  " Reply with a single shell command line only, no explanation, no markdown.",
                  BUDGET["git"]))
    return t


# ------------------------------------------------------------------- runner
def run(model, out_path):
    tasks = all_tasks()
    res = {"model": model, "tier": "hard", "items": {},
           "arm": ("native" if (b3.THINK and b3.can_think(model))
                   else "cot" if (b3.COT and not b3.can_think(model)) else "plain")}
    if os.path.exists(out_path):
        try:
            prev = json.load(open(out_path))
            if prev.get("model") == model:
                res["items"] = {k: v for k, v in prev.get("items", {}).items()
                                if not v.get("error")}
                print("  resuming: %d/%d already done" % (len(res["items"]), len(tasks)),
                      flush=True)
        except Exception:  # noqa: BLE001
            print("  existing output unreadable, starting fresh", flush=True)

    todo = [t for t in tasks if t[0] not in res["items"]]
    workers = int(os.environ.get("B4_WORKERS", "1"))
    print("  %d to run, %d concurrent" % (len(todo), workers), flush=True)

    lock = threading.Lock()
    t0 = time.time()
    done = [0]

    def work(task):
        tid, cat, kind, prompt, mt = task
        try:
            r = b3.ask(model, prompt, mt)
        except Exception as e:  # noqa: BLE001
            r = {"text": "", "tok": 0, "secs": 0, "error": "%s: %s" % (type(e).__name__, e)}
        r.update(cat=cat, kind=kind)
        with lock:
            res["items"][tid] = r
            done[0] += 1
            n = done[0]
            if n % 5 == 0 or n == len(todo):
                el = time.time() - t0
                left = (el / n) * (len(todo) - n) / 3600
                # A model that will not stop reasoning looks exactly like a slow
                # model until you count how the generations ended. Qwen3.8's
                # thinking arm burned the entire 32000-token budget on every
                # request at greedy -- 28 minutes each, a projected six days --
                # and the only visible symptom was a progress line that said
                # "elapsed". Report the two numbers that name the cause, and
                # refuse to spend days on a run whose projection is absurd.
                cap = sum(1 for v in res["items"].values()
                          if v.get("finish") == "length")
                mt = sum(1 for v in res["items"].values()
                         if not (v.get("text") or "").strip())
                print("  %d/%d  %.1fm elapsed, ~%.1fh left  [capped %d, no-answer %d]"
                      % (len(res["items"]), len(tasks), el / 60, left, cap, mt),
                      flush=True)
                if left > SPIRAL_WARN_H:
                    print("    WARNING: projected %.0fh for this arm -- %d/%d capped, "
                          "%d unanswered. Check for non-termination."
                          % (left, cap, n, mt), flush=True)
                if left > SPIRAL_ABORT_H:
                    raise RuntimeError(
                        "ABORT: projected %.0fh exceeds B5_ABORT_HOURS=%.0f "
                        "(capped %d/%d, unanswered %d). Fix sampling or budget."
                        % (left, SPIRAL_ABORT_H, cap, n, mt))
                with open(out_path + ".tmp", "w") as f:
                    json.dump(res, f)
                os.replace(out_path + ".tmp", out_path)

    if todo:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            list(ex.map(work, todo))

    with open(out_path + ".tmp", "w") as f:
        json.dump(res, f)
    os.replace(out_path + ".tmp", out_path)
    print("saved -> %s" % out_path)


# ------------------------------------------------------------------ graders
def fresh(name):
    import shutil
    d = os.path.join(TMP, name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    return d


def container(image, stage, script, timeout=10800, mem="4g"):
    open(os.path.join(stage, "_run.sh"), "w").write(script)
    p = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--memory", mem,
         "--pids-limit", "512", "-e", "HOME=/tmp", "-v", "%s:/w" % stage, "-w", "/w",
         image, "sh", "/w/_run.sh"],
        capture_output=True, text=True, timeout=timeout)
    return p.stdout, p.stderr


def _verdicts(out, ids, label):
    got = {i: ("OK " + i) in out for i in ids}
    silent = [i for i in ids if ("OK " + i) not in out and ("BAD " + i) not in out]
    if silent:
        # A grader that returns no verdict at all is not the same as a failure.
        # The b3 tier once reported 0/50 for six whole categories because the
        # sandbox image was missing and the driver died silently; say so loudly.
        print("    WARNING: %d %s cases produced NO verdict (container died?): %s"
              % (len(silent), label, silent[:6]), flush=True)
    return got


def grade_py(items):
    d = fresh("py")
    ids = []
    for tid, _spec, tests, _r in PY.T:
        ids.append(tid)
        cd = os.path.join(d, "cases", tid)
        os.makedirs(cd, exist_ok=True)
        open(os.path.join(cd, "m.py"), "w").write(
            b3.code_of(items[tid]["text"]) + "\n\n" + tests)
    # 120s per case, not b3's 60: several tasks are scale-gated and the
    # reference itself legitimately takes 20s.
    drv = ("import os, subprocess\n"
           "for tid in sorted(os.listdir('/w/cases')):\n"
           "    d='/w/cases/'+tid\n"
           "    try:\n"
           "        r=subprocess.run(['python','m.py'],capture_output=True,text=True,"
           "timeout=120,cwd=d)\n"
           "        print(('OK ' if r.returncode==0 else 'BAD ')+tid)\n"
           "    except subprocess.TimeoutExpired:\n"
           "        print('BAD '+tid)\n")
    open(os.path.join(d, "drv.py"), "w").write(drv)
    out, _e = container("bench-py:1", d, "python /w/drv.py\n")
    return _verdicts(out, ids, "python")


def grade_js(items):
    d = fresh("js")
    ids = []
    for tid, _spec, tests, _r in JSTS.JS:
        ids.append(tid)
        cd = os.path.join(d, "cases", tid)
        os.makedirs(cd, exist_ok=True)
        norm = ("\n;(function(){var m=module.exports;"
                "if(typeof m==='function'&&m.name){var o={};o[m.name]=m;module.exports=o;}})();\n")
        open(os.path.join(cd, "sol.js"), "w").write(b3.code_of(items[tid]["text"]) + norm)
        open(os.path.join(cd, "t.js"), "w").write(tests)
    script = ("for id in $(ls /w/cases); do\n"
              "  if (cd /w/cases/$id && timeout 60 node t.js >/dev/null 2>&1); "
              "then echo \"OK $id\"; else echo \"BAD $id\"; fi\ndone\n")
    out, _e = container("bench-node:1", d, script)
    return _verdicts(out, ids, "js")


def grade_ts(items):
    d = fresh("ts")
    ids = []
    for tid, _spec, tests, _r in JSTS.TS:
        ids.append(tid)
        cd = os.path.join(d, "cases", tid)
        os.makedirs(cd, exist_ok=True)
        open(os.path.join(cd, "sol.ts"), "w").write(b3.code_of(items[tid]["text"]))
        open(os.path.join(cd, "t.ts"), "w").write(tests)
    script = ("for id in $(ls /w/cases); do\n"
              "  if (cd /w/cases/$id && timeout 150 tsc --strict --module commonjs "
              "--target es2020 --types node "
              "--typeRoots /usr/local/lib/node_modules/@types --outDir out sol.ts t.ts "
              ">/dev/null 2>&1 && timeout 60 node out/t.js >/dev/null 2>&1); "
              "then echo \"OK $id\"; else echo \"BAD $id\"; fi\ndone\n")
    out, _e = container("bench-node:1", d, script, mem="6g")
    return _verdicts(out, ids, "ts")


# The SQL grader is the one grader that does NOT run inside a container, so it
# does not inherit the container's timeout -- and a model answer is arbitrary
# code. Qwen3.6-27B wrote a non-terminating query (a recursive CTE with no
# stopping condition); sqlite executed it inside a single C call for 53 minutes
# and blocked the whole sweep, because a wrong answer had become an infinite
# loop instead of a False.
#
# A thread-based timeout cannot fix this: the interpreter never regains control
# during sqlite3_step. set_progress_handler is the mechanism that can -- sqlite
# calls back into Python every N VM opcodes and aborts when the callback returns
# non-zero. The row cap is the second half of the same problem: a cartesian
# product terminates, but not before exhausting memory.
SQL_DEADLINE = float(os.environ.get("B5_SQL_TIMEOUT", "15"))
SQL_ROW_CAP = int(os.environ.get("B5_SQL_ROW_CAP", "100000"))
# Wall-clock sanity on a whole arm. A reasoning arm legitimately runs ~10h here;
# anything projecting past a day means the model is not terminating, not that it
# is thoughtful.
SPIRAL_WARN_H = float(os.environ.get("B5_WARN_HOURS", "20"))
SPIRAL_ABORT_H = float(os.environ.get("B5_ABORT_HOURS", "40"))


def _sql_run(con, sql):
    """Execute one model query under a wall-clock and a row ceiling."""
    stop = time.monotonic() + SQL_DEADLINE
    con.set_progress_handler(lambda: 1 if time.monotonic() > stop else 0, 2000)
    try:
        cur = con.execute(sql)
        rows = cur.fetchmany(SQL_ROW_CAP + 1)
        if len(rows) > SQL_ROW_CAP:
            raise RuntimeError("row cap exceeded")
        return rows
    finally:
        con.set_progress_handler(None, 0)


def grade_sql(items):
    res = {}
    for tid, _prompt, expected in SQL_TASKS:
        sql = b3.code_of(items[tid]["text"]).strip().rstrip(";")
        ok = False
        if sql:
            con = sqlite3.connect(":memory:")
            try:
                con.executescript(SQL.SCHEMA)
                rows = _sql_run(con, sql)

                def norm(rs):
                    return [tuple(round(v, 2) if isinstance(v, float) else v for v in r)
                            for r in rs]
                g, w = norm(rows), norm(expected)
                # Extra trailing columns are tolerated, exactly as in b3, but the
                # row COUNT and ORDER must match: every reference is fully ordered.
                ok = g == w or (len(g) == len(w) and
                                all(a[:len(b)] == b for a, b in zip(g, w)))
            except Exception:  # noqa: BLE001
                ok = False
            finally:
                con.close()
        res[tid] = ok
    return res


def grade_shell(items, rows, name):
    d = fresh(name)
    ids = []
    for tid, setup, _p, chk, _r in rows:
        ids.append(tid)
        open(os.path.join(d, tid + ".setup"), "w").write(setup + "\n")
        open(os.path.join(d, tid + ".cmd"), "w").write(b3.cmd_of(items[tid]["text"]) + "\n")
        open(os.path.join(d, tid + ".chk"), "w").write(chk + "\n")
    open(os.path.join(d, "ids"), "w").write("\n".join(ids) + "\n")
    script = ("mkdir -p /tmp/outs\n"
              "for id in $(cat /w/ids); do\n"
              "  rm -rf /tmp/b/$id; mkdir -p /tmp/b/$id; cd /tmp/b/$id\n"
              "  sh /w/$id.setup >/dev/null 2>&1\n"
              "  OUT=/tmp/outs/$id; export OUT\n"
              "  timeout 60 sh /w/$id.cmd > \"$OUT\" 2>&1\n"
              "  cd /tmp/b/$id\n"
              "  if OUT=/tmp/outs/$id sh /w/$id.chk >/dev/null 2>&1; "
              "then echo \"OK $id\"; else echo \"BAD $id\"; fi\ndone\n")
    out, _e = container("bench-sh:1", d, script, mem="2g")
    return _verdicts(out, ids, name)


def grade(path):
    data = json.load(open(path))
    b3.COT_SPLIT = data.get("arm") == "cot"
    if b3.COT_SPLIT:
        used = sum(1 for v in data["items"].values()
                   if b3.COT_MARK in (v.get("text") or ""))
        print("  CoT arm: %d/%d answers used the %s marker"
              % (used, len(data["items"]), b3.COT_MARK), flush=True)
    items = data["items"]
    have = set(items)
    want = [t[0] for t in all_tasks()]
    missing = [t for t in want if t not in have]
    if missing:
        print("  NOTE: %d/%d tasks absent from %s -- scored 0, not graded: %s"
              % (len(missing), len(want), os.path.basename(path),
                 missing[:6] + (["..."] if len(missing) > 6 else [])), flush=True)
        for tid in missing:
            items[tid] = {"text": "", "tok": 0, "secs": 0, "absent": True}

    ok = {}
    for name, fn in (("python", lambda: grade_py(items)),
                     ("js", lambda: grade_js(items)),
                     ("ts", lambda: grade_ts(items)),
                     ("sql", lambda: grade_sql(items)),
                     ("bash", lambda: grade_shell(items, SH.SH, "sh")),
                     ("git", lambda: grade_shell(items, SH.GIT, "git"))):
        print("  grading %s ..." % name, flush=True)
        ok.update(fn())

    out = {"model": data["model"], "tier": "hard", "results": {}}
    for tid, cat, _k, _p, _m in all_tasks():
        it = items.get(tid, {})
        out["results"][tid] = {"ok": bool(ok.get(tid, False)), "cat": cat,
                               "secs": it.get("secs", 0), "tok": it.get("tok", 0)}
        if it.get("absent"):
            out["results"][tid]["absent"] = True
    gp = path.replace(".json", ".graded.json")
    json.dump(out, open(gp, "w"), indent=1)

    dom = {}
    for tid, r in out["results"].items():
        e = dom.setdefault(r["cat"], [0, 0])
        e[1] += 1
        e[0] += 1 if r["ok"] else 0
    print("\n===== %s  (hard tier)" % data["model"])
    for c in sorted(dom):
        print("  %-13s %3d/%d" % (c, dom[c][0], dom[c][1]))
    tot = (sum(v[0] for v in dom.values()), sum(v[1] for v in dom.values()))
    tok = sum(r["tok"] for r in out["results"].values())
    sec = sum(r["secs"] for r in out["results"].values())
    print("  %-13s %3d/%d" % ("TOTAL", tot[0], tot[1]))
    print("  decode: %d tok / %.0fs = %.1f tok/s" % (tok, sec, tok / max(sec, 1)))
    print("graded -> %s" % gp)


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "count":
        from collections import Counter
        t = all_tasks()
        print("total %d" % len(t))
        for c, n in sorted(Counter(x[1] for x in t).items()):
            print("  %-13s %3d   budget %d" % (c, n, [x[4] for x in t if x[1] == c][0]))
        ids = [x[0] for x in t]
        assert len(ids) == len(set(ids)), "DUPLICATE IDS"
        print("ids unique: ok")
    elif a == "run":
        os.makedirs(TMP, exist_ok=True)
        run(sys.argv[2], sys.argv[3])
    else:
        os.makedirs(TMP, exist_ok=True)
        grade(sys.argv[2])
