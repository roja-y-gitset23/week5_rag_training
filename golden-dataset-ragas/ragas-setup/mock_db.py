import sqlite3

EMPLOYEES = [
    ("E101", "Priya Sharma", "Engineering", 95000, "Bengaluru"),
    ("E102", "Rahul Verma", "Engineering", 88000, "Hyderabad"),
    ("E103", "Anita Desai", "HR", 62000, "Mumbai"),
    ("E104", "Vikram Singh", "Finance", 74000, "Delhi"),
    ("E105", "Meera Nair", "Marketing", 68000, "Kochi"),
    ("E106", "Arjun Reddy", "Sales", 71000, "Chennai"),
    ("E107", "Sana Khan", "Engineering", 99000, "Pune"),
    ("E108", "Karan Mehta", "Sales", 66000, "Ahmedabad"),
]


def get_connection():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE employees (emp_id TEXT, name TEXT, department TEXT, salary INTEGER, city TEXT)"
    )
    conn.executemany("INSERT INTO employees VALUES (?,?,?,?,?)", EMPLOYEES)
    conn.commit()
    return conn


def rows_as_text():
    conn = get_connection()
    rows = conn.execute("SELECT emp_id, name, department, salary, city FROM employees").fetchall()
    conn.close()
    return [
        f"Employee {r[0]}: name={r[1]}, department={r[2]}, salary={r[3]} INR, city={r[4]}"
        for r in rows
    ]