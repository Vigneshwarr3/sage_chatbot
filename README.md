# Sage — Networking Chatbot (with Self-Learning)

A stateful networking assistant powered by **LangGraph + Ollama (Llama 3.1 8B)** with a React UI, MySQL chat history, and a **self-learning feature** that lets the chatbot learn from solutions users report.

---

## What's New — Self-Learning Feature

When the chatbot gives troubleshooting steps and the user finds a **different solution** on their own, they can click:

> **✅ I solved it differently — teach Sage!**

A panel slides up where the user describes what they actually did. Sage:
1. Extracts a topic tag using the LLM
2. Saves the solution to `backend/dataset/learned_solutions.csv`
3. Rebuilds the FAISS vector index in real-time
4. Saves to MySQL (`learned_solutions` table)

From that point on, whenever a **similar question** is asked, Sage retrieves the user-reported fix and includes it in its answer, labelled clearly as:

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
           Ollama (llama3.2:3b)
                  │
                  ▼
              MySQL
     (chat_history + learned_solutions)
```

---

## Project Structure

```
Sage-Chat-bot/
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

# Pull the model (llama3.2:3b is a lighter, faster option for CPU-only
# laptops; swap for llama3.1:8b if you have the hardware and want higher
# answer quality)
ollama pull llama3.2:3b
```

### 2. MySQL

```bash
mysql -u root -p --port 3307 < database/schema.sql
```

Edit `database/db.py` with your credentials.

### 3. Backend

```bash
conda create -n Sage_bot python=3.12
conda activate Sage_bot
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

## Running with Docker Compose

The whole stack — MySQL, Ollama, the Flask/LangGraph backend, and the React
frontend — can be run with a single command via `docker-compose.yml`.

### 1. Configure environment

```bash
cp .env.example .env
# then edit .env and set a real MYSQL_ROOT_PASSWORD
```

### 2. Start everything

```bash
docker compose up -d --build
```

First run will: build the backend/frontend images, start MySQL and
auto-run `database/schema.sql` (creates `chat_history` and
`learned_solutions` tables), start Ollama, and run a one-shot
`ollama-pull` sidecar that downloads the model set by `OLLAMA_MODEL` in
`.env` (defaults to `llama3.2:3b`). The model pull can take
several minutes depending on your connection — the backend will start in
parallel but chat responses will fail until the pull finishes.

### 3. Verify each service

| Service | Check |
|---|---|
| **mysql** | `docker compose ps mysql` should show `healthy`. Or: `docker compose exec mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "SHOW TABLES;" ai_chatbot` — should list `chat_history` and `learned_solutions`. |
| **ollama** | `docker compose ps ollama` should show `healthy`. Or: `curl http://localhost:11434/api/tags` — should return JSON. Confirm the model downloaded: `docker compose exec ollama ollama list` should include `llama3.2:3b` (or whatever `OLLAMA_MODEL` is set to). |
| **backend** | `curl http://localhost:5001/` → `Sage Chatbot is running`. Then `curl -X POST http://localhost:5001/chat -H "Content-Type: application/json" -d '{"message":"hi","session_id":"test"}'` should return a JSON answer. |
| **frontend** | Open `http://localhost:5173` in a browser — the chat UI should load and sending a message should get a reply (proxied through nginx to the backend). |

### 4. Logs / troubleshooting

```bash
docker compose logs -f backend      # backend errors (e.g. Ollama not ready yet)
docker compose logs -f ollama-pull  # model download progress
```

### 5. Stop / reset

```bash
docker compose down          # stop containers, keep volumes (DB data, models)
docker compose down -v       # also wipe MySQL data and downloaded models
```

The FAISS vector store (`backend/vector_store/`) is bind-mounted, so it
persists on the host across `docker compose down`/`up` cycles.

---

## How Self-Learning Works

```
User asks: "My internet is not connecting"
Bot gives steps 1, 2, 3...

User tries something else → it works!
User clicks: ✅ I solved it differently — teach Sage!

User types: "I unplugged the modem for 30 seconds and it worked"
           → Saved to learned_solutions.csv + FAISS rebuilt

Next user asks: "WiFi not working"
Bot responds with normal steps PLUS:
  ✅ Also works (user-reported fix): "I unplugged the modem for 30 seconds and it worked"
```
