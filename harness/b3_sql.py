#!/usr/bin/env python3
"""SQL category — 50 tasks over one richer schema.

Every task ships a reference query. Expected rows are DERIVED by executing the
reference at build time, so a task can never encode a hand-typed wrong answer.
`verify()` additionally re-runs each reference through the real grader.
"""

SCHEMA = """
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, country TEXT, signup TEXT, tier TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, total REAL, created TEXT, status TEXT);
CREATE TABLE items (id INTEGER PRIMARY KEY, order_id INTEGER, product TEXT, category TEXT, qty INTEGER, price REAL);
CREATE TABLE refunds (id INTEGER PRIMARY KEY, order_id INTEGER, amount REAL, reason TEXT);
CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT, manager_id INTEGER, dept TEXT, salary REAL);

INSERT INTO customers VALUES
 (1,'Ann','UK','2023-01-05','gold'),(2,'Bob','US','2023-06-11','silver'),
 (3,'Cid','UK','2024-02-20','silver'),(4,'Dee','US','2024-03-02','gold'),
 (5,'Eve','DE','2023-11-30','bronze'),(6,'Fay','DE','2024-05-14','silver');

INSERT INTO orders VALUES
 (1,1,100.0,'2024-01-15','shipped'),(2,1,50.0,'2024-02-10','shipped'),
 (3,2,200.0,'2024-01-20','shipped'),(4,2,25.0,'2024-03-05','cancelled'),
 (5,3,75.0,'2024-02-28','shipped'),(6,4,300.0,'2024-03-18','pending'),
 (7,4,120.0,'2024-04-02','shipped'),(8,1,80.0,'2024-04-22','pending'),
 (9,5,50.0,'2024-05-01','shipped'),(10,3,60.0,'2024-05-19','cancelled'),
 -- order 11 deliberately has no item rows, and is a second January order for customer 1
 (11,1,90.0,'2024-01-28','shipped');

INSERT INTO items VALUES
 (1,1,'widget','tools',2,25.0),(2,1,'gizmo','tools',1,50.0),
 (3,2,'book','media',5,10.0),(4,3,'widget','tools',4,25.0),
 (5,3,'film','media',2,50.0),(6,4,'book','media',1,25.0),
 (7,5,'gizmo','tools',1,75.0),(8,6,'widget','tools',6,25.0),
 (9,6,'kit','tools',3,50.0),(10,7,'film','media',2,60.0),
 (11,8,'book','media',8,10.0),(12,9,'gizmo','tools',1,45.0),
 (13,10,'kit','tools',1,60.0),(14,7,'widget','tools',0,25.0),
 -- 'sticker' is only ever sold at qty 0; 'kit' appears under two categories
 (15,7,'sticker','media',0,5.0),(16,8,'kit','media',1,20.0);

INSERT INTO refunds VALUES
 (1,2,20.0,'damaged'),(2,4,25.0,'cancelled'),(3,7,60.0,'wrong item'),(4,10,60.0,'cancelled');

INSERT INTO employees VALUES
 (1,'Root',NULL,'exec',200000),(2,'Mia',1,'eng',150000),(3,'Ned',2,'eng',120000),
 (4,'Ola',2,'eng',110000),(5,'Pim',1,'sales',130000),(6,'Quy',5,'sales',90000),
 (7,'Rex',3,'eng',95000);
"""

CTX = ("Given this SQLite schema:\n\n```sql\n"
       "customers(id, name, country, signup, tier)      -- signup is 'YYYY-MM-DD'\n"
       "orders(id, customer_id, total, created, status) -- created 'YYYY-MM-DD'; status shipped|pending|cancelled\n"
       "items(id, order_id, product, category, qty, price)\n"
       "refunds(id, order_id, amount, reason)\n"
       "employees(id, name, manager_id, dept, salary)   -- manager_id is a self-reference\n"
       "```\n\n")

