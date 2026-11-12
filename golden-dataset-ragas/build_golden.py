"""Creates sample data (PDFs, CSV, SQLite) and builds golden_30.jsonl"""
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

BASE = Path(__file__).parent
PDF_DIR = BASE / "data" / "pdfs"
CSV_PATH = BASE / "data" / "csv" / "products.csv"
DB_PATH = BASE / "data" / "mock_db.sqlite"
OUT = BASE / "golden_30.jsonl"
IDK = "I don't know"

# Each page = list of (sentence, question, ground_truth, key_that_must_appear_on_page)
# question=None means filler text (no question asked about it)
PDF_SPEC = {
    "hr_policy.pdf": [
        [("Acme Corp HR Policy Handbook. This handbook explains leave and employment rules for all staff.", None, None, None),
         ("Full-time employees receive 20 days of paid annual leave per calendar year.",
          "How many days of paid annual leave do full-time employees receive per calendar year?", "20 days", "20 days"),
         ("The standard probation period for new hires is 90 days.",
          "How long is the standard probation period for new hires?", "90 days", "90 days")],
        [("Remote work arrangements are reviewed by the line manager every quarter.", None, None, None),
         ("Employees may work remotely up to 3 days per week with manager approval.",
          "How many days per week may employees work remotely with manager approval?", "Up to 3 days per week", "3 days per week")],
        [("All HR policies are owned by the Human Resources department.", None, None, None),
         ("Performance reviews are held twice a year, in June and December.",
          "When are performance reviews held?", "Twice a year, in June and December", "June and December")],
    ],
    "it_security_policy.pdf": [
        [("Acme Corp IT Security Policy. This policy applies to all employees and contractors.", None, None, None),
         ("Passwords must be at least 14 characters long.",
          "What is the minimum password length?", "14 characters", "14 characters")],
        [("Remote access to company systems is only allowed through the approved VPN client.", None, None, None),
         ("Multi-factor authentication is mandatory for all VPN access.",
          "What is mandatory for all VPN access?", "Multi-factor authentication", "Multi-factor authentication"),
         ("Laptops must use full-disk encryption (BitLocker or FileVault).",
          "What disk protection must company laptops use?", "Full-disk encryption (BitLocker or FileVault)", "full-disk encryption")],
        [("The IT helpdesk is available on all working days.", None, None, None),
         ("Security incidents must be reported to the helpdesk within 2 hours.",
          "Within what time must security incidents be reported to the helpdesk?", "Within 2 hours", "2 hours")],
    ],
    "expense_policy.pdf": [
        [("Acme Corp Expense Policy. This policy explains how business expenses are claimed.", None, None, None),
         ("Meals during business travel are reimbursed up to $60 per day.",
          "What is the daily reimbursement limit for meals during business travel?", "$60 per day", "$60 per day")],
        [("Receipts must be attached to every expense claim.", None, None, None),
         ("Any single expense above $500 requires prior written approval from a director.",
          "What approval is needed for a single expense above $500?", "Prior written approval from a director", "$500"),
         ("Economy class is required for flights shorter than 6 hours.",
          "Which flight class is required for flights shorter than 6 hours?", "Economy class", "6 hours")],
        [("Reimbursements are processed by the Finance team.", None, None, None),
         ("Approved reimbursements are paid within 10 business days.",
          "How soon are approved reimbursements paid?", "Within 10 business days", "10 business days")],
    ],
}

CSV_QS = [
    ("What is the price of the Laptop Pro?",
     lambda d: d.loc[d["name"] == "Laptop Pro", "price"].iloc[0]),
    ("How many units of the Wireless Mouse are in stock?",
     lambda d: d.loc[d["name"] == "Wireless Mouse", "stock"].iloc[0]),
    ("Which product is out of stock?",
     lambda d: d.loc[d["stock"] == 0, "name"].iloc[0]),
    ("How many products are in the Furniture category?",
     lambda d: (d["category"] == "Furniture").sum()),
    ("Which product has the highest price?",
     lambda d: d.loc[d["price"].idxmax(), "name"]),
    ("What is the average price of products in the Accessories category?",
     lambda d: d.loc[d["category"] == "Accessories", "price"].mean()),
    ("What is the total stock of all Electronics products?",
     lambda d: d.loc[d["category"] == "Electronics", "stock"].sum()),
]

