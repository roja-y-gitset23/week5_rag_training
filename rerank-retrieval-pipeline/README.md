# Rerank Retrieval Pipeline

Two tasks on improving retrieval for a RAG question-answering system:

- **Task 1:** Add a cross-encoder reranker on top of hybrid search and measure the effect.
- **Task 2:** Integrate retrieval into a configurable pipeline controlled by `config.yaml`, then compare reranker on and off.

## Project structure

```
rerank-retrieval-pipeline/
├── README.md
├── rerank_test.py              # Task 1
├── Task2/
│   ├── config.yaml             # Task 2 configuration
│   ├── pipeline.py             # Task 2 configurable pipeline
│   ├── run_comparison.py       # Task 2 reranker on/off comparison
│   └── comparison_table.md     # generated output
└── final_default_configuration.md
```

## Requirements

- Python 3.10 or newer
- Windows PowerShell (commands below), a virtual environment

## Setup

```powershell
cd C:\Rag_Training_Practice\rerank-retrieval-pipeline
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install sentence-transformers rank-bm25 numpy pyyaml
```

The first run downloads two small models from Hugging Face (about 100 MB in total):

- `all-MiniLM-L6-v2` (bi-encoder, embeddings)
- `cross-encoder/ms-marco-MiniLM-L-6-v2` (cross-encoder, reranker)

Optional, to hide the symlink warning on Windows:

```powershell
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
```

---

## Task 1: Cross-Encoder Reranker

### What it does

1. Builds a 30-chunk policy corpus and 10 test questions, each with a known correct chunk.
2. Retrieves the top 20 chunks with hybrid search (BM25 + embeddings, merged with Reciprocal Rank Fusion).
3. Reranks the 20 candidates with the cross-encoder and keeps the top 5.
4. Prints the position of the correct chunk before and after reranking for each question.
5. Measures the extra latency added by reranking (after a warm-up call).

### Run

```powershell
python rerank_test.py
```

### Result

```
Correct chunk rank: before reranking avg 1.2 -> after reranking avg 1.0
Extra latency: +137 ms per question
```

The correct chunk was already near the top for these questions, so the average rank improved only from 1.2 to 1.0. The extra latency is about 137 ms per question on CPU.

### Bi-encoder vs cross-encoder

1. A bi-encoder embeds the query and each chunk separately, so chunk vectors are precomputed and search is fast, but it is less precise.
2. A cross-encoder reads the query and chunk together in one pass, so it scores relevance much more accurately.
3. It is also much slower, so use the bi-encoder to fetch the top 20, then the cross-encoder to rerank them to the top 5.

---

## Task 2: Retrieval Pipeline Integration

### What it does

- Retrieval is configurable through `config.yaml`: `use_bm25`, `use_vector`, `use_reranker`, `top_k`, `chunk_size` (plus `candidate_k`, `chunk_overlap` and the model names). Nothing is hardcoded.
- `run_comparison.py` runs the end-to-end pipeline for 5 questions with the reranker off and on, and prints a comparison table.
- Answers are graded as correct, partly correct or wrong. The script suggests a grade from a keyword check, and the final grades were confirmed manually.

### Final default configuration (`config.yaml`)

```yaml
use_bm25: true
use_vector: true
use_reranker: true
top_k: 5
candidate_k: 20
chunk_size: 25
chunk_overlap: 5
embedding_model: all-MiniLM-L6-v2
reranker_model: cross-encoder/ms-marco-MiniLM-L-6-v2
```

### Run

```powershell
cd Task2
python run_comparison.py
```

This prints the table and saves it to `comparison_table.md`.

### Result

| # | Question | Reranker OFF | Reranker ON |
|---|---|---|---|
| 1 | What is my yearly time-off entitlement? | correct | correct |
| 2 | Which paperwork does a prolonged absence due to illness require? | correct | correct |
| 3 | What is the spending cap on eating while on a business trip? | partly correct | correct |
| 4 | How frequently should my sign-in secret be renewed? | partly correct | correct |
| 5 | How much advance warning is needed to leave the company? | partly correct | correct |

**Correct answers: reranker OFF 2/5, reranker ON 5/5.**

### Why these defaults

| Setting | Default | Reason |
|---|---|---|
| use_bm25 | true | Matches exact terms such as numbers and policy names. |
| use_vector | true | Matches paraphrased questions where the wording differs. |
| use_reranker | true | Raised correct answers from 2/5 to 5/5 for about +137 ms per question. |
| top_k | 5 | Enough context without adding noise. |
| candidate_k | 20 | A wide pool for the reranker to choose from. |
| chunk_size / chunk_overlap | 25 / 5 words | 50-word chunks mixed several policies together; smaller chunks keep each fact focused. |

See `final_default_configuration.md` for the full write-up.

## Changing the configuration

Edit only `Task2/config.yaml` and re-run `run_comparison.py`. For example, set `use_reranker: false` to turn reranking off, or `use_bm25: false` to test vector search alone. At least one of `use_bm25` and `use_vector` must be true.

## Notes

- Task 1 uses a built-in test corpus and does not read `config.yaml`.
- Latency depends on the machine, so expect different values on other computers.
- The pipeline returns the top chunk as an extractive answer. To use an LLM instead, call it inside `answer()` in `pipeline.py` with the retrieved chunks as context.