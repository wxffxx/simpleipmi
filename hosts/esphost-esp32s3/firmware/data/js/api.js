/**
 * SI BMC — API Client Module
 * Shared across Dashboard and HID pages
 */

const API = {
    token: localStorage.getItem('bmc_token') || '',

    // Check if auth is needed and handle login
    async init() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            if (data.authEnabled && !this.token) {
                showLogin();
            } else {
                hideLogin();
            }
            return data;
        } catch (e) {
            console.error('API init failed:', e);
            return null;
        }
    },

    headers() {
        const h = { 'Content-Type': 'application/json' };
        if (this.token) h['Authorization'] = 'Bearer ' + this.token;
        return h;
    },

    async get(url) {
        const sep = url.includes('?') ? '&' : '?';
        const authUrl = this.token ? url + sep + 'auth=' + encodeURIComponent(this.token) : url;
        const res = await fetch(authUrl);
        if (res.status === 401) { showLogin(); throw new Error('Unauthorized'); }
        return res.json();
    },

    async post(url, body = {}) {
        const sep = url.includes('?') ? '&' : '?';
        const authUrl = this.token ? url + sep + 'auth=' + encodeURIComponent(this.token) : url;
        const res = await fetch(authUrl, {
            method: 'POST',
            headers: this.headers(),
            body: JSON.stringify(body)
        });
        if (res.status === 401) { showLogin(); throw new Error('Unauthorized'); }
        return res.json();
    },

    setToken(t) {
        this.token = t;
        localStorage.setItem('bmc_token', t);
    }
};

// ─── Login ────────────────────────────────────────────────
function showLogin() {
    const overlay = document.getElementById('login-overlay');
    if (overlay) overlay.style.display = 'flex';
}

function hideLogin() {
    const overlay = document.getElementById('login-overlay');
    if (overlay) overlay.style.display = 'none';
}

async function doLogin() {
    const pw = document.getElementById('login-password').value;
    const errEl = document.getElementById('login-error');
    
    try {
        const res = await fetch('/api/auth', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: pw })
        });
        const data = await res.json();
        
        if (data.success) {
            API.setToken(data.token);
            hideLogin();
            if (errEl) errEl.style.display = 'none';
            // Trigger page refresh logic
            if (typeof onLoginSuccess === 'function') onLoginSuccess();
        } else {
            if (errEl) { errEl.textContent = data.error || '密码错误'; errEl.style.display = 'block'; }
        }
    } catch (e) {
        if (errEl) { errEl.textContent = '连接失败'; errEl.style.display = 'block'; }
    }
}

// Enter key to login
document.addEventListener('DOMContentLoaded', () => {
    const pwInput = document.getElementById('login-password');
    if (pwInput) {
        pwInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') doLogin();
        });
    }
});

// ─── Toast Notifications ──────────────────────────────────
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
    const toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.innerHTML = '<span>' + (icons[type] || '') + '</span> ' + message;
    container.appendChild(toast);
    
    setTimeout(() => {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 4000);
}

// ─── Utility ──────────────────────────────────────────────
function formatUptime(seconds) {
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (d > 0) return d + '天 ' + h + '时';
    if (h > 0) return h + '时 ' + m + '分';
    return m + '分 ' + s + '秒';
}
