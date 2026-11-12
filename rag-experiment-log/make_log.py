import subprocess
import sys
import platform
from datetime import date
from importlib import metadata

# ====== EDIT THESE ======
GEN_MODEL = "gemini-2.5-flash"          # exact generation model you used
JUDGE_MODEL = "gemini-2.5-flash"        # exact RAGAS judge model you used
EMBED_MODEL = "models/gemini-embedding-001"  # exact embedding model you used
RUN_DATE = str(date.today())            # or set e.g. "2026-11-10" per experiment

# Metrics order: faithfulness, answer_relevancy, context_precision, context_recall
EXPERIMENTS = [
    {
        "id": "E1",
        "date": RUN_DATE,
        "config": "Variant A: chunk 256 + vector search",
        "metrics": "faith 0.00 | relev 0.00 | ctx_prec 0.00 | ctx_recall 0.00 | 0.0 s/q | $0.00",
        "changed": "Baseline run on 30 golden questions",
        "decision": "Keep as baseline",
        "learning": "Small chunks with vector-only search miss context spread across chunks.",
    },
    {
        "id": "E2",
        "date": RUN_DATE,
        "config": "Variant B: chunk 512 + hybrid (BM25 + vector)",
        "metrics": "faith 0.00 | relev 0.00 | ctx_prec 0.00 | ctx_recall 0.00 | 0.0 s/q | $0.00",
        "changed": "Chunk size 256 -> 512; added keyword (BM25) retrieval",
        "decision": "Better than A, keep",
        "learning": "Hybrid retrieval helps on exact terms like IDs and names.",
    },
    {
        "id": "E3",
        "date": RUN_DATE,
        "config": "Variant C: chunk 512 + hybrid + reranker",
        "metrics": "faith 0.00 | relev 0.00 | ctx_prec 0.00 | ctx_recall 0.00 | 0.0 s/q | $0.00",
        "changed": "Added reranker on top of hybrid results",
        "decision": "Best variant, selected",
        "learning": "Reranking raises context precision but adds latency and cost.",
    },
    {
        "id": "E4",
        "date": RUN_DATE,
        "config": "Failure-fix re-run: 8 worst questions of best variant (one fix per failure type)",
        "metrics": "before: faith 0.00 | ctx_recall 0.00 -> after: faith 0.00 | ctx_recall 0.00",
        "changed": "Retrieval fix (e.g. larger top-k) and generation fix (e.g. stricter prompt)",
        "decision": "Adopt fixes",
        "learning": "Classify failures as retrieval or generation first, then fix each type separately.",
    },
]

PACKAGES = [
    "ragas", "langchain-google-genai", "google-generativeai", "datasets",
    "pandas", "matplotlib", "python-dotenv",
]
# ========================


def version_of(pkg):
    try:
        return metadata.version(pkg)
    except metadata.PackageNotFoundError:
        return "not installed"


lines = []
lines.append("# Experiment Log\n")
lines.append("## Experiments\n")
lines.append("| ID | Date | Configuration change | Metrics | What changed | Decision | Learning |")
lines.append("|----|------|----------------------|---------|--------------|----------|----------|")
for e in EXPERIMENTS:
    lines.append(
        f"| {e['id']} | {e['date']} | {e['config']} | {e['metrics']} | "
        f"{e['changed']} | {e['decision']} | {e['learning']} |"
    )

lines.append("\n## Models used\n")
lines.append("| Role | Model |")
lines.append("|------|-------|")
lines.append(f"| Generation | {GEN_MODEL} |")
lines.append(f"| RAGAS judge | {JUDGE_MODEL} |")
lines.append(f"| Embeddings | {EMBED_MODEL} |")

lines.append("\n## Environment and library versions\n")
lines.append(f"- Python: {platform.python_version()}")
lines.append(f"- OS: {platform.platform()}")
lines.append("")
lines.append("| Library | Version |")
lines.append("|---------|---------|")
for p in PACKAGES:
    lines.append(f"| {p} | {version_of(p)} |")

lines.append("\n## Reproduce\n")
lines.append("```powershell")
lines.append("pip install -r requirements.lock.txt")
lines.append("python run_variants.py")
lines.append("python failure_analysis.py")
lines.append("```")

with open("experiments.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

freeze = subprocess.run(
    [sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True
).stdout
with open("requirements.lock.txt", "w", encoding="utf-8") as f:
    f.write(freeze)

print("Created experiments.md and requirements.lock.txt")