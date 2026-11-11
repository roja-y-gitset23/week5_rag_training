from search import bm25_search, vector_search

# (question, expected chunk id, type)
tests = [
    ("What does HR-204 say?",                           "c1",  "keyword"),
    ("Who is Priya Nair?",                              "c5",  "keyword"),
    ("Explain policy FIN-112",                          "c4",  "keyword"),
    ("What is SEC-880?",                                "c10", "keyword"),
    ("What is the LD-45 limit?",                        "c12", "keyword"),
    ("How many days off do I get in a year?",           "c1",  "meaning"),
    ("Can I work from my house?",                       "c2",  "meaning"),
    ("What should I do if my work computer is stolen?", "c3",  "meaning"),
    ("When do I receive my pay?",                       "c8",  "meaning"),
    ("How often are staff evaluated?",                  "c11", "meaning"),
]

rows = []
for q, expected, kind in tests:
    bm = [i for i, _ in bm25_search(q, 3)]
    vec = [i for i, _ in vector_search(q, 3)]
    rows.append((q, "Y" if expected in bm else "N", "Y" if expected in vec else "N", kind, bm, vec))

print(f"\n{'Question':52} | BM25 hit (Y/N) | Vector hit (Y/N)")
print("-" * 90)
for q, b, v, kind, bm, vec in rows:
    print(f"{q:52} | {b:^14} | {v:^16}")

print("\nDetails (top-3 ids):")
for q, b, v, kind, bm, vec in rows:
    print(f"[{kind}] {q}\n   BM25: {bm}  Vector: {vec}")

# Save the submission table as markdown
with open("results.md", "w", encoding="utf-8") as f:
    f.write("| Question | BM25 hit (Y/N) | Vector hit (Y/N) |\n|---|---|---|\n")
    for q, b, v, *_ in rows:
        f.write(f"| {q} | {b} | {v} |\n")
print("\nSaved results.md")


"""
4-line explanation where BM25 beats vectors and where vectors beat BM25:

1. Exact keywords (HR-204, SEC-880, FIN-112, Priya Nair): BM25 and vectors both retrieved the right chunk (5/5 each). BM25 matches these rare tokens literally and cannot be fooled by similar-looking codes, but with only 12 distinct chunks the vector model had no confusing neighbours, so there was no BM25 advantage to see.

2. Where BM25 is stronger in principle: BM25 should win when many chunks share similar codes or names (HR-204 vs HR-310), because embeddings blur such near-identical strings. My small test set did not stress this.
3. Where vectors beat BM25: On meaning-based questions, vectors hit 5/5 and BM25 only 1/5. “How many days off do I get in a year?”, “work computer is stolen”, “When do I receive my pay?” and “How often are staff evaluated?” share almost no words with the chunks (“annual leave”, “lost devices”, “salaries are credited”, “appraisals”).
4. Conclusion: Vectors handle paraphrases and synonyms; BM25 handles exact identifiers. Hybrid search combines both, so neither weakness decides the result.
"""