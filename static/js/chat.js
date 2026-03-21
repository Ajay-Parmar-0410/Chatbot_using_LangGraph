/* ============================================
   Chat Module - Send / Receive / Stream SSE
   ============================================ */

const Chat = {
    /**
     * Send a message and stream the AI response via SSE.
     */
    async sendMessage(userInput) {
        if (!userInput.trim() || App.state.isStreaming) return;

        const message = userInput.trim();

        // Create thread if needed
        if (!App.state.currentThreadId) {
            App.state.currentThreadId = Utils.generateId();
        }

        // Show user message
        App.state.messages.push({ role: 'user', content: message });
        this._renderUserMessage(message);
        this._showChatContainer();

        // Disable input during streaming
        App.state.isStreaming = true;
        this._updateInputState();

        // Show typing indicator
        const typingEl = this._showTypingIndicator();

        // Stream AI response
        let fullResponse = '';
        let assistantEl = null;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message,
                    thread_id: App.state.currentThreadId,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            // Remove typing indicator, create assistant bubble only after fetch succeeds
            typingEl.remove();
            assistantEl = this._createAssistantBubble();

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const jsonStr = line.slice(6).trim();
                    if (!jsonStr) continue;

                    try {
                        const event = JSON.parse(jsonStr);
                        if (event.type === 'token') {
                            fullResponse += event.content;
                            this._updateAssistantBubble(assistantEl, fullResponse);
                        } else if (event.type === 'done') {
                            // Streaming complete
                        } else if (event.type === 'error') {
                            fullResponse += `\n\nError: ${event.content}`;
                            this._updateAssistantBubble(assistantEl, fullResponse);
                        }
                    } catch {
                        // Skip malformed JSON lines
                    }
                }
            }
        } catch (err) {
            if (typingEl.parentNode) typingEl.remove();
            if (!assistantEl) assistantEl = this._createAssistantBubble();
            fullResponse = `Sorry, something went wrong: ${err.message}`;
            this._updateAssistantBubble(assistantEl, fullResponse);
        }

        // Save assistant message to state
        if (fullResponse) {
            App.state.messages.push({ role: 'assistant', content: fullResponse });
        }

        // Add message actions (copy, regenerate)
        this._addMessageActions(assistantEl, fullResponse);

        // Generate title for new threads
        if (App.state.messages.length === 2) {
            this._generateTitle(App.state.currentThreadId, message);
        }

        // Re-enable input
        App.state.isStreaming = false;
        this._updateInputState();
        this._scrollToBottom();
    },

    /**
     * Regenerate the last AI response.
     */
    async regenerate() {
        if (App.state.isStreaming) return;
        const lastUserMsg = [...App.state.messages].reverse().find((m) => m.role === 'user');
        if (!lastUserMsg) return;

        // Remove the last assistant message from state (immutable) and DOM
        if (App.state.messages.length > 0 && App.state.messages[App.state.messages.length - 1].role === 'assistant') {
            App.state.messages = App.state.messages.slice(0, -1);
        }
        const messagesEl = document.getElementById('messages');
        const lastGroup = messagesEl.querySelector('.message-group:last-child');
        if (lastGroup && lastGroup.dataset.role === 'assistant') {
            lastGroup.remove();
        }

        // Re-send the last user message
        App.state.isStreaming = false;
        await this.sendMessage(lastUserMsg.content);
    },

    /**
     * Load messages from a thread into the UI.
     */
    loadMessages(messages) {
        const messagesEl = document.getElementById('messages');
        messagesEl.innerHTML = '';
        App.state.messages = [...messages];

        for (const msg of messages) {
            if (msg.role === 'user') {
                this._renderUserMessage(msg.content);
            } else if (msg.role === 'assistant') {
                const el = this._createAssistantBubble();
                this._updateAssistantBubble(el, msg.content);
                this._addMessageActions(el, msg.content);
            }
        }

        this._showChatContainer();
        this._scrollToBottom();
    },

    /**
     * Clear the chat UI for a new conversation.
     */
    clearChat() {
        const messagesEl = document.getElementById('messages');
        messagesEl.innerHTML = '';
        App.state.messages = [];
        App.state.currentThreadId = null;
        this._showWelcomeScreen();
    },

    // --- Private helpers ---

    _renderUserMessage(content) {
        const messagesEl = document.getElementById('messages');
        const group = document.createElement('div');
        group.className = 'message-group flex justify-end';
        group.dataset.role = 'user';
        group.innerHTML = `
            <div class="message-bubble max-w-[80%] px-4 py-3 rounded-2xl rounded-br-sm bg-[#6366f1] dark:bg-[#4f46e5] text-white">
                <p class="text-[15px] leading-relaxed whitespace-pre-wrap">${Utils.escapeHtml(content)}</p>
            </div>
        `;
        messagesEl.appendChild(group);
        this._scrollToBottom();
    },

    _createAssistantBubble() {
        const messagesEl = document.getElementById('messages');
        const group = document.createElement('div');
        group.className = 'message-group flex gap-3';
        group.dataset.role = 'assistant';
        group.innerHTML = `
            <div class="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-[#6366f1] to-[#818cf8] flex items-center justify-center mt-1">
                <i data-lucide="bot" class="w-4 h-4 text-white"></i>
            </div>
            <div class="flex-1 min-w-0">
                <div class="message-bubble message-content text-[15px] leading-relaxed bg-[#f3f4f6] dark:bg-[#2a2a2a] rounded-2xl rounded-tl-sm px-4 py-3 inline-block max-w-full">
                </div>
                <div class="message-actions mt-1 flex gap-1"></div>
            </div>
        `;
        messagesEl.appendChild(group);
        // Re-initialize Lucide icons for the new bot avatar
        if (typeof lucide !== 'undefined') lucide.createIcons();
        return group;
    },

    _updateAssistantBubble(el, content) {
        const bubble = el.querySelector('.message-content');
        if (bubble) {
            bubble.innerHTML = Markdown.render(content);
            Markdown.addCodeCopyButtons(bubble);
        }
        this._scrollToBottom();
    },

    _addMessageActions(el, content) {
        const actionsEl = el.querySelector('.message-actions');
        if (!actionsEl) return;
        actionsEl.innerHTML = `
            <button class="action-copy p-1.5 rounded-md hover:bg-[#e5e7eb] dark:hover:bg-[#333333] transition-colors" title="Copy">
                <i data-lucide="copy" class="w-4 h-4 text-[#6b7280]"></i>
            </button>
            <button class="action-regen p-1.5 rounded-md hover:bg-[#e5e7eb] dark:hover:bg-[#333333] transition-colors" title="Regenerate">
                <i data-lucide="refresh-cw" class="w-4 h-4 text-[#6b7280]"></i>
            </button>
        `;

        actionsEl.querySelector('.action-copy').addEventListener('click', () => {
            navigator.clipboard.writeText(content).then(() => {
                const icon = actionsEl.querySelector('.action-copy i');
                icon.setAttribute('data-lucide', 'check');
                if (typeof lucide !== 'undefined') lucide.createIcons();
                setTimeout(() => {
                    icon.setAttribute('data-lucide', 'copy');
                    if (typeof lucide !== 'undefined') lucide.createIcons();
                }, 2000);
            });
        });

        actionsEl.querySelector('.action-regen').addEventListener('click', () => {
            Chat.regenerate();
        });

        if (typeof lucide !== 'undefined') lucide.createIcons();
    },

    _showTypingIndicator() {
        const messagesEl = document.getElementById('messages');
        const typing = document.createElement('div');
        typing.id = 'typing-indicator';
        typing.className = 'flex gap-3 items-start';
        typing.innerHTML = `
            <div class="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-[#6366f1] to-[#818cf8] flex items-center justify-center">
                <i data-lucide="bot" class="w-4 h-4 text-white"></i>
            </div>
            <div class="flex items-center gap-1.5 px-4 py-3 rounded-2xl bg-[#f3f4f6] dark:bg-[#2a2a2a]">
                <span class="typing-dot bg-[#6b7280]"></span>
                <span class="typing-dot bg-[#6b7280]"></span>
                <span class="typing-dot bg-[#6b7280]"></span>
            </div>
        `;
        messagesEl.appendChild(typing);
        if (typeof lucide !== 'undefined') lucide.createIcons();
        this._scrollToBottom();
        return typing;
    },

    _showChatContainer() {
        document.getElementById('welcome-screen').classList.add('hidden');
        document.getElementById('chat-container').classList.remove('hidden');
    },

    _showWelcomeScreen() {
        document.getElementById('welcome-screen').classList.remove('hidden');
        document.getElementById('chat-container').classList.add('hidden');
    },

    _scrollToBottom() {
        const container = document.getElementById('chat-container');
        requestAnimationFrame(() => {
            container.scrollTop = container.scrollHeight;
        });
    },

    _updateInputState() {
        const input = document.getElementById('user-input');
        const sendBtn = document.getElementById('send-btn');
        sendBtn.disabled = !input.value.trim() || App.state.isStreaming;
    },

    async _generateTitle(threadId, firstMessage) {
        try {
            const res = await fetch(`/api/threads/${threadId}/title`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ first_message: firstMessage }),
            });
            const data = await res.json();
            if (data.title) {
                Sidebar.loadThreads();
            }
        } catch {
            // Title generation is non-critical
        }
    },
};
