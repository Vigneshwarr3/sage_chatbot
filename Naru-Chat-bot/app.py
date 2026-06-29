import logging
from flask import Flask, jsonify, request
from flask_cors import CORS

from database.chat_repository import get_session_history, save_chat
from langchain_chatbot.graph import chat as lc_chat
from langchain_chatbot.learner import learn_new_solution, get_learned_solutions

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route("/")
def home():
    return "Naru Chatbot is running"


# ─────────────────────────────────────────────
#  /chat  — normal question answering
# ─────────────────────────────────────────────
@app.route("/chat", methods=["POST"])
def chatbot():
    try:
        data = request.get_json()
        question = data.get("message", "").strip()
        session_id = data.get("session_id", "").strip()

        if not question:
            return jsonify({"error": "No question provided"}), 400
        if not session_id:
            return jsonify({"error": "No session_id provided"}), 400

        result = lc_chat(question, session_id)
        answer = result["answer"]
        intent = result["intent"]

        try:
            save_chat(session_id, question, answer, intent)
        except Exception as db_err:
            logger.warning("DB save failed (non-fatal): %s", db_err)

        return jsonify({"question": question, "answer": answer, "intent": intent})

    except Exception:
        logger.exception("Error in /chat")
        return jsonify({"error": "Internal server error"}), 500


# ─────────────────────────────────────────────
#  /learn  — user reports a solution that worked
#  Body: { "session_id": "...",
#           "original_question": "my internet is not connecting",
#           "user_solution": "I restarted the modem and it worked" }
# ─────────────────────────────────────────────
@app.route("/learn", methods=["POST"])
def learn():
    try:
        data = request.get_json()
        session_id       = data.get("session_id", "").strip()
        original_question = data.get("original_question", "").strip()
        user_solution    = data.get("user_solution", "").strip()

        if not original_question or not user_solution:
            return jsonify({"error": "original_question and user_solution are required"}), 400

        result = learn_new_solution(session_id, original_question, user_solution)

        return jsonify({
            "message": "Thank you! I've learned this solution and will include it in future answers.",
            "topic": result.get("topic", ""),
            "saved": True
        })

    except Exception:
        logger.exception("Error in /learn")
        return jsonify({"error": "Internal server error"}), 500


# ─────────────────────────────────────────────
#  /learned_solutions  — see what the bot learned
# ─────────────────────────────────────────────
@app.route("/learned_solutions", methods=["GET"])
def learned_solutions():
    try:
        rows = get_learned_solutions()
        return jsonify(rows)
    except Exception:
        logger.exception("Error in /learned_solutions")
        return jsonify({"error": "Internal server error"}), 500


# ─────────────────────────────────────────────
#  /history/<session_id>
# ─────────────────────────────────────────────
@app.route("/history/<session_id>", methods=["GET"])
def history(session_id):
    try:
        rows = get_session_history(session_id)
        return jsonify(rows)
    except Exception:
        logger.exception("Error in /history")
        return jsonify({"error": "Internal server error"}), 500


# ─────────────────────────────────────────────
#  /batch_chat
# ─────────────────────────────────────────────
@app.route("/batch_chat", methods=["POST"])
def batch_chat():
    try:
        data = request.get_json()
        questions = data.get("questions")
        session_id = data.get("session_id", "batch")

        if not questions:
            return jsonify({"error": "No questions provided"}), 400

        results = []
        for question in questions:
            result = lc_chat(question, session_id)
            answer = result["answer"]
            intent = result["intent"]
            try:
                save_chat(session_id, question, answer, intent)
            except Exception as db_err:
                logger.warning("DB save failed (non-fatal): %s", db_err)
            results.append({"question": question, "answer": answer, "intent": intent})

        return jsonify(results)

    except Exception:
        logger.exception("Error in /batch_chat")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
