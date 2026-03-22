/* ============================================
   Markdown Rendering (marked.js + highlight.js + DOMPurify)
   ============================================ */

const Markdown = {
    init() {
        if (typeof marked === 'undefined') return;

        const renderer = new marked.Renderer();
        const originalCode = renderer.code.bind(renderer);

        renderer.code = function (code, lang) {
            if (typeof hljs !== 'undefined') {
                const validLang = lang && hljs.getLanguage(lang) ? lang : null;
                const highlighted = validLang
                    ? hljs.highlight(code, { language: validLang }).value
                    : hljs.highlightAuto(code).value;
                return `<pre><code class="hljs language-${validLang || ''}">${highlighted}</code></pre>`;
            }
            return originalCode(code, lang);
        };

        marked.setOptions({
            renderer,
            breaks: true,
            gfm: true,
        });

        // DOMPurify hook: enforce noopener on _blank links
        if (typeof DOMPurify !== 'undefined') {
            DOMPurify.addHook('afterSanitizeAttributes', (node) => {
                if (node.tagName === 'A') {
                    node.setAttribute('target', '_blank');
                    node.setAttribute('rel', 'noopener noreferrer');
                }
            });
        }
    },

    /**
     * Render markdown string to sanitized HTML.
     */
    render(text) {
        if (!text) return '';

        // Fail closed: if DOMPurify is unavailable, render as plain text only
        if (typeof DOMPurify === 'undefined') {
            return Utils.escapeHtml(text).replace(/\n/g, '<br>');
        }

        let html;
        if (typeof marked !== 'undefined') {
            html = marked.parse(text);
        } else {
            return Utils.escapeHtml(text).replace(/\n/g, '<br>');
        }

        return DOMPurify.sanitize(html, {
            ALLOWED_ATTR: ['class', 'href', 'src', 'alt', 'title', 'target', 'rel'],
            ALLOWED_URI_REGEXP: /^(?:https?|mailto):/i,
            FORCE_BODY: true,
        });
    },

    /**
     * Add copy buttons to all code blocks within a container.
     */
    addCodeCopyButtons(container) {
        const blocks = container.querySelectorAll('pre');
        blocks.forEach((pre) => {
            // Guard: don't add duplicate buttons
            if (pre.querySelector('.code-copy-btn')) return;

            pre.style.position = 'relative';
            const btn = document.createElement('button');
            btn.className = 'code-copy-btn';
            btn.textContent = 'Copy';
            btn.addEventListener('click', () => {
                const code = pre.querySelector('code');
                const text = code ? code.textContent : pre.textContent;
                navigator.clipboard.writeText(text).then(() => {
                    btn.textContent = 'Copied!';
                    setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
                });
            });
            pre.appendChild(btn);
        });
    },
};
