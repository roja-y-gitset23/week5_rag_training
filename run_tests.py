from mock_db import setup_db
from router import answer_question

# (question, correct route, text that MUST appear in the answer to count it correct)
TESTS = [
    ("What is the carry forward policy for annual leave?", "RAG", ["8 unused", "carried forward"]),
    ("What is the notice period for resignation?", "RAG", ["60-day"]),
    ("What is the work from home policy?", "RAG", ["2 days per week"]),
    ("What is the leave balance of employee 3?", "SQL", ["Total 28"]),
    ("Show the payslip of employee 5 for 2026-09", "SQL", ["70,400"]),
    ("How many employees are in the Engineering department?", "SQL", ["4 employees"]),
    ("What is the sick leave policy and what is the leave balance of employee 2?", "BOTH", ["12 days", "Total 27"]),
    ("Explain the payslip deduction policy and show the payslip of employee 1 for 2026-09.", "BOTH", ["12 percent", "44,800"]),
]

setup_db()
rows = []
for i, (q, correct_route, must_have) in enumerate(TESTS, start=1):
    r = answer_question(q)
    route_ok = "Y" if r["route"] == correct_route else "N"
    ans_ok = "Y" if all(s.lower() in r["answer"].lower() for s in must_have) else "N"
    rows.append((q, r["route"], route_ok, ans_ok))
    print(f"Q{i}: {q}")
    print(f"  Route chosen : {r['route']}  (tool: {r['tool']})")
    print(f"  Answer       : {r['answer']}")
    print(f"  Sources used : {'; '.join(r['sources'])}")
    print()

lines = ["| Question | Route chosen | Correct route (Y/N) | Answer correct (Y/N) |",
         "|---|---|---|---|"]
lines += [f"| {q} | {route} | {a} | {b} |" for q, route, a, b in rows]
table = "\n".join(lines)
print(table)
with open("results.md", "w", encoding="utf-8") as f:
    f.write(table + "\n")
print("\nSaved to results.md")