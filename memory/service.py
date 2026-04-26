"""SQLite-backed long-term memory service with semantic recall.

Design contract (see plan3.md § Standards followed):
- Three-tier memory: this module is the COLD tier (cross-session, persistent).
- Atomic facts only (1-500 chars); not full transcripts.
- Strict namespace isolation by `user_id` — every method takes user_id,
  every query is `WHERE user_id = ?`.
- Top-k cosine retrieval over sentence-transformer embeddings.

Thread-safety: the SQLite connection is created with `check_same_thread=False`
to mirror the existing `chatbot_backend_gemini.py` pattern. A reentrant lock
serializes writes; reads are concurrent-safe with SQLite's WAL mode.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from memory.embeddings import (
    EMBEDDING_DIM,
    cosine_similarity,
    deserialize,
    embed,
    serialize,
)

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {"preference", "fact", "goal", "other"}
MAX_CONTENT_LEN = 500
MIN_CONTENT_LEN = 1


@dataclass(frozen=True)
class Memory:
    """A single atomic fact about a user. Immutable."""

    id: str
    user_id: str
    content: str
    category: str
    created_at: str  # ISO8601 UTC

    def to_dict(self) -> dict:
        """Serialize for API responses. Excludes embedding."""
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class RecalledMemory:
    """A memory returned by recall(), with its similarity score."""

    memory: Memory
    similarity: float

    def to_dict(self) -> dict:
        return {
            **self.memory.to_dict(),
            "similarity": round(self.similarity, 4),
        }


class MemoryService:
    """SQLite-backed memory service. Namespace-isolated by user_id.

    Usage:
        svc = MemoryService(db_path="chatbot2.db")
        mid = svc.save(user_id="default", content="User is vegetarian",
                       category="preference")
        hits = svc.recall(user_id="default", query="dinner ideas", top_k=3)
    """

    def __init__(self, db_path: str = "chatbot2.db") -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._write_lock = threading.RLock()
        self._init_schema()
        # Cache: {user_id: {memory_id: np.ndarray}} — lazy per-user.
        self._embedding_cache: dict[str, dict[str, np.ndarray]] = {}

    def _init_schema(self) -> None:
        with self._write_lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id          TEXT PRIMARY KEY,
                    user_id     TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    category    TEXT NOT NULL,
                    embedding   BLOB NOT NULL,
                    created_at  TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id)"
            )
            self._conn.commit()

    # ---- Validation -------------------------------------------------------

    @staticmethod
    def _validate_user_id(user_id: str) -> None:
        if not user_id or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")

    @staticmethod
    def _validate_content(content: str) -> None:
        if not isinstance(content, str):
            raise TypeError("content must be a string")
        stripped = content.strip()
        if len(stripped) < MIN_CONTENT_LEN:
            raise ValueError("content must not be empty")
        if len(stripped) > MAX_CONTENT_LEN:
            raise ValueError(
                f"content exceeds {MAX_CONTENT_LEN} characters (got {len(stripped)})"
            )

    @staticmethod
    def _validate_category(category: str) -> None:
        if category not in VALID_CATEGORIES:
            raise ValueError(
                f"category must be one of {sorted(VALID_CATEGORIES)}, got {category!r}"
            )

    # ---- Embedding cache --------------------------------------------------

    def _ensure_user_cache(self, user_id: str) -> dict[str, np.ndarray]:
        """Lazy-build the embedding cache for one user from DB.

        Holds `_write_lock` (RLock) so that concurrent save/delete cannot
        race with cache initialization. Without this, two callers could
        each build a cache, then one's writes would land on the other's
        orphaned dict and be lost until process restart.
        """
        cache = self._embedding_cache.get(user_id)
        if cache is not None:
            return cache
        with self._write_lock:
            cache = self._embedding_cache.get(user_id)
            if cache is not None:
                return cache
            cache = {}
            cursor = self._conn.execute(
                "SELECT id, embedding FROM memories WHERE user_id = ?",
                (user_id,),
            )
            for mid, blob in cursor.fetchall():
                cache[mid] = deserialize(blob)
            self._embedding_cache[user_id] = cache
            return cache

    # ---- Public API -------------------------------------------------------

    def save(self, user_id: str, content: str, category: str) -> str:
        """Persist a new memory. Returns the new memory's id."""
        self._validate_user_id(user_id)
        self._validate_content(content)
        self._validate_category(category)

        memory_id = str(uuid.uuid4())
        content_clean = content.strip()
        vec = embed(content_clean)
        if vec.shape[0] != EMBEDDING_DIM:
            raise RuntimeError(
                f"Embedding dim mismatch: expected {EMBEDDING_DIM}, got {vec.shape[0]}"
            )
        created_at = datetime.now(timezone.utc).isoformat()

        with self._write_lock:
            self._conn.execute(
                "INSERT INTO memories (id, user_id, content, category, embedding, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (memory_id, user_id, content_clean, category, serialize(vec), created_at),
            )
            self._conn.commit()
            cache = self._ensure_user_cache(user_id)
            cache[memory_id] = vec

        logger.info("Saved memory %s for user=%s category=%s", memory_id, user_id, category)
        return memory_id

    def recall(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[RecalledMemory]:
        """Return up to top_k memories most similar to `query`, scoped to user_id."""
        self._validate_user_id(user_id)
        if not query or not query.strip():
            raise ValueError("query must be a non-empty string")
        if top_k < 1:
            raise ValueError("top_k must be >= 1")

        cache = self._ensure_user_cache(user_id)
        if not cache:
            return []

        query_vec = embed(query.strip())
        scored: list[tuple[str, float]] = [
            (mid, cosine_similarity(query_vec, vec)) for mid, vec in cache.items()
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:top_k]

        if not top:
            return []
        ids = [mid for mid, _ in top]
        sim_by_id = dict(top)
        rows = self._fetch_by_ids(user_id, ids)
        # Preserve top-k ranking order.
        rows_by_id = {r.id: r for r in rows}
        results: list[RecalledMemory] = []
        for mid in ids:
            row = rows_by_id.get(mid)
            if row is None:
                continue  # raced with delete; skip
            results.append(RecalledMemory(memory=row, similarity=sim_by_id[mid]))
        return results

    def list_all(self, user_id: str) -> list[Memory]:
        """Return all memories for the user, newest first."""
        self._validate_user_id(user_id)
        cursor = self._conn.execute(
            "SELECT id, user_id, content, category, created_at "
            "FROM memories WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        return [
            Memory(id=r[0], user_id=r[1], content=r[2], category=r[3], created_at=r[4])
            for r in cursor.fetchall()
        ]

    def delete(self, user_id: str, memory_id: str) -> bool:
        """Delete one memory. Returns True if a row was deleted."""
        self._validate_user_id(user_id)
        if not memory_id:
            raise ValueError("memory_id must be a non-empty string")

        with self._write_lock:
            cursor = self._conn.execute(
                "DELETE FROM memories WHERE user_id = ? AND id = ?",
                (user_id, memory_id),
            )
            self._conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                cache = self._embedding_cache.get(user_id)
                if cache is not None:
                    cache.pop(memory_id, None)
                logger.info("Deleted memory %s for user=%s", memory_id, user_id)
            return deleted

    def get(self, user_id: str, memory_id: str) -> Optional[Memory]:
        """Fetch one memory by id, scoped to user_id. Returns None if missing."""
        self._validate_user_id(user_id)
        if not memory_id:
            return None
        cursor = self._conn.execute(
            "SELECT id, user_id, content, category, created_at "
            "FROM memories WHERE user_id = ? AND id = ?",
            (user_id, memory_id),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return Memory(id=row[0], user_id=row[1], content=row[2], category=row[3], created_at=row[4])

    # ---- Internal ---------------------------------------------------------

    def _fetch_by_ids(self, user_id: str, ids: list[str]) -> list[Memory]:
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        cursor = self._conn.execute(
            f"SELECT id, user_id, content, category, created_at "
            f"FROM memories WHERE user_id = ? AND id IN ({placeholders})",
            (user_id, *ids),
        )
        return [
            Memory(id=r[0], user_id=r[1], content=r[2], category=r[3], created_at=r[4])
            for r in cursor.fetchall()
        ]

    def close(self) -> None:
        """Close the underlying SQLite connection. Idempotent."""
        with self._write_lock:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass


# Process-wide singleton wired up by chatbot_backend_gemini.py.
# Tests construct their own MemoryService instances against temp DBs.
_default_service: Optional[MemoryService] = None
_singleton_lock = threading.Lock()


def get_default_service(db_path: str = "chatbot2.db") -> MemoryService:
    """Return the process-wide MemoryService, creating it on first call."""
    global _default_service
    if _default_service is not None:
        return _default_service
    with _singleton_lock:
        if _default_service is None:
            _default_service = MemoryService(db_path=db_path)
    return _default_service
