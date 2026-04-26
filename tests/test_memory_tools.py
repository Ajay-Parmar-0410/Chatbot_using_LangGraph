"""Tests for tools/memory_tools.py — schema validation and happy paths.

Uses a temp DB by monkey-patching `get_default_service` so tests don't
touch the real `chatbot2.db`.
"""

from __future__ import annotations

import os
import tempfile

import pytest
from pydantic import ValidationError

from memory.service import MAX_CONTENT_LEN, MemoryService
from tools import memory_tools
from tools.memory_tools import (
    RecallMemoryArgs,
    SaveMemoryArgs,
    list_memories,
    recall_memory,
    save_memory,
)


@pytest.fixture
def temp_service(monkeypatch):
    """Swap the default service for one against a temp DB."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    svc = MemoryService(db_path=path)
    monkeypatch.setattr(memory_tools, "get_default_service", lambda: svc)
    try:
        yield svc
    finally:
        svc.close()
        try:
            os.remove(path)
        except OSError:
            pass


# ---------- Pydantic schema validation ------------------------------------


def test_save_args_rejects_empty_content():
    with pytest.raises(ValidationError):
        SaveMemoryArgs(content="", category="fact")


def test_save_args_rejects_whitespace_only_content():
    with pytest.raises(ValidationError):
        SaveMemoryArgs(content="   ", category="fact")


def test_save_args_rejects_oversized_content():
    with pytest.raises(ValidationError):
        SaveMemoryArgs(content="x" * (MAX_CONTENT_LEN + 1), category="fact")


def test_save_args_rejects_invalid_category():
    with pytest.raises(ValidationError):
        SaveMemoryArgs(content="hi", category="invalid")


def test_save_args_strips_whitespace():
    args = SaveMemoryArgs(content="  hello  ", category="fact")
    assert args.content == "hello"


def test_recall_args_clamps_top_k():
    with pytest.raises(ValidationError):
        RecallMemoryArgs(query="x", top_k=0)
    with pytest.raises(ValidationError):
        RecallMemoryArgs(query="x", top_k=11)


def test_recall_args_default_top_k():
    args = RecallMemoryArgs(query="x")
    assert args.top_k == 5


# ---------- Tool execution (happy paths) ----------------------------------


def test_save_memory_tool_persists(temp_service):
    result = save_memory.invoke({"content": "User likes jazz", "category": "preference"})
    assert "Saved memory" in result
    items = temp_service.list_all("default")
    assert len(items) == 1
    assert "jazz" in items[0].content


def test_recall_memory_tool_returns_relevant(temp_service):
    save_memory.invoke({"content": "User loves Italian food", "category": "preference"})
    save_memory.invoke({"content": "User works in finance", "category": "fact"})
    result = recall_memory.invoke({"query": "favorite cuisine", "top_k": 2})
    assert "Italian food" in result


def test_recall_memory_tool_no_matches(temp_service):
    result = recall_memory.invoke({"query": "anything", "top_k": 5})
    assert "No relevant memories" in result


def test_list_memories_tool_empty(temp_service):
    assert "No memories" in list_memories.invoke({})


def test_list_memories_tool_lists_all(temp_service):
    save_memory.invoke({"content": "fact one", "category": "fact"})
    save_memory.invoke({"content": "fact two", "category": "fact"})
    result = list_memories.invoke({})
    assert "Total memories: 2" in result
    assert "fact one" in result
    assert "fact two" in result


# ---------- Tool invocation through LangChain framework -------------------


def test_save_tool_rejects_bad_args_via_invoke(temp_service):
    """Invoking through LangChain should still validate via Pydantic."""
    with pytest.raises(Exception):  # ValidationError or ToolException
        save_memory.invoke({"content": "", "category": "fact"})


def test_save_tool_rejects_invalid_category_via_invoke(temp_service):
    with pytest.raises(Exception):
        save_memory.invoke({"content": "hi", "category": "not-real"})
