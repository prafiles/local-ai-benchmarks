#!/usr/bin/env python3
"""Long-context multi-turn sessions, part 1: Python / Django / SQL / JS / TS.

Each session is ONE conversation that grows to ~120K tokens. Conventions are
planted in the opening turns; graded asks are interleaved at increasing depth.
A task is only counted as a long-context task if it CANNOT be answered without
the planted facts -- so every probe below is graded on something that was stated
up front and never repeated.

The assistant turns after each probe are the *reference* answers, not whatever
the model said. Every model therefore sees a byte-identical history, and one
early mistake cannot cascade into the rest of the session. That costs realism
and buys comparability, which is the trade this benchmark wants.
"""

DEPTHS = [10_000, 35_000, 65_000, 95_000, 112_000]


def P(pid, depth, prompt, mt, kind, payload, ref):
    return {"id": pid, "depth": depth, "prompt": prompt, "max_tokens": mt,
            "kind": kind, "payload": payload, "ref": ref}


# =========================================================== Python
AER_RESULT = '''from typing import NamedTuple, Optional


class Result(NamedTuple):
    """The one record type every public function in this repo returns."""
    ok: bool
    value: object
    err: Optional[str]
'''

AER_ITERS = '''def chunked(seq, n):
    """Yield successive n-sized lists from seq. Raises ValueError if n < 1."""
    if n < 1:
        raise ValueError("n must be >= 1")
    buf = []
    for x in seq:
        buf.append(x)
        if len(buf) == n:
            yield buf
            buf = []
    if buf:
        yield buf
'''

PY_INTRO = [
    ("We're pairing on the `aerelith` monorepo for the rest of this session. "
     "Start by reading the core result type — every public function in the repo "
     "returns this, no exceptions.\n\n`aerelith/core/result.py`\n\n```python\n"
     + AER_RESULT + "```",
     "Read. `Result` is a NamedTuple with fields `(ok, value, err)` in that order."),

    ("And the batching helper. This is the only approved way to batch anything; "
     "importing `itertools` is blocked by our lint rules.\n\n"
     "`aerelith/core/iters.py`\n\n```python\n" + AER_ITERS + "```",
     "Got it — `chunked(seq, n)` from `aerelith.core.iters`, and no `itertools`."),

    ("House rules for this codebase, so I don't have to repeat them:\n\n"
     "1. Every public function returns a `Result`. Never a bare value, never a tuple.\n"
     "2. Expected failures are NOT exceptions. Return "
     "`Result(ok=False, value=None, err=<CODE>)`.\n"
     "3. The error code vocabulary is closed. Exactly four codes exist:\n"
     "   - `E_EMPTY`  — the input had nothing to work on\n"
     "   - `E_RANGE`  — a numeric argument was outside its allowed range\n"
     "   - `E_CONFLICT` — two inputs disagreed and neither wins\n"
     "   - `E_STATE`  — the requested transition isn't legal from the current state\n"
     "4. Batching goes through `chunked`. Never `itertools`, never a manual slice loop.\n\n"
     "Confirm you have those and we'll start on the actual work.",
     "Confirmed. `Result(ok, value, err)`; no raising for expected failures; codes are "
     "exactly `E_EMPTY`, `E_RANGE`, `E_CONFLICT`, `E_STATE`; batching via `chunked`."),
]

PY_PKG = {"aerelith/__init__.py": "", "aerelith/core/__init__.py": "",
          "aerelith/core/result.py": AER_RESULT, "aerelith/core/iters.py": AER_ITERS}

