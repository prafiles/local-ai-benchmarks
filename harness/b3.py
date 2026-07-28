#!/usr/bin/env python3
"""600-task benchmark: runner + batched grader.

    b3.py count
    b3.py run <model> <out.json>
    b3.py grade <out.json>
"""
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import b3_django as DJ      # noqa: E402
import b3_git as GITM       # noqa: E402
import b3_jsts as JSTS      # noqa: E402
import b3_misc as M1        # noqa: E402
import b3_misc2 as M2       # noqa: E402
import b3_python as PY      # noqa: E402
import b3_rag as RAG        # noqa: E402
import b3_shell as SH       # noqa: E402
import b3_sql as SQL        # noqa: E402

URL = "http://localhost:8000/v1/chat/completions"
TMP = "/root/bench2/tmp/run"

SQL_TASKS, SQL_BROKEN = SQL.build()
assert not SQL_BROKEN, SQL_BROKEN

DOCS_ALL = M1.DOCS + M2.DOCS_EXTRA
RN_ALL = M1.RN + M2.RN_EXTRA


def all_tasks():
    """[(id, category, kind, prompt, max_tokens)]"""
    t = []
    for tid, spec, _tests, _r in PY.T:
        t.append((tid, "Python", "py",
                  "Write a Python " + spec + "\n\nOutput only the code, no explanation.", 900))
    for tid, spec, _tests, _r in DJ.T:
        t.append((tid, "Django", "django",
                  DJ.CTX + "Write a " + spec + "\n\nOutput only the code, no explanation.", 700))
    for tid, prompt, _rows in SQL_TASKS:
        t.append((tid, "SQL", "sql", prompt, 400))
    for tid, spec, _tests, _r in JSTS.JS:
        t.append((tid, "JS", "js", "Write JavaScript defining " + spec +
                  " Export it with module.exports. Output only the code, no explanation.", 800))
    for tid, spec, _tests, _r in JSTS.TS:
        t.append((tid, "TS", "ts", "Write TypeScript that " + spec +
                  " It must typecheck under --strict. Output only the code, no explanation.", 800))
    for tid, _s, prompt, _c, _r in SH.BASH:
        t.append((tid, "Bash", "bash",
                  prompt + " Reply with a single shell command only, no explanation, no markdown.", 220))
    for tid, _s, prompt, _c, _r in GITM.GIT:
        t.append((tid, "Git", "git",
                  prompt + " Reply with a single shell command only, no explanation, no markdown.", 220))
    for tid, spec, _alias, _spec2, _r in M1.SSH_CFG:
        t.append((tid, "SSH", "sshcfg", "Write an OpenSSH client config block for " + spec +
                  ". Output only the config file content, no markdown.", 300))
    for tid, prompt, _pats, _r in M1.SSH_CMD:
        t.append((tid, "SSH", "rubric", "Give the command to " + prompt +
                  ". Reply with a single shell command only, no explanation, no markdown.", 220))
    for tid, spec, _chk, _r in M1.GH_WF:
        t.append((tid, "GitHub", "yaml", "Write a GitHub Actions workflow that " + spec +
                  ". Output only the YAML, no markdown fences.", 700))
    for tid, prompt, _pats, _r in M1.GH_CLI:
        t.append((tid, "GitHub", "rubric", "Using the GitHub CLI, " + prompt +
                  ". Reply with a single shell command only, no explanation, no markdown.", 220))
    for tid, prompt, _pats, _r in DOCS_ALL:
        t.append((tid, "Docs", "rubric", prompt, 700))
    for tid, spec, _pats, _r in RN_ALL:
        t.append((tid, "ReactNative", "rubric", "Write " + spec +
                  " Output only the code, no explanation.", 800))
    for tid, prompt in RAG.tasks():
        t.append((tid, "RAG", "rag", prompt, 250))
    return t



# --------------------------------------------------------------- reasoning
# Only two of the four models have a reasoning mode at all: Gemma 4 defaults
# enable_thinking to false in its template, and Qwen3.5 thinks unless told not
# to. Mellum2's template merely strips </think> out of history and Qwen2.5-Coder
# has no thinking in its template whatsoever -- for those two this is a no-op,
# which is the honest outcome rather than a fabricated one.
THINK = os.environ.get("B4_THINK") == "1"
BUDGET_FLOOR = int(os.environ.get("B4_BUDGET", "0"))
BUDGET_MULT = float(os.environ.get("B4_BUDGET_MULT", "1"))
TEMP = float(os.environ.get("B4_TEMP", "0"))
TOPP = float(os.environ.get("B4_TOPP", "0.95"))

