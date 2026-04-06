/**
 * SI BMC — USB HID Module Implementation
 * Full JS keyCode → USB HID mapping, keyboard + relative mouse
 * Uses built-in USBHIDMouse (proven to work)
 */

#include "usb_hid.h"
#include "config.h"
#include "USB.h"
#include "USBHIDKeyboard.h"
#include "USBHIDMouse.h"

// Use Arduino's built-in USBHIDKeyboard for keyboard HID
static USBHIDKeyboard Keyboard;

// ─── JavaScript Key → USB HID Keycode Map ─────────────────
struct KeyMapping {
    const char* jsCode;
    uint8_t hidCode;
};

static const KeyMapping KEY_MAP[] = {
    // Letters
    {"KeyA", 0x04}, {"KeyB", 0x05}, {"KeyC", 0x06}, {"KeyD", 0x07},
    {"KeyE", 0x08}, {"KeyF", 0x09}, {"KeyG", 0x0A}, {"KeyH", 0x0B},
    {"KeyI", 0x0C}, {"KeyJ", 0x0D}, {"KeyK", 0x0E}, {"KeyL", 0x0F},
    {"KeyM", 0x10}, {"KeyN", 0x11}, {"KeyO", 0x12}, {"KeyP", 0x13},
    {"KeyQ", 0x14}, {"KeyR", 0x15}, {"KeyS", 0x16}, {"KeyT", 0x17},
    {"KeyU", 0x18}, {"KeyV", 0x19}, {"KeyW", 0x1A}, {"KeyX", 0x1B},
    {"KeyY", 0x1C}, {"KeyZ", 0x1D},
    // Numbers
    {"Digit1", 0x1E}, {"Digit2", 0x1F}, {"Digit3", 0x20}, {"Digit4", 0x21},
    {"Digit5", 0x22}, {"Digit6", 0x23}, {"Digit7", 0x24}, {"Digit8", 0x25},
    {"Digit9", 0x26}, {"Digit0", 0x27},
    // Control keys
    {"Enter", 0x28}, {"Escape", 0x29}, {"Backspace", 0x2A}, {"Tab", 0x2B},
    {"Space", 0x2C}, {"Minus", 0x2D}, {"Equal", 0x2E},
    {"BracketLeft", 0x2F}, {"BracketRight", 0x30}, {"Backslash", 0x31},
    {"Semicolon", 0x33}, {"Quote", 0x34}, {"Backquote", 0x35},
    {"Comma", 0x36}, {"Period", 0x37}, {"Slash", 0x38}, {"CapsLock", 0x39},
    // Function keys
    {"F1", 0x3A}, {"F2", 0x3B}, {"F3", 0x3C}, {"F4", 0x3D},
    {"F5", 0x3E}, {"F6", 0x3F}, {"F7", 0x40}, {"F8", 0x41},
    {"F9", 0x42}, {"F10", 0x43}, {"F11", 0x44}, {"F12", 0x45},
    // Navigation
    {"PrintScreen", 0x46}, {"ScrollLock", 0x47}, {"Pause", 0x48},
    {"Insert", 0x49}, {"Home", 0x4A}, {"PageUp", 0x4B},
    {"Delete", 0x4C}, {"End", 0x4D}, {"PageDown", 0x4E},
    {"ArrowRight", 0x4F}, {"ArrowLeft", 0x50}, {"ArrowDown", 0x51},
    {"ArrowUp", 0x52}, {"NumLock", 0x53},
    // Numpad
    {"NumpadDivide", 0x54}, {"NumpadMultiply", 0x55}, {"NumpadSubtract", 0x56},
    {"NumpadAdd", 0x57}, {"NumpadEnter", 0x58},
    {"Numpad1", 0x59}, {"Numpad2", 0x5A}, {"Numpad3", 0x5B},
    {"Numpad4", 0x5C}, {"Numpad5", 0x5D}, {"Numpad6", 0x5E},
    {"Numpad7", 0x5F}, {"Numpad8", 0x60}, {"Numpad9", 0x61},
    {"Numpad0", 0x62}, {"NumpadDecimal", 0x63},
    // Extra
    {"IntlBackslash", 0x64}, {"ContextMenu", 0x65}, {"Power", 0x66},
    {nullptr, 0}  // sentinel
};

