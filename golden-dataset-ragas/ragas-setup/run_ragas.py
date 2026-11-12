import nest_asyncio
nest_asyncio.apply = lambda *args, **kwargs: None

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import argparse
import numpy as np
import pandas as pd
from ragas import evaluate, EvaluationDataset, RunConfig
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import (
    Faithfulness,
    ResponseRelevancy,
    LLMContextPrecisionWithReference,
    LLMContextRecall,
)
from rag_pipeline import run_pipeline_for_dataset, get_llm, get_embeddings

parser = argparse.ArgumentParser()
parser.add_argument("--n", type=int, default=5, help="number of golden questions (5 first, then 30)")
args = parser.parse_args()

rows = run_pipeline_for_dataset(limit=args.n, out_path=f"ragas_dataset_{args.n}.json")

dataset = EvaluationDataset.from_list([
    {
        "user_input": r["question"],
        "retrieved_contexts": r["contexts"],
        "response": r["answer"],
        "reference": r["ground_truth"],
    }
    for r in rows
])

judge_llm = LangchainLLMWrapper(get_llm())
judge_emb = LangchainEmbeddingsWrapper(get_embeddings())

result = evaluate(
    dataset=dataset,
    metrics=[
        Faithfulness(),
        ResponseRelevancy(),
        LLMContextPrecisionWithReference(),
        LLMContextRecall(),
    ],
    llm=judge_llm,
    embeddings=judge_emb,
    run_config=RunConfig(timeout=300, max_retries=10, max_workers=2),
    raise_exceptions=False,
    show_progress=True,
)

df = result.to_pandas()
for col in list(df.columns):
    if "precision" in col:
        df = df.rename(columns={col: "context_precision"})

metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
df["question"] = [r["question"] for r in rows]

pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 60)
print("\nPer-question metrics")
print(df[["question"] + metrics].round(2).to_string(index=False))

df.to_csv(f"ragas_scores_{args.n}.csv", index=False)

if df[metrics].isna().all().all():
    raise SystemExit("All metrics are NaN - evaluation failed, see errors above.")

avg = {m: float(np.nanmean(df[m].astype(float))) for m in metrics}
print("\nAverage")
print(f"faithfulness: {avg['faithfulness']:.2f} | answer_relevancy: {avg['answer_relevancy']:.2f}")
print(f"context_precision: {avg['context_precision']:.2f} | context_recall: {avg['context_recall']:.2f}")