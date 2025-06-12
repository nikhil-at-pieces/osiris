#!/usr/bin/env python3
# File: load.py

import os
import sys
import json
import pickle
import logging
import time
from pathlib import Path
from tqdm import tqdm

from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel

# --- CONFIGURATION ---
PROJECT_ID       = os.getenv("PROJECT_ID", "global-cloud-runtime")
REGION           = os.getenv("REGION", "us-central1")
EMBEDDINGS_FILE  = os.getenv("EMBEDDINGS_FILE", "embeddings.pkl")
TEXTS_FILE       = os.getenv("TEXTS_FILE", "texts.json")
MODEL_NAME       = os.getenv("EMBED_MODEL", "gemini-embedding-001")
RETRY_COUNT      = int(os.getenv("RETRY_COUNT", "3"))

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def get_latest_transcript_file(pattern="transcripts_*.jsonl") -> str:
    """Return the most recent transcript file based on modification time."""
    files = sorted(Path().glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return str(files[0]) if files else None


def load_chunks(jsonl_path):
    """Load text chunks from a JSONL file."""
    chunks = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line)
            for chunk in entry.get('chunks', []):
                text = chunk.get('text')
                if text:
                    chunks.append(text)
    return chunks


def embed_texts(model, texts):
    """Get embeddings for a list of texts with retries."""
    embeddings = []
    for text in tqdm(texts, desc="Embedding", unit="chunk"):
        for attempt in range(1, RETRY_COUNT + 1):
            try:
                result = model.get_embeddings([text])
                embeddings.append(result[0].values)
                break
            except Exception as e:
                logging.warning(f"Attempt {attempt} failed: {e}")
                if attempt == RETRY_COUNT:
                    logging.error(f"Failed after {RETRY_COUNT} attempts: {text[:60]}...")
                    embeddings.append(None)
                else:
                    time.sleep(attempt)
    return embeddings


def save_pickle(data, path):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(data, f)
    os.replace(tmp, path)


def save_json(data, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def main():
    start = time.time()

    # --- Resolve input file ---
    input_file = os.getenv("INPUT_FILE") or get_latest_transcript_file()
    if not input_file or not Path(input_file).exists():
        logging.error(f"Input file not found: {input_file}")
        sys.exit(1)

    logging.info(f"📥 Loading from {input_file}")

    # --- Init Vertex AI ---
    aiplatform.init(project=PROJECT_ID, location=REGION)
    model = TextEmbeddingModel.from_pretrained(MODEL_NAME)

    # --- Load Chunks ---
    texts = load_chunks(input_file)
    logging.info(f"Loaded {len(texts)} text chunks")

    # --- Embed ---
    embeddings = embed_texts(model, texts)
    valid_count = sum(1 for e in embeddings if e is not None)
    logging.info(f"Generated {valid_count} valid embeddings")

    # --- Save Results ---
    save_pickle(embeddings, EMBEDDINGS_FILE)
    logging.info(f"Saved embeddings to {EMBEDDINGS_FILE}")

    save_json(texts, TEXTS_FILE)
    logging.info(f"Saved text chunks to {TEXTS_FILE}")

    logging.info(f"✅ Completed in {time.time() - start:.2f}s")


if __name__ == "__main__":
    main()
