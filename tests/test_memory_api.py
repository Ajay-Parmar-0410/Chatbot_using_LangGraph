"""End-to-end tests for the /api/memories endpoints.

Uses FastAPI TestClient + temp DB swap so we don't pollute chatbot2.db.
"""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from memory.service import MemoryService


@pytest.fixture
def client(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    svc = MemoryService(db_path=path)

    # Ensure both app and tools modules use this swapped service.
    import app as app_module
    from tools import memory_tools

    monkeypatch.setattr(app_module, "get_default_service", lambda: svc)
    monkeypatch.setattr(memory_tools, "get_default_service", lambda: svc)

    test_client = TestClient(app_module.app)
    try:
        yield test_client, svc
    finally:
        svc.close()
        try:
            os.remove(path)
        except OSError:
            pass


def test_list_empty(client):
    c, _ = client
    r = c.get("/api/memories")
    assert r.status_code == 200
    body = r.json()
    assert body == {"memories": [], "count": 0}


def test_create_then_list(client):
    c, _ = client
    r = c.post("/api/memories", json={"content": "User likes hiking", "category": "preference"})
    assert r.status_code == 200, r.text
    mid = r.json()["id"]
    assert r.json()["saved"] is True

    r = c.get("/api/memories")
    body = r.json()
    assert body["count"] == 1
    assert body["memories"][0]["id"] == mid
    assert body["memories"][0]["content"] == "User likes hiking"


def test_create_rejects_invalid_category(client):
    c, _ = client
    r = c.post("/api/memories", json={"content": "x", "category": "nope"})
    assert r.status_code == 422  # Pydantic validation


def test_create_rejects_empty_content(client):
    c, _ = client
    r = c.post("/api/memories", json={"content": "", "category": "fact"})
    assert r.status_code == 422


def test_create_rejects_oversized_content(client):
    c, _ = client
    r = c.post("/api/memories", json={"content": "x" * 600, "category": "fact"})
    assert r.status_code == 422


def test_delete_existing(client):
    c, _ = client
    r = c.post("/api/memories", json={"content": "delete me", "category": "other"})
    mid = r.json()["id"]
    r = c.delete(f"/api/memories/{mid}")
    assert r.status_code == 200
    assert r.json() == {"success": True}
    r = c.get("/api/memories")
    assert r.json()["count"] == 0


def test_delete_nonexistent_uuid(client):
    """Valid UUID format but not in DB → 404."""
    c, _ = client
    r = c.delete("/api/memories/00000000-0000-4000-8000-000000000000")
    assert r.status_code == 404


def test_delete_invalid_id_format_rejected(client):
    """Non-UUID id → 400."""
    c, _ = client
    r = c.delete("/api/memories/not-a-uuid")
    assert r.status_code == 400


def test_delete_overlong_id_rejected(client):
    c, _ = client
    r = c.delete("/api/memories/" + "x" * 100)
    assert r.status_code == 400
