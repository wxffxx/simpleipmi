/**
 * SI BMC — Dashboard Application Logic
 */

let pendingAction = null;
let refreshInterval = null;

// ─── Init ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    const status = await API.init();
    if (status) updateDashboard(status);
    
    // Start periodic refresh
    refreshInterval = setInterval(refreshStatus, 2000);
    
    // Load logs
    refreshLogs();
    setInterval(refreshLogs, 5000);
    
    // Load GPIO config
    refreshGPIO();
});

function onLoginSuccess() {
    refreshStatus();
    refreshLogs();
}

// ─── Refresh Status ───────────────────────────────────────
async function refreshStatus() {
    try {
        const data = await API.get('/api/status');
        updateDashboard(data);
    } catch (e) {
        // Ignore auth errors (login will show)
    }
}

function updateDashboard(data) {
    // Chip info
    setText('chip-model', data.chipModel || 'ESP32-S3');
    setText('chip-detail', (data.cpuFreq || '--') + ' MHz · ' + 
            Math.round((data.freeHeap || 0) / 1024) + ' KB Free');
    
    // Network
    const net = data.network || {};
    setText('net-ip', net.ip || '--');
    setText('net-detail', (net.mode || '--') + ' · ' + (net.link ? '已连接' : '断开'));
    setText('info-ip', net.ip || '--');
    setText('info-mac', net.mac || '--');
    setText('info-gateway', net.gateway || '--');
    setText('info-netmode', net.mode || '--');
    setText('info-link', net.link ? '✓ 已连接' : '✕ 断开');
    
    // HID
    setText('hid-status', data.hidReady ? '就绪' : '未连接');
    const hidDetail = document.getElementById('hid-detail');
    if (hidDetail) hidDetail.textContent = data.hidReady ? '键盘 + 绝对定位鼠标' : '等待 USB 连接...';
    
    // Uptime
    setText('uptime-value', formatUptime(data.uptime || 0));
    const tempEl = document.getElementById('temp-detail');
    if (tempEl) {
        const temp = data.temperature;
        tempEl.textContent = temp > 0 ? 'SoC 温度: ' + temp.toFixed(1) + '°C' : '';
    }
    
    // Version
    setText('version-badge', 'v' + (data.version || '--'));
    
    // Power status
    updatePowerStatus(data.powered);
    
    // WS clients
    setText('ws-clients', (data.wsClients || 0) + ' 个连接');
}

function updatePowerStatus(powered) {
    const indicator = document.getElementById('power-indicator');
    const statusText = document.getElementById('power-status-text');
    const badge = document.getElementById('power-badge');
    
    if (indicator) {
        indicator.className = 'power-indicator ' + (powered ? 'on' : 'off');
        indicator.textContent = powered ? '⏽' : '⭘';
    }
    if (statusText) statusText.textContent = powered ? '已开机 · 运行中' : '已关机';
    if (badge) {
        badge.className = 'badge ' + (powered ? 'badge-success' : 'badge-danger');
        badge.textContent = powered ? '● 运行中' : '○ 已关机';
    }
}

// ─── Logs ─────────────────────────────────────────────────
async function refreshLogs() {
    try {
        const data = await API.get('/api/logs?n=50');
        const container = document.getElementById('log-container');
        if (!container || !data.logs) return;
        
        if (data.logs.length === 0) {
            container.innerHTML = '<div class="log-line text-muted">暂无日志</div>';
            return;
        }
        
        let html = '';
        for (const log of data.logs) {
            html += '<div class="log-line">' +
                    '<span class="log-time">' + (log.time || '') + '</span>' +
                    '<span class="log-level ' + (log.level || '') + '">' + (log.level || '') + '</span>' +
                    '<span class="log-msg">' + escapeHtml(log.message || '') + '</span>' +
                    '</div>';
        }
        container.innerHTML = html;
        container.scrollTop = container.scrollHeight;
    } catch (e) {}
}

// ─── GPIO ─────────────────────────────────────────────────
async function refreshGPIO() {
    try {
        const data = await API.get('/api/gpio/status');
        if (data.power) setText('gpio-pwr', 'GPIO' + data.power.pin);
        if (data.reset) setText('gpio-rst', 'GPIO' + data.reset.pin);
        if (data.power_detect) setText('gpio-led', 'GPIO' + data.power_detect.pin);
    } catch (e) {}
}

// ─── Power Actions ────────────────────────────────────────
async function powerAction(action) {
    try {
        const data = await API.post('/api/power/' + action);
        if (data.success) {
            const msgs = { on: '开机指令已发送', off: '强制关机指令已发送', reset: '重启指令已发送' };
            showToast(msgs[action] || '操作完成', 'success');
        }
    } catch (e) {
        showToast('操作失败: ' + e.message, 'error');
    }
}

function confirmAction(action) {
    pendingAction = action;
    const titles = { off: '确认强制关机', reset: '确认重启' };
    const bodies = {
        off: '这将模拟长按电源按钮 (5 秒) 强制关闭目标主机。确定继续？',
        reset: '这将触发目标主机硬重启。未保存的数据可能丢失。确定继续？'
    };
    
    setText('modal-title', titles[action] || '确认操作');
    setText('modal-body', bodies[action] || '确定要执行此操作吗？');
    
    const modal = document.getElementById('confirm-modal');
    if (modal) modal.classList.add('active');
}

function closeModal() {
    const modal = document.getElementById('confirm-modal');
    if (modal) modal.classList.remove('active');
    pendingAction = null;
}

function executeConfirmed() {
    if (pendingAction) {
        powerAction(pendingAction);
    }
    closeModal();
}

// ─── Helpers ──────────────────────────────────────────────
function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
