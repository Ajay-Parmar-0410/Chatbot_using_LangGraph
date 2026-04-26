/* ============================================
   Memories — long-term memory sidebar panel
   ============================================ */

const Memories = {
    state: {
        items: [],
        expanded: false,
    },

    async init() {
        const toggle = document.getElementById('memories-toggle');
        if (!toggle) return;

        toggle.addEventListener('click', () => this._toggleExpanded());

        // Lazy load on first render so we don't block app boot.
        await this.refresh();
    },

    async refresh() {
        try {
            const resp = await fetch('/api/memories', {
                headers: { 'Accept': 'application/json' },
            });
            if (!resp.ok) {
                throw new Error(`HTTP ${resp.status}`);
            }
            const body = await resp.json();
            this.state = { ...this.state, items: Array.isArray(body.memories) ? body.memories : [] };
            this._render();
        } catch (err) {
            this._renderError(err);
        }
    },

    async _delete(memoryId) {
        const safeId = encodeURIComponent(memoryId);
        try {
            const resp = await fetch(`/api/memories/${safeId}`, { method: 'DELETE' });
            if (!resp.ok) {
                throw new Error(`HTTP ${resp.status}`);
            }
            // Refresh from server to stay in sync with DB.
            await this.refresh();
        } catch (err) {
            this._renderError(err);
        }
    },

    _toggleExpanded() {
        const next = !this.state.expanded;
        this.state = { ...this.state, expanded: next };
        const list = document.getElementById('memories-list');
        const chevron = document.getElementById('memories-chevron');
        const toggle = document.getElementById('memories-toggle');
        if (!list) return;
        if (next) {
            list.classList.remove('hidden');
            if (chevron) chevron.style.transform = 'rotate(180deg)';
            if (toggle) toggle.setAttribute('aria-expanded', 'true');
        } else {
            list.classList.add('hidden');
            if (chevron) chevron.style.transform = '';
            if (toggle) toggle.setAttribute('aria-expanded', 'false');
        }
    },

    _render() {
        const countEl = document.getElementById('memories-count');
        if (countEl) countEl.textContent = `(${this.state.items.length})`;

        const list = document.getElementById('memories-list');
        if (!list) return;
        list.innerHTML = '';

        if (this.state.items.length === 0) {
            const empty = document.createElement('p');
            empty.className = 'text-xs text-[#9ca3af] px-2 py-2';
            empty.textContent = 'No memories saved yet.';
            list.appendChild(empty);
            return;
        }

        for (const m of this.state.items) {
            list.appendChild(this._renderItem(m));
        }
        if (typeof lucide !== 'undefined') lucide.createIcons();
    },

    _renderItem(memory) {
        const row = document.createElement('div');
        row.className = 'group flex items-start gap-2 px-2 py-1.5 rounded-md hover:bg-[#f3f4f6] dark:hover:bg-[#333333] transition-colors';

        const pill = document.createElement('span');
        pill.className = 'text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-[#e0e7ff] dark:bg-[#3730a3] text-[#4338ca] dark:text-[#c7d2fe] flex-shrink-0 mt-0.5';
        pill.textContent = memory.category || 'other';

        const text = document.createElement('span');
        text.className = 'text-xs text-[#374151] dark:text-[#d1d5db] flex-1 break-words';
        text.textContent = memory.content;  // textContent => no XSS risk

        const del = document.createElement('button');
        del.className = 'opacity-0 group-hover:opacity-100 flex-shrink-0 p-1 rounded hover:bg-[#fecaca] dark:hover:bg-[#7f1d1d] transition-all';
        del.title = 'Delete memory';
        del.setAttribute('aria-label', `Delete memory: ${memory.content}`);
        del.innerHTML = '<i data-lucide="x" class="w-3 h-3 text-[#ef4444]"></i>';
        del.addEventListener('click', (e) => {
            e.stopPropagation();
            this._delete(memory.id);
        });

        row.appendChild(pill);
        row.appendChild(text);
        row.appendChild(del);
        return row;
    },

    _renderError(err) {
        const list = document.getElementById('memories-list');
        if (!list) return;
        list.innerHTML = '';
        const msg = document.createElement('p');
        msg.className = 'text-xs text-[#ef4444] px-2 py-2';
        msg.textContent = `Failed to load memories: ${err && err.message ? err.message : 'unknown error'}`;
        list.appendChild(msg);
    },
};

window.Memories = Memories;
