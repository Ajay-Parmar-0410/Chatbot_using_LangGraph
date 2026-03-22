"""Dictionary lookup tool using Free Dictionary API."""

from langchain_core.tools import tool

from tools._http_client import get_client
from tools._cache import ttl_cache


@ttl_cache(seconds=3600)
def _dictionary_cached(word: str) -> str:
    """Cached dictionary lookup."""
    client = get_client()
    resp = client.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")

    if resp.status_code == 404:
        return f"No definition found for '{word}'."

    resp.raise_for_status()
    data = resp.json()

    if not data or not isinstance(data, list):
        return f"No definition found for '{word}'."

    entry = data[0]
    word_text = entry.get("word", word)
    phonetic = entry.get("phonetic", "")

    results = [f"**{word_text}**"]
    if phonetic:
        results.append(f"Pronunciation: {phonetic}")
    results.append("")

    count = 0
    for meaning in entry.get("meanings", []):
        if count >= 2:
            break
        part = meaning.get("partOfSpeech", "")
        for defn in meaning.get("definitions", [])[:1]:
            count += 1
            definition = defn.get("definition", "")
            example = defn.get("example", "")
            results.append(f"**{part}**: {definition}")
            if example:
                results.append(f"  _Example: \"{example}\"_")

    return "\n".join(results)


@tool
def dictionary_lookup(word: str) -> str:
    """Look up the definition of an English word.
    Returns definitions, parts of speech, and example usage."""
    try:
        return _dictionary_cached(word.strip().lower())
    except Exception as e:
        return f"Error looking up definition: {str(e)}"
