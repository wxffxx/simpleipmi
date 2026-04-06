"""
SI BMC — HID module (Serial ESP32-S3 Bridge + Legacy Gadget fallback)
Sends keyboard/mouse commands to ESP32-S3 via UART serial,
or falls back to Linux ConfigFS USB Gadget (/dev/hidg*).

Supports:
  - Auto-discovery of UART ports with ESP32-S3 heartbeat probe
  - Runtime port selection via API
  - Dual mode: "serial" (ESP32-S3) or "gadget" (ConfigFS)
"""

import asyncio
import glob
import struct
import logging
import os
import time
from typing import Optional

logger = logging.getLogger("si-bmc.hid")

# ============================================================
# CRC8 (polynomial 0x07, init 0x00) — matches protocol.h
# ============================================================
def crc8_calc(data: bytes) -> int:
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc

# ============================================================
# Protocol constants — mirrors protocol.h
# ============================================================
PROTO_HEAD          = 0xAA
MSG_KEYBOARD_REPORT = 0x01
MSG_MOUSE_REPORT    = 0x02
MSG_HEARTBEAT       = 0x03
MSG_RESET_ALL       = 0x04
MSG_MOUSE_MOVE_REL  = 0x05
MSG_JSON_HID        = 0x10
MSG_HEARTBEAT_ACK   = 0x83
MSG_ERROR           = 0xFE

KB_REPORT_SIZE      = 8
MOUSE_REPORT_SIZE   = 7
MOUSE_ABS_MAX       = 32767

# ============================================================
# USB HID Keycode mapping: JavaScript key → USB HID Usage ID
# Reference: USB HID Usage Tables, Section 10 (Keyboard/Keypad)
# ============================================================
JS_TO_HID_KEYCODE = {
    # Letters
    "KeyA": 0x04, "KeyB": 0x05, "KeyC": 0x06, "KeyD": 0x07,
    "KeyE": 0x08, "KeyF": 0x09, "KeyG": 0x0A, "KeyH": 0x0B,
    "KeyI": 0x0C, "KeyJ": 0x0D, "KeyK": 0x0E, "KeyL": 0x0F,
    "KeyM": 0x10, "KeyN": 0x11, "KeyO": 0x12, "KeyP": 0x13,
    "KeyQ": 0x14, "KeyR": 0x15, "KeyS": 0x16, "KeyT": 0x17,
    "KeyU": 0x18, "KeyV": 0x19, "KeyW": 0x1A, "KeyX": 0x1B,
    "KeyY": 0x1C, "KeyZ": 0x1D,

    # Numbers (top row)
    "Digit1": 0x1E, "Digit2": 0x1F, "Digit3": 0x20, "Digit4": 0x21,
    "Digit5": 0x22, "Digit6": 0x23, "Digit7": 0x24, "Digit8": 0x25,
    "Digit9": 0x26, "Digit0": 0x27,

    # Control keys
    "Enter": 0x28, "Escape": 0x29, "Backspace": 0x2A, "Tab": 0x2B,
    "Space": 0x2C, "Minus": 0x2D, "Equal": 0x2E, "BracketLeft": 0x2F,
    "BracketRight": 0x30, "Backslash": 0x31, "Semicolon": 0x33,
    "Quote": 0x34, "Backquote": 0x35, "Comma": 0x36, "Period": 0x37,
    "Slash": 0x38, "CapsLock": 0x39,

    # Function keys
    "F1": 0x3A, "F2": 0x3B, "F3": 0x3C, "F4": 0x3D,
    "F5": 0x3E, "F6": 0x3F, "F7": 0x40, "F8": 0x41,
    "F9": 0x42, "F10": 0x43, "F11": 0x44, "F12": 0x45,

    # Navigation / editing
    "PrintScreen": 0x46, "ScrollLock": 0x47, "Pause": 0x48,
    "Insert": 0x49, "Home": 0x4A, "PageUp": 0x4B,
    "Delete": 0x4C, "End": 0x4D, "PageDown": 0x4E,
    "ArrowRight": 0x4F, "ArrowLeft": 0x50, "ArrowDown": 0x51,
    "ArrowUp": 0x52, "NumLock": 0x53,

    # Numpad
    "NumpadDivide": 0x54, "NumpadMultiply": 0x55, "NumpadSubtract": 0x56,
    "NumpadAdd": 0x57, "NumpadEnter": 0x58,
    "Numpad1": 0x59, "Numpad2": 0x5A, "Numpad3": 0x5B,
    "Numpad4": 0x5C, "Numpad5": 0x5D, "Numpad6": 0x5E,
    "Numpad7": 0x5F, "Numpad8": 0x60, "Numpad9": 0x61,
    "Numpad0": 0x62, "NumpadDecimal": 0x63,

    # Additional keys
    "ContextMenu": 0x65, "Power": 0x66,
    "IntlBackslash": 0x64,
}

