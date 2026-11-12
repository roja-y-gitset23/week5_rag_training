from datetime import date
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                Table, TableStyle, PageBreak)
from pypdf import PdfReader

# ================= EDIT THESE (placeholder numbers) =================
CLIENT = "Client Name"
PROJECT = "Company Document Assistant"
BEST = "C"  # recommended variant: "A", "B" or "C"

SCORES = {
    "A": {"faithfulness": 0.70, "answer_relevancy": 0.78, "context_precision": 0.60, "context_recall": 0.68,
          "sec_per_q": 2.1, "cost_per_run": 0.40, "desc": "Chunk 256 + vector search"},
    "B": {"faithfulness": 0.80, "answer_relevancy": 0.84, "context_precision": 0.72, "context_recall": 0.78,
          "sec_per_q": 2.6, "cost_per_run": 0.52, "desc": "Chunk 512 + hybrid search"},
    "C": {"faithfulness": 0.89, "answer_relevancy": 0.89, "context_precision": 0.84, "context_recall": 0.83,
          "sec_per_q": 3.4, "cost_per_run": 0.70, "desc": "Chunk 512 + hybrid + reranker"},
}
# Failure-fix re-run on the 8 worst questions of the best variant
BEFORE_FIX = {"faithfulness": 0.55, "context_recall": 0.50}
AFTER_FIX = {"faithfulness": 0.78, "context_recall": 0.72}
GEN_MODEL = "gemini-2.5-flash"
# ====================================================================


def out_of_10(x):
    return round(x * 10)


b = SCORES[BEST]
a = SCORES["A"]

# ---------- Chart ----------
metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
labels = ["Answers backed\nby documents", "Answers on\ntopic", "Right documents\nfound", "Nothing important\nmissed"]
fig, ax = plt.subplots(figsize=(8, 3.6))
width = 0.25
x = range(len(metrics))
colors_v = {"A": "#9aa5b1", "B": "#4a90d9", "C": "#1f7a4d"}
for i, v in enumerate(["A", "B", "C"]):
    vals = [SCORES[v][m] for m in metrics]
    bars = ax.bar([p + (i - 1) * width for p in x], vals, width, label=f"Variant {v}", color=colors_v[v])
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.01, f"{val:.2f}", ha="center", fontsize=8)
ax.set_xticks(list(x))
ax.set_xticklabels(labels, fontsize=9)
ax.set_ylim(0, 1.1)
ax.set_ylabel("Score (1.0 = perfect)")
ax.set_title("Quality scores by variant (30 test questions)")
ax.legend(loc="lower right")
plt.tight_layout()
plt.savefig("chart.png", dpi=200)
plt.close()

# ---------- Styles ----------
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=18, spaceAfter=4)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12, spaceBefore=8, spaceAfter=3,
                    textColor=colors.HexColor("#1f4e79"))
P = ParagraphStyle("P", parent=ss["BodyText"], fontSize=9.5, leading=13)
SMALL = ParagraphStyle("S", parent=P, fontSize=8.5, textColor=colors.grey)


def bullets(items):
    return [Paragraph("&bull; " + t, P) for t in items]


story = []

# ---------- PAGE 1 ----------
story.append(Paragraph(f"{PROJECT}: Results Report", H1))
story.append(Paragraph(f"Prepared for {CLIENT} | {date.today():%d %B %Y}", SMALL))

story.append(Paragraph("Summary", H2))
story.append(Paragraph(
    f"We tested three ways of building the assistant on 30 real questions. "
    f"<b>Variant {BEST} ({b['desc']}) is our recommendation.</b> About "
    f"<b>{out_of_10(b['faithfulness'])} out of 10 answers are fully supported by company documents</b>, "
    f"and the system finds the right documents "
    f"<b>{out_of_10(b['context_precision'])} out of 10 times</b>.", P))

story.append(Paragraph("What the scores mean in plain words", H2))
story += bullets([
    f"<b>Faithfulness {b['faithfulness']:.2f}</b>: about {out_of_10(b['faithfulness'])} out of 10 answers "
    f"are fully supported by your documents. The rest may include details the documents do not support.",
    f"<b>Answer relevancy {b['answer_relevancy']:.2f}</b>: about {out_of_10(b['answer_relevancy'])} out of 10 "
    f"answers directly address the question asked.",
    f"<b>Retrieval precision {b['context_precision']:.2f}</b>: when the assistant looks up documents, "
    f"about {out_of_10(b['context_precision'])} out of 10 of the pages it picks are actually useful. "
    f"Think of it as a librarian: precision is how many of the books handed over are the right ones.",
    f"<b>Retrieval recall {b['context_recall']:.2f}</b>: the assistant found about "
    f"{out_of_10(b['context_recall'])} out of 10 of the facts needed to answer.",
])

