# SI BMC — SimpleIPMI Baseboard Management Controller

**[中文文档](README_CN.md)**

An open-source, low-cost KVM-over-IP solution. Remotely control physical machines — keyboard, mouse, video, and power — through a web browser, similar to commercial IPMI/BMC systems.

Supports multiple hardware platforms, from a $5 ESP32-S3 dev board to CM4-class ARM Linux SBCs, covering both single-machine and multi-host management scenarios.

## Features

- **Remote Video** — HDMI capture via USB or CSI, streamed as MJPEG
- **Remote Keyboard & Mouse** — USB HID emulation
- **Power Control** — Optocoupler/relay-isolated power, reset, and force-off
- **Web Dashboard** — Browser-based control panel, zero client installation
- **Flexible Networking** — WiFi AP direct connect, Ethernet LAN, or Tailscale overlay

## Architecture

```
                        ┌──────────────────────────────────┐
    User (Browser) ────→│         Web Dashboard             │
                        │   Video │ HID Input │ Power Ctrl  │
                        └────┬─────┴────┬─────┴────┬────────┘
                             │          │          │
                      ┌──────┴──────────┴──────────┴──────┐
                      │           KVM Host                 │
                      │  ESP32-S3 / CM4 / OrangePi / ...   │
                      └──┬──────────┬──────────┬──────────┘
                         │          │          │
                   USB Capture   USB HID    GPIO Relay
                   (HDMI input) (KB+Mouse)  (Power Ctrl)
                         │          │          │
                         └──────────┴──────────┘
                             Target Machine
```

## Repository Structure

```
simpleipmi/
├── hosts/                            # KVM host firmware & software
│   ├── esphost-esp32s3/              #   ESP32-S3 standalone (WiFi AP + HID)
│   ├── armhost-cm4/                  #   CM4 ARM Linux (Ethernet + HID Bridge)
│   ├── armhost-orangepi4/            #   OrangePi CM4 (USB OTG HID)
│   ├── stmhost-f103/                 #   STM32F103 ultra-low-cost (WIP)
│   └── esphost-esp32c3(switch_only)/ #   ESP32-C3 power-switch only (WIP)
│
├── hardware/                         # PCB / schematic / BOM design files
│   ├── km/                           #   Keyboard-Mouse HID modules
│   ├── kvm-carrier/                  #   KVM carrier boards
│   ├── coreboard/                    #   SoC core modules
│   └── accessories/                  #   Video capture, relay, etc.
│
├── composite/                        # Multi-host management system (WIP)
│   └── server/
│
├── shared/                           # Cross-device shared resources
│   └── protocol/                     #   Communication protocol (protocol.h)
│
└── docs/                             # Documentation & manuals
```

## Host Platform Comparison

| | ESP32-S3 | ARM CM4 | OrangePi CM4 | STM32F103 |
|---|---|---|---|---|
| **Cost** | ~$5 | ~$30 | ~$20 | ~$2 |
| **Video Capture** | External only | USB capture card | USB capture card | None |
| **HID** | Native USB OTG | ESP32-S3 serial bridge | Native USB OTG | Native USB |
| **Networking** | WiFi AP | Ethernet / WiFi | Ethernet / WiFi | External |
| **Web Panel** | Built-in (SPIFFS) | FastAPI server | FastAPI server | None |
| **Use Case** | Simple single-host | Full-featured remote KVM | Full-featured remote KVM | Ultra-low-cost HID |
| **Status** | Ready | Ready | Ready | WIP |

## Quick Start

### Option 1: ESP32-S3 (Simplest)

**Requirements:** ESP32-S3-DevKitC-1, jumper wires, optocoupler module

```bash
# Install PlatformIO
pip install platformio

# Build and flash firmware
cd hosts/esphost-esp32s3/firmware
pio run -t upload

# Upload web UI (SPIFFS)
pio run -t uploadfs

# Connect to WiFi AP "SI-BMC-XXXX", open http://192.168.4.1
```

See [hosts/esphost-esp32s3/README.md](hosts/esphost-esp32s3/README.md)

### Option 2: ARM CM4 (Full-Featured)

**Requirements:** CM4-compatible SBC, ESP32-S3 (HID bridge), USB capture card

```bash
# Deploy server on CM4
cd hosts/armhost-cm4/server
pip install -r requirements.txt
python main.py

# Flash ESP32-S3 HID bridge firmware
cd hosts/armhost-cm4/firmware
pio run -t upload
```

See [hosts/armhost-cm4/docs/DEVELOPMENT.md](hosts/armhost-cm4/docs/DEVELOPMENT.md)

## Hardware Designs

All PCB and schematic files are under `hardware/`, organized by function:

| Category | Description |
|----------|-------------|
| `km/` | Keyboard-mouse HID modules (ESP32-S2, XIAO-ESP32S3, STM32F103) |
| `kvm-carrier/` | KVM carrier boards (PCIe CM4 v1/v2, T113) |
| `coreboard/` | SoC core modules (H616, ARM Linux full-module) |
| `accessories/` | HDMI capture (Toshiba TC358743, MS2109), relay module |

See [hardware/README.md](hardware/README.md)

## Roadmap

- [x] ESP32-S3 standalone KVM host
- [x] CM4 ARM Linux KVM host + ESP32-S3 HID bridge
- [x] OrangePi CM4 KVM host (USB OTG)
- [x] Web dashboard (KVM view, terminal, system info)
- [ ] STM32F103 low-cost HID host
- [ ] Composite multi-host management system
- [ ] H616 coreboard completion

## License

MIT
