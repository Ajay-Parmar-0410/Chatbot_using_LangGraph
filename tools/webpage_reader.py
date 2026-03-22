"""Webpage reader tool with SSRF prevention and content extraction."""

import ipaddress
import logging
from urllib.parse import urlparse

from langchain_core.tools import tool

from tools._http_client import get_client
from tools._cache import ttl_cache

logger = logging.getLogger(__name__)

# Private IP ranges to block (SSRF prevention)
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]

MAX_CONTENT_LENGTH = 6000


def _is_safe_url(url: str) -> bool:
    """Validate URL is safe (no SSRF to private networks)."""
    try:
        parsed = urlparse(url)

        # Only allow HTTP(S)
        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # Block obvious private hostnames
        if hostname in ("localhost", "0.0.0.0"):
            return False

        # Resolve and check IP
        import socket
        try:
            ip = ipaddress.ip_address(socket.gethostbyname(hostname))
            for network in _BLOCKED_NETWORKS:
                if ip in network:
                    return False
        except (socket.gaierror, ValueError):
            return False

        return True
    except Exception:
        return False


@ttl_cache(seconds=300)
def _read_webpage_cached(url: str) -> str:
    """Cached webpage content extraction."""
    client = get_client()
    resp = client.get(url)
    resp.raise_for_status()

    html = resp.text

    # Try trafilatura first
    try:
        import trafilatura
        text = trafilatura.extract(html, include_links=True, include_tables=True)
        if text:
            if len(text) > MAX_CONTENT_LENGTH:
                text = text[:MAX_CONTENT_LENGTH] + "\n\n[Content truncated...]"
            return text
    except ImportError:
        pass

    # Fallback: basic regex text extraction
    import re
    # Remove script and style tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    if len(text) > MAX_CONTENT_LENGTH:
        text = text[:MAX_CONTENT_LENGTH] + "\n\n[Content truncated...]"

    return text if text else "Could not extract text content from this page."


@tool
def read_webpage(url: str) -> str:
    """Fetch and read the text content of a webpage URL.
    Use after web_search to read full articles for detailed answers.
    You can call this on multiple URLs in parallel for faster research."""
    # SSRF validation
    if not _is_safe_url(url):
        return "Error: URL is not allowed (blocked for security reasons)."

    try:
        return _read_webpage_cached(url)
    except Exception as e:
        return f"Error reading webpage: {str(e)}"
