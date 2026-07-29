#!/usr/bin/env python3
"""Runner + grader for the 50-task agentic benchmark and RAG set.

    b2.py setup                    build sandbox images
    b2.py run <model> <out.json>   query the vLLM endpoint
    b2.py grade <out.json>         grade and emit <out>.graded.json
"""
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b2_tasks import (  # noqa: E402
    BASH, DJANGO, DJANGO_MODELS, DOCS, GIT, GITHUB, JS, PYTHON, RAG, RAG_DOC,
    REFUSAL, RN, SQL, SQL_SCHEMA, SSH, TS,
)

URL = "http://localhost:8000/v1/chat/completions"
TMP = "/root/bench2/tmp"
IMG_PY, IMG_NODE, IMG_SH = "bench-py:1", "bench-node:1", "bench-sh:1"

# ------------------------------------------------------------------ sandboxes
DOCKERFILES = {
    # pyyaml must be baked in: graders run with --network none
    IMG_PY: "FROM python:3.12-slim\nRUN pip install --no-cache-dir django==5.1.4 pyyaml==6.0.2\n",
    IMG_NODE: "FROM node:22-alpine\nRUN npm i -g typescript@5.6.3 @types/node@22\n",
    IMG_SH: ("FROM alpine:3.20\n"
             "RUN apk add --no-cache git openssh-client tar coreutils findutils "
             "grep sed bash gzip\n"),
}


def setup():
    os.makedirs(TMP, exist_ok=True)
    for tag, df in DOCKERFILES.items():
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "Dockerfile"), "w") as f:
            f.write(df)
        print(f"building {tag} ...", flush=True)
        p = subprocess.run(["docker", "build", "-q", "-t", tag, d],
                           capture_output=True, text=True)
        print("  ok" if p.returncode == 0 else f"  FAILED: {p.stderr[-400:]}")
        shutil.rmtree(d, ignore_errors=True)


def sandbox(image, files, script, timeout=180):
    """Run `script` in a network-less container over a throwaway dir of `files`."""
    os.makedirs(TMP, exist_ok=True)
    d = tempfile.mkdtemp(dir=TMP)
    try:
        for name, content in files.items():
            path = os.path.join(d, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
        with open(os.path.join(d, "_run.sh"), "w") as f:
            f.write(script)
        os.chmod(d, 0o777)
        p = subprocess.run(
            ["docker", "run", "--rm", "--network", "none", "--memory", "1g",
             "--pids-limit", "256", "-e", "HOME=/w", "-v", f"{d}:/w", "-w", "/w",
             image, "sh", "/w/_run.sh"],
            capture_output=True, text=True, timeout=timeout,
        )
        return p.returncode == 0, (p.stdout or "")[-8000:], (p.stderr or "")[-300:]
    except subprocess.TimeoutExpired:
        return False, "", "harness timeout"
    finally:
        subprocess.run(["docker", "run", "--rm", "-v", f"{d}:/x", "alpine",
                        "sh", "-c", "rm -rf /x/* /x/.[!.]* 2>/dev/null || true"],
                       capture_output=True)
        shutil.rmtree(d, ignore_errors=True)


# -------------------------------------------------------------------- prompts
def all_prompts():
    """[(id, domain, kind, prompt, max_tokens)]"""
    out = []
    for tid, prompt, _t in PYTHON:
        out.append((tid, "Python", "py", prompt, 900))
    for tid, prompt, _t in DJANGO:
        out.append((tid, "Django", "django", prompt, 700))
    for tid, prompt, _rows in SQL:
        out.append((tid, "SQL", "sql", prompt, 400))
    for tid, prompt, _t in JS:
        out.append((tid, "JS", "js", prompt, 800))
    for tid, prompt, _t in TS:
        out.append((tid, "TS", "ts", prompt, 800))
    for tid, _setup, prompt, _chk in BASH:
        out.append((tid, "Bash", "bash", prompt, 200))
    for tid, _setup, prompt, _chk in GIT:
        out.append((tid, "Git", "git", prompt, 200))
    for tid, prompt, alias, spec in SSH:
        out.append((tid, "SSH", "sshcfg" if alias else "rubric", prompt,
                    300 if alias else 200))
    for tid, prompt, spec in GITHUB:
        out.append((tid, "GitHub", "yaml" if isinstance(spec, str) else "rubric",
                    prompt, 700 if isinstance(spec, str) else 200))
    for tid, prompt, _pats in DOCS:
        out.append((tid, "Docs", "rubric", prompt, 600))
    for tid, prompt, _pats in RN:
        out.append((tid, "ReactNative", "rubric", prompt, 700))
    for tid, q, _pats, _unans in RAG:
        p = ("Answer the question using ONLY the document below. If the document does not "
             "contain the answer, say so explicitly and do not guess.\n\n"
             f"--- DOCUMENT ---\n{RAG_DOC}\n--- END ---\n\nQuestion: {q}")
        out.append((tid, "RAG", "rag", p, 250))
    return out


def ask(model, prompt, max_tokens):
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "max_tokens": max_tokens, "temperature": 0}
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1200) as r:
        d = json.loads(r.read())
    return {"text": d["choices"][0]["message"]["content"] or "",
            "tok": d["usage"]["completion_tokens"],
            "secs": round(time.time() - t0, 2)}