PY_PROBES = [
    P("x-py-1", DEPTHS[0],
      "Write `top_by_weight(rows, k)`. `rows` is a list of dicts each having 'id' and "
      "'weight'. Return the k highest-weight rows, highest first. An empty `rows` is "
      "E_EMPTY; a k outside 1..len(rows) is E_RANGE. Output only the code.", 500, "pyx",
      "r = top_by_weight([{'id':'a','weight':3},{'id':'b','weight':9},{'id':'c','weight':5}], 2)\n"
      "assert r.ok is True and r.err is None, r\n"
      "assert r._fields == ('ok','value','err'), r._fields\n"
      "assert [x['id'] for x in r.value] == ['b','c'], r.value\n"
      "r = top_by_weight([], 2)\n"
      "assert r.ok is False and r.value is None and r.err == 'E_EMPTY', r\n"
      "r = top_by_weight([{'id':'a','weight':1}], 0)\n"
      "assert r.ok is False and r.err == 'E_RANGE', r\n"
      "r = top_by_weight([{'id':'a','weight':1}], 5)\n"
      "assert r.ok is False and r.err == 'E_RANGE', r\n",
      "from aerelith.core.result import Result\n\n"
      "def top_by_weight(rows, k):\n"
      "    if not rows:\n        return Result(ok=False, value=None, err='E_EMPTY')\n"
      "    if k < 1 or k > len(rows):\n        return Result(ok=False, value=None, err='E_RANGE')\n"
      "    ordered = sorted(rows, key=lambda r: r['weight'], reverse=True)\n"
      "    return Result(ok=True, value=ordered[:k], err=None)\n"),

    P("x-py-2", DEPTHS[1],
      "Write `batch_apply(rows, n, fn)`. Split `rows` into batches of n, call `fn` on each "
      "batch (it returns a list), and return the concatenation. n < 1 is E_RANGE. "
      "Use the repo's approved batching helper. Output only the code.", 500, "pyx",
      # sol.txt is the answer ONLY -- reading __file__ here would match the
      # assertion literals below and pass no matter what the model wrote
      "src = open('sol.txt').read()\n"
      "assert 'chunked' in src, 'must use the approved batching helper'\n"
      "assert 'aerelith.core.iters' in src, 'must import chunked from aerelith.core.iters'\n"
      "assert 'itertools' not in src, 'itertools is banned by the repo lint rules'\n"
      "r = batch_apply([1,2,3,4,5], 2, lambda b: [x*10 for x in b])\n"
      "assert r.ok is True and r.value == [10,20,30,40,50], r\n"
      "assert r._fields == ('ok','value','err'), r._fields\n"
      "r = batch_apply([1,2], 0, lambda b: b)\n"
      "assert r.ok is False and r.value is None and r.err == 'E_RANGE', r\n",
      "from aerelith.core.iters import chunked\nfrom aerelith.core.result import Result\n\n"
      "def batch_apply(rows, n, fn):\n"
      "    if n < 1:\n        return Result(ok=False, value=None, err='E_RANGE')\n"
      "    out = []\n    for batch in chunked(rows, n):\n        out.extend(fn(batch))\n"
      "    return Result(ok=True, value=out, err=None)\n"),

    P("x-py-3", DEPTHS[2],
      "Write `merge_quota(a, b)`. Both are dicts mapping tenant id to an int quota. Return "
      "the merged dict. If a tenant is in both with the SAME value that's fine; with "
      "different values neither wins. Both dicts empty is E_EMPTY. Output only the code.",
      500, "pyx",
      "r = merge_quota({'t1':5,'t2':7}, {'t2':7,'t3':9})\n"
      "assert r.ok is True and r.value == {'t1':5,'t2':7,'t3':9}, r\n"
      "assert r._fields == ('ok','value','err'), r._fields\n"
      "r = merge_quota({'t1':5}, {'t1':6})\n"
      "assert r.ok is False and r.value is None and r.err == 'E_CONFLICT', r\n"
      "r = merge_quota({}, {})\n"
      "assert r.ok is False and r.err == 'E_EMPTY', r\n",
      "from aerelith.core.result import Result\n\n"
      "def merge_quota(a, b):\n"
      "    if not a and not b:\n        return Result(ok=False, value=None, err='E_EMPTY')\n"
      "    out = dict(a)\n    for k, v in b.items():\n"
      "        if k in out and out[k] != v:\n"
      "            return Result(ok=False, value=None, err='E_CONFLICT')\n"
      "        out[k] = v\n    return Result(ok=True, value=out, err=None)\n"),

    P("x-py-4", DEPTHS[3],
      "Write `advance(task, to_state)`. `task` is a dict with a 'state' key. The only legal "
      "transitions are open->review, review->closed, and anything->blocked. Return a NEW dict "
      "with the updated state — do not mutate the argument. An illegal transition is E_STATE. "
      "Output only the code.", 500, "pyx",
      "t = {'id':'k1','state':'open'}\n"
      "r = advance(t, 'review')\n"
      "assert r.ok is True and r.value['state'] == 'review', r\n"
      "assert r._fields == ('ok','value','err'), r._fields\n"
      "assert t['state'] == 'open', 'must not mutate the input'\n"
      "assert advance({'id':'k','state':'review'}, 'closed').ok is True\n"
      "assert advance({'id':'k','state':'open'}, 'blocked').value['state'] == 'blocked'\n"
      "r = advance({'id':'k','state':'closed'}, 'open')\n"
      "assert r.ok is False and r.err == 'E_STATE', r\n"
      "r = advance({'id':'k','state':'open'}, 'closed')\n"
      "assert r.ok is False and r.err == 'E_STATE', r\n",
      "from aerelith.core.result import Result\n\n"
      "LEGAL = {('open','review'), ('review','closed')}\n\n"
      "def advance(task, to_state):\n"
      "    cur = task['state']\n"
      "    if to_state != 'blocked' and (cur, to_state) not in LEGAL:\n"
      "        return Result(ok=False, value=None, err='E_STATE')\n"
      "    updated = dict(task)\n    updated['state'] = to_state\n"
      "    return Result(ok=True, value=updated, err=None)\n"),

    P("x-py-5", DEPTHS[4],
      "Write `parse_window(spec)`. `spec` is a string like '7d', '12h' or '30m'. Return the "
      "window length in whole minutes as an int. An empty string is E_EMPTY; an unknown unit "
      "or a number that is not strictly positive is E_RANGE. Output only the code.", 500, "pyx",
      "assert parse_window('7d').value == 10080, parse_window('7d')\n"
      "assert parse_window('12h').value == 720, parse_window('12h')\n"
      "assert parse_window('30m').value == 30, parse_window('30m')\n"
      "assert parse_window('7d')._fields == ('ok','value','err')\n"
      "assert parse_window('7d').ok is True and parse_window('7d').err is None\n"
      "r = parse_window('')\nassert r.ok is False and r.value is None and r.err == 'E_EMPTY', r\n"
      "r = parse_window('5y')\nassert r.ok is False and r.err == 'E_RANGE', r\n"
      "r = parse_window('0h')\nassert r.ok is False and r.err == 'E_RANGE', r\n",
      "from aerelith.core.result import Result\n\n"
      "UNITS = {'d': 1440, 'h': 60, 'm': 1}\n\n"
      "def parse_window(spec):\n"
      "    if not spec:\n        return Result(ok=False, value=None, err='E_EMPTY')\n"
      "    unit = spec[-1]\n    head = spec[:-1]\n"
      "    if unit not in UNITS or not head.isdigit():\n"
      "        return Result(ok=False, value=None, err='E_RANGE')\n"
      "    n = int(head)\n"
      "    if n <= 0:\n        return Result(ok=False, value=None, err='E_RANGE')\n"
      "    return Result(ok=True, value=n * UNITS[unit], err=None)\n"),
]


