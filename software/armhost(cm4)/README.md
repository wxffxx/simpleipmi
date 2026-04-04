# SI BMC Server

**Baseboard Management Controller / IP-KVM based on Orange Pi CM4 (RK3566)**

> Remotely control a target machine via web browser — video capture, keyboard/mouse emulation, and power management. No software installation required on the target.

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Hardware Requirements](#-hardware-requirements)
- [Wiring Guide](#-wiring-guide)
- [Software Prerequisites](#-software-prerequisites)
- [Getting Started](#-getting-started)
- [Configuration](#-configuration)
- [Usage Guide](#-usage-guide)
- [API Reference](#-api-reference)
- [Troubleshooting](#-troubleshooting)
- [Project Structure](#-project-structure)
- [Extending the Project](#-extending-the-project)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🖥 **Remote Video** | Captures HDMI signal from target via MS2109 USB capture card, real-time MJPEG streaming to browser |
| ⌨️ **Keyboard Emulation** | USB OTG emulates a standard USB keyboard — all keys, modifiers, and combos |
| 🖱 **Mouse Emulation** | USB OTG emulates an absolute-positioning USB mouse — click anywhere on the target screen |
| ⚡ **Power Control** | GPIO-driven power on (short press), force power off (5s long press), hard reset |
| 🔋 **Power Detection** | Real-time 12V power status via PCIe voltage divider circuit |
| 📊 **Dashboard** | Modern dark-themed dashboard with real-time CPU, memory, temperature, disk, and network stats |
| ⌨️ **Virtual Keyboard** | Full on-screen QWERTY keyboard with function keys — works on touch devices |
| 🔑 **Quick Combos** | One-click Ctrl+Alt+Del, Alt+Tab, Alt+F4, and more |
| 🔐 **Authentication** | Optional JWT token-based API protection |
| 📱 **Responsive** | Works on desktop and mobile browsers |

---

## 🏗 Architecture

```
┌───────────────────────────────────────────────────────────┐
│                    Client Browser                         │
│  ┌───────────────────┐  ┌──────────────────────────────┐  │
│  │   Dashboard Panel  │  │   KVM Remote Desktop         │  │
│  │  · System Monitor  │  │  · MJPEG Video Stream        │  │
│  │  · Power Control   │  │  · Click-through Mouse       │  │
│  │  · Device Status   │  │  · Physical Keyboard Capture  │  │
│  │  · GPIO Manager    │  │  · Virtual On-screen Keyboard │  │
│  │  · Activity Logs   │  │  · Combo Key Panel           │  │
│  └───────────────────┘  └──────────────────────────────┘  │
│            │ HTTP / WebSocket                              │
└────────────┼──────────────────────────────────────────────┘
             │
    ┌────────┴─────────┐
    │  FastAPI Server   │ ← Orange Pi CM4 (RK3566)
    │     :8080         │
    ├───────────────────┤
    │ Video: V4L2/MJPEG │ ← MS2109 USB Capture ← HDMI ← Target
    │ HID:   ConfigFS   │ ← USB OTG Cable → Target USB Port
    │ GPIO:  sysfs      │ ← Jumper Wires → ATX Power/Reset Pins
    └───────────────────┘
```

---

## 🔧 Hardware Requirements

### Required

| Device | Model / Spec | Purpose |
|--------|-------------|---------|
| SBC | **Orange Pi CM4** (RK3566) | Core board + base board |
| Video Capture | **MS2109** chipset USB capture card | HDMI input, USB 2.0 output |
| USB OTG Cable | USB-A or Type-C data cable | Connect CM4 OTG port to target |
| HDMI Cable | Standard HDMI cable | Target HDMI → Capture card |
| Jumper Wires | Female-to-female × 5 | GPIO → Target ATX header pins |
| Storage | TF card or eMMC ≥ 16GB | Linux OS |
| Power Supply | Type-C 5V/3A | CM4 power |

### Optional

| Device | Purpose |
|--------|---------|
| Voltage Divider Resistors | 12V → 3.3V detection circuit (PCIe 12V) |
| Optocoupler Module | GPIO isolation from ATX pins (recommended for production) |

---

## 🔌 Wiring Guide

### GPIO Pin Definitions

| Function | GPIO Name | Linux GPIO # | Direction | Physical Connection |
|----------|-----------|-------------|-----------|---------------------|
| **Power Control** (PWR) | GPIO4_A6 | 134 | Output | → Target ATX `Power SW+` |
| **Reset Control** (RST) | GPIO1_A1 | 33 | Output | → Target ATX `Reset SW+` |
| **12V Detection** | GPIO4_C0 | 144 | Input | ← PCIe 12V voltage divider output |

> **GPIO Number Formula**: `bank × 32 + group × 8 + pin`
> - GPIO4_A6 = 4×32 + 0×8 + 6 = **134**
> - GPIO1_A1 = 1×32 + 0×8 + 1 = **33**
> - GPIO4_C0 = 4×32 + 2×8 + 0 = **144**

### ATX Power Wiring Diagram

```
Orange Pi CM4                         Target Machine ATX Header
──────────────                        ──────────────────────────
GPIO4_A6 (Pin ?) ────────────────── Power SW+  (Power toggle)
GND              ────────────────── Power SW-  (Power ground)

GPIO1_A1 (Pin ?) ────────────────── Reset SW+  (Reset trigger)
GND              ────────────────── Reset SW-  (Reset ground)

GPIO4_C0 (Pin ?) ←── Divider ←───── PCIe 12V   (Power detect)
GND              ────────────────── PCIe GND
```

### 12V Voltage Divider Circuit

```
PCIe 12V ───┬─── [10kΩ] ───┬─── GPIO4_C0 (3.3V safe input)
             │               │
             └─── [3.3kΩ] ──┴─── GND

Output Voltage = 12V × 3.3k / (10k + 3.3k) ≈ 2.98V (within safe range)
```

### USB Connections

```
Target Machine                 Orange Pi CM4
──────────────                 ──────────────
HDMI Output ──── HDMI Cable ──── MS2109 Capture Card (USB → CM4 USB HOST)
USB Port    ──── USB Cable  ──── CM4 USB OTG Port (emulates keyboard+mouse)
```

---

## 📦 Software Prerequisites

### Orange Pi CM4 System Requirements

- **Operating System**: Ubuntu 20.04/22.04 or Debian 11/12 (Ubuntu 22.04 Server recommended)
- **Python**: 3.8+
- **Kernel Requirements**:
  - `CONFIG_USB_CONFIGFS=y` (USB ConfigFS support)
  - `CONFIG_USB_CONFIGFS_F_HID=y` (HID gadget function)
  - `CONFIG_USB_GADGET=y`
  - UVC camera support (MS2109 is a standard UVC device)

---

## 🚀 Getting Started

### Method 1: Automated Install (Recommended)

```bash
# 1. Transfer project files to Orange Pi CM4
scp -r SI_server/ orangepi@<CM4_IP>:~/

# 2. SSH into the CM4
ssh orangepi@<CM4_IP>

# 3. Run the installation script
cd ~/SI_server
sudo bash scripts/install.sh

# 4. Start the service
sudo systemctl start si_bmc

# 5. Open in browser
# http://<CM4_IP>:8080
```

### Method 2: Manual Install

```bash
# ── Step 1: Install system dependencies ──────────────────────
sudo apt update
sudo apt install -y python3 python3-pip v4l-utils libgpiod-dev gpiod

# ── Step 2: Install Python dependencies ─────────────────────
cd ~/SI_server
pip3 install -r requirements.txt

# ── Step 3: Initialize USB HID Gadget ────────────────────────
#    (Must run as root — makes CM4 appear as USB keyboard + mouse)
sudo bash setup_gadget.sh setup

# Verify HID devices were created:
ls -la /dev/hidg*
# Expected: /dev/hidg0 (keyboard) and /dev/hidg1 (mouse)

# ── Step 4: Start the server ─────────────────────────────────
sudo python3 main.py

# Or run in background:
sudo python3 main.py &

# ── Step 5: Enable auto-start on boot (optional) ────────────
sudo cp si_bmc.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable si_bmc
sudo systemctl start si_bmc
```

### Verify Installation

```bash
# Check service status
sudo systemctl status si_bmc

# Check USB Gadget status
sudo bash setup_gadget.sh status

# Check video device
v4l2-ctl --device=/dev/video0 --all

# Test API response
curl http://localhost:8080/api/status
```

---

## ⚙️ Configuration

All settings are stored in `config.yaml`:

```yaml
# Server settings
server:
  host: "0.0.0.0"      # Listen address
  port: 8080            # Port number

# Video Capture (MS2109)
video:
  device: "/dev/video0"    # V4L2 device path
  width: 1920              # Target resolution
  height: 1080
  fps: 30                  # Target frame rate
  jpeg_quality: 85         # MJPEG quality (1-100)

# USB HID Devices
hid:
  keyboard_device: "/dev/hidg0"
  mouse_device: "/dev/hidg1"
  target_width: 1920       # Target machine screen resolution
  target_height: 1080

# GPIO Pins (modify according to your wiring)
gpio:
  power:
    linux_gpio: 134        # GPIO4_A6
    short_press_ms: 500    # Short press = power on
    long_press_ms: 5000    # Long press = force power off
  reset:
    linux_gpio: 33         # GPIO1_A1
    pulse_ms: 200          # Reset pulse duration
  power_status:
    linux_gpio: 144        # GPIO4_C0 (12V detection)

# Authentication (enable & change password for production!)
auth:
  enabled: false
  default_user: "admin"
  default_password: "admin"
```

---

## 📖 Usage Guide

### Dashboard

Navigate to `http://<CM4_IP>:8080` to access the dashboard:

- **System Monitoring**: Real-time ring charts for CPU / memory / temperature / disk
- **Power Control**: View 12V status, one-click power on / off / reset (with confirmation dialogs)
- **Device Status**: Connection status of capture card, HID keyboard, HID mouse
- **GPIO Info**: Current GPIO pin configuration
- **KVM Preview**: Live thumbnail of the target machine video — click to enter full KVM
- **Activity Logs**: Scrolling log of all operations

### KVM Remote Desktop

Navigate to `http://<CM4_IP>:8080/kvm` for the remote desktop:

**Mouse Control**:
- **Click directly on the video** to control the target machine
- Left click, right click, and middle click supported
- Scroll wheel supported
- Absolute positioning mode — click where you point

**Keyboard Control**:
- Click the video area to give it focus, then **type on your physical keyboard**
- All key events are intercepted and forwarded to the target machine

**Virtual On-Screen Keyboard**:
- Click `⌨️ 软键盘` (Virtual Keyboard) in the toolbar to open
- Full QWERTY layout with function key row
- Modifier keys (Shift/Ctrl/Alt) support sticky toggle
- Optimized for touch screens and mobile devices

**Quick Combo Keys**:
- `C+A+Del` → Ctrl+Alt+Delete (task manager / login screen)
- `Alt+Tab` → Switch windows
- `Alt+F4` → Close window
- `Win` → Open start menu
- `TTY1` → Ctrl+Alt+F1 (switch to terminal)
- `GUI` → Ctrl+Alt+F7 (switch back to desktop)
- `PrtSc` → Print Screen

**Quality Adjustment**:
- Toolbar slider adjusts MJPEG quality (10–100)
- Lower quality = less bandwidth, higher quality = sharper image

**Fullscreen Mode**:
- Click `⛶ 全屏` (Fullscreen) to toggle

---

## 🔗 API Reference

All API endpoints are prefixed with `http://<CM4_IP>:8080`

### Video

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/stream` | MJPEG video stream (display directly in browser) |
| `GET` | `/api/snapshot` | Single JPEG frame capture |
| `GET` | `/api/video/status` | Video capture device status |
| `POST` | `/api/video/quality?quality=85` | Set JPEG quality |

### HID (WebSocket)

| Protocol | Path | Description |
|----------|------|-------------|
| `WS` | `/api/ws/hid` | WebSocket HID input channel |

WebSocket message formats:
```json
// Key press
{"type": "keydown", "code": "KeyA"}

// Key release
{"type": "keyup", "code": "KeyA"}

// Mouse move (x, y are 0.0–1.0 as screen percentage)
{"type": "mousemove", "x": 0.5, "y": 0.3}

// Mouse button press (button: 0=left, 1=middle, 2=right)
{"type": "mousedown", "x": 0.5, "y": 0.3, "button": 0}

// Mouse button release
{"type": "mouseup", "x": 0.5, "y": 0.3, "button": 0}

// Scroll wheel
{"type": "wheel", "x": 0.5, "y": 0.3, "deltaY": -1}

// Key combination
{"type": "combo", "modifiers": ["ControlLeft", "AltLeft"], "keys": ["Delete"]}

// Release all keys
{"type": "releaseall"}
```

### Power Control

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/power/on` | Short press power button |
| `POST` | `/api/power/off` | Long press power button (force off) |
| `POST` | `/api/power/reset` | Press reset button |
| `GET` | `/api/power/status` | Read 12V power status |

### GPIO

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/gpio/status` | All GPIO status |
| `GET` | `/api/gpio/config` | GPIO configuration |
| `POST` | `/api/gpio/custom/{name}?value=1` | Set custom GPIO |
| `GET` | `/api/gpio/custom/{name}` | Read custom GPIO |

### System Info

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/system/info` | CPU / memory / temp / disk / network |
| `GET` | `/api/system/logs?n=50` | Recent operation logs |
| `GET` | `/api/status` | Overall BMC status |

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/login` | Login (body: `{"username": "admin", "password": "admin"}`) |

Returns: `{"token": "<JWT>", "type": "bearer"}`

Include in subsequent requests: `Authorization: Bearer <JWT>`

---

## 🔍 Troubleshooting

### Video Capture Card Not Detected

```bash
# Check USB devices
lsusb | grep -i "534d\|macro\|2109"

# Check V4L2 devices
v4l2-ctl --list-devices

# If /dev/video0 doesn't exist:
# 1. Reconnect the capture card
# 2. Check dmesg for errors: dmesg | tail -20
# 3. If detected as audio-only, add udev rules to rebind to uvcvideo
```

### USB HID Gadget Creation Fails

```bash
# Check kernel ConfigFS support
ls /sys/kernel/config/

# Manually load the module
sudo modprobe libcomposite

# Check for UDC (USB Device Controller)
ls /sys/class/udc/

# If no UDC found:
# The USB OTG port's device tree needs dr_mode = "peripheral" or "otg"
# This requires editing the device tree blob (DTB)
```

### GPIO Permission Denied

```bash
# Run as root
sudo python3 main.py

# Or add user to gpio group
sudo usermod -aG gpio $USER
# Then log out and back in
```

### Black Screen or Stuttering Video

```bash
# Try lower resolution/frame rate in config.yaml:
# video:
#   width: 1280
#   height: 720
#   fps: 15
#   jpeg_quality: 60

# Check USB bandwidth (MS2109 requires USB 2.0+)
lsusb -t

# Ensure the capture card is not connected via a USB hub
```

### WebSocket Keeps Disconnecting

```bash
# Check if HID devices exist
ls -la /dev/hidg*

# If missing, re-run gadget setup
sudo bash setup_gadget.sh setup

# Check system logs
sudo journalctl -u si_bmc -f
```

---

## 📁 Project Structure

```
SI_server/
├── config.yaml              # Global configuration file
├── main.py                  # FastAPI entry point (all API routes)
├── requirements.txt         # Python dependencies
├── setup_gadget.sh          # USB OTG HID Gadget setup script
├── si_bmc.service           # systemd service unit file
├── GPIOdefine               # GPIO pin definitions (source file)
│
├── modules/                 # Backend modules
│   ├── video.py             # V4L2 video capture + MJPEG streaming
│   ├── hid.py               # USB HID keyboard/mouse emulation
│   ├── gpio_ctrl.py         # GPIO power control (sysfs)
│   ├── system_info.py       # System metrics (psutil + /proc fallback)
│   └── auth.py              # JWT authentication
│
├── static/                  # Frontend
│   ├── index.html           # Dashboard page
│   ├── kvm.html             # KVM remote desktop page
│   ├── css/
│   │   ├── main.css         # Design system (dark glassmorphism)
│   │   ├── dashboard.css    # Dashboard styles
│   │   └── kvm.css          # KVM styles (virtual keyboard etc.)
│   ├── js/
│   │   ├── api.js           # API communication + Toast + Confirm
│   │   ├── app.js           # Dashboard logic
│   │   ├── kvm.js           # KVM core (video + input handling)
│   │   ├── keyboard.js      # Virtual keyboard
│   │   └── mouse.js         # Mouse coordinate mapping
│   └── assets/
│       └── favicon.svg      # Site icon
│
└── scripts/
    └── install.sh           # Automated installation script
```

---

## 🔧 Extending the Project

### Adding Custom GPIO Pins

Add to the `gpio` section in `config.yaml`:

```yaml
gpio:
  custom_gpios:
    - name: "led_status"
      linux_gpio: 150
      direction: "out"
      active_low: false
    - name: "buzzer"
      linux_gpio: 151
      direction: "out"
    - name: "door_sensor"
      linux_gpio: 152
      direction: "in"
```

Control via API:
```bash
# Set output value
curl -X POST "http://<IP>:8080/api/gpio/custom/led_status?value=1"

# Read input value
curl "http://<IP>:8080/api/gpio/custom/door_sensor"
```

### Adding New API Endpoints

Add new routes in `main.py`:

```python
@app.get("/api/my-feature")
async def my_feature():
    return {"status": "ok", "data": "your data here"}
```

### Customizing the Virtual Keyboard Layout

Edit the `layout` object in `static/js/keyboard.js` to add/remove/modify keys.

### Adding Virtual Media (Future)

The USB ConfigFS framework can be extended to emulate a USB Mass Storage device, allowing ISO mounting for remote OS installation. This would require:
1. Adding a `mass_storage` function to `setup_gadget.sh`
2. Creating an API endpoint for ISO upload/mount
3. Adding a UI panel for virtual media management

---

## 📄 License

This project is for educational and internal use only.

---

*SI BMC Server v1.0 — Built for Orange Pi CM4 (RK3566)*
