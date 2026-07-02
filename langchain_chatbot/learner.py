"""
learner.py
----------
Handles the self-learning feature:
  - Receives a user-reported solution
  - Extracts the topic using Ollama
  - Appends it to backend/dataset/learned_solutions.csv
  - Rebuilds the FAISS learned index so future queries include it
  - Saves the learning event to MySQL (learned_solutions table)
"""

import csv
import logging
import os
from datetime import datetime

from langchain_ollama import ChatOllama

from langchain_chatbot.config import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "backend", "dataset")
LEARNED_CSV = os.path.join(DATASET_DIR, "learned_solutions.csv")

os.makedirs(DATASET_DIR, exist_ok=True)

_llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)

# CSV columns
CSV_COLUMNS = ["id", "topic", "question", "solution", "session_id", "created_at"]


def _ensure_csv_exists():
    """Create the CSV with headers if it doesn't exist."""
    if not os.path.exists(LEARNED_CSV):
        with open(LEARNED_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()


def _get_next_id() -> int:
    """Read the CSV and return max(id) + 1."""
    _ensure_csv_exists()
    max_id = 0
    with open(LEARNED_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                max_id = max(max_id, int(row.get("id", 0)))
            except ValueError:
                pass
    return max_id + 1


def _extract_topic(question: str, solution: str) -> str:
    """Ask Ollama to extract a short networking topic tag from the Q&A."""
    prompt = (
        f"Given this networking question and its solution, "
        f"give ONE short topic tag (2-4 words, e.g. 'WiFi Reconnect', 'DNS Flush', 'IP Reset').\n\n"
        f"Question: {question}\n"
        f"Solution: {solution}\n\n"
        f"Topic tag (only the tag, nothing else):"
    )
    try:
        response = _llm.invoke(prompt)
        topic = response.content.strip().split("\n")[0].strip('"\'').strip()
        return topic[:60]  # limit length
    except Exception:
        logger.warning("Topic extraction failed, using fallback.")
        return "General Networking"


def _append_to_csv(row: dict):
    _ensure_csv_exists()
    with open(LEARNED_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writerow(row)


def _save_to_db(row: dict):
    """Save learned solution to MySQL. Non-fatal if DB is unavailable."""
    try:
        from database.db import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO learned_solutions
               (session_id, question, solution, topic, created_at)
               VALUES (%s, %s, %s, %s, %s)""",
            (row["session_id"], row["question"], row["solution"],
             row["topic"], row["created_at"])
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.warning("DB save for learned solution failed (non-fatal): %s", e)


# ─────────────────────────────────────────────────────────────────────────────
#  Public functions
# ─────────────────────────────────────────────────────────────────────────────

def learn_new_solution(session_id: str, original_question: str, user_solution: str) -> dict:
    """
    1. Extract topic via LLM
    2. Append to learned_solutions.csv
    3. Rebuild FAISS learned index
    4. Save to MySQL
    Returns the saved row dict.
    """
    topic      = _extract_topic(original_question, user_solution)
    new_id     = _get_next_id()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = {
        "id":         new_id,
        "topic":      topic,
        "question":   original_question,
        "solution":   user_solution,
        "session_id": session_id,
        "created_at": created_at,
    }

    # Save to CSV
    _append_to_csv(row)
    logger.info("Learned solution #%d saved to CSV: [%s]", new_id, topic)

    # Rebuild FAISS index so retriever picks it up immediately
    from langchain_chatbot.retriever import rebuild_learned_index
    rebuild_learned_index()

    # Save to DB (non-fatal)
    _save_to_db(row)

    return row


def get_learned_solutions() -> list[dict]:
    """Return all learned solutions from the CSV."""
    _ensure_csv_exists()
    rows = []
    with open(LEARNED_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows
