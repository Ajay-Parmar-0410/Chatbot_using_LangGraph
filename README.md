# AI Chatbot using LangGraph

## Overview
AI-powered chatbot with a custom Qwen-style UI built using LangGraph, Google Gemini, and FastAPI.

## Tech Stack
- **Backend:** FastAPI, LangGraph, Google Gemini (2.5-flash)
- **Frontend:** Vanilla JS, Tailwind CSS (CDN), marked.js, highlight.js, DOMPurify
- **Streaming:** SSE (Server-Sent Events)
- **Database:** SQLite (conversation persistence via LangGraph checkpointer)
- **Tools (15):** Web search, calculator, stocks, Wikipedia, webpage reader, Python REPL, unit converter, datetime, dictionary, news search, YouTube search, image search, plus 3 memory tools (`save_memory`, `recall_memory`, `list_memories`).
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` (384-dim, runs locally).

## Features
- Real-time streaming AI responses
- Dark/Light theme toggle
- Conversation history sidebar
- Markdown rendering with syntax highlighting
- Copy and regenerate message actions
- Dual Gemini API key failover for reliability
- Responsive design (desktop + mobile)
- **Persistent three-tier memory** with cross-session recall (see below).

## Persistent Memory

Three layers, following standard production-chatbot conventions:

| Tier | Scope | Storage | Purpose |
|---|---|---|---|
| Hot (short-term) | Current thread | `SqliteSaver` checkpointer | Live conversation context |
| Warm (summary) | Current thread | Rolling `SystemMessage` written by `summarize_node` | Compress old turns when message count > 12 |
| Cold (long-term) | Cross-thread, per-user | `memories` table in SQLite + sentence-transformer embeddings | Atomic facts the model decides to remember |

**Token reduction:** the summarization node compresses old turns into a concise summary while keeping the last 4 messages verbatim. Measured reduction on a 25-turn fixture: **~67%** drop in prompt tokens (`pytest tests/test_token_reduction.py -s`).

**Cross-session recall:** every chat turn, the top-k (default 5) relevant memories for the current user are retrieved via cosine similarity and injected as a transient `SystemMessage`. The injection lives only for the LLM call — it never persists into state, so recalls don't compound.

**User-controlled:** every memory is visible in the sidebar "Memories" panel and deletable. The full surface:

```
GET    /api/memories             list all memories
POST   /api/memories             manually save one
DELETE /api/memories/{id}        delete one
```

The model can also save/recall memories autonomously via the `save_memory`, `recall_memory`, and `list_memories` tools.

See [`docs/memory-architecture.md`](docs/memory-architecture.md) for the full design and [`demo_memory.md`](demo_memory.md) for a walkthrough.

## Tests

```bash
pytest tests/ -q
```

49 tests cover the memory subsystem: service-layer unit tests, namespace isolation, schema validation, API endpoints, and the token-reduction benchmark.

## Setup

```bash
git clone https://github.com/Ajay-Parmar-0410/Chatbot_using_LangGraph.git
cd Chatbot_using_LangGraph
pip install -r requirements.txt
```

Create a `.env` file (see `.env.example`):
```
GOOGLE_API_KEY=your_gemini_key
GOOGLE_API_KEY_2=your_backup_gemini_key
SERPER_API_KEY=your_serper_key
LANGSMITH_TRACING=false
```

## Run

```bash
uvicorn app:app --port 8000
```

Open http://localhost:8000

## Project Structure
```
app.py                    # FastAPI server (chat + memory endpoints)
chatbot_backend_gemini.py # LangGraph + Gemini backend with summarize_node
memory/
  __init__.py
  embeddings.py           # sentence-transformer singleton + cosine
  service.py              # SQLite-backed MemoryService (namespaced per user)
tools/
  memory_tools.py         # save_memory, recall_memory, list_memories
  ...                     # 12 other tools (web search, wiki, python, ...)
static/
  index.html              # Main UI (with Memories panel)
  js/memories.js          # Memories sidebar panel
  js/...                  # chat, sidebar, theme, markdown, app
tests/
  test_memory_service.py  # 23 unit tests
  test_memory_tools.py    # 14 tool/schema tests
  test_memory_api.py      # 8 API endpoint tests
  test_token_reduction.py # 4 summarization benchmarks
```
