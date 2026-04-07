# hosts/

KVM Host implementations. Each subdirectory is a self-contained host targeting a specific hardware platform.

## Directory

| Host | Platform | Architecture | Status |
|------|----------|-------------|--------|
| [armhost-cm4](armhost-cm4/) | Raspberry Pi CM4 / compatible | ARM Linux + ESP32-S3 HID bridge | Available |
| [armhost-orangepi4](armhost-orangepi4/) | OrangePi CM4 (RK3566) | ARM Linux + native USB OTG | Available |
| [esphost-esp32s3](esphost-esp32s3/) | ESP32-S3-DevKitC-1 | MCU standalone (WiFi AP / W5500) | Available |
| [stmhost-f103](stmhost-f103/) | STM32F103 (Blue Pill) | MCU, USB Full Speed HID only | WIP |
| [esphost-esp32c3(switch_only)](esphost-esp32c3(switch_only)/) | ESP32-C3 | MCU, power switch only (no HID) | WIP |

## ARM Linux Hosts

`armhost-cm4/` and `armhost-orangepi4/` share a similar structure:

```
armhost-*/
├── server/             # Python (FastAPI) server
│   ├── main.py         #   Application entry point
│   ├── modules/        #   Subsystem modules (video, hid, gpio, auth, terminal)
│   ├── static/         #   Web dashboard (HTML/CSS/JS)
│   ├── config.yaml     #   Runtime configuration
│   └── si_bmc.service  #   systemd unit file
├── firmware/           # ESP32-S3 HID bridge firmware (CM4 only)
│   ├── src/            #   C++ source (main.cpp, usb_hid.cpp)
│   ├── include/        #   Headers (protocol.h, config.h, usb_hid.h)
│   └── platformio.ini  #   PlatformIO build config
└── docs/               # Development guides, topology diagrams
```

Key difference: CM4 uses an external ESP32-S3 as a UART-based HID bridge, while OrangePi uses native USB OTG gadget (`/dev/hidg*`).

## MCU Hosts

`esphost-esp32s3/` is a single-chip solution:

```
esphost-esp32s3/
├── firmware/
│   ├── src/            # C++ source (main, network, usb_hid, gpio_ctrl, web_server)
│   ├── data/           # SPIFFS web assets (HTML/CSS/JS + gzip)
│   ├── platformio.ini  # Build config (ESP32-S3, TinyUSB)
│   └── flash.sh        # One-shot flash script
├── README.md
└── README_zh.md
```
