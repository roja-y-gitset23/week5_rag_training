from search import bm25_search, vector_search

POOL = 10  # how many results to take from each method before fusing

def hybrid_search(query, k=3, weight=0.5):
    """
    weight = share given to BM25 (0.0 = vector only, 1.0 = BM25 only)
    RRF score = weight * 1/(60 + bm25_rank) + (1 - weight) * 1/(60 + vector_rank)
    """
    scores = {}
    for rank, (cid, _) in enumerate(bm25_search(query, POOL), start=1):
        scores[cid] = scores.get(cid, 0) + weight * (1 / (60 + rank))
    for rank, (cid, _) in enumerate(vector_search(query, POOL), start=1):
        scores[cid] = scores.get(cid, 0) + (1 - weight) * (1 / (60 + rank))
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]
    return ranked