story.append(Paragraph("Improvement across variants (retrieval precision)", H2))
gain = (b["context_precision"] - a["context_precision"]) * 100
story.append(Paragraph(
    f"Retrieval precision rose from <b>{a['context_precision']:.2f}</b> in Variant A to "
    f"<b>{SCORES['B']['context_precision']:.2f}</b> in Variant B and "
    f"<b>{b['context_precision']:.2f}</b> in Variant C, a gain of about "
    f"<b>{gain:.0f} percentage points</b>. In everyday terms: the assistant now hands over "
    f"{out_of_10(b['context_precision'])} useful pages out of 10 instead of "
    f"{out_of_10(a['context_precision'])}.", P))
story.append(Spacer(1, 4))
story.append(Image("chart.png", width=15.5 * cm, height=7 * cm))

story.append(PageBreak())

# ---------- PAGE 2 ----------
story.append(Paragraph("Recommended configuration", H2))
rows = [["", "Variant A", "Variant B", "Variant C"],
        ["Setup", SCORES["A"]["desc"], SCORES["B"]["desc"], SCORES["C"]["desc"]],
        ["Seconds per answer"] + [f"{SCORES[v]['sec_per_q']:.1f}" for v in "ABC"],
        ["Cost per 30 questions"] + [f"${SCORES[v]['cost_per_run']:.2f}" for v in "ABC"]]
t = Table([[Paragraph(str(c), P) for c in r] for r in rows], colWidths=[3.6 * cm, 4.4 * cm, 4.4 * cm, 4.4 * cm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce6f1")),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
    ("BACKGROUND", ({"A": 1, "B": 2, "C": 3}[BEST], 1), ({"A": 1, "B": 2, "C": 3}[BEST], -1),
     colors.HexColor("#e2f0e6")),
]))
story.append(t)
story.append(Spacer(1, 4))
story.append(Paragraph(
    f"We recommend <b>Variant {BEST}</b>. It scores highest on quality. The trade-off is "
    f"{b['sec_per_q'] - a['sec_per_q']:.1f} extra seconds per answer and "
    f"${b['cost_per_run'] - a['cost_per_run']:.2f} more per 30 questions, which we consider worth it for "
    f"more trustworthy answers.", P))

story.append(Paragraph("Can we trust it?", H2))
story.append(Paragraph(
    f"<b>Mostly yes, with human review for important decisions.</b> About "
    f"{out_of_10(b['faithfulness'])} out of 10 answers are fully backed by your documents. "
    f"Every answer shows its source so staff can check it in seconds. When the documents do not contain "
    f"the answer, the assistant is designed to say \"I don't know\" instead of guessing.", P))

story.append(Paragraph("What if it is wrong?", H2))
story += bullets([
    "Each answer links to its source document, so errors are easy to spot.",
    "High-impact outputs (for example customer emails) are drafts only and need a person's approval before use.",
    "Staff can flag a wrong answer. We review flagged answers and fix the cause.",
    f"We found our 8 weakest questions, fixed them, and faithfulness on them rose from "
    f"{BEFORE_FIX['faithfulness']:.2f} to {AFTER_FIX['faithfulness']:.2f}. This shows mistakes can be "
    f"diagnosed and reduced.",
])

story.append(Paragraph("Known limitations", H2))
story += bullets([
    f"About {10 - out_of_10(b['faithfulness'])} in 10 answers may not be fully supported by documents.",
    "Tested on only 30 questions, so real-world results may differ.",
    "It only knows what is in the uploaded documents; outdated documents give outdated answers.",
    f"Answers take about {b['sec_per_q']:.1f} seconds and each run has a running cost.",
    f"Scoring itself is done by an AI judge ({GEN_MODEL}), which is useful but not perfect.",
])

story.append(Paragraph("Next steps", H2))
story += bullets([
    "Run a 2-week pilot with a small team and collect their feedback.",
    "Grow the test set from 30 to 100 questions using real user questions.",
    "Add a thumbs-up / thumbs-down button and track wrong answers weekly.",
    "Keep documents up to date and re-test after every change.",
    f"Target: faithfulness of 0.95 or higher before wider rollout (now {b['faithfulness']:.2f}).",
])

doc = SimpleDocTemplate("client_report.pdf", pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                        topMargin=1.5 * cm, bottomMargin=1.4 * cm,
                        title=f"{PROJECT} Results Report")
doc.build(story)

pages = len(PdfReader("client_report.pdf").pages)
print(f"client_report.pdf created: {pages} page(s)")
if pages != 2:
    print("WARNING: report is not 2 pages. Shorten text or reduce chart height.")