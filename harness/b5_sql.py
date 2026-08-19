#!/usr/bin/env python3
"""SQL, hard tier -- 20 tasks over a schema built to punish the easy answer.

Expected rows are DERIVED by executing the reference at build time, exactly as
the b3 tier does, so a task can never encode a hand-typed wrong answer.

What makes this set hard is the DATA, not the question length. The schema carries
deliberate hazards, and every task steps on at least one:

  * NULLs in aggregated and joined columns, where COUNT(col) and COUNT(*) differ,
    and where `NOT IN (subquery containing NULL)` returns nothing at all.
  * Duplicate and tied rows, so ROW_NUMBER, RANK and DENSE_RANK give three
    different answers and only one is being asked for.
  * Gaps in time series, so a plain GROUP BY silently omits the empty buckets the
    question asks to see.
  * A hierarchy deep enough that a self-join cannot reach the bottom -- it needs a
    recursive CTE.
  * Rows that exist on one side only, so an inner join loses them.

Every reference is fully ordered; a query whose row order is undefined is a
broken task here, not a hard one.
"""

SCHEMA = """
CREATE TABLE staff (
  id INTEGER PRIMARY KEY, name TEXT, manager_id INTEGER, dept TEXT, salary REAL);
CREATE TABLE events (
  id INTEGER PRIMARY KEY, user_id INTEGER, ts TEXT, kind TEXT);
CREATE TABLE readings (
  sensor TEXT, ts TEXT, value REAL);
CREATE TABLE ledger (
  id INTEGER PRIMARY KEY, account TEXT, ts TEXT, amount REAL, memo TEXT);
CREATE TABLE subs (
  id INTEGER PRIMARY KEY, user_id INTEGER, start TEXT, finish TEXT, plan TEXT);
CREATE TABLE users (
  id INTEGER PRIMARY KEY, name TEXT, country TEXT, referrer_id INTEGER);

-- a 5-deep chain (1 -> 2 -> 4 -> 7 -> 9) that no fixed self-join depth reaches,
-- two staff on identical salaries so RANK and ROW_NUMBER diverge,
-- and one NULL salary that must not be counted as zero
INSERT INTO staff VALUES
 (1,'Ada',NULL,'eng',200000),(2,'Ben',1,'eng',150000),(3,'Cai',1,'sales',150000),
 (4,'Dot',2,'eng',120000),(5,'Eli',2,'eng',120000),(6,'Fen',3,'sales',95000),
 (7,'Gus',4,'eng',90000),(8,'Hal',3,'sales',NULL),(9,'Ivy',7,'eng',70000),
 (10,'Jo',NULL,'ops',110000);

-- user 1 has a >30min gap that splits one day into two sessions;
-- user 3 has a single event; user 4 appears in events but not in users
INSERT INTO events VALUES
 (1,1,'2024-03-01 09:00:00','view'),(2,1,'2024-03-01 09:10:00','click'),
 (3,1,'2024-03-01 09:25:00','view'),(4,1,'2024-03-01 11:00:00','view'),
 (5,1,'2024-03-01 11:20:00','buy'),(6,2,'2024-03-01 09:05:00','view'),
 (7,2,'2024-03-02 09:05:00','view'),(8,2,'2024-03-02 09:40:00','click'),
 (9,3,'2024-03-03 14:00:00','view'),(10,4,'2024-03-03 15:00:00','view'),
 (11,1,'2024-03-04 08:00:00','view'),(12,1,'2024-03-04 08:29:00','click');

-- march 2 is missing entirely for s1; s2 has a NULL value in the middle
INSERT INTO readings VALUES
 ('s1','2024-03-01',10.0),('s1','2024-03-03',14.0),('s1','2024-03-04',12.0),
 ('s1','2024-03-05',12.0),('s2','2024-03-01',5.0),('s2','2024-03-02',NULL),
 ('s2','2024-03-03',7.0),('s2','2024-03-04',9.0),('s3','2024-03-02',1.0);

-- signed amounts; account 'C' goes negative and recovers
INSERT INTO ledger VALUES
 (1,'A','2024-01-05',100.0,'open'),(2,'A','2024-02-05',-30.0,'fee'),
 (3,'A','2024-03-05',50.0,'top up'),(4,'B','2024-01-20',200.0,'open'),
 (5,'B','2024-03-20',-200.0,'close'),(6,'C','2024-01-10',10.0,'open'),
 (7,'C','2024-01-11',-40.0,'chargeback'),(8,'C','2024-02-01',80.0,'top up'),
 (9,'A','2024-03-05',-10.0,'fee');

-- user 1 has two ADJACENT subscriptions that must merge, and one overlapping;
-- an open-ended subscription has a NULL finish
INSERT INTO subs VALUES
 (1,1,'2024-01-01','2024-01-31','basic'),(2,1,'2024-02-01','2024-02-28','pro'),
 (3,1,'2024-02-15','2024-03-10','pro'),(4,2,'2024-01-01','2024-01-10','basic'),
 (5,2,'2024-03-01','2024-03-05','basic'),(6,3,'2024-01-01',NULL,'pro');

INSERT INTO users VALUES
 (1,'Ann','UK',NULL),(2,'Bob','US',1),(3,'Cid','UK',1),(5,'Eve','DE',2),
 (6,'Fay','DE',NULL);
"""

