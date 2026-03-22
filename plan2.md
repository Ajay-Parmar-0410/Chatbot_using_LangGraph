# Plan 2: Qwen-Style UI Redesign

## Overview

Redesign the existing FastAPI + Vanilla JS chatbot frontend to match the **Qwen chat application's UI/UX**. This involves a collapsible sidebar with icon strip, a floating pill-shaped input bar with tool menus, a minimal welcome screen, and refined dark-mode color palette. The backend (`app.py`, `chatbot_backend_gemini.py`) remains **untouched**.

## Target UI (from Qwen Screenshots in `qwen_ss/`)

> **Reference:** 5 screenshots in `qwen_ss/` folder. Read them for visual reference.

### Screenshot Descriptions (for sessions that can't view images)

**Screenshot 1 — Sidebar open (small view):**
Dark theme. Left sidebar (~280px) with: purple sparkle logo top-left, "Qwen3.5-Plus ▼" model name at top. Navigation: "New Chat" (+icon), "Search Chats" (search icon), "Community". "Projects" section: "New Project", "Health", "Learning Agentic AI Plan". "All chats" section with date-grouped history. Bottom: user avatar circle + "Ajay Balvantbhai Parmar". Main area: centered "What would you like to explore?" text. Below: pill-shaped input bar with "+" left, "How can I help you today?" placeholder, "Auto ▼" dropdown, mic icon, purple circular send button.

**Screenshot 2 — Sidebar collapsed:**
Sidebar collapsed to ~50px icon strip. Icons top-to-bottom: sidebar toggle (panel-left icon), "+" (new chat), search (magnifying glass). At bottom: user avatar. Model name "Qwen3.5-Plus ▼" appears at top of main area next to icon strip. Top-right: canvas/artboard icon. Main area same as screenshot 1.

**Screenshot 3 — "+" tools dropdown open:**
Clicking "+" in input bar opens a dropdown menu BELOW the "+" button (drops down from input). Menu items with icons: "Upload attachment" (subtitle: file,image,video,audio), "Deep Research", "Create Image", "Create Video", "Web Dev", "Slides", "More >" (has chevron-right).

**Screenshot 4 — "Auto" mode dropdown:**
"Auto ▼" in input bar opens dropdown BELOW the button. Three options: "Auto" (purple checkmark ✓), "Thinking", "Fast". Dark bg dropdown, clean spacing. Chevron flips to "^" when open.

**Screenshot 5 — Both menus visible + "More" submenu:**
Sidebar open + "+" menu open simultaneously. "More >" item expanded into a SIDE PANEL to the right showing: "Web search", "Artifacts", "Layout", "Travel Planner". The submenu appears as a separate column to the right of the main dropdown.

### Key Visual Elements
1. **Collapsible sidebar** with ~50px icon strip (collapsed) / ~280px full panel (expanded)
2. **Floating pill-shaped input bar** with `+` tools menu, `Auto` mode dropdown, mic icon, circular purple send button
3. **Minimal welcome screen**: just "What would you like to explore?" in large centered text (NO suggestion cards)
4. **No navbar/header** in main content area; model name lives in sidebar top
5. **Dark mode primary** with Qwen's exact color palette

### Color Palette

| Element | Value |
|---------|-------|
| Main background | `#171717` |
| Sidebar background | `#1e1e1e` |
| Surface / Input bar | `#2a2a2a` |
| Input border | `#3a3a3a` |
| Text primary | `#fafafc` |
| Text secondary | `#9ca3af` |
| Accent | `#6366f1` / `#818cf8` |
| Hover states | `#333333` |
| Send button | `#6366f1` (circular) |

---

## Constraints

- **DO NOT modify** `app.py` or `chatbot_backend_gemini.py`
- Keep Vanilla JS + Tailwind CSS CDN (no React/Vue)
- Keep existing JS module structure (`app.js`, `chat.js`, `sidebar.js`, `theme.js`, `markdown.js`, `utils.js`)
- Keep DOMPurify, marked.js, highlight.js, Lucide Icons
- All new dropdowns (`+` menu, Auto mode) are **UI-only cosmetic** — they do not change backend behavior
- Dark mode is the **primary/default** theme

---

