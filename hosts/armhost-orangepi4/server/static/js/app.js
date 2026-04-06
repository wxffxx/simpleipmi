/**
 * SI BMC — Dashboard Application Logic
 * Handles system monitoring, power control, and device status display.
 */

document.addEventListener('DOMContentLoaded', () => {
    API.loadToken();
    Toast.init();
    Dashboard.init();
});

const Dashboard = {
    updateInterval: null,
    canvasRings: {},

    init() {
        this.setupPowerButtons();
        this.update();
        this.updateInterval = setInterval(() => this.update(), 2000);
        this.loadLogs();
        setInterval(() => this.loadLogs(), 5000);
    },

    async update() {
        try {
            const [sysInfo, status] = await Promise.all([
                API.getSystemInfo(),
                API.getStatus(),
            ]);
            this.renderSystemInfo(sysInfo);
            this.renderStatCards(sysInfo);
            this.renderPowerStatus(status.power);
            this.renderDeviceStatus(status);
            this.renderNetworkInfo(sysInfo.network);
            this.renderGPIOInfo(status.gpio);
        } catch (err) {
            console.error('Dashboard update error:', err);
        }
    },

    // ── Stat Cards (Ring Progress) ──────────────────────────────

    renderStatCards(info) {
        this.drawRing('cpu-ring', info.cpu?.usage_percent || 0, '#3b82f6', '#8b5cf6');
        document.getElementById('cpu-value').textContent = `${Math.round(info.cpu?.usage_percent || 0)}%`;
        document.getElementById('cpu-detail').textContent =
            `${info.cpu?.cores || 0} Cores · ${info.cpu?.freq_mhz || 0} MHz`;

        this.drawRing('mem-ring', info.memory?.usage_percent || 0, '#10b981', '#06b6d4');
        document.getElementById('mem-value').textContent = `${Math.round(info.memory?.usage_percent || 0)}%`;
        document.getElementById('mem-detail').textContent =
            `${info.memory?.used_mb || 0} / ${info.memory?.total_mb || 0} MB`;

        const temp = info.temperature?.celsius || 0;
        const tempPct = Math.min(100, (temp / 85) * 100); // 85°C = 100%
        const tempColor = temp > 70 ? '#ef4444' : temp > 50 ? '#f59e0b' : '#10b981';
        this.drawRing('temp-ring', tempPct, tempColor, tempColor);
        document.getElementById('temp-value').textContent = `${temp}°`;
        document.getElementById('temp-detail').textContent = info.temperature?.source || '';

        this.drawRing('disk-ring', info.disk?.usage_percent || 0, '#8b5cf6', '#06b6d4');
        document.getElementById('disk-value').textContent = `${Math.round(info.disk?.usage_percent || 0)}%`;
        document.getElementById('disk-detail').textContent =
            `${info.disk?.used_gb || 0} / ${info.disk?.total_gb || 0} GB`;
    },

    drawRing(canvasId, percent, color1, color2) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const size = 64;

        canvas.width = size * dpr;
        canvas.height = size * dpr;
        ctx.scale(dpr, dpr);

        const cx = size / 2;
        const cy = size / 2;
        const radius = 26;
        const lineWidth = 5;
        const startAngle = -Math.PI / 2;
        const endAngle = startAngle + (2 * Math.PI * Math.min(100, percent) / 100);

        ctx.clearRect(0, 0, size, size);

        // Background ring
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, 2 * Math.PI);
        ctx.strokeStyle = 'rgba(255,255,255,0.06)';
        ctx.lineWidth = lineWidth;
        ctx.lineCap = 'round';
        ctx.stroke();

        // Progress ring with gradient
        if (percent > 0) {
            const gradient = ctx.createLinearGradient(0, 0, size, size);
            gradient.addColorStop(0, color1);
            gradient.addColorStop(1, color2);

            ctx.beginPath();
            ctx.arc(cx, cy, radius, startAngle, endAngle);
            ctx.strokeStyle = gradient;
            ctx.lineWidth = lineWidth;
            ctx.lineCap = 'round';
            ctx.stroke();
        }
    },

    // ── System Info Bar ─────────────────────────────────────────

    renderSystemInfo(info) {
        const el = document.getElementById('sys-info-bar');
        if (!el) return;
        el.innerHTML = `
            <div class="sys-info-item">🖥 <strong>${info.hostname || 'N/A'}</strong></div>
            <div class="sys-info-item">⏱ Uptime: <strong>${info.uptime?.formatted || 'N/A'}</strong></div>
            <div class="sys-info-item">📊 Load: <strong>${info.load?.['1min'] || 0} / ${info.load?.['5min'] || 0} / ${info.load?.['15min'] || 0}</strong></div>
        `;
    },

    // ── Power Status ────────────────────────────────────────────

    renderPowerStatus(power) {
        const indicator = document.getElementById('power-indicator');
        const statusText = document.getElementById('power-status-text');
        const badge = document.getElementById('power-badge');

        if (power && power.powered) {
            indicator.className = 'power-indicator on';
            indicator.textContent = '⚡';
            statusText.textContent = '已开机 (12V Active)';
            if (badge) {
                badge.className = 'badge badge-success';
                badge.textContent = 'POWERED ON';
            }
        } else {
            indicator.className = 'power-indicator off';
            indicator.textContent = '⭘';
            statusText.textContent = '已关机 (12V Absent)';
            if (badge) {
                badge.className = 'badge badge-danger';
                badge.textContent = 'POWERED OFF';
            }
        }
    },

    // ── Device Status ───────────────────────────────────────────

    renderDeviceStatus(status) {
        const list = document.getElementById('device-list');
        if (!list) return;

        const video = status.video || {};
        const hid = status.hid || {};

        list.innerHTML = `
            <div class="device-item">
                <span class="device-icon">📹</span>
                <div class="device-info">
                    <div class="device-name">视频采集卡 (MS2109)</div>
                    <div class="device-detail">${video.device || '/dev/video0'} · ${video.resolution || 'N/A'}</div>
                </div>
                <span class="status-dot ${video.connected ? 'online' : 'offline'}"></span>
            </div>
            <div class="device-item">
                <span class="device-icon">⌨️</span>
                <div class="device-info">
                    <div class="device-name">HID 键盘</div>
                    <div class="device-detail">${hid.keyboard?.device || '/dev/hidg0'}</div>
                </div>
                <span class="status-dot ${hid.keyboard?.available ? 'online' : 'offline'}"></span>
            </div>
            <div class="device-item">
                <span class="device-icon">🖱</span>
                <div class="device-info">
                    <div class="device-name">HID 鼠标 (绝对坐标)</div>
                    <div class="device-detail">${hid.mouse?.device || '/dev/hidg1'}</div>
                </div>
                <span class="status-dot ${hid.mouse?.available ? 'online' : 'offline'}"></span>
            </div>
            <div class="device-item">
                <span class="device-icon">🔌</span>
                <div class="device-info">
                    <div class="device-name">活跃 KVM 连接</div>
                    <div class="device-detail">${status.active_connections || 0} 个客户端</div>
                </div>
                <span class="badge badge-info">${status.active_connections || 0}</span>
            </div>
        `;
    },

    // ── Network Info ────────────────────────────────────────────

    renderNetworkInfo(network) {
        const list = document.getElementById('network-list');
        if (!list || !network) return;

        list.innerHTML = Object.entries(network).map(([name, iface]) => `
            <div class="network-item">
                <div class="flex items-center gap-sm">
                    <span class="status-dot ${iface.up ? 'online' : 'offline'}"></span>
                    <span class="network-iface">${name}</span>
                </div>
                <span class="network-ip">${iface.ipv4 || 'No IP'}</span>
            </div>
        `).join('');

        if (Object.keys(network).length === 0) {
            list.innerHTML = '<div class="text-muted text-sm" style="padding:8px">暂无网络接口数据</div>';
        }
    },

    // ── GPIO Info ───────────────────────────────────────────────

    renderGPIOInfo(gpio) {
        const list = document.getElementById('gpio-list');
        if (!list || !gpio) return;

        const pins = gpio.pins || {};
        list.innerHTML = Object.entries(pins).map(([key, pin]) => `
            <div class="gpio-item">
                <div>
                    <span class="gpio-name">${pin.name}</span>
                    <span class="text-muted text-xs" style="margin-left:4px">(${key})</span>
                </div>
                <span class="gpio-pin">GPIO ${pin.gpio}</span>
                <span class="gpio-dir ${pin.direction}">${pin.direction.toUpperCase()}</span>
            </div>
        `).join('');
    },

    // ── Power Buttons ───────────────────────────────────────────

    setupPowerButtons() {
        document.getElementById('btn-power-on')?.addEventListener('click', () => {
            confirmDialog(
                '确认开机',
                '确定要发送短按电源键信号吗？这将尝试开启目标主机。',
                async () => {
                    try {
                        await API.powerOn();
                        Toast.success('电源开机信号已发送');
                    } catch (e) {
                        Toast.error('操作失败: ' + e.message);
                    }
                },
                'btn-success'
            );
        });

        document.getElementById('btn-power-off')?.addEventListener('click', () => {
            confirmDialog(
                '⚠️ 确认强制关机',
                '这将长按电源键 5 秒强制关机，可能导致数据丢失！确定继续吗？',
                async () => {
                    try {
                        await API.powerOff();
                        Toast.warning('强制关机信号已发送 (5s长按)');
                    } catch (e) {
                        Toast.error('操作失败: ' + e.message);
                    }
                },
                'btn-danger'
            );
        });

        document.getElementById('btn-reset')?.addEventListener('click', () => {
            confirmDialog(
                '⚠️ 确认重启',
                '确定要发送硬重启信号吗？目标主机将立即重启。',
                async () => {
                    try {
                        await API.powerReset();
                        Toast.warning('重启信号已发送');
                    } catch (e) {
                        Toast.error('操作失败: ' + e.message);
                    }
                },
                'btn-warning'
            );
        });
    },

    // ── Logs ────────────────────────────────────────────────────

    async loadLogs() {
        try {
            const data = await API.getLogs(80);
            const container = document.getElementById('log-container');
            if (!container) return;

            container.innerHTML = (data.logs || []).map(log => `
                <div class="log-line">
                    <span class="log-time">${log.time}</span>
                    <span class="log-level ${log.level}">${log.level}</span>
                    <span class="log-msg">${log.message}</span>
                </div>
            `).join('');

            // Auto-scroll to bottom
            container.scrollTop = container.scrollHeight;
        } catch (err) {
            console.error('Failed to load logs:', err);
        }
    },
};