# =========================================================== Django
DJ_MODELS = '''from django.db import models


class Tenant(models.Model):
    name = models.CharField(max_length=80)
    plan = models.CharField(max_length=20)          # free | pro


class Project(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=80)
    archived = models.BooleanField(default=False)


class Task(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=120)
    state = models.CharField(max_length=20)         # open | review | closed | blocked
    points = models.IntegerField(default=0)
    assignee = models.CharField(max_length=40, blank=True)


class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    body = models.TextField()
    author = models.CharField(max_length=40)
'''

DJ_SEED = '''
acme = Tenant.objects.create(name='Acme', plan='pro')
bolt = Tenant.objects.create(name='Bolt', plan='free')
cusp = Tenant.objects.create(name='Cusp', plan='pro')
dyne = Tenant.objects.create(name='Dyne', plan='pro')      # no projects at all

p_a1 = Project.objects.create(tenant=acme, name='apollo', archived=False)
p_a2 = Project.objects.create(tenant=acme, name='atlas', archived=True)
p_b1 = Project.objects.create(tenant=bolt, name='beacon', archived=False)
p_c1 = Project.objects.create(tenant=cusp, name='cobalt', archived=False)
p_c2 = Project.objects.create(tenant=cusp, name='cedar', archived=False)   # no tasks

def T(proj, title, state, points, who):
    return Task.objects.create(project=proj, title=title, state=state,
                               points=points, assignee=who)

t1 = T(p_a1, 'apollo-open-1',   'open',    5, 'rhea')
t2 = T(p_a1, 'apollo-review-1', 'review',  8, 'rhea')
t3 = T(p_a1, 'apollo-closed-1', 'closed',  3, 'iven')
t4 = T(p_a2, 'atlas-open-1',    'open',   13, 'iven')
t5 = T(p_b1, 'beacon-open-1',   'open',    2, 'sora')
t6 = T(p_b1, 'beacon-blocked-1','blocked', 5, 'sora')
t7 = T(p_c1, 'cobalt-closed-1', 'closed', 21, 'rhea')
t8 = T(p_c1, 'cobalt-closed-2', 'closed',  1, 'tazz')
t9 = T(p_c1, 'cobalt-open-1',   'open',    8, '')

for tk, n in ((t1, 3), (t2, 1), (t7, 2)):
    for i in range(n):
        Comment.objects.create(task=tk, body='c%d' % i, author='rhea' if i else 'iven')
'''

DJ_HARNESS = '''
import django, datetime, os
from django.conf import settings
settings.configure(DEBUG=True, USE_TZ=True,
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    INSTALLED_APPS=["bench_app"], DEFAULT_AUTO_FIELD="django.db.models.BigAutoField")
django.setup()
from django.db import connection
from bench_app.models import Tenant, Project, Task, Comment
from django.db.models import (F, Q, Count, Sum, Avg, Max, Min, OuterRef, Subquery,
                              Exists, Value, Case, When, IntegerField, FloatField,
                              CharField, BooleanField, DecimalField)
from django.db.models.functions import Coalesce, Cast, Lower, Upper, Concat
with connection.schema_editor() as se:
    for m in (Tenant, Project, Task, Comment):
        se.create_model(m)
exec(open("/w/seed.py").read(), globals())
exec(open(os.environ["CASE"] + "/sol.py").read(), globals())
exec(open(os.environ["CASE"] + "/test.py").read(), globals())
print("OK")
'''

DJ_INTRO = [
    ("Different part of the same monorepo now — the Django service. Here are the only "
     "four models that exist. There is no `User` model and no `Sprint` model in this app; "
     "if you reach for one the code won't run.\n\n`aerelith/work/models.py`\n\n```python\n"
     + DJ_MODELS + "```",
     "Read. Tenant -> Project -> Task -> Comment, with `projects`, `tasks` and `comments` "
     "as the reverse accessors. `assignee` is a plain CharField, not a relation."),

    ("Query rules for this app, and they are not negotiable:\n\n"
     "1. Every function returns a QuerySet, never a list — the callers slice and paginate.\n"
     "2. Tenant scoping goes through the relation: `project__tenant`. There is no denormalised "
     "`tenant_id` on Task and adding one is out of scope.\n"
     "3. Archived projects are excluded from every aggregate unless the ask says otherwise.\n"
     "4. Anything that reads a related object in a loop must prefetch or select_related — "
     "an N+1 in review is an automatic reject.\n\n"
     "Ready?",
     "Ready. QuerySets only, scope with `project__tenant`, exclude `project__archived=True` "
     "from aggregates by default, and no N+1s."),
]

