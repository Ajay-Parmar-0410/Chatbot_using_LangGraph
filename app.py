"""FastAPI server wrapping the LangGraph chatbot backend."""

import re
import json
import uuid
import logging
from typing import Optional, List
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field, validator
from langchain_core.messages import HumanMessage, AIMessage

from chatbot_backend_gemini import chatbot, checkpointer, llm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.I)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    thread_id: str = Field(..., min_length=1)

    @validator('thread_id')
    def validate_thread_id(cls, v):
        if not UUID_RE.match(v):
            raise ValueError('thread_id must be a valid UUID v4')
        return v


class TitleRequest(BaseModel):
    first_message: str = Field(..., min_length=1, max_length=500)


class ThreadMessage(BaseModel):
    role: str
    content: str


class ThreadResponse(BaseModel):
    thread_id: str
    messages: List[ThreadMessage]
    title: Optional[str] = None


# ---------------------------------------------------------------------------
# In-memory thread titles store  (lightweight, no extra DB table)
# ---------------------------------------------------------------------------
_thread_titles: dict[str, str] = {}

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="AI Chatbot")

# ---------------------------------------------------------------------------
# Middleware: CORS + Security Headers
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# Static files
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root():
    """Serve the main HTML page."""
    return FileResponse(str(STATIC_DIR / "index.html"))


# ---------------------------------------------------------------------------
# POST /api/chat  –  SSE streaming
# ---------------------------------------------------------------------------

@app.post("/api/chat")
async def chat_stream(request: ChatRequest):
    """Stream AI response tokens via Server-Sent Events."""

    def event_generator():
        got_ai_response = False
        try:
            config = {"configurable": {"thread_id": request.thread_id}}
            for message_chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=request.message)]},
                config=config,
                stream_mode="messages",
            ):
                if isinstance(message_chunk, AIMessage) and message_chunk.content:
                    got_ai_response = True
                    data = json.dumps({"type": "token", "content": message_chunk.content})
                    yield f"data: {data}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

            # Register thread only after successful AI response
            if got_ai_response and request.thread_id not in _thread_titles:
                title = request.message[:40] + ("..." if len(request.message) > 40 else "")
                _thread_titles[request.thread_id] = title
        except Exception:
            logger.exception("Streaming error")
            error_data = json.dumps({"type": "error", "content": "An error occurred. Please try again."})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# GET /api/threads  –  list all conversations
# ---------------------------------------------------------------------------

@app.get("/api/threads")
async def list_threads():
    """Return only threads that are tracked (had successful AI responses)."""
    threads = []
    for tid, title in _thread_titles.items():
        threads.append({
            "thread_id": tid,
            "title": title,
            "updated_at": "",
        })
    return threads


# ---------------------------------------------------------------------------
# GET /api/threads/{thread_id}  –  load a conversation
# ---------------------------------------------------------------------------

@app.get("/api/threads/{thread_id}")
async def get_thread(thread_id: str):
    """Load all messages for a given thread."""
    if not UUID_RE.match(thread_id):
        raise HTTPException(status_code=400, detail="Invalid thread_id format")
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = chatbot.get_state(config)
        if not state or not state.values:
            raise HTTPException(status_code=404, detail="Thread not found")

        messages = []
        for msg in state.values.get("messages", []):
            if isinstance(msg, HumanMessage):
                messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage) and msg.content:
                messages.append({"role": "assistant", "content": msg.content})

        return {
            "thread_id": thread_id,
            "messages": messages,
            "title": _thread_titles.get(thread_id),
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error loading thread")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
# DELETE /api/threads/{thread_id}
# ---------------------------------------------------------------------------

@app.delete("/api/threads/{thread_id}")
async def delete_thread(thread_id: str):
    """Delete a conversation thread (removes title only; checkpoint stays)."""
    if not UUID_RE.match(thread_id):
        raise HTTPException(status_code=400, detail="Invalid thread_id format")
    _thread_titles.pop(thread_id, None)
    return {"success": True}


# ---------------------------------------------------------------------------
# POST /api/threads/{thread_id}/title  –  generate title
# ---------------------------------------------------------------------------

@app.post("/api/threads/{thread_id}/title")
async def generate_title(thread_id: str, request: TitleRequest):
    """Generate a short title from the first message using the LLM."""
    if not UUID_RE.match(thread_id):
        raise HTTPException(status_code=400, detail="Invalid thread_id format")
    try:
        prompt = (
            f"Generate a very short title (3-6 words, no quotes) for a conversation "
            f"that starts with: \"{request.first_message}\""
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        title = response.content.strip().strip('"').strip("'")[:60]
        _thread_titles[thread_id] = title
        return {"title": title}
    except Exception as exc:
        logger.exception("Error generating title")
        title = request.first_message[:40] + ("..." if len(request.first_message) > 40 else "")
        _thread_titles[thread_id] = title
        return {"title": title}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
