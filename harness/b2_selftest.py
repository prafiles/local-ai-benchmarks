#!/usr/bin/env python3
"""Feed known-good reference answers to every grader kind.

Any FAIL here is a harness bug, not a model result.
"""
import sys
sys.path.insert(0, "/root/bench2")
import b2  # noqa: E402
from b2_tasks import BASH, DJANGO, GIT, JS, PYTHON, SQL, SSH, TS  # noqa: E402

T = dict((t[0], t) for t in PYTHON)
D = dict((t[0], t) for t in DJANGO)
S = dict((t[0], t) for t in SQL)
J = dict((t[0], t) for t in JS)
X = dict((t[0], t) for t in TS)
B = dict((t[0], t) for t in BASH)
G = dict((t[0], t) for t in GIT)

checks = []

# ---- python
checks.append(("py-lcs", b2.g_py("""```python
def lcs_len(a, b):
    m = [[0]*(len(b)+1) for _ in range(len(a)+1)]
    for i in range(1, len(a)+1):
        for j in range(1, len(b)+1):
            m[i][j] = m[i-1][j-1]+1 if a[i-1] == b[j-1] else max(m[i-1][j], m[i][j-1])
    return m[len(a)][len(b)]
```""", T["py-lcs"][2])))

# ---- django (annotate)
checks.append(("dj-annotate", b2.g_django("""```python
from django.db.models import Count
def prolific(n):
    return Author.objects.annotate(book_count=Count('books')).filter(
        book_count__gt=n).order_by('-book_count')
```""", D["dj-annotate"][2])))

# ---- django (n+1)
checks.append(("dj-nplus1", b2.g_django("""```python
def books_with_authors():
    return Book.objects.select_related('author')
```""", D["dj-nplus1"][2])))

# ---- sql
checks.append(("sql-revenue", b2.g_sql("""```sql
SELECT c.name, SUM(o.total) AS revenue
FROM customers c JOIN orders o ON o.customer_id = c.id
GROUP BY c.id HAVING SUM(o.total) > 100 ORDER BY revenue DESC;
```""", S["sql-revenue"][2])))

checks.append(("sql-window", b2.g_sql("""```sql
WITH t AS (
  SELECT i.category, i.product, SUM(i.qty) AS qty,
         ROW_NUMBER() OVER (PARTITION BY i.category ORDER BY SUM(i.qty) DESC) rn
  FROM items i GROUP BY i.category, i.product)
SELECT category, product, qty FROM t WHERE rn = 1 ORDER BY category;
```""", S["sql-window"][2])))

# ---- js
checks.append(("js-groupby", b2.g_js("""```javascript
function groupBy(arr, keyFn) {
  const out = {};
  for (const it of arr) { const k = keyFn(it); (out[k] ||= []).push(it); }
  return out;
}
module.exports = { groupBy };
```""", J["js-groupby"][2])))

# ---- ts
checks.append(("ts-pick", b2.g_ts("""```typescript
export function pick<T extends object, K extends keyof T>(obj: T, keys: K[]): Pick<T, K> {
  const out = {} as Pick<T, K>;
  for (const k of keys) out[k] = obj[k];
  return out;
}
```""", X["ts-pick"][2])))

# ---- bash
checks.append(("sh-dedupe", b2.g_shell("awk '!seen[$0]++' in.txt > out.txt",
                                       B["sh-dedupe"][1], B["sh-dedupe"][3])))
checks.append(("sh-rename", b2.g_shell(
    "for f in d/*.txt; do mv \"$f\" \"${f%.txt}.md\"; done",
    B["sh-rename"][1], B["sh-rename"][3])))

# ---- git
checks.append(("git-soft", b2.g_shell("git reset --soft HEAD~1",
                                      G["git-soft"][1], G["git-soft"][3])))
checks.append(("git-uncached", b2.g_shell("git rm --cached secret.env",
                                          G["git-uncached"][1], G["git-uncached"][3])))
checks.append(("git-revert", b2.g_shell("git revert --no-edit HEAD",
                                        G["git-revert"][1], G["git-revert"][3])))

# ---- ssh config
checks.append(("ssh-jump", b2.g_sshcfg("""Host prod
    HostName 10.0.5.20
    User deploy
    Port 2222
    ProxyJump jump@bastion.example.com
""", SSH[0][2], SSH[0][3])))

# ---- yaml
checks.append(("gh-ci", b2.g_yaml("""```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pytest
```""", "workflow_ci")))

bad = 0
for name, (ok, note) in checks:
    print(f"  {'ok  ' if ok else 'BUG '} {name:<14} {note[:90]}")
    bad += 0 if ok else 1
print(f"\n{len(checks)-bad}/{len(checks)} harnesses verified" +
      ("" if not bad else f"  <-- {bad} HARNESS BUG(S)"))