CTX = ("Schema (SQLite):\n" + SCHEMA.strip() +
       "\n\nColumn names in the result must match any the task names. ")

# (id, ask, reference)
T = [

 ("hsql-001",
  "for every member of staff, their name and the name of the most senior person above them in "
  "the reporting chain (the root of their chain), plus their depth below that root where the root "
  "itself is depth 0; name the columns name, root, depth; ordered by root then depth then name",
  "WITH RECURSIVE chain(id,name,root,depth) AS ("
  " SELECT id,name,name,0 FROM staff WHERE manager_id IS NULL"
  " UNION ALL"
  " SELECT s.id,s.name,c.root,c.depth+1 FROM staff s JOIN chain c ON s.manager_id=c.id)"
  " SELECT name,root,depth FROM chain ORDER BY root,depth,name"),

 ("hsql-002",
  "the name and salary of every member of staff whose salary is strictly greater than the average "
  "salary of their own department, where the average ignores staff with no recorded salary; "
  "ordered by salary descending then name",
  "SELECT s.name,s.salary FROM staff s WHERE s.salary > "
  "(SELECT AVG(x.salary) FROM staff x WHERE x.dept=s.dept AND x.salary IS NOT NULL) "
  "ORDER BY s.salary DESC, s.name"),

 ("hsql-003",
  "each department with its headcount, the number of staff with a recorded salary, and the total "
  "payroll; a department where nobody has a recorded salary must show 0 payroll rather than NULL; "
  "name the columns dept, headcount, paid, payroll; ordered by dept",
  "SELECT dept, COUNT(*) AS headcount, COUNT(salary) AS paid, "
  "COALESCE(SUM(salary),0) AS payroll FROM staff GROUP BY dept ORDER BY dept"),

 ("hsql-004",
  "the second-highest distinct salary in each department, as dept and salary; departments with "
  "fewer than two distinct salaries are omitted; ordered by dept",
  "WITH d AS (SELECT DISTINCT dept,salary FROM staff WHERE salary IS NOT NULL), "
  "r AS (SELECT dept,salary,ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC) rn FROM d) "
  "SELECT dept,salary FROM r WHERE rn=2 ORDER BY dept"),

 ("hsql-005",
  "for each user in the events table, the number of distinct sessions they had, where a new "
  "session starts whenever more than 30 minutes pass since that user's previous event; name the "
  "columns user_id, sessions; ordered by user_id",
  "WITH g AS (SELECT user_id, ts, CASE WHEN LAG(ts) OVER (PARTITION BY user_id ORDER BY ts) IS NULL "
  "OR (julianday(ts)-julianday(LAG(ts) OVER (PARTITION BY user_id ORDER BY ts)))*1440.0 > 30 "
  "THEN 1 ELSE 0 END AS newsess FROM events) "
  "SELECT user_id, SUM(newsess) AS sessions FROM g GROUP BY user_id ORDER BY user_id"),

 ("hsql-006",
  "a running balance per account: account, ts, amount and the cumulative sum of amount up to and "
  "including that row ordered by ts then id; name the cumulative column balance; ordered by "
  "account then ts then id",
  "SELECT account, ts, amount, SUM(amount) OVER (PARTITION BY account ORDER BY ts, id "
  "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS balance "
  "FROM ledger ORDER BY account, ts, id"),

 ("hsql-007",
  "every account whose running balance ever went strictly below zero, with the earliest ts at "
  "which that happened; name the columns account, ts; ordered by account",
  "WITH b AS (SELECT account, ts, id, SUM(amount) OVER (PARTITION BY account ORDER BY ts, id "
  "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS bal FROM ledger) "
  "SELECT account, MIN(ts) AS ts FROM b WHERE bal < 0 GROUP BY account ORDER BY account"),

 ("hsql-008",
  "one row per calendar date from 2024-03-01 to 2024-03-05 inclusive for sensor s1, as ts and "
  "value, where a date with no reading shows NULL; ordered by ts",
  "WITH RECURSIVE d(ts) AS (SELECT '2024-03-01' UNION ALL "
  "SELECT date(ts,'+1 day') FROM d WHERE ts < '2024-03-05') "
  "SELECT d.ts, r.value FROM d LEFT JOIN readings r ON r.ts=d.ts AND r.sensor='s1' ORDER BY d.ts"),

 ("hsql-009",
  "for sensor s2, each ts and its value with any NULL value replaced by the most recent earlier "
  "non-null value for that sensor (last observation carried forward); name the columns ts, value; "
  "ordered by ts",
  "SELECT ts, COALESCE(value,(SELECT r2.value FROM readings r2 WHERE r2.sensor=r.sensor "
  "AND r2.ts<r.ts AND r2.value IS NOT NULL ORDER BY r2.ts DESC LIMIT 1)) AS value "
  "FROM readings r WHERE r.sensor='s2' ORDER BY ts"),

 ("hsql-010",
  "the maximal merged subscription periods per user, treating two periods as one when they "
  "overlap OR merely touch end-to-start on consecutive days, and treating a NULL finish as "
  "9999-12-31; name the columns user_id, start, finish; ordered by user_id then start",
  "WITH s AS (SELECT user_id, start, COALESCE(finish,'9999-12-31') AS finish FROM subs), "
  "m AS (SELECT user_id, start, finish, CASE WHEN start <= date(MAX(finish) OVER "
  "(PARTITION BY user_id ORDER BY start, finish ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),"
  "'+1 day') THEN 0 ELSE 1 END AS isnew FROM s), "
  "g AS (SELECT user_id, start, finish, SUM(isnew) OVER (PARTITION BY user_id ORDER BY start, finish "
  "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS grp FROM m) "
  "SELECT user_id, MIN(start) AS start, MAX(finish) AS finish FROM g GROUP BY user_id, grp "
  "ORDER BY user_id, start"),

 ("hsql-011",
  "the names of users who have never appeared in the events table, alphabetically; note that the "
  "events table contains a user id that is not in users, and that some users have no events at all",
  "SELECT name FROM users WHERE id NOT IN (SELECT user_id FROM events WHERE user_id IS NOT NULL) "
  "ORDER BY name"),

 ("hsql-012",
  "user ids present in events but absent from the users table, and separately user ids present in "
  "users but absent from events; return id and a side column that is 'events_only' or "
  "'users_only'; ordered by side then id",
  "SELECT DISTINCT e.user_id AS id, 'events_only' AS side FROM events e "
  "LEFT JOIN users u ON u.id=e.user_id WHERE u.id IS NULL "
  "UNION ALL "
  "SELECT u.id, 'users_only' FROM users u LEFT JOIN events e ON e.user_id=u.id "
  "WHERE e.id IS NULL ORDER BY side, id"),

 ("hsql-013",
  "each staff member's name, salary and their dense rank by salary within their department with "
  "the highest salary ranked 1, excluding staff with no recorded salary; tied salaries share a "
  "rank and the next rank is not skipped; name the rank column rnk; ordered by dept, rnk, name",
  "SELECT name, salary, DENSE_RANK() OVER (PARTITION BY dept ORDER BY salary DESC) AS rnk "
  "FROM staff WHERE salary IS NOT NULL ORDER BY dept, rnk, name"),

 ("hsql-014",
  "for each department the difference between that department's highest salary and the highest "
  "salary of the department ranked immediately above it by highest salary; the top department "
  "shows NULL; name the columns dept, top_salary, gap; ordered by top_salary descending",
  "WITH d AS (SELECT dept, MAX(salary) AS top_salary FROM staff WHERE salary IS NOT NULL GROUP BY dept) "
  "SELECT dept, top_salary, LAG(top_salary) OVER (ORDER BY top_salary DESC) - top_salary AS gap "
  "FROM d ORDER BY top_salary DESC"),

 ("hsql-015",
  "one row per user_id in events giving the kind of their first event and the kind of their last "
  "event by ts; name the columns user_id, first_kind, last_kind; ordered by user_id",
  "WITH r AS (SELECT user_id, ts, kind, "
  "ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY ts) AS a, "
  "ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY ts DESC) AS b FROM events) "
  "SELECT user_id, MAX(CASE WHEN a=1 THEN kind END) AS first_kind, "
  "MAX(CASE WHEN b=1 THEN kind END) AS last_kind FROM r GROUP BY user_id ORDER BY user_id"),

 ("hsql-016",
  "a pivot of the events table: one row per user_id with a count column per kind named view, "
  "click and buy, counting zero where that kind never occurred; ordered by user_id",
  "SELECT user_id, SUM(kind='view') AS view, SUM(kind='click') AS click, "
  "SUM(kind='buy') AS buy FROM events GROUP BY user_id ORDER BY user_id"),

 ("hsql-017",
  "the longest run of consecutive calendar days on which sensor s1 has a reading, as sensor, "
  "start, finish and days; ordered by sensor",
  "WITH r AS (SELECT sensor, ts, julianday(ts) - ROW_NUMBER() OVER "
  "(PARTITION BY sensor ORDER BY ts) AS grp FROM readings WHERE sensor='s1'), "
  "g AS (SELECT sensor, MIN(ts) AS start, MAX(ts) AS finish, COUNT(*) AS days "
  "FROM r GROUP BY sensor, grp) "
  "SELECT sensor, start, finish, days FROM g WHERE days=(SELECT MAX(days) FROM g) ORDER BY sensor"),

 ("hsql-018",
  "every user with the name of the user who referred them, including users with no referrer, who "
  "show NULL; name the columns name, referrer; ordered by name",
  "SELECT u.name, r.name AS referrer FROM users u LEFT JOIN users r ON r.id=u.referrer_id "
  "ORDER BY u.name"),

 ("hsql-019",
  "each account with its total, the number of entries, and that account's share of the grand "
  "total of all amounts as a percentage rounded to two decimal places; name the columns account, "
  "total, n, pct; ordered by account",
  "SELECT account, SUM(amount) AS total, COUNT(*) AS n, "
  "ROUND(100.0*SUM(amount)/(SELECT SUM(amount) FROM ledger),2) AS pct "
  "FROM ledger GROUP BY account ORDER BY account"),

 ("hsql-020",
  "the direct and indirect report count for every manager, where an indirect report is anyone "
  "further down the chain; return name and reports for staff who have at least one report; "
  "ordered by reports descending then name",
  "WITH RECURSIVE d(root,id) AS ("
  " SELECT manager_id,id FROM staff WHERE manager_id IS NOT NULL"
  " UNION ALL"
  " SELECT d.root,s.id FROM staff s JOIN d ON s.manager_id=d.id) "
  "SELECT st.name, COUNT(*) AS reports FROM d JOIN staff st ON st.id=d.root "
  "GROUP BY d.root ORDER BY reports DESC, st.name"),
]


def build():
    """Derive expected rows by executing each reference query."""
    import sqlite3
    out, broken = [], []
    for tid, ask, ref in T:
        con = sqlite3.connect(":memory:")
        try:
            con.executescript(SCHEMA)
            rows = con.execute(ref).fetchall()
            if not rows:
                broken.append((tid, "reference returned zero rows"))
                continue
            out.append((tid, CTX + "Write one SQL query returning " + ask +
                        ". Output only the SQL.", rows))
        except Exception as e:  # noqa: BLE001
            broken.append((tid, f"{type(e).__name__}: {e}"))
        finally:
            con.close()
    return out, broken


if __name__ == "__main__":
    ok, bad = build()
    print("hard SQL tasks built: %d/%d" % (len(ok), len(T)))
    for tid, why in bad:
        print("  BROKEN %s: %s" % (tid, why))
