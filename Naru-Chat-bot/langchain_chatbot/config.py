import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
