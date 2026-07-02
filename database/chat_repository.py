"""
database/chat_repository.py
----------------------------
Functions to save and retrieve chat history from MySQL.
"""

from database.db import get_connection


def save_chat(session_id: str, question: str, answer: str, intent: str):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO chat_history (session_id, question, answer, intent)
           VALUES (%s, %s, %s, %s)""",
        (session_id, question, answer, intent),
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_session_history(session_id: str) -> list[dict]:
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT id, session_id, question, answer, intent,
                  created_at
           FROM   chat_history
           WHERE  session_id = %s
           ORDER  BY created_at ASC""",
        (session_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    # Convert datetime objects to strings for JSON serialisation
    for row in rows:
        if row.get("created_at"):
            row["created_at"] = str(row["created_at"])
    return rows
