"""
retriever.py
------------
Manages TWO FAISS vector stores:
  1. knowledge_store  — built from backend/dataset/knowledge.csv  (existing)
  2. learned_store    — built from backend/dataset/learned_solutions.csv (new, self-learning)

Both are used at query time so the chatbot retrieves from both sources.
"""

import csv
import logging
import os

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR      = os.path.join(BASE_DIR, "backend", "dataset")
VECTOR_DIR       = os.path.join(BASE_DIR, "backend", "vector_store")

KNOWLEDGE_CSV    = os.path.join(DATASET_DIR, "knowledge.csv")
LEARNED_CSV      = os.path.join(DATASET_DIR, "learned_solutions.csv")

KNOWLEDGE_INDEX  = os.path.join(VECTOR_DIR, "knowledge.index")
LEARNED_INDEX    = os.path.join(VECTOR_DIR, "learned.index")

os.makedirs(VECTOR_DIR, exist_ok=True)

# ── Embedding model (shared) ─────────────────────────────────────────────────
_model = SentenceTransformer("all-MiniLM-L6-v2")

# ── In-memory document stores ────────────────────────────────────────────────
_knowledge_docs: list[dict] = []   # [{topic, intent, content}]
_learned_docs:   list[dict] = []   # [{topic, question, solution}]

# ── FAISS indexes ────────────────────────────────────────────────────────────
_knowledge_index = None
_learned_index   = None


# ─────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _embed(texts: list[str]) -> np.ndarray:
    vecs = _model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return vecs.astype("float32")


def _build_index(vecs: np.ndarray) -> faiss.IndexFlatIP:
    dim = vecs.shape[1]
    index = faiss.IndexFlatIP(dim)   # inner-product on normalised vecs = cosine sim
    index.add(vecs)
    return index


# ─────────────────────────────────────────────────────────────────────────────
#  Knowledge base (knowledge.csv)
# ─────────────────────────────────────────────────────────────────────────────

def _load_knowledge_csv() -> list[dict]:
    docs = []
    if not os.path.exists(KNOWLEDGE_CSV):
        logger.warning("knowledge.csv not found at %s", KNOWLEDGE_CSV)
        return docs
    with open(KNOWLEDGE_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            content = row.get("content", "").strip()
            if content:
                docs.append({
                    "topic":   row.get("topic", ""),
                    "intent":  row.get("intent", ""),
                    "content": content,
                })
    logger.info("Loaded %d rows from knowledge.csv", len(docs))
    return docs


def _init_knowledge_store():
    global _knowledge_docs, _knowledge_index
    _knowledge_docs = _load_knowledge_csv()
    if not _knowledge_docs:
        return
    texts = [d["content"] for d in _knowledge_docs]
    vecs  = _embed(texts)
    _knowledge_index = _build_index(vecs)
    faiss.write_index(_knowledge_index, KNOWLEDGE_INDEX)
    logger.info("Knowledge FAISS index built and saved.")


def _load_knowledge_store_from_disk():
    global _knowledge_docs, _knowledge_index
    _knowledge_docs = _load_knowledge_csv()
    if not _knowledge_docs:
        return
    _knowledge_index = faiss.read_index(KNOWLEDGE_INDEX)
    logger.info("Knowledge FAISS index loaded from disk.")


def init_knowledge():
    """Call once at startup."""
    if os.path.exists(KNOWLEDGE_INDEX):
        _load_knowledge_store_from_disk()
    else:
        _init_knowledge_store()


# ─────────────────────────────────────────────────────────────────────────────
#  Learned solutions store (learned_solutions.csv)
# ─────────────────────────────────────────────────────────────────────────────

def _load_learned_csv() -> list[dict]:
    docs = []
    if not os.path.exists(LEARNED_CSV):
        return docs
    with open(LEARNED_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            question = row.get("question", "").strip()
            solution = row.get("solution", "").strip()
            if question and solution:
                docs.append({
                    "topic":    row.get("topic", ""),
                    "question": question,
                    "solution": solution,
                })
    logger.info("Loaded %d learned solutions from CSV", len(docs))
    return docs


def rebuild_learned_index():
    """
    Re-read learned_solutions.csv and rebuild the FAISS index.
    Called after every new /learn request so the index stays current.
    """
    global _learned_docs, _learned_index
    _learned_docs = _load_learned_csv()
    if not _learned_docs:
        _learned_index = None
        return
    texts = [d["question"] + " " + d["solution"] for d in _learned_docs]
    vecs  = _embed(texts)
    _learned_index = _build_index(vecs)
    faiss.write_index(_learned_index, LEARNED_INDEX)
    logger.info("Learned FAISS index rebuilt with %d entries.", len(_learned_docs))


def init_learned():
    """Call once at startup."""
    global _learned_docs, _learned_index
    _learned_docs = _load_learned_csv()
    if not _learned_docs:
        return
    if os.path.exists(LEARNED_INDEX):
        _learned_index = faiss.read_index(LEARNED_INDEX)
        logger.info("Learned FAISS index loaded from disk.")
    else:
        rebuild_learned_index()


# ─────────────────────────────────────────────────────────────────────────────
#  Public retrieval API
# ─────────────────────────────────────────────────────────────────────────────

def retrieve_knowledge(query: str, top_k: int = 3) -> str:
    """Return top-k knowledge-base snippets for the query."""
    if _knowledge_index is None or not _knowledge_docs:
        return ""
    vec = _embed([query])
    _, idxs = _knowledge_index.search(vec, min(top_k, len(_knowledge_docs)))
    snippets = []
    for i in idxs[0]:
        if i < 0:
            continue
        doc = _knowledge_docs[i]
        snippets.append(f"[{doc['topic']}] {doc['content']}")
    return "\n\n".join(snippets)


def retrieve_learned(query: str, top_k: int = 3) -> str:
    """
    Return top-k learned solution snippets for the query.
    Returns empty string if nothing has been learned yet.
    """
    if _learned_index is None or not _learned_docs:
        return ""
    vec = _embed([query])
    _, idxs = _learned_index.search(vec, min(top_k, len(_learned_docs)))
    snippets = []
    for i in idxs[0]:
        if i < 0:
            continue
        doc = _learned_docs[i]
        snippets.append(
            f"[User-Reported Fix for '{doc['question']}']: {doc['solution']}"
        )
    return "\n\n".join(snippets)


# ── Initialise both stores when this module is first imported ─────────────────
init_knowledge()
init_learned()
