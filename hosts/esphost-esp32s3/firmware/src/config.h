/**
 * ============================================================
 * SI BMC — 全局配置文件
 * ESP32-S3 Lite Baseboard Management Controller
 * 
 * !! 烧录前请根据实际硬件修改以下配置值 !!
 * 
 * 主要配置项:
 *   - WiFi AP: SSID / 密码
 *   - 认证: Web 登录密码
 *   - GPIO: 电源/复位按钮引脚
 *   - 时序: 按键脉冲时长
 * ============================================================
 */
#pragma once

// ─── Firmware Info ─────────────────────────────────────────
#define BMC_VERSION       "1.0.0"
#define BMC_HOSTNAME      "si-bmc"

// ─── Network Mode ─────────────────────────────────────────
// WiFi AP Mode — ESP32 creates its own hotspot
#define AP_SSID           "SI-BMC"
#define AP_PASSWORD       "12345678"

// ─── Network Configuration ────────────────────────────────
// Set to true for DHCP (default), false for static IP
#define NET_USE_DHCP      true

// Static IP settings (only used when NET_USE_DHCP = false)
#define NET_STATIC_IP     192, 168, 1, 100
#define NET_GATEWAY       192, 168, 1, 1
#define NET_SUBNET        255, 255, 255, 0
#define NET_DNS            8, 8, 8, 8

// Web server port
#define WEB_SERVER_PORT   80

// ─── Authentication ───────────────────────────────────────
// Simple password protection for power control operations.
// Leave AUTH_PASSWORD empty ("") to disable authentication.
#define AUTH_PASSWORD      "admin"

// ─── W5500 SPI Pins ───────────────────────────────────────
// Using SPI2 (HSPI) — adjust if your PCB routes differently
#define PIN_W5500_MOSI    11
#define PIN_W5500_MISO    13
#define PIN_W5500_SCLK    12
#define PIN_W5500_CS      10
#define PIN_W5500_RST     9
#define PIN_W5500_INT     8     // Optional, set to -1 to disable

// SPI clock speed for W5500 (Hz). Lower if you have long wires.
#define W5500_SPI_FREQ    20000000  // 20 MHz

// ─── USB HID Pins ─────────────────────────────────────────
// These are FIXED on ESP32-S3, do NOT change.
#define PIN_USB_DP        20    // USB D+
#define PIN_USB_DN        19    // USB D-

// ─── Optocoupler / Relay GPIO ─────────────────────────────
// Active HIGH: GPIO goes HIGH → optocoupler triggers → 
//   shorts the target motherboard's button pins
#define PIN_PWR_BTN       4     // Parallel to target Power Button
#define PIN_RST_BTN       5     // Parallel to target Reset Button

// Set to true if your optocoupler circuit is active-low
#define PWR_ACTIVE_LOW    false
#define RST_ACTIVE_LOW    false

// ─── Power Status Detection ──────────────────────────────
// Read target machine's power LED to determine if it's on.
// Connect via voltage divider if LED voltage > 3.3V
#define PIN_PWR_LED       6     // Input: target power LED detect
#define PWR_LED_ACTIVE_LOW false // false = HIGH means powered on

// ─── Status LED ───────────────────────────────────────────
#define PIN_STATUS_LED    48    // Onboard LED (ESP32-S3-DevKitC)

// ─── Timing Parameters (milliseconds) ────────────────────
#define POWER_SHORT_PRESS_MS   500    // Short press = power on
#define POWER_LONG_PRESS_MS    5000   // Long press = force shutdown
#define RESET_PULSE_MS         200    // Reset pulse duration
#define STATUS_POLL_INTERVAL   1000   // How often to check power LED
#define WS_HEARTBEAT_INTERVAL  5000   // WebSocket ping interval

// ─── 鼠标配置 ────────────────────────────────────────────
// 当前使用相对鼠标模式 (USBHIDMouse)
// 绝对鼠标描述符与键盘复合设备在当前 Arduino ESP32 版本有冲突
#define MOUSE_ABS_MAX    32767  // 保留, 供未来绝对鼠标模式使用

// ─── 调试配置 ─────────────────────────────────────────────
// 注意: USB_MODE=0 后串口输出走 UART0 (GPIO43/44), 不走 USB 口
// 需要外接 USB-TTL 适配器才能看到串口日志
#define SERIAL_BAUD      115200
#define DEBUG_ENABLED    true
