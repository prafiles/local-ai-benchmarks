#!/usr/bin/env python3
"""Deterministic filler for the long-context sessions.

Two rules the filler has to obey, or the whole suite measures nothing:

  1. It must look like the category it pads.  A Python session padded with
     lorem ipsum is a needle test; padded with more Python it is a long-context
     test, because the model has to tell the planted convention apart from two
     hundred plausible neighbours.
  2. It must carry distractors -- near-misses for the planted fact.  Without
     them a model can score by pattern-matching the only Result-shaped thing in
     the window instead of by remembering which one we said to use.

Everything here is seeded; no wall-clock, no unseeded random, so two builds of
the suite are byte-identical and runs stay comparable.
"""
import random

VERBS = ["collect", "reconcile", "flush", "compact", "resolve", "hydrate", "prune",
         "annotate", "dispatch", "settle", "rebalance", "verify", "expire", "index"]
NOUNS = ["ledger", "shard", "manifest", "envelope", "digest", "checkpoint", "lease",
         "quota", "backlog", "snapshot", "cursor", "receipt", "tranche", "beacon"]
SVCS = ["ingest", "billing", "notify", "search", "gateway", "scheduler", "audit",
        "registry", "relay", "vault"]


def rng(seed):
    return random.Random(seed)


def name(r):
    return f"{r.choice(VERBS)}_{r.choice(NOUNS)}"


# --------------------------------------------------------------- Python
# Distractor: several modules define their own *Outcome*/*Reply* records with
# ok/value/err-ish fields but different names, so "return the record type this
# repo uses" cannot be answered by shape-matching alone.
def py_module(i):
    r = rng(1000 + i)
    svc = SVCS[i % len(SVCS)]
    fns = []
    for k in range(r.randint(3, 5)):
        fn = name(r)
        fns.append(f'''

def {fn}_{k}(records, *, limit={r.randint(10, 500)}, strict={r.choice(["True", "False"])}):
    """{fn.replace('_', ' ').capitalize()} for the {svc} service.

    Called from aerelith.{svc}.pipeline during the {r.choice(["nightly", "hourly", "on-demand"])} pass.
    """
    seen = set()
    out = []
    for rec in records[:limit]:
        key = (rec.get("tenant_id"), rec.get("{r.choice(NOUNS)}_id"))
        if key in seen:
            continue
        seen.add(key)
        if strict and rec.get("state") not in ("ready", "settled"):
            continue
        out.append({{**rec, "pass_{k}": True}})
    return Result(ok=True, value=out, err=None)''')
    distract = ""
    if i % 7 == 3:
        distract = f'''

class {r.choice(["Outcome", "Reply", "Verdict", "Answer"])}(NamedTuple):
    """Legacy record used only inside aerelith.{svc}.legacy -- do not use in new code."""
    success: bool
    data: object
    reason: str
'''
    return (f"Next file: `aerelith/{svc}/{name(r)}.py`\n\n```python\n"
            f'"""{svc.capitalize()} helpers ({len(fns)} public functions)."""\n'
            f"from typing import NamedTuple\n\nfrom aerelith.core.result import Result\n"
            f"{distract}{''.join(fns)}\n```")


# --------------------------------------------------------------- Django
def dj_module(i):
    r = rng(2000 + i)
    svc = SVCS[i % len(SVCS)]
    body = []
    for k in range(r.randint(2, 4)):
        body.append(f'''

class {svc.capitalize()}{r.choice(["List", "Detail", "Bulk", "Export"])}View{k}(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request, *args, **kwargs):
        qs = Task.objects.filter(project__tenant=request.tenant)
        if request.query_params.get("state"):
            qs = qs.filter(state=request.query_params["state"])
        qs = qs.select_related("project").order_by("-created_at")[:{r.randint(20, 200)}]
        return Response([{{"id": t.id, "title": t.title}} for t in qs])''')
    return (f"Next file: `aerelith/{svc}/views.py`\n\n```python\n"
            "from rest_framework.views import APIView\nfrom rest_framework.response import Response\n"
            "from aerelith.core.perms import IsTenantMember\nfrom aerelith.work.models import Task\n"
            f"{''.join(body)}\n```")


