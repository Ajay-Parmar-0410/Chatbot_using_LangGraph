/* ============================================
   Sidebar - Collapsible Icon Strip + Panel
   ============================================ */

const Sidebar = {
    init() {
        this._bindEvents();
        this.loadThreads();
    },

    /**
     * Fetch and render all threads grouped by date.
     */
    async loadThreads() {
        try {
            const res = await fetch('/api/threads');
            const threads = await res.json();
            App.state.threads = threads;
            this._renderThreads(threads);
        } catch {
            // Silently fail - sidebar just stays empty
        }
    },

    /**
     * Set sidebar mode: 'expanded', 'collapsed', or 'hidden'
     */
    setMode(mode) {
        const sidebar = document.getElementById('sidebar');
        const modelLabel = document.getElementById('model-label');
        const mobileBtn = document.getElementById('mobile-menu-btn');

        // Remove all state classes
        sidebar.classList.remove('sidebar-expanded', 'sidebar-collapsed', 'sidebar-hidden');

        // Apply new state
        sidebar.classList.add(`sidebar-${mode}`);
        App.state.sidebarMode = mode;

        // Model label visibility (show when collapsed on desktop)
        if (modelLabel) {
            modelLabel.classList.toggle('hidden', mode !== 'collapsed');
        }

        // Mobile menu button
        if (mobileBtn) {
            mobileBtn.classList.toggle('hidden', mode !== 'hidden');
        }

        // Remove overlay if not mobile-expanded
        if (mode !== 'expanded' || window.innerWidth >= 769) {
            this._removeOverlay();
        }

        if (typeof lucide !== 'undefined') lucide.createIcons();
    },

    /**
     * Toggle between expanded and collapsed (desktop) or hidden and expanded (mobile).
     */
    toggle() {
        const current = App.state.sidebarMode;

        if (window.innerWidth < 769) {
            // Mobile: hidden <-> expanded (overlay)
            if (current === 'hidden') {
                this.setMode('expanded');
                this._addOverlay();
            } else {
                this.setMode('hidden');
            }
        } else {
            // Desktop/tablet: expanded <-> collapsed
            if (current === 'expanded') {
                this.setMode('collapsed');
            } else {
                this.setMode('expanded');
            }
        }
    },

    // --- Private ---

    _bindEvents() {
        const toggleBtn = document.getElementById('sidebar-toggle-btn');
        const newChatBtn = document.getElementById('new-chat-btn');
        const searchToggleBtn = document.getElementById('search-toggle-btn');
        const mobileBtn = document.getElementById('mobile-menu-btn');
        const searchInput = document.getElementById('search-input');

        if (toggleBtn) toggleBtn.addEventListener('click', () => this.toggle());
        if (mobileBtn) mobileBtn.addEventListener('click', () => this.toggle());

        if (newChatBtn) {
            newChatBtn.addEventListener('click', () => {
                Chat.clearChat();
                document.getElementById('user-input').focus();
            });
        }

        if (searchToggleBtn) {
            searchToggleBtn.addEventListener('click', () => {
                // If collapsed, expand first
                if (App.state.sidebarMode === 'collapsed') {
                    this.setMode('expanded');
                }
                // Focus search input
                setTimeout(() => {
                    const input = document.getElementById('search-input');
                    if (input) input.focus();
                }, 300);
            });
        }

        if (searchInput) {
            searchInput.addEventListener(
                'input',
                Utils.debounce((e) => this._filterThreads(e.target.value), 200)
            );
        }
    },

    _renderThreads(threads) {
        const container = document.getElementById('thread-list');
        container.innerHTML = '';

        if (!threads.length) {
            container.innerHTML = '<p class="text-sm text-[#9ca3af] text-center py-4">No conversations yet</p>';
            return;
        }

        // Group by date
        const groups = {};
        for (const t of threads) {
            const group = Utils.dateGroup(t.updated_at);
            if (!groups[group]) groups[group] = [];
            groups[group].push(t);
        }

        const order = ['Today', 'Yesterday', 'Last 7 Days', 'Older'];
        for (const groupName of order) {
            const items = groups[groupName];
            if (!items || !items.length) continue;

            const section = document.createElement('div');
            section.className = 'mb-3';
            const label = document.createElement('p');
            label.className = 'text-xs font-medium text-[#6b7280] dark:text-[#9ca3af] px-3 py-1.5 uppercase tracking-wider';
            label.textContent = groupName;
            section.appendChild(label);

            for (const t of items) {
                const item = document.createElement('div');
                const isActive = t.thread_id === App.state.currentThreadId;
                item.className = `thread-item flex items-center justify-between px-3 py-2.5 mx-1 rounded-lg cursor-pointer hover:bg-[#f3f4f6] dark:hover:bg-[#333333] ${isActive ? 'active' : ''}`;
                item.dataset.threadId = t.thread_id;
                item.innerHTML = `
                    <span class="text-sm truncate flex-1">${Utils.escapeHtml(t.title || 'New Chat')}</span>
                    <button class="thread-delete p-1 rounded hover:bg-[#e5e7eb] dark:hover:bg-[#444444] transition-colors" title="Delete">
                        <i data-lucide="trash-2" class="w-3.5 h-3.5 text-[#9ca3af]"></i>
                    </button>
                `;

                item.addEventListener('click', (e) => {
                    if (e.target.closest('.thread-delete')) return;
                    this._loadThread(t.thread_id);
                });

                item.querySelector('.thread-delete').addEventListener('click', (e) => {
                    e.stopPropagation();
                    this._deleteThread(t.thread_id);
                });

                section.appendChild(item);
            }
            container.appendChild(section);
        }

        if (typeof lucide !== 'undefined') lucide.createIcons();
    },

    async _loadThread(threadId) {
        try {
            const res = await fetch(`/api/threads/${threadId}`);
            if (!res.ok) return;
            const data = await res.json();

            App.state.currentThreadId = threadId;
            Chat.loadMessages(data.messages || []);
            this.loadThreads();

            // Close sidebar on mobile
            if (window.innerWidth < 769) this.setMode('hidden');
        } catch {
            // Fail silently
        }
    },

    async _deleteThread(threadId) {
        try {
            await fetch(`/api/threads/${threadId}`, { method: 'DELETE' });
            if (threadId === App.state.currentThreadId) {
                Chat.clearChat();
            }
            this.loadThreads();
        } catch {
            // Fail silently
        }
    },

    _filterThreads(query) {
        const q = query.toLowerCase().trim();
        const filtered = q
            ? App.state.threads.filter((t) => (t.title || '').toLowerCase().includes(q))
            : App.state.threads;
        this._renderThreads(filtered);
    },

    _addOverlay() {
        if (document.getElementById('sidebar-overlay')) return;
        const overlay = document.createElement('div');
        overlay.id = 'sidebar-overlay';
        overlay.className = 'fixed inset-0 bg-black/50 z-20';
        overlay.addEventListener('click', () => this.toggle());
        document.body.appendChild(overlay);
    },

    _removeOverlay() {
        const overlay = document.getElementById('sidebar-overlay');
        if (overlay) overlay.remove();
    },
};
