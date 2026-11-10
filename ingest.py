import hashlib
import json
import time
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

PDF_DIR = Path("data/pdfs")
CSV_DIR = Path("data/csv")
STORE_DIR = Path("store")
CHUNKS_FILE = STORE_DIR / "chunks.jsonl"
MANIFEST_FILE = STORE_DIR / "manifest.json"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100


# ---------- helpers ----------
def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()


def split_text(text: str):
    text = " ".join(text.split())
    if not text:
        return []
    if len(text) <= CHUNK_SIZE:
        return [text]
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + CHUNK_SIZE])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def load_manifest():
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text())
    return {}


def load_chunks():
    if not CHUNKS_FILE.exists():
        return []
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def save_chunks(chunks):
    with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c) + "\n")


# ---------- loaders ----------
def load_pdf(path: Path, fhash: str):
    reader = PdfReader(str(path))
    chunks = []
    for page_no, page in enumerate(reader.pages, start=1):
        for i, piece in enumerate(split_text(page.extract_text() or "")):
            chunks.append({
                "text": piece,
                "metadata": {
                    "source_type": "pdf",
                    "source": path.name,
                    "page": page_no,
                    "chunk_index": i,
                    "file_hash": fhash,
                },
            })
    return chunks


def load_csv(path: Path, fhash: str):
    df = pd.read_csv(path)
    chunks = []
    for row_no, row in df.iterrows():
        text = f"{path.stem} record: " + ", ".join(f"{col}: {row[col]}" for col in df.columns)
        chunks.append({
            "text": text,
            "metadata": {
                "source_type": "csv",
                "source": path.name,
                "row": int(row_no) + 1,
                "file_hash": fhash,
            },
        })
    return chunks


# ---------- main ----------
def fmt_time(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}m {s}s"


def main():
    start = time.time()
    STORE_DIR.mkdir(exist_ok=True)
    manifest = load_manifest()
    all_chunks = load_chunks()

    summary = {"pdf": {"files": 0, "chunks": 0}, "csv": {"files": 0, "chunks": 0}}
    skipped = 0

    sources = [("pdf", p, load_pdf) for p in sorted(PDF_DIR.glob("*.pdf"))]
    sources += [("csv", p, load_csv) for p in sorted(CSV_DIR.glob("*.csv"))]

    for kind, path, loader in sources:
        fhash = file_hash(path)
        if manifest.get(path.name) == fhash:
            skipped += 1
            print(f"  skipped (unchanged): {path.name}")
            continue
        # remove old chunks of this file if it was changed
        all_chunks = [c for c in all_chunks if c["metadata"]["source"] != path.name]
        new_chunks = loader(path, fhash)
        all_chunks.extend(new_chunks)
        manifest[path.name] = fhash
        summary[kind]["files"] += 1
        summary[kind]["chunks"] += len(new_chunks)
        print(f"  ingested: {path.name} -> {len(new_chunks)} chunks")

    save_chunks(all_chunks)
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2))

    print()
    print(f"PDF: {summary['pdf']['files']} files, {summary['pdf']['chunks']} chunks")
    print(f"CSV: {summary['csv']['files']} files, {summary['csv']['chunks']} chunks")
    print(f"Skipped (unchanged): {skipped} | Time: {fmt_time(time.time() - start)}")


if __name__ == "__main__":
    main()