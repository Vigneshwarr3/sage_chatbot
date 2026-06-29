from typing import Annotated, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    intent: str
    context: str
    learned_context: str   # NEW: extra context from self-learned solutions
