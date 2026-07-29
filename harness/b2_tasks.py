#!/usr/bin/env python3
"""Task definitions for the 50-task agentic benchmark + RAG set.

Grading kinds:
  py      execute generated python against assertions
  django  execute against a real Django ORM + sqlite (query counts checked)
  sql     execute generated SQL against seeded sqlite, compare result rows
  bash    execute generated command in a fixture dir, verify filesystem state
  git     execute generated command in a fixture git repo, verify repo state
  js      execute generated JS in node against assertions
  ts      typecheck with tsc --strict, then execute against assertions
  sshcfg  write generated ssh config, validate with `ssh -G`
  yaml    parse generated YAML, assert structural facts
  rubric  pattern match (used only where execution is impossible)
"""

# ============================================================== PYTHON (8)
PYTHON = [
    ("py-lru", "Write a Python class `LRUCache` with `__init__(self, capacity)`, `get(self, key)` "
     "returning -1 when absent, and `put(self, key, value)`. Both operations must be O(1). Code only.",
     """
c = LRUCache(2)
c.put(1,1); c.put(2,2)
assert c.get(1) == 1
c.put(3,3)
assert c.get(2) == -1
c.put(4,4)
assert c.get(1) == -1 and c.get(3) == 3 and c.get(4) == 4
import inspect, re
src = inspect.getsource(LRUCache)
assert not re.search(r'\\.index\\(|\\.remove\\(', src), 'used O(n) list ops'
"""),
    ("py-topo", "Write a Python function `topo_sort(graph)` where graph is a dict mapping node -> "
     "list of nodes it depends on. Return a list ordering every node after its dependencies, or "
     "None if there is a cycle. Code only.",
     """
r = topo_sort({'a': [], 'b': ['a'], 'c': ['b']})
assert r.index('a') < r.index('b') < r.index('c'), r
assert topo_sort({'a': ['b'], 'b': ['a']}) is None
assert topo_sort({}) == []
r2 = topo_sort({'x': [], 'y': []})
assert sorted(r2) == ['x','y']
"""),
    ("py-csv", "Write a Python function `parse_csv(text)` that parses CSV with a header row and "
     "returns a list of dicts. It must handle double-quoted fields containing commas and escaped "
     "double quotes (\"\" means a literal quote). Code only.",
     """
t = 'name,note\\nalice,\"hello, world\"\\nbob,\"say \"\"hi\"\"\"'
r = parse_csv(t)
assert r == [{'name':'alice','note':'hello, world'},{'name':'bob','note':'say \"hi\"'}], r
"""),
    ("py-bucket", "Write a Python class `TokenBucket` with `__init__(self, capacity, refill_per_sec, "
     "now)` and `allow(self, now)` returning True if a token was consumed. Tokens refill "
     "continuously based on elapsed time and never exceed capacity. `now` is a float timestamp "
     "passed in (do not call time.time). Code only.",
     """
b = TokenBucket(2, 1.0, 0.0)
assert b.allow(0.0) is True
assert b.allow(0.0) is True
assert b.allow(0.0) is False
assert b.allow(1.0) is True
assert b.allow(1.0) is False
b2 = TokenBucket(3, 1.0, 0.0)
assert b2.allow(100.0) is True
for _ in range(2): b2.allow(100.0)
assert b2.allow(100.0) is False, 'capacity exceeded'
"""),
    ("py-lcs", "Write a Python function `lcs_len(a, b)` returning the length of the longest common "
     "subsequence of two strings. Code only.",
     """
assert lcs_len('abcde','ace') == 3
assert lcs_len('abc','abc') == 3
assert lcs_len('abc','def') == 0
assert lcs_len('','x') == 0
"""),
    ("py-normpath", "Write a Python function `normalize(path)` that normalizes a POSIX path string: "
     "collapse duplicate slashes, resolve '.' and '..' segments, keep a leading '/' if absolute. "
     "Never use os.path. Return '/' for an empty absolute result and '.' for an empty relative "
     "result. Code only.",
     """
assert normalize('/a//b/../c/') == '/a/c'
assert normalize('a/./b/../../c') == 'c'
assert normalize('/..') == '/'
assert normalize('') == '.'
assert normalize('/a/b/c') == '/a/b/c'
"""),
    ("py-merge", "Write a Python function `merge_dicts(a, b)` that deeply merges dict b into dict a "
     "and returns a NEW dict, without mutating either input. Nested dicts merge recursively; "
     "non-dict values in b overwrite a. Code only.",
     """
a = {'x': {'y': 1, 'z': 2}, 'k': 1}
b = {'x': {'z': 9, 'w': 3}, 'n': 5}
r = merge_dicts(a, b)
assert r == {'x': {'y':1,'z':9,'w':3}, 'k':1, 'n':5}, r
assert a == {'x': {'y': 1, 'z': 2}, 'k': 1}, 'mutated input a'
assert b == {'x': {'z': 9, 'w': 3}, 'n': 5}, 'mutated input b'
"""),
    ("py-retry", "Write a Python decorator `retry(times)` that retries the wrapped function up to "
     "`times` total attempts when it raises, re-raising the final exception if all fail. Preserve "
     "the wrapped function's __name__. Do not sleep. Code only.",
     """
calls = {'n': 0}
@retry(3)
def flaky():
    calls['n'] += 1
    if calls['n'] < 3: raise ValueError('boom')
    return 'ok'
assert flaky() == 'ok' and calls['n'] == 3
assert flaky.__name__ == 'flaky', flaky.__name__
c2 = {'n': 0}
@retry(2)
def always():
    c2['n'] += 1
    raise KeyError('nope')
try:
    always(); assert False
except KeyError: pass
assert c2['n'] == 2
"""),
]

