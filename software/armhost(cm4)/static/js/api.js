/**
 * SI BMC — API Communication Layer
 * Handles REST API calls, WebSocket management, and token handling.
 */

const API = {
    baseUrl: '',
    token: null,
    ws: null,
    wsReconnectTimer: null,
    wsReconnectDelay: 2000,
    wsCallbacks: {},

    // ── REST API ────────────────────────────────────────────────

    async request(method, path, body = null) {
        const headers = { 'Content-Type': 'application/json' };
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        const opts = { method, headers };
        if (body) opts.body = JSON.stringify(body);

        try {
            const res = await fetch(`${this.baseUrl}${path}`, opts);
            if (res.status === 401) {
                this.token = null;
                localStorage.removeItem('si_bmc_token');
                // Could trigger login modal here
            }
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail || `HTTP ${res.status}`);
            }
            return await res.json();
        } catch (error) {
            console.error(`API ${method} ${path} failed:`, error);
            throw error;
        }
    },

    get(path)        { return this.request('GET', path); },
    post(path, body) { return this.request('POST', path, body); },

    // ── Auth ────────────────────────────────────────────────────

    async login(username, password) {
        const data = await this.post('/api/auth/login', { username, password });
        this.token = data.token;
        localStorage.setItem('si_bmc_token', data.token);
        return data;
    },

    loadToken() {
        this.token = localStorage.getItem('si_bmc_token');
    },

    // ── System Info ─────────────────────────────────────────────

    getSystemInfo() { return this.get('/api/system/info'); },
    getStatus()     { return this.get('/api/status'); },
    getLogs(n = 50) { return this.get(`/api/system/logs?n=${n}`); },

    // ── Video ───────────────────────────────────────────────────

    getStreamUrl()   { return `${this.baseUrl}/api/stream`; },
    getSnapshotUrl() { return `${this.baseUrl}/api/snapshot`; },
    getVideoStatus() { return this.get('/api/video/status'); },

    async setVideoQuality(q) {
        return this.post(`/api/video/quality?quality=${q}`);
    },

    // ── Power ───────────────────────────────────────────────────

    powerOn()     { return this.post('/api/power/on'); },
    powerOff()    { return this.post('/api/power/off'); },
    powerReset()  { return this.post('/api/power/reset'); },
    powerStatus() { return this.get('/api/power/status'); },

    // ── GPIO ────────────────────────────────────────────────────

    gpioStatus() { return this.get('/api/gpio/status'); },
    gpioConfig() { return this.get('/api/gpio/config'); },

    // ── HID ─────────────────────────────────────────────────────

    hidStatus() { return this.get('/api/hid/status'); },

    // ── WebSocket ───────────────────────────────────────────────

    connectWS(callbacks = {}) {
        this.wsCallbacks = callbacks;
        this._openWS();
    },

    _openWS() {
        if (this.ws && this.ws.readyState <= 1) return;

        const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${proto}//${location.host}/api/ws/hid`;

        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
            console.log('[WS] Connected');
            if (this.wsCallbacks.onOpen) this.wsCallbacks.onOpen();
            this.wsReconnectDelay = 2000;
        };

        this.ws.onclose = (e) => {
            console.log('[WS] Disconnected', e.code);
            if (this.wsCallbacks.onClose) this.wsCallbacks.onClose();
            // Auto-reconnect
            this.wsReconnectTimer = setTimeout(() => {
                this._openWS();
            }, this.wsReconnectDelay);
            this.wsReconnectDelay = Math.min(this.wsReconnectDelay * 1.5, 15000);
        };

        this.ws.onerror = (e) => {
            console.error('[WS] Error', e);
            if (this.wsCallbacks.onError) this.wsCallbacks.onError(e);
        };

        this.ws.onmessage = (e) => {
            if (this.wsCallbacks.onMessage) {
                this.wsCallbacks.onMessage(JSON.parse(e.data));
            }
        };
    },

    sendHID(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    },

    disconnectWS() {
        if (this.wsReconnectTimer) clearTimeout(this.wsReconnectTimer);
        if (this.ws) {
            this.ws.onclose = null;
            this.ws.close();
            this.ws = null;
        }
    },
};

// ── Toast Notifications ─────────────────────────────────────────

const Toast = {
    container: null,

    init() {
        this.container = document.createElement('div');
        this.container.className = 'toast-container';
        document.body.appendChild(this.container);
    },

    show(message, type = 'info') {
        if (!this.container) this.init();

        const icons = {
            success: '✓', error: '✕', warning: '⚠', info: 'ℹ'
        };

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `<span>${icons[type] || 'ℹ'}</span> ${message}`;
        this.container.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 4000);
    },

    success(msg) { this.show(msg, 'success'); },
    error(msg)   { this.show(msg, 'error'); },
    warning(msg) { this.show(msg, 'warning'); },
    info(msg)    { this.show(msg, 'info'); },
};

// ── Confirm Dialog ──────────────────────────────────────────────

function confirmDialog(title, message, onConfirm, confirmClass = 'btn-danger') {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
        <div class="modal">
            <div class="modal-title">${title}</div>
            <div class="modal-body">${message}</div>
            <div class="modal-actions">
                <button class="btn" id="modal-cancel">取消</button>
                <button class="btn ${confirmClass}" id="modal-confirm">确认</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    requestAnimationFrame(() => overlay.classList.add('active'));

    const close = () => {
        overlay.classList.remove('active');
        setTimeout(() => overlay.remove(), 300);
    };

    overlay.querySelector('#modal-cancel').onclick = close;
    overlay.querySelector('#modal-confirm').onclick = () => {
        close();
        onConfirm();
    };
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) close();
    });
}
