"""Tests for memory.service.MemoryService.

Covers:
- save -> list_all roundtrip
- save -> recall returns the saved memory
- namespace isolation (user A vs user B)
- delete removes from list and embedding cache
- input validation rejects bad inputs
- semantic ranking (related items rank above unrelated ones)
"""

from __future__ import annotations

import os
import tempfile

import pytest

from memory.service import (
    MAX_CONTENT_LEN,
    Memory,
    MemoryService,
    VALID_CATEGORIES,
)


@pytest.fixture
def svc():
    """Fresh MemoryService against a temp SQLite file. Cleaned up after test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    service = MemoryService(db_path=path)
    try:
        yield service
    finally:
        service.close()
        try:
            os.remove(path)
        except OSError:
            pass


# ---------- save / list / get ---------------------------------------------


def test_save_returns_id_and_persists(svc):
    mid = svc.save(user_id="u1", content="User is vegetarian", category="preference")
    assert isinstance(mid, str) and len(mid) > 0
    items = svc.list_all("u1")
    assert len(items) == 1
    assert items[0].id == mid
    assert items[0].content == "User is vegetarian"
    assert items[0].category == "preference"


def test_get_by_id(svc):
    mid = svc.save(user_id="u1", content="Lives in NYC", category="fact")
    got = svc.get("u1", mid)
    assert got is not None
    assert got.id == mid
    assert got.content == "Lives in NYC"


def test_get_nonexistent_returns_none(svc):
    assert svc.get("u1", "no-such-id") is None


def test_list_all_orders_newest_first(svc):
    a = svc.save(user_id="u1", content="first fact", category="fact")
    b = svc.save(user_id="u1", content="second fact", category="fact")
    items = svc.list_all("u1")
    assert [m.id for m in items] == [b, a]


# ---------- namespace isolation -------------------------------------------


def test_namespace_isolation_list(svc):
    svc.save(user_id="alice", content="Alice loves pizza", category="preference")
    svc.save(user_id="bob", content="Bob hates olives", category="preference")
    alice_items = svc.list_all("alice")
    bob_items = svc.list_all("bob")
    assert len(alice_items) == 1 and "pizza" in alice_items[0].content
    assert len(bob_items) == 1 and "olives" in bob_items[0].content


def test_namespace_isolation_recall(svc):
    """Critical: recall under user B must NOT return user A's memories."""
    svc.save(user_id="alice", content="Alice is allergic to peanuts", category="fact")
    bob_hits = svc.recall(user_id="bob", query="peanut allergy", top_k=5)
    assert bob_hits == []


def test_namespace_isolation_get(svc):
    mid = svc.save(user_id="alice", content="x", category="fact")
    # Bob cannot fetch Alice's memory even with the right id.
    assert svc.get("bob", mid) is None


def test_namespace_isolation_delete(svc):
    mid = svc.save(user_id="alice", content="x", category="fact")
    # Bob's delete should not affect Alice's memory.
    deleted = svc.delete("bob", mid)
    assert deleted is False
    assert svc.get("alice", mid) is not None


# ---------- delete --------------------------------------------------------


def test_delete_removes_from_list(svc):
    mid = svc.save(user_id="u1", content="x", category="fact")
    assert svc.delete("u1", mid) is True
    assert svc.list_all("u1") == []


def test_delete_removes_from_recall_cache(svc):
    """After delete, recall must not surface the deleted memory."""
    mid = svc.save(user_id="u1", content="The user owns a cat named Mittens", category="fact")
    hits_before = svc.recall(user_id="u1", query="cat", top_k=5)
    assert any(h.memory.id == mid for h in hits_before)

    svc.delete("u1", mid)
    hits_after = svc.recall(user_id="u1", query="cat", top_k=5)
    assert all(h.memory.id != mid for h in hits_after)


def test_delete_nonexistent_returns_false(svc):
    assert svc.delete("u1", "no-such-id") is False


# ---------- recall / semantic ranking -------------------------------------


def test_recall_empty_for_new_user(svc):
    assert svc.recall(user_id="u_new", query="anything", top_k=5) == []


def test_recall_returns_top_k(svc):
    svc.save(user_id="u1", content="A", category="fact")
    svc.save(user_id="u1", content="B", category="fact")
    svc.save(user_id="u1", content="C", category="fact")
    hits = svc.recall(user_id="u1", query="A", top_k=2)
    assert len(hits) == 2


def test_recall_ranks_semantically_related_higher(svc):
    """A query about food should rank food memories above unrelated ones."""
    svc.save(user_id="u1", content="The user loves pasta and Italian cuisine", category="preference")
    svc.save(user_id="u1", content="The user works as a software engineer", category="fact")
    svc.save(user_id="u1", content="The user enjoys eating sushi for dinner", category="preference")

    hits = svc.recall(user_id="u1", query="What food does the user like?", top_k=3)
    assert len(hits) == 3
    # Top-2 hits should be the food-related ones.
    top_two_contents = {hits[0].memory.content, hits[1].memory.content}
    assert "pasta" in " ".join(top_two_contents).lower() or "sushi" in " ".join(top_two_contents).lower()
    # The job memory should rank lower than at least one food memory.
    job_hit = next(h for h in hits if "engineer" in h.memory.content)
    food_hits = [h for h in hits if "engineer" not in h.memory.content]
    assert max(h.similarity for h in food_hits) > job_hit.similarity


def test_recall_similarity_in_range(svc):
    svc.save(user_id="u1", content="Hello world", category="other")
    hits = svc.recall(user_id="u1", query="Hello world", top_k=1)
    assert len(hits) == 1
    # Identical text + normalized embeddings => similarity ~ 1.0.
    assert 0.95 <= hits[0].similarity <= 1.0001


# ---------- validation ----------------------------------------------------


def test_save_rejects_empty_content(svc):
    with pytest.raises(ValueError):
        svc.save(user_id="u1", content="", category="fact")
    with pytest.raises(ValueError):
        svc.save(user_id="u1", content="   ", category="fact")


def test_save_rejects_oversized_content(svc):
    big = "x" * (MAX_CONTENT_LEN + 1)
    with pytest.raises(ValueError):
        svc.save(user_id="u1", content=big, category="fact")


def test_save_rejects_invalid_category(svc):
    with pytest.raises(ValueError):
        svc.save(user_id="u1", content="x", category="not-a-category")


def test_save_accepts_all_valid_categories(svc):
    for cat in VALID_CATEGORIES:
        mid = svc.save(user_id="u1", content=f"sample for {cat}", category=cat)
        assert svc.get("u1", mid).category == cat


def test_save_rejects_blank_user_id(svc):
    with pytest.raises(ValueError):
        svc.save(user_id="", content="x", category="fact")


def test_recall_rejects_blank_query(svc):
    with pytest.raises(ValueError):
        svc.recall(user_id="u1", query="", top_k=5)


def test_recall_rejects_invalid_top_k(svc):
    with pytest.raises(ValueError):
        svc.recall(user_id="u1", query="x", top_k=0)


# ---------- Memory dataclass ----------------------------------------------


def test_memory_to_dict_excludes_internal_fields():
    m = Memory(
        id="abc",
        user_id="u1",
        content="hi",
        category="other",
        created_at="2026-01-01T00:00:00+00:00",
    )
    d = m.to_dict()
    assert "user_id" not in d  # internal, never returned to clients
    assert d["id"] == "abc"
    assert d["content"] == "hi"
    assert d["category"] == "other"
    assert d["created_at"] == "2026-01-01T00:00:00+00:00"
