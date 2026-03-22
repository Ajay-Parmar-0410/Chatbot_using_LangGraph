"""Shared HTTP client with connection pooling and strict timeouts."""

from typing import Optional

import httpx

_client: Optional[httpx.Client] = None


def get_client() -> httpx.Client:
    """Return a shared httpx.Client with connection pooling."""
    global _client
    if _client is None:
        _client = httpx.Client(
            timeout=httpx.Timeout(connect=4.0, read=5.0, write=5.0, pool=5.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            headers={"User-Agent": "ChatBot/1.0"},
            follow_redirects=True,
        )
    return _client