# (id, question, reference SQL)  -- expected rows derived from the reference
T = [
 ("sql-001", "customer names and their total order value as revenue, for customers whose total "
  "exceeds 100, ordered by revenue descending",
  "SELECT c.name, SUM(o.total) AS revenue FROM customers c JOIN orders o ON o.customer_id=c.id "
  "GROUP BY c.id HAVING SUM(o.total)>100 ORDER BY revenue DESC"),
 ("sql-002", "names of customers who have never placed an order, alphabetically",
  "SELECT name FROM customers WHERE id NOT IN (SELECT customer_id FROM orders) ORDER BY name"),
 ("sql-003", "for each category, the single product with the highest total quantity sold; "
  "return category, product, qty ordered by category",
  "WITH t AS (SELECT category, product, SUM(qty) qty, "
  "ROW_NUMBER() OVER (PARTITION BY category ORDER BY SUM(qty) DESC, product) rn "
  "FROM items GROUP BY category, product) "
  "SELECT category, product, qty FROM t WHERE rn=1 ORDER BY category"),
 ("sql-004", "year-month as 'YYYY-MM' and the sum of order totals per month, chronologically; "
  "name the columns month and total",
  "SELECT substr(created,1,7) AS month, SUM(total) AS total FROM orders GROUP BY month ORDER BY month"),
 ("sql-005", "country and number of orders placed by customers from it, only where that count "
  "exceeds 2; name the columns country and n",
  "SELECT c.country, COUNT(o.id) AS n FROM customers c JOIN orders o ON o.customer_id=c.id "
  "GROUP BY c.country HAVING COUNT(o.id)>2 ORDER BY c.country"),
 ("sql-006", "using a CTE, each customer's name and their single largest order as biggest, "
  "for customers who have ordered, ordered by biggest descending",
  "WITH m AS (SELECT customer_id, MAX(total) biggest FROM orders GROUP BY customer_id) "
  "SELECT c.name, m.biggest FROM m JOIN customers c ON c.id=m.customer_id ORDER BY m.biggest DESC"),
 ("sql-007", "total refunded amount per order, for orders with any refund; columns order_id, refunded, "
  "ordered by order_id",
  "SELECT order_id, SUM(amount) AS refunded FROM refunds GROUP BY order_id ORDER BY order_id"),
 ("sql-008", "net revenue per customer, defined as total orders minus total refunds on those orders; "
  "columns name, net; only customers with orders; ordered by net descending",
  "SELECT c.name, SUM(o.total) - COALESCE((SELECT SUM(r.amount) FROM refunds r "
  "JOIN orders o2 ON o2.id=r.order_id WHERE o2.customer_id=c.id),0) AS net "
  "FROM customers c JOIN orders o ON o.customer_id=c.id GROUP BY c.id ORDER BY net DESC"),
 ("sql-009", "orders whose status is not 'cancelled', with customer name and total, ordered by total descending",
  "SELECT c.name, o.total FROM orders o JOIN customers c ON c.id=o.customer_id "
  "WHERE o.status<>'cancelled' ORDER BY o.total DESC"),
 ("sql-010", "count of orders by status; columns status, n, ordered by status",
  "SELECT status, COUNT(*) AS n FROM orders GROUP BY status ORDER BY status"),
 ("sql-011", "the average order total per customer tier; columns tier, avg_total, rounded to 2 decimals, "
  "ordered by tier",
  "SELECT c.tier, ROUND(AVG(o.total),2) AS avg_total FROM customers c JOIN orders o ON o.customer_id=c.id "
  "GROUP BY c.tier ORDER BY c.tier"),
 ("sql-012", "products never sold in any order item with quantity greater than zero; column product, alphabetical",
  "SELECT DISTINCT product FROM items WHERE product NOT IN "
  "(SELECT product FROM items WHERE qty>0) ORDER BY product"),
 ("sql-013", "the line revenue (qty*price) per order; columns order_id, line_total, ordered by order_id",
  "SELECT order_id, SUM(qty*price) AS line_total FROM items GROUP BY order_id ORDER BY order_id"),
 ("sql-014", "orders where the sum of item line revenue does not equal the order total; "
  "columns order_id, total, line_total, ordered by order_id",
  "SELECT o.id AS order_id, o.total, SUM(i.qty*i.price) AS line_total FROM orders o "
  "JOIN items i ON i.order_id=o.id GROUP BY o.id HAVING SUM(i.qty*i.price)<>o.total ORDER BY o.id"),
 ("sql-015", "each employee and their manager's name; columns employee, manager; employees with no "
  "manager show NULL; ordered by employee",
  "SELECT e.name AS employee, m.name AS manager FROM employees e "
  "LEFT JOIN employees m ON m.id=e.manager_id ORDER BY e.name"),
 ("sql-016", "using a recursive CTE, every employee reporting directly or indirectly to 'Mia'; "
  "column name, alphabetical",
  "WITH RECURSIVE d(id) AS (SELECT id FROM employees WHERE name='Mia' "
  "UNION ALL SELECT e.id FROM employees e JOIN d ON e.manager_id=d.id) "
  "SELECT name FROM employees WHERE id IN (SELECT id FROM d) AND name<>'Mia' ORDER BY name"),
 ("sql-017", "department headcount and total salary; columns dept, n, payroll, ordered by payroll descending",
  "SELECT dept, COUNT(*) AS n, SUM(salary) AS payroll FROM employees GROUP BY dept ORDER BY payroll DESC"),
 ("sql-018", "employees earning more than the average salary of their own department; "
  "columns name, dept, salary, ordered by name",
  "SELECT name, dept, salary FROM employees e WHERE salary > "
  "(SELECT AVG(salary) FROM employees x WHERE x.dept=e.dept) ORDER BY name"),
 ("sql-019", "rank employees by salary descending within each department; columns dept, name, salary, rnk; "
  "ordered by dept then rnk",
  "SELECT dept, name, salary, RANK() OVER (PARTITION BY dept ORDER BY salary DESC) AS rnk "
  "FROM employees ORDER BY dept, rnk, name"),
 ("sql-020", "the running total of order values ordered by created date; columns created, total, running; "
  "ordered by created",
  "SELECT created, total, SUM(total) OVER (ORDER BY created, id) AS running FROM orders ORDER BY created, id"),
 ("sql-021", "customers who signed up in 2024; columns name, signup, ordered by signup",
  "SELECT name, signup FROM customers WHERE signup>='2024-01-01' AND signup<'2025-01-01' ORDER BY signup"),
 ("sql-022", "the number of distinct products in each category; columns category, n, ordered by category",
  "SELECT category, COUNT(DISTINCT product) AS n FROM items GROUP BY category ORDER BY category"),
 ("sql-023", "total quantity sold per product across all orders; columns product, qty, ordered by qty "
  "descending then product",
  "SELECT product, SUM(qty) AS qty FROM items GROUP BY product ORDER BY qty DESC, product"),
 ("sql-024", "the most recent order per customer; columns name, created, total; ordered by name",
  "WITH r AS (SELECT customer_id, id, created, total, "
  "ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created DESC, id DESC) rn FROM orders) "
  "SELECT c.name, r.created, r.total FROM r JOIN customers c ON c.id=r.customer_id WHERE rn=1 ORDER BY c.name"),
 ("sql-025", "customers with more than one order; columns name, n, ordered by n descending then name",
  "SELECT c.name, COUNT(o.id) AS n FROM customers c JOIN orders o ON o.customer_id=c.id "
  "GROUP BY c.id HAVING COUNT(o.id)>1 ORDER BY n DESC, c.name"),
 ("sql-026", "the percentage of orders that were cancelled, as a single row column pct rounded to 1 decimal",
  "SELECT ROUND(100.0*SUM(CASE WHEN status='cancelled' THEN 1 ELSE 0 END)/COUNT(*),1) AS pct FROM orders"),
 ("sql-027", "for each country, the highest single order total; columns country, best, ordered by best descending",
  "SELECT c.country, MAX(o.total) AS best FROM customers c JOIN orders o ON o.customer_id=c.id "
  "GROUP BY c.country ORDER BY best DESC"),
 ("sql-028", "refund reasons and how many refunds cite each; columns reason, n, ordered by n descending then reason",
  "SELECT reason, COUNT(*) AS n FROM refunds GROUP BY reason ORDER BY n DESC, reason"),
 ("sql-029", "orders that have items in more than one category; columns order_id, n_categories, ordered by order_id",
  "SELECT order_id, COUNT(DISTINCT category) AS n_categories FROM items GROUP BY order_id "
  "HAVING COUNT(DISTINCT category)>1 ORDER BY order_id"),
 ("sql-030", "the average number of days between a customer's signup and their first order; "
  "single column avg_days rounded to 1 decimal",
  "SELECT ROUND(AVG(julianday(f.first)-julianday(c.signup)),1) AS avg_days FROM customers c "
  "JOIN (SELECT customer_id, MIN(created) first FROM orders GROUP BY customer_id) f ON f.customer_id=c.id"),
 ("sql-031", "gold tier customers and their order count including those with zero orders; "
  "columns name, n, ordered by name",
  "SELECT c.name, COUNT(o.id) AS n FROM customers c LEFT JOIN orders o ON o.customer_id=c.id "
  "WHERE c.tier='gold' GROUP BY c.id ORDER BY c.name"),
 ("sql-032", "the single product generating the most line revenue; columns product, revenue",
  "SELECT product, SUM(qty*price) AS revenue FROM items GROUP BY product ORDER BY revenue DESC, product LIMIT 1"),
 ("sql-033", "months in which more than 2 orders were placed; columns month, n, ordered by month",
  "SELECT substr(created,1,7) AS month, COUNT(*) AS n FROM orders GROUP BY month HAVING COUNT(*)>2 ORDER BY month"),
 ("sql-034", "each order with a flag refunded set to 1 if any refund exists for it else 0; "
  "columns id, refunded, ordered by id",
  "SELECT o.id, CASE WHEN EXISTS (SELECT 1 FROM refunds r WHERE r.order_id=o.id) THEN 1 ELSE 0 END "
  "AS refunded FROM orders o ORDER BY o.id"),
 ("sql-035", "customers whose every order is shipped; column name, alphabetical",
  "SELECT c.name FROM customers c JOIN orders o ON o.customer_id=c.id GROUP BY c.id "
  "HAVING SUM(CASE WHEN o.status<>'shipped' THEN 1 ELSE 0 END)=0 ORDER BY c.name"),
 ("sql-036", "the difference between each order total and the average order total; "
  "columns id, total, delta rounded to 2 decimals, ordered by id",
  "SELECT id, total, ROUND(total-(SELECT AVG(total) FROM orders),2) AS delta FROM orders ORDER BY id"),
 ("sql-037", "item rows with a quantity of zero; columns id, order_id, product, ordered by id",
  "SELECT id, order_id, product FROM items WHERE qty=0 ORDER BY id"),
 ("sql-038", "the top 3 orders by total; columns id, total, ordered by total descending",
  "SELECT id, total FROM orders ORDER BY total DESC, id LIMIT 3"),
 ("sql-039", "for each tier, how many customers and their average order count; "
  "columns tier, customers, avg_orders rounded to 2 decimals, ordered by tier",
  "SELECT t.tier, COUNT(*) AS customers, ROUND(AVG(t.n),2) AS avg_orders FROM "
  "(SELECT c.id, c.tier, COUNT(o.id) n FROM customers c LEFT JOIN orders o ON o.customer_id=c.id "
  "GROUP BY c.id) t GROUP BY t.tier ORDER BY t.tier"),
 ("sql-040", "products sold in both the tools and media categories; column product, alphabetical",
  "SELECT product FROM items WHERE category='tools' INTERSECT "
  "SELECT product FROM items WHERE category='media' ORDER BY product"),
 ("sql-041", "the second highest order total as a single column second_highest",
  "SELECT DISTINCT total AS second_highest FROM orders ORDER BY total DESC LIMIT 1 OFFSET 1"),
 ("sql-042", "each customer's share of total revenue as a percentage rounded to 1 decimal; "
  "columns name, pct, ordered by pct descending",
  "SELECT c.name, ROUND(100.0*SUM(o.total)/(SELECT SUM(total) FROM orders),1) AS pct "
  "FROM customers c JOIN orders o ON o.customer_id=c.id GROUP BY c.id ORDER BY pct DESC"),
 ("sql-043", "orders placed in the same month as another order by the same customer; "
  "columns customer_id, month, n, only where n>1, ordered by customer_id",
  "SELECT customer_id, substr(created,1,7) AS month, COUNT(*) AS n FROM orders "
  "GROUP BY customer_id, month HAVING COUNT(*)>1 ORDER BY customer_id, month"),
 ("sql-044", "employees who manage at least one other employee; columns name, reports, "
  "ordered by reports descending then name",
  "SELECT m.name, COUNT(e.id) AS reports FROM employees m JOIN employees e ON e.manager_id=m.id "
  "GROUP BY m.id ORDER BY reports DESC, m.name"),
 ("sql-045", "the median-ish value: the highest salary that is below the overall average salary; "
  "single column salary",
  "SELECT MAX(salary) AS salary FROM employees WHERE salary < (SELECT AVG(salary) FROM employees)"),
 ("sql-046", "categories whose total line revenue exceeds 200; columns category, revenue, "
  "ordered by revenue descending",
  "SELECT category, SUM(qty*price) AS revenue FROM items GROUP BY category "
  "HAVING SUM(qty*price)>200 ORDER BY revenue DESC"),
 ("sql-047", "customers who ordered in both January and February 2024; column name, alphabetical",
  "SELECT DISTINCT c.name FROM customers c JOIN orders a ON a.customer_id=c.id AND substr(a.created,1,7)='2024-01' "
  "JOIN orders b ON b.customer_id=c.id AND substr(b.created,1,7)='2024-02' ORDER BY c.name"),
 ("sql-048", "the change in each order total versus the customer's previous order, in date order; "
  "columns customer_id, created, total, delta (NULL for the first), ordered by customer_id then created",
  "SELECT customer_id, created, total, total - LAG(total) OVER "
  "(PARTITION BY customer_id ORDER BY created, id) AS delta FROM orders ORDER BY customer_id, created, id"),
 ("sql-049", "how many orders each country produced per status; columns country, status, n, "
  "ordered by country then status",
  "SELECT c.country, o.status, COUNT(*) AS n FROM customers c JOIN orders o ON o.customer_id=c.id "
  "GROUP BY c.country, o.status ORDER BY c.country, o.status"),
 ("sql-050", "orders with no items at all; column id, ordered by id",
  "SELECT o.id FROM orders o LEFT JOIN items i ON i.order_id=o.id WHERE i.id IS NULL ORDER BY o.id"),
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
    print(f"SQL tasks built: {len(ok)}/{len(T)}")
    for tid, why in bad:
        print(f"  BROKEN {tid}: {why}")
