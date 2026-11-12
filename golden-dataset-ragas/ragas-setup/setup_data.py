import os
import csv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from data_sources import POLICY_PAGES, SALES_COLUMNS, SALES_ROWS

os.makedirs("data", exist_ok=True)

c = canvas.Canvas("data/handbook.pdf", pagesize=A4)
for title, lines in POLICY_PAGES:
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 780, title)
    c.setFont("Helvetica", 11)
    y = 740
    for line in lines:
        c.drawString(50, y, line)
        y -= 28
    c.showPage()
c.save()

with open("data/sales.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(SALES_COLUMNS)
    w.writerows(SALES_ROWS)

print("Created data/handbook.pdf and data/sales.csv")