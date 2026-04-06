/**
 * SI BMC — Virtual Keyboard Renderer
 * Full 104-key layout rendered into #vkbd container
 */

const KEYBOARD_LAYOUT = [
    // Row 0: Function keys
    [
        { label: 'Esc', code: 'Escape', w: 1 },
        { spacer: 0.5 },
        { label: 'F1', code: 'F1' }, { label: 'F2', code: 'F2' },
        { label: 'F3', code: 'F3' }, { label: 'F4', code: 'F4' },
        { spacer: 0.25 },
        { label: 'F5', code: 'F5' }, { label: 'F6', code: 'F6' },
        { label: 'F7', code: 'F7' }, { label: 'F8', code: 'F8' },
        { spacer: 0.25 },
        { label: 'F9', code: 'F9' }, { label: 'F10', code: 'F10' },
        { label: 'F11', code: 'F11' }, { label: 'F12', code: 'F12' },
        { spacer: 0.25 },
        { label: 'PrtSc', code: 'PrintScreen' },
        { label: 'ScrLk', code: 'ScrollLock' },
        { label: 'Pause', code: 'Pause' },
    ],
    // Row 1: Number row
    [
        { label: '`', code: 'Backquote' },
        { label: '1', code: 'Digit1' }, { label: '2', code: 'Digit2' },
        { label: '3', code: 'Digit3' }, { label: '4', code: 'Digit4' },
        { label: '5', code: 'Digit5' }, { label: '6', code: 'Digit6' },
        { label: '7', code: 'Digit7' }, { label: '8', code: 'Digit8' },
        { label: '9', code: 'Digit9' }, { label: '0', code: 'Digit0' },
        { label: '-', code: 'Minus' }, { label: '=', code: 'Equal' },
        { label: '⌫ Bksp', code: 'Backspace', cls: 'w-backspace' },
        { spacer: 0.25 },
        { label: 'Ins', code: 'Insert' }, { label: 'Home', code: 'Home' },
        { label: 'PgUp', code: 'PageUp' },
    ],
    // Row 2: QWERTY
    [
        { label: 'Tab', code: 'Tab', cls: 'w-tab' },
        { label: 'Q', code: 'KeyQ' }, { label: 'W', code: 'KeyW' },
        { label: 'E', code: 'KeyE' }, { label: 'R', code: 'KeyR' },
        { label: 'T', code: 'KeyT' }, { label: 'Y', code: 'KeyY' },
        { label: 'U', code: 'KeyU' }, { label: 'I', code: 'KeyI' },
        { label: 'O', code: 'KeyO' }, { label: 'P', code: 'KeyP' },
        { label: '[', code: 'BracketLeft' }, { label: ']', code: 'BracketRight' },
        { label: '\\', code: 'Backslash' },
        { spacer: 0.25 },
        { label: 'Del', code: 'Delete' }, { label: 'End', code: 'End' },
        { label: 'PgDn', code: 'PageDown' },
    ],
    // Row 3: Home row
    [
        { label: 'Caps', code: 'CapsLock', cls: 'w-caps' },
        { label: 'A', code: 'KeyA' }, { label: 'S', code: 'KeyS' },
        { label: 'D', code: 'KeyD' }, { label: 'F', code: 'KeyF' },
        { label: 'G', code: 'KeyG' }, { label: 'H', code: 'KeyH' },
        { label: 'J', code: 'KeyJ' }, { label: 'K', code: 'KeyK' },
        { label: 'L', code: 'KeyL' }, { label: ';', code: 'Semicolon' },
        { label: "'", code: 'Quote' },
        { label: 'Enter ↵', code: 'Enter', cls: 'w-enter' },
    ],
    // Row 4: Shift row
    [
        { label: 'Shift', code: 'ShiftLeft', cls: 'w-shift modifier', modifier: true },
        { label: 'Z', code: 'KeyZ' }, { label: 'X', code: 'KeyX' },
        { label: 'C', code: 'KeyC' }, { label: 'V', code: 'KeyV' },
        { label: 'B', code: 'KeyB' }, { label: 'N', code: 'KeyN' },
        { label: 'M', code: 'KeyM' },
        { label: ',', code: 'Comma' }, { label: '.', code: 'Period' },
        { label: '/', code: 'Slash' },
        { label: 'Shift', code: 'ShiftRight', cls: 'w-shift modifier', modifier: true },
        { spacer: 0.25 },
        { spacer: 1 },
        { label: '↑', code: 'ArrowUp' },
    ],
    // Row 5: Bottom row
    [
        { label: 'Ctrl', code: 'ControlLeft', cls: 'w-ctrl modifier', modifier: true },
        { label: 'Win', code: 'MetaLeft', cls: 'w-ctrl modifier', modifier: true },
        { label: 'Alt', code: 'AltLeft', cls: 'w-ctrl modifier', modifier: true },
        { label: '', code: 'Space', cls: 'w-space' },
        { label: 'Alt', code: 'AltRight', cls: 'w-ctrl modifier', modifier: true },
        { label: 'Win', code: 'MetaRight', cls: 'w-ctrl modifier', modifier: true },
        { label: 'Menu', code: 'ContextMenu', cls: 'w-ctrl' },
        { label: 'Ctrl', code: 'ControlRight', cls: 'w-ctrl modifier', modifier: true },
        { spacer: 0.25 },
        { label: '←', code: 'ArrowLeft' },
        { label: '↓', code: 'ArrowDown' },
        { label: '→', code: 'ArrowRight' },
    ]
];