## Architecture Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `static/index.html` | **Major rewrite** | New sidebar structure (icon strip + panel), remove navbar, new input bar with dropdowns, minimal welcome screen |
| `static/css/styles.css` | **Major rewrite** | Sidebar collapse/expand animations, floating input bar, dropdown menus, icon strip styles, color refinements |
| `static/js/sidebar.js` | **Major rewrite** | Tri-state sidebar (expanded/collapsed/hidden), icon strip rendering, collapse animation logic |
| `static/js/app.js` | **Moderate update** | New state shape (`sidebarMode`), bind new UI elements, remove suggestion card bindings |
| `static/js/chat.js` | **Minor update** | AI messages: no bubble background; user messages: uniform pill shape |
| `static/js/theme.js` | **Minor update** | Move theme toggle to sidebar icon strip |
| `static/js/utils.js` | No change | Existing utilities sufficient |
| `static/js/markdown.js` | No change | Rendering logic unchanged |

---

## Implementation Phases

### Phase 1: Sidebar Redesign (Collapsible Icon Strip)
**Complexity: HIGH** | **Files: `index.html`, `styles.css`, `sidebar.js`, `app.js`**
**ECC Agents: `architect` (design), `code-reviewer` (after)**
**ECC Skills: `frontend-patterns`**

#### Step 1.1: Update App State for Tri-State Sidebar
**File:** `static/js/app.js`
- Change `state.sidebarOpen` (boolean) → `state.sidebarMode` with values `'expanded'`, `'collapsed'`, `'hidden'`
- All sidebar references across modules must use the new state shape
- **Risk:** Medium — all sidebar references must be updated

#### Step 1.2: Restructure Sidebar HTML
**File:** `static/index.html`
- Replace current `<aside>` with two-part structure:
  - **Icon strip** (`#sidebar-icons`): Always visible on desktop, ~50px wide
    - Top icons: sidebar toggle (panel-left), new chat (+), search
    - Bottom icons: theme toggle, user avatar circle
  - **Expanded panel** (`#sidebar-panel`): ~230px wide (total sidebar = 280px)
    - Header: model name "AI Chatbot" with chevron (decorative)
    - Body: thread list (same data as current, restyled)
    - Search input (shown inline or on search icon click)
- **Risk:** High — largest HTML restructure

#### Step 1.3: Sidebar CSS (Collapse/Expand Animations)
**File:** `static/css/styles.css`
- `.sidebar-strip`: fixed 50px width, `#1e1e1e` bg, flex-col, centered icons
- `.sidebar-panel`: 230px width, slides via `transform: translateX(0)` / `translateX(-100%)`
- Transition: `transform 0.25s cubic-bezier(0.4, 0, 0.2, 1)`
- Icon buttons: 40px touch targets, `#333333` hover bg, rounded
- **Risk:** Low

#### Step 1.4: Rewrite Sidebar JS Toggle Logic
**File:** `static/js/sidebar.js`
- `toggle()` cycles between expanded ↔ collapsed:
  - `expanded` → `collapsed`: hide panel, show icon strip only, main content expands
  - `collapsed` → `expanded`: show panel + icon strip, main content shrinks
  - Mobile: `hidden` (nothing) vs `expanded` (overlay)
- Icon strip's sidebar-toggle button triggers toggle
- "+" icon calls `Chat.clearChat()`
- Search icon expands sidebar with search focused
- **Risk:** Medium — must handle mobile/desktop breakpoints

#### Step 1.5: Update Responsive Logic
**File:** `static/js/app.js`
- Update `_checkResponsive()`:
  - Mobile (<769px): `sidebarMode = 'hidden'`, no icon strip
  - Tablet (769–1024px): `sidebarMode = 'collapsed'`, icon strip only
  - Desktop (>1024px): `sidebarMode = 'expanded'`, full sidebar
- **Risk:** Low

---

### Phase 2: Input Bar Redesign
**Complexity: HIGH** | **Files: `index.html`, `styles.css`, `app.js`**
**ECC Agents: `code-reviewer` (after)**
**ECC Skills: `frontend-patterns`, `api-design`**

#### Step 2.1: Restructure Input Bar HTML
**File:** `static/index.html`
- Remove current `<footer>` input area with `border-t`
- New floating structure inside main content area:
```html
<div id="input-area">  <!-- positioned absolute bottom, centered -->
  <div id="input-wrapper">  <!-- pill shape, max-w-[700px], mx-auto -->
    <button id="tools-btn"><!-- + icon --></button>
    <textarea id="user-input" placeholder="How can I help you today?"></textarea>
    <div id="input-right-controls">
      <button id="auto-mode-btn">Auto <!-- chevron --></button>
      <button id="mic-btn"><!-- mic icon --></button>
      <button id="send-btn"><!-- send/waveform icon --></button>
    </div>
  </div>
</div>
```
- **Risk:** Medium — textarea auto-resize must still work

