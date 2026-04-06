/**
 * SI BMC — Serial HID Bridge Protocol
 * Shared protocol definitions between ARM host and ESP32-S3.
 *
 * Frame format:
 *   [HEAD 0xAA] [TYPE 1B] [LEN 1B] [PAYLOAD 0-255B] [CRC8 1B]
 */

#ifndef SI_BMC_PROTOCOL_H
#define SI_BMC_PROTOCOL_H

#include <stdint.h>

// ── Frame constants ────────────────────────────────────────────
#define PROTO_HEAD              0xAA
#define PROTO_MAX_PAYLOAD       255
#define PROTO_FRAME_OVERHEAD    4       // HEAD + TYPE + LEN + CRC8

// ── Message types: Host → ESP32 ────────────────────────────────
#define MSG_KEYBOARD_REPORT     0x01    // 8 bytes: standard HID keyboard report
#define MSG_MOUSE_REPORT        0x02    // 7 bytes: absolute mouse report
#define MSG_HEARTBEAT           0x03    // 0 bytes: ping
#define MSG_RESET_ALL           0x04    // 0 bytes: release all keys/buttons
#define MSG_MOUSE_MOVE_REL      0x05    // 2 bytes: [dx_int8, dy_int8] relative mouse
#define MSG_JSON_HID            0x10    // N bytes: raw JSON string for USBHIDManager

// ── Message types: ESP32 → Host ────────────────────────────────
#define MSG_HEARTBEAT_ACK       0x83    // 1 byte: status (0=OK, 1=USB disconnected)
#define MSG_ERROR               0xFE    // 1 byte: error code

// ── Error codes ────────────────────────────────────────────────
#define ERR_CRC_MISMATCH        0x01
#define ERR_UNKNOWN_TYPE        0x02
#define ERR_USB_NOT_READY       0x03
#define ERR_PAYLOAD_TOO_LARGE   0x04

// ── Keyboard report layout (8 bytes) ──────────────────────────
// [0] modifier bitmask
// [1] reserved (0x00)
// [2-7] up to 6 keycodes
#define KB_REPORT_SIZE          8

// ── Mouse report layout (7 bytes) ─────────────────────────────
// [0] button bitmask (bit0=left, bit1=right, bit2=middle)
// [1-2] X absolute (uint16 LE, 0-32767)
// [3-4] Y absolute (uint16 LE, 0-32767)
// [5] vertical scroll (int8)
// [6] horizontal scroll (int8)
#define MOUSE_REPORT_SIZE       7
#define MOUSE_ABS_MAX           32767

// ── CRC8 (polynomial 0x07, init 0x00) ─────────────────────────
static inline uint8_t crc8_calc(const uint8_t *data, uint8_t len) {
    uint8_t crc = 0x00;
    for (uint8_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (uint8_t bit = 0; bit < 8; bit++) {
            if (crc & 0x80)
                crc = (crc << 1) ^ 0x07;
            else
                crc <<= 1;
        }
    }
    return crc;
}

#endif // SI_BMC_PROTOCOL_H
