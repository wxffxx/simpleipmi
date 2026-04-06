/**
 * SI BMC — ESP32-S3 USB HID Bridge Firmware
 *
 * Receives commands from ARM host via UART serial protocol,
 * dispatches them to the proven USBHIDManager from esphost.
 *
 * HID layer: usb_hid.cpp / usb_hid.h (tested & working from esphost)
 * Transport: UART binary protocol (protocol.h)
 *
 * Hardware:
 *   - UART0 (GPIO43 RX / GPIO44 TX) ← connected to ARM host
 *   - Native USB (GPIO19 D- / GPIO20 D+) → connected to target machine
 */

#include <Arduino.h>
#include <ArduinoJson.h>
#include "protocol.h"
#include "usb_hid.h"

// ── Frame parser state machine ─────────────────────────────
enum ParseState {
    WAIT_HEAD,
    WAIT_TYPE,
    WAIT_LEN,
    WAIT_PAYLOAD,
    WAIT_CRC
};

static ParseState parse_state = WAIT_HEAD;
static uint8_t frame_type = 0;
static uint8_t frame_len = 0;
static uint8_t frame_payload[PROTO_MAX_PAYLOAD];
static uint8_t frame_idx = 0;

// ── Status LED ─────────────────────────────────────────────
#ifndef LED_BUILTIN
#define LED_BUILTIN 48  // ESP32-S3-DevKitC-1 onboard LED
#endif

static unsigned long led_blink_time = 0;

// ── Send response frame back to host ───────────────────────
void send_response(uint8_t type, const uint8_t *payload, uint8_t len) {
    uint8_t buf[PROTO_MAX_PAYLOAD + PROTO_FRAME_OVERHEAD];
    buf[0] = PROTO_HEAD;
    buf[1] = type;
    buf[2] = len;

    if (len > 0 && payload != nullptr) {
        memcpy(&buf[3], payload, len);
    }

    // CRC over TYPE + LEN + PAYLOAD
    uint8_t crc_data[PROTO_MAX_PAYLOAD + 2];
    crc_data[0] = type;
    crc_data[1] = len;
    if (len > 0) memcpy(&crc_data[2], payload, len);
    buf[3 + len] = crc8_calc(crc_data, 2 + len);

    Serial.write(buf, 3 + len + 1);
    Serial.flush();
}

void send_error(uint8_t error_code) {
    uint8_t payload = error_code;
    send_response(MSG_ERROR, &payload, 1);
}

// ── Process a complete frame ───────────────────────────────
void process_frame() {
    switch (frame_type) {
        case MSG_KEYBOARD_REPORT: {
            if (frame_len != KB_REPORT_SIZE) {
                send_error(ERR_PAYLOAD_TOO_LARGE);
                return;
            }
            // Build a JSON message that USBHIDManager understands
            // frame_payload: [modifier, reserved, key0..key5]
            // Send raw keyboard report via the proven HID stack
            KeyReport report;
            report.modifiers = frame_payload[0];
            report.reserved = 0;
            memcpy(report.keys, &frame_payload[2], 6);

            // Access the keyboard directly (extern from usb_hid.cpp)
            extern USBHIDKeyboard Keyboard;
            Keyboard.sendReport(&report);

            led_blink_time = millis();
            break;
        }

        case MSG_MOUSE_REPORT: {
            if (frame_len != MOUSE_REPORT_SIZE) {
                send_error(ERR_PAYLOAD_TOO_LARGE);
                return;
            }
            // frame_payload: [buttons, xL, xH, yL, yH, scrollY, scrollX]
            // Use relative mouse via USBHIDManager (proven to work)
            uint8_t buttons = frame_payload[0];
            int8_t scrollV = (int8_t)frame_payload[5];
            int8_t scrollH = (int8_t)frame_payload[6];

            // For relative mouse: dx/dy come as scaled values from ARM host
            // In serial bridge mode, ARM host converts absolute to relative deltas
            // But we also support raw button + scroll via the proven Mouse API
            extern USBHIDMouse Mouse;

            // Handle button state changes
            static uint8_t prev_buttons = 0;
            if ((buttons & 0x01) && !(prev_buttons & 0x01)) Mouse.press(MOUSE_LEFT);
            if (!(buttons & 0x01) && (prev_buttons & 0x01)) Mouse.release(MOUSE_LEFT);
            if ((buttons & 0x02) && !(prev_buttons & 0x02)) Mouse.press(MOUSE_RIGHT);
            if (!(buttons & 0x02) && (prev_buttons & 0x02)) Mouse.release(MOUSE_RIGHT);
            if ((buttons & 0x04) && !(prev_buttons & 0x04)) Mouse.press(MOUSE_MIDDLE);
            if (!(buttons & 0x04) && (prev_buttons & 0x04)) Mouse.release(MOUSE_MIDDLE);
            prev_buttons = buttons;

            // Send scroll if any
            if (scrollV != 0 || scrollH != 0) {
                Mouse.move(0, 0, scrollV, scrollH);
            }

            led_blink_time = millis();
            break;
        }

        case MSG_MOUSE_MOVE_REL: {
            // Relative mouse move: [dx_int8, dy_int8]
            if (frame_len != 2) {
                send_error(ERR_PAYLOAD_TOO_LARGE);
                return;
            }
            extern USBHIDMouse Mouse;
            int8_t dx = (int8_t)frame_payload[0];
            int8_t dy = (int8_t)frame_payload[1];
            Mouse.move(dx, dy);

            led_blink_time = millis();
            break;
        }

        case MSG_JSON_HID: {
            // Full JSON passthrough — forward directly to proven USBHIDManager
            // This allows ARM host to send the same WebSocket JSON format that
            // esphost uses, for maximum compatibility
            if (frame_len == 0 || frame_len > PROTO_MAX_PAYLOAD) {
                send_error(ERR_PAYLOAD_TOO_LARGE);
                return;
            }

            // Null-terminate the JSON string
            char json_buf[PROTO_MAX_PAYLOAD + 1];
            memcpy(json_buf, frame_payload, frame_len);
            json_buf[frame_len] = '\0';

            JsonDocument doc;
            DeserializationError err = deserializeJson(doc, json_buf);
            if (err) {
                send_error(ERR_UNKNOWN_TYPE);
                return;
            }

            JsonObject obj = doc.as<JsonObject>();
            usbHID.handleMessage(obj);

            led_blink_time = millis();
            break;
        }

        case MSG_HEARTBEAT: {
            uint8_t status = usbHID.isReady() ? 0x00 : 0x01;
            send_response(MSG_HEARTBEAT_ACK, &status, 1);
            break;
        }

        case MSG_RESET_ALL: {
            usbHID.releaseAllKeys();
            break;
        }

        default:
            send_error(ERR_UNKNOWN_TYPE);
            break;
    }
}

