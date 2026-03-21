# AI Chatbot using LangGraph

## Overview
AI-powered chatbot with a custom Qwen-style UI built using LangGraph, Google Gemini, and FastAPI.

## Tech Stack
- **Backend:** FastAPI, LangGraph, Google Gemini (2.5-flash)
- **Frontend:** Vanilla JS, Tailwind CSS (CDN), marked.js, highlight.js, DOMPurify
- **Streaming:** SSE (Server-Sent Events)
- **Database:** SQLite (conversation persistence via LangGraph checkpointer)
- **Tools:** Web search (Serper), Calculator, Stock price (Alpha Vantage)

## Features
- Real-time streaming AI responses
- Dark/Light theme toggle
- Conversation history sidebar
- Markdown rendering with syntax highlighting
- Copy and regenerate message actions
- Dual Gemini API key failover for reliability
- Responsive design (desktop + mobile)

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
app.py                    # FastAPI server
chatbot_backend_gemini.py # LangGraph + Gemini backend with dual-key failover
static/
  index.html              # Main UI
  css/styles.css          # Custom CSS + animations
  js/app.js               # Entry point + state
  js/chat.js              # SSE streaming chat
  js/sidebar.js           # Thread history
  js/theme.js             # Dark/light toggle
  js/markdown.js          # Markdown rendering
  js/utils.js             # Utilities
  assets/bot-avatar.svg   # Bot icon
```
