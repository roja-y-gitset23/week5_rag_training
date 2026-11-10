"""Tiny policy RAG: keyword retrieval over policy snippets (no packages needed)."""
import re

POLICY_DOCS = [
    {"source": "leave_policy.pdf", "page": 2,
     "text": "Annual leave and carry forward: each employee gets 18 days of annual leave per year. "
             "Carry forward: up to 8 unused annual leave days can be carried forward to the next year; "
             "the rest lapse on 31 December."},
    {"source": "leave_policy.pdf", "page": 3,
     "text": "Sick leave: employees get 12 days of sick leave per year. A medical certificate is "
             "required for sick leave longer than 2 consecutive days. Sick leave cannot be carried forward."},
    {"source": "leave_policy.pdf", "page": 4,
     "text": "Casual leave: employees get 6 days of casual leave per year. Casual leave cannot be "
             "combined with annual leave for more than 3 consecutive days."},
    {"source": "hr_policy.pdf", "page": 5,
     "text": "Notice period: confirmed employees must serve a 60-day notice period on resignation. "
             "Probationary employees must serve 15 days."},
    {"source": "hr_policy.pdf", "page": 7,
     "text": "Work from home: employees may work from home up to 2 days per week with manager approval. "
             "Client-facing roles need written approval from the department head."},
    {"source": "payroll_policy.pdf", "page": 1,
     "text": "Payslips are issued by the 5th of every month. Deductions include provident fund at "
             "12 percent of basic salary and professional tax. Net pay = basic + HRA - deductions."},
    {"source": "code_of_conduct.pdf", "page": 4,
     "text": "Dress code: employees must follow a smart casual dress code in the office. "
             "Formal wear is required for client meetings."},
]

STOPWORDS = {"what", "is", "the", "of", "for", "and", "a", "an", "to", "in", "are", "from",
             "show", "explain", "tell", "me", "about", "how", "many", "does", "do", "on", "per",
             "with", "policy", "policies", "employee", "employees", "according", "their", "my"}


def _stem(w):
    return w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w


def _tokens(text):
    return {_stem(w) for w in re.findall(r"[a-z]+", text.lower()) if w not in STOPWORDS}


def search_policy(question):
    """Return (answer_text, sources_list) for the best matching policy snippet."""
    q = _tokens(question)
    best, best_score = None, 0
    for doc in POLICY_DOCS:
        score = len(q & _tokens(doc["text"]))
        if score > best_score:
            best, best_score = doc, score
    if best is None:
        return "No matching policy found.", []
    return best["text"], [f"RAG: {best['source']} p.{best['page']}"]