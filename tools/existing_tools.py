"""Existing tools migrated from chatbot_backend_gemini.py with enhancements."""

import os
import logging

from langchain_core.tools import tool

from tools._http_client import get_client
from tools._cache import ttl_cache

logger = logging.getLogger(__name__)

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")


@ttl_cache(seconds=300)
def _web_search_cached(query: str) -> str:
    """Cached web search via Serper API directly (returns URLs for agentic use)."""
    client = get_client()
    resp = client.post(
        "https://google.serper.dev/search",
        json={"q": query, "num": 5},
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("organic", [])[:5]:
        title = item.get("title", "")
        link = item.get("link", "")
        snippet = item.get("snippet", "")
        results.append(f"- [{title}]({link}) — {snippet}")

    if not results:
        return f"No results found for '{query}'."

    return f"Results for \"{query}\":\n" + "\n".join(results)


@tool
def web_search(query: str) -> str:
    """Search the web for current information. Returns titles, URLs, and snippets.
    When you need detailed information, first search, then use read_webpage
    on the most relevant URLs. Always cite sources with [Title](URL) format."""
    try:
        return _web_search_cached(query)
    except Exception as e:
        return f"Error during web search: {str(e)}"


@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div"""
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}


@tool
def get_stock_price(symbol: str) -> dict:
    """Get the latest stock price for a given stock symbol using Alpha Vantage.
    Example symbols: AAPL, TSLA, MSFT, GOOGL"""
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        return {"error": "ALPHA_VANTAGE_API_KEY not configured in .env"}

    try:
        client = get_client()
        resp = client.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": api_key,
            },
        )
        data = resp.json()
        if "Global Quote" not in data or not data["Global Quote"]:
            return {"error": f"No data found for symbol '{symbol}'"}
        quote = data["Global Quote"]
        return {
            "symbol": quote.get("01. symbol"),
            "price": float(quote.get("05. price", 0)),
            "change": float(quote.get("09. change", 0)),
            "change_percent": quote.get("10. change percent"),
        }
    except Exception as e:
        return {"error": str(e)}