# Modifier bit masks (byte 0 of keyboard HID report)
MODIFIER_KEYS = {
    "ControlLeft":  0x01,
    "ShiftLeft":    0x02,
    "AltLeft":      0x04,
    "MetaLeft":     0x08,
    "ControlRight": 0x10,
    "ShiftRight":   0x20,
    "AltRight":     0x40,
    "MetaRight":    0x80,
}


# ============================================================
# Serial HID Bridge — communicates with ESP32-S3 via UART
# ============================================================
class SerialHIDBridge:
    """
    Handles serial communication with ESP32-S3 HID bridge.
    Supports auto-discovery, heartbeat monitoring, and port switching.
    """

    # Standard UART device patterns to scan on Linux ARM boards
    UART_PATTERNS = [
        "/dev/ttyS*",
        "/dev/ttyAMA*",
        "/dev/ttyUSB*",
        "/dev/ttyACM*",
    ]

    # Ports to skip (usually kernel console or unreliable)
    SKIP_PORTS = {"/dev/ttyS0"}

    def __init__(self, config: dict):
        self._port: Optional[str] = config.get("serial_port", "auto")
        self._baud = config.get("serial_baud", 115200)
        self._heartbeat_interval = config.get("heartbeat_interval", 5)
        self._probe_timeout = config.get("probe_timeout", 0.5)
        self._auto_save = config.get("auto_save_port", True)
        self._serial = None  # serial.Serial instance
        self._connected = False
        self._esp32_status = 0  # 0=OK from last heartbeat
        self._last_heartbeat = 0
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._discovered_ports: list = []

    async def start(self):
        """Initialize serial connection."""
        try:
            import serial
        except ImportError:
            logger.error("pyserial not installed! Run: pip install pyserial")
            return

        if self._port == "auto":
            logger.info("Auto-discovering ESP32-S3 on available UART ports...")
            result = await self.probe_all_ports()
            if result:
                self._port = result
                logger.info(f"ESP32-S3 auto-detected on {self._port}")
            else:
                logger.warning("No ESP32-S3 found on any UART port")
                return
        else:
            # Try configured port
            if not await self._probe_port(self._port):
                logger.warning(f"ESP32-S3 not responding on configured port {self._port}, scanning...")
                result = await self.probe_all_ports()
                if result:
                    self._port = result
                    logger.info(f"ESP32-S3 found on fallback port {self._port}")
                else:
                    logger.warning("No ESP32-S3 found on any port")
                    return

        # Open the selected port
        await self._open_port(self._port)

        # Start heartbeat monitor
        if self._connected:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self):
        """Close serial connection."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        if self._serial and self._serial.is_open:
            # Send reset command before closing
            await self._send_frame(MSG_RESET_ALL, b'')
            self._serial.close()
        self._serial = None
        self._connected = False

    def _scan_ports(self) -> list:
        """Enumerate all available UART devices."""
        ports = []
        for pattern in self.UART_PATTERNS:
            for dev in sorted(glob.glob(pattern)):
                if dev not in self.SKIP_PORTS:
                    ports.append(dev)
        return ports

    async def probe_all_ports(self) -> Optional[str]:
        """Scan all UART ports and probe for ESP32-S3 via heartbeat."""
        ports = self._scan_ports()
        self._discovered_ports = []

        for port in ports:
            detected = await self._probe_port(port)
            self._discovered_ports.append({
                "device": port,
                "description": os.path.basename(port),
                "esp32_detected": detected,
                "active": False,
            })
            if detected:
                # Mark as found but continue scanning all ports for the list
                pass

        # Return first detected port
        for p in self._discovered_ports:
            if p["esp32_detected"]:
                return p["device"]
        return None

    async def _probe_port(self, port: str) -> bool:
        """Try to ping ESP32-S3 on a specific port."""
        try:
            import serial
            test_ser = serial.Serial(
                port=port,
                baudrate=self._baud,
                timeout=self._probe_timeout,
                write_timeout=self._probe_timeout,
            )

            # Build heartbeat frame
            frame = self._build_frame(MSG_HEARTBEAT, b'')
            test_ser.reset_input_buffer()
            test_ser.write(frame)
            test_ser.flush()

            # Wait for response
            await asyncio.sleep(self._probe_timeout)

            if test_ser.in_waiting >= 5:  # HEAD + TYPE + LEN + 1-byte payload + CRC
                resp = test_ser.read(test_ser.in_waiting)
                # Look for heartbeat ACK (0xAA 0x83 ...)
                if PROTO_HEAD in resp:
                    idx = resp.index(PROTO_HEAD)
                    if idx + 2 < len(resp) and resp[idx + 1] == MSG_HEARTBEAT_ACK:
                        test_ser.close()
                        return True

            test_ser.close()
            return False

        except Exception as e:
            logger.debug(f"Probe failed on {port}: {e}")
            return False

    async def _open_port(self, port: str):
        """Open and configure the serial port."""
        try:
            import serial
            if self._serial and self._serial.is_open:
                self._serial.close()

            self._serial = serial.Serial(
                port=port,
                baudrate=self._baud,
                timeout=0.01,
                write_timeout=0.1,
            )
            self._connected = True
            self._port = port

            # Update discovered ports list
            for p in self._discovered_ports:
                p["active"] = (p["device"] == port)

            logger.info(f"Serial HID bridge connected: {port} @ {self._baud} baud")
        except Exception as e:
            logger.error(f"Failed to open serial port {port}: {e}")
            self._connected = False

    async def select_port(self, port: str) -> dict:
        """Switch to a different serial port (called from API)."""
        if not os.path.exists(port):
            return {"error": f"Port {port} does not exist"}

        # Close current connection
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        if self._serial and self._serial.is_open:
            self._serial.close()

        # Probe new port
        detected = await self._probe_port(port)
        if not detected:
            return {"error": f"No ESP32-S3 responding on {port}", "device": port}

        # Open it
        await self._open_port(port)

        # Restart heartbeat
        if self._connected:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        return {"ok": True, "device": port}

    def _build_frame(self, msg_type: int, payload: bytes) -> bytes:
        """Build a complete protocol frame."""
        length = len(payload)
        # CRC is over TYPE + LEN + PAYLOAD
        crc_data = bytes([msg_type, length]) + payload
        crc = crc8_calc(crc_data)
        return bytes([PROTO_HEAD, msg_type, length]) + payload + bytes([crc])

    async def _send_frame(self, msg_type: int, payload: bytes):
        """Send a protocol frame over serial."""
        if not self._connected or not self._serial or not self._serial.is_open:
            return
        frame = self._build_frame(msg_type, payload)
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._serial.write(frame)
            )
        except Exception as e:
            logger.error(f"Serial write error: {e}")
            self._connected = False

    async def send_keyboard_report(self, modifier: int, keys: list):
        """Send an 8-byte keyboard HID report."""
        padded_keys = (keys + [0] * 6)[:6]
        payload = struct.pack('BBBBBBBB',
                              modifier, 0x00,
                              padded_keys[0], padded_keys[1], padded_keys[2],
                              padded_keys[3], padded_keys[4], padded_keys[5])
        await self._send_frame(MSG_KEYBOARD_REPORT, payload)

    async def send_mouse_report(self, buttons: int, abs_x: int, abs_y: int,
                                scroll_y: int = 0, scroll_x: int = 0):
        """Send a 7-byte absolute mouse HID report."""
        abs_x = max(0, min(MOUSE_ABS_MAX, abs_x))
        abs_y = max(0, min(MOUSE_ABS_MAX, abs_y))
        scroll_y = max(-127, min(127, scroll_y))
        scroll_x = max(-127, min(127, scroll_x))
        payload = struct.pack('<BHHbb', buttons, abs_x, abs_y, scroll_y, scroll_x)
        await self._send_frame(MSG_MOUSE_REPORT, payload)

    async def reset_all(self):
        """Send reset command to release all keys and buttons."""
        await self._send_frame(MSG_RESET_ALL, b'')

    async def send_json(self, data: dict):
        """Send raw JSON to ESP32-S3's proven USBHIDManager for direct handling."""
        import json
        json_bytes = json.dumps(data, separators=(',', ':')).encode('utf-8')
        if len(json_bytes) > 255:
            logger.warning(f"JSON too large ({len(json_bytes)} bytes), skipping")
            return
        await self._send_frame(MSG_JSON_HID, json_bytes)

    async def send_mouse_move_rel(self, dx: int, dy: int):
        """Send relative mouse movement (int8 dx, dy)."""
        dx = max(-127, min(127, dx))
        dy = max(-127, min(127, dy))
        payload = struct.pack('bb', dx, dy)
        await self._send_frame(MSG_MOUSE_MOVE_REL, payload)

    async def _heartbeat_loop(self):
        """Periodically check ESP32-S3 connection."""
        while True:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                if not self._connected:
                    continue

                await self._send_frame(MSG_HEARTBEAT, b'')
                await asyncio.sleep(0.3)

                if self._serial and self._serial.in_waiting > 0:
                    data = self._serial.read(self._serial.in_waiting)
                    if PROTO_HEAD in data:
                        idx = data.index(PROTO_HEAD)
                        if idx + 3 < len(data) and data[idx + 1] == MSG_HEARTBEAT_ACK:
                            self._esp32_status = data[idx + 3]  # status byte
                            self._last_heartbeat = time.time()
                else:
                    # No response — may be disconnected
                    if time.time() - self._last_heartbeat > self._heartbeat_interval * 3:
                        logger.warning("ESP32-S3 heartbeat lost")
                        self._connected = False

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    def get_ports_info(self) -> dict:
        """Get discovered ports and current status (for API)."""
        # Refresh port list
        current_ports = self._scan_ports()

        # Merge with discovered info
        ports = []
        for dev in current_ports:
            existing = next((p for p in self._discovered_ports if p["device"] == dev), None)
            if existing:
                ports.append(existing)
            else:
                ports.append({
                    "device": dev,
                    "description": os.path.basename(dev),
                    "esp32_detected": False,
                    "active": False,
                })

        return {
            "ports": ports,
            "current": self._port if self._connected else None,
            "mode": "serial",
        }

    @property
    def is_connected(self) -> bool:
        return self._connected


