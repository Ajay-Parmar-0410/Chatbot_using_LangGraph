"""Wikipedia lookup tool using the REST API."""

from langchain_core.tools import tool

from tools._http_client import get_client
from tools._cache import ttl_cache


@ttl_cache(seconds=600)
def _wikipedia_cached(query: str) -> str:
    """Cached Wikipedia summary lookup."""
    client = get_client()

    # Search for the page first
    search_resp = client.get(
        "https://en.wikipedia.org/api/rest_v1/page/summary/" + query.replace(" ", "_"),
    )

    if search_resp.status_code == 404:
        # Try search API as fallback
        search_resp = client.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "opensearch", "search": query, "limit": 1, "format": "json"},
        )
        data = search_resp.json()
        if len(data) >= 4 and data[1]:
            title = data[1][0]
            search_resp = client.get(
                "https://en.wikipedia.org/api/rest_v1/page/summary/" + title.replace(" ", "_"),
            )
        else:
            return f"No Wikipedia article found for '{query}'."

    if search_resp.status_code != 200:
        return f"No Wikipedia article found for '{query}'."

    data = search_resp.json()
    title = data.get("title", query)
    extract = data.get("extract", "")
    url = data.get("content_urls", {}).get("desktop", {}).get("page", "")

    if not extract:
        return f"No Wikipedia article found for '{query}'."

    # Truncate to 2000 chars
    if len(extract) > 2000:
        extract = extract[:2000] + "..."

    result = f"**{title}**\n\n{extract}"
    if url:
        result += f"\n\nSource: {url}"
    return result


@tool
def wikipedia_lookup(query: str) -> str:
    """Look up a topic on Wikipedia. Returns a concise summary.
    Use for factual info about people, places, events, concepts."""
    try:
        return _wikipedia_cached(query)
    except Exception as e:
        return f"Error looking up Wikipedia: {str(e)}"
