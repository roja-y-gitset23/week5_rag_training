import csv
import random
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

random.seed(42)
PDF_DIR = Path("data/pdfs")
CSV_DIR = Path("data/csv")
PDF_DIR.mkdir(parents=True, exist_ok=True)
CSV_DIR.mkdir(parents=True, exist_ok=True)

POLICIES = {
    "hr_policy.pdf": "HR Policy",
    "leave_policy.pdf": "Leave Policy",
    "code_of_conduct.pdf": "Code of Conduct",
}

def make_pdf(filename, title):
    c = canvas.Canvas(str(PDF_DIR / filename), pagesize=A4)
    width, height = A4
    for page in range(1, 61):  # 60 pages per PDF
        text = (
            f"{title} - Section {page}. This section explains rule {page} of the "
            f"{title.lower()} for all employees. Employees must follow the "
            f"procedure described here and inform their manager in writing. "
            f"Any exception needs approval from the HR department. Records are "
            f"kept for {page % 5 + 1} years and reviewed every quarter."
        )
        y = height - 80
        for line in simpleSplit(text, "Helvetica", 11, width - 120):
            c.setFont("Helvetica", 11)
            c.drawString(60, y, line)
            y -= 16
        c.showPage()
    c.save()

for fname, title in POLICIES.items():
    make_pdf(fname, title)

depts = ["HR", "Engineering", "Sales", "Finance", "Support"]
with open(CSV_DIR / "employees.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["employee_id", "name", "department", "role", "join_date"])
    for i in range(1, 221):  # 220 rows
        w.writerow([i, f"Employee {i}", random.choice(depts),
                    f"Role {i % 12}", f"20{random.randint(15, 24)}-0{random.randint(1, 9)}-15"])

with open(CSV_DIR / "leave_records.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["leave_id", "employee_id", "leave_type", "days", "status"])
    for i in range(1, 201):  # 200 rows
        w.writerow([i, random.randint(1, 220),
                    random.choice(["Sick", "Casual", "Annual"]),
                    random.randint(1, 10),
                    random.choice(["Approved", "Pending", "Rejected"])])

print("Sample data created: 3 PDFs (60 pages each), 2 CSVs (220 + 200 rows)")