THINK_CAPABLE = ("gemma-4", "qwen3.5")

# --------------------------------------------------------------- CoT arm
# For models with no reasoning mode of their own. Asking in the prompt is not the
# same thing as a trained thinking mode, so this arm is reported separately.
COT = os.environ.get("B4_COT") == "1"

COT_PREFIX = (
    "Work through this carefully, step by step, inside <think> and </think> tags.\n"
    "After the closing </think> tag, give ONLY the final answer in exactly the "
    "format requested below, with no commentary before or after it.\n\n"
)


def with_cot(model, prompt):
    """Prepend the reasoning instruction only where the model has no native mode."""
    if COT and not can_think(model):
        return COT_PREFIX + prompt
    return prompt



def can_think(model):
    m = model.lower()
    return any(k in m for k in THINK_CAPABLE)


def budget(mt):
    return max(int(mt * BUDGET_MULT), BUDGET_FLOOR) if THINK else mt


def sampling(payload, model):
    payload["temperature"] = TEMP
    if TEMP > 0:
        payload["top_p"] = TOPP
    if can_think(model):
        # explicit either way: the flag is what separates the two arms
        payload["chat_template_kwargs"] = {"enable_thinking": bool(THINK)}
    return payload


# ------------------------------------------------------------------- runner
def ask(model, prompt, max_tokens):
    payload = sampling({"model": model,
                        "messages": [{"role": "user",
                                      "content": with_cot(model, prompt)}],
                        "max_tokens": budget(max_tokens)}, model)
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as r:
        d = json.loads(r.read())
    ch = d["choices"][0]
    msg = ch["message"]
    # vLLM 0.22 puts the chain of thought in `reasoning`, NOT `reasoning_content`;
    # `content` is left holding the final answer only, so graders need no change
    think = msg.get("reasoning") or msg.get("reasoning_content") or ""
    return {"text": msg.get("content") or "",
            "tok": d["usage"]["completion_tokens"],
            "think_chars": len(think),
            "finish": ch.get("finish_reason", ""),
            "secs": round(time.time() - t0, 2)}


def run(model, out_path):
    tasks = all_tasks()
    res = {"model": model, "items": {}}
    if os.path.exists(out_path):
        try:
            prev = json.load(open(out_path))
            if prev.get("model") == model:
                # keep only clean results; anything that errored gets another go
                res["items"] = {k: v for k, v in prev.get("items", {}).items()
                                if not v.get("error")}
                print(f"  resuming: {len(res['items'])}/{len(tasks)} already done",
                      flush=True)
        except Exception:  # noqa: BLE001
            print("  existing output unreadable, starting fresh", flush=True)
    t0 = time.time()
    done = 0
    for i, (tid, cat, kind, prompt, mt) in enumerate(tasks, 1):
        if tid in res["items"]:
            continue
        try:
            r = ask(model, prompt, mt)
        except Exception as e:  # noqa: BLE001
            r = {"text": "", "tok": 0, "secs": 0, "error": f"{type(e).__name__}: {e}"}
        r.update(cat=cat, kind=kind)
        res["items"][tid] = r
        done += 1
        if done % 10 == 0 or i == len(tasks):
            el = time.time() - t0
            left = len(tasks) - len(res["items"])
            rate = el / max(done, 1)
            print(f"  {len(res['items'])}/{len(tasks)}  {el/60:.1f}m elapsed, "
                  f"~{rate*left/3600:.1f}h left", flush=True)
            with open(out_path, "w") as f:
                json.dump(res, f)
    with open(out_path, "w") as f:
        json.dump(res, f)
    print(f"saved -> {out_path}")


# ------------------------------------------------------------------ helpers
FENCE = re.compile(r"```[a-zA-Z]*\s*\n(.*?)```", re.S)


def strip_think(t):
    return re.sub(r"<think>.*?</think>", "", t, flags=re.S)


