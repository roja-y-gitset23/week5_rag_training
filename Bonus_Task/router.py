"""Router: policy question -> RAG, data question -> SQL tool, mixed -> both.
Bonus: every routed question is timed and logged to route_log.csv."""
import re
import time

from mock_db import call_tool, run_query
from rag import search_policy
from route_logger import log_route

POLICY_RE = re.compile(
    r"\b(policy|policies|rules?|guidelines?|notice period|allowed|handbook|"
    r"work from home|wfh|dress code)\b", re.I)
DATA_RE = re.compile(
    r"\b(balance|payslip|net pay|how many employees|number of employees|headcount)\b"
    r"|\b(?:employee|emp)\s*#?\d+", re.I)


def classify(question):
    p = bool(POLICY_RE.search(question))
    d = bool(DATA_RE.search(question))
    if p and d:
        return "BOTH"
    if d:
        return "SQL"
    return "RAG"


def _format(tool, r):
    if "error" in r:
        return "Error: " + r["error"]
    if tool == "get_leave_balance":
        parts = ", ".join(f"{k} {v}" for k, v in r["balances"].items())
        return f"Employee {r['emp_id']} ({r['name']}) leave balance: {parts}. Total {r['total']} days."
    if tool == "get_payslip":
        return (f"Payslip for employee {r['emp_id']} ({r['name']}), {r['month']}: "
                f"Basic {r['basic']:,}, HRA {r['hra']:,}, Deductions {r['deductions']:,}, "
                f"Net pay {r['net_pay']:,}.")
    return f"{r['count']} employees in {r['department']}."


def run_sql(question):
    ql = question.lower()
    emp = re.search(r"(?:employee|emp)(?:\s*id)?\s*[#:_-]?\s*(\d+)", ql)
    emp_id = int(emp.group(1)) if emp else None
    month = re.search(r"\b(\d{4}-\d{2})\b", ql)

    if "payslip" in ql or "net pay" in ql:
        tool, args = "get_payslip", {"emp_id": emp_id, "month": month.group(1) if month else None}
    elif "balance" in ql:
        tool, args = "get_leave_balance", {"emp_id": emp_id}
    else:
        depts = [r[0] for r in run_query("SELECT DISTINCT department FROM employees")]
        dept = next((d for d in depts if d.lower() in ql), None)
        tool, args = "count_employees", {"department": dept}

    result = call_tool(tool, **args)
    sources = [f"SQL: {tool}() on tables {result['tables']}"] if "tables" in result else [f"SQL: {tool}()"]
    return tool, _format(tool, result), sources


def answer_question(question):
    start = time.perf_counter()                      # bonus: start the timer
    route = classify(question)
    answer_parts, sources, tool = [], [], "-"
    if route in ("RAG", "BOTH"):
        text, src = search_policy(question)
        answer_parts.append(("[Policy] " if route == "BOTH" else "") + text)
        sources += src
    if route in ("SQL", "BOTH"):
        tool, text, src = run_sql(question)
        answer_parts.append(("[Data] " if route == "BOTH" else "") + text)
        sources += src
    elapsed = time.perf_counter() - start            # bonus: stop the timer
    log_route(question, route, tool, sources, elapsed)   # bonus: write one log row
    return {"route": route, "tool": tool, "answer": "\n    ".join(answer_parts),
            "sources": sources, "time_ms": elapsed * 1000}