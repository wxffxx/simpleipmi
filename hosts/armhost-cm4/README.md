# armhost-cm4/

Full-featured KVM host for CM4-compatible ARM Linux SBCs. Uses an external ESP32-S3 as a UART-based USB HID bridge for keyboard/mouse, and a USB capture card (MS2109) for video.

## Structure

```
armhost-cm4/
├── server/                 # Python server (FastAPI)
│   ├── main.py             #   Application entry, REST API + WebSocket
│   ├── config.yaml         #   Runtime configuration (video, HID, GPIO, auth)
│   ├── modules/
│   │   ├── video.py        #   MJPEG capture from USB card (OpenCV/V4L2)
│   │   ├── hid.py          #   HID manager (UART ESP32-S3 bridge + ConfigFS fallback)
│   │   ├── gpio_ctrl.py    #   Power/reset button control via GPIO
│   │   ├── auth.py         #   Simple password authentication
│   │   ├── terminal.py     #   Web terminal (pty)
│   │   ├── system_info.py  #   System status (CPU, RAM, temp, etc.)
│   │   └── esp32_flasher.py#   ESP32-S3 OTA firmware update
│   ├── static/             #   Web dashboard frontend
│   │   ├── index.html      #     Dashboard
│   │   ├── kvm.html        #     KVM remote desktop
│   │   ├── console.html    #     Web terminal
│   │   ├── css/            #     Stylesheets
│   │   └── js/             #     Frontend logic (api, app, keyboard, mouse, kvm)
│   ├── scripts/
│   │   └── install.sh      #   Deployment script
│   ├── legacy/             #   Legacy USB gadget scripts (deprecated)
│   ├── si_bmc.service      #   systemd unit file
│   └── requirements.txt    #   Python dependencies
├── firmware/               # ESP32-S3 HID bridge firmware
│   ├── src/
│   │   ├── main.cpp        #   UART listener + USB HID output
│   │   └── usb_hid.cpp     #   TinyUSB keyboard + mouse composite device
│   ├── include/
│   │   ├── protocol.h      #   Binary serial protocol (shared with server)
│   │   ├── config.h        #   Pin and UART settings
│   │   └── usb_hid.h       #   HID interface
│   └── platformio.ini      #   Build config (ESP32-S3, USB mode)
└── docs/
    ├── DEVELOPMENT.md      #   Development and debugging guide
    └── topology.png        #   System topology diagram
```

## Quick Start

```bash
# Server
cd server
pip install -r requirements.txt
python main.py

# Firmware (requires PlatformIO)
cd firmware
pio run -t upload
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed setup instructions.