#### Step 2.2: "+" Tools Dropdown Menu
**File:** `static/index.html` + `static/js/app.js`
- Hidden dropdown `#tools-dropdown` with menu items:
  - Upload attachment (upload icon + subtitle "file, image, video, audio")
  - Deep Research (sparkles icon)
  - Create Image (image icon)
  - Create Video (video icon)
  - Web Dev (code icon)
  - Slides (presentation icon)
  - More → (chevron-right, opens a **side panel submenu to the right** of the main dropdown)
    - Side submenu items: Web search, Artifacts, Layout, Travel Planner
    - Submenu appears on hover/click of "More" item, positioned to the right edge
- Click handler on `#tools-btn` toggles visibility
- Click-outside-to-close handler
- **All items are cosmetic-only** (no backend wiring)
- **Risk:** Low

#### Step 2.2b: "Auto" Dropdown Direction & Chevron Behavior
- The "Auto" dropdown opens **below** the input bar (not above)
- The chevron on the "Auto" button **flips upward** (^) when dropdown is open, points downward (v) when closed
- Selected option shows a **purple checkmark** (✓) next to it

#### Step 2.3: "Auto" Mode Dropdown
**File:** `static/index.html` + `static/js/app.js`
- Small dropdown `#mode-dropdown` with 3 options:
  - Auto (with checkmark when selected)
  - Thinking
  - Fast
- Store in `App.state.chatMode` (default: `'auto'`)
- On selection: update button label, close dropdown
- **Cosmetic only** — backend always uses same model
- **Risk:** Low

#### Step 2.4: Input Bar CSS
**File:** `static/css/styles.css`
- Pill shape: `border-radius: 28px`, bg `#2a2a2a`, border `1px solid #3a3a3a`
- Width: `max-width: 700px; width: calc(100% - 32px);`
- Send button: `40px × 40px`, `border-radius: 50%`, bg `#6366f1`
- "+" button: same size, rounded, subtle hover
- Mic button: icon only, no background
- "Auto" button: text + chevron, `rounded-full`, subtle border
- Dropdowns: `position: absolute`, dark bg, `rounded-xl`, `shadow-xl`
- Dropdown items: `padding: 10px 16px`, hover bg `#333333`
- **Risk:** Medium — textarea expansion within pill shape

#### Step 2.5: Bind New Input Bar Events
**File:** `static/js/app.js`
- Keep existing textarea auto-resize + Enter/Shift+Enter logic
- Add tools-btn, auto-mode-btn, mic-btn click handlers
- Add click-outside handlers for all dropdowns
- Update send button disabled state logic
- **Risk:** Low

---

### Phase 3: Welcome Screen Redesign
**Complexity: LOW** | **Files: `index.html`, `app.js`, `styles.css`**

#### Step 3.1: Simplify Welcome Screen HTML
**File:** `static/index.html`
- Remove bot avatar gradient circle
- Remove "Hi! I'm your AI Assistant" heading
- Remove all 4 suggestion cards and their grid
- Replace with:
```html
<h1 class="text-4xl font-bold text-white">What would you like to explore?</h1>
```
- Center vertically and horizontally in main content area

#### Step 3.2: Remove Suggestion Card Bindings
**File:** `static/js/app.js`
- Remove `_bindSuggestionCards()` method and its call in `init()`
- Dead code removal

#### Step 3.3: Remove Suggestion Card CSS
**File:** `static/css/styles.css`
- Remove `.suggestion-card` styles

---

### Phase 4: Top Bar / Header Redesign
**Complexity: MEDIUM** | **Files: `index.html`, `styles.css`, `theme.js`**

#### Step 4.1: Remove Current Navbar
**File:** `static/index.html`
- Remove entire `<header id="navbar">` element
- Model name display → sidebar panel top (Phase 1)
- Theme toggle → sidebar icon strip bottom (Phase 1)

#### Step 4.2: Add Minimal Top Controls (Collapsed State)
**File:** `static/index.html`
- When sidebar is collapsed, optionally show a floating model name label in top-left of main area
- Small, subtle text that appears only when sidebar panel is hidden

#### Step 4.3: Move Theme Toggle
**File:** `static/js/theme.js`
- Theme toggle button now lives in sidebar icon strip
- Update `Theme.init()` to find new button location
- Button ID (`theme-toggle`) stays the same

---

### Phase 5: Color Palette & Typography Refinement
**Complexity: LOW** | **Files: `index.html`, `styles.css`**

#### Step 5.1: Audit & Refine Colors
- Verify all color values against Qwen palette (table above)
- Input border: change from `#333333` → `#3a3a3a`
- Add any missing colors to Tailwind config extend

#### Step 5.2: Typography Adjustments
- Welcome text: `text-4xl`, `font-bold`, white
- Sidebar items: `14px`, regular weight
- Chat messages: `15px` (already correct)
- Sidebar section headers: `12px`, uppercase, `letter-spacing: 0.05em`, `#6b7280`
- Model name: `16px`, `font-weight: 600`