// Active modifiers state
const activeModifiers = new Set();

function renderKeyboard() {
    const container = document.getElementById('vkbd');
    if (!container) return;
    
    container.innerHTML = '';
    
    for (const row of KEYBOARD_LAYOUT) {
        const rowEl = document.createElement('div');
        rowEl.className = 'vkbd-row';
        
        for (const key of row) {
            if (key.spacer !== undefined) {
                const spacer = document.createElement('div');
                spacer.style.width = (key.spacer * 34 + (key.spacer - 1) * 3) + 'px';
                spacer.style.flexShrink = '0';
                rowEl.appendChild(spacer);
                continue;
            }
            
            const btn = document.createElement('button');
            btn.className = 'vkbd-key' + (key.cls ? ' ' + key.cls : '');
            btn.textContent = key.label;
            btn.dataset.code = key.code;
            
            if (key.modifier) {
                btn.dataset.modifier = 'true';
            }
            
            // Mouse events
            btn.addEventListener('mousedown', (e) => {
                e.preventDefault();
                vkbdKeyDown(key.code, key.modifier, btn);
            });
            btn.addEventListener('mouseup', (e) => {
                e.preventDefault();
                vkbdKeyUp(key.code, key.modifier, btn);
            });
            btn.addEventListener('mouseleave', (e) => {
                if (!key.modifier) vkbdKeyUp(key.code, false, btn);
            });
            
            // Touch events
            btn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                vkbdKeyDown(key.code, key.modifier, btn);
            });
            btn.addEventListener('touchend', (e) => {
                e.preventDefault();
                vkbdKeyUp(key.code, key.modifier, btn);
            });
            
            rowEl.appendChild(btn);
        }
        
        container.appendChild(rowEl);
    }
}

function vkbdKeyDown(code, isModifier, btn) {
    if (isModifier) {
        // Toggle modifier
        if (activeModifiers.has(code)) {
            activeModifiers.delete(code);
            btn.classList.remove('pressed');
            if (typeof sendHIDMessage === 'function') {
                sendHIDMessage({ type: 'keyup', code: code });
            }
        } else {
            activeModifiers.add(code);
            btn.classList.add('pressed');
            if (typeof sendHIDMessage === 'function') {
                sendHIDMessage({ type: 'keydown', code: code });
            }
        }
    } else {
        btn.classList.add('pressed');
        if (typeof sendHIDMessage === 'function') {
            sendHIDMessage({ type: 'keydown', code: code });
        }
    }
}

function vkbdKeyUp(code, isModifier, btn) {
    if (!isModifier) {
        btn.classList.remove('pressed');
        if (typeof sendHIDMessage === 'function') {
            sendHIDMessage({ type: 'keyup', code: code });
        }
        
        // Auto-release modifiers after a non-modifier key
        if (activeModifiers.size > 0) {
            for (const mod of activeModifiers) {
                if (typeof sendHIDMessage === 'function') {
                    sendHIDMessage({ type: 'keyup', code: mod });
                }
                // Remove pressed class from modifier buttons
                const modBtn = document.querySelector('[data-code="' + mod + '"]');
                if (modBtn) modBtn.classList.remove('pressed');
            }
            activeModifiers.clear();
        }
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', renderKeyboard);