DJ_PROBES = [
    P("x-dj-1", DEPTHS[0],
      "Write `open_tasks_for(tenant_name)` returning the Tasks in state 'open' belonging to "
      "that tenant, ordered by title. Output only the code.", 450, "djx",
      "from django.db.models.query import QuerySet\n"
      "r = open_tasks_for('Acme')\n"
      "assert isinstance(r, QuerySet), type(r)\n"
      # The house rule says archived projects are excluded from every *aggregate*,
      # and this is a plain filter -- my wording, so both readings are accepted.
      # dj-2 and dj-5 are aggregates, where the rule is unambiguous and enforced.
      "assert [t.title for t in r] in (['apollo-open-1'], "
      "['apollo-open-1', 'atlas-open-1']), [t.title for t in r]\n"
      "assert [t.title for t in open_tasks_for('Cusp')] == ['cobalt-open-1']\n"
      "assert list(open_tasks_for('Dyne')) == []\n",
      "def open_tasks_for(tenant_name):\n"
      "    return Task.objects.filter(project__tenant__name=tenant_name, state='open',\n"
      "                               project__archived=False).order_by('title')\n"),

    P("x-dj-2", DEPTHS[1],
      "Write `points_by_tenant()` returning Tenants annotated with `total_points`, the sum of "
      "points across their tasks, ordered by total_points descending then name. Tenants with "
      "no tasks must still appear, with 0. Output only the code.", 450, "djx",
      "from django.db.models.query import QuerySet\n"
      "r = points_by_tenant()\nassert isinstance(r, QuerySet), type(r)\n"
      "got = [(t.name, t.total_points or 0) for t in r]\n"
      "assert got == [('Cusp',30),('Acme',16),('Bolt',7),('Dyne',0)], got\n",
      "from django.db.models import Sum\nfrom django.db.models.functions import Coalesce\n"
      "def points_by_tenant():\n"
      "    return Tenant.objects.annotate(\n"
      "        total_points=Coalesce(Sum('projects__tasks__points',\n"
      "                              filter=Q(projects__archived=False)), 0)\n"
      "    ).order_by('-total_points', 'name')\n"),

    P("x-dj-3", DEPTHS[2],
      "Write `tasks_with_comment_authors()` returning every Task such that iterating the "
      "result and touching `task.comments.all()` for each one does not fire a query per task. "
      "Order by id. Output only the code.", 450, "djx",
      "from django.test.utils import CaptureQueriesContext\nfrom django.db import connection\n"
      "from django.db.models.query import QuerySet\n"
      "r = tasks_with_comment_authors()\nassert isinstance(r, QuerySet), type(r)\n"
      "with CaptureQueriesContext(connection) as c:\n"
      "    n = 0\n"
      "    for t in tasks_with_comment_authors():\n"
      "        n += len([cm.author for cm in t.comments.all()])\n"
      "assert n == 6, n\n"
      "assert len(c.captured_queries) <= 2, len(c.captured_queries)\n",
      "def tasks_with_comment_authors():\n"
      "    return Task.objects.prefetch_related('comments').order_by('id')\n"),

    P("x-dj-4", DEPTHS[3],
      "Write `stalled_projects()` returning the non-archived Projects that have at least one "
      "task and none of whose tasks are in state 'closed', ordered by name. Output only the "
      "code.", 450, "djx",
      "from django.db.models.query import QuerySet\n"
      "r = stalled_projects()\nassert isinstance(r, QuerySet), type(r)\n"
      "assert [p.name for p in r] == ['beacon'], [p.name for p in r]\n",
      "def stalled_projects():\n"
      "    return Project.objects.filter(archived=False, tasks__isnull=False)\\\n"
      "        .exclude(tasks__state='closed').distinct().order_by('name')\n"),

    P("x-dj-5", DEPTHS[4],
      "Write `assignee_load(plan)` returning a QuerySet of dicts `{'assignee':..., "
      "'open_points':...}` — the total points of not-closed tasks per assignee, restricted to "
      "tenants on the given plan, excluding the empty assignee, ordered by open_points "
      "descending then assignee. Output only the code.", 450, "djx",
      "from django.db.models.query import QuerySet\n"
      "r = assignee_load('pro')\nassert isinstance(r, QuerySet), type(r)\n"
      "got = [(d['assignee'], d['open_points']) for d in r]\n"
      "assert got == [('rhea',13)], got\n"
      "got2 = [(d['assignee'], d['open_points']) for d in assignee_load('free')]\n"
      "assert got2 == [('sora',7)], got2\n",
      "from django.db.models import Sum\n"
      "def assignee_load(plan):\n"
      "    return (Task.objects\n"
      "            .filter(project__tenant__plan=plan, project__archived=False)\n"
      "            .exclude(state='closed').exclude(assignee='')\n"
      "            .values('assignee').annotate(open_points=Sum('points'))\n"
      "            .order_by('-open_points', 'assignee'))\n"),
]