---

### Phase 6: Chat Message Styling Adjustments
**Complexity: LOW** | **Files: `chat.js`, `styles.css`**

#### Step 6.1: AI Message Bubble → Transparent
**File:** `static/js/chat.js`
- Remove background color from AI message bubble
- Use `bg-transparent` in dark mode
- Keep bot avatar (gradient circle with icon)

#### Step 6.2: User Message Bubble → Uniform Pill
**File:** `static/js/chat.js`
- Keep right-aligned indigo bubble
- Change to uniform `rounded-2xl` (remove `rounded-br-sm`)

#### Step 6.3: Typing Indicator
- Remove background from typing indicator container
- Keep bouncing dots animation

---

### Phase 7: Animations & Transitions
**Complexity: MEDIUM** | **Files: `styles.css`**

#### Step 7.1: Sidebar Slide Animation
- `transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1)`
- Main content area animates width/margin change smoothly
- Icon strip stays fixed, only panel slides

#### Step 7.2: Dropdown Animations
```css
@keyframes dropdownIn {
  from { opacity: 0; transform: translateY(8px) scale(0.95); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
```
- Applied to `.dropdown-visible` class
- Duration: 150ms ease-out

#### Step 7.3: Message Fade-In Refinement
- Reduce `translateY` from 10px → 6px
- Duration: 0.25s (from 0.3s)

---

### Phase 8: Responsive Design Updates
**Complexity: MEDIUM** | **Files: `styles.css`, `sidebar.js`, `app.js`**

#### Step 8.1: Mobile (<769px)
- Sidebar icon strip and panel both hidden by default
- Hamburger button floats in top-left of main area
- Tapping shows full sidebar as overlay with dark backdrop
- Input bar: full width, still pill-shaped
- Welcome text: `text-2xl`

#### Step 8.2: Tablet (769–1024px)
- Icon strip only (collapsed) by default
- Panel expands as overlay (not pushing content)
- Input bar: `max-width: 600px`

#### Step 8.3: Desktop (>1024px)
- Full sidebar (strip + panel) visible by default
- Toggle collapses to icon strip (panel slides out, content expands)
- Input bar: `max-width: 700px`

---

### Phase 9: Code Review & Security Review
**Complexity: LOW** | **Files: All modified files**
**ECC Agents: `code-reviewer`, `security-reviewer`**
**ECC Skills: `/code-review`, `/verify`, `/simplify`**

#### Step 9.1: Code Review (agent: `code-reviewer`)
- Functions < 50 lines, files < 800 lines
- No deep nesting (>4 levels)
- Proper error handling
- No hardcoded values
- Immutable state updates
- Accessible markup (ARIA labels, keyboard nav)

#### Step 9.2: Security Review (agent: `security-reviewer`)
- DOMPurify still sanitizes all markdown output
- No XSS vectors in new dropdown HTML
- No user input rendered without escaping
- No event listener leaks
- No secrets exposed

#### Step 9.3: Cross-Browser Testing
- Chrome (primary), Firefox, Safari, Mobile Chrome/Safari
- Focus: sidebar animations, dropdown positioning, input bar pill shape, scrollbar styling

---

## Phase Dependency Graph

```
Phase 5 (Colors) ─────────── independent, do first (quick win)
Phase 3 (Welcome) ────────── independent (quick win)
Phase 6 (Chat Messages) ──── independent

Phase 1 (Sidebar) ──────────┐
                             ├──> Phase 4 (Top Bar)
                             ├──> Phase 7.1 (Sidebar anim)
Phase 2 (Input Bar) ────────┤
                             ├──> Phase 7.2 (Dropdown anim)
                             └──> Phase 8 (Responsive)

All phases ────────────────────> Phase 9 (Review)
```

## Recommended Execution Order

| Order | Phase | Why |
|-------|-------|-----|
| 1 | Phase 5: Colors & Typography | Quick win, establishes visual foundation |
| 2 | Phase 3: Welcome Screen | Quick win, simple removal |
| 3 | Phase 1: Sidebar Redesign | Largest change, unlocks Phases 4 and 8 |
| 4 | Phase 4: Top Bar Removal | Depends on Phase 1 |
| 5 | Phase 2: Input Bar Redesign | Second largest change |
| 6 | Phase 6: Chat Message Styling | Quick, independent |
| 7 | Phase 7: Animations | Polish pass after layout is stable |
| 8 | Phase 8: Responsive | Depends on Phases 1 and 2 |
| 9 | Phase 9: Review & Security | Final pass |

