import faiss
import numpy as np
import pickle
import json
import os
import logging
from tqdm import tqdm

# --- CONFIGURATION ---
EMBEDDINGS_FILE   = os.getenv("EMBEDDINGS_FILE", "embeddings.pkl")
TEXTS_FILE        = os.getenv("TEXTS_FILE", "texts.json")
FAISS_INDEX_FILE  = os.getenv("FAISS_INDEX_FILE", "faiss_index.index")
USE_IVF           = os.getenv("USE_IVF", "False").lower() == "true"
NUM_CLUSTERS      = int(os.getenv("NUM_CLUSTERS", "100"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# --- Load Data ---
logging.info(f"Loading embeddings from '{EMBEDDINGS_FILE}' and texts from '{TEXTS_FILE}'")
with open(EMBEDDINGS_FILE, "rb") as f:
    embeddings = pickle.load(f)
with open(TEXTS_FILE, "r") as f:
    chunks = json.load(f)

valid_data = [(e, t) for e, t in zip(embeddings, chunks) if e is not None]
if not valid_data:
    logging.error("No valid embeddings to index. Exiting.")
    exit(1)

vectors, valid_chunks = zip(*valid_data)
mat = np.array(vectors, dtype="float32")
faiss.normalize_L2(mat)
dim = mat.shape[1]

# --- Build Index ---
if USE_IVF:
    logging.info(f"Using IVF index with {NUM_CLUSTERS} clusters")
    quantizer = faiss.IndexFlatIP(dim)
    index = faiss.IndexIVFFlat(quantizer, dim, NUM_CLUSTERS, faiss.METRIC_INNER_PRODUCT)
    if not index.is_trained:
        logging.info("Training IVF index...")
        index.train(mat)
    index.add(mat)
else:
    index = faiss.IndexFlatIP(dim)
    index.add(mat)

logging.info(f"FAISS index built with {index.ntotal} vectors")

# --- Save Index ---
tmp_index = FAISS_INDEX_FILE + ".tmp"
faiss.write_index(index, tmp_index)
os.replace(tmp_index, FAISS_INDEX_FILE)
logging.info(f"Saved FAISS index to '{FAISS_INDEX_FILE}'")

# --- Save Metadata (optional) ---
meta_file = FAISS_INDEX_FILE + ".meta.json"
with open(meta_file, 'w') as f:
    json.dump({"chunks_file": TEXTS_FILE, "count": index.ntotal}, f, indent=2)
logging.info(f"Saved index metadata to '{meta_file}'")
