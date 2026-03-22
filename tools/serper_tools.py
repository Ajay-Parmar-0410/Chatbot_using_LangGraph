"""Serper-powered search tools: news, YouTube, image search."""

import os

from langchain_core.tools import tool

from tools._http_client import get_client
from tools._cache import ttl_cache

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
_HEADERS = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}


@ttl_cache(seconds=300)
def _news_search_cached(query: str) -> str:
    """Cached news search."""
    client = get_client()
    resp = client.post(
        "https://google.serper.dev/news",
        json={"q": query, "num": 5},
        headers=_HEADERS,
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("news", [])[:5]:
        title = item.get("title", "")
        link = item.get("link", "")
        source = item.get("source", "")
        date = item.get("date", "")
        snippet = item.get("snippet", "")
        results.append(f"- [{title}]({link}) — {source} ({date})\n  {snippet}")

    if not results:
        return f"No news found for '{query}'."

    return f"News results for \"{query}\":\n" + "\n".join(results)


@tool
def news_search(query: str) -> str:
    """Search for the latest news articles on a topic.
    Returns headlines, sources, and publication dates."""
    try:
        return _news_search_cached(query)
    except Exception as e:
        return f"Error searching news: {str(e)}"


@ttl_cache(seconds=300)
def _youtube_search_cached(query: str) -> str:
    """Cached YouTube search."""
    client = get_client()
    resp = client.post(
        "https://google.serper.dev/videos",
        json={"q": query, "num": 5},
        headers=_HEADERS,
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("videos", [])[:5]:
        title = item.get("title", "")
        link = item.get("link", "")
        channel = item.get("channel", "")
        duration = item.get("duration", "")
        results.append(f"- [{title}]({link}) — {channel} ({duration})")

    if not results:
        return f"No videos found for '{query}'."

    return f"Video results for \"{query}\":\n" + "\n".join(results)


@tool
def youtube_search(query: str) -> str:
    """Search YouTube for videos on a topic.
    Returns video titles, channels, and links."""
    try:
        return _youtube_search_cached(query)
    except Exception as e:
        return f"Error searching YouTube: {str(e)}"


@ttl_cache(seconds=300)
def _image_search_cached(query: str) -> str:
    """Cached image search."""
    client = get_client()
    resp = client.post(
        "https://google.serper.dev/images",
        json={"q": query, "num": 5},
        headers=_HEADERS,
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("images", [])[:5]:
        title = item.get("title", "")
        link = item.get("imageUrl", "")
        source = item.get("source", "")
        results.append(f"- [{title}]({link}) — {source}")

    if not results:
        return f"No images found for '{query}'."

    return f"Image results for \"{query}\":\n" + "\n".join(results)


@tool
def image_search(query: str) -> str:
    """Search for images on a topic. Returns image URLs with titles."""
    try:
        return _image_search_cached(query)
    except Exception as e:
        return f"Error searching images: {str(e)}"
