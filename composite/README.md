# composite/

Multi-host management system. Central server that manages multiple KVM hosts and USB capture cards simultaneously. WIP.

## Architecture

```
composite/
└── server/       # Unified management server (WIP)
```

## Planned Features

- Device discovery and registration (mDNS / manual)
- USB capture card enumeration (`/dev/video*`)
- Host-to-capture-card pairing ("KVM channel")
- Multi-channel web panel with unified HID routing
- Centralized logging and firmware updates

## Tech Stack (Planned)

- Backend: Python (FastAPI) or Go
- Frontend: React / Vue
- Database: SQLite
- Deployment: Docker / systemd
