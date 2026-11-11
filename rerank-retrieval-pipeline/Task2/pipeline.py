import re
import yaml
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder

# ---------- Documents ----------
DOCS = {
    "leave_policy": (
        "Annual leave: Full-time employees receive 24 days of paid annual leave per calendar year, accrued monthly. "
        "Sick leave: Employees may take up to 10 days of paid sick leave per year; a medical certificate is required after 3 consecutive days. "
        "Maternity leave: Mothers are entitled to 26 weeks of paid maternity leave, which can start up to 4 weeks before the due date. "
        "Paternity leave: Fathers are entitled to 2 weeks of paid paternity leave taken within 3 months of birth. "
        "Carry forward: Up to 5 unused annual leave days can be carried forward to the next year and expire on 31 March. "
        "Public holidays: The company observes 12 public holidays, published in January."
    ),
    "it_security": (
        "Password policy: Passwords must have at least 12 characters and be changed every 90 days. "
        "MFA: Multi-factor authentication is mandatory for email, VPN and the HR portal. "
        "VPN: Connect to the VPN before accessing internal systems from outside the office network. "
        "Data classification: Documents are labelled Public, Internal, Confidential or Restricted. "
        "Incident reporting: Security incidents must be reported to the helpdesk within 1 hour of discovery."
    ),
    "travel_expenses": (
        "Expenses: Travel expenses must be submitted within 30 days with original receipts. "
        "Meal allowance: Meals during business travel are reimbursed up to 40 USD per day. "
        "Hotel: Hotel stays are capped at 150 USD per night in standard cities and 220 USD in major cities. "
        "Training budget: Each employee has a learning budget of 1000 USD per year for courses and certifications."
    ),
    "hr_general": (
        "Probation: New employees serve a 6 month probation period with a notice period of 1 week. "
        "Notice period: After probation, the notice period for resignation is 60 days. "
        "Performance review: Performance reviews happen twice a year, in June and December. "
        "Bonus: Annual bonus is paid in March based on the December review rating. "
        "Health insurance: Health insurance covers the employee, spouse and up to 2 children from the first day. "
        "Payroll: Salaries are paid on the last working day of each month by bank transfer. "
        "Exit: On the last day, return all assets and complete the exit interview with HR."
    ),
}

# ---------- Config ----------
def load_config(path="config.yaml", **overrides):
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg.update(overrides)
    return cfg

# ---------- Helpers ----------
def tok(text):
    return re.findall(r"\w+", text.lower())

def chunk_text(text, size, overlap):
    words = text.split()
    step = max(size - overlap, 1)
    chunks = []
    for start in range(0, len(words), step):
        piece = words[start:start + size]
        if piece:
            chunks.append(" ".join(piece))
        if start + size >= len(words):
            break
    return chunks

_MODELS = {}
def get_model(kind, name):
    if (kind, name) not in _MODELS:
        _MODELS[(kind, name)] = SentenceTransformer(name) if kind == "bi" else CrossEncoder(name)
    return _MODELS[(kind, name)]

# ---------- Pipeline ----------
class RetrievalPipeline:
    def __init__(self, cfg):
        if not (cfg["use_bm25"] or cfg["use_vector"]):
            raise ValueError("Enable at least one of use_bm25 / use_vector")
        self.cfg = cfg

        self.chunks = []
        for source, text in DOCS.items():
            for c in chunk_text(text, cfg["chunk_size"], cfg["chunk_overlap"]):
                self.chunks.append({"source": source, "text": c})
        texts = [c["text"] for c in self.chunks]

        self.bm25 = BM25Okapi([tok(t) for t in texts]) if cfg["use_bm25"] else None
        self.bi = get_model("bi", cfg["embedding_model"]) if cfg["use_vector"] else None
        self.emb = self.bi.encode(texts, normalize_embeddings=True) if self.bi else None
        self.cross = get_model("cross", cfg["reranker_model"]) if cfg["use_reranker"] else None

    @staticmethod
    def _rank(scores):
        return [int(i) for i in np.argsort(-scores)]

    def retrieve(self, query):
        cfg = self.cfg
        n = max(cfg["candidate_k"], cfg["top_k"])

        rankings = []
        if self.bm25 is not None:
            rankings.append(self._rank(self.bm25.get_scores(tok(query))))
        if self.emb is not None:
            q = self.bi.encode(query, normalize_embeddings=True)
            rankings.append(self._rank(self.emb @ q))

        fused = {}  # Reciprocal Rank Fusion
        for ranking in rankings:
            for rank, idx in enumerate(ranking):
                fused[idx] = fused.get(idx, 0) + 1 / (60 + rank + 1)
        cand = [i for i, _ in sorted(fused.items(), key=lambda x: -x[1])][:n]

        if self.cross is not None:
            scores = self.cross.predict([(query, self.chunks[i]["text"]) for i in cand])
            cand = [cand[i] for i in np.argsort(-scores)]

        return [self.chunks[i] for i in cand[:cfg["top_k"]]]

    def answer(self, query):
        hits = self.retrieve(query)
        # Extractive answer: the best chunk. Replace with an LLM call if your project has one.
        return {"answer": hits[0]["text"], "source": hits[0]["source"], "hits": hits}