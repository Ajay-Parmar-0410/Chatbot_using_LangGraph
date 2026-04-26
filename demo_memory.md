# Persistent Memory — Demo Walkthrough

This demo shows the cross-session recall behaviour described in the resume bullet:

> *Created a working prototype demonstrating cross-session recall and user-specific context retrieval for Generative AI applications.*

## Setup

```bash
uvicorn app:app --port 8000
```

Open http://localhost:8000.

## Demo 1 — Cross-thread recall

**Thread A.** Click "New chat" in the sidebar. Send:

> *"I'm vegetarian and allergic to peanuts."*

The model should respond and call `save_memory` for each fact (visible in the sidebar **Memories** panel after a moment — refresh the panel by collapsing/expanding it if needed).

You should now see two entries:
- `[fact] User is allergic to peanuts`
- `[preference] User is vegetarian`

**Thread B (new thread).** Click "New chat" again to start a fresh thread. Send:

> *"Suggest a dinner I can make tonight."*

The reply should:
- Suggest something **vegetarian**
- Avoid **peanuts** (or call them out as excluded)

This works because `chat_node` recalls top-k memories for the current user **regardless of thread_id**, then injects them as a transient `SystemMessage` before the LLM call.

## Demo 2 — Manual memory management

The sidebar **Memories** panel lists every long-term memory with a delete button on hover. You can also drive it via the API:

```bash
# List
curl http://localhost:8000/api/memories

# Save manually
curl -X POST http://localhost:8000/api/memories \
  -H "Content-Type: application/json" \
  -d '{"content":"User prefers dark mode UIs","category":"preference"}'

# Delete
curl -X DELETE http://localhost:8000/api/memories/<memory_id>
```

## Demo 3 — Token reduction via summarization

Run the benchmark:

```bash
pytest tests/test_token_reduction.py -s
```

Expected output:
```
Token reduction: 637 -> 211 (66.9% drop)
4 passed
```

This corresponds to a real 25-turn conversation about Paris being compressed once `len(messages) > SUMMARY_TRIGGER` (12). The trigger fires only at turn boundaries (after a final `AIMessage` with no pending tool call), so summarization never interrupts an in-flight tool sequence.

## Demo 4 — Namespace isolation (single-user demo, multi-user test)

The demo runs with a hardcoded `user_id = "default"`, but the service-layer tests prove the rule:

```bash
pytest tests/test_memory_service.py::test_namespace_isolation_recall -v
pytest tests/test_memory_service.py::test_namespace_isolation_get -v
pytest tests/test_memory_service.py::test_namespace_isolation_delete -v
```

These tests save under `user_id="alice"` and verify that all access paths (`recall`, `get`, `delete`) return empty/false when called with `user_id="bob"`. To enable multi-user mode in the API, swap the hardcoded `DEFAULT_USER_ID` constant for a value derived from a request header or auth context.

## What's running under the hood

When you send a chat message, the LangGraph flow is:

```
START → chat_node ────tool_calls? ──▶ tools ──▶ chat_node ...
            │ (recall top-5 memories       │
            │  inject as SystemMessage)    │
            │                              │
            └─ no tool call ─▶ should_summarize?
                              │           │
                            yes           no
                              │            │
                              ▼            ▼
                          summarize       END
                              │
                              ▼
                             END
```

`summarize` only runs when message count > 12 and the last message is a final `AIMessage`. This keeps short conversations untouched while collapsing long ones to a summary + last 4 turns.
