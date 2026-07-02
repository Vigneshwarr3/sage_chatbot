# syntax=docker/dockerfile:1.7
# Build context is the project root (docker-compose.yml sets `context: .`)
# because app.py, database/ and langchain_chatbot/ live at the repo root,
# not inside backend/.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/backend/.cache

# libgomp1 is required by faiss-cpu at runtime; build-essential covers any
# source builds needed by sentence-transformers' dependency chain.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# torch's default PyPI wheel bundles the CUDA runtime (several GB of nvidia-*
# packages) that this CPU-only container never uses. Installing the CPU-only
# build first satisfies sentence-transformers' torch dependency without ever
# pulling the CUDA variant, cutting the build download by >10x.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch --index-url https://download.pytorch.org/whl/cpu
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt \
    langchain langchain-core langchain-ollama langgraph python-dotenv

COPY app.py .
COPY database ./database
COPY langchain_chatbot ./langchain_chatbot
COPY backend ./backend

EXPOSE 5001

CMD ["python", "app.py"]
