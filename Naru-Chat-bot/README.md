# Naru — Networking Chatbot (with Self-Learning)

A stateful networking assistant powered by **LangGraph + Ollama (Llama 3.1 8B)** with a React UI, MySQL chat history, and a **self-learning feature** that lets the chatbot learn from solutions users report.

---

## What's New — Self-Learning Feature

When the chatbot gives troubleshooting steps and the user finds a **different solution** on their own, they can click:

> **✅ I solved it differently — teach Naru!**

A panel slides up where the user describes what they actually did. Naru:
1. Extracts a topic tag using the LLM
2. Saves the solution to `backend/dataset/learned_solutions.csv`
3. Rebuilds the FAISS vector index in real-time
4. Saves to MySQL (`learned_solutions` table)

From that point on, whenever a **similar question** is asked, Naru retrieves the user-reported fix and includes it in its answer, labelled clearly as:

> **✅ Also works (user-reported fix):** ...

---

## Architecture

```
Browser (React + Vite)
        │
        │  POST /chat   { message, session_id }
        │  POST /learn  { original_question, user_solution, session_id }
        ▼
┌──────────────────────────────────────────────┐
│              Flask API  (app.py)             │
│  /chat  /learn  /learned_solutions  /history │
└─────────────────┬────────────────────────────┘
                  │
         ┌────────┴────────┐
         ▼                 ▼
  LangGraph chatbot    learner.py
  (graph.py)           ├── extract topic via LLM
  ├── router_node      ├── append learned_solutions.csv
  ├── small_talk_node  └── rebuild FAISS learned index
  └── rag_node
      ├── retrieve_knowledge()   ← knowledge.csv FAISS
      └── retrieve_learned()     ← learned_solutions.csv FAISS
                  │
                  ▼
           Ollama (llama3.1:8b)
                  │
                  ▼
              MySQL
     (chat_history + learned_solutions)
```

---

## Project Structure

```
Naru-Chat-bot/
├── app.py                               # Flask entry point
├── .env                                 # Ollama config
├── requirements.txt
│
├── langchain_chatbot/                   # LangGraph chatbot engine
│   ├── __init__.py
│   ├── config.py                        # Loads env vars
│   ├── state.py                         # ChatState (messages, intent, context, learned_context)
│   ├── retriever.py                     # FAISS for knowledge + learned solutions
│   ├── nodes.py                         # router / small_talk / rag nodes
│   ├── graph.py                         # Compiled StateGraph + chat() function
│   └── learner.py                       # NEW: self-learning logic
│
├── backend/
│   ├── dataset/
│   │   ├── knowledge.csv                # Networking knowledge base
│   │   └── learned_solutions.csv        # Auto-populated by /learn endpoint
│   └── vector_store/                    # FAISS indexes (auto-generated)
│
├── database/
│   ├── __init__.py
│   ├── schema.sql                       # Creates chat_history + learned_solutions tables
│   ├── db.py                            # MySQL connection pool
│   └── chat_repository.py              # save_chat() / get_session_history()
│
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── main.jsx
        ├── App.jsx                      # Chat UI with "I solved it!" button
        └── App.css
```

---

## Setup

### 1. Ollama

```bash
# Install and start
ollama serve

# Pull the model
ollama pull llama3.1:8b
```

### 2. MySQL

```bash
mysql -u root -p --port 3307 < database/schema.sql
```

Edit `database/db.py` with your credentials.

### 3. Backend

```bash
conda create -n naru_bot python=3.12
conda activate naru_bot
pip install -r requirements.txt
python app.py
```

Flask starts on `http://localhost:5001`.

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

UI at `http://localhost:5173`.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Send a question, get an answer |
| POST | `/learn` | Report a user solution (self-learning) |
| GET  | `/learned_solutions` | View all learned solutions |
| GET  | `/history/<session_id>` | Chat history for a session |
| POST | `/batch_chat` | Multiple questions at once |

### POST /learn

```json
{
  "session_id": "abc-123",
  "original_question": "my internet is not connecting",
  "user_solution": "I restarted the modem by unplugging it for 30 seconds"
}
```

Response:
```json
{
  "message": "Thank you! I've learned this solution and will include it in future answers.",
  "topic": "Modem Restart",
  "saved": true
}
```

---

## How Self-Learning Works

```
User asks: "My internet is not connecting"
Bot gives steps 1, 2, 3...

User tries something else → it works!
User clicks: ✅ I solved it differently — teach Naru!

User types: "I unplugged the modem for 30 seconds and it worked"
           → Saved to learned_solutions.csv + FAISS rebuilt

Next user asks: "WiFi not working"
Bot responds with normal steps PLUS:
  ✅ Also works (user-reported fix): "I unplugged the modem for 30 seconds and it worked"
```