# ============================================================
# Legacy Gadget HID — original ConfigFS implementation
# ============================================================
class GadgetHIDKeyboard:
    """USB HID Keyboard via Linux ConfigFS (/dev/hidg0)."""

    def __init__(self, device: str = "/dev/hidg0"):
        self.device = device
        self._fd: Optional[int] = None
        self._available = False

    async def open(self):
        try:
            self._fd = os.open(self.device, os.O_WRONLY | os.O_NONBLOCK)
            self._available = True
            logger.info(f"Gadget keyboard opened: {self.device}")
        except Exception as e:
            logger.warning(f"Gadget keyboard unavailable: {e}")
            self._available = False

    async def close(self):
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
            self._available = False

    async def send_report(self, report: bytes):
        if not self._available or self._fd is None:
            return
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: os.write(self._fd, report)
            )
        except Exception as e:
            logger.error(f"Gadget keyboard write error: {e}")


class GadgetHIDMouse:
    """USB HID Mouse via Linux ConfigFS (/dev/hidg1)."""

    def __init__(self, device: str = "/dev/hidg1"):
        self.device = device
        self._fd: Optional[int] = None
        self._available = False

    async def open(self):
        try:
            self._fd = os.open(self.device, os.O_WRONLY | os.O_NONBLOCK)
            self._available = True
            logger.info(f"Gadget mouse opened: {self.device}")
        except Exception as e:
            logger.warning(f"Gadget mouse unavailable: {e}")
            self._available = False

    async def close(self):
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
            self._available = False

    async def send_report(self, report: bytes):
        if not self._available or self._fd is None:
            return
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: os.write(self._fd, report)
            )
        except Exception as e:
            logger.error(f"Gadget mouse write error: {e}")