# ============================================================== DJANGO (5)
# Harness supplies these models; the model only writes the query function.
DJANGO_MODELS = """
from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=50)

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')
    price = models.DecimalField(max_digits=8, decimal_places=2)
    published = models.DateField()
"""

DJANGO_CTX = (
    "Given these Django models:\n\n```python\n" + DJANGO_MODELS.strip() + "\n```\n\n"
)

DJANGO = [
    ("dj-annotate",
     DJANGO_CTX + "Write a function `prolific(n)` returning a QuerySet of Authors who have strictly "
     "more than n books, annotated with attribute `book_count`, ordered by book_count descending. "
     "Assume Author and Book are already imported. Code only.",
     """
r = list(prolific(1))
assert [a.name for a in r] == ['Ann'], [a.name for a in r]
assert r[0].book_count == 2, r[0].book_count
assert list(prolific(5)) == []
"""),
    ("dj-nplus1",
     DJANGO_CTX + "Write a function `books_with_authors()` returning a QuerySet of all Books that "
     "will NOT trigger an additional query per book when accessing `book.author.name`. "
     "Assume Author and Book are already imported. Code only.",
     """
from django.test.utils import CaptureQueriesContext
from django.db import connection
with CaptureQueriesContext(connection) as ctx:
    for b in books_with_authors():
        _ = b.author.name
assert len(ctx.captured_queries) == 1, f'N+1: {len(ctx.captured_queries)} queries'
"""),
    ("dj-aggregate",
     DJANGO_CTX + "Write a function `price_stats()` returning a dict with keys 'total' and 'avg' "
     "for all Book prices, computed in the database with a single aggregate query (not in Python). "
     "Assume Author and Book are already imported. Code only.",
     """
from decimal import Decimal
s = price_stats()
assert round(Decimal(str(s['total'])), 2) == Decimal('60.00'), s
assert round(Decimal(str(s['avg'])), 2) == Decimal('20.00'), s
"""),
    ("dj-filter",
     DJANGO_CTX + "Write a function `by_author_substring(sub)` returning a QuerySet of Books whose "
     "author's name contains `sub` case-insensitively, ordered by published date ascending. "
     "Assume Author and Book are already imported. Code only.",
     """
r = [b.title for b in by_author_substring('an')]
assert r == ['B1','B2'], r
assert list(by_author_substring('zzz')) == []
"""),
    ("dj-bulk",
     DJANGO_CTX + "Write a function `add_books(author, titles, price, when)` that creates one Book "
     "per title in a single database INSERT statement and returns the number created. "
     "Assume Author and Book are already imported. Code only.",
     """
from django.test.utils import CaptureQueriesContext
from django.db import connection
import datetime
a = Author.objects.get(name='Ann')
with CaptureQueriesContext(connection) as ctx:
    n = add_books(a, ['X','Y','Z'], 5, datetime.date(2024,1,1))
assert n == 3, n
inserts = [q for q in ctx.captured_queries if 'INSERT' in q['sql'].upper()]
assert len(inserts) == 1, f'{len(inserts)} INSERTs, expected 1'
"""),
]

