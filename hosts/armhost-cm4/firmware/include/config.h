/**
 * SI BMC — HID Bridge Config
 * Minimal config.h for the UART HID bridge firmware.
 * (Full esphost config.h has WiFi/GPIO/W5500 which we don't need here)
 */
#pragma once

// ─── Firmware Info ─────────────────────────────────────────
#define BMC_VERSION       "2.0.0"

// ─── USB HID Pins ─────────────────────────────────────────
// Fixed on ESP32-S3, do NOT change.
#define PIN_USB_DP        20    // USB D+
#define PIN_USB_DN        19    // USB D-

// ─── 鼠标配置 ────────────────────────────────────────────
#define MOUSE_ABS_MAX    32767  // 保留, 供未来绝对鼠标模式使用

// ─── 调试配置 ─────────────────────────────────────────────
#define SERIAL_BAUD      115200
#define DEBUG_ENABLED    true
