"""TTL cache decorator for tool results."""

import time
from functools import lru_cache, wraps


def ttl_cache(seconds: int = 300, maxsize: int = 256):
    """Cache function results with a time-to-live expiration."""
    def decorator(func):
        @lru_cache(maxsize=maxsize)
        def _cached(*args, _ttl_round=0):
            return func(*args)

        @wraps(func)
        def wrapper(*args):
            return _cached(*args, _ttl_round=int(time.time()) // seconds)

        wrapper.cache_clear = _cached.cache_clear
        return wrapper
    return decorator
