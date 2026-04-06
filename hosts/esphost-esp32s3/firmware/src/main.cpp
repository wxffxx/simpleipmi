/**
 * ============================================================
 * SI BMC — Main Entry Point
 * ESP32-S3 Lite Baseboard Management Controller
 * 
 * 硬件: ESP32-S3-DevKitC-1 (N8R2/N8R8)
 * 
 * Boot sequence:
 *   1. UART0 串口初始化 (调试输出, GPIO43/44)
 *   2. GPIO 初始化 (电源/复位光耦 + 状态LED)
 *   3. USB HID 初始化 (键盘 + 相对鼠标, OTG口 GPIO19/20)
 *   4. WiFi AP 启动 (SI-BMC, 192.168.4.1)
 *   5. Web 服务器 + WebSocket 启动
 *   6. 主循环 (网络维护 + GPIO更新 + 电源状态轮询)
 * 
 * USB 配置: ARDUINO_USB_MODE=0 (原生USB/TinyUSB)
 *          ARDUINO_USB_CDC_ON_BOOT=0 (USB不做串口)
 * ============================================================
 */

#include <Arduino.h>
#include "config.h"
#include "usb_hid.h"
#include "gpio_ctrl.h"
#include "network.h"
#include "web_server.h"

// ─── State ────────────────────────────────────────────────
static uint32_t lastStatusPoll = 0;
static bool lastPowerState = false;
static bool networkReady = false;

void setup() {
    // 1. Serial debug (via UART0, external USB-UART adapter)
    Serial.begin(SERIAL_BAUD);
    delay(500);
    
    Serial.println();
    Serial.println("╔══════════════════════════════════════════╗");
    Serial.println("║    SI BMC — ESP32-S3 Lite Controller     ║");
    Serial.printf( "║    Firmware v%s                        ║\n", BMC_VERSION);
    Serial.println("╚══════════════════════════════════════════╝");
    Serial.println();

    // 2. GPIO setup
    Serial.println("[BOOT] Initializing GPIO...");
    gpioCtrl.begin();
    gpioCtrl.blinkStatusLED(200);  // Fast blink = booting
    
    // 3. USB HID init (native USB mode on OTG port)
    Serial.println("[BOOT] Initializing USB HID...");
    usbHID.begin();
    
    // 4. WiFi AP Network
    Serial.println("[BOOT] Starting WiFi AP...");
    networkReady = network.begin();
    
    if (networkReady) {
        Serial.println("[BOOT] Network ready!");
        gpioCtrl.blinkStatusLED(1000);  // Slow blink = running
        
        // 5. Web server
        Serial.println("[BOOT] Starting web server...");
        webServer.begin();
        
        // Log boot info
        char msg[128];
        snprintf(msg, sizeof(msg), "系统启动完成 | IP: %s", network.getIPAddress().c_str());
        webServer.addLog(msg);
        webServer.addLog(usbHID.isReady() ? "USB HID 就绪" : "USB HID 未连接", 
                         usbHID.isReady() ? "INFO" : "WARNING");
        
        Serial.println();
        Serial.println("═══════════════════════════════════════");
        Serial.printf("  BMC Ready! Open http://%s\n", network.getIPAddress().c_str());
        Serial.println("═══════════════════════════════════════");
        Serial.println();
    } else {
        Serial.println("[BOOT] Network failed! Retrying in loop...");
        gpioCtrl.blinkStatusLED(100);  // Very fast blink = error
    }
}

void loop() {
    // Retry network if it failed during boot
    if (!networkReady) {
        static uint32_t lastRetry = 0;
        if (millis() - lastRetry > 5000) {
            lastRetry = millis();
            Serial.println("[NET] Retrying network init...");
            networkReady = network.begin();
            if (networkReady) {
                gpioCtrl.blinkStatusLED(1000);
                webServer.begin();
                char msg[128];
                snprintf(msg, sizeof(msg), "网络重连成功 | IP: %s", network.getIPAddress().c_str());
                webServer.addLog(msg);
            }
        }
    }
    
    // Maintain network (DHCP lease, link check)
    network.update();
    
    // Update GPIO (non-blocking pulse handler + LED blink)
    gpioCtrl.update();
    
    // Periodic power status check
    if (millis() - lastStatusPoll >= STATUS_POLL_INTERVAL) {
        lastStatusPoll = millis();
        bool powered = gpioCtrl.isPowered();
        if (powered != lastPowerState) {
            lastPowerState = powered;
            Serial.printf("[STATUS] Target machine power: %s\n", powered ? "ON" : "OFF");
            webServer.addLog(powered ? "目标主机已开机" : "目标主机已关机",
                           powered ? "INFO" : "WARNING");
        }
    }
    
    // Small yield to prevent watchdog
    delay(1);
}