def run(model, out_path):
    res = {"model": model, "items": {}}
    tasks = all_prompts()
    for i, (tid, domain, kind, prompt, mt) in enumerate(tasks, 1):
        print(f"  [{i:>2}/{len(tasks)}] {domain}/{tid}", flush=True)
        try:
            r = ask(model, prompt, mt)
        except Exception as e:  # noqa: BLE001
            r = {"text": "", "tok": 0, "secs": 0, "error": f"{type(e).__name__}: {e}"}
        r.update(domain=domain, kind=kind)
        res["items"][tid] = r
        with open(out_path, "w") as f:
            json.dump(res, f, indent=1)
    print(f"saved -> {out_path}")


# -------------------------------------------------------------------- helpers
FENCE = re.compile(r"```[a-zA-Z]*\s*\n(.*?)```", re.S)


def code_of(text):
    m = FENCE.search(text)
    return m.group(1) if m else text


def cmd_of(text):
    for line in code_of(text).strip().splitlines():
        s = line.strip()
        if s and not s.startswith("#") and not s.startswith("$"):
            return s
    return ""


def strip_think(text):
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S)


# -------------------------------------------------------------------- graders
def g_py(text, tests):
    src = code_of(text) + "\n\n" + tests
    ok, _o, err = sandbox(IMG_PY, {"m.py": src}, "timeout 30 python /w/m.py\n")
    return ok, err.strip().splitlines()[-1][:110] if err.strip() else ""


DJ_HARNESS = """
import django, datetime
from django.conf import settings
settings.configure(DEBUG=True, USE_TZ=True,
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    INSTALLED_APPS=["bench_app"], DEFAULT_AUTO_FIELD="django.db.models.BigAutoField")
django.setup()
from django.db import connection
from bench_app.models import Author, Book
with connection.schema_editor() as se:
    se.create_model(Author); se.create_model(Book)
ann = Author.objects.create(name="Ann", country="UK")
bob = Author.objects.create(name="Bob", country="US")
Book.objects.create(title="B1", author=ann, price=10, published=datetime.date(2021,1,1))
Book.objects.create(title="B2", author=ann, price=20, published=datetime.date(2022,1,1))
Book.objects.create(title="B3", author=bob, price=30, published=datetime.date(2023,1,1))
exec(open("/w/sol.py").read(), globals())
exec(open("/w/test.py").read(), globals())
print("OK")
"""


def g_django(text, tests):
    files = {"bench_app/__init__.py": "", "bench_app/models.py": DJANGO_MODELS,
             "sol.py": code_of(text), "test.py": tests, "h.py": DJ_HARNESS}
    ok, _o, err = sandbox(IMG_PY, files, "timeout 60 python /w/h.py\n")
    return ok, err.strip().splitlines()[-1][:110] if err.strip() else ""


