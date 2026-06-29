"""
nodes.py
--------
LangGraph node functions:
  - router_node       : classifies the message as small_talk or networking
  - small_talk_node   : handles greetings / meta questions
  - rag_node          : retrieves knowledge + learned solutions, calls Ollama
"""

import logging

from langchain_core.messages import AIMessage, HumanMessage
from langchain_ollama import ChatOllama

from langchain_chatbot.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from langchain_chatbot.retriever import retrieve_knowledge, retrieve_learned
from langchain_chatbot.state import ChatState

logger = logging.getLogger(__name__)

_llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)

SMALL_TALK_INTENTS = {
    "hi", "hello", "hey", "thanks", "thank you",
    "bye", "goodbye", "who are you", "what are you",
    "what can you do", "help",
}


# ─────────────────────────────────────────────────────────────────────────────
#  Router node
# ─────────────────────────────────────────────────────────────────────────────

def router_node(state: ChatState) -> ChatState:
    last_msg = state["messages"][-1].content.lower().strip()
    if any(t in last_msg for t in SMALL_TALK_INTENTS):
        return {**state, "intent": "small_talk"}
    return {**state, "intent": "rag"}


# ─────────────────────────────────────────────────────────────────────────────
#  Small-talk node
# ─────────────────────────────────────────────────────────────────────────────

def small_talk_node(state: ChatState) -> ChatState:
    last_msg = state["messages"][-1].content.lower().strip()

    if any(g in last_msg for g in ["hi", "hello", "hey"]):
        reply = (
            "Hi! I'm Naru, your networking assistant. "
            "Ask me anything about WiFi, DNS, routers, or connectivity issues!"
        )
    elif any(t in last_msg for t in ["thanks", "thank you"]):
        reply = "You're welcome! Let me know if you have more networking questions."
    elif any(b in last_msg for b in ["bye", "goodbye"]):
        reply = "Goodbye! Come back anytime you have networking questions."
    elif any(w in last_msg for w in ["who are you", "what are you"]):
        reply = (
            "I'm Naru, an AI-powered networking chatbot. "
            "I can help you troubleshoot connectivity issues, explain networking concepts, "
            "and I even learn from solutions that work for you!"
        )
    else:
        reply = (
            "I specialise in networking topics — WiFi, DNS, IP addressing, routers, "
            "and troubleshooting. What would you like to know?"
        )

    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=reply)],
        "intent": "small_talk",
    }


# ─────────────────────────────────────────────────────────────────────────────
#  RAG node  (knowledge + learned solutions)
# ─────────────────────────────────────────────────────────────────────────────

def rag_node(state: ChatState) -> ChatState:
    query = state["messages"][-1].content

    # 1. Retrieve from knowledge base
    knowledge_ctx = retrieve_knowledge(query, top_k=3)

    # 2. Retrieve from learned solutions (may be empty if nothing learned yet)
    learned_ctx = retrieve_learned(query, top_k=3)

    # 3. Build conversation history string (last 6 turns)
    history_msgs = state["messages"][:-1][-6:]
    history_str = "\n".join(
        f"{'User' if isinstance(m, HumanMessage) else 'Naru'}: {m.content}"
        for m in history_msgs
    )

    # 4. Build prompt — learned section is included only when it has content
    learned_section = ""
    if learned_ctx.strip():
        learned_section = f"""
---
**Community-Reported Solutions (learned from real users):**
{learned_ctx}
---
IMPORTANT: When answering, include the community-reported solutions above as
additional steps or alternatives. Label them clearly as "✅ Also works (user-reported fix):".
"""

    prompt = f"""You are Naru, an expert networking assistant.
Use the knowledge base and conversation history below to answer the user's question.
Be clear, structured, and practical. Use numbered steps for troubleshooting.

=== Knowledge Base ===
{knowledge_ctx if knowledge_ctx else "No specific knowledge base entry found."}
{learned_section}
=== Conversation History ===
{history_str if history_str else "This is the start of the conversation."}

=== User Question ===
{query}

Answer:"""

    try:
        response = _llm.invoke(prompt)
        answer = response.content
    except Exception as e:
        logger.exception("Ollama inference failed")
        answer = "Sorry, I'm having trouble connecting to my AI engine right now. Please try again."

    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=answer)],
        "intent": "rag",
        "context": knowledge_ctx,
        "learned_context": learned_ctx,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Router decision function (used in graph.py)
# ─────────────────────────────────────────────────────────────────────────────

def route_decision(state: ChatState) -> str:
    return state.get("intent", "rag")