# ============================================================== SQL (6)
SQL_SCHEMA = """
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, country TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, total REAL, created TEXT);
CREATE TABLE items (id INTEGER PRIMARY KEY, order_id INTEGER, product TEXT, category TEXT, qty INTEGER, price REAL);
INSERT INTO customers VALUES (1,'Ann','UK'),(2,'Bob','US'),(3,'Cid','UK'),(4,'Dee','US');
INSERT INTO orders VALUES
 (1,1,100.0,'2024-01-15'),(2,1,50.0,'2024-02-10'),(3,2,200.0,'2024-01-20'),
 (4,2,25.0,'2024-03-05'),(5,3,75.0,'2024-02-28');
INSERT INTO items VALUES
 (1,1,'widget','tools',2,25.0),(2,1,'gizmo','tools',1,50.0),
 (3,2,'book','media',5,10.0),(4,3,'widget','tools',4,25.0),
 (5,3,'film','media',2,50.0),(6,4,'book','media',1,25.0),
 (7,5,'gizmo','tools',1,75.0);
"""

SQL_CTX = ("Given this SQLite schema:\n\n```sql\n"
           "customers(id, name, country)\n"
           "orders(id, customer_id, total, created)   -- created is 'YYYY-MM-DD' text\n"
           "items(id, order_id, product, category, qty, price)\n```\n\n")

SQL = [
    ("sql-revenue", SQL_CTX + "Write one SQL query returning customer name and their total order "
     "value as `revenue`, for customers whose total exceeds 100, ordered by revenue descending. "
     "Output only the SQL.",
     [("Bob", 225.0), ("Ann", 150.0)]),
    ("sql-noorders", SQL_CTX + "Write one SQL query returning the names of customers who have no "
     "orders at all, ordered alphabetically. Output only the SQL.",
     [("Dee",)]),
    ("sql-window", SQL_CTX + "Write one SQL query returning category, product and total quantity "
     "sold, ranked within each category by quantity descending, keeping only the top product per "
     "category. Return columns category, product, qty ordered by category. Output only the SQL.",
     [("media", "book", 6), ("tools", "widget", 6)]),
    ("sql-monthly", SQL_CTX + "Write one SQL query returning the year-month (as 'YYYY-MM') and the "
     "sum of order totals for each month, ordered chronologically. Name the columns month and "
     "total. Output only the SQL.",
     [("2024-01", 300.0), ("2024-02", 125.0), ("2024-03", 25.0)]),
    ("sql-having", SQL_CTX + "Write one SQL query returning country and the number of orders placed "
     "by customers from that country, only for countries with more than 2 orders. Name the columns "
     "country and n. Output only the SQL.",
     [("UK", 3)]),
    ("sql-cte", SQL_CTX + "Using a CTE, write one SQL query returning the name of each customer and "
     "the value of their single largest order as `biggest`, only for customers who have ordered, "
     "ordered by biggest descending. Output only the SQL.",
     [("Bob", 200.0), ("Ann", 100.0), ("Cid", 75.0)]),
]

