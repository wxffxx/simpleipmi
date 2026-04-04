"""
SI BMC Server — Main Application
Orange Pi CM4 (RK3566) Baseboard Management Controller

Features:
  - MJPEG video stream from MS2109 USB capture card
  - USB OTG HID keyboard/mouse emulation
  - GPIO power control (on/off/reset) & 12V status
  - Web dashboard + KVM remote desktop
  - REST API + WebSocket

Usage:
  python3 main.py
  # or: uvicorn main:app --host 0.0.0.0 --port 8080
"""

import os
import sys
import yaml
import time
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Load Configuration ──────────────────────────────────────────
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")

def load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

config = load_config()

# ── Logging ─────────────────────────────────────────────────────
log_level = config.get("logging", {}).get("level", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("si-bmc")

# In-memory log buffer for dashboard
class LogBuffer:
    def __init__(self, max_lines: int = 500):
        self.max_lines = max_lines
        self.lines = []

    def add(self, msg: str, level: str = "INFO"):
        entry = {
            "time": time.strftime("%H:%M:%S"),
            "level": level,
            "message": msg,
        }
        self.lines.append(entry)
        if len(self.lines) > self.max_lines:
            self.lines = self.lines[-self.max_lines:]

    def get(self, n: int = 50) -> list:
        return self.lines[-n:]

log_buffer = LogBuffer(config.get("logging", {}).get("max_lines", 500))

class LogHandler(logging.Handler):
    def emit(self, record):
        log_buffer.add(record.getMessage(), record.levelname)

logging.getLogger("si-bmc").addHandler(LogHandler())

# ── Import Modules ──────────────────────────────────────────────
from modules.video import VideoCapture
from modules.hid import HIDManager
from modules.gpio_ctrl import GPIOController
from modules.system_info import SystemInfo
from modules.auth import AuthManager
from modules.terminal import WebTerminal

# ── Initialize Modules ──────────────────────────────────────────
video_capture = VideoCapture(config.get("video", {}))
hid_manager = HIDManager(config.get("hid", {}))
gpio_controller = GPIOController(config.get("gpio", {}))
system_info = SystemInfo()
auth_manager = AuthManager(config.get("auth", {}))
web_terminal = WebTerminal(config.get("terminal", {}))

# ── WebSocket connections tracking ───────────────────────────────
active_ws_connections: list[WebSocket] = []

# ── Application Lifecycle ───────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("=" * 50)
    logger.info("SI BMC Server starting up...")
    logger.info("=" * 50)

    # Start video capture
    await video_capture.start()
    log_buffer.add("Video capture module started")

    # Start HID devices
    await hid_manager.start()
    log_buffer.add("HID manager started")

    # Setup GPIO
    await gpio_controller.setup()
    log_buffer.add("GPIO controller initialized")

    logger.info(f"Server ready on port {config.get('server', {}).get('port', 8080)}")
    log_buffer.add("BMC Server ready", "INFO")

    yield  # Application runs here

    # Shutdown
    logger.info("SI BMC Server shutting down...")
    await video_capture.stop()
    await hid_manager.stop()
    await gpio_controller.cleanup()
    web_terminal.cleanup()
    logger.info("Cleanup complete")


# ── FastAPI App ─────────────────────────────────────────────────
app = FastAPI(
    title="SI BMC Server",
    description="Orange Pi CM4 Baseboard Management Controller",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files
static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")


# ── Auth Dependency ─────────────────────────────────────────────
async def check_auth(request: Request):
    """Dependency to check authorization."""
    if not auth_manager.enabled:
        return True
    auth_header = request.headers.get("Authorization")
    if not auth_manager.check_request(auth_header):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


# ── Page Routes ─────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve dashboard page."""
    index_path = os.path.join(static_path, "index.html")
    with open(index_path, "r") as f:
        return HTMLResponse(content=f.read())


@app.get("/kvm", response_class=HTMLResponse)
async def kvm_page():
    """Serve KVM remote desktop page."""
    kvm_path = os.path.join(static_path, "kvm.html")
    with open(kvm_path, "r") as f:
        return HTMLResponse(content=f.read())


@app.get("/console", response_class=HTMLResponse)
async def console_page():
    """Serve web console page."""
    console_path = os.path.join(static_path, "console.html")
    with open(console_path, "r") as f:
        return HTMLResponse(content=f.read())


# ── Auth API ────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    """Authenticate and return JWT token."""
    token = auth_manager.authenticate(req.username, req.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": token, "type": "bearer"}


# ── Video Stream API ────────────────────────────────────────────
@app.get("/api/stream")
async def video_stream():
    """MJPEG video stream endpoint."""
    return StreamingResponse(
        video_capture.mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/api/snapshot")
async def video_snapshot():
    """Get a single JPEG frame."""
    frame = await video_capture.get_snapshot()
    if frame is None:
        raise HTTPException(status_code=503, detail="No video frame available")
    return StreamingResponse(
        iter([frame]),
        media_type="image/jpeg",
    )


@app.get("/api/video/status")
async def video_status():
    """Get video capture status."""
    return video_capture.get_status()


@app.post("/api/video/quality")
async def set_video_quality(quality: int = Query(ge=1, le=100)):
    """Set MJPEG quality (1-100)."""
    await video_capture.set_quality(quality)
    log_buffer.add(f"Video quality set to {quality}")
    return {"quality": quality}


# ── HID WebSocket ───────────────────────────────────────────────
@app.websocket("/api/ws/hid")
async def hid_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time HID input.
    Receives keyboard/mouse events from browser and forwards to USB HID devices.
    """
    await websocket.accept()
    active_ws_connections.append(websocket)
    client = websocket.client
    logger.info(f"HID WebSocket connected: {client}")
    log_buffer.add(f"KVM client connected: {client}")

    try:
        while True:
            data = await websocket.receive_json()
            await hid_manager.handle_ws_message(data)
    except WebSocketDisconnect:
        logger.info(f"HID WebSocket disconnected: {client}")
        log_buffer.add(f"KVM client disconnected: {client}")
    except Exception as e:
        logger.error(f"HID WebSocket error: {e}")
    finally:
        if websocket in active_ws_connections:
            active_ws_connections.remove(websocket)


# ── Power Control API ───────────────────────────────────────────
@app.post("/api/power/{action}")
async def power_control(action: str, _auth=Depends(check_auth)):
    """
    Control target machine power.
    action: "on" | "off" | "reset"
    """
    if action == "on":
        result = await gpio_controller.power_on()
        log_buffer.add("Power ON command sent", "WARNING")
    elif action == "off":
        result = await gpio_controller.power_off()
        log_buffer.add("Power OFF (force) command sent", "WARNING")
    elif action == "reset":
        result = await gpio_controller.reset()
        log_buffer.add("Reset command sent", "WARNING")
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    return result


@app.get("/api/power/status")
async def power_status():
    """Get 12V power status from PCIe voltage divider."""
    return await gpio_controller.get_power_status()


# ── GPIO API ────────────────────────────────────────────────────
@app.get("/api/gpio/status")
async def gpio_status():
    """Get all GPIO status."""
    return gpio_controller.get_status()


@app.get("/api/gpio/config")
async def gpio_config():
    """Get GPIO configuration."""
    return gpio_controller.get_config()


@app.post("/api/gpio/custom/{name}")
async def custom_gpio_set(name: str, value: int = Query(ge=0, le=1), _auth=Depends(check_auth)):
    """Set a custom GPIO pin value."""
    result = await gpio_controller.set_custom_gpio(name, value)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    log_buffer.add(f"Custom GPIO '{name}' set to {value}")
    return result


@app.get("/api/gpio/custom/{name}")
async def custom_gpio_get(name: str):
    """Read a custom GPIO pin value."""
    result = await gpio_controller.get_custom_gpio(name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ── System Info API ─────────────────────────────────────────────
@app.get("/api/system/info")
async def get_system_info():
    """Get comprehensive system information."""
    info = await system_info.get_all()
    return info


@app.get("/api/system/logs")
async def get_system_logs(n: int = Query(default=50, ge=1, le=500)):
    """Get recent operation logs."""
    return {"logs": log_buffer.get(n)}


# ── HID Status API ──────────────────────────────────────────────
@app.get("/api/hid/status")
async def hid_status():
    """Get HID device status."""
    return hid_manager.get_status()


# ── Terminal WebSocket ──────────────────────────────────────────
@app.websocket("/api/ws/terminal")
async def terminal_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for web terminal (console).
    Provides PTY-based shell access through the browser.
    """
    await websocket.accept()
    session_id = f"ws_{id(websocket)}"
    client = websocket.client
    logger.info(f"Terminal WebSocket connected: {client}")
    log_buffer.add(f"Console session opened: {client}")

    try:
        # Receive initial resize info
        init_data = await websocket.receive_json()
        cols = init_data.get("cols", 120)
        rows = init_data.get("rows", 40)

        if not web_terminal.create_session(session_id, cols, rows):
            await websocket.send_json({"error": "Failed to create terminal session"})
            await websocket.close()
            return

        # Read loop: send terminal output to browser
        async def read_loop():
            while True:
                if not web_terminal.is_alive(session_id):
                    break
                output = web_terminal.read(session_id)
                if output is None:
                    break
                if output:
                    await websocket.send_json({"output": output})
                await asyncio.sleep(0.02)  # 50fps

        read_task = asyncio.create_task(read_loop())

        # Write loop: send browser input to terminal
        try:
            while True:
                msg = await websocket.receive_json()
                if "input" in msg:
                    web_terminal.write(session_id, msg["input"])
                elif "resize" in msg:
                    r = msg["resize"]
                    web_terminal.resize(session_id, r.get("cols", 120), r.get("rows", 40))
        except WebSocketDisconnect:
            pass
        finally:
            read_task.cancel()

    except Exception as e:
        logger.error(f"Terminal WebSocket error: {e}")
    finally:
        web_terminal.close_session(session_id)
        log_buffer.add(f"Console session closed: {client}")
        logger.info(f"Terminal WebSocket disconnected: {client}")


# ── Overall Status API ──────────────────────────────────────────
@app.get("/api/status")
async def overall_status():
    """Get overall BMC status (for dashboard overview)."""
    power = await gpio_controller.get_power_status()
    return {
        "server_uptime": time.time(),
        "video": video_capture.get_status(),
        "hid": hid_manager.get_status(),
        "gpio": gpio_controller.get_status(),
        "power": power,
        "active_connections": len(active_ws_connections),
    }


# ── Main Entry Point ───────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    server_config = config.get("server", {})
    uvicorn.run(
        "main:app",
        host=server_config.get("host", "0.0.0.0"),
        port=server_config.get("port", 8080),
        reload=server_config.get("debug", False),
        log_level="info",
    )