# --------------------------------------------------------------- SQL
# Distractor: reporting views join near-identical column names (ticket.points vs
# worklog.points) so a model that half-remembers the schema picks the wrong one.
def sql_chunk(i):
    r = rng(3000 + i)
    v = f"vw_{name(r)}_{i}"
    return (f"Next reporting view: `{v}`\n\n```sql\n"
            f"CREATE VIEW {v} AS\n"
            f"SELECT t.tenant_id,\n       s.name AS sprint_name,\n"
            f"       COUNT(DISTINCT tk.id) AS ticket_count,\n"
            f"       SUM(w.minutes) AS logged_minutes,\n"
            f"       AVG(tk.points) AS avg_points\n"
            f"FROM tenant t\n"
            f"JOIN sprint s ON s.tenant_id = t.id\n"
            f"JOIN ticket tk ON tk.sprint_id = s.id\n"
            f"LEFT JOIN worklog w ON w.ticket_id = tk.id\n"
            f"WHERE tk.state IN ('{r.choice(['open', 'closed', 'blocked'])}', 'review')\n"
            f"GROUP BY t.tenant_id, s.name\nHAVING SUM(w.minutes) > {r.randint(60, 4000)};\n```")


# --------------------------------------------------------------- JS / TS
def js_module(i):
    r = rng(4000 + i)
    fns = []
    for k in range(r.randint(3, 5)):
        fn = name(r).replace("_", "")
        fns.append(f'''
function {fn}{k}(items, opts) {{
  const max = (opts && opts.max) || {r.randint(8, 400)};
  const seen = new Set();
  const out = [];
  for (const it of items) {{
    if (seen.has(it.id)) continue;
    seen.add(it.id);
    if (out.length >= max) break;
    out.push({{ ...it, tier: "{r.choice(['gold', 'silver', 'bronze'])}" }});
  }}
  return out;
}}''')
    names = [f"{name(rng(4000 + i))}".replace("_", "") + str(k) for k in range(len(fns))]
    return (f"Next file: `web/src/lib/{name(r)}.js`\n\n```javascript\n"
            f"'use strict';\nconst {{ clampInt }} = require('./aerutil');\n"
            f"{''.join(fns)}\n\nmodule.exports = {{ {', '.join(names)} }};\n```")


def ts_module(i):
    r = rng(5000 + i)
    return (f"Next file: `web/src/lib/{name(r)}.ts`\n\n```typescript\n"
            f"import type {{ Result }} from './result';\n\n"
            f"export interface {r.choice(NOUNS).capitalize()}{i} {{\n"
            f"  id: string;\n  tenantId: string;\n  weight: number;\n"
            f"  labels: readonly string[];\n}}\n\n"
            f"export function {name(r).replace('_', '')}{i}<T extends {{ id: string }}>(\n"
            f"  rows: readonly T[],\n  pick: (row: T) => number,\n"
            f"): Result<T[]> {{\n"
            f"  if (rows.length === 0) return {{ ok: false, error: 'empty' }};\n"
            f"  const sorted = [...rows].sort((a, b) => pick(b) - pick(a));\n"
            f"  return {{ ok: true, value: sorted.slice(0, {r.randint(3, 90)}) }};\n}}\n```")


# --------------------------------------------------------------- shell / git
def sh_script(i):
    r = rng(6000 + i)
    return (f"Next file: `ops/bin/{name(r)}.sh`\n\n```bash\n#!/usr/bin/env bash\n"
            f"set -euo pipefail\n\n: \"${{AER_LOG_DIR:?}}\"\n"
            f"src=${{1:-/srv/aerelith/{r.choice(SVCS)}}}\n"
            f"keep={r.randint(3, 40)}\n\n"
            f"find \"$src\" -type f -name '*.{r.choice(['jsonl', 'ndjson', 'log'])}' -mtime +$keep -print0 |\n"
            f"  xargs -0 -r gzip -9\n\n"
            f"ops/bin/aerlog info \"{name(r)} finished for $src\"\n```")


def git_chunk(i):
    r = rng(7000 + i)
    lines = []
    for k in range(r.randint(4, 8)):
        sha = "".join(r.choice("0123456789abcdef") for _ in range(7))
        lines.append(f"{sha} {r.choice(['feat', 'fix', 'chore', 'refactor'])}"
                     f"({r.choice(SVCS)}): {name(r).replace('_', ' ')}")
    return ("Recent history on a topic branch:\n\n```\n$ git log --oneline -"
            f"{len(lines)}\n" + "\n".join(lines) + "\n```")