def code_of(t):
    t = strip_think(t)
    m = FENCE.search(t)
    return m.group(1) if m else t


def cmd_of(t):
    for line in code_of(strip_think(t)).strip().splitlines():
        s = line.strip()
        if s and not s.startswith("#") and not s.startswith("$"):
            return s
    return ""


def container(image, stage, script, timeout=5400, mem="2g"):
    open(os.path.join(stage, "_run.sh"), "w").write(script)
    p = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--memory", mem,
         "--pids-limit", "512", "-e", "HOME=/tmp", "-v", f"{stage}:/w", "-w", "/w",
         image, "sh", "/w/_run.sh"],
        capture_output=True, text=True, timeout=timeout)
    return p.stdout, p.stderr


def fresh(name):
    d = os.path.join(TMP, name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    return d


def parse_okbad(stdout, ids):
    got = {}
    for ln in stdout.splitlines():
        parts = ln.split()
        if len(parts) == 2 and parts[0] in ("OK", "BAD"):
            got[parts[1]] = parts[0] == "OK"
    return {i: got.get(i, False) for i in ids}


# ------------------------------------------------------------------ graders
FILE_DRIVER = """
import json, os, subprocess
res = {}
for tid in sorted(os.listdir("/w/cases")):
    d = "/w/cases/" + tid
    r = subprocess.run(CMD(d), capture_output=True, text=True, timeout=90, cwd=d)
    print(("OK " if r.returncode == 0 else "BAD ") + tid)
"""


def grade_py(items):
    d = fresh("py")
    ids = []
    for tid, _spec, tests, _r in PY.T:
        ids.append(tid)
        cd = os.path.join(d, "cases", tid)
        os.makedirs(cd, exist_ok=True)
        open(os.path.join(cd, "m.py"), "w").write(
            code_of(items[tid]["text"]) + "\n\n" + tests)
    drv = ("import os, subprocess\n"
           "for tid in sorted(os.listdir('/w/cases')):\n"
           "    d='/w/cases/'+tid\n"
           "    r=subprocess.run(['python','m.py'],capture_output=True,text=True,"
           "timeout=60,cwd=d)\n"
           "    print(('OK ' if r.returncode==0 else 'BAD ')+tid)\n")
    open(os.path.join(d, "drv.py"), "w").write(drv)
    out, _e = container("bench-py:1", d, "python /w/drv.py\n")
    return parse_okbad(out, ids)


def grade_django(items):
    d = fresh("dj")
    os.makedirs(os.path.join(d, "bench_app"), exist_ok=True)
    open(os.path.join(d, "bench_app", "__init__.py"), "w").close()
    open(os.path.join(d, "bench_app", "models.py"), "w").write(DJ.MODELS)
    open(os.path.join(d, "seed.py"), "w").write(DJ.SEED)
    h = (DJ.HARNESS.replace('open("/w/sol.py")', 'open(os.environ["CASE"]+"/sol.py")')
                   .replace('open("/w/test.py")', 'open(os.environ["CASE"]+"/test.py")')
                   .replace("import django, datetime", "import django, datetime, os"))
    open(os.path.join(d, "h.py"), "w").write(h)
    ids = []
    for tid, _spec, tests, _r in DJ.T:
        ids.append(tid)
        cd = os.path.join(d, "cases", tid)
        os.makedirs(cd, exist_ok=True)
        open(os.path.join(cd, "sol.py"), "w").write(code_of(items[tid]["text"]))
        open(os.path.join(cd, "test.py"), "w").write(tests)
    drv = ("import os, subprocess\n"
           "for tid in sorted(os.listdir('/w/cases')):\n"
           "    e=dict(os.environ); e['CASE']='/w/cases/'+tid\n"
           "    r=subprocess.run(['python','/w/h.py'],capture_output=True,text=True,"
           "timeout=90,env=e,cwd='/w')\n"
           "    print(('OK ' if r.returncode==0 else 'BAD ')+tid)\n")
    open(os.path.join(d, "drv.py"), "w").write(drv)
    out, _e = container("bench-py:1", d, "cd /w && python /w/drv.py\n")
    return parse_okbad(out, ids)


def grade_sql(items):
    res = {}
    for tid, _prompt, expected in SQL_TASKS:
        sql = code_of(items[tid]["text"]).strip().rstrip(";")
        ok = False
        if sql:
            con = sqlite3.connect(":memory:")
            try:
                con.executescript(SQL.SCHEMA)
                rows = con.execute(sql).fetchall()

                def norm(rs):
                    return [tuple(round(v, 2) if isinstance(v, float) else v for v in r)
                            for r in rs]
                g, w = norm(rows), norm(expected)
                ok = g == w or (len(g) == len(w) and
                                all(a[:len(b)] == b for a, b in zip(g, w)))
            except Exception:  # noqa: BLE001
                ok = False
            finally:
                con.close()
        res[tid] = ok
    return res


def grade_js(items):
    d = fresh("js")
    ids = []
    for tid, _spec, tests, _r in JSTS.JS:
        ids.append(tid)
        cd = os.path.join(d, "cases", tid)
        os.makedirs(cd, exist_ok=True)
        # `module.exports = fn` and `module.exports = {fn}` are both valid answers;
        # normalise the former so the tests' destructuring works either way.
        norm = ("\n;(function(){var m=module.exports;"
                "if(typeof m==='function'&&m.name){var o={};o[m.name]=m;module.exports=o;}})();\n")
        open(os.path.join(cd, "sol.js"), "w").write(code_of(items[tid]["text"]) + norm)
        open(os.path.join(cd, "t.js"), "w").write(tests)
    script = ("for id in $(ls /w/cases); do\n"
              "  if (cd /w/cases/$id && timeout 30 node t.js >/dev/null 2>&1); "
              "then echo \"OK $id\"; else echo \"BAD $id\"; fi\ndone\n")
    out, _e = container("bench-node:1", d, script)
    return parse_okbad(out, ids)


def grade_ts(items):
    d = fresh("ts")
    ids = []
    for tid, _spec, tests, _r in JSTS.TS:
        ids.append(tid)
        cd = os.path.join(d, "cases", tid)
        os.makedirs(cd, exist_ok=True)
        open(os.path.join(cd, "sol.ts"), "w").write(code_of(items[tid]["text"]))
        open(os.path.join(cd, "t.ts"), "w").write(tests)
    script = ("for id in $(ls /w/cases); do\n"
              "  if (cd /w/cases/$id && timeout 90 tsc --strict --module commonjs "
              "--target es2020 --types node "
              "--typeRoots /usr/local/lib/node_modules/@types --outDir out sol.ts t.ts "
              ">/dev/null 2>&1 && timeout 30 node out/t.js >/dev/null 2>&1); "
              "then echo \"OK $id\"; else echo \"BAD $id\"; fi\ndone\n")
    out, err = container("bench-node:1", d, script, timeout=7200, mem="6g")
    got = parse_okbad(out, ids)
    missing = [i for i in ids if (" " + i) not in out]
    if missing:
        print("    WARNING: %d ts cases produced NO verdict (container died?): %s"
              % (len(missing), missing[:5]), flush=True)
        print("    stderr tail: %r" % (err[-300:],), flush=True)
    return got


def grade_shell(items, rows, name):
    d = fresh(name)
    ids = []
    for tid, setup, _p, chk, _r in rows:
        ids.append(tid)
        open(os.path.join(d, f"{tid}.setup"), "w").write(setup + "\n")
        open(os.path.join(d, f"{tid}.cmd"), "w").write(cmd_of(items[tid]["text"]) + "\n")
        open(os.path.join(d, f"{tid}.chk"), "w").write(chk + "\n")
    open(os.path.join(d, "ids"), "w").write("\n".join(ids) + "\n")
    script = ("mkdir -p /tmp/outs\n"
              "for id in $(cat /w/ids); do\n"
              "  rm -rf /tmp/b/$id; mkdir -p /tmp/b/$id; cd /tmp/b/$id\n"
              "  sh /w/$id.setup >/dev/null 2>&1\n"
              "  OUT=/tmp/outs/$id; export OUT\n"
              "  timeout 30 sh /w/$id.cmd > \"$OUT\" 2>&1\n"
              "  cd /tmp/b/$id\n"
              "  if OUT=/tmp/outs/$id sh /w/$id.chk >/dev/null 2>&1; "
              "then echo \"OK $id\"; else echo \"BAD $id\"; fi\ndone\n")
    out, _e = container("bench-sh:1", d, script)
    return parse_okbad(out, ids)


def grade_sshcfg(items):
    d = fresh("sshcfg")
    ids, specs = [], {}
    for tid, _p, alias, spec, _r in M1.SSH_CFG:
        ids.append(tid)
        specs[tid] = spec
        open(os.path.join(d, f"{tid}.cfg"), "w").write(code_of(items[tid]["text"]))
        open(os.path.join(d, f"{tid}.alias"), "w").write(alias + "\n")
    open(os.path.join(d, "ids"), "w").write("\n".join(ids) + "\n")
    script = ("for id in $(cat /w/ids); do\n"
              "  cp /w/$id.cfg /tmp/c && chmod 600 /tmp/c\n"
              "  echo \"### $id\"\n"
              "  ssh -G -F /tmp/c $(cat /w/$id.alias) 2>/dev/null | tr 'A-Z' 'a-z'\n"
              "done\n")
    out, _e = container("bench-sh:1", d, script)
    blocks, cur = {}, None
    for ln in out.splitlines():
        if ln.startswith("### "):
            cur = ln[4:].strip()
            blocks[cur] = {}
        elif cur:
            p = ln.strip().split(None, 1)
            if len(p) == 2:
                blocks[cur][p[0]] = p[1]
    # ssh -G normalises some booleans: `no` is reported as `false`, `yes` as `true`
    equiv = {"no": {"no", "false"}, "yes": {"yes", "true"},
             "false": {"no", "false"}, "true": {"yes", "true"}}

    def matches(got_v, want_v):
        want_v = want_v.lower()
        return got_v in equiv.get(want_v, {want_v})

    res = {}
    for tid in ids:
        got = blocks.get(tid, {})
        res[tid] = bool(got) and all(matches(got.get(k, ""), v)
                                     for k, v in specs[tid].items())
    return res


YAML_CHECKS = {
 "ci": "assert 'push' in s and 'pull_request' in s and 'main' in s\n"
       "assert 'actions/checkout' in st and 'setup-python' in st and '3.12' in st\n"
       "assert 'requirements.txt' in st and 'pytest' in st",
 "matrix": "m=json.dumps(j.get('strategy',{}).get('matrix',{}))\n"
           "assert all(v in m for v in ('18','20','22'))\n"
           "assert 'ubuntu-latest' in json.dumps(j.get('runs-on'))\n"
           "assert 'actions/checkout' in st and 'npm test' in st",
 "cron": "assert 'schedule' in s and 'cron' in s and '4' in s\n"
         "assert 'actions/checkout' in st and 'nightly.sh' in st",
 "needs": "assert 'push' in s and 'main' in s\n"
          "assert any('needs' in jj for jj in d['jobs'].values())\n"
          "assert 'build' in json.dumps(d['jobs'])",
 "dispatch": "assert 'workflow_dispatch' in s and 'environment' in s\n"
             "assert 'environment' in st",
 "secret": "assert 'pull_request' in s\nassert 'API_TOKEN' in st and 'secrets' in st",
 "cache": "assert 'actions/cache' in st and '.npm' in st",
 "artifact": "assert 'upload-artifact' in st and 'build-output' in st and 'dist' in st",
 "timeout": "assert 'timeout-minutes' in json.dumps(j) and '15' in json.dumps(j)\n"
            "assert 'continue-on-error' in st",
 "ifcond": "assert 'if' in json.dumps(j) and 'refs/heads/main' in json.dumps(j)",
}


def grade_yaml(items):
    d = fresh("yaml")
    ids = []
    for tid, _spec, chk, _r in M1.GH_WF:
        ids.append(tid)
        cd = os.path.join(d, "cases", tid)
        os.makedirs(cd, exist_ok=True)
        open(os.path.join(cd, "w.yml"), "w").write(code_of(items[tid]["text"]))
        body = ("import yaml, json\n"
                "d=yaml.safe_load(open('w.yml'))\n"
                "on=d.get('on', d.get(True))\n"
                "s=json.dumps(on)\n"
                "j=list(d['jobs'].values())[0]\n"
                "st=json.dumps(d['jobs'])\n" + YAML_CHECKS[chk] + "\nprint('ok')\n")
        open(os.path.join(cd, "chk.py"), "w").write(body)
    drv = ("import os, subprocess\n"
           "for tid in sorted(os.listdir('/w/cases')):\n"
           "    d='/w/cases/'+tid\n"
           "    r=subprocess.run(['python','chk.py'],capture_output=True,text=True,"
           "timeout=30,cwd=d)\n"
           "    print(('OK ' if r.returncode==0 else 'BAD ')+tid)\n")
    open(os.path.join(d, "drv.py"), "w").write(drv)
    out, _e = container("bench-py:1", d, "python /w/drv.py\n")
    return parse_okbad(out, ids)


def grade_rubric(items):
    res = {}
    groups = [(M1.SSH_CMD, 2), (M1.GH_CLI, 2), (DOCS_ALL, 2), (RN_ALL, 2)]
    for rows, pat_ix in groups:
        for row in rows:
            tid, pats = row[0], row[pat_ix]
            body = strip_think(items[tid]["text"])
            res[tid] = all(re.search(p, body, re.I | re.S) for p in pats)
    return res


def grade_rag(items):
    res = {}
    for tid, _q, pats in RAG.ANSWERABLE:
        b = strip_think(items[tid]["text"])
        res[tid] = all(re.search(p, b, re.I) for p in pats)
    for tid, _q, _w in RAG.UNANSWERABLE:
        b = strip_think(items[tid]["text"])
        res[tid] = any(re.search(p, b, re.I) for p in RAG.REFUSAL)
    return res


def grade(path):
    data = json.load(open(path))
    items = data["items"]
    ok = {}
    for name, fn in (("python", lambda: grade_py(items)),
                     ("django", lambda: grade_django(items)),
                     ("sql", lambda: grade_sql(items)),
                     ("js", lambda: grade_js(items)),
                     ("ts", lambda: grade_ts(items)),
                     ("bash", lambda: grade_shell(items, SH.BASH, "bash")),
                     ("git", lambda: grade_shell(items, GITM.GIT, "git")),
                     ("sshcfg", lambda: grade_sshcfg(items)),
                     ("yaml", lambda: grade_yaml(items)),
                     ("rubric", lambda: grade_rubric(items)),
                     ("rag", lambda: grade_rag(items))):
        print(f"  grading {name} ...", flush=True)
        ok.update(fn())

    out = {"model": data["model"], "results": {}}
    for tid, cat, _k, _p, _m in all_tasks():
        it = items.get(tid, {})
        out["results"][tid] = {"ok": bool(ok.get(tid, False)), "cat": cat,
                               "secs": it.get("secs", 0), "tok": it.get("tok", 0)}
    gp = path.replace(".json", ".graded.json")
    json.dump(out, open(gp, "w"), indent=1)

    dom = {}
    for tid, r in out["results"].items():
        e = dom.setdefault(r["cat"], [0, 0])
        e[1] += 1
        e[0] += 1 if r["ok"] else 0
    print(f"\n===== {data['model']}")
    for c in sorted(dom):
        print(f"  {c:<13} {dom[c][0]:>3}/{dom[c][1]}")
    tot = (sum(v[0] for v in dom.values()), sum(v[1] for v in dom.values()))
    tok = sum(r["tok"] for r in out["results"].values())
    sec = sum(r["secs"] for r in out["results"].values())
    print(f"  {'TOTAL':<13} {tot[0]:>3}/{tot[1]}")
    print(f"  decode: {tok} tok / {sec:.0f}s = {tok/max(sec,1):.1f} tok/s")
    print(f"graded -> {gp}")


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "count":
        t = all_tasks()
        from collections import Counter
        print(f"total {len(t)}")
        for c, n in sorted(Counter(x[1] for x in t).items()):
            print(f"  {c:<13} {n}")
        ids = [x[0] for x in t]
        assert len(ids) == len(set(ids)), "DUPLICATE IDS"
        print("ids unique: ok")
    elif a == "run":
        os.makedirs(TMP, exist_ok=True)
        run(sys.argv[2], sys.argv[3])
    else:
        os.makedirs(TMP, exist_ok=True)
        grade(sys.argv[2])