# =========================================================== SQL
SQL_SCHEMA = """
CREATE TABLE tenant (id INTEGER PRIMARY KEY, name TEXT, plan TEXT);
CREATE TABLE sprint (id INTEGER PRIMARY KEY, tenant_id INTEGER, name TEXT, starts TEXT);
CREATE TABLE ticket (id INTEGER PRIMARY KEY, sprint_id INTEGER, title TEXT,
                     state TEXT, points INTEGER, assignee TEXT);
CREATE TABLE worklog (id INTEGER PRIMARY KEY, ticket_id INTEGER, minutes INTEGER,
                      logged_by TEXT);
CREATE TABLE ticket_tag (ticket_id INTEGER, tag TEXT);

INSERT INTO tenant VALUES (1,'Acme','pro'),(2,'Bolt','free'),(3,'Cusp','pro'),(4,'Dyne','pro');
INSERT INTO sprint VALUES
 (1,1,'2026-S1','2026-01-05'),(2,1,'2026-S2','2026-02-02'),
 (3,2,'2026-S1','2026-01-05'),(4,3,'2026-S1','2026-03-02'),
 (5,3,'2026-S2','2026-04-06');
INSERT INTO ticket VALUES
 (1,1,'apollo latch','closed',5,'rhea'),
 (2,1,'apollo drift','open',8,'rhea'),
 (3,1,'apollo seal','review',3,'iven'),
 (4,2,'atlas hoist','closed',13,'iven'),
 (5,2,'atlas tether','blocked',2,'rhea'),
 (6,3,'beacon ping','open',5,'sora'),
 (7,3,'beacon echo','closed',8,'sora'),
 (8,4,'cobalt vent','closed',21,'tazz'),
 (9,4,'cobalt shim','closed',1,'tazz');
INSERT INTO worklog VALUES
 (1,1,120,'rhea'),(2,1,45,'iven'),(3,2,300,'rhea'),
 (4,4,90,'iven'),(5,6,30,'sora'),(6,7,210,'sora'),
 (7,8,600,'tazz'),(8,9,15,'tazz');
INSERT INTO ticket_tag VALUES
 (1,'infra'),(2,'infra'),(2,'urgent'),(3,'docs'),(4,'infra'),
 (6,'urgent'),(7,'docs'),(8,'infra'),(8,'urgent');
"""

SQL_INTRO = [
    ("Switching to the reporting database. This is the whole schema plus the fixture rows "
     "the analysts use — there is no `users` table, no `epic` table, and `assignee` is a "
     "bare text column, not a foreign key.\n\n```sql\n" + SQL_SCHEMA + "```",
     "Read. Five tables: tenant, sprint, ticket, worklog, ticket_tag. `sprint` hangs off "
     "tenant, `ticket` off sprint, `worklog` off ticket, and `ticket_tag` is a plain join "
     "table with no surrogate key."),

    ("Rules for anything you hand me from here on:\n\n"
     "1. SQLite dialect. No window-function-free workarounds needed — SQLite here has them — "
     "but no CTE-only-in-Postgres syntax.\n"
     "2. One statement, no trailing semicolon needed, no explanatory prose.\n"
     "3. Column aliases exactly as the ask names them.\n"
     "4. `sprint 5` deliberately has zero tickets and tenant `Dyne` has zero sprints. Any "
     "query that claims to include empty groups has to actually include them.\n\n"
     "Understood?",
     "Understood — SQLite, single statement, exact aliases, and I'll use outer joins where "
     "empty groups have to survive."),
]

SQL_PROBES = [
    P("x-sql-1", DEPTHS[0],
      "Total logged minutes per tenant, for tenants on the 'pro' plan only. Return columns "
      "`name` and `total_minutes`, highest first. Tenants with no logged minutes are omitted.",
      350, "sqlx", None,
      "SELECT t.name AS name, SUM(w.minutes) AS total_minutes FROM tenant t "
      "JOIN sprint s ON s.tenant_id=t.id JOIN ticket tk ON tk.sprint_id=s.id "
      "JOIN worklog w ON w.ticket_id=tk.id WHERE t.plan='pro' "
      "GROUP BY t.name ORDER BY total_minutes DESC"),

    P("x-sql-2", DEPTHS[1],
      "Every ticket that has no worklog rows at all. Return column `title`, ordered by title.",
      350, "sqlx", None,
      "SELECT tk.title AS title FROM ticket tk LEFT JOIN worklog w ON w.ticket_id=tk.id "
      "WHERE w.id IS NULL ORDER BY title"),

    P("x-sql-3", DEPTHS[2],
      "For every sprint, its `name` and `closed_count` — the number of its tickets in state "
      "'closed'. Sprints with no closed tickets, and sprints with no tickets at all, must "
      "still appear with 0. Order by sprint id.", 350, "sqlx", None,
      "SELECT s.name AS name, SUM(CASE WHEN tk.state='closed' THEN 1 ELSE 0 END) AS "
      "closed_count FROM sprint s LEFT JOIN ticket tk ON tk.sprint_id=s.id "
      "GROUP BY s.id, s.name ORDER BY s.id"),

    P("x-sql-4", DEPTHS[3],
      "The single assignee with the most points across tickets NOT in state 'closed'. Return "
      "`assignee` and `open_points`, one row.", 350, "sqlx", None,
      "SELECT assignee AS assignee, SUM(points) AS open_points FROM ticket "
      "WHERE state<>'closed' GROUP BY assignee ORDER BY open_points DESC LIMIT 1"),

    P("x-sql-5", DEPTHS[4],
      "Tenants that have at least one ticket and none of whose tickets are in state 'open' or "
      "'review'. Return column `name`, ordered by name.", 350, "sqlx", None,
      "SELECT t.name AS name FROM tenant t JOIN sprint s ON s.tenant_id=t.id "
      "JOIN ticket tk ON tk.sprint_id=s.id GROUP BY t.id, t.name "
      "HAVING SUM(CASE WHEN tk.state IN ('open','review') THEN 1 ELSE 0 END)=0 ORDER BY name"),
]


