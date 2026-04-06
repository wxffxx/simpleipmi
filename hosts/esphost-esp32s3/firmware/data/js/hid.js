/**
 * SI BMC — HID Control Page Logic
 * WebSocket connection + touchpad + mouse buttons + combo keys
 */

let ws = null;
let wsConnected = false;
let reconnectTimer = null;
let lastMouseX = 0.5, lastMouseY = 0.5;

// ─── Init ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    await API.init();
    connectWebSocket();
    setupTouchpad();
    setupComboButtons();
    setupPhysicalKeyboard();
});

function onLoginSuccess() {
    connectWebSocket();
}

// ─── WebSocket ────────────────────────────────────────────
function connectWebSocket() {
    if (ws && ws.readyState <= 1) return;
    
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = proto + '//' + location.host + '/ws/hid';
    
    ws = new WebSocket(url);
    
    ws.onopen = () => {
        wsConnected = true;
        updateConnectionStatus(true);
        showToast('HID 已连接', 'success');
        if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
    };
    
    ws.onclose = () => {
        wsConnected = false;
        updateConnectionStatus(false);
        // Auto reconnect
        reconnectTimer = setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = () => {
        wsConnected = false;
        updateConnectionStatus(false);
    };
    
    ws.onmessage = (evt) => {
        try {
            const data = JSON.parse(evt.data);
            if (data.type === 'log') {
                // Could display in a mini-log area if needed
            }
        } catch (e) {}
    };
}

function sendHIDMessage(msg) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(msg));
    }
}

function updateConnectionStatus(connected) {
    const el = document.getElementById('ws-status');
    if (!el) return;
    const dot = el.querySelector('.status-dot');
    if (connected) {
        el.className = 'conn-status connected';
        el.innerHTML = '<span class="status-dot online"></span> 已连接';
    } else {
        el.className = 'conn-status disconnected';
        el.innerHTML = '<span class="status-dot offline"></span> 断开';
    }
}

// ─── Touchpad (Relative Mode — like a laptop trackpad) ───
function setupTouchpad() {
    const pad = document.getElementById('touchpad');
    const cursor = document.getElementById('touchpad-cursor');
    if (!pad) return;
    
    let isDown = false;
    let lastX = null, lastY = null;
    const sensitivity = 1.5;  // Adjust trackpad sensitivity
    
    function getClientPos(e) {
        if (e.touches && e.touches.length > 0) {
            return { x: e.touches[0].clientX, y: e.touches[0].clientY };
        }
        return { x: e.clientX, y: e.clientY };
    }
    
    function onMove(e) {
        e.preventDefault();
        if (!isDown) return;
        
        const pos = getClientPos(e);
        const rect = pad.getBoundingClientRect();
        
        // Update visual cursor position (cosmetic only)
        if (cursor) {
            const cx = Math.max(0, Math.min(1, (pos.x - rect.left) / rect.width));
            const cy = Math.max(0, Math.min(1, (pos.y - rect.top) / rect.height));
            cursor.style.left = (cx * 100) + '%';
            cursor.style.top = (cy * 100) + '%';
            cursor.style.display = 'block';
        }
        
        if (lastX !== null && lastY !== null) {
            // Calculate relative delta, normalized to -1.0 ~ 1.0
            const dx = ((pos.x - lastX) / rect.width) * sensitivity;
            const dy = ((pos.y - lastY) / rect.height) * sensitivity;
            
            if (Math.abs(dx) > 0.001 || Math.abs(dy) > 0.001) {
                sendHIDMessage({ type: 'mousemove', x: dx, y: dy });
            }
        }
        
        lastX = pos.x;
        lastY = pos.y;
    }
    
    function onDown(e) {
        e.preventDefault();
        isDown = true;
        pad.classList.add('active');
        const pos = getClientPos(e);
        lastX = pos.x;
        lastY = pos.y;
        
        if (cursor) {
            const rect = pad.getBoundingClientRect();
            const cx = (pos.x - rect.left) / rect.width;
            const cy = (pos.y - rect.top) / rect.height;
            cursor.style.left = (cx * 100) + '%';
            cursor.style.top = (cy * 100) + '%';
            cursor.style.display = 'block';
        }
    }
    
    function onUp(e) {
        isDown = false;
        lastX = null;
        lastY = null;
        pad.classList.remove('active');
    }
    
    // Mouse events
    pad.addEventListener('mousemove', onMove);
    pad.addEventListener('mousedown', onDown);
    pad.addEventListener('mouseup', onUp);
    pad.addEventListener('mouseleave', () => {
        isDown = false;
        lastX = null;
        lastY = null;
        pad.classList.remove('active');
        if (cursor) cursor.style.display = 'none';
    });
    
    // Touch events
    pad.addEventListener('touchmove', onMove, { passive: false });
    pad.addEventListener('touchstart', onDown, { passive: false });
    pad.addEventListener('touchend', onUp);
    
    // Scroll wheel
    pad.addEventListener('wheel', (e) => {
        e.preventDefault();
        const dy = Math.sign(e.deltaY) * -3;
        sendHIDMessage({
            type: 'wheel',
            x: 0, y: 0,
            deltaY: dy,
            deltaX: 0
        });
    }, { passive: false });
    
    // Right click via context menu
    pad.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        sendHIDMessage({ type: 'click', x: 0, y: 0, button: 2 });
    });
}

