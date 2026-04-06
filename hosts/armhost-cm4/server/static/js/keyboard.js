/**
 * SI BMC — Virtual Keyboard Module
 * Full QWERTY virtual keyboard with function keys, modifiers, and special keys.
 * Sends HID events via WebSocket.
 */

const VirtualKeyboard = {
    container: null,
    modifiers: {
        ShiftLeft: false,
        ControlLeft: false,
        AltLeft: false,
        MetaLeft: false,
    },
    capsLock: false,

    // Complete keyboard layout
    layout: {
        fnRow: [
            { code: 'Escape', label: 'Esc', w: 1 },
            { code: 'F1', label: 'F1' }, { code: 'F2', label: 'F2' },
            { code: 'F3', label: 'F3' }, { code: 'F4', label: 'F4' },
            { code: 'F5', label: 'F5' }, { code: 'F6', label: 'F6' },
            { code: 'F7', label: 'F7' }, { code: 'F8', label: 'F8' },
            { code: 'F9', label: 'F9' }, { code: 'F10', label: 'F10' },
            { code: 'F11', label: 'F11' }, { code: 'F12', label: 'F12' },
            { code: 'PrintScreen', label: 'PrtSc' },
            { code: 'Delete', label: 'Del' },
        ],
        rows: [
            // Row 1: Number row
            [
                { code: 'Backquote', label: '`', shift: '~' },
                { code: 'Digit1', label: '1', shift: '!' },
                { code: 'Digit2', label: '2', shift: '@' },
                { code: 'Digit3', label: '3', shift: '#' },
                { code: 'Digit4', label: '4', shift: '$' },
                { code: 'Digit5', label: '5', shift: '%' },
                { code: 'Digit6', label: '6', shift: '^' },
                { code: 'Digit7', label: '7', shift: '&' },
                { code: 'Digit8', label: '8', shift: '*' },
                { code: 'Digit9', label: '9', shift: '(' },
                { code: 'Digit0', label: '0', shift: ')' },
                { code: 'Minus', label: '-', shift: '_' },
                { code: 'Equal', label: '=', shift: '+' },
                { code: 'Backspace', label: '⌫ Backspace', w: 2 },
            ],
            // Row 2
            [
                { code: 'Tab', label: 'Tab', w: 1.5 },
                { code: 'KeyQ', label: 'Q' }, { code: 'KeyW', label: 'W' },
                { code: 'KeyE', label: 'E' }, { code: 'KeyR', label: 'R' },
                { code: 'KeyT', label: 'T' }, { code: 'KeyY', label: 'Y' },
                { code: 'KeyU', label: 'U' }, { code: 'KeyI', label: 'I' },
                { code: 'KeyO', label: 'O' }, { code: 'KeyP', label: 'P' },
                { code: 'BracketLeft', label: '[', shift: '{' },
                { code: 'BracketRight', label: ']', shift: '}' },
                { code: 'Backslash', label: '\\', shift: '|', w: 1.5 },
            ],
            // Row 3
            [
                { code: 'CapsLock', label: 'Caps', w: 1.75, type: 'caps' },
                { code: 'KeyA', label: 'A' }, { code: 'KeyS', label: 'S' },
                { code: 'KeyD', label: 'D' }, { code: 'KeyF', label: 'F' },
                { code: 'KeyG', label: 'G' }, { code: 'KeyH', label: 'H' },
                { code: 'KeyJ', label: 'J' }, { code: 'KeyK', label: 'K' },
                { code: 'KeyL', label: 'L' },
                { code: 'Semicolon', label: ';', shift: ':' },
                { code: 'Quote', label: "'", shift: '"' },
                { code: 'Enter', label: 'Enter ↵', w: 2.25 },
            ],
            // Row 4
            [
                { code: 'ShiftLeft', label: 'Shift', w: 2.25, type: 'modifier' },
                { code: 'KeyZ', label: 'Z' }, { code: 'KeyX', label: 'X' },
                { code: 'KeyC', label: 'C' }, { code: 'KeyV', label: 'V' },
                { code: 'KeyB', label: 'B' }, { code: 'KeyN', label: 'N' },
                { code: 'KeyM', label: 'M' },
                { code: 'Comma', label: ',', shift: '<' },
                { code: 'Period', label: '.', shift: '>' },
                { code: 'Slash', label: '/', shift: '?' },
                { code: 'ShiftRight', label: 'Shift', w: 2.25, type: 'modifier', modKey: 'ShiftLeft' },
            ],
            // Row 5: Bottom row
            [
                { code: 'ControlLeft', label: 'Ctrl', w: 1.5, type: 'modifier' },
                { code: 'MetaLeft', label: 'Win', w: 1.25, type: 'modifier' },
                { code: 'AltLeft', label: 'Alt', w: 1.25, type: 'modifier' },
                { code: 'Space', label: '', w: 6.25 },
                { code: 'AltRight', label: 'Alt', w: 1.25, type: 'modifier', modKey: 'AltLeft' },
                { code: 'ArrowLeft', label: '←' },
                { code: 'ArrowUp', label: '↑' },
                { code: 'ArrowDown', label: '↓' },
                { code: 'ArrowRight', label: '→' },
            ],
        ],
    },

    init() {
        this.container = document.getElementById('vkbd');
        if (!this.container) return;
        this.render();
    },

    render() {
        let html = '';

        // Function key row
        html += '<div class="vkbd-fn-row">';
        this.layout.fnRow.forEach(key => {
            html += this.renderKey(key, true);
        });
        html += '</div>';

        // Main rows
        this.layout.rows.forEach(row => {
            html += '<div class="vkbd-row">';
            row.forEach(key => {
                html += this.renderKey(key);
            });
            html += '</div>';
        });

        this.container.innerHTML = html;

        // Bind events
        this.container.querySelectorAll('.vkbd-key').forEach(el => {
            const code = el.dataset.code;
            const type = el.dataset.type;

            el.addEventListener('mousedown', (e) => {
                e.preventDefault();
                this.onKeyDown(code, type, el);
            });

            el.addEventListener('mouseup', (e) => {
                e.preventDefault();
                this.onKeyUp(code, type, el);
            });

            el.addEventListener('mouseleave', (e) => {
                if (type !== 'modifier' && type !== 'caps') {
                    this.onKeyUp(code, type, el);
                }
            });

            // Touch support
            el.addEventListener('touchstart', (e) => {
                e.preventDefault();
                this.onKeyDown(code, type, el);
            });

            el.addEventListener('touchend', (e) => {
                e.preventDefault();
                this.onKeyUp(code, type, el);
            });
        });
    },

    renderKey(key, isFn = false) {
        const widthClass = key.w ? this.getWidthClass(key.w) : '';
        const classes = [
            'vkbd-key',
            isFn ? 'vkbd-fn-key' : '',
            widthClass,
            key.type === 'modifier' ? 'modifier' : '',
            key.type === 'caps' ? 'modifier' : '',
        ].filter(Boolean).join(' ');

        const modKey = key.modKey || key.code;
        let label = key.label;
        const shiftLabel = key.shift || '';

        return `<button class="${classes}"
                    data-code="${modKey}"
                    data-type="${key.type || 'normal'}"
                    data-label="${key.label}"
                    data-shift="${shiftLabel}">
                    ${shiftLabel ? `<span class="sub">${shiftLabel}</span>` : ''}
                    ${label}
                </button>`;
    },

    getWidthClass(w) {
        const map = {
            1.25: 'w-125',
            1.5: 'w-15',
            1.75: 'w-175',
            2: 'w-2',
            2.25: 'w-225',
            2.5: 'w-25',
            6.25: 'w-625',
        };
        return map[w] || '';
    },

    onKeyDown(code, type, el) {
        if (type === 'modifier') {
            // Toggle modifier state
            const modKey = code;
            this.modifiers[modKey] = !this.modifiers[modKey];
            el.classList.toggle('active', this.modifiers[modKey]);

            if (this.modifiers[modKey]) {
                API.sendHID({ type: 'keydown', code: modKey });
            } else {
                API.sendHID({ type: 'keyup', code: modKey });
            }
        } else if (type === 'caps') {
            this.capsLock = !this.capsLock;
            el.classList.toggle('active', this.capsLock);
            API.sendHID({ type: 'keydown', code: 'CapsLock' });
            setTimeout(() => {
                API.sendHID({ type: 'keyup', code: 'CapsLock' });
            }, 50);
        } else {
            el.classList.add('pressed');
            API.sendHID({ type: 'keydown', code });
        }
    },

    onKeyUp(code, type, el) {
        if (type === 'modifier' || type === 'caps') return;

        el.classList.remove('pressed');
        API.sendHID({ type: 'keyup', code });

        // Release non-sticky modifiers after key press
        this.releaseModifiers();
    },

    releaseModifiers() {
        Object.keys(this.modifiers).forEach(mod => {
            if (this.modifiers[mod]) {
                this.modifiers[mod] = false;
                API.sendHID({ type: 'keyup', code: mod });
                const el = this.container.querySelector(`[data-code="${mod}"]`);
                if (el) el.classList.remove('active');
            }
        });
    },
};