---

## ECC Agent & Skill Usage Map

| Phase | ECC Agent | ECC Skill | Purpose |
|-------|-----------|-----------|---------|
| Phase 1 | `architect` | `frontend-patterns` | Sidebar architecture decisions |
| Phase 1 | `code-reviewer` | `/code-review` | Review after implementation |
| Phase 2 | `code-reviewer` | `frontend-patterns` | Input bar review |
| Phase 5 | — | `coding-standards` | Color/typography consistency |
| Phase 9 | `code-reviewer` | `/simplify` | Final code quality |
| Phase 9 | `security-reviewer` | `/verify` | Security & XSS check |

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Sidebar tri-state breaks thread loading | **High** | Test thread click after each sub-step; keep `_loadThread()` unchanged |
| Floating input bar breaks textarea auto-resize | **Medium** | Test auto-resize in isolation; keep existing resize logic |
| Dropdown z-index conflicts with sidebar overlay | **Medium** | Explicit z-index ladder: sidebar=30, overlay=20, dropdowns=50 |
| Removing navbar loses sidebar button on mobile | **High** | Add mobile hamburger in Phase 8.1; don't remove navbar until Phase 1 sidebar is stable |
| Light mode breaks after dark-first redesign | **Medium** | Test light mode after Phase 5; ensure all colors have light-mode equivalents |
| Lucide icons break after HTML restructure | **Low** | Call `lucide.createIcons()` after every DOM update |

---

## Success Criteria

