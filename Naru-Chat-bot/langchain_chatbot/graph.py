"""
graph.py
--------
Compiles the LangGraph StateGraph and exposes a single public function: chat()
"""

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from langchain_chatbot.nodes import rag_node, route_decision, router_node, small_talk_node
from langchain_chatbot.state import ChatState

# ── Build graph ───────────────────────────────────────────────────────────────
_builder = StateGraph(ChatState)

_builder.add_node("router",      router_node)
_builder.add_node("small_talk",  small_talk_node)
_builder.add_node("rag",         rag_node)

_builder.set_entry_point("router")

_builder.add_conditional_edges(
    "router",
    route_decision,
    {
        "small_talk": "small_talk",
        "rag":        "rag",
    }
)

_builder.add_edge("small_talk", END)
_builder.add_edge("rag",        END)

_memory  = MemorySaver()
_graph   = _builder.compile(checkpointer=_memory)


# ── Public API ────────────────────────────────────────────────────────────────

def chat(question: str, session_id: str) -> dict:
    """
    Send a user message and return {"answer": str, "intent": str}.
    The MemorySaver keeps conversation history per session_id automatically.
    """
    config = {"configurable": {"thread_id": session_id}}

    initial_state: ChatState = {
        "messages":        [HumanMessage(content=question)],
        "intent":          "",
        "context":         "",
        "learned_context": "",
    }

    result = _graph.invoke(initial_state, config=config)

    # Last message is always the AI reply
    ai_reply = result["messages"][-1].content
    intent   = result.get("intent", "rag")

    return {"answer": ai_reply, "intent": intent}