def g_sql(text, expected):
    sql = code_of(text).strip().rstrip(";")
    if not sql:
        return False, "empty"
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(SQL_SCHEMA)
        rows = con.execute(sql).fetchall()
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {str(e)[:80]}"
    finally:
        con.close()

    def norm(rs):
        out = []
        for r in rs:
            out.append(tuple(round(v, 2) if isinstance(v, float) else v for v in r))
        return out
    got, want = norm(rows), norm(expected)
    if got == want:
        return True, ""
    # tolerate extra trailing columns only if the leading ones match exactly
    if len(got) == len(want) and all(
            g[:len(w)] == w for g, w in zip(got, want)):
        return True, ""
    return False, f"got {got[:3]}"


def g_js(text, tests):
    files = {"sol.js": code_of(text), "t.js": tests}
    ok, _o, err = sandbox(IMG_NODE, files, "timeout 30 node /w/t.js\n")
    return ok, err.strip().splitlines()[-1][:110] if err.strip() else ""


TSC = ("cd /w && timeout 90 tsc --strict --module commonjs --target es2020 "
       "--types node --typeRoots /usr/local/lib/node_modules/@types "
       "--outDir out sol.ts t.ts 2>&1 | head -5 && "
       "test -f out/t.js && timeout 30 node out/t.js\n")


def g_ts(text, tests):
    files = {"sol.ts": code_of(text), "t.ts": tests}
    ok, out, err = sandbox(IMG_NODE, files, TSC)
    msg = (err or out).strip().splitlines()
    return ok, (msg[-1][:110] if msg else "")


def g_shell(text, setup_sh, checker, image=IMG_SH):
    cmd = cmd_of(strip_think(text))
    if not cmd:
        return False, "empty"
    script = (f"set -e\nmkdir -p /w/box && cd /w/box\n{setup_sh}\nset +e\n"
              f"{cmd}\ncd /w/box\n{checker}\n")
    ok, _o, err = sandbox(image, {}, script)
    return ok, (cmd[:80] if not ok else "")


def g_sshcfg(text, alias, spec):
    cfg = code_of(text)
    # grep the keys we care about in-container: ssh -G emits 50+ lines
    keys = "|".join(spec.keys())
    script = (f"cp /w/cfg /w/c && chmod 600 /w/c && "
              f"ssh -G -F /w/c {alias} 2>/dev/null | tr 'A-Z' 'a-z' "
              f"| grep -E '^({keys}) '\n")
    ok, out, _e = sandbox(IMG_SH, {"cfg": cfg}, script)
    if not ok:
        return False, "ssh -G rejected config"
    got = {}
    for line in out.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            got[parts[0]] = parts[1]
    miss = [k for k, v in spec.items() if got.get(k, "") != v.lower()]
    return (not miss), (f"wrong/missing: {miss}" if miss else "")


def g_yaml(text, which):
    body = code_of(text)
    files = {"w.yml": body, "chk.py": _YAML_CHECK[which]}
    ok, _o, err = sandbox(IMG_PY, files, "timeout 30 python /w/chk.py\n")
    return ok, err.strip().splitlines()[-1][:110] if err.strip() else ""


_YAML_CHECK = {
    "workflow_ci": """
import yaml, json
d = yaml.safe_load(open('/w/w.yml'))
on = d.get('on', d.get(True))
assert on, 'no trigger'
s = json.dumps(on)
assert 'push' in s and 'pull_request' in s, f'triggers: {s}'
assert 'main' in s, 'main branch not targeted'
jobs = d['jobs']; j = list(jobs.values())[0]
steps = json.dumps(j['steps'])
assert 'actions/checkout' in steps, 'no checkout'
assert 'setup-python' in steps, 'no setup-python'
assert '3.12' in steps, 'python 3.12 missing'
assert 'requirements.txt' in steps, 'no requirements install'
assert 'pytest' in steps, 'no pytest'
print('OK')
""",
    "workflow_matrix": """
import yaml, json
d = yaml.safe_load(open('/w/w.yml'))
j = list(d['jobs'].values())[0]
m = json.dumps(j['strategy']['matrix'])
for v in ('18','20','22'):
    assert v in m, f'node {v} missing from matrix'
assert 'ubuntu-latest' in json.dumps(j.get('runs-on')), 'runs-on'
steps = json.dumps(j['steps'])
assert 'actions/checkout' in steps and 'npm test' in steps, 'steps'
print('OK')
""",
}