// Modifier key → bitmask
struct ModifierMapping {
    const char* jsCode;
    uint8_t mask;
};

static const ModifierMapping MODIFIER_MAP[] = {
    {"ControlLeft",  0x01}, {"ShiftLeft",    0x02},
    {"AltLeft",      0x04}, {"MetaLeft",     0x08},
    {"ControlRight", 0x10}, {"ShiftRight",   0x20},
    {"AltRight",     0x40}, {"MetaRight",    0x80},
    {nullptr, 0}
};

// ─── Singleton ────────────────────────────────────────────
USBHIDManager usbHID;

// Built-in relative mouse (proven to work)
static USBHIDMouse Mouse;

// ─── Implementation ───────────────────────────────────────

void USBHIDManager::begin() {
    Keyboard.begin();
    Mouse.begin();
    USB.begin();
    
    _ready = true;
    Serial.println("[HID] USB HID initialized (Keyboard + Mouse)");
}

void USBHIDManager::end() {
    releaseAllKeys();
    _ready = false;
}

void USBHIDManager::handleMessage(JsonObject& msg) {
    if (!_ready) return;

    const char* type = msg["type"];
    if (!type) return;

    if (strcmp(type, "keydown") == 0) {
        keyDown(msg["code"] | "");
    } else if (strcmp(type, "keyup") == 0) {
        keyUp(msg["code"] | "");
    } else if (strcmp(type, "mousemove") == 0) {
        mouseMove(msg["x"] | 0.0f, msg["y"] | 0.0f);
    } else if (strcmp(type, "mousedown") == 0) {
        mouseDown(msg["x"] | 0.0f, msg["y"] | 0.0f, msg["button"] | 0);
    } else if (strcmp(type, "mouseup") == 0) {
        mouseUp(msg["x"] | 0.0f, msg["y"] | 0.0f, msg["button"] | 0);
    } else if (strcmp(type, "click") == 0) {
        mouseDown(msg["x"] | 0.0f, msg["y"] | 0.0f, msg["button"] | 0);
        delay(20);
        mouseUp(msg["x"] | 0.0f, msg["y"] | 0.0f, msg["button"] | 0);
    } else if (strcmp(type, "wheel") == 0) {
        mouseScroll(msg["x"] | 0.0f, msg["y"] | 0.0f,
                    msg["deltaY"] | 0, msg["deltaX"] | 0);
    } else if (strcmp(type, "combo") == 0) {
        JsonArray mods = msg["modifiers"];
        JsonArray keys = msg["keys"];
        sendCombo(mods, keys);
    } else if (strcmp(type, "releaseall") == 0) {
        releaseAllKeys();
    }
}

void USBHIDManager::keyDown(const char* code) {
    if (!_ready || !code || !code[0]) return;

    // Check modifier
    uint8_t mod = _jsCodeToModifier(code);
    if (mod) {
        _modifierState |= mod;
    } else {
        uint8_t hid = _jsCodeToHID(code);
        if (hid && _pressedKeyCount < 6) {
            // Check not already pressed
            bool found = false;
            for (int i = 0; i < _pressedKeyCount; i++) {
                if (_pressedKeys[i] == hid) { found = true; break; }
            }
            if (!found) {
                _pressedKeys[_pressedKeyCount++] = hid;
            }
        }
    }
    _sendKeyboardReport();
}

void USBHIDManager::keyUp(const char* code) {
    if (!_ready || !code || !code[0]) return;

    uint8_t mod = _jsCodeToModifier(code);
    if (mod) {
        _modifierState &= ~mod;
    } else {
        uint8_t hid = _jsCodeToHID(code);
        if (hid) {
            for (int i = 0; i < _pressedKeyCount; i++) {
                if (_pressedKeys[i] == hid) {
                    // Shift remaining keys down
                    for (int j = i; j < _pressedKeyCount - 1; j++) {
                        _pressedKeys[j] = _pressedKeys[j + 1];
                    }
                    _pressedKeyCount--;
                    _pressedKeys[_pressedKeyCount] = 0;
                    break;
                }
            }
        }
    }
    _sendKeyboardReport();
}