# ============================================================
# HIDManager — unified interface (serial or gadget mode)
# ============================================================
class HIDManager:
    """
    Manages HID input regardless of backend.
    mode: "serial" → ESP32-S3 via UART
    mode: "gadget" → Linux ConfigFS /dev/hidg*
    """

    def __init__(self, config: dict):
        self._mode = config.get("mode", "serial")
        self._config = config

        # Keyboard state tracking (shared by both modes)
        self._modifier_state = 0
        self._pressed_keys: list = []
        self._mouse_buttons = 0

        # Backend instances
        self._bridge: Optional[SerialHIDBridge] = None
        self._gadget_kb: Optional[GadgetHIDKeyboard] = None
        self._gadget_mouse: Optional[GadgetHIDMouse] = None

    async def start(self):
        """Initialize the selected HID backend."""
        if self._mode == "serial":
            self._bridge = SerialHIDBridge(self._config)
            await self._bridge.start()
            if self._bridge.is_connected:
                logger.info("HID mode: Serial ESP32-S3 bridge")
            else:
                logger.warning("HID mode: Serial — ESP32-S3 not connected")
        elif self._mode == "gadget":
            kb_dev = self._config.get("keyboard_device", "/dev/hidg0")
            mouse_dev = self._config.get("mouse_device", "/dev/hidg1")
            self._gadget_kb = GadgetHIDKeyboard(kb_dev)
            self._gadget_mouse = GadgetHIDMouse(mouse_dev)
            await self._gadget_kb.open()
            await self._gadget_mouse.open()
            logger.info("HID mode: Legacy ConfigFS gadget")
        else:
            logger.error(f"Unknown HID mode: {self._mode}")

    async def stop(self):
        """Shutdown HID backend."""
        if self._bridge:
            await self._bridge.stop()
        if self._gadget_kb:
            await self._gadget_kb.close()
        if self._gadget_mouse:
            await self._gadget_mouse.close()

    # ── Keyboard operations ─────────────────────────────────────

    async def _send_keyboard_state(self):
        """Send current keyboard state to the active backend."""
        keys = (self._pressed_keys + [0] * 6)[:6]

        if self._mode == "serial" and self._bridge:
            await self._bridge.send_keyboard_report(self._modifier_state, keys)
        elif self._mode == "gadget" and self._gadget_kb:
            report = struct.pack('BBBBBBBB',
                                 self._modifier_state, 0x00,
                                 keys[0], keys[1], keys[2],
                                 keys[3], keys[4], keys[5])
            await self._gadget_kb.send_report(report)

    async def key_down(self, code: str):
        if code in MODIFIER_KEYS:
            self._modifier_state |= MODIFIER_KEYS[code]
        else:
            hid_code = JS_TO_HID_KEYCODE.get(code)
            if hid_code and hid_code not in self._pressed_keys:
                if len(self._pressed_keys) < 6:
                    self._pressed_keys.append(hid_code)
        await self._send_keyboard_state()

    async def key_up(self, code: str):
        if code in MODIFIER_KEYS:
            self._modifier_state &= ~MODIFIER_KEYS[code]
        else:
            hid_code = JS_TO_HID_KEYCODE.get(code)
            if hid_code and hid_code in self._pressed_keys:
                self._pressed_keys.remove(hid_code)
        await self._send_keyboard_state()

    async def release_all(self):
        self._modifier_state = 0
        self._pressed_keys.clear()
        self._mouse_buttons = 0
        if self._mode == "serial" and self._bridge:
            await self._bridge.reset_all()
        else:
            await self._send_keyboard_state()

    async def send_combo(self, modifiers: list, keys: list):
        mod_byte = 0
        for m in modifiers:
            mod_byte |= MODIFIER_KEYS.get(m, 0)
        hid_keys = [JS_TO_HID_KEYCODE[k] for k in keys if k in JS_TO_HID_KEYCODE]

        self._modifier_state = mod_byte
        self._pressed_keys = hid_keys[:6]
        await self._send_keyboard_state()
        await asyncio.sleep(0.05)
        await self.release_all()

    # ── Mouse operations ────────────────────────────────────────

    async def _send_mouse_state(self, x_pct: float, y_pct: float,
                                 scroll_y: int = 0, scroll_x: int = 0):
        abs_x = int(max(0, min(1, x_pct)) * MOUSE_ABS_MAX)
        abs_y = int(max(0, min(1, y_pct)) * MOUSE_ABS_MAX)

        if self._mode == "serial" and self._bridge:
            await self._bridge.send_mouse_report(
                self._mouse_buttons, abs_x, abs_y, scroll_y, scroll_x)
        elif self._mode == "gadget" and self._gadget_mouse:
            report = struct.pack('<BHHbb',
                                 self._mouse_buttons, abs_x, abs_y, scroll_y, scroll_x)
            await self._gadget_mouse.send_report(report)

    async def mouse_move(self, x: float, y: float):
        await self._send_mouse_state(x, y)

    async def mouse_button_down(self, x: float, y: float, button: int = 0):
        self._mouse_buttons |= (1 << button)
        await self._send_mouse_state(x, y)

    async def mouse_button_up(self, x: float, y: float, button: int = 0):
        self._mouse_buttons &= ~(1 << button)
        await self._send_mouse_state(x, y)

    async def mouse_click(self, x: float, y: float, button: int = 0):
        self._mouse_buttons |= (1 << button)
        await self._send_mouse_state(x, y)
        await asyncio.sleep(0.02)
        self._mouse_buttons &= ~(1 << button)
        await self._send_mouse_state(x, y)

    async def mouse_scroll(self, x: float, y: float, delta_y: int, delta_x: int = 0):
        await self._send_mouse_state(x, y, delta_y, delta_x)

    # ── WebSocket message handler (unchanged interface) ─────────

    async def handle_ws_message(self, data: dict):
        """
        Process a WebSocket HID message from the browser.

        In serial mode with JSON passthrough, the message is forwarded
        directly to the proven USBHIDManager on ESP32-S3, avoiding
        ARM-side keycode translation entirely.

        In gadget mode, falls back to local HID report generation.
        """
        msg_type = data.get("type")

        # Serial mode: use JSON passthrough to proven ESP32-S3 HID stack
        if self._mode == "serial" and self._bridge and self._bridge.is_connected:
            await self._bridge.send_json(data)
            return

        # Gadget mode fallback: ARM-side HID report generation
        if msg_type == "keydown":
            await self.key_down(data.get("code", ""))
        elif msg_type == "keyup":
            await self.key_up(data.get("code", ""))
        elif msg_type == "mousemove":
            await self.mouse_move(data.get("x", 0), data.get("y", 0))
        elif msg_type == "mousedown":
            await self.mouse_button_down(
                data.get("x", 0), data.get("y", 0), data.get("button", 0))
        elif msg_type == "mouseup":
            await self.mouse_button_up(
                data.get("x", 0), data.get("y", 0), data.get("button", 0))
        elif msg_type == "click":
            await self.mouse_click(
                data.get("x", 0), data.get("y", 0), data.get("button", 0))
        elif msg_type == "wheel":
            await self.mouse_scroll(
                data.get("x", 0), data.get("y", 0),
                data.get("deltaY", 0), data.get("deltaX", 0))
        elif msg_type == "combo":
            await self.send_combo(
                data.get("modifiers", []), data.get("keys", []))
        elif msg_type == "releaseall":
            await self.release_all()

    # ── Port management (for API) ───────────────────────────────

    async def get_ports(self) -> dict:
        """List all discovered UART ports."""
        if self._bridge:
            return self._bridge.get_ports_info()
        return {"ports": [], "current": None, "mode": self._mode}

    async def select_port(self, port: str) -> dict:
        """Switch to a different UART port."""
        if self._bridge:
            return await self._bridge.select_port(port)
        return {"error": "Not in serial mode"}

    async def probe_ports(self) -> dict:
        """Re-scan all UART ports."""
        if self._bridge:
            result = await self._bridge.probe_all_ports()
            info = self._bridge.get_ports_info()
            info["auto_detected"] = result
            return info
        return {"error": "Not in serial mode"}

    # ── Status ──────────────────────────────────────────────────

    def get_status(self) -> dict:
        if self._mode == "serial":
            connected = self._bridge.is_connected if self._bridge else False
            port = self._bridge._port if self._bridge else None
            return {
                "mode": "serial",
                "connected": connected,
                "port": port,
                "keyboard": {"available": connected},
                "mouse": {"available": connected},
            }
        else:
            return {
                "mode": "gadget",
                "keyboard": {
                    "available": self._gadget_kb._available if self._gadget_kb else False,
                    "device": self._gadget_kb.device if self._gadget_kb else None,
                },
                "mouse": {
                    "available": self._gadget_mouse._available if self._gadget_mouse else False,
                    "device": self._gadget_mouse.device if self._gadget_mouse else None,
                },
            }
