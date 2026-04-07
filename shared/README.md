# shared/

Cross-device shared resources used by multiple hosts.

## Contents

### protocol/

Communication protocol definitions shared between ARM Linux hosts and ESP32-S3 HID bridges.

- `protocol.h` -- Binary serial protocol for UART HID commands (keyboard reports, mouse reports, heartbeat). Defines packet structure, message types, and CRC8 checksum. Used by both the ESP32-S3 firmware (`hosts/armhost-cm4/firmware/`) and the Python server (`hosts/armhost-cm4/server/modules/hid.py`).

Packet format:
```
[HEAD 0xAA] [TYPE 1B] [LENGTH 1B] [PAYLOAD ...] [CRC8 1B]
```
