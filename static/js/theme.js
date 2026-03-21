/* ============================================
   Theme Toggle (Dark / Light)
   ============================================ */

const Theme = {
    init() {
        const stored = localStorage.getItem('theme');
        const theme = stored || 'dark';
        this.apply(theme);

        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => this.toggle());
        }
    },

    apply(theme) {
        const html = document.documentElement;
        if (theme === 'dark') {
            html.classList.add('dark');
        } else {
            html.classList.remove('dark');
        }
        localStorage.setItem('theme', theme);
        this._updateHighlightTheme(theme);
    },

    toggle() {
        const current = localStorage.getItem('theme') || 'dark';
        const next = current === 'dark' ? 'light' : 'dark';
        this.apply(next);
    },

    current() {
        return localStorage.getItem('theme') || 'dark';
    },

    _updateHighlightTheme(theme) {
        const darkSheet = document.getElementById('hljs-dark');
        const lightSheet = document.getElementById('hljs-light');
        if (darkSheet && lightSheet) {
            darkSheet.disabled = theme !== 'dark';
            lightSheet.disabled = theme !== 'light';
        }
    },
};
