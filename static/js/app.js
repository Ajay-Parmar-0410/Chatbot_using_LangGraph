/* ============================================
   App - Entry Point & State Management
   ============================================ */

const App = {
    state: {
        currentThreadId: null,
        threads: [],
        messages: [],
        isStreaming: false,
        sidebarMode: 'expanded', // 'expanded' | 'collapsed' | 'hidden'
        chatMode: 'auto', // 'auto' | 'thinking' | 'fast'
        theme: 'dark',
    },

    _VALID_MODES: ['auto', 'thinking', 'fast'],
    _dropdownTimers: new WeakMap(),

    init() {
        // Initialize modules
        Theme.init();
        Markdown.init();
        Sidebar.init();

        // Bind UI events
        this._bindInputEvents();
        this._bindDropdowns();

        // Initialize Lucide icons
        if (typeof lucide !== 'undefined') lucide.createIcons();

        // Responsive sidebar check
        this._checkResponsive();
        window.addEventListener('resize', Utils.debounce(() => this._checkResponsive(), 150));

        // Global click-outside handler for dropdowns
        document.addEventListener('click', (e) => this._handleClickOutside(e));

        // Escape key closes dropdowns
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this._closeAllDropdowns();
        });
    },

    _bindInputEvents() {
        const input = document.getElementById('user-input');
        const sendBtn = document.getElementById('send-btn');

        // Auto-resize textarea
        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 200) + 'px';
            sendBtn.disabled = !input.value.trim() || App.state.isStreaming;
        });

        // Enter to send, Shift+Enter for newline
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (input.value.trim() && !App.state.isStreaming) {
                    const msg = input.value;
                    input.value = '';
                    input.style.height = 'auto';
                    sendBtn.disabled = true;
                    Chat.sendMessage(msg);
                }
            }
        });

        // Send button click
        sendBtn.addEventListener('click', () => {
            if (input.value.trim() && !App.state.isStreaming) {
                const msg = input.value;
                input.value = '';
                input.style.height = 'auto';
                sendBtn.disabled = true;
                Chat.sendMessage(msg);
            }
        });
    },

    _bindDropdowns() {
        // Tools dropdown (+)
        const toolsBtn = document.getElementById('tools-btn');
        const toolsDropdown = document.getElementById('tools-dropdown');
        const moreToolsBtn = document.getElementById('more-tools-btn');
        const moreSubmenu = document.getElementById('more-submenu');

        if (toolsBtn && toolsDropdown) {
            toolsBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const isOpen = toolsDropdown.classList.contains('dropdown-visible');
                this._closeAllDropdowns();
                if (!isOpen) {
                    this._showDropdown(toolsDropdown);
                    toolsBtn.setAttribute('aria-expanded', 'true');
                }
            });
        }

        // More submenu hover/click
        if (moreToolsBtn && moreSubmenu) {
            moreToolsBtn.addEventListener('mouseenter', () => {
                this._showDropdown(moreSubmenu);
            });

            moreToolsBtn.parentElement.addEventListener('mouseleave', () => {
                this._hideDropdown(moreSubmenu);
            });
        }

        // Auto mode dropdown
        const autoBtn = document.getElementById('auto-mode-btn');
        const modeDropdown = document.getElementById('mode-dropdown');
        const chevron = autoBtn ? autoBtn.querySelector('.mode-chevron') : null;

        if (autoBtn && modeDropdown) {
            autoBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const isOpen = modeDropdown.classList.contains('dropdown-visible');
                this._closeAllDropdowns();
                if (!isOpen) {
                    this._showDropdown(modeDropdown);
                    if (chevron) chevron.classList.add('chevron-up');
                    autoBtn.setAttribute('aria-expanded', 'true');
                }
            });
        }

        // Mode option selection
        document.querySelectorAll('.mode-option').forEach((option) => {
            option.addEventListener('click', (e) => {
                e.stopPropagation();
                const mode = option.dataset.mode;

                // Validate mode against allowlist
                if (!this._VALID_MODES.includes(mode)) return;

                App.state.chatMode = mode;

                // Update label
                const label = document.getElementById('mode-label');
                if (label) {
                    label.textContent = mode.charAt(0).toUpperCase() + mode.slice(1);
                }

                // Update checkmarks
                document.querySelectorAll('.mode-check').forEach((check) => {
                    check.classList.add('hidden');
                });
                const check = option.querySelector('.mode-check');
                if (check) check.classList.remove('hidden');

                this._closeAllDropdowns();
                if (typeof lucide !== 'undefined') lucide.createIcons();
            });
        });
    },

    _showDropdown(dropdown) {
        // Cancel any pending hide timer
        const timer = this._dropdownTimers.get(dropdown);
        if (timer) clearTimeout(timer);

        dropdown.classList.remove('hidden');
        requestAnimationFrame(() => {
            dropdown.classList.add('dropdown-visible');
        });
    },

    _hideDropdown(dropdown) {
        // Cancel any pending timer first
        const existing = this._dropdownTimers.get(dropdown);
        if (existing) clearTimeout(existing);

        dropdown.classList.remove('dropdown-visible');
        const timer = setTimeout(() => dropdown.classList.add('hidden'), 150);
        this._dropdownTimers.set(dropdown, timer);
    },

    _closeAllDropdowns() {
        const dropdowns = document.querySelectorAll('.dropdown-menu');
        const chevron = document.querySelector('.mode-chevron');

        dropdowns.forEach((dd) => this._hideDropdown(dd));

        if (chevron) chevron.classList.remove('chevron-up');

        // Reset aria-expanded
        const toolsBtn = document.getElementById('tools-btn');
        const autoBtn = document.getElementById('auto-mode-btn');
        if (toolsBtn) toolsBtn.setAttribute('aria-expanded', 'false');
        if (autoBtn) autoBtn.setAttribute('aria-expanded', 'false');
    },

    _handleClickOutside(e) {
        const toolsDropdown = document.getElementById('tools-dropdown');
        const modeDropdown = document.getElementById('mode-dropdown');
        const toolsBtn = document.getElementById('tools-btn');
        const autoBtn = document.getElementById('auto-mode-btn');

        // Close tools dropdown (with null guards)
        if (toolsDropdown && toolsBtn
            && !toolsDropdown.contains(e.target)
            && !toolsBtn.contains(e.target)) {
            this._hideDropdown(toolsDropdown);
            toolsBtn.setAttribute('aria-expanded', 'false');
        }

        // Close mode dropdown (with null guards)
        if (modeDropdown && autoBtn
            && !modeDropdown.contains(e.target)
            && !autoBtn.contains(e.target)) {
            this._hideDropdown(modeDropdown);
            autoBtn.setAttribute('aria-expanded', 'false');
            const chevron = document.querySelector('.mode-chevron');
            if (chevron) chevron.classList.remove('chevron-up');
        }
    },

    _checkResponsive() {
        if (window.innerWidth < 769) {
            Sidebar.setMode('hidden');
        } else if (window.innerWidth < 1025) {
            Sidebar.setMode('collapsed');
        } else {
            Sidebar.setMode('expanded');
        }
    },
};

// Boot the app
document.addEventListener('DOMContentLoaded', () => App.init());
