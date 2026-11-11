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