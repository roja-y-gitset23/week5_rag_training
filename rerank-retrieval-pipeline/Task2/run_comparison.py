from pipeline import RetrievalPipeline, load_config

# (question, keyword that must appear in a correct answer)
"""QUESTIONS = [
    ("How many vacation days do I get each year?", "24 days"),
    ("Do I need a doctor's note when I am ill for several days?", "medical certificate"),
    ("What is the daily food limit when I travel for work?", "40 USD"),
    ("How often must I change my login credentials?", "90 days"),
    ("How long do I have to give notice if I quit?", "60 days"),
]"""

QUESTIONS = [
    ("What is my yearly time-off entitlement?", "24 days"),
    ("Which paperwork does a prolonged absence due to illness require?", "medical certificate"),
    ("What is the spending cap on eating while on a business trip?", "40 USD"),
    ("How frequently should my sign-in secret be renewed?", "90 days"),
    ("How much advance warning is needed to leave the company?", "60 days"),
]

def grade_hint(result, keyword):
    """Suggested grade only. Verify it manually."""
    if keyword.lower() in result["answer"].lower():
        return "correct"
    if any(keyword.lower() in h["text"].lower() for h in result["hits"]):
        return "partly correct"
    return "wrong"

def short(text, n=90):
    return text if len(text) <= n else text[:n] + "..."

results = {}
for flag in (False, True):
    cfg = load_config("config.yaml", use_reranker=flag)
    pipe = RetrievalPipeline(cfg)
    results[flag] = [pipe.answer(q) for q, _ in QUESTIONS]

base = load_config("config.yaml")
print("Config:", {k: base[k] for k in
      ["use_bm25", "use_vector", "top_k", "candidate_k", "chunk_size", "chunk_overlap"]})
print()

lines = [
    "| # | Question | Reranker OFF answer | OFF grade | Reranker ON answer | ON grade |",
    "|---|----------|---------------------|-----------|--------------------|----------|",
]
score = {False: 0, True: 0}
for i, (q, kw) in enumerate(QUESTIONS):
    off, on = results[False][i], results[True][i]
    g_off, g_on = grade_hint(off, kw), grade_hint(on, kw)
    score[False] += g_off == "correct"
    score[True] += g_on == "correct"
    lines.append(f"| {i+1} | {q} | {short(off['answer'])} | {g_off} | {short(on['answer'])} | {g_on} |")

table = "\n".join(lines)
print(table)
print(f"\nCorrect: reranker OFF {score[False]}/5, reranker ON {score[True]}/5")

with open("comparison_table.md", "w", encoding="utf-8") as f:
    f.write(table + f"\n\nCorrect: reranker OFF {score[False]}/5, reranker ON {score[True]}/5\n")
print("Saved comparison_table.md")