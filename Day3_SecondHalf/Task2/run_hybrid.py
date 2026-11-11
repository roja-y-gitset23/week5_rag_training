from search import bm25_search, vector_search
from hybrid import hybrid_search

# SAME 10 questions as Task 1 (question, expected chunk id)
tests = [
    ("What does HR-204 say?",                           "c1"),
    ("Who is Priya Nair?",                              "c5"),
    ("Explain policy FIN-112",                          "c4"),
    ("What is SEC-880?",                                "c10"),
    ("What is the LD-45 limit?",                        "c12"),
    ("How many days off do I get in a year?",           "c1"),
    ("Can I work from my house?",                       "c2"),
    ("What should I do if my work computer is stolen?", "c3"),
    ("When do I receive my pay?",                       "c8"),
    ("How often are staff evaluated?",                  "c11"),
]

def hits(fn, **kw):
    flags = []
    for q, exp in tests:
        top = [cid for cid, _ in fn(q, 3, **kw)]
        flags.append(exp in top)
    return flags

bm_flags = hits(bm25_search)
vec_flags = hits(vector_search)

# ---- Try weights 0.0 to 1.0 ----
print("Weight sweep (hybrid hits @3):")
results = {}
for w in [round(x * 0.1, 1) for x in range(1, 10)]:
    results[w] = sum(hits(hybrid_search, weight=w))
    print(f"  weight={w:.1f} -> {results[w]}/10")

# Best = most hits; ties -> closest to 0.5 (most balanced)
best_w = sorted(results, key=lambda w: (-results[w], abs(w - 0.5)))[0]
hy_flags = hits(hybrid_search, weight=best_w)

# ---- Per-question table ----
print(f"\n{'Question':52} | BM25 | Vector | Hybrid(w={best_w})")
print("-" * 90)
for (q, _), b, v, h in zip(tests, bm_flags, vec_flags, hy_flags):
    print(f"{q:52} |  {'Y' if b else 'N'}   |   {'Y' if v else 'N'}    |   {'Y' if h else 'N'}")

# ---- Final line ----
print(f"\nBest weight: {best_w}")
print(f"Hit rate @3 -> BM25: {sum(bm_flags)}/10 | Vector: {sum(vec_flags)}/10 | Hybrid: {sum(hy_flags)}/10")