- [ ] Sidebar collapses to icon strip (~50px) with smooth animation
- [ ] Sidebar expands to full panel (~280px) with thread list
- [ ] Icon strip shows: toggle, new chat, search, theme toggle, user avatar
- [ ] Input bar is pill-shaped, centered, floating at bottom
- [ ] "+" button opens tools dropdown with icons and labels
- [ ] "Auto" button opens mode selector dropdown
- [ ] Send button is circular and purple (#6366f1)
- [ ] Welcome screen shows only "What would you like to explore?"
- [ ] No navbar/header visible in main content area
- [ ] AI messages have no/subtle bubble background
- [ ] User messages have indigo pill bubbles
- [ ] Dark mode is default and pixel-accurate to Qwen
- [ ] Light mode still works
- [ ] All existing functionality preserved (send, stream, load thread, delete, search, new chat)
- [ ] Responsive at mobile / tablet / desktop breakpoints
- [ ] No XSS vulnerabilities introduced
- [ ] All files under 800 lines
- [ ] Code reviewed by `code-reviewer` agent
- [ ] Security reviewed by `security-reviewer` agent

---
---

# Part B: Extended Tools with Minimum Latency

## Overview

Add 9 new tools to the LangGraph chatbot organized in a modular `tools/` package, with aggressive latency optimization via connection pooling (httpx), TTL caching, strict timeouts, content truncation, and parallel tool execution. The crown feature is **agentic web search** — the LLM autonomously searches, reads multiple pages in parallel, and synthesizes answers with citations.

## Final Tool Count: 12 (3 existing + 9 new)

| # | Tool | Type | Network Calls | Latency (cold) | Latency (cached) |
|---|------|------|--------------|-----------------|-------------------|
| 1 | `web_search` | Existing (enhanced) | 1 | <800ms | <1ms |
| 2 | `calculator` | Existing | 0 | <1ms | N/A |
| 3 | `get_stock_price` | Existing | 1 | <1s | N/A |
| 4 | `wikipedia_lookup` | New — Free | 1 | <500ms | <1ms |
| 5 | `read_webpage` | New — Free | 1 | <3s | <1ms |
| 6 | `python_execute` | New — Free | 0 (subprocess) | <5s | N/A |
| 7 | `convert_units` | New — Free | 0 | <5ms | N/A |
| 8 | `datetime_info` | New — Free | 0 | <5ms | N/A |
| 9 | `dictionary_lookup` | New — Free | 1 | <400ms | <1ms |
| 10 | `news_search` | New — Serper | 1 | <800ms | <1ms |
| 11 | `youtube_search` | New — Serper | 1 | <800ms | <1ms |
| 12 | `image_search` | New — Serper | 1 | <800ms | <1ms |

## Latency Optimization Strategy

| Strategy | How | Impact |
|----------|-----|--------|
| **Connection pooling** | Single `httpx.Client` shared across all tools, keep-alive enabled | -50–100ms per HTTP call (no TCP/TLS handshake) |
| **Strict timeouts** | 4s connect, 5s read on all external HTTP calls | Prevents 30s+ hangs on slow APIs |
| **TTL caching** | `@ttl_cache(seconds=300)` on search, Wikipedia, dictionary | Instant on repeated queries |
| **Content truncation** | Webpage reader returns max 6000 chars | Fewer LLM input tokens = faster inference |
| **Lightweight extraction** | `trafilatura` for HTML→text (faster than BeautifulSoup) | ~2x faster page parsing |
| **Parallel tool calls** | Gemini 2.5 Flash natively requests parallel tools; LangGraph `ToolNode` executes concurrently | Search + read 3 pages in 1 round instead of 4 |
| **Partial results on timeout** | Tools return error message instead of raising exceptions | User never waits indefinitely |
| **Small tool output** | All tools truncate output | Faster LLM inference on results |

## Target Project Structure

```
chatbot_backend_gemini.py          # Simplified: imports tools from package
app.py                             # UNCHANGED
tools/
  __init__.py                      # Exports all_tools list
  _http_client.py                  # Shared httpx.Client (connection pooling, timeouts)
  _cache.py                        # TTL cache decorator
  existing_tools.py                # web_search (enhanced), calculator, get_stock_price
  wikipedia_tool.py                # Wikipedia REST API
  webpage_reader.py                # URL fetcher + trafilatura extraction
  python_repl.py                   # Sandboxed subprocess Python execution
  unit_converter.py                # pint-based unit conversion
  datetime_tool.py                 # Timezone, date math (stdlib)
  dictionary_tool.py               # Free Dictionary API
  serper_tools.py                  # news_search, youtube_search, image_search
tests/
  test_tools.py                    # Unit tests for all tools
  test_agentic_search.py           # Integration test
  test_latency.py                  # Latency benchmarks
```

## New Dependencies

```
httpx           # Async-capable HTTP client with connection pooling
trafilatura     # Fast HTML-to-text extraction
pint            # Unit conversion library
```

All stdlib: `datetime`, `zoneinfo`, `subprocess`, `functools` — no install needed.

---

## Implementation Phases

### Phase B1: Infrastructure — Shared HTTP Client & Cache
**Complexity: LOW** | **Files: 3 new files**

#### Step B1.1: Create `tools/` package
- Create `tools/__init__.py` (initially empty)

#### Step B1.2: Shared HTTP client (`tools/_http_client.py`)
```python
import httpx

_client: httpx.Client | None = None

def get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            timeout=httpx.Timeout(connect=4.0, read=5.0, write=5.0, pool=5.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            headers={"User-Agent": "ChatBot/1.0"},
            follow_redirects=True,
        )
    return _client
```

#### Step B1.3: TTL cache decorator (`tools/_cache.py`)
```python
import time
from functools import lru_cache, wraps

def ttl_cache(seconds: int = 300, maxsize: int = 256):
    def decorator(func):
        @lru_cache(maxsize=maxsize)
        def _cached(*args, _ttl_round, **kwargs):
            return func(*args, **kwargs)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return _cached(*args, _ttl_round=int(time.time()) // seconds, **kwargs)
        wrapper.cache_clear = _cached.cache_clear
        return wrapper
    return decorator
```

---

### Phase B2: Migrate Existing Tools
**Complexity: MEDIUM** | **Files: `tools/existing_tools.py`, `chatbot_backend_gemini.py`**

#### Step B2.1: Move tools to `tools/existing_tools.py`
- Move `web_search`, `calculator`, `get_stock_price` out of backend file
- Upgrade `get_stock_price` to use `get_client()` instead of `requests.get`
- Add `@ttl_cache(seconds=300)` to `web_search`
- `calculator` stays as-is (pure computation)

#### Step B2.2: Update backend imports
- Remove inline tool definitions from `chatbot_backend_gemini.py`
- Add `from tools import all_tools`
- Change `tools = [web_search, calculator, get_stock_price]` → `tools = all_tools`
- Everything else (graph, chat_node, checkpointer) stays identical

**Verification:** Run `uvicorn app:app`, test web_search, calculator, get_stock_price all still work.

---

### Phase B3: Tier 1 Tools — Zero-Cost, No API Key
**Complexity: MEDIUM** | **Files: 6 new files**

#### Step B3.1: Wikipedia lookup (`tools/wikipedia_tool.py`)
```python
@tool
def wikipedia_lookup(query: str) -> str:
    """Look up a topic on Wikipedia. Returns a concise summary.
    Use for factual info about people, places, events, concepts."""
```
- Uses Wikipedia REST API: `en.wikipedia.org/api/rest_v1/page/summary/{title}`
- `@ttl_cache(seconds=600)`, truncate to 2000 chars
- **Latency:** <500ms cold, <1ms cached

#### Step B3.2: Webpage reader (`tools/webpage_reader.py`)
```python
@tool
def read_webpage(url: str) -> str:
    """Fetch and read the text content of a webpage URL.
    Use after web_search to read full articles for detailed answers.
    You can call this on multiple URLs in parallel for faster research."""
```
- Uses `trafilatura` for extraction, `get_client()` for HTTP
- `@ttl_cache(seconds=300)`, truncate to 6000 chars
- **SSRF prevention:** Block `127.0.0.1`, `localhost`, `10.*`, `192.168.*`, `172.16-31.*`, `169.254.*`, non-HTTP schemes
- **Latency:** <3s cold, <1ms cached

#### Step B3.3: Python REPL (`tools/python_repl.py`)
```python
@tool
def python_execute(code: str) -> str:
    """Execute Python code and return the output.
    Use for calculations, data processing, or logic tasks.
    Print results using print() to see output."""
```
- `subprocess.run()` with 5s timeout
- Block dangerous imports: `os`, `subprocess`, `shutil`, `sys`
- Capture stdout + stderr, truncate to 3000 chars
- **Latency:** <5s (hard timeout)
- **Risk:** HIGH for production, acceptable for personal chatbot

#### Step B3.4: Unit converter (`tools/unit_converter.py`)
```python
@tool
def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """Convert a value between units.
    Supports length, weight, temperature, volume, speed, area.
    Examples: (100, 'km', 'miles'), (72, 'degF', 'degC')"""
```
- Uses `pint` library, pure computation
- **Latency:** <5ms

#### Step B3.5: Date/Time utility (`tools/datetime_tool.py`)
```python
@tool
def datetime_info(action: str, timezone: str = "UTC", date1: str = "", date2: str = "") -> str:
    """Get current date/time or perform date calculations.
    Actions: 'now', 'diff', 'day_of_week', 'add_days'.
    Dates: YYYY-MM-DD. Timezones: 'US/Eastern', 'Asia/Tokyo', etc."""
```
- stdlib only (`datetime`, `zoneinfo`)
- **Latency:** <5ms

#### Step B3.6: Dictionary (`tools/dictionary_tool.py`)
```python
@tool
def dictionary_lookup(word: str) -> str:
    """Look up the definition of an English word.
    Returns definitions, parts of speech, and example usage."""
```
- Free Dictionary API: `api.dictionaryapi.dev/api/v2/entries/en/{word}`
- `@ttl_cache(seconds=3600)`, return first 2 definitions
- **Latency:** <400ms cold, <1ms cached

---

### Phase B4: Tier 2 Tools — Serper-Powered
**Complexity: LOW** | **Files: `tools/serper_tools.py`**

All three use Serper API directly via `get_client()` (not LangChain wrapper — saves ~50ms overhead). Use existing `SERPER_API_KEY`.

```python
@tool
def news_search(query: str) -> str:
    """Search for the latest news articles on a topic.
    Returns headlines, sources, and publication dates."""

@tool
def youtube_search(query: str) -> str:
    """Search YouTube for videos on a topic.
    Returns video titles, channels, and links."""

@tool
def image_search(query: str) -> str:
    """Search for images on a topic. Returns image URLs with titles."""
```

- `@ttl_cache(seconds=300)` on all three
- Endpoints: `google.serper.dev/news`, `/videos`, `/images`
- **Latency:** <800ms each cold, <1ms cached

---

### Phase B5: Agentic Web Search — "Deep Research"
**Complexity: MEDIUM** | **Files: `tools/existing_tools.py` (modify)**

This is **NOT a new tool**. It's emergent behavior from `web_search` + `read_webpage` + LLM reasoning.

#### Step B5.1: Enhance `web_search` output
- Switch from `GoogleSerperAPIWrapper` to direct Serper API via `get_client()`
- Return URLs alongside snippets:
```
Results for "query":
1. [Title](url) - Snippet text here...
2. [Title](url) - Snippet text here...
```
- Why: LangChain wrapper strips URLs, preventing the LLM from calling `read_webpage` on results

#### Step B5.2: Update docstrings for agentic behavior
```python
# web_search docstring:
"""Search the web for current information. Returns titles, URLs, and snippets.
When you need detailed information, first search, then use read_webpage
on the most relevant URLs. Always cite sources with [Title](URL) format."""

# read_webpage docstring:
"""Fetch and read the text content of a webpage URL.
Use after web_search to read full articles for detailed answers.
You can call this on multiple URLs in parallel for faster research."""
```

#### Step B5.3: Verify parallel execution
- LangGraph's `ToolNode` already runs multiple tool calls from a single AI message **concurrently**
- No code change needed — just verify it works

### Agentic Search Flow (3 rounds)

```
User: "What are the latest developments in quantum computing?"

Round 1: LLM → web_search("quantum computing 2026")
  → Returns 5 results with titles, URLs, snippets        ~800ms

Round 2: LLM → read_webpage(url1), read_webpage(url2), read_webpage(url3)  IN PARALLEL
  → ToolNode executes all 3 concurrently                  ~3s (not 9s)

Round 3: LLM → synthesizes answer with citations           ~2-3s streaming
  "Recent developments include...
   - [IBM 1000-qubit](https://...) reports that...
   - According to [Nature](https://...), researchers..."

Total: ~5-7s (vs ~12-15s without parallelism)
```

---

### Phase B6: Wire Everything Together
**Complexity: LOW** | **Files: `tools/__init__.py`, `chatbot_backend_gemini.py`**

#### Step B6.1: Final `tools/__init__.py`
```python
from tools.existing_tools import web_search, calculator, get_stock_price
from tools.wikipedia_tool import wikipedia_lookup
from tools.webpage_reader import read_webpage
from tools.python_repl import python_execute
from tools.unit_converter import convert_units
from tools.datetime_tool import datetime_info
from tools.dictionary_tool import dictionary_lookup
from tools.serper_tools import news_search, youtube_search, image_search

all_tools = [
    web_search, calculator, get_stock_price,
    wikipedia_lookup, read_webpage, python_execute,
    convert_units, datetime_info, dictionary_lookup,
    news_search, youtube_search, image_search,
]
```

#### Step B6.2: Final `chatbot_backend_gemini.py`
- Remove all inline tool code
- Add `from tools import all_tools`
- Set `tools = all_tools`
- Graph construction, chat_node, checkpointer — **all unchanged**

---

### Phase B7: Update Dependencies
**File:** `requirements.txt`

Add:
```
httpx
trafilatura
pint
```

---

### Phase B8: Testing
**Complexity: MEDIUM** | **ECC Agents: `tdd-guide`, `security-reviewer`**

#### Step B8.1: Unit tests (`tests/test_tools.py`)
- Each tool returns a string
- Timeout handling returns graceful messages
- Cache works (second call instant)
- `read_webpage` blocks SSRF (private IPs)
- `python_execute` blocks dangerous imports
- `convert_units` handles incompatible units
- All tools handle empty/None inputs

#### Step B8.2: Integration test (`tests/test_agentic_search.py`)
- Full LangGraph flow: research question → web_search → read_webpage → synthesized answer
- Assert response contains `[Title](URL)` citations

#### Step B8.3: Latency benchmarks (`tests/test_latency.py`)
- Time each tool, assert within latency targets

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Python REPL code execution | **HIGH** | Subprocess with 5s timeout, import blocklist. Personal use only. |
| SSRF via `read_webpage` | **HIGH** | Validate URLs against private IP ranges. Block non-HTTP schemes. |
| Too many tools confuse LLM | **MEDIUM** | Gemini 2.5 Flash handles 10+ tools well. Monitor tool selection quality. |
| Trafilatura fails on some pages | **LOW** | Fallback to regex text extractor. Return partial content. |
| Serper rate limits | **LOW** | TTL cache prevents redundant calls. Free tier: 2500 queries/month. |
| Adding deps breaks venv | **LOW** | Only 3 new packages, all well-maintained. |

---

## Recommended Execution Order

| Order | Phase | Verify |
|-------|-------|--------|
| 1 | B1: Infrastructure (HTTP client, cache) | Files created |
| 2 | B7: Install dependencies (`pip install`) | Import works |
| 3 | B2: Migrate existing tools | Existing chat still works |
| 4 | B3: Tier 1 tools (one at a time) | Each tool works in chat |
| 5 | B4: Tier 2 Serper tools | News/YouTube/Image search works |
| 6 | B5: Agentic search (enhance web_search) | Multi-step research works |
| 7 | B6: Final wiring | All 12 tools accessible |
| 8 | B8: Testing | Tests pass, latency within targets |

---

## Success Criteria

- [ ] All 12 tools callable by the LLM
- [ ] Existing chat functionality works identically (backward compatible)
- [ ] `app.py` requires ZERO changes
- [ ] No single tool call takes longer than 5 seconds
- [ ] Agentic web search completes in under 8 seconds
- [ ] Cached tool calls return in under 5ms
- [ ] `read_webpage` blocks SSRF attempts
- [ ] `python_execute` blocks dangerous imports, enforces 5s timeout
- [ ] All tools return user-friendly error messages on failure
- [ ] Unit tests pass with 80%+ coverage on `tools/` package
- [ ] LLM autonomously performs multi-step research on complex questions
