"""Schema-driven memory tools exposed to the LangGraph agent.

Design patterns drawn from common production-chatbot memory systems:
- Tool args are validated by Pydantic before reaching the service layer.
- Atomic facts only — content limited to 1-500 chars, one fact per call.
- Categorization via Literal enum.
- The model decides what to save; we never regex user text.

For the demo, all tools operate on a single user_id="default". Multi-user
support is one parameter flip away (read user_id from a context var or
LangGraph config).
"""

from __future__ import annotations

import logging
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

from memory.service import MAX_CONTENT_LEN, get_default_service

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default"

MemoryCategory = Literal["preference", "fact", "goal", "other"]


# ---------------------------------------------------------------------------
# Argument schemas
# ---------------------------------------------------------------------------


class SaveMemoryArgs(BaseModel):
    """Arguments for save_memory."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=MAX_CONTENT_LEN,
        description=(
            "An atomic fact about the user, in third person, "
            "1-500 chars. Example: 'User is vegetarian'."
        ),
    )
    category: MemoryCategory = Field(
        ...,
        description=(
            "Category of fact. 'preference' for likes/dislikes, "
            "'fact' for biographical info, 'goal' for objectives, "
            "'other' for anything else."
        ),
    )

    @field_validator("content")
    @classmethod
    def _strip_and_check(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("content must not be blank after stripping whitespace")
        return v


class RecallMemoryArgs(BaseModel):
    """Arguments for recall_memory."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=MAX_CONTENT_LEN,
        description="Natural-language query describing what to recall.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of most relevant memories to return (1-10).",
    )

    @field_validator("query")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query must not be blank after stripping whitespace")
        return v


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool("save_memory", args_schema=SaveMemoryArgs)
def save_memory(content: str, category: str) -> str:
    """Persist an atomic fact about the user for future conversations.

    Use this when the user shares information worth remembering across
    sessions: preferences, biographical facts, goals, or constraints.
    Save short, third-person statements (e.g., 'User is vegetarian').
    Do NOT save transient context, the assistant's own opinions, or
    anything the user did not explicitly share.
    """
    svc = get_default_service()
    memory_id = svc.save(user_id=DEFAULT_USER_ID, content=content, category=category)
    return f"Saved memory ({category}): {content[:80]}{'...' if len(content) > 80 else ''}"


@tool("recall_memory", args_schema=RecallMemoryArgs)
def recall_memory(query: str, top_k: int = 5) -> str:
    """Retrieve up to top_k previously-saved memories most relevant to the query.

    Use this proactively when the user's question depends on personal
    context (preferences, past statements, profile facts). Returns a
    formatted list of facts with similarity scores.
    """
    svc = get_default_service()
    hits = svc.recall(user_id=DEFAULT_USER_ID, query=query, top_k=top_k)
    if not hits:
        return "No relevant memories found."
    lines = ["Relevant memories:"]
    for i, h in enumerate(hits, 1):
        lines.append(
            f"{i}. [{h.memory.category}] {h.memory.content} "
            f"(similarity={h.similarity:.3f})"
        )
    return "\n".join(lines)


@tool("list_memories")
def list_memories() -> str:
    """List every memory saved about the user. Use sparingly — prefer recall_memory."""
    svc = get_default_service()
    items = svc.list_all(user_id=DEFAULT_USER_ID)
    if not items:
        return "No memories saved yet."
    lines = [f"Total memories: {len(items)}"]
    for i, m in enumerate(items, 1):
        lines.append(f"{i}. [{m.category}] {m.content}")
    return "\n".join(lines)
