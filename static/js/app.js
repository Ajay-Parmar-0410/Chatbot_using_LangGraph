/* ============================================
   App - Entry Point & State Management
   ============================================ */

const App = {
    state: {
        currentThreadId: null,
        threads: [],
        messages: [],
        isStreaming: false,
        sidebarOpen: true,
        theme: 'dark',
    },

    init() {
        // Initialize modules
        Theme.init();
        Markdown.init();
        Sidebar.init();

        // Bind UI events
        this._bindInputEvents();
        this._bindSuggestionCards();
        this._bindNewChat();

        // Initialize Lucide icons
        if (typeof lucide !== 'undefined') lucide.createIcons();

        // Responsive sidebar check
        this._checkResponsive();
        window.addEventListener('resize', Utils.debounce(() => this._checkResponsive(), 150));
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

    _bindSuggestionCards() {
        document.querySelectorAll('.suggestion-card').forEach((card) => {
            card.addEventListener('click', () => {
                const prompt = card.dataset.prompt;
                if (prompt) Chat.sendMessage(prompt);
            });
        });
    },

    _bindNewChat() {
        const newChatBtn = document.getElementById('new-chat-btn');
        if (newChatBtn) {
            newChatBtn.addEventListener('click', () => {
                Chat.clearChat();
                document.getElementById('user-input').focus();
            });
        }
    },

    _checkResponsive() {
        const sidebar = document.getElementById('sidebar');
        const openBtn = document.getElementById('sidebar-open-btn');

        if (window.innerWidth < 769) {
            sidebar.classList.remove('sidebar-visible');
            sidebar.classList.add('sidebar-hidden');
            openBtn.classList.remove('hidden');
        } else {
            sidebar.classList.remove('sidebar-hidden');
            sidebar.classList.add('sidebar-visible');
            openBtn.classList.add('hidden');
        }
    },
};

// Boot the app
document.addEventListener('DOMContentLoaded', () => App.init());
