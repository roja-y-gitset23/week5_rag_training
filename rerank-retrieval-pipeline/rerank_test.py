import re
import time
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder

# ---------- 1. Corpus (chunk id = list index) ----------
CHUNKS = [
    "Annual leave: Full-time employees receive 24 days of paid annual leave per calendar year, accrued monthly.",
    "Sick leave: Employees may take up to 10 days of paid sick leave per year; a medical certificate is required after 3 consecutive days.",
    "Maternity leave: Mothers are entitled to 26 weeks of paid maternity leave, which can start up to 4 weeks before the due date.",
    "Paternity leave: Fathers are entitled to 2 weeks of paid paternity leave taken within 3 months of birth.",
    "Carry forward: Up to 5 unused annual leave days can be carried forward to the next year and expire on 31 March.",
    "Remote work: Employees may work remotely up to 3 days per week with manager approval.",
    "Home office allowance: A one-time allowance of 500 USD is paid for setting up a home office.",
    "Laptop: New joiners receive a company laptop on day one; it must be returned on exit.",
    "Password policy: Passwords must have at least 12 characters and be changed every 90 days.",
    "MFA: Multi-factor authentication is mandatory for email, VPN and the HR portal.",
    "VPN: Connect to the VPN before accessing internal systems from outside the office network.",
    "Expenses: Travel expenses must be submitted within 30 days with original receipts.",
    "Meal allowance: Meals during business travel are reimbursed up to 40 USD per day.",
    "Hotel: Hotel stays are capped at 150 USD per night in standard cities and 220 USD in major cities.",
    "Probation: New employees serve a 6 month probation period with a notice period of 1 week.",
    "Notice period: After probation, the notice period for resignation is 60 days.",
    "Performance review: Performance reviews happen twice a year, in June and December.",
    "Bonus: Annual bonus is paid in March based on the December review rating.",
    "Training budget: Each employee has a learning budget of 1000 USD per year for courses and certifications.",
    "Health insurance: Health insurance covers the employee, spouse and up to 2 children from the first day.",
    "Working hours: Core working hours are 10 am to 4 pm; the standard week is 40 hours.",
    "Overtime: Overtime must be pre-approved and is compensated with time off at 1.5 times.",
    "Public holidays: The company observes 12 public holidays, published in January.",
    "Dress code: Business casual is the standard; formal wear is required for client meetings.",
    "Data classification: Documents are labelled Public, Internal, Confidential or Restricted.",
    "Incident reporting: Security incidents must be reported to the helpdesk within 1 hour of discovery.",
    "Referral: Employees get a 1500 USD referral bonus when a referred candidate completes 6 months.",
    "Exit: On the last day, return all assets and complete the exit interview with HR.",
    "Payroll: Salaries are paid on the last working day of each month by bank transfer.",
    "Parental support: The return-to-work program offers 2 months of part-time hours after parental leave.",
]
"""
# (question, correct chunk id)
QUESTIONS = [
    ("How many vacation days do I get each year?", 0),
    ("Do I need a doctor's note when I am ill for several days?", 1),
    ("How long is leave for new mothers?", 2),
    ("Can leftover holiday days roll over into next year?", 4),
    ("How often must I change my login credentials?", 8),
    ("What is the daily food limit when I travel for work?", 12),
    ("How long do I have to give notice if I quit?", 15),
    ("When do I receive my yearly bonus?", 17),
    ("Who is covered by medical insurance?", 19),
    ("How soon must a security breach be reported?", 25),
]
"""
QUESTIONS = [
    ("What is my yearly time-off entitlement?", 0),
    ("Which paperwork does a prolonged absence due to illness require?", 1),
    ("How many weeks off does a woman get after having a baby?", 6),
    ("What happens to my unused time off at year end?", 4),
    ("How frequently should my sign-in secret be renewed?", 8),
    ("What is the spending cap on eating while on a business trip?", 12),
    ("How much advance warning is needed to leave the company?", 15),
    ("What determines the payout I get each spring?", 17),
    ("Are my dependents protected under the medical plan?", 19),
    ("What is the deadline for flagging a compromised account?", 25),
]

TOP_N, TOP_K = 20, 5

# ---------- 2. Models and indexes ----------
def tok(text):
    return re.findall(r"\w+", text.lower())

bm25 = BM25Okapi([tok(c) for c in CHUNKS])
bi_encoder = SentenceTransformer("all-MiniLM-L6-v2")
chunk_emb = bi_encoder.encode(CHUNKS, normalize_embeddings=True)
cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# ---------- 3. Hybrid search (BM25 + embeddings, merged with RRF) ----------
def hybrid_search(query, n=TOP_N, rrf_k=60):
    bm25_scores = bm25.get_scores(tok(query))
    q_emb = bi_encoder.encode(query, normalize_embeddings=True)
    dense_scores = chunk_emb @ q_emb

    bm25_rank = np.argsort(-bm25_scores)
    dense_rank = np.argsort(-dense_scores)

    fused = {}
    for rank, idx in enumerate(bm25_rank):
        fused[idx] = fused.get(idx, 0) + 1 / (rrf_k + rank + 1)
    for rank, idx in enumerate(dense_rank):
        fused[idx] = fused.get(idx, 0) + 1 / (rrf_k + rank + 1)

    return [int(i) for i, _ in sorted(fused.items(), key=lambda x: -x[1])[:n]]

# ---------- 4. Rerank ----------
def rerank(query, candidate_ids):
    pairs = [(query, CHUNKS[i]) for i in candidate_ids]
    scores = cross_encoder.predict(pairs)
    order = np.argsort(-scores)
    return [candidate_ids[i] for i in order]

def position(ids, gold):
    """1-based position of the correct chunk; TOP_N + 1 if missing."""
    return ids.index(gold) + 1 if gold in ids else TOP_N + 1

# ---------- 5. Warm-up (so the first call does not distort latency) ----------
_ = rerank("warm up", hybrid_search("warm up"))

# ---------- 6. Run the 10 questions ----------
before_ranks, after_ranks, latencies = [], [], []

print(f"{'#':<3}{'Before':<8}{'After':<8}Question")
print("-" * 70)
for n, (q, gold) in enumerate(QUESTIONS, 1):
    candidates = hybrid_search(q)            # top 20
    before = position(candidates, gold)

    t0 = time.perf_counter()
    reranked = rerank(q, candidates)         # cross-encoder over 20 pairs
    latencies.append((time.perf_counter() - t0) * 1000)

    after = position(reranked, gold)
    top5 = reranked[:TOP_K]                  # what you would send to the LLM

    before_ranks.append(before)
    after_ranks.append(after)
    print(f"{n:<3}{before:<8}{after:<8}{q}  (in top 5: {gold in top5})")

# ---------- 7. Summary ----------
print()
print(f"Correct chunk rank: before reranking avg {np.mean(before_ranks):.1f} "
      f"-> after reranking avg {np.mean(after_ranks):.1f}")
print(f"Extra latency: +{np.mean(latencies):.0f} ms per question")

print("""
Bi-encoder vs cross-encoder:
1. A bi-encoder embeds the query and each chunk separately, so chunk vectors are precomputed and search is fast, but it is less precise.
2. A cross-encoder reads the query and chunk together in one pass, so it scores relevance much more accurately.
3. It is also much slower, so use the bi-encoder to fetch the top 20, then the cross-encoder to rerank them to the top 5.
""")