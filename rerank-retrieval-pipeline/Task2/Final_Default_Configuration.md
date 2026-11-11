# Retrieval Pipeline: Final Default Configuration

Task 2: Retrieval Pipeline Integration

## 1. Purpose

The retrieval pipeline is configurable from a single file, `config.yaml`, so no setting is hardcoded in the code. This document records the final default configuration, the reason for each choice, and the reranker on/off comparison.

## 2. Final default configuration (`config.yaml`)

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

## 3. Why each default was chosen

| Setting | Default | Reason |
|---|---|---|
| use_bm25 | true | Keyword search matches exact terms such as numbers, amounts and policy names (for example "90 days" or "40 USD"), which embeddings can miss. |
| use_vector | true | Embedding search matches paraphrased questions where the wording differs from the document (for example "time-off" versus "annual leave"). |
| use_reranker | true | The cross-encoder reads the question and chunk together and moves the correct chunk to the top. In the on/off test, correct answers improved from 2/5 to 5/5. The extra cost was about +137 ms per question (Task 1 measurement). |
| top_k | 5 | Five chunks give enough context for a correct answer without adding noise or extra length. |
| candidate_k | 20 | The reranker can only promote chunks that are in its candidate pool, so a pool of 20 gives it enough choice while keeping latency low. |
| chunk_size | 25 words | With 50-word chunks, several policies were mixed in one chunk and answers started with the wrong topic. Smaller chunks keep each chunk focused on one fact. |
| chunk_overlap | 5 words | A small overlap stops a fact from being split across two chunks without adding much duplicate text. |
| embedding_model | all-MiniLM-L6-v2 | Small, fast and accurate enough for short policy text; runs on CPU. |
| reranker_model | cross-encoder/ms-marco-MiniLM-L-6-v2 | A light cross-encoder with good ranking quality at CPU-friendly speed. |

## 4. Reranker on/off comparison

Five questions were run through the full pipeline with `use_reranker` set to false and then true. Each answer was graded manually as correct, partly correct or wrong.

| # | Question | Reranker OFF | Reranker ON |
|---|---|---|---|
| 1 | What is my yearly time-off entitlement? | correct | correct |
| 2 | Which paperwork does a prolonged absence due to illness require? | correct | correct |
| 3 | What is the spending cap on eating while on a business trip? | partly correct | correct |
| 4 | How frequently should my sign-in secret be renewed? | partly correct | correct |
| 5 | How much advance warning is needed to leave the company? | partly correct | correct |

**Result: correct answers with reranker OFF 2/5, with reranker ON 5/5.**

Grading notes:

- **Correct:** the top answer contains the right fact.
- **Partly correct (OFF, Q3 to Q5):** the top answer was about a wrong topic (bonus, carry forward, sick leave), although the right chunk was still inside the top 5.
- With the reranker ON, the right chunk was moved to first place for all three of those questions.

## 5. Conclusion

The default keeps both retrieval methods and the reranker on. Hybrid search finds the right chunk for both exact and paraphrased questions, and the reranker moves it to first place where it was not ranked first, improving correct answers from 2/5 to 5/5. The added latency of about 137 ms per question is acceptable for an internal question-answering tool, where accuracy matters more than a few milliseconds. If speed becomes more important, `use_reranker` can be set to false in `config.yaml` without any code change.