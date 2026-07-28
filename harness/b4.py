#!/usr/bin/env python3
"""Long-context multi-turn benchmark: runner + grader.

    b4.py count
    b4.py run <model> <out.json> [deep|shallow|both]
    b4.py oracle [out.json]
    b4.py grade <out.json>

Every probe is asked twice: once at its target depth inside a ~120K-token
session (`deep`), and once with only the convention-setting turns in front of it
(`shallow`). The shallow run is the control -- it separates "the model can't do
this task" from "the model couldn't reach the fact any more". Without it a low
deep score is unattributable.
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

import b4_ctx as C1     # noqa: E402
import b4_ctx2 as C2    # noqa: E402
import b4_gen as GEN    # noqa: E402

URL = "http://localhost:8000/v1/chat/completions"
TMP = "/root/bench2/tmp/b4"
CPT = 3.4               # nominal chars per token

# Per-category correction, measured against the served tokenizer. The generators
# differ in density -- one flat constant landed the deepest probe anywhere from
# 104K (Docs) to 152K (Bash), and 152K is a hard reject against a 131K window.
# These factors put every category's deepest probe within a few percent of its
# target, which is what makes a cross-category comparison mean anything.
SCALE = {"Python": 1.122, "Django": 1.193, "SQL": 0.960, "JS": 0.907, "TS": 0.911,
         "Bash": 0.817, "Git": 0.879, "SSH": 0.897, "GitHub": 0.880, "Docs": 1.183,
         "ReactNative": 1.000, "RAG": 1.183}

SESSIONS = dict(C1.PART1)
SESSIONS.update(C2.PART2)
ORDER = ["Python", "Django", "SQL", "JS", "TS", "Bash", "Git", "SSH", "GitHub",
         "Docs", "ReactNative", "RAG"]


def probes():
    for cat in ORDER:
        for p in SESSIONS[cat]["probes"]:
            yield cat, p


# ------------------------------------------------------------------ sessions
def build_deep(cat, scale=1.0):
    """[(messages, probe)] -- one entry per probe, sharing a growing prefix.

    `scale` trims the padding for models whose tokenizer runs hotter than the one
    SCALE was calibrated on. Same text, same conventions, same distractors -- just
    less filler, so the probe lands inside the model's window instead of being
    rejected outright.
    """
    s = SESSIONS[cat]
    msgs, out = [], []
    for u, a in s["intro"]:
        msgs.append({"role": "user", "content": u})
        msgs.append({"role": "assistant", "content": a})
    chars = sum(len(m["content"]) for m in msgs)
    idx = 0
    for p in s["probes"]:
        need = int(p["depth"] * CPT * SCALE[cat] * scale) - chars
        if need > 0:
            turns, idx = GEN.pad(cat, idx, need)
            for u, a in turns:
                msgs.append({"role": "user", "content": u})
                msgs.append({"role": "assistant", "content": a})
                chars += len(u) + len(a)
        ask = msgs + [{"role": "user", "content": p["prompt"]}]
        out.append((ask, p))
        # the *reference* answer goes into the history, not the model's -- every
        # model then sees identical context and no early slip can cascade
        msgs.append({"role": "user", "content": p["prompt"]})
        msgs.append({"role": "assistant", "content": p["ref"]})
        chars += len(p["prompt"]) + len(p["ref"])
    return out


def build_shallow(cat):
    """The same conversation with the filler removed -- and nothing else removed.

    The first cut of this dropped the earlier probe/reference exchanges too, which
    made the control useless: those references are few-shot demonstrations of the
    house style, so the deep run had up to four worked examples the shallow run
    lacked. Deep then outscored shallow, which is not a thing distance can do.
    Keeping them means deep and shallow differ by exactly one variable: padding.
    """
    s = SESSIONS[cat]
    msgs = []
    for u, a in s["intro"]:
        msgs.append({"role": "user", "content": u})
        msgs.append({"role": "assistant", "content": a})
    out = []
    for p in s["probes"]:
        out.append((msgs + [{"role": "user", "content": p["prompt"]}], p))
        msgs = msgs + [{"role": "user", "content": p["prompt"]},
                       {"role": "assistant", "content": p["ref"]}]
    return out



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
def ask(model, msgs, max_tokens):
    payload = sampling({"model": model, "messages": msgs,
                        "max_tokens": budget(max_tokens)}, model)
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=3600) as r:
        d = json.loads(r.read())
    ch = d["choices"][0]
    msg = ch["message"]
    think = msg.get("reasoning") or msg.get("reasoning_content") or ""
    return {"text": msg.get("content") or "",
            "tok": d["usage"]["completion_tokens"],
            "ptok": d["usage"]["prompt_tokens"],
            "think_chars": len(think),
            "finish": ch.get("finish_reason", ""),
            "secs": round(time.time() - t0, 2)}


def run(model, out_path, mode="both"):
    res = {"model": model, "deep": {}, "shallow": {}}
    plan = []
    for cat in ORDER:
        if mode in ("both", "deep"):
            plan += [("deep", cat, m, p) for m, p in build_deep(cat)]
        if mode in ("both", "shallow"):
            plan += [("shallow", cat, m, p) for m, p in build_shallow(cat)]
    t0 = time.time()
    for i, (bucket, cat, msgs, p) in enumerate(plan, 1):
        try:
            r = ask(model, msgs, p["max_tokens"])
        except Exception as e:  # noqa: BLE001
            r = {"text": "", "tok": 0, "ptok": 0, "secs": 0, "finish": "error",
                 "error": f"{type(e).__name__}: {str(e)[:200]}"}
        r["cat"] = cat
        res[bucket][p["id"]] = r
        el = time.time() - t0
        print(f"  {i}/{len(plan)} {bucket:<7} {p['id']:<10} "
              f"ptok={r.get('ptok', 0):>6} {r['secs']:>6.1f}s  "
              f"[{el/60:.1f}m elapsed, ~{el/i*(len(plan)-i)/60:.0f}m left]", flush=True)
        with open(out_path, "w") as f:
            json.dump(res, f)
    print(f"saved -> {out_path}")


# ------------------------------------------------------------------ helpers
FENCE = re.compile(r"```[a-zA-Z]*\s*\n(.*?)```", re.S)


def strip_think(t):
    return re.sub(r"<think>.*?</think>", "", t, flags=re.S)


def code_of(t):
    m = FENCE.search(strip_think(t))
    return m.group(1) if m else strip_think(t)


def cmd_of(t):
    for line in code_of(t).strip().splitlines():
        s = line.strip()
        if s and not s.startswith("#") and not s.startswith("$"):
            return s
    return ""


def container(image, stage, script, timeout=5400, mem="2g"):
    open(os.path.join(stage, "_run.sh"), "w").write(script)
    p = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--memory", mem,
         "--pids-limit", "512", "-e", "HOME=/tmp", "-v", f"{stage}:/w", "-w", "/w",
         image, "sh", "/w/_run.sh"], capture_output=True, text=True, timeout=timeout)
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


def by_kind(kind):
    return [(cat, p) for cat, p in probes() if p["kind"] == kind]


# ------------------------------------------------------------------ graders
def g_pyx(items, tag):
    rows = by_kind("pyx")
    d = fresh("pyx" + tag)
    ids = []
    for _cat, p in rows:
        ids.append(p["id"])
        cd = os.path.join(d, "cases", p["id"])
        for rel, body in C1.PY_PKG.items():
            fp = os.path.join(cd, rel)
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            open(fp, "w").write(body)
        sol = code_of(items.get(p["id"], {}).get("text", ""))
        # the answer on its own, so source-inspecting tests can't match themselves
        open(os.path.join(cd, "sol.txt"), "w").write(sol)
        open(os.path.join(cd, "m.py"), "w").write(sol + "\n\n" + p["payload"])
    drv = ("import os, subprocess\n"
           "for tid in sorted(os.listdir('/w/cases')):\n"
           "    d='/w/cases/'+tid\n"
           "    r=subprocess.run(['python','m.py'],capture_output=True,text=True,"
           "timeout=60,cwd=d)\n"
           "    print(('OK ' if r.returncode==0 else 'BAD ')+tid)\n")
    open(os.path.join(d, "drv.py"), "w").write(drv)
    out, _e = container("bench-py:1", d, "python /w/drv.py\n")
    return parse_okbad(out, ids)


def g_djx(items, tag):
    rows = by_kind("djx")
    d = fresh("djx" + tag)
    os.makedirs(os.path.join(d, "bench_app"), exist_ok=True)
    open(os.path.join(d, "bench_app", "__init__.py"), "w").close()
    open(os.path.join(d, "bench_app", "models.py"), "w").write(C1.DJ_MODELS)
    open(os.path.join(d, "seed.py"), "w").write(C1.DJ_SEED)
    open(os.path.join(d, "h.py"), "w").write(C1.DJ_HARNESS)
    # The session tells the model these models live in `aerelith/work/models.py`,
    # so a correct answer may well open with `from aerelith.work.models import Task`.
    # Without this shim that import raises and the answer is graded wrong for a
    # reason the model had no way to avoid. The oracle never caught it because the
    # reference answers rely on the harness globals instead of importing.
    wk = os.path.join(d, "aerelith", "work")
    os.makedirs(wk, exist_ok=True)
    open(os.path.join(d, "aerelith", "__init__.py"), "w").close()
    open(os.path.join(wk, "__init__.py"), "w").close()
    open(os.path.join(wk, "models.py"), "w").write(
        "from bench_app.models import Tenant, Project, Task, Comment  # noqa: F401\n")
    ids = []
    for _cat, p in rows:
        ids.append(p["id"])
        cd = os.path.join(d, "cases", p["id"])
        os.makedirs(cd, exist_ok=True)
        open(os.path.join(cd, "sol.py"), "w").write(
            code_of(items.get(p["id"], {}).get("text", "")))
        open(os.path.join(cd, "test.py"), "w").write(p["payload"])
    drv = ("import os, subprocess\n"
           "for tid in sorted(os.listdir('/w/cases')):\n"
           "    e=dict(os.environ); e['CASE']='/w/cases/'+tid\n"
           "    r=subprocess.run(['python','/w/h.py'],capture_output=True,text=True,"
           "timeout=90,env=e,cwd='/w')\n"
           "    print(('OK ' if r.returncode==0 else 'BAD ')+tid)\n")
    open(os.path.join(d, "drv.py"), "w").write(drv)
    out, _e = container("bench-py:1", d, "cd /w && python /w/drv.py\n")
    return parse_okbad(out, ids)


def _sql_expected():
    exp = {}
    for _cat, p in by_kind("sqlx"):
        con = sqlite3.connect(":memory:")
        con.executescript(C1.SQL_SCHEMA)
        exp[p["id"]] = con.execute(p["ref"]).fetchall()
        con.close()
    return exp


def g_sqlx(items, _tag):
    exp = _sql_expected()
    res = {}
    for _cat, p in by_kind("sqlx"):
        sql = code_of(items.get(p["id"], {}).get("text", "")).strip().rstrip(";")
        ok = False
        if sql:
            con = sqlite3.connect(":memory:")
            try:
                con.executescript(C1.SQL_SCHEMA)
                rows = con.execute(sql).fetchall()

                def norm(rs):
                    return [tuple(round(v, 2) if isinstance(v, float) else v for v in r)
                            for r in rs]
                g, w = norm(rows), norm(exp[p["id"]])
                ok = g == w or (len(g) == len(w) and
                                all(a[:len(b)] == b for a, b in zip(g, w)))
            except Exception:  # noqa: BLE001
                ok = False
            finally:
                con.close()
        res[p["id"]] = ok
    return res


def g_jsx(items, tag):
    rows = by_kind("jsx")
    d = fresh("jsx" + tag)
    ids = []
    for _cat, p in rows:
        ids.append(p["id"])
        cd = os.path.join(d, "cases", p["id"])
        os.makedirs(cd, exist_ok=True)
        # no export-shape normaliser here: object-literal exports are a stated
        # rule of this session, so getting it wrong is a real failure
        open(os.path.join(cd, "sol.js"), "w").write(
            code_of(items.get(p["id"], {}).get("text", "")))
        open(os.path.join(cd, "aerutil.js"), "w").write(C1.JS_UTIL)
        open(os.path.join(cd, "t.js"), "w").write(p["payload"])
    script = ("for id in $(ls /w/cases); do\n"
              "  if (cd /w/cases/$id && timeout 30 node t.js >/dev/null 2>&1); "
              "then echo \"OK $id\"; else echo \"BAD $id\"; fi\ndone\n")
    out, _e = container("bench-node:1", d, script)
    return parse_okbad(out, ids)


def g_tsx(items, tag):
    rows = by_kind("tsx")
    d = fresh("tsx" + tag)
    ids = []
    for _cat, p in rows:
        ids.append(p["id"])
        cd = os.path.join(d, "cases", p["id"])
        os.makedirs(cd, exist_ok=True)
        open(os.path.join(cd, "sol.ts"), "w").write(
            code_of(items.get(p["id"], {}).get("text", "")))
        open(os.path.join(cd, "result.ts"), "w").write(C1.TS_RESULT)
        open(os.path.join(cd, "t.ts"), "w").write(p["payload"])
    script = ("for id in $(ls /w/cases); do\n"
              "  if (cd /w/cases/$id && timeout 90 tsc --strict --module commonjs "
              "--target es2020 --types node "
              "--typeRoots /usr/local/lib/node_modules/@types --outDir out "
              "sol.ts result.ts t.ts >/dev/null 2>&1 && "
              "timeout 30 node out/t.js >/dev/null 2>&1); "
              "then echo \"OK $id\"; else echo \"BAD $id\"; fi\ndone\n")
    out, _e = container("bench-node:1", d, script, timeout=7200)
    return parse_okbad(out, ids)


def g_shellish(items, kind, tag):
    rows = by_kind(kind)
    d = fresh(kind + tag)
    ids = []
    for _cat, p in rows:
        ids.append(p["id"])
        open(os.path.join(d, p["id"] + ".setup"), "w").write(p["payload"]["setup"] + "\n")
        open(os.path.join(d, p["id"] + ".cmd"), "w").write(
            cmd_of(items.get(p["id"], {}).get("text", "")) + "\n")
        open(os.path.join(d, p["id"] + ".chk"), "w").write(p["payload"]["chk"] + "\n")
    open(os.path.join(d, "ids"), "w").write("\n".join(ids) + "\n")
    script = ("mkdir -p /tmp/outs\n"
              "AER_LOG_DIR=/srv/aer/log; export AER_LOG_DIR\n"
              "for id in $(cat /w/ids); do\n"
              "  rm -rf /tmp/b/$id /tmp/origin.git /tmp/mirror.git \"$AER_LOG_DIR\"\n"
              "  mkdir -p /tmp/b/$id \"$AER_LOG_DIR\"; cd /tmp/b/$id\n"
              "  sh /w/$id.setup >/dev/null 2>&1\n"
              "  OUT=/tmp/outs/$id; export OUT\n"
              "  timeout 30 sh /w/$id.cmd > \"$OUT\" 2>&1\n"
              "  cd /tmp/b/$id\n"
              "  if OUT=/tmp/outs/$id sh /w/$id.chk >/dev/null 2>&1; "
              "then echo \"OK $id\"; else echo \"BAD $id\"; fi\ndone\n")
    out, _e = container("bench-sh:1", d, script)
    return parse_okbad(out, ids)


def g_sshcfgx(items, tag):
    rows = by_kind("sshcfgx")
    d = fresh("sshcfgx" + tag)
    ids, specs, pats, raws = [], {}, {}, {}
    for _cat, p in rows:
        ids.append(p["id"])
        specs[p["id"]] = p["payload"]["spec"]
        pats[p["id"]] = p["payload"].get("pats", [])
        cfg = code_of(items.get(p["id"], {}).get("text", ""))
        raws[p["id"]] = cfg
        open(os.path.join(d, p["id"] + ".cfg"), "w").write(cfg)
        open(os.path.join(d, p["id"] + ".alias"), "w").write(p["payload"]["alias"] + "\n")
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
            q = ln.strip().split(None, 1)
            if len(q) == 2:
                blocks[cur].setdefault(q[0], q[1])
    equiv = {"no": {"no", "false"}, "yes": {"yes", "true"},
             "false": {"no", "false"}, "true": {"yes", "true"}}

    def m(got, want):
        want = want.lower()
        return got in equiv.get(want, {want})

    res = {}
    for tid in ids:
        got = blocks.get(tid, {})
        ok = bool(got) and all(m(got.get(k, ""), v) for k, v in specs[tid].items())
        ok = ok and all(re.search(pt, raws[tid], re.I) for pt in pats[tid])
        res[tid] = ok
    return res


def g_yamlx(items, tag):
    rows = by_kind("yamlx")
    d = fresh("yamlx" + tag)
    ids = []
    for _cat, p in rows:
        ids.append(p["id"])
        cd = os.path.join(d, "cases", p["id"])
        os.makedirs(cd, exist_ok=True)
        open(os.path.join(cd, "w.yml"), "w").write(
            code_of(items.get(p["id"], {}).get("text", "")))
        body = ("import yaml, json\n"
                "d=yaml.safe_load(open('w.yml'))\n"
                "on=d.get('on', d.get(True))\n"
                "s=json.dumps(on)\n"
                "j=list(d['jobs'].values())[0]\n"
                "st=json.dumps(d['jobs'])\n"
                "st_all=json.dumps(d)\n" + p["payload"] + "\nprint('ok')\n")
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


def g_rubricx(items, _tag):
    res = {}
    for _cat, p in by_kind("rubricx"):
        body = strip_think(items.get(p["id"], {}).get("text", ""))
        ok = bool(body.strip())
        ok = ok and all(re.search(x, body, re.I | re.M) for x in p["payload"]["must"])
        ok = ok and not any(re.search(x, body, re.I) for x in p["payload"]["must_not"])
        res[p["id"]] = ok
    return res


def g_ragx(items, _tag):
    res = {}
    for _cat, p in by_kind("ragx"):
        body = strip_think(items.get(p["id"], {}).get("text", ""))
        if p["payload"]["unanswerable"]:
            res[p["id"]] = any(re.search(x, body, re.I) for x in C2.REFUSAL)
        else:
            res[p["id"]] = bool(body.strip()) and all(
                re.search(x, body, re.I) for x in p["payload"]["must"])
    return res


GRADERS = [("pyx", g_pyx), ("djx", g_djx), ("sqlx", g_sqlx), ("jsx", g_jsx),
           ("tsx", g_tsx), ("shx", lambda i, t: g_shellish(i, "shx", t)),
           ("gitx", lambda i, t: g_shellish(i, "gitx", t)), ("sshcfgx", g_sshcfgx),
           ("yamlx", g_yamlx), ("rubricx", g_rubricx), ("ragx", g_ragx)]


def grade_bucket(items, tag):
    ok = {}
    for nm, fn in GRADERS:
        print(f"    {tag} {nm} ...", flush=True)
        ok.update(fn(items, tag))
    return ok


def grade(path):
    data = json.load(open(path))
    out = {"model": data["model"], "results": {}}
    deep_ok = grade_bucket(data.get("deep", {}), "deep")
    shal_ok = grade_bucket(data.get("shallow", {}), "shal")
    for cat, p in probes():
        dd = data.get("deep", {}).get(p["id"], {})
        ss = data.get("shallow", {}).get(p["id"], {})
        out["results"][p["id"]] = {
            "cat": cat, "depth": p["depth"],
            "deep": bool(deep_ok.get(p["id"], False)),
            "shallow": bool(shal_ok.get(p["id"], False)),
            "deep_ptok": dd.get("ptok", 0), "deep_secs": dd.get("secs", 0),
            "deep_tok": dd.get("tok", 0), "deep_finish": dd.get("finish", ""),
            "shal_ptok": ss.get("ptok", 0), "shal_tok": ss.get("tok", 0),
            "shal_secs": ss.get("secs", 0)}
    gp = path.replace(".json", ".graded.json")
    json.dump(out, open(gp, "w"), indent=1)

    print(f"\n===== {data['model']}")
    print(f"  {'category':<13} {'deep':>6} {'shallow':>8}")
    dom = {}
    for r in out["results"].values():
        e = dom.setdefault(r["cat"], [0, 0, 0])
        e[2] += 1
        e[0] += r["deep"]
        e[1] += r["shallow"]
    for c in ORDER:
        e = dom[c]
        print(f"  {c:<13} {e[0]:>3}/{e[2]}   {e[1]:>3}/{e[2]}")
    td = sum(e[0] for e in dom.values())
    ts = sum(e[1] for e in dom.values())
    tn = sum(e[2] for e in dom.values())
    print(f"  {'TOTAL':<13} {td:>3}/{tn}   {ts:>3}/{tn}")
    print("\n  by depth:")
    for depth in C1.DEPTHS:
        rs = [r for r in out["results"].values() if r["depth"] == depth]
        pt = [r["deep_ptok"] for r in rs if r["deep_ptok"]]
        avg = sum(pt) // len(pt) if pt else 0
        print(f"   ~{depth//1000:>3}K (measured {avg:>6} tok): "
              f"deep {sum(r['deep'] for r in rs):>2}/{len(rs)}   "
              f"shallow {sum(r['shallow'] for r in rs):>2}/{len(rs)}")
    print(f"graded -> {gp}")


def oracle(path):
    items = {}
    for _cat, p in probes():
        items[p["id"]] = {"text": p["ref"], "tok": 0, "ptok": 0, "secs": 0,
                          "finish": "stop"}
    json.dump({"model": "ORACLE(reference)", "deep": items,
               "shallow": dict(items)}, open(path, "w"))
    print(f"oracle written: {len(items)} items -> {path}")


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "count":
        n = 0
        from collections import Counter
        cc, kk = Counter(), Counter()
        ids = []
        for cat, p in probes():
            n += 1
            cc[cat] += 1
            kk[p["kind"]] += 1
            ids.append(p["id"])
        assert len(ids) == len(set(ids)), "DUPLICATE IDS"
        print(f"probes {n} (x2 = {n*2} generations per model)")
        for c in ORDER:
            print(f"  {c:<13} {cc[c]}")
        print("kinds:", dict(kk))
        for cat in ORDER:
            built = build_deep(cat)
            est = [len(json.dumps(m)) // 1000 for m, _ in built]
            print(f"  {cat:<13} chars/1000 at each probe: {est}")
    elif a == "run":
        os.makedirs(TMP, exist_ok=True)
        run(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "both")
    elif a == "fix":
        # Re-run only the deep probes the server REJECTED, with trimmed padding.
        # Use this when a model's tokenizer overshoots the window on identical
        # text -- not when the model's window is simply too small for the rung,
        # where shrinking the prompt would silently answer a different question.
        os.makedirs(TMP, exist_ok=True)
        model, path, sc = sys.argv[2], sys.argv[3], float(sys.argv[4])
        data = json.load(open(path))
        bad = {k for k, v in data["deep"].items() if v.get("finish") == "error"}
        print(f"rejected probes to redo at scale {sc}: {sorted(bad)}")
        for cat in ORDER:
            ids = {p["id"] for p in SESSIONS[cat]["probes"]}
            if not (bad & ids):
                continue
            for msgs, p in build_deep(cat, scale=sc):
                if p["id"] not in bad:
                    continue
                try:
                    r = ask(model, msgs, p["max_tokens"])
                except Exception as e:  # noqa: BLE001
                    r = {"text": "", "tok": 0, "ptok": 0, "secs": 0, "finish": "error",
                         "error": f"{type(e).__name__}: {str(e)[:200]}"}
                r["cat"] = cat
                r["retried_scale"] = sc
                data["deep"][p["id"]] = r
                print(f"  {p['id']:<10} ptok={r.get('ptok', 0):>6} "
                      f"finish={r['finish']}", flush=True)
        json.dump(data, open(path, "w"))
        still = [k for k, v in data["deep"].items() if v.get("finish") == "error"]
        print(f"still rejected: {still}")
    elif a == "oracle":
        oracle(sys.argv[2] if len(sys.argv) > 2 else "/root/bench2/b4_oracle.json")
    else:
        os.makedirs(TMP, exist_ok=True)
        grade(sys.argv[2])
