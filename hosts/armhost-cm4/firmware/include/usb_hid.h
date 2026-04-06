/**
 * SI BMC — USB HID Module Header
 * 
 * 键盘: USBHIDKeyboard (内置), 支持完整 JS event.code → USB HID 键码映射
 * 鼠标: USBHIDMouse (内置, 相对移动模式), 前端发送 dx/dy 增量
 * 
 * 通过 ESP32-S3 原生 USB (TinyUSB) 在 OTG 口 (GPIO19/20) 模拟 HID 设备。
 * 需要 ARDUINO_USB_MODE=0 和 ARDUINO_USB_CDC_ON_BOOT=0。
 */
#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

// ─── USB HID Keyboard Report (8 bytes) ─────────────────────
// [0]   Modifier bitmask (Ctrl, Shift, Alt, Meta)
// [1]   Reserved (0x00)
// [2-7] Up to 6 simultaneous keycodes (6KRO)
//
// ─── USB HID Mouse Report (relative mode) ──────────────────
// 使用内置 USBHIDMouse, 发送相对移动量 (-127 ~ +127)
// 前端 JS 从触摸板计算 dx/dy 后通过 WebSocket 发送

class USBHIDManager {
public:
    void begin();   // 初始化 USB HID (键盘 + 鼠标), 启动 USB 栈
    void end();     // 释放所有按键

    // 处理 WebSocket JSON 消息 (类型: keydown/keyup/mousemove/mousedown/mouseup/wheel/combo/releaseall)
    void handleMessage(JsonObject& msg);

    // ── 键盘 ──
    void keyDown(const char* code);     // code = JS event.code, 如 "KeyA", "Enter"
    void keyUp(const char* code);
    void releaseAllKeys();
    void sendCombo(JsonArray& modifiers, JsonArray& keys);  // 组合键, 如 Ctrl+Alt+Del

    // ── 鼠标 (相对移动) ──
    void mouseMove(float dx, float dy);                    // dx/dy: -1.0 ~ 1.0 的相对偏移
    void mouseDown(float dx, float dy, uint8_t button = 0); // button: 0=左, 1=中, 2=右
    void mouseUp(float dx, float dy, uint8_t button = 0);
    void mouseScroll(float dx, float dy, int8_t deltaY, int8_t deltaX = 0);

    bool isReady() const { return _ready; }

private:
    bool _ready = false;
    uint8_t _modifierState = 0;        // 当前修饰键状态 bitmask
    uint8_t _pressedKeys[6] = {0};     // 当前按下的键码 (6KRO)
    uint8_t _pressedKeyCount = 0;
    uint8_t _mouseButtons = 0;         // 当前鼠标按钮状态

    void _sendKeyboardReport();
    void _sendMouseReport(uint16_t absX, uint16_t absY, int8_t scrollY = 0, int8_t scrollX = 0);
    uint8_t _jsCodeToHID(const char* code);       // JS code → USB HID keycode
    uint8_t _jsCodeToModifier(const char* code);   // JS code → modifier bitmask
};

extern USBHIDManager usbHID;  // 全局单例
