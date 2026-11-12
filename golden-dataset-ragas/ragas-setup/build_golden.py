import os
import json
import time
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from pypdf import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from mock_db import rows_as_text

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
LLM_MODEL = os.getenv("GEMINI_LLM_MODEL", "gemini-2.5-flash-lite")
EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "models/gemini-embedding-001")
TOP_K = 3

if not API_KEY:
    raise SystemExit("GOOGLE_API_KEY missing in .env")


def get_llm(temperature=0.0):
    return ChatGoogleGenerativeAI(model=LLM_MODEL, google_api_key=API_KEY, temperature=temperature)


def get_embeddings():
    return GoogleGenerativeAIEmbeddings(model=EMBED_MODEL, google_api_key=API_KEY)


def load_chunks():
    chunks = []
    reader = PdfReader("data/handbook.pdf")
    for page in reader.pages:
        for line in (page.extract_text() or "").splitlines():
            line = line.strip()
            if len(line) >= 30:
                chunks.append(line)
    df = pd.read_csv("data/sales.csv")
    for _, r in df.iterrows():
        chunks.append(
            f"Order {r['order_id']}: customer={r['customer']}, region={r['region']}, "
            f"product={r['product']}, units={r['units']}, unit_price={r['unit_price']} INR, month={r['month']}"
        )
    chunks.extend(rows_as_text())
    return chunks


class Retriever:
    def __init__(self):
        self.emb = get_embeddings()
        self.chunks = load_chunks()
        vecs = np.array(self.emb.embed_documents(self.chunks), dtype=float)
        self.vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)

    def search(self, query, k=TOP_K):
        qv = np.array(self.emb.embed_query(query), dtype=float)
        qv = qv / np.linalg.norm(qv)
        idx = np.argsort(-(self.vecs @ qv))[:k]
        return [self.chunks[i] for i in idx]


PROMPT = """Answer the question using ONLY the context below.
If the context does not contain the answer, reply exactly: I don't know
Keep the answer to one short sentence.

Context:
{context}

Question: {question}
Answer:"""


def _text(content):
    if isinstance(content, list):
        return "".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in content
        ).strip()
    return str(content).strip()


def generate_answer(llm, question, contexts):
    prompt = PROMPT.format(context="\n".join(contexts), question=question)
    for attempt in range(5):
        try:
            return _text(llm.invoke(prompt).content)
        except Exception as e:
            print(f"  LLM retry {attempt + 1}: {e}")
            time.sleep(20)
    return "I don't know"


def run_pipeline_for_dataset(golden_path="golden_30.jsonl", limit=None, out_path="ragas_dataset.json", delay=4):
    with open(golden_path, encoding="utf-8") as f:
        golden = [json.loads(line) for line in f if line.strip()]
    if limit:
        golden = golden[:limit]

    retriever = Retriever()
    llm = get_llm()
    results = []
    for i, g in enumerate(golden, 1):
        contexts = retriever.search(g["question"])
        answer = generate_answer(llm, g["question"], contexts)
        results.append({
            "question": g["question"],
            "answer": answer,
            "contexts": contexts,
            "ground_truth": g["ground_truth"],
        })
        print(f"[{i}/{len(golden)}] {g['question']} -> {answer}")
        time.sleep(delay)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(results)} rows to {out_path}")
    return results
