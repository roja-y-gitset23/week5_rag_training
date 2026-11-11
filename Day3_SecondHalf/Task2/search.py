import json
import re
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

# ---- Load chunks ----
with open("chunks.json", encoding="utf-8") as f:
    chunks = json.load(f)
texts = [c["text"] for c in chunks]
ids = [c["id"] for c in chunks]

# ---- BM25 index ----
def tokenize(text):
    # keeps codes like "hr-204" as ONE token
    return re.findall(r"[a-z0-9\-]+", text.lower())

bm25 = BM25Okapi([tokenize(t) for t in texts])

def bm25_search(query, k=3):
    scores = bm25.get_scores(tokenize(query))
    top = np.argsort(scores)[::-1][:k]
    return [(ids[i], float(scores[i])) for i in top]

# ---- Vector index ----
model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(texts, normalize_embeddings=True)

def vector_search(query, k=3):
    q = model.encode([query], normalize_embeddings=True)[0]
    scores = embeddings @ q  # cosine similarity (vectors are normalized)
    top = np.argsort(scores)[::-1][:k]
    return [(ids[i], float(scores[i])) for i in top]