#!/usr/bin/env python3
"""
run_pipeline.py

Orchestrates the full preprocessing & indexing pipeline:
1. tst.py                   → Fetch + chunk GDocs into JSONL
2. load.py                  → Embed text chunks into embeddings.pkl and texts.json
3. generate_metadata.py     → Extract speaker/timestamp/text into metadata.json
4. validate_alignment.py    → Ensure texts.json and metadata.json line up
5. save_to_faiss.py         → Build & save FAISS index (faiss_index.index + .meta.json)
"""

import subprocess
import sys
import logging

# --- Setup logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# --- Ordered steps to run ---
PIPELINE_SCRIPTS = [
    ("1. Fetching + Chunking",       "tst.py"),
    ("2. Generating Embeddings",     "load.py"),
    ("3. Generating Metadata",       "generate_metadata.py"),
    ("4. Validating Alignment",      "validate_alignment.py"),
    ("5. Saving to FAISS Index",     "save_to_faiss.py"),
]

def run_script(description: str, script: str):
    logging.info(f"\n🚀 {description} → {script}")
    result = subprocess.run([sys.executable, script])
    if result.returncode != 0:
        logging.error(f"❌ Failed during: {description}")
        sys.exit(result.returncode)
    logging.info(f"✅ Completed: {description}")

def main():
    for description, script in PIPELINE_SCRIPTS:
        run_script(description, script)
    logging.info("\n🎉 All preprocessing and indexing steps completed successfully.")

if __name__ == "__main__":
    main()
