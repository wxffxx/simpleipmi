# SimpleIPMI

**[中文文档](README_zh.md)** 

An [RCOS](https://rcos.io) Project

Open-source, low-cost KVM-over-IP solution. Remotely control physical machines — keyboard, mouse, video, and power — through a web browser, similar to commercial IPMI/BMC systems.

## Features

- **Remote Video** — HDMI capture via USB or CSI, streamed as MJPEG
- **Remote Keyboard & Mouse** — USB HID emulation
- **Power Control** — Optocoupler/relay-isolated power, reset, and force-off
- **Web Dashboard** — Browser-based control panel, zero client installation
- **Flexible Networking** — WiFi AP direct connect, Ethernet LAN, or Tailscale overlay

## Architecture

The project supports three distinct host architectures:

### ARM Linux Host (Available)

Full-featured KVM solution based on ARM Linux SBCs (CM4, OrangePi). The SBC runs a Python (FastAPI) server, captures video via USB capture card, and controls the target machine's keyboard/mouse through an ESP32-S3 HID bridge or native USB OTG.

```
User (Browser)
     │
     ▼
┌──────────────────────────┐
│  ARM Linux SBC           │
│  FastAPI Server           │
│  ┌────────┐ ┌──────────┐ │
│  │ Video  │ │ HID Mgr  │ │
│  │(USB Cap)│ │(ESP32/OTG)│ │
│  └────┬───┘ └────┬─────┘ │
└───────┼──────────┼────────┘
        │          │
   HDMI-in    USB HID out ──→ Target Machine
```

### MCU Host (WIP)

Lightweight standalone solution based on ESP32-S3 or STM32. The MCU handles WiFi AP, web server (SPIFFS), and USB HID natively. No Linux, no capture card — minimal cost, single-host only.

### Composite Host (WIP)

Central management server running on Ubuntu (x86/ARM). Manages multiple KVM hosts and USB capture cards simultaneously, providing a unified web panel for multi-target-machine control.

## Repository Structure

```
simpleipmi/
├── hosts/                            # KVM host firmware & software
│   ├── esphost-esp32s3/              #   ESP32-S3 MCU host (WiFi AP + HID)
│   ├── armhost-cm4/                  #   CM4 ARM Linux host (Ethernet + HID Bridge)
│   ├── armhost-orangepi4/            #   OrangePi CM4 host (USB OTG HID)
│   ├── stmhost-f103/                 #   STM32F103 MCU host (WIP)
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

| | ARM CM4 | OrangePi CM4 | ESP32-S3 | STM32F103 |
|---|---|---|---|---|
| **Architecture** | ARM Linux | ARM Linux | MCU | MCU |
| **Cost** | TBD | TBD | TBD | TBD |
| **Video Capture** | USB capture card | USB capture card | External only | None |
| **HID** | ESP32-S3 serial bridge | Native USB OTG | Native USB OTG | Native USB |
| **Networking** | Ethernet / WiFi | Ethernet / WiFi | WiFi AP | External |
| **Web Panel** | FastAPI server | FastAPI server | Built-in (SPIFFS) | None |
| **Status** | Available | Available | WIP | WIP |

## Quick Start

### ARM CM4 Host

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

**Completed**
- ARM CM4 KVM host with ESP32-S3 HID bridge
- OrangePi CM4 KVM host with native USB OTG
- Web dashboard (KVM view, terminal, system info)

**TODO**
- ESP32-S3 standalone MCU host
- STM32F103 low-cost MCU host
- Composite multi-host management system
- H616 coreboard completion

## About RCOS

This project is developed under the [Rensselaer Center for Open Source](https://rcos.io) (RCOS), an organization at Rensselaer Polytechnic Institute that supports student-driven open source software serving the greater good.

## License

MIT