# =========================================================== JS
JS_UTIL = """'use strict';

function clampInt(n, lo, hi) {
  if (typeof n !== 'number' || !Number.isFinite(n)) return null;
  return Math.max(lo, Math.min(hi, Math.trunc(n)));
}

function byId(rows) {
  const m = new Map();
  for (const r of rows) m.set(r.id, r);
  return m;
}

module.exports = { clampInt, byId };
"""

JS_INTRO = [
    ("Front-end library now. Everything in `web/src/lib` may import exactly one thing: the "
     "shared util module. No lodash, no ramda, no date-fns — the bundle budget is hard.\n\n"
     "`web/src/lib/aerutil.js`\n\n```javascript\n" + JS_UTIL + "```",
     "Read. `clampInt(n, lo, hi)` returns null for non-finite input, and `byId(rows)` returns "
     "a Map keyed by `id`."),

    ("Module rules for `web/src/lib`:\n\n"
     "1. Export with an object literal: `module.exports = { fnName };`. A bare "
     "`module.exports = fn` breaks our barrel file — it is a build error, not a style nit.\n"
     "2. Library functions never throw. Invalid input returns `null`.\n"
     "3. Any clamping of a numeric argument goes through `clampInt`. Don't hand-roll "
     "Math.min/Math.max chains.\n"
     "4. CommonJS, not ESM. `require`, not `import`.\n\n"
     "Got all that?",
     "Got it — object-literal exports, return null instead of throwing, clamp via `clampInt`, "
     "CommonJS only."),
]

JS_PROBES = [
    P("x-js-1", DEPTHS[0],
      "Write `pageOf(rows, page, size)` in `web/src/lib/page.js`. It returns the given page "
      "(1-based) of rows. `size` is clamped to 1..100 and `page` to 1..1000. If `rows` is not "
      "an array, return null. Output only the code.", 550, "jsx",
      "const { pageOf } = require('./sol.js');\nconst assert = require('assert');\n"
      "const rows = Array.from({length: 25}, (_, i) => ({ id: 'r' + i }));\n"
      "assert.deepStrictEqual(pageOf(rows, 2, 10).map(r => r.id), "
      "['r10','r11','r12','r13','r14','r15','r16','r17','r18','r19']);\n"
      "assert.strictEqual(pageOf(rows, 1, 500).length, 25);\n"
      "assert.strictEqual(pageOf(rows, 1, 0).length, 1);\n"
      "assert.strictEqual(pageOf('nope', 1, 10), null);\n"
      "const src = require('fs').readFileSync('./sol.js', 'utf8');\n"
      "assert.ok(src.includes('clampInt'), 'must clamp via clampInt');\n",
      "'use strict';\nconst { clampInt } = require('./aerutil');\n\n"
      "function pageOf(rows, page, size) {\n"
      "  if (!Array.isArray(rows)) return null;\n"
      "  const s = clampInt(size, 1, 100);\n  const p = clampInt(page, 1, 1000);\n"
      "  if (s === null || p === null) return null;\n"
      "  return rows.slice((p - 1) * s, (p - 1) * s + s);\n}\n\n"
      "module.exports = { pageOf };\n"),

    P("x-js-2", DEPTHS[1],
      "Write `dedupeById(rows)` in `web/src/lib/dedupe.js`. Later rows win over earlier ones "
      "with the same id; the returned array keeps the order of first appearance. Non-array "
      "input returns null. Use the shared util for the id lookup. Output only the code.",
      550, "jsx",
      "const { dedupeById } = require('./sol.js');\nconst assert = require('assert');\n"
      "const out = dedupeById([{id:'a',v:1},{id:'b',v:2},{id:'a',v:3}]);\n"
      "assert.deepStrictEqual(out, [{id:'a',v:3},{id:'b',v:2}]);\n"
      "assert.strictEqual(dedupeById(null), null);\n"
      "const src = require('fs').readFileSync('./sol.js', 'utf8');\n"
      "assert.ok(src.includes('byId'), 'must use the shared byId helper');\n",
      "'use strict';\nconst { byId } = require('./aerutil');\n\n"
      "function dedupeById(rows) {\n"
      "  if (!Array.isArray(rows)) return null;\n"
      "  const m = byId(rows);\n  const seen = new Set();\n  const out = [];\n"
      "  for (const r of rows) {\n"
      "    if (seen.has(r.id)) continue;\n    seen.add(r.id);\n    out.push(m.get(r.id));\n  }\n"
      "  return out;\n}\n\nmodule.exports = { dedupeById };\n"),

    P("x-js-3", DEPTHS[2],
      "Write `groupBy(rows, key)` in `web/src/lib/group.js`. Returns a plain object mapping "
      "each distinct String(row[key]) to the array of rows having it, in input order. If rows "
      "is not an array or key is not a string, return null. Output only the code.", 550, "jsx",
      "const { groupBy } = require('./sol.js');\nconst assert = require('assert');\n"
      "const out = groupBy([{t:'a',n:1},{t:'b',n:2},{t:'a',n:3}], 't');\n"
      "assert.deepStrictEqual(Object.keys(out).sort(), ['a','b']);\n"
      "assert.deepStrictEqual(out.a.map(r => r.n), [1,3]);\n"
      "assert.strictEqual(groupBy([], 5), null);\n"
      "assert.strictEqual(groupBy('x', 't'), null);\n",
      "'use strict';\n\nfunction groupBy(rows, key) {\n"
      "  if (!Array.isArray(rows) || typeof key !== 'string') return null;\n"
      "  const out = {};\n  for (const r of rows) {\n"
      "    const k = String(r[key]);\n    if (!out[k]) out[k] = [];\n    out[k].push(r);\n  }\n"
      "  return out;\n}\n\nmodule.exports = { groupBy };\n"),

    P("x-js-4", DEPTHS[3],
      "Write `retryPlan(attempts, baseMs)` in `web/src/lib/retry.js`. Returns an array of "
      "`attempts` delays: baseMs * 2^i, each capped at 30000. `attempts` is clamped to 1..10 "
      "and `baseMs` to 1..5000, using the shared util. Non-numeric input returns null. Output "
      "only the code.", 550, "jsx",
      "const { retryPlan } = require('./sol.js');\nconst assert = require('assert');\n"
      "assert.deepStrictEqual(retryPlan(4, 100), [100,200,400,800]);\n"
      # baseMs clamps to 5000 first, then the 30000 ceiling bites on the 4th delay
      "assert.deepStrictEqual(retryPlan(4, 20000), [5000,10000,20000,30000]);\n"
      "assert.strictEqual(retryPlan(50, 100).length, 10);\n"
      "assert.strictEqual(retryPlan('x', 100), null);\n"
      "const src = require('fs').readFileSync('./sol.js', 'utf8');\n"
      "assert.ok(src.includes('clampInt'), 'must clamp via clampInt');\n",
      "'use strict';\nconst { clampInt } = require('./aerutil');\n\n"
      "function retryPlan(attempts, baseMs) {\n"
      "  const a = clampInt(attempts, 1, 10);\n  const b = clampInt(baseMs, 1, 5000);\n"
      "  if (a === null || b === null) return null;\n"
      "  const out = [];\n"
      "  for (let i = 0; i < a; i++) out.push(Math.min(b * Math.pow(2, i), 30000));\n"
      "  return out;\n}\n\nmodule.exports = { retryPlan };\n"),

    P("x-js-5", DEPTHS[4],
      "Write `diffSets(a, b)` in `web/src/lib/diff.js`. Both arguments are arrays of strings. "
      "Return `{ added, removed }` where added is in b but not a, removed is in a but not b, "
      "both sorted ascending. Either argument not an array returns null. Output only the code.",
      550, "jsx",
      "const { diffSets } = require('./sol.js');\nconst assert = require('assert');\n"
      "assert.deepStrictEqual(diffSets(['a','b','c'], ['b','c','d']), "
      "{ added: ['d'], removed: ['a'] });\n"
      "assert.deepStrictEqual(diffSets([], []), { added: [], removed: [] });\n"
      "assert.strictEqual(diffSets(['a'], 'b'), null);\n",
      "'use strict';\n\nfunction diffSets(a, b) {\n"
      "  if (!Array.isArray(a) || !Array.isArray(b)) return null;\n"
      "  const sa = new Set(a);\n  const sb = new Set(b);\n"
      "  return {\n    added: b.filter(x => !sa.has(x)).sort(),\n"
      "    removed: a.filter(x => !sb.has(x)).sort(),\n  };\n}\n\n"
      "module.exports = { diffSets };\n"),
]


