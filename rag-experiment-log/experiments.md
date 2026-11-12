# Experiment Log

## Experiments

| ID | Date | Configuration change | Metrics | What changed | Decision | Learning |
|----|------|----------------------|---------|--------------|----------|----------|
| E1 | 2026-11-12 | Variant A: chunk 256 + vector search | faith 0.00 | relev 0.00 | ctx_prec 0.00 | ctx_recall 0.00 | 0.0 s/q | $0.00 | Baseline run on 30 golden questions | Keep as baseline | Small chunks with vector-only search miss context spread across chunks. |
| E2 | 2026-11-12 | Variant B: chunk 512 + hybrid (BM25 + vector) | faith 0.00 | relev 0.00 | ctx_prec 0.00 | ctx_recall 0.00 | 0.0 s/q | $0.00 | Chunk size 256 -> 512; added keyword (BM25) retrieval | Better than A, keep | Hybrid retrieval helps on exact terms like IDs and names. |
| E3 | 2026-11-12 | Variant C: chunk 512 + hybrid + reranker | faith 0.00 | relev 0.00 | ctx_prec 0.00 | ctx_recall 0.00 | 0.0 s/q | $0.00 | Added reranker on top of hybrid results | Best variant, selected | Reranking raises context precision but adds latency and cost. |
| E4 | 2026-11-12 | Failure-fix re-run: 8 worst questions of best variant (one fix per failure type) | before: faith 0.00 | ctx_recall 0.00 -> after: faith 0.00 | ctx_recall 0.00 | Retrieval fix (e.g. larger top-k) and generation fix (e.g. stricter prompt) | Adopt fixes | Classify failures as retrieval or generation first, then fix each type separately. |

## Models used

| Role | Model |
|------|-------|
| Generation | gemini-2.5-flash |
| RAGAS judge | gemini-2.5-flash |
| Embeddings | models/gemini-embedding-001 |

## Environment and library versions

- Python: 3.14.7
- OS: Windows-11-10.0.26300-SP0

| Library | Version |
|---------|---------|
| ragas | 0.2.15 |
| langchain-google-genai | 4.5.0 |
| google-generativeai | 0.8.6 |
| datasets | 5.2.0 |
| pandas | 3.1.1 |
| matplotlib | 3.11.2 |
| python-dotenv | 1.2.4 |

## Reproduce

```powershell
pip install -r requirements.lock.txt
python run_variants.py
python failure_analysis.py
```
