/* ============================================
   Utility Functions
   ============================================ */

const Utils = {
    /**
     * Generate a UUID v4.
     */
    generateId() {
        if (crypto.randomUUID) return crypto.randomUUID();
        // Fallback using crypto.getRandomValues (cryptographically secure)
        const bytes = new Uint8Array(16);
        crypto.getRandomValues(bytes);
        bytes[6] = (bytes[6] & 0x0f) | 0x40; // version 4
        bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant 1
        const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
        return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
    },

    /**
     * Group a date into "Today", "Yesterday", "Last 7 Days", or "Older".
     * Uses calendar-day comparison (not elapsed time).
     */
    dateGroup(dateStr) {
        if (!dateStr) return 'Older';
        const now = new Date();
        const date = new Date(dateStr);
        const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const dateStart = new Date(date.getFullYear(), date.getMonth(), date.getDate());
        const diffDays = Math.round((todayStart - dateStart) / (1000 * 60 * 60 * 24));

        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays <= 7) return 'Last 7 Days';
        return 'Older';
    },

    /**
     * Debounce a function.
     */
    debounce(fn, delay) {
        let timer;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => fn(...args), delay);
        };
    },

    /**
     * Escape HTML to prevent XSS in non-markdown contexts.
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
};