void USBHIDManager::releaseAllKeys() {
    _modifierState = 0;
    _pressedKeyCount = 0;
    memset(_pressedKeys, 0, sizeof(_pressedKeys));
    _sendKeyboardReport();
    _mouseButtons = 0;
    _sendMouseReport(0, 0);
}

void USBHIDManager::sendCombo(JsonArray& modifiers, JsonArray& keys) {
    if (!_ready) return;

    uint8_t prevMod = _modifierState;
    uint8_t prevCount = _pressedKeyCount;
    uint8_t prevKeys[6];
    memcpy(prevKeys, _pressedKeys, 6);

    // Build combo
    _modifierState = 0;
    _pressedKeyCount = 0;
    memset(_pressedKeys, 0, 6);

    for (JsonVariant m : modifiers) {
        uint8_t mod = _jsCodeToModifier(m.as<const char*>());
        _modifierState |= mod;
    }
    for (JsonVariant k : keys) {
        uint8_t hid = _jsCodeToHID(k.as<const char*>());
        if (hid && _pressedKeyCount < 6) {
            _pressedKeys[_pressedKeyCount++] = hid;
        }
    }

    // Press
    _sendKeyboardReport();
    delay(50);

    // Release
    _modifierState = 0;
    _pressedKeyCount = 0;
    memset(_pressedKeys, 0, 6);
    _sendKeyboardReport();

    // Restore previous state
    _modifierState = prevMod;
    _pressedKeyCount = prevCount;
    memcpy(_pressedKeys, prevKeys, 6);
}

void USBHIDManager::mouseMove(float dx, float dy) {
    if (!_ready) return;
    // dx, dy are relative movement (-1.0 to 1.0 range from JS)
    int8_t mx = constrain((int)(dx * 127), -127, 127);
    int8_t my = constrain((int)(dy * 127), -127, 127);
    Mouse.move(mx, my);
}

void USBHIDManager::mouseDown(float dx, float dy, uint8_t button) {
    if (!_ready) return;
    uint8_t btn = (button == 0) ? MOUSE_LEFT : (button == 2) ? MOUSE_RIGHT : MOUSE_MIDDLE;
    Mouse.press(btn);
    if (dx != 0 || dy != 0) {
        int8_t mx = constrain((int)(dx * 127), -127, 127);
        int8_t my = constrain((int)(dy * 127), -127, 127);
        Mouse.move(mx, my);
    }
}

void USBHIDManager::mouseUp(float dx, float dy, uint8_t button) {
    if (!_ready) return;
    uint8_t btn = (button == 0) ? MOUSE_LEFT : (button == 2) ? MOUSE_RIGHT : MOUSE_MIDDLE;
    Mouse.release(btn);
}

void USBHIDManager::mouseScroll(float dx, float dy, int8_t deltaY, int8_t deltaX) {
    if (!_ready) return;
    Mouse.move(0, 0, deltaY, deltaX);
}

void USBHIDManager::_sendKeyboardReport() {
    KeyReport report = {0};
    report.modifiers = _modifierState;
    report.reserved = 0x00;
    for (int i = 0; i < 6 && i < _pressedKeyCount; i++) {
        report.keys[i] = _pressedKeys[i];
    }
    Keyboard.sendReport(&report);
}

void USBHIDManager::_sendMouseReport(uint16_t absX, uint16_t absY, int8_t scrollY, int8_t scrollX) {
    // Not used in relative mode, but keep for interface compatibility
    Mouse.move(0, 0, scrollY, scrollX);
}

uint8_t USBHIDManager::_jsCodeToHID(const char* code) {
    for (int i = 0; KEY_MAP[i].jsCode != nullptr; i++) {
        if (strcmp(KEY_MAP[i].jsCode, code) == 0) {
            return KEY_MAP[i].hidCode;
        }
    }
    return 0;
}

uint8_t USBHIDManager::_jsCodeToModifier(const char* code) {
    for (int i = 0; MODIFIER_MAP[i].jsCode != nullptr; i++) {
        if (strcmp(MODIFIER_MAP[i].jsCode, code) == 0) {
            return MODIFIER_MAP[i].mask;
        }
    }
    return 0;
}
