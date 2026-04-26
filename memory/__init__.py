"""Persistent memory subsystem.

Provides a SQLite-backed long-term memory store with semantic recall,
following common production-chatbot patterns: atomic facts,
categorized, namespaced per user, retrieved via top-k cosine
similarity over sentence-transformer embeddings.

See `docs/memory-architecture.md` for the full design.
"""

from memory.service import Memory, MemoryService

__all__ = ["Memory", "MemoryService"]