SQL_QS = [
    ("How many employees are there in total?", "SELECT COUNT(*) FROM employees"),
    ("How many employees are in the Engineering department?",
     "SELECT COUNT(*) FROM employees WHERE department='Engineering'"),
    ("What is Asha Rao's leave balance in days?",
     "SELECT leave_balance FROM employees WHERE name='Asha Rao'"),
    ("Which employee has the highest salary?",
     "SELECT name FROM employees ORDER BY salary DESC LIMIT 1"),
    ("What is the average salary in the Sales department?",
     "SELECT AVG(salary) FROM employees WHERE department='Sales'"),
    ("Which employees were hired in 2022 or later?",
     "SELECT name FROM employees WHERE hire_year>=2022 ORDER BY name"),
]

# (question, source) -> expected answer is always "I don't know"
UNANSWERABLE = [
    ("What is the company policy on sabbatical leave?", "hr_policy.pdf"),
    ("Which firewall vendor does the company use?", "it_security_policy.pdf"),
    ("What is the maximum nightly hotel rate reimbursed for travel?", "expense_policy.pdf"),
    ("Who is the supplier of the Laptop Pro?", "products.csv"),
    ("What is the home address of Asha Rao?", "mock_db.sqlite:employees"),
]


def fmt(v):
    if isinstance(v, (float, np.floating)):
        return f"{v:g}"
    return str(v)


def sql_answer(cur, sql):
    rows = cur.execute(sql).fetchall()
    return fmt(rows[0][0]) if len(rows) == 1 else ", ".join(fmt(r[0]) for r in rows)


def make_pdf(path, pages):
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    for i, sentences in enumerate(pages, 1):
        y = h - 80
        c.setFont("Helvetica-Bold", 14)
        c.drawString(60, y, f"{path.stem.replace('_', ' ').title()} - Page {i}")
        y -= 40
        c.setFont("Helvetica", 11)
        for s, *_ in sentences:
            for line in simpleSplit(s, "Helvetica", 11, w - 120):
                c.drawString(60, y, line)
                y -= 16
            y -= 10
        c.showPage()
    c.save()


def make_csv():
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        ("P001", "Laptop Pro", "Electronics", 1200, 15),
        ("P002", "Wireless Mouse", "Accessories", 25, 150),
        ("P003", "Mechanical Keyboard", "Accessories", 80, 60),
        ("P004", "27in Monitor", "Electronics", 300, 40),
        ("P005", "USB-C Hub", "Accessories", 45, 90),
        ("P006", "Webcam HD", "Electronics", 70, 0),
        ("P007", "Standing Desk", "Furniture", 450, 12),
        ("P008", "Office Chair", "Furniture", 220, 25),
        ("P009", "Noise Headset", "Accessories", 130, 35),
        ("P010", "Desk Lamp", "Furniture", 35, 80),
    ]
    pd.DataFrame(rows, columns=["product_id", "name", "category", "price", "stock"]).to_csv(CSV_PATH, index=False)


def make_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.unlink(missing_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT, department TEXT,
                   salary INTEGER, hire_year INTEGER, leave_balance INTEGER)""")
    con.executemany("INSERT INTO employees VALUES (?,?,?,?,?,?)", [
        (1, "Asha Rao", "Engineering", 90000, 2019, 12),
        (2, "Ravi Kumar", "Engineering", 85000, 2021, 18),
        (3, "Meena Iyer", "HR", 60000, 2018, 9),
        (4, "John Smith", "Sales", 70000, 2020, 15),
        (5, "Priya Nair", "Sales", 72000, 2022, 20),
        (6, "Karan Shah", "Finance", 80000, 2017, 7),
        (7, "Lina Das", "HR", 58000, 2023, 22),
        (8, "Omar Khan", "Engineering", 95000, 2016, 5),
    ])
    con.commit()
    con.close()


def main():
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    for name, pages in PDF_SPEC.items():
        make_pdf(PDF_DIR / name, pages)
    make_csv()
    make_db()

    records = []
    # PDF: 12 answerable
    for name, pages in PDF_SPEC.items():
        for page_no, page in enumerate(pages, 1):
            for _, q, a, _ in page:
                if q:
                    records.append({"question": q, "ground_truth": a, "source": name, "page": page_no})
    # CSV: 7 answerable
    df = pd.read_csv(CSV_PATH)
    for q, fn in CSV_QS:
        records.append({"question": q, "ground_truth": fmt(fn(df)), "source": "products.csv", "page": None})
    # SQL: 6 answerable
    cur = sqlite3.connect(DB_PATH).cursor()
    for q, sql in SQL_QS:
        records.append({"question": q, "ground_truth": sql_answer(cur, sql),
                        "source": "mock_db.sqlite:employees", "page": None})
    # 5 unanswerable
    for q, src in UNANSWERABLE:
        records.append({"question": q, "ground_truth": IDK, "source": src, "page": None})

    with open(OUT, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {len(records)} records to {OUT.name}")


if __name__ == "__main__":
    main()