# =========================================================== TS
TS_RESULT = """export type Result<T> =
  | { readonly ok: true; readonly value: T }
  | { readonly ok: false; readonly error: string };
"""

TS_INTRO = [
    ("Same front end, the typed half. This is the discriminated union every exported function "
     "returns. Note it is `error`, a string — not `err`, and there is no `code` field. The "
     "Python side of the monorepo uses a different record; don't mix them up.\n\n"
     "`web/src/lib/result.ts`\n\n```typescript\n" + TS_RESULT + "```",
     "Read. `Result<T>` is `{ok: true, value: T} | {ok: false, error: string}`, discriminated "
     "on `ok`, with `error` spelled out in full."),

    ("TypeScript rules here:\n\n"
     "1. `--strict` is on and CI fails on any error. `noImplicitAny` included.\n"
     "2. The word `any` is banned outright; so is `as` for anything but `as const`.\n"
     "3. Exported functions return `Result<T>`. They never throw and never return null.\n"
     "4. Import the type with `import type { Result } from './result';`.\n\n"
     "Confirm and we'll start.",
     "Confirmed — strict mode, no `any`, no non-const assertions, everything returns "
     "`Result<T>` imported as a type from `./result`."),
]

TS_PROBES = [
    P("x-ts-1", DEPTHS[0],
      "Write and export `parsePort(raw: string)`. It returns the port as a number when raw is "
      "all digits and in 1..65535, otherwise a failure carrying the message 'bad port'. Output "
      "only the code.", 500, "tsx",
      "import { parsePort } from './sol';\n"
      "const a = parsePort('8080');\nif (!a.ok) throw new Error('want ok');\n"
      "if (a.value !== 8080) throw new Error('value');\n"
      "const b = parsePort('0');\nif (b.ok) throw new Error('want fail');\n"
      "if (b.error !== 'bad port') throw new Error('error text: ' + b.error);\n"
      "const c = parsePort('7x');\nif (c.ok || c.error !== 'bad port') throw new Error('c');\n"
      "const d = parsePort('70000');\nif (d.ok) throw new Error('d');\n",
      "import type { Result } from './result';\n\n"
      "export function parsePort(raw: string): Result<number> {\n"
      "  if (!/^[0-9]+$/.test(raw)) return { ok: false, error: 'bad port' };\n"
      "  const n = Number(raw);\n"
      "  if (n < 1 || n > 65535) return { ok: false, error: 'bad port' };\n"
      "  return { ok: true, value: n };\n}\n"),

    P("x-ts-2", DEPTHS[1],
      "Write and export `firstWhere<T>(rows: readonly T[], pred: (row: T) => boolean)` "
      "returning the first matching row, or a failure with the message 'not found'. Output "
      "only the code.", 500, "tsx",
      "import { firstWhere } from './sol';\n"
      "const r = firstWhere([1,2,3], (n) => n > 1);\n"
      "if (!r.ok || r.value !== 2) throw new Error('r');\n"
      "const s = firstWhere<number>([], () => true);\n"
      "if (s.ok || s.error !== 'not found') throw new Error('s');\n"
      "const t = firstWhere(['a','bb'], (x) => x.length === 2);\n"
      "if (!t.ok || t.value !== 'bb') throw new Error('t');\n",
      "import type { Result } from './result';\n\n"
      "export function firstWhere<T>(rows: readonly T[], pred: (row: T) => boolean): "
      "Result<T> {\n"
      "  for (const row of rows) {\n    if (pred(row)) return { ok: true, value: row };\n  }\n"
      "  return { ok: false, error: 'not found' };\n}\n"),

    P("x-ts-3", DEPTHS[2],
      "Write and export `sumPoints(rows: readonly { points: number }[])` returning the total, "
      "and failing with 'empty' when there are no rows. Output only the code.", 500, "tsx",
      "import { sumPoints } from './sol';\n"
      "const r = sumPoints([{points:2},{points:5}]);\n"
      "if (!r.ok || r.value !== 7) throw new Error('r');\n"
      "const s = sumPoints([]);\nif (s.ok || s.error !== 'empty') throw new Error('s');\n",
      "import type { Result } from './result';\n\n"
      "export function sumPoints(rows: readonly { points: number }[]): Result<number> {\n"
      "  if (rows.length === 0) return { ok: false, error: 'empty' };\n"
      "  let total = 0;\n  for (const row of rows) total += row.points;\n"
      "  return { ok: true, value: total };\n}\n"),

    P("x-ts-4", DEPTHS[3],
      "Write and export `pickKeys<T extends object, K extends keyof T>(row: T, keys: "
      "readonly K[])` returning a new object with only those keys. An empty `keys` fails with "
      "'no keys'. Output only the code.", 500, "tsx",
      "import { pickKeys } from './sol';\n"
      "const r = pickKeys({ a: 1, b: 'x', c: true }, ['a','c'] as const);\n"
      "if (!r.ok) throw new Error('want ok');\n"
      "if (r.value.a !== 1 || r.value.c !== true) throw new Error('value');\n"
      "if (Object.keys(r.value).length !== 2) throw new Error('extra keys');\n"
      "const s = pickKeys({ a: 1 }, [] as const);\n"
      "if (s.ok || s.error !== 'no keys') throw new Error('s');\n",
      "import type { Result } from './result';\n\n"
      "export function pickKeys<T extends object, K extends keyof T>(\n"
      "  row: T,\n  keys: readonly K[],\n): Result<Pick<T, K>> {\n"
      "  if (keys.length === 0) return { ok: false, error: 'no keys' };\n"
      "  const out = {} as Pick<T, K>;\n"
      "  for (const k of keys) out[k] = row[k];\n"
      "  return { ok: true, value: out };\n}\n"),

    P("x-ts-5", DEPTHS[4],
      "Write and export `splitOk<T>(rows: readonly Result<T>[])` returning `{ values, errors }` "
      "— the unwrapped values of the successes and the messages of the failures, in input "
      "order. An empty input fails with 'empty'. Output only the code.", 550, "tsx",
      "import { splitOk } from './sol';\n"
      "const r = splitOk<number>([{ok:true,value:1},{ok:false,error:'e1'},{ok:true,value:3}]);\n"
      "if (!r.ok) throw new Error('want ok');\n"
      "if (JSON.stringify(r.value.values) !== '[1,3]') throw new Error('values');\n"
      "if (JSON.stringify(r.value.errors) !== '[\"e1\"]') throw new Error('errors');\n"
      "const s = splitOk<number>([]);\n"
      "if (s.ok || s.error !== 'empty') throw new Error('s');\n",
      "import type { Result } from './result';\n\n"
      "export function splitOk<T>(\n  rows: readonly Result<T>[],\n"
      "): Result<{ values: T[]; errors: string[] }> {\n"
      "  if (rows.length === 0) return { ok: false, error: 'empty' };\n"
      "  const values: T[] = [];\n  const errors: string[] = [];\n"
      "  for (const row of rows) {\n"
      "    if (row.ok) values.push(row.value);\n    else errors.push(row.error);\n  }\n"
      "  return { ok: true, value: { values, errors } };\n}\n"),
]


PART1 = {
    "Python": {"intro": PY_INTRO, "probes": PY_PROBES},
    "Django": {"intro": DJ_INTRO, "probes": DJ_PROBES},
    "SQL": {"intro": SQL_INTRO, "probes": SQL_PROBES},
    "JS": {"intro": JS_INTRO, "probes": JS_PROBES},
    "TS": {"intro": TS_INTRO, "probes": TS_PROBES},
}