# ============================================================== JS (4) / TS (3)
JS = [
    ("js-deepequal", "Write a JavaScript function `deepEqual(a, b)` returning true if two values are "
     "deeply equal (objects, arrays, primitives; key order irrelevant). Export it with "
     "`module.exports = { deepEqual }`. Code only.",
     """
const {deepEqual} = require('./sol.js');
const assert = require('assert');
assert.strictEqual(deepEqual({a:1,b:[1,2]}, {b:[1,2],a:1}), true);
assert.strictEqual(deepEqual({a:1}, {a:2}), false);
assert.strictEqual(deepEqual([1,[2]], [1,[2]]), true);
assert.strictEqual(deepEqual(null, null), true);
assert.strictEqual(deepEqual({a:1}, {a:1,b:2}), false);
console.log('OK');
"""),
    ("js-flatten", "Write a JavaScript function `flattenObject(obj)` turning a nested object into a "
     "flat object with dot-separated keys. Arrays are treated as leaf values. Export with "
     "`module.exports = { flattenObject }`. Code only.",
     """
const {flattenObject} = require('./sol.js');
const assert = require('assert');
assert.deepStrictEqual(flattenObject({a:{b:{c:1}},d:2}), {'a.b.c':1,'d':2});
assert.deepStrictEqual(flattenObject({a:[1,2]}), {'a':[1,2]});
assert.deepStrictEqual(flattenObject({}), {});
console.log('OK');
"""),
    ("js-retry", "Write an async JavaScript function `retryAsync(fn, attempts)` that calls fn (which "
     "returns a promise) up to `attempts` times, resolving with the first success and rejecting "
     "with the last error if all fail. Do not sleep. Export with "
     "`module.exports = { retryAsync }`. Code only.",
     """
const {retryAsync} = require('./sol.js');
const assert = require('assert');
(async () => {
  let n = 0;
  const r = await retryAsync(async () => { n++; if (n < 3) throw new Error('x'); return 'ok'; }, 5);
  assert.strictEqual(r, 'ok'); assert.strictEqual(n, 3);
  let m = 0;
  await assert.rejects(retryAsync(async () => { m++; throw new Error('always'); }, 2));
  assert.strictEqual(m, 2);
  console.log('OK');
})().catch(e => { console.error(e); process.exit(1); });
"""),
    ("js-groupby", "Write a JavaScript function `groupBy(arr, keyFn)` returning an object mapping "
     "each key produced by keyFn to the array of matching items, preserving input order. Export "
     "with `module.exports = { groupBy }`. Code only.",
     """
const {groupBy} = require('./sol.js');
const assert = require('assert');
assert.deepStrictEqual(groupBy([1,2,3,4], x => x % 2 ? 'odd' : 'even'), {odd:[1,3], even:[2,4]});
assert.deepStrictEqual(groupBy([], x => x), {});
console.log('OK');
"""),
]

TS = [
    ("ts-pick", "Write TypeScript exporting a generic function "
     "`export function pick<T extends object, K extends keyof T>(obj: T, keys: K[]): Pick<T, K>` "
     "that returns a new object with only the given keys. It must typecheck under --strict. Code only.",
     """
import { pick } from './sol';
import * as assert from 'assert';
const r = pick({a: 1, b: 'x', c: true}, ['a', 'b']);
assert.deepStrictEqual(r, {a: 1, b: 'x'});
const n: number = r.a;
assert.strictEqual(n, 1);
console.log('OK');
"""),
    ("ts-union", "Write TypeScript defining a discriminated union "
     "`export type Shape = {kind:'circle'; r:number} | {kind:'rect'; w:number; h:number}` and "
     "`export function area(s: Shape): number` using exhaustive switching on kind. Must typecheck "
     "under --strict. Code only.",
     """
import { area, Shape } from './sol';
import * as assert from 'assert';
const shapes: Shape[] = [{kind:'circle', r:1}, {kind:'rect', w:2, h:3}];
assert.ok(Math.abs(area(shapes[0]) - Math.PI) < 1e-9);
assert.strictEqual(area(shapes[1]), 6);
console.log('OK');
"""),
    ("ts-result", "Write TypeScript exporting "
     "`export type Result<T, E> = {ok: true; value: T} | {ok: false; error: E}` plus "
     "`export function mapResult<T, U, E>(r: Result<T,E>, f: (t:T)=>U): Result<U,E>` which applies "
     "f only on success. Must typecheck under --strict. Code only.",
     """
import { mapResult, Result } from './sol';
import * as assert from 'assert';
const ok: Result<number, string> = {ok: true, value: 2};
const bad: Result<number, string> = {ok: false, error: 'e'};
assert.deepStrictEqual(mapResult(ok, x => x * 3), {ok: true, value: 6});
assert.deepStrictEqual(mapResult(bad, x => x * 3), {ok: false, error: 'e'});
console.log('OK');
"""),
]