// ── Parse incoming serial bytes ────────────────────────────
void parse_byte(uint8_t b) {
    switch (parse_state) {
        case WAIT_HEAD:
            if (b == PROTO_HEAD) parse_state = WAIT_TYPE;
            break;

        case WAIT_TYPE:
            frame_type = b;
            parse_state = WAIT_LEN;
            break;

        case WAIT_LEN:
            frame_len = b;
            frame_idx = 0;
            if (frame_len > PROTO_MAX_PAYLOAD) {
                send_error(ERR_PAYLOAD_TOO_LARGE);
                parse_state = WAIT_HEAD;
            } else if (frame_len == 0) {
                parse_state = WAIT_CRC;
            } else {
                parse_state = WAIT_PAYLOAD;
            }
            break;

        case WAIT_PAYLOAD:
            frame_payload[frame_idx++] = b;
            if (frame_idx >= frame_len) parse_state = WAIT_CRC;
            break;

        case WAIT_CRC: {
            uint8_t crc_buf[PROTO_MAX_PAYLOAD + 2];
            crc_buf[0] = frame_type;
            crc_buf[1] = frame_len;
            if (frame_len > 0) memcpy(&crc_buf[2], frame_payload, frame_len);
            uint8_t expected = crc8_calc(crc_buf, 2 + frame_len);

            if (b == expected) {
                process_frame();
            } else {
                send_error(ERR_CRC_MISMATCH);
            }
            parse_state = WAIT_HEAD;
            break;
        }
    }
}

// ── Arduino setup ──────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    delay(300);

    Serial.println();
    Serial.println("╔══════════════════════════════════════════╗");
    Serial.println("║  SI BMC — ESP32-S3 HID Bridge v2.0      ║");
    Serial.println("║  UART Protocol + Proven HID Stack        ║");
    Serial.println("╚══════════════════════════════════════════╝");
    Serial.println();

    // Status LED
    pinMode(LED_BUILTIN, OUTPUT);

    // Initialize proven USB HID stack from esphost
    Serial.println("[BOOT] Initializing USB HID (from esphost)...");
    usbHID.begin();
    Serial.printf("[BOOT] HID ready: %s\n", usbHID.isReady() ? "YES" : "NO");

    // Blink LED 3 times to indicate ready
    for (int i = 0; i < 3; i++) {
        digitalWrite(LED_BUILTIN, HIGH);
        delay(100);
        digitalWrite(LED_BUILTIN, LOW);
        delay(100);
    }

    Serial.println("[BOOT] Waiting for UART commands from ARM host...");
}

// ── Arduino loop ───────────────────────────────────────────
void loop() {
    // Process all available serial bytes
    while (Serial.available()) {
        parse_byte(Serial.read());
    }

    // LED activity indicator
    unsigned long now = millis();
    if (led_blink_time > 0 && (now - led_blink_time) < 50) {
        digitalWrite(LED_BUILTIN, HIGH);
    } else {
        // Slow heartbeat blink when idle (1s on, 1s off)
        digitalWrite(LED_BUILTIN, ((now / 1000) % 2 == 0) ? HIGH : LOW);
    }
}
