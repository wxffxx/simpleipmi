# SI BMC — ESP32-S3 Lite Baseboard Management Controller

A lightweight remote management controller based on the ESP32-S3-DevKitC-1 development board.
It provides a web-based management interface via WiFi hotspot and emulates USB HID keyboard/mouse
through the native USB (OTG) interface to control a target host machine.

## Features

- **Web Dashboard** — View system status, power control, live logs
- **USB HID Keyboard** — Capture keyboard input from the web page and send it to the target host
- **USB HID Mouse** — Trackpad-style relative mouse control
- **Remote Power Control** — Optocoupler-isolated power/reset button control for the target host
- **WiFi AP Mode** — Direct connection, no router required

## Hardware Requirements

| Component | Description |
|-----------|-------------|
| **Board** | ESP32-S3-DevKitC-1 (N8R2/N8R8) |
| **OTG USB** | GPIO19(D-) / GPIO20(D+) — connects to target host USB port |
| **UART0** | GPIO43(TX) / GPIO44(RX) — optional debug serial |
| **Power Button** | GPIO4 — optocoupler — target host PWR_BTN |
| **Reset Button** | GPIO5 — optocoupler — target host RST_BTN |
| **Power Status** | GPIO6 — target host PWR_LED (detect power state) |
| **Status LED** | GPIO48 (onboard) |

### USB Port Layout

The development board has two USB ports:

```
+----------------------------------+
|  ESP32-S3-DevKitC-1              |
|                                  |
|  [USB]  <- OTG (GPIO19/20)      |  -> Connect to TARGET HOST
|  [COM]  <- USB-JTAG/Serial      |  -> Connect to DEV PC (flash/debug only)
|                                  |
+----------------------------------+
```

## Quick Start

### 1. Prerequisites

```bash
pip install platformio
cd SI_server/esp32s3_bmc
```

### 2. Flash Firmware

Enter download mode: **Hold BOOT, press RST, release BOOT**

```bash
# One-shot: build + flash firmware + SPIFFS
./flash.sh all

# Or step by step:
pio run                          # Build firmware
pio run --target buildfs         # Build SPIFFS filesystem

# Flash via esptool (through OTG port)
esptool --chip esp32s3 --port /dev/cu.usbmodem21201 \
  --baud 460800 write-flash \
  --flash-mode dio --flash-size 8MB \
  0x10000 .pio/build/esp32s3/firmware.bin \
  0x670000 .pio/build/esp32s3/spiffs.bin
```

Press **RST** after flashing to reboot.

### 3. Connect

1. Connect the OTG USB port to the target host
2. Join WiFi: **`SI-BMC`** (password: `12345678`)
3. Open browser: **`http://192.168.4.1`**
4. Login password: `admin`

## Project Structure

```
esp32s3_bmc/
├── platformio.ini          # PlatformIO build configuration
├── flash.sh                # One-shot build & flash script
├── README.md               # This file (English)
├── README_CN.md            # Chinese version
├── src/
│   ├── config.h            # Global config (pins, WiFi, auth)
│   ├── main.cpp            # Entry point: boot sequence + main loop
│   ├── usb_hid.h/cpp       # USB HID keyboard + mouse driver
│   ├── gpio_ctrl.h/cpp     # GPIO control (power/reset/status LED)
│   ├── network.h/cpp       # WiFi AP network management
│   └── web_server.h/cpp    # Web server + WebSocket + REST API
├── data/                   # SPIFFS static assets (Web UI)
│   ├── index.html(.gz)     # Dashboard page
│   ├── hid.html(.gz)       # HID keyboard/mouse control page
│   ├── css/                # Stylesheets
│   └── js/                 # Frontend logic
│       ├── app.js          # Common (auth, toast, API)
│       └── hid.js          # HID control (WebSocket + trackpad + keyboard)
```

## Module Overview

### USB HID (`usb_hid.h/cpp`)

Uses ESP32-S3 native USB (TinyUSB) to emulate a composite HID device:

- **Keyboard**: Built-in `USBHIDKeyboard` class with full JavaScript `event.code` to USB HID keycode mapping
- **Mouse**: Built-in `USBHIDMouse` class (relative movement mode); the frontend trackpad sends `dx/dy` deltas

> Note: Absolute mouse mode (custom HID descriptor) conflicts with the keyboard composite device
> in the current ESP32 Arduino version, so relative mouse mode is used instead.

### Web Server (`web_server.h/cpp`)

Based on ESPAsyncWebServer:

- **Static Assets**: Serves gzip-compressed HTML/CSS/JS from SPIFFS
- **REST API**: `/api/status`, `/api/power`, `/api/reset`, `/api/led`
- **WebSocket**: `/ws/hid` — receives keyboard/mouse commands in real time

### Network (`network.h/cpp`)

WiFi AP mode:

- SSID: `SI-BMC`, Password: `12345678` (configurable in `config.h`)
- IP: `192.168.4.1`
- No external router needed

## Key Configuration

Edit `src/config.h`:

| Setting | Default | Description |
|---------|---------|-------------|
| `AP_SSID` | `"SI-BMC"` | WiFi hotspot name |
| `AP_PASSWORD` | `"12345678"` | WiFi password |
| `AUTH_PASSWORD` | `"admin"` | Web login password |
| `PIN_PWR_BTN` | `4` | Power button GPIO |
| `PIN_RST_BTN` | `5` | Reset button GPIO |
| `PIN_PWR_LED` | `6` | Power status detect GPIO |

## Build Flags

```ini
build_flags =
    -DARDUINO_USB_MODE=0          # Native USB (not JTAG), enables HID
    -DARDUINO_USB_CDC_ON_BOOT=0   # USB port is NOT used for serial output
    -DBOARD_HAS_PSRAM=0           # Disable PSRAM (saves boot time)
```

> Note: With `USB_MODE=0`, serial output goes to UART0 (GPIO43/44), not the USB port.
> An external USB-TTL adapter is required for debug logging.

## Development Notes

1. **Flashing**: Must flash through the COM port (USB-JTAG) in download mode; OTG port is for HID output only
2. **Frontend changes**: After modifying files under `data/`, re-gzip and run `buildfs`
3. **Reboot**: Manual RST press required after flashing, or auto-reset via COM port RTS signal

## License

Internal project — SI Server Team