def g_rubric(text, pats):
    body = strip_think(text)
    miss = [p for p in pats if not re.search(p, body, re.I | re.S)]
    return (not miss), (f"missing {miss[:2]}" if miss else "")


def g_rag(text, pats, unanswerable):
    body = strip_think(text)
    if unanswerable:
        declined = any(re.search(p, body, re.I) for p in REFUSAL)
        return declined, ("" if declined else "hallucinated instead of declining")
    miss = [p for p in pats if not re.search(p, body, re.I)]
    return (not miss), (f"missing {miss[:2]}" if miss else "")


# ---------------------------------------------------------------------- grade
def grade(path):
    data = json.load(open(path))
    items = data["items"]
    out = {"model": data["model"], "results": {}}

    def put(tid, ok, note):
        it = items.get(tid, {})
        out["results"][tid] = {"ok": bool(ok), "note": note,
                               "domain": it.get("domain", "?"),
                               "secs": it.get("secs", 0), "tok": it.get("tok", 0)}
        print(f"  {'PASS' if ok else 'FAIL'}  {tid:<18} {note[:80]}")

    for tid, _p, tests in PYTHON:
        put(tid, *g_py(items[tid]["text"], tests))
    for tid, _p, tests in DJANGO:
        put(tid, *g_django(items[tid]["text"], tests))
    for tid, _p, rows in SQL:
        put(tid, *g_sql(items[tid]["text"], rows))
    for tid, _p, tests in JS:
        put(tid, *g_js(items[tid]["text"], tests))
    for tid, _p, tests in TS:
        put(tid, *g_ts(items[tid]["text"], tests))
    for tid, setup_sh, _p, chk in BASH:
        put(tid, *g_shell(items[tid]["text"], setup_sh, chk))
    for tid, setup_sh, _p, chk in GIT:
        put(tid, *g_shell(items[tid]["text"], setup_sh, chk))
    for tid, _p, alias, spec in SSH:
        if alias:
            put(tid, *g_sshcfg(items[tid]["text"], alias, spec))
        else:
            put(tid, *g_rubric(items[tid]["text"], spec))
    for tid, _p, spec in GITHUB:
        if isinstance(spec, str):
            put(tid, *g_yaml(items[tid]["text"], spec))
        else:
            put(tid, *g_rubric(items[tid]["text"], spec))
    for tid, _p, pats in DOCS:
        put(tid, *g_rubric(items[tid]["text"], pats))
    for tid, _p, pats in RN:
        put(tid, *g_rubric(items[tid]["text"], pats))
    for tid, _q, pats, unans in RAG:
        put(tid, *g_rag(items[tid]["text"], pats, unans))

    gp = path.replace(".json", ".graded.json")
    with open(gp, "w") as f:
        json.dump(out, f, indent=1)

    dom = {}
    for tid, r in out["results"].items():
        d = dom.setdefault(r["domain"], [0, 0])
        d[1] += 1
        d[0] += 1 if r["ok"] else 0
    print(f"\n===== {data['model']}")
    for d in sorted(dom):
        print(f"  {d:<12} {dom[d][0]}/{dom[d][1]}")
    tot = sum(v[0] for v in dom.values()), sum(v[1] for v in dom.values())
    print(f"  {'TOTAL':<12} {tot[0]}/{tot[1]}")
    print(f"graded -> {gp}")


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "setup":
        setup()
    elif a == "run":
        run(sys.argv[2], sys.argv[3])
    else:
        grade(sys.argv[2])
