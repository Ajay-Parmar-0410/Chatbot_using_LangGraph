"""Sentence-transformer embedding utilities.

Wraps `sentence-transformers/all-MiniLM-L6-v2` (384-dim) behind a lazy
singleton so model load is paid at most once per process. Provides a
`cosine_similarity` helper used by `MemoryService` for top-k recall.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

_model_lock = threading.Lock()
_model: Optional["SentenceTransformer"] = None  # type: ignore[name-defined]


def _load_model():
    """Lazy-load the sentence-transformer model. Thread-safe."""
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        logger.info("Loading sentence-transformer model: %s", MODEL_NAME)
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
        logger.info("Sentence-transformer model loaded")
    return _model


def embed(text: str) -> np.ndarray:
    """Encode text to a float32 numpy array of length EMBEDDING_DIM.

    Raises ValueError if `text` is empty or whitespace-only.
    """
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text")
    model = _load_model()
    vec = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
    return vec.astype(np.float32, copy=False)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity for L2-normalized vectors reduces to dot product.

    `embed()` already normalizes, so this is just a dot. We still guard
    against unnormalized inputs for safety.
    """
    if a.shape != b.shape:
        raise ValueError(f"Shape mismatch: {a.shape} vs {b.shape}")
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def serialize(vec: np.ndarray) -> bytes:
    """Serialize a float32 numpy array to bytes for SQLite BLOB storage."""
    if vec.dtype != np.float32:
        vec = vec.astype(np.float32, copy=False)
    return vec.tobytes()


def deserialize(blob: bytes) -> np.ndarray:
    """Inverse of `serialize`. Returns a writable float32 numpy array.

    `np.frombuffer` returns a read-only view sharing memory with the
    bytes object. Copying ensures callers can safely mutate the result
    (e.g., re-normalize) without surprising read-only errors.
    """
    return np.frombuffer(blob, dtype=np.float32).copy()