// ─── Mouse Buttons ────────────────────────────────────────
function mouseBtn(button, pressed) {
    const btnNames = ['mouse-left', 'mouse-middle', 'mouse-right'];
    const el = document.getElementById(btnNames[button]);
    
    if (pressed) {
        if (el) el.classList.add('pressed');
        sendHIDMessage({ type: 'mousedown', x: 0, y: 0, button: button });
    } else {
        if (el) el.classList.remove('pressed');
        sendHIDMessage({ type: 'mouseup', x: 0, y: 0, button: button });
    }
}

// ─── Combo Key Buttons ───────────────────────────────────
function setupComboButtons() {
    document.querySelectorAll('.combo-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const combo = btn.dataset.combo;
            let msg = null;
            
            switch (combo) {
                case 'ctrl-alt-del':
                    msg = { type: 'combo', modifiers: ['ControlLeft', 'AltLeft'], keys: ['Delete'] };
                    break;
                case 'alt-tab':
                    msg = { type: 'combo', modifiers: ['AltLeft'], keys: ['Tab'] };
                    break;
                case 'alt-f4':
                    msg = { type: 'combo', modifiers: ['AltLeft'], keys: ['F4'] };
                    break;
                case 'win':
                    msg = { type: 'combo', modifiers: ['MetaLeft'], keys: [] };
                    break;
                case 'ctrl-alt-f1':
                    msg = { type: 'combo', modifiers: ['ControlLeft', 'AltLeft'], keys: ['F1'] };
                    break;
                case 'ctrl-alt-f7':
                    msg = { type: 'combo', modifiers: ['ControlLeft', 'AltLeft'], keys: ['F7'] };
                    break;
                case 'prtsc':
                    msg = { type: 'combo', modifiers: [], keys: ['PrintScreen'] };
                    break;
            }
            
            if (msg) {
                sendHIDMessage(msg);
                showToast('已发送: ' + btn.title, 'info');
                // Visual feedback
                btn.style.transform = 'scale(0.9)';
                setTimeout(() => { btn.style.transform = ''; }, 150);
            }
        });
    });
}

// ─── Physical Keyboard Capture ────────────────────────────
// Capture physical keyboard input and forward to target machine
function setupPhysicalKeyboard() {
    document.addEventListener('keydown', (e) => {
        // Don't capture when typing in login input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        
        e.preventDefault();
        sendHIDMessage({ type: 'keydown', code: e.code });
        
        // Highlight virtual keyboard key
        const vkbdKey = document.querySelector('.vkbd-key[data-code="' + e.code + '"]');
        if (vkbdKey) vkbdKey.classList.add('pressed');
    });
    
    document.addEventListener('keyup', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        
        e.preventDefault();
        sendHIDMessage({ type: 'keyup', code: e.code });
        
        const vkbdKey = document.querySelector('.vkbd-key[data-code="' + e.code + '"]');
        if (vkbdKey && !vkbdKey.dataset.modifier) vkbdKey.classList.remove('pressed');
    });
}

// ─── Toggle Keyboard ──────────────────────────────────────
function toggleKeyboard() {
    const container = document.getElementById('vkbd-container');
    if (!container) return;
    container.style.display = container.style.display === 'none' ? '' : 'none';
    
    const btn = document.getElementById('btn-toggle-kbd');
    if (btn) btn.classList.toggle('btn-primary');
}

// ─── Release All ──────────────────────────────────────────
function releaseAll() {
    sendHIDMessage({ type: 'releaseall' });
    showToast('已释放全部按键和鼠标', 'info');
    
    // Clear all pressed visual states
    document.querySelectorAll('.vkbd-key.pressed').forEach(k => k.classList.remove('pressed'));
    document.querySelectorAll('.mouse-btn.pressed').forEach(b => b.classList.remove('pressed'));
    if (typeof activeModifiers !== 'undefined') activeModifiers.clear();
}
