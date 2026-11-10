"""Mock HR database (employees, leaves, payslips) + 3 safe tool functions."""
import os
import re
import sqlite3
from pathlib import Path

DB_FILE = Path("mock_hr.db")
PG_DSN = os.getenv("PG_DSN")  # set only if you want real PostgreSQL


def _connect():
    if PG_DSN:
        import psycopg2
        return psycopg2.connect(PG_DSN)
    return sqlite3.connect(DB_FILE)


def _sql(sql):
    # sqlite uses ?, PostgreSQL (psycopg2) uses %s
    return sql.replace("?", "%s") if PG_DSN else sql


def run_query(sql, params=()):
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(sql), params)
        return cur.fetchall()
    finally:
        conn.close()


# ---------------- sample data ----------------
EMPLOYEES = [
    (1, "Asha Rao", "HR", "HR Executive", "2020-03-15"),
    (2, "Ravi Kumar", "Engineering", "Software Engineer", "2019-07-01"),
    (3, "Meena Iyer", "Engineering", "Senior Engineer", "2018-01-10"),
    (4, "Suresh Babu", "Sales", "Sales Manager", "2021-05-20"),
    (5, "Divya Nair", "Finance", "Accountant", "2022-02-14"),
    (6, "Arjun Reddy", "Engineering", "QA Engineer", "2023-09-04"),
    (7, "Kavya Menon", "Support", "Support Lead", "2020-11-23"),
    (8, "Imran Khan", "Sales", "Sales Executive", "2022-08-08"),
    (9, "Lakshmi Devi", "HR", "HR Manager", "2017-04-17"),
    (10, "Rohit Sharma", "Engineering", "DevOps Engineer", "2024-01-29"),
]
QUOTA = {"Annual": 18, "Sick": 12, "Casual": 6}
USED = {  # emp_id: (annual, sick, casual) days already used
    1: (3, 1, 0), 2: (4, 3, 2), 3: (5, 2, 1), 4: (2, 0, 1), 5: (6, 1, 2),
    6: (0, 0, 0), 7: (7, 4, 1), 8: (1, 2, 0), 9: (3, 3, 3), 10: (2, 1, 1),
}
MONTHS = ("2026-08", "2026-09", "2026-10")


def setup_db():
    conn = _connect()
    try:
        cur = conn.cursor()
        for t in ("payslips", "leaves", "employees"):
            cur.execute(f"DROP TABLE IF EXISTS {t}")
        cur.execute("""CREATE TABLE employees (
            emp_id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            department VARCHAR(50) NOT NULL,
            role VARCHAR(50),
            join_date DATE)""")
        cur.execute("""CREATE TABLE leaves (
            leave_id INTEGER PRIMARY KEY,
            emp_id INTEGER REFERENCES employees(emp_id),
            leave_type VARCHAR(20),
            quota INTEGER,
            used INTEGER)""")
        cur.execute("""CREATE TABLE payslips (
            payslip_id INTEGER PRIMARY KEY,
            emp_id INTEGER REFERENCES employees(emp_id),
            pay_month VARCHAR(7),
            basic INTEGER,
            hra INTEGER,
            deductions INTEGER,
            net_pay INTEGER)""")

        for row in EMPLOYEES:
            cur.execute(_sql("INSERT INTO employees VALUES (?,?,?,?,?)"), row)

        leave_id = 1
        for emp_id, used in USED.items():
            for (ltype, quota), u in zip(QUOTA.items(), used):
                cur.execute(_sql("INSERT INTO leaves VALUES (?,?,?,?,?)"),
                            (leave_id, emp_id, ltype, quota, u))
                leave_id += 1

        payslip_id = 1
        for emp_id, *_ in EMPLOYEES:
            basic = 30000 + 5000 * emp_id
            hra = basic * 40 // 100
            ded = basic * 12 // 100
            for month in MONTHS:
                cur.execute(_sql("INSERT INTO payslips VALUES (?,?,?,?,?,?,?)"),
                            (payslip_id, emp_id, month, basic, hra, ded, basic + hra - ded))
                payslip_id += 1
        conn.commit()
    finally:
        conn.close()


# ---------------- 3 safe tools (parameterised SQL, read-only) ----------------
def get_leave_balance(emp_id):
    if emp_id is None:
        return {"error": "Please give an employee id, e.g. 'employee 3'."}
    rows = run_query(
        "SELECT e.name, l.leave_type, l.quota - l.used "
        "FROM leaves l JOIN employees e ON e.emp_id = l.emp_id "
        "WHERE l.emp_id = ? ORDER BY l.leave_id", (int(emp_id),))
    if not rows:
        return {"error": f"No leave record for employee {emp_id}."}
    balances = {r[1]: r[2] for r in rows}
    return {"emp_id": int(emp_id), "name": rows[0][0],
            "balances": balances, "total": sum(balances.values()),
            "tables": "leaves, employees"}


def get_payslip(emp_id, month):
    if emp_id is None or not month:
        return {"error": "Please give an employee id and a month like 2026-09."}
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        return {"error": "Month must look like 2026-09."}
    rows = run_query(
        "SELECT e.name, p.basic, p.hra, p.deductions, p.net_pay "
        "FROM payslips p JOIN employees e ON e.emp_id = p.emp_id "
        "WHERE p.emp_id = ? AND p.pay_month = ?", (int(emp_id), month))
    if not rows:
        return {"error": f"No payslip for employee {emp_id} in {month}."}
    name, basic, hra, ded, net = rows[0]
    return {"emp_id": int(emp_id), "name": name, "month": month, "basic": basic,
            "hra": hra, "deductions": ded, "net_pay": net,
            "tables": "payslips, employees"}


def count_employees(department=None):
    if department:
        rows = run_query(
            "SELECT COUNT(*) FROM employees WHERE LOWER(department) = LOWER(?)",
            (department,))
    else:
        rows = run_query("SELECT COUNT(*) FROM employees")
    return {"department": department or "all departments", "count": rows[0][0],
            "tables": "employees"}


TOOLS = {  # whitelist: only these 3 can ever run
    "get_leave_balance": get_leave_balance,
    "get_payslip": get_payslip,
    "count_employees": count_employees,
}


def call_tool(name, **args):
    if name not in TOOLS:
        return {"error": f"Tool '{name}' is not allowed."}
    return TOOLS[name](**args)


if __name__ == "__main__":
    setup_db()
    print("Mock database created with employees, leaves, payslips.")