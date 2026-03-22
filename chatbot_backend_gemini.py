"""
LangGraph chatbot backend using Google Gemini with dual-key failover.

Key design: Both keys use the SAME checkpointer (SQLite) and thread_id,
so chat history is fully consistent regardless of which key handles a request.
The user will never notice a key switch.
"""

import os
import logging
import sqlite3

from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition
from typing import TypedDict, Annotated
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from tools import all_tools

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dual-key LLM wrapper — failover from key1 to key2 transparently
# ---------------------------------------------------------------------------

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_API_KEY_2 = os.getenv("GOOGLE_API_KEY_2", "")

_active_key_index = 0  # 0 = primary, 1 = backup


def _create_llm(api_key):
    """Create a Gemini LLM instance with the given key."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.7,
        convert_system_message_to_human=True,
    )


def _get_keys():
    """Return (primary, backup) keys based on current active index."""
    keys = [GOOGLE_API_KEY, GOOGLE_API_KEY_2]
    return keys[_active_key_index], keys[1 - _active_key_index]


# Create initial LLM instances
_llm_primary = _create_llm(GOOGLE_API_KEY)
_llm_backup = _create_llm(GOOGLE_API_KEY_2)


def get_llm_with_failover():
    """Return the currently active LLM, swapping on failure is handled in chat_node."""
    global _active_key_index
    if _active_key_index == 0:
        return _llm_primary, _llm_backup
    return _llm_backup, _llm_primary


# Expose a plain llm for title generation in app.py
llm = _llm_primary


# ---------------------------------------------------------------------------
# Tools — imported from tools/ package
# ---------------------------------------------------------------------------

tools = all_tools


# ---------------------------------------------------------------------------
# Chat state
# ---------------------------------------------------------------------------

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ---------------------------------------------------------------------------
# Chat node with dual-key failover
# ---------------------------------------------------------------------------

def chat_node(state: ChatState):
    """LLM node with transparent key failover.

    If the primary key fails (rate limit, auth error, etc.), the backup key
    is tried immediately. Chat history is unaffected because messages live in
    the checkpointer (SQLite), not in the LLM client.
    """
    global _active_key_index

    messages = state["messages"]
    primary, backup = get_llm_with_failover()

    # Try primary key first
    try:
        primary_with_tools = primary.bind_tools(tools)
        response = primary_with_tools.invoke(messages)
        return {"messages": [response]}
    except Exception as primary_err:
        logger.warning(
            "Primary Gemini key (index=%d) failed: %s. Switching to backup.",
            _active_key_index, str(primary_err)[:100],
        )

    # Failover to backup key
    try:
        _active_key_index = 1 - _active_key_index  # swap active key
        backup_with_tools = backup.bind_tools(tools)
        response = backup_with_tools.invoke(messages)
        return {"messages": [response]}
    except Exception as backup_err:
        logger.error(
            "Backup Gemini key also failed: %s", str(backup_err)[:100],
        )
        # Return an error message so the user sees something
        error_msg = AIMessage(content="I'm sorry, I'm temporarily unable to respond. Please try again in a moment.")
        return {"messages": [error_msg]}


tool_node = ToolNode(tools)

# ---------------------------------------------------------------------------
# Database & Graph (same checkpointer = consistent history)
# ---------------------------------------------------------------------------

conn = sqlite3.connect(database="chatbot2.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

graph = StateGraph(ChatState)
graph.add_node("Chat_node", chat_node)
graph.add_node("tools", tool_node)
graph.add_edge(START, "Chat_node")
graph.add_conditional_edges("Chat_node", tools_condition)
graph.add_edge("tools", "Chat_node")

chatbot = graph.compile(checkpointer=checkpointer)


def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])
    return list(all_threads)