# ============================================================== BASH (6)
# (setup script, prompt, checker script) -- all run inside a fixture dir
BASH = [
    ("sh-rename",
     "mkdir -p d && touch d/a.txt d/b.txt d/c.log",
     "In the current directory there is a folder `d` containing .txt and .log files. Rename every "
     ".txt file inside d to the same name with a .md extension, leaving .log files alone. "
     "Reply with a single shell command only, no explanation, no markdown.",
     "test -f d/a.md && test -f d/b.md && test -f d/c.log && ! test -f d/a.txt"),
    ("sh-dedupe",
     "printf 'b\\na\\nb\\nc\\na\\n' > in.txt",
     "The file in.txt has duplicate lines. Write the deduplicated content, preserving the order of "
     "first appearance, to out.txt. Reply with a single shell command only, no explanation, no markdown.",
     "test \"$(cat out.txt)\" = \"$(printf 'b\\na\\nc\\n')\""),
    ("sh-findbig",
     "mkdir -p x/y && head -c 2000 /dev/zero > x/big.bin && head -c 10 /dev/zero > x/y/small.bin",
     "Write the paths of all files under the directory x that are larger than 1 kilobyte into "
     "found.txt, one per line. Reply with a single shell command only, no explanation, no markdown.",
     "grep -q 'big.bin' found.txt && ! grep -q 'small.bin' found.txt"),
    ("sh-count",
     "mkdir -p p/q && printf 'a\\nb\\n' > p/one.py && printf 'c\\n' > p/q/two.py && printf 'x\\n' > p/skip.txt",
     "Count the total number of lines across all .py files under the directory p (recursively) and "
     "write just that number into count.txt. Reply with a single shell command only, no explanation, "
     "no markdown.",
     "test \"$(tr -dc '0-9' < count.txt)\" = 3"),
    ("sh-archive",
     "mkdir -p data && echo hello > data/f1 && echo world > data/f2",
     "Create a gzip-compressed tar archive named backup.tar.gz containing the directory data. "
     "Reply with a single shell command only, no explanation, no markdown.",
     "test -f backup.tar.gz && tar -tzf backup.tar.gz | grep -q 'data/f1'"),
    ("sh-sed",
     "mkdir -p s/deep && echo 'foo here' > s/a.conf && echo 'foo there' > s/deep/b.conf",
     "Replace every occurrence of the word foo with bar, in place, in all .conf files under the "
     "directory s including subdirectories. Reply with a single shell command only, no explanation, "
     "no markdown.",
     "grep -q bar s/a.conf && grep -q bar s/deep/b.conf && ! grep -rq foo s/"),
]

# ============================================================== GIT (6)
GIT = [
    ("git-soft",
     "git init -q . && git config user.email a@b.c && git config user.name t && "
     "echo one > f.txt && git add . && git commit -qm first && "
     "echo two >> f.txt && git add . && git commit -qm second",
     "Undo the most recent commit but keep its changes staged in the index. "
     "Reply with a single shell command only, no explanation, no markdown.",
     "test \"$(git rev-list --count HEAD)\" = 1 && git diff --cached --quiet; test $? -ne 0"),
    ("git-revert",
     "git init -q . && git config user.email a@b.c && git config user.name t && "
     "echo good > f.txt && git add . && git commit -qm first && "
     "echo bad > f.txt && git add . && git commit -qm bad",
     "Create a new commit that undoes the changes introduced by the most recent commit, without "
     "rewriting history. Do not open an editor. Reply with a single shell command only, no "
     "explanation, no markdown.",
     "test \"$(cat f.txt)\" = good && test \"$(git rev-list --count HEAD)\" = 3"),
    ("git-uncached",
     "git init -q . && git config user.email a@b.c && git config user.name t && "
     "echo x > keep.txt && echo y > secret.env && git add . && git commit -qm first",
     "Stop tracking the file secret.env in git, but keep the file on disk. "
     "Reply with a single shell command only, no explanation, no markdown.",
     "test -f secret.env && ! git ls-files --error-unmatch secret.env 2>/dev/null"),
    ("git-tag",
     "git init -q . && git config user.email a@b.c && git config user.name t && "
     "echo x > f.txt && git add . && git commit -qm first",
     "Create an annotated git tag named v1.0.0 with the message 'release one' on the current commit. "
     "Reply with a single shell command only, no explanation, no markdown.",
     "git cat-file -t \"$(git rev-parse v1.0.0)\" | grep -q tag && git tag -l -n1 v1.0.0 | grep -q 'release one'"),
    ("git-branch-rename",
     "git init -q . && git config user.email a@b.c && git config user.name t && "
     "echo x > f.txt && git add . && git commit -qm first && git branch -m oldname",
     "Rename the current git branch from oldname to newname. "
     "Reply with a single shell command only, no explanation, no markdown.",
     "test \"$(git rev-parse --abbrev-ref HEAD)\" = newname"),
    ("git-cherry",
     "git init -q . && git config user.email a@b.c && git config user.name t && "
     "echo base > f.txt && git add . && git commit -qm base && "
     "git checkout -q -b feature && echo feat > g.txt && git add . && git commit -qm featwork && "
     "git checkout -q -",
     "You are on the main branch. Apply only the single commit from the branch `feature` (its tip) "
     "onto the current branch. Reply with a single shell command only, no explanation, no markdown.",
     "test -f g.txt && test \"$(git rev-parse --abbrev-ref HEAD)\" != feature"),
]