def ssh_chunk(i):
    r = rng(8000 + i)
    h = f"{r.choice(SVCS)}-{r.randint(1, 40):02d}"
    return (f"Another inventory entry:\n\n```\nHost {h}\n"
            f"    HostName {h}.{r.choice(['eu-west', 'us-east', 'ap-south'])}.aerelith.internal\n"
            f"    User svc-{r.choice(SVCS)}\n    Port {r.choice([22, 22, 22, 2200])}\n"
            f"    IdentityFile ~/.ssh/svc_{r.choice(SVCS)}_ed25519\n"
            f"    ServerAliveInterval {r.randint(15, 90)}\n```")


def gh_chunk(i):
    r = rng(9000 + i)
    return (f"Another workflow: `.github/workflows/{name(r)}.yml`\n\n```yaml\n"
            f"name: {name(r).replace('_', ' ')}\non:\n  schedule:\n"
            f"    - cron: '{r.randint(0, 59)} {r.randint(0, 23)} * * *'\n"
            f"jobs:\n  {name(r)}:\n    runs-on: aer-linux-x64\n"
            f"    timeout-minutes: {r.randint(5, 60)}\n    steps:\n"
            f"      - uses: actions/checkout@v4\n"
            f"      - run: ops/bin/{name(r)}.sh\n```")


def doc_chunk(i):
    r = rng(10000 + i)
    t = name(r).replace("_", " ").capitalize()
    return (f"### {t}\n\n"
            f"The {r.choice(SVCS)} service performs this step during the "
            f"{r.choice(['nightly', 'weekly', 'per-request'])} pass. It reads from the "
            f"{r.choice(NOUNS)} table and writes a {r.choice(NOUNS)} record for every tenant "
            f"whose quota exceeds {r.randint(100, 9000)} units. Operators can force a re-run "
            f"with `aerctl {name(r).replace('_', '-')} --tenant <id>`; the command is "
            f"idempotent and safe to repeat. Failures raise `AerError` with code "
            f"`E{r.randint(1000, 9999)}` and are retried {r.randint(2, 6)} times with "
            f"exponential backoff before the run is marked failed.\n")


def rn_chunk(i):
    r = rng(11000 + i)
    c = f"Aer{r.choice(NOUNS).capitalize()}{i}"
    return (f"Next component: `mobile/src/components/{c}.tsx`\n\n```tsx\n"
            f"import React from 'react';\nimport {{ View, Text }} from 'react-native';\n"
            f"import {{ useAerTheme }} from '../theme';\n\n"
            f"export function {c}({{ label, onPress }}: {{ label: string; onPress: () => void }}) {{\n"
            f"  const theme = useAerTheme();\n"
            f"  return (\n    <View style={{{{ padding: theme.space.{r.choice(['sm', 'md', 'lg'])} }}}}>\n"
            f"      <Text style={{{{ color: theme.color.{r.choice(['ink', 'muted', 'accent'])} }}}}>{{label}}</Text>\n"
            f"    </View>\n  );\n}}\n```")


ACKS = [
    "Indexed. Nothing there conflicts with what you've told me so far.",
    "Read it. Noted the naming and the call sites.",
    "Got it — added to my picture of the repo.",
    "Understood. That one is consistent with the earlier files.",
    "Noted. I'll keep using the conventions you established up front.",
    "Read and indexed.",
]


GENERATORS = {
    "Python": py_module, "Django": dj_module, "SQL": sql_chunk, "JS": js_module,
    "TS": ts_module, "Bash": sh_script, "Git": git_chunk, "SSH": ssh_chunk,
    "GitHub": gh_chunk, "Docs": doc_chunk, "ReactNative": rn_chunk, "RAG": doc_chunk,
}


def pad(category, start_idx, chars_needed):
    """Return ([(user, assistant), ...], next_idx) covering ~chars_needed."""
    gen = GENERATORS[category]
    turns = []
    n = 0
    i = start_idx
    while n < chars_needed:
        u = gen(i)
        a = ACKS[i % len(ACKS)]
        turns.append((u, a))
        n += len(u) + len(a)
        i += 1
    return turns, i
