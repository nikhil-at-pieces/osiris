import faiss
import numpy as np
import json
import logging
import re
from functools import lru_cache
from typing import List, Tuple

from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig, Part

# --- CONFIGURATION ---
PROJECT_ID         = "global-cloud-runtime"
REGION             = "us-central1"
FAISS_INDEX        = "faiss_index.index"
METADATA_FILE      = "metadata.json"  # List of dicts: {speaker, timestamp, text}
EMBED_MODEL        = "gemini-embedding-001"
GEN_MODEL_MAIN     = "gemini-2.0-flash"
GEN_MODEL_FALLBACK = "gemini-2.0-flash-lite"

# Retrieval parameters
RETRIEVE_K         = 100   # initial dense retrieval size
RERANK_K           = 20    # final top chunks after hybrid rerank
SCORE_THRESHOLD    = 0.0   # keep all before rerank

# Generation parameters
MAX_OUTPUT_TOKENS  = 3000  # up to 8192 supported
TEMPERATURE        = 0.2   # deterministic
TOP_K_SAMPLING     = 50    # for LLM generation sampling

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# --- Initialize Vertex AI ---
aiplatform.init(project=PROJECT_ID, location=REGION)
embed_model        = TextEmbeddingModel.from_pretrained(EMBED_MODEL)
gen_model_main     = GenerativeModel(GEN_MODEL_MAIN)
gen_model_fallback = GenerativeModel(GEN_MODEL_FALLBACK)

# --- Load FAISS index & metadata ---
index = faiss.read_index(FAISS_INDEX)
with open(METADATA_FILE, 'r') as f:
    metadata = json.load(f)

# --- Cache query embeddings ---
@lru_cache(maxsize=128)
def embed_query(query: str) -> np.ndarray:
    result = embed_model.get_embeddings([query])[0]
    emb = result.values
    q_vec = np.array([emb], dtype="float32")
    faiss.normalize_L2(q_vec)
    return q_vec

# --- Hybrid rerank: combine cosine + keyword match ---
def hybrid_rerank(
    query: str,
    dense_scores: List[float],
    dense_indices: List[int],
    chunks: List[str]
) -> List[Tuple[float,int]]:
    # compute keyword overlap score
    q_tokens = set(re.findall(r"\w+", query.lower()))
    hybrid = []
    for score, idx in zip(dense_scores, dense_indices):
        text = chunks[idx].lower()
        words = re.findall(r"\w+", text)
        overlap = len(q_tokens.intersection(words)) / (len(q_tokens)+1)
        combined = 0.8 * score + 0.2 * overlap
        hybrid.append((combined, idx))
    # sort and pick top RERANK_K
    hybrid.sort(key=lambda x: x[0], reverse=True)
    return hybrid[:RERANK_K]

# --- RAG Query & Generate ---
def answer_question(
    conversation: list,
    use_stream: bool = False,
    temperature: float = None  # Allow override
) -> str:
    # Extract the latest question
    if isinstance(conversation, str):
        # Backward compatibility - if just a string is passed
        latest_question = conversation
        chat_history = ""
    else:
        # Build conversation history for context
        chat_history = ""
        for msg in conversation[:-1]:  # Exclude the latest user question
            role = "User" if msg["role"] == "user" else "Osiris"
            chat_history += f"{role}: {msg['content']}\n"
        
        # Get the latest question
        latest_question = conversation[-1]["content"] if conversation else ""
    
    # 1. Embed query
    q_vec = embed_query(latest_question)

    # 2. Initial dense retrieval
    D, I = index.search(q_vec, RETRIEVE_K)
    scores = D[0].tolist()
    indices = I[0].tolist()
    logging.info(f"Dense retrieval: min={min(scores):.3f}, avg={sum(scores)/len(scores):.3f}, max={max(scores):.3f}")

    # 3. Hybrid rerank
    reranked = hybrid_rerank(latest_question, scores, indices, [m['text'] for m in metadata])
    logging.info(f"Reranked and picked top {RERANK_K} chunks")

    # 4. Build context
    context_lines = []
    for score, idx in reranked:
        rec = metadata[idx]
        context_lines.append(f"[{rec['timestamp']}] {rec['speaker']}: {rec['text']} (score={score:.3f})")
    context_text = "\n\n---\n\n".join(context_lines)

    # 5. Construct prompts with conversation history
    system_prompt = (
        "You are Osiris, an internal AI knowledge assistant for product analytics.\n"
        "Use the context to answer in 2–4 bullet points, paraphrasing key statements and citing speaker & timestamp.\n"
        "Consider previous conversation for context continuity.\n"
        "State any ambiguities."
    )
    
    # Include conversation history in the user prompt
    if chat_history:
        user_prompt = (
            f"Previous conversation:\n{chat_history}\n\n"
            f"Latest question: {latest_question}\n\n"
            f"Context:\n{context_text}"
        )
    else:
        user_prompt = (
            f"Question: {latest_question}\n\n"
            f"Context:\n{context_text}"
        )
    
    full_prompt = system_prompt + "\n\n" + user_prompt

    # Detect if the latest question is creative
    creative_keywords = ["tweet", "twitter", "blog", "post", "creative", "story", "write", "linkedin"]
    latest_question_lower = latest_question.lower()
    is_creative = any(word in latest_question_lower for word in creative_keywords)

    # Set temperature
    temp = temperature
    if temp is None:
        temp = 0.6 if is_creative else TEMPERATURE

    gen_config = GenerationConfig(
        temperature=temp,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        top_k=TOP_K_SAMPLING
    )

    # 7. Generate response
    try:
        if use_stream:
            answer = ''
            for chunk in gen_model_main.generate_content(
                [Part.from_text(full_prompt)],
                generation_config=gen_config,
                stream=True
            ):
                print(chunk.text, end='', flush=True)
                answer += chunk.text
            print()
        else:
            resp = gen_model_main.generate_content(
                [Part.from_text(full_prompt)],
                generation_config=gen_config
            )
            answer = resp.text
    except Exception as e:
        logging.warning(f"Main model failed: {e}, using fallback.")
        resp = gen_model_fallback.generate_content(
            [Part.from_text(full_prompt)],
            generation_config=gen_config
        )
        answer = resp.text

    return answer

# --- CLI Entry Point ---
if __name__ == "__main__":
    question = input("Enter your question: ")
    print("\n=== Answer ===\n", answer_question(question, use_stream=False))