# ============================================================== SSH (3)
SSH = [
    ("ssh-jump",
     "Write an OpenSSH client config block for a host alias `prod` at hostname 10.0.5.20, user "
     "deploy, port 2222, reached through the jump host `bastion.example.com` as user jump. "
     "Output only the config file content, no markdown.",
     "prod", {"hostname": "10.0.5.20", "user": "deploy", "port": "2222", "proxyjump": "jump@bastion.example.com"}),
    ("ssh-keepalive",
     "Write an OpenSSH client config block for host alias `db` at hostname db.internal, user admin, "
     "using the private key ~/.ssh/db_ed25519, sending a keepalive every 30 seconds, and disabling "
     "agent forwarding. Output only the config file content, no markdown.",
     "db", {"hostname": "db.internal", "user": "admin", "serveraliveinterval": "30", "forwardagent": "no"}),
    ("ssh-tunnel",
     "Give the command to forward local port 5433 to port 5432 on host db.internal reached via ssh "
     "to user@jump.example.com, without opening a remote shell, running in the background. "
     "Reply with a single shell command only, no explanation, no markdown.",
     # flags may be bundled: `ssh -fN` is equivalent to `ssh -f -N`
     None, [r"ssh", r"-[a-zA-Z]*L", r"5433:db\.internal:5432", r"-[a-zA-Z]*N",
            r"(-[a-zA-Z]*f|&\s*$)", r"user@jump\.example\.com"]),
]

# ============================================================== GITHUB (4)
GITHUB = [
    ("gh-ci", "Write a GitHub Actions workflow that runs on pushes and pull requests targeting the "
     "main branch, checks out the repo, sets up Python 3.12, installs requirements.txt, and runs "
     "pytest. Output only the YAML, no markdown fences.",
     "workflow_ci"),
    ("gh-matrix", "Write a GitHub Actions workflow triggered on push that runs the job on a matrix of "
     "Node versions 18, 20 and 22 on ubuntu-latest, checking out the repo and running `npm test`. "
     "Output only the YAML, no markdown fences.",
     "workflow_matrix"),
    ("gh-pr", "Using the GitHub CLI, create a pull request from the current branch into main with "
     "title 'Add caching' and body 'Speeds up builds'. Reply with a single shell command only, no "
     "explanation, no markdown.",
     [r"gh\s+pr\s+create", r"(--base|-B)\s+main", r"--title", r"Add caching", r"--body", r"Speeds up builds"]),
    ("gh-issues", "Using the GitHub CLI, list all open issues labelled `bug` assigned to the user "
     "octocat. Reply with a single shell command only, no explanation, no markdown.",
     [r"gh\s+issue\s+list", r"--label", r"bug", r"--assignee", r"octocat"]),
]

# ============================================================== DOCS (3)
DOCS = [
    ("doc-docstring",
     "Write a NumPy-style Python docstring for this function. Output only the docstring text.\n\n"
     "```python\ndef fetch(url, timeout=5.0, retries=3):\n"
     "    '''...'''\n    # returns parsed JSON dict; raises TimeoutError after retries exhausted\n```",
     [r"Parameters", r"Returns", r"Raises", r"url", r"timeout", r"retries", r"TimeoutError", r"(dict|JSON)"]),
    ("doc-readme",
     "Write the Installation and Usage sections of a README for a Python CLI tool called `logsift` "
     "installed via pip, which takes a --level flag and a file path. Use markdown headings. "
     "Output only the markdown.",
     [r"#+\s*Install", r"pip install", r"logsift", r"#+\s*Usage", r"--level"]),
    ("doc-api",
     "Document a REST endpoint: POST /api/v1/orders which accepts a JSON body with customer_id "
     "(int) and items (array), returns 201 with the created order, 400 on validation failure and "
     "401 if unauthenticated. Include the method, path, request fields, and every response status. "
     "Output only the documentation.",
     [r"POST", r"/api/v1/orders", r"customer_id", r"items", r"201", r"400", r"401"]),
]

