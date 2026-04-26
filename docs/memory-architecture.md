# Persistent Memory Architecture

> Implementation reference for the three-layer memory system added in plan3.md. Patterns follow standard production-chatbot conventions (see `plan3.md` § Standards followed).

## Three layers

```
┌─────────────────────────────────────────────────────────────┐
│  HOT — short-term (in-context messages, current thread)     │
│  ────────────────────────────────────────────────────────   │
│  Storage: LangGraph state.messages, persisted by SqliteSaver│
│  Lifetime: until summarized or thread deleted               │
│  Used by: every LLM call                                    │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│  WARM — summary (rolling compressed history, current thread)│
│  ────────────────────────────────────────────────────────   │
│  Storage: SystemMessage at head of state.messages           │
│  Lifetime: rewritten each time summarize_node fires         │
│  Trigger: len(messages) > SUMMARY_TRIGGER (default 12)      │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│  COLD — long-term (cross-session, per user)                 │
│  ────────────────────────────────────────────────────────   │
│  Storage: SQLite table `memories` in chatbot2.db            │
│  Lifetime: persistent until user deletes                    │
│  Access: top-k cosine retrieval injected as SystemMessage   │
└─────────────────────────────────────────────────────────────┘
```

## Graph topology

```
                 ┌─────────────────────────────────┐
START ──────────▶│ chat_node                       │
                 │   1. Recall top-k memories      │
                 │   2. Prepend SystemMessage      │
                 │   3. LLM.invoke(...)            │
                 └────────┬───────────┬────────────┘
                          │           │
            tools_condition           │ no tool call
                          │           ▼
                          ▼      should_summarize?
                 ┌─────────────┐    │       │
                 │ tools       │   yes      no
                 │ (ToolNode)  │    │       │
                 └──────┬──────┘    ▼       ▼
                        │     summarize_   END
                        │     node
                        │       │
                        ▼       ▼
                  back to chat_node
```

`should_summarize` is a conditional edge that returns `"summarize"` when `len(state.messages) > SUMMARY_TRIGGER` and the last message is an `AIMessage` (so we summarize at turn boundaries, not mid-tool-call).

## SQLite schema

```sql
CREATE TABLE IF NOT EXISTS memories (
    id          TEXT PRIMARY KEY,           -- uuid4
    user_id     TEXT NOT NULL,              -- namespace key
    content     TEXT NOT NULL,              -- atomic fact, 1-500 chars
    category    TEXT NOT NULL,              -- preference|fact|goal|other
    embedding   BLOB NOT NULL,              -- float32 numpy bytes (384 dims)
    created_at  TEXT NOT NULL               -- ISO8601 UTC
);
CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);
```

- One DB file (`chatbot2.db`) shared with `SqliteSaver`. New table only — no migration to existing checkpoint tables.
- `embedding` is a `float32` numpy array serialized via `np.ndarray.tobytes()`; deserialized via `np.frombuffer(..., dtype=np.float32)`.
- 384 dims = `all-MiniLM-L6-v2` output. Documented in `embeddings.py` so future model swaps fail loudly.

## Namespace isolation

Every public method on `MemoryService` takes `user_id: str` as the first parameter. SQL queries always include `WHERE user_id = ?`. There is no method that returns rows across users. The recall path:

```
recall(user_id="default", query="...")
  └─▶ SELECT id, content, category, embedding FROM memories
      WHERE user_id = ?                   ← parameterized
  └─▶ cosine(query_embedding, row.embedding) for each row
  └─▶ top-k by similarity
```

Tests assert that `save(user_id="A", ...)` then `recall(user_id="B", ...)` returns `[]`.

## Embedding cache

`MemoryService` keeps an in-memory dict `{user_id: {memory_id: np.ndarray}}` rebuilt on first access per user. Saves and deletes update the cache in lockstep with the DB. This keeps recall O(N) over only that user's memories without re-decoding blobs every call. Cache is rebuilt on process start; for a personal chatbot demo this is fine (memories typically <1000 per user).

## Recall injection format

When `chat_node` recalls memories, it prepends:

```
SystemMessage(content="Relevant facts about the user:\n- {memory_1}\n- {memory_2}\n...")
```

This SystemMessage is **not** persisted into the checkpointer state — it's added at invocation time, then dropped from the response. Otherwise repeated recalls would compound. The state retains only the actual conversation turns + summary.

## Summarization

Trigger: `len(state.messages) > SUMMARY_TRIGGER` (default 12) **and** last message is `AIMessage`.

Action:
1. Slice `messages[:-KEEP_RECENT]` (default keeps last 4).
2. Send them to the LLM with prompt: *"Summarize this conversation into a concise paragraph capturing key facts, decisions, and context. Be terse."*
3. Replace the sliced portion with a single `SystemMessage(content="Conversation summary so far:\n{summary}")`.
4. Keep `messages[-KEEP_RECENT:]` verbatim.

Net result: 12+ messages collapse to 1 summary + 4 recent turns = 5 messages going into the next LLM call.

Token reduction is measured in `tests/test_token_reduction.py` against a 25-turn fixture. Target: ≥45% reduction in prompt tokens.

## Tool surface (schema-driven)

| Tool | Args (Pydantic) | Returns |
|---|---|---|
| `save_memory` | `content: str` (1–500), `category: Literal[...]` | `{"id": "...", "saved": true}` |
| `recall_memory` | `query: str` (1–500), `top_k: int` (1–10, default 5) | `[{content, category, similarity}, ...]` |
| `list_memories` | (none) | `[{id, content, category, created_at}, ...]` |

All schemas validated by Pydantic before the service is called. Bad input → `ValidationError`, never reaches SQLite.

## Cross-session demo

```
Thread A:
  user> "I'm vegetarian and allergic to peanuts."
  ai>   [calls save_memory(content="User is vegetarian", category="preference")]
        [calls save_memory(content="User is allergic to peanuts", category="fact")]
        "Got it, I'll keep that in mind."

Thread B (new thread_id, same user_id="default"):
  user> "Suggest a dinner I can make tonight."
  chat_node:
    1. recall("dinner suggestion") → ["User is vegetarian", "User is allergic to peanuts"]
    2. Prepend SystemMessage with those facts
    3. LLM responds with peanut-free vegetarian dinner.
```

This is the test we ship in `demo_memory.md`.

## Why a plain SQLite table, not `BaseStore`?

`langgraph 1.1.9` ships only `InMemoryStore`. We could subclass `BaseStore` to write a `SqliteStore`, but:
- We need vector similarity search anyway, which `BaseStore` doesn't provide.
- A plain table with `user_id` as a column is simpler to reason about, easier to debug with sqlite CLI, and matches the resume claim ("backend memory service") more directly than a generic key-value abstraction.
- Future migration to `BaseStore` if langgraph adds vector support is mechanical.

## Files

| File | Purpose |
|---|---|
| `memory/__init__.py` | Public exports (`MemoryService`, `Memory`) |
| `memory/embeddings.py` | `Embedder` singleton, `cosine_similarity` |
| `memory/service.py` | `MemoryService`, `Memory` dataclass, SQLite IO |
| `tools/memory_tools.py` | `save_memory`, `recall_memory`, `list_memories` |
| `chatbot_backend_gemini.py` | `summarize_node`, recall injection, edge wiring |
| `app.py` | `/api/memories` endpoints |
