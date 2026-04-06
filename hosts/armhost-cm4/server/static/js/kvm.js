/**
 * SI BMC — KVM Core Logic
 * Manages video stream display, keyboard/mouse event capture,
 * and WebSocket communication with the BMC HID subsystem.
 */

document.addEventListener('DOMContentLoaded', () => {
    API.loadToken();
    Toast.init();
    KVM.init();
});

const KVM = {
    videoEl: null,
    overlayEl: null,
    cursorEl: null,
    connected: false,
    keyboardActive: false,

    init() {
        this.videoEl = document.getElementById('kvm-video');
        this.overlayEl = document.getElementById('kvm-overlay');
        this.cursorEl = document.getElementById('kvm-cursor');

        // Start video stream
        this.startVideo();

        // Connect WebSocket for HID
        this.connectHID();

        // Bind mouse events on overlay
        this.bindMouseEvents();

        // Bind physical keyboard events
        this.bindKeyboardEvents();

        // Toolbar buttons
        this.bindToolbar();

        // Initialize virtual keyboard
        if (typeof VirtualKeyboard !== 'undefined') {
            VirtualKeyboard.init();
        }

        // Update status periodically
        setInterval(() => this.updateStatus(), 3000);
    },

    // ── Video Stream ────────────────────────────────────────────

    startVideo() {
        if (this.videoEl) {
            this.videoEl.src = API.getStreamUrl();
            this.videoEl.onerror = () => {
                console.warn('Video stream error, retrying in 3s...');
                setTimeout(() => this.startVideo(), 3000);
            };
        }
    },

    // ── HID WebSocket ───────────────────────────────────────────

    connectHID() {
        API.connectWS({
            onOpen: () => {
                this.connected = true;
                this.updateConnectionUI(true);
                Toast.success('KVM 已连接');
            },
            onClose: () => {
                this.connected = false;
                this.updateConnectionUI(false);
            },
            onError: () => {
                Toast.error('WebSocket 连接错误');
            },
        });
    },

    updateConnectionUI(connected) {
        const statusEl = document.getElementById('kvm-conn-status');
        if (statusEl) {
            statusEl.className = `kvm-status ${connected ? 'connected' : 'disconnected'}`;
            statusEl.innerHTML = `
                <span class="status-dot"></span>
                ${connected ? '已连接' : '未连接'}
            `;
        }
    },

    // ── Mouse Events ────────────────────────────────────────────

    bindMouseEvents() {
        const overlay = this.overlayEl;
        if (!overlay) return;

        // Calculate position relative to actual video content
        const getVideoCoords = (e) => {
            const video = this.videoEl;
            const rect = video.getBoundingClientRect();

            // Account for object-fit: contain
            const videoAspect = video.naturalWidth / video.naturalHeight || 16 / 9;
            const containerAspect = rect.width / rect.height;

            let renderW, renderH, offsetX, offsetY;

            if (containerAspect > videoAspect) {
                // Letterboxed (black bars on sides)
                renderH = rect.height;
                renderW = renderH * videoAspect;
                offsetX = (rect.width - renderW) / 2;
                offsetY = 0;
            } else {
                // Pillarboxed (black bars on top/bottom)
                renderW = rect.width;
                renderH = renderW / videoAspect;
                offsetX = 0;
                offsetY = (rect.height - renderH) / 2;
            }

            let x = (e.clientX - rect.left - offsetX) / renderW;
            let y = (e.clientY - rect.top - offsetY) / renderH;

            // Clamp to [0, 1]
            x = Math.max(0, Math.min(1, x));
            y = Math.max(0, Math.min(1, y));

            return { x, y };
        };

        // Mouse move
        overlay.addEventListener('mousemove', (e) => {
            const { x, y } = getVideoCoords(e);

            // Update custom cursor position
            if (this.cursorEl) {
                this.cursorEl.style.left = e.clientX + 'px';
                this.cursorEl.style.top = e.clientY + 'px';
                this.cursorEl.style.opacity = '1';
            }

            // Send to HID
            API.sendHID({ type: 'mousemove', x, y });
        });

        // Mouse down
        overlay.addEventListener('mousedown', (e) => {
            e.preventDefault();
            const { x, y } = getVideoCoords(e);
            const button = e.button; // 0=left, 1=middle, 2=right
            API.sendHID({ type: 'mousedown', x, y, button });
        });

        // Mouse up
        overlay.addEventListener('mouseup', (e) => {
            e.preventDefault();
            const { x, y } = getVideoCoords(e);
            API.sendHID({ type: 'mouseup', x, y, button: e.button });
        });

        // Scroll wheel
        overlay.addEventListener('wheel', (e) => {
            e.preventDefault();
            const { x, y } = getVideoCoords(e);
            const deltaY = Math.sign(e.deltaY) * -1; // Invert for natural scrolling
            const deltaX = Math.sign(e.deltaX) * -1;
            API.sendHID({ type: 'wheel', x, y, deltaY, deltaX });
        }, { passive: false });

        // Context menu (prevent default)
        overlay.addEventListener('contextmenu', (e) => {
            e.preventDefault();
        });

        // Hide cursor when leaving
        overlay.addEventListener('mouseleave', () => {
            if (this.cursorEl) {
                this.cursorEl.style.opacity = '0';
            }
        });
    },

    // ── Keyboard Events ─────────────────────────────────────────

    bindKeyboardEvents() {
        // Capture keyboard events when overlay is focused or in KVM mode
        document.addEventListener('keydown', (e) => {
            // Only capture if we're focused on the KVM area
            if (!this.isKVMFocused()) return;

            e.preventDefault();
            e.stopPropagation();

            API.sendHID({ type: 'keydown', code: e.code });
        });

        document.addEventListener('keyup', (e) => {
            if (!this.isKVMFocused()) return;

            e.preventDefault();
            e.stopPropagation();

            API.sendHID({ type: 'keyup', code: e.code });
        });

        // Focus the overlay when clicking on it
        if (this.overlayEl) {
            this.overlayEl.setAttribute('tabindex', '0');
            this.overlayEl.addEventListener('click', () => {
                this.overlayEl.focus();
            });
        }
    },

    isKVMFocused() {
        return document.activeElement === this.overlayEl ||
               document.activeElement === document.getElementById('kvm-display');
    },

    // ── Toolbar ─────────────────────────────────────────────────

    bindToolbar() {
        // Fullscreen
        document.getElementById('btn-fullscreen')?.addEventListener('click', () => {
            this.toggleFullscreen();
        });

        // Virtual keyboard toggle
        document.getElementById('btn-keyboard')?.addEventListener('click', () => {
            this.toggleVirtualKeyboard();
        });

        // Combo keys
        document.querySelectorAll('.combo-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const combo = btn.dataset.combo;
                this.sendCombo(combo);
            });
        });

        // Quality slider
        const qualitySlider = document.getElementById('quality-slider');
        const qualityValue = document.getElementById('quality-value');
        if (qualitySlider) {
            qualitySlider.addEventListener('input', (e) => {
                if (qualityValue) qualityValue.textContent = e.target.value;
            });
            qualitySlider.addEventListener('change', async (e) => {
                try {
                    await API.setVideoQuality(parseInt(e.target.value));
                    Toast.info(`画质: ${e.target.value}%`);
                } catch (err) {
                    Toast.error('设置画质失败');
                }
            });
        }
    },

    toggleFullscreen() {
        const wrapper = document.querySelector('.kvm-wrapper');
        if (!wrapper) return;

        if (!document.fullscreenElement) {
            wrapper.requestFullscreen().catch(err => {
                // Fallback: use CSS fullscreen
                wrapper.classList.toggle('fullscreen');
            });
        } else {
            document.exitFullscreen();
        }
    },

    toggleVirtualKeyboard() {
        const wrapper = document.querySelector('.vkbd-wrapper');
        if (wrapper) {
            wrapper.classList.toggle('active');
            this.keyboardActive = wrapper.classList.contains('active');
        }
    },

    sendCombo(combo) {
        const combos = {
            'ctrl-alt-del': {
                modifiers: ['ControlLeft', 'AltLeft'],
                keys: ['Delete']
            },
            'alt-tab': {
                modifiers: ['AltLeft'],
                keys: ['Tab']
            },
            'alt-f4': {
                modifiers: ['AltLeft'],
                keys: ['F4']
            },
            'ctrl-alt-f1': {
                modifiers: ['ControlLeft', 'AltLeft'],
                keys: ['F1']
            },
            'ctrl-alt-f7': {
                modifiers: ['ControlLeft', 'AltLeft'],
                keys: ['F7']
            },
            'win': {
                modifiers: ['MetaLeft'],
                keys: []
            },
            'print-screen': {
                modifiers: [],
                keys: ['PrintScreen']
            },
        };

        const c = combos[combo];
        if (c) {
            API.sendHID({
                type: 'combo',
                modifiers: c.modifiers,
                keys: c.keys,
            });
            Toast.info(`已发送: ${combo.replace(/-/g, '+').toUpperCase()}`);
        }
    },

    // ── Status Update ───────────────────────────────────────────

    async updateStatus() {
        try {
            const videoStatus = await API.getVideoStatus();
            const fpsEl = document.getElementById('kvm-fps');
            if (fpsEl && videoStatus) {
                fpsEl.textContent = `${videoStatus.fps_actual || 0} FPS`;
            }

            const resEl = document.getElementById('kvm-resolution');
            if (resEl && videoStatus) {
                resEl.textContent = videoStatus.resolution || 'N/A';
            }
        } catch (err) {
            // Ignore
        }
    },

    // ── Cleanup ────────────────────────────────────────────────

    destroy() {
        API.disconnectWS();
        if (this.videoEl) this.videoEl.src = '';
    },
};

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    // Release all keys before leaving
    API.sendHID({ type: 'releaseall' });
    KVM.destroy();
});