# ============================================================== REACT NATIVE (2)
RN = [
    ("rn-list",
     "Write a React Native function component `ContactList` that renders a FlatList of contacts "
     "from props, using a stable keyExtractor based on contact.id, a renderItem showing "
     "contact.name in a Text, and pull-to-refresh wired to an onRefresh prop with a refreshing "
     "prop. Import from 'react-native'. Code only.",
     [r"import.*from\s+['\"]react-native['\"]", r"FlatList", r"keyExtractor",
      r"renderItem", r"refreshing", r"onRefresh", r"<Text"]),
    ("rn-hook",
     "Write a React Native custom hook `useDebouncedSearch(query, delay)` that returns the debounced "
     "query value, using useState and useEffect, and clearing the pending timer in the effect "
     "cleanup so it does not leak on unmount. Code only.",
     [r"useState", r"useEffect", r"setTimeout", r"clearTimeout", r"return\s*\(\s*\)\s*=>",
      r"\[.*query.*delay.*\]"]),
]

# ============================================================== RAG (10)
# Synthetic internal doc so no model can have memorised it.
RAG_DOC = """
# Aerelith Platform — Internal Operations Runbook (rev 7.2)

## Service topology
The Aerelith platform runs three services. `quill-api` handles inbound HTTP and listens on
port 8443. `marrow-worker` consumes the task queue and runs with a default concurrency of 12.
`tessel-cache` is a Redis-compatible store pinned to version 6.2.14.

## Deployment
Deployments are performed with the `aerectl` CLI. The command `aerectl roll <service>` performs
a rolling restart. A rolling restart waits 45 seconds between each pod. Deployments are frozen
between 22:00 and 06:00 UTC unless the on-call engineer sets the override flag `--break-glass`,
which is audited and pages the platform lead.

## Alert thresholds
The p99 latency alert for quill-api fires at 850 milliseconds. The queue depth alert for
marrow-worker fires when depth exceeds 4000 messages for more than 5 minutes. Cache eviction
alerts fire when the eviction rate exceeds 200 keys per second.

## Incident severities
Sev1 means total customer-facing outage and requires a public status page update within 15
minutes. Sev2 means degraded performance affecting more than 10 percent of requests. Sev3 is
internal-only impact. Only Sev1 and Sev2 require a written postmortem, due within 5 business days.

## Access
Production database access requires an approved change ticket and is granted through the
`db-breakglass` group for a maximum of 4 hours. Direct SSH to production hosts was removed in
rev 6.0; all access is now through the session broker.
"""

RAG = [
    ("rag-port", "Which port does quill-api listen on?", [r"8443"], False),
    ("rag-concurrency", "What is the default concurrency of marrow-worker?", [r"\b12\b"], False),
    ("rag-roll", "How long does a rolling restart wait between each pod?",
     [r"45\s*(second|sec|s\b)"], False),
    ("rag-freeze", "During what hours are deployments frozen, and what flag overrides the freeze?",
     [r"22:00", r"06:00", r"break-glass"], False),
    ("rag-latency", "At what p99 latency does the quill-api alert fire?",
     [r"850\s*(millisecond|ms)"], False),
    ("rag-postmortem", "Which incident severities require a written postmortem and by when?",
     [r"Sev\s*1", r"Sev\s*2", r"5\s*business\s*day"], False),
    ("rag-dbaccess", "How long can production database access be granted for, and through what group?",
     [r"4\s*hour", r"db-breakglass"], False),
    ("rag-ssh", "Can engineers SSH directly into production hosts?",
     [r"(no|removed|cannot|can't|not)", r"(session broker|broker)"], False),
    # Unanswerable — the doc says nothing about these. Model must decline.
    ("rag-unknown-sla", "What is the contractual uptime SLA percentage promised to customers?",
     None, True),
    ("rag-unknown-oncall", "What is the phone number for the on-call escalation hotline?",
     None, True),
]

# Phrases that count as correctly declining an unanswerable question.
REFUSAL = [
    r"not (specified|mentioned|stated|included|provided|given|listed|documented|covered|defined)",
    r"does(n't| not) (say|specify|mention|state|contain|include|provide)",
    r"no (information|mention|reference|details?) ",
    r"isn'?t (in|mentioned|specified|stated)",
    r"cannot be (determined|found|answered)",
    r"unable to (find|determine|answer)",
    r"not (found|available) in the",
    r"the (document|runbook|text) does not",
]
