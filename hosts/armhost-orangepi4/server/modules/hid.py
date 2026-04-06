"""
SI BMC — USB HID Gadget module
Emulates USB keyboard and mouse via Linux ConfigFS USB Gadget.
Sends HID reports to /dev/hidg0 (keyboard) and /dev/hidg1 (mouse).
"""

import asyncio
import struct
import logging
from typing import Optional

logger = logging.getLogger("si-bmc.hid")

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


class HIDKeyboard:
    """
    USB HID Keyboard emulation.
    Sends 8-byte HID reports to /dev/hidg0.

    Report format (8 bytes):
      [0] Modifier bitmask (Ctrl, Shift, Alt, Meta)
      [1] Reserved (0x00)
      [2-7] Up to 6 simultaneous keycodes
    """

    def __init__(self, device: str = "/dev/hidg0"):
        self.device = device
        self._fd: Optional[int] = None
        self._modifier_state = 0
        self._pressed_keys: list = []  # Currently pressed keycodes
        self._available = False

    async def open(self):
        """Open the HID keyboard device."""
        try:
            import os
            self._fd = os.open(self.device, os.O_WRONLY | os.O_NONBLOCK)
            self._available = True
            logger.info(f"HID Keyboard opened: {self.device}")
        except FileNotFoundError:
            logger.warning(f"HID keyboard device not found: {self.device} (run setup_gadget.sh)")
            self._available = False
        except PermissionError:
            logger.error(f"Permission denied for {self.device} — run as root or fix permissions")
            self._available = False
        except Exception as e:
            logger.error(f"Failed to open HID keyboard: {e}")
            self._available = False

    async def close(self):
        """Close the HID keyboard device."""
        if self._fd is not None:
            import os
            os.close(self._fd)
            self._fd = None
            self._available = False

    async def key_down(self, code: str):
        """Handle key press event from browser."""
        if not self._available:
            return

        # Check if it's a modifier key
        if code in MODIFIER_KEYS:
            self._modifier_state |= MODIFIER_KEYS[code]
        else:
            hid_code = JS_TO_HID_KEYCODE.get(code)
            if hid_code and hid_code not in self._pressed_keys:
                if len(self._pressed_keys) < 6:  # Max 6 keys in standard report
                    self._pressed_keys.append(hid_code)

        await self._send_report()

    async def key_up(self, code: str):
        """Handle key release event from browser."""
        if not self._available:
            return

        if code in MODIFIER_KEYS:
            self._modifier_state &= ~MODIFIER_KEYS[code]
        else:
            hid_code = JS_TO_HID_KEYCODE.get(code)
            if hid_code and hid_code in self._pressed_keys:
                self._pressed_keys.remove(hid_code)

        await self._send_report()

    async def release_all(self):
        """Release all keys (send empty report)."""
        self._modifier_state = 0
        self._pressed_keys.clear()
        await self._send_report()

    async def send_combo(self, modifiers: list, keys: list):
        """
        Send a key combination (e.g. Ctrl+Alt+Del).
        modifiers: list of modifier codes (e.g. ["ControlLeft", "AltLeft"])
        keys: list of key codes (e.g. ["Delete"])
        """
        if not self._available:
            return

        mod_byte = 0
        for m in modifiers:
            mod_byte |= MODIFIER_KEYS.get(m, 0)

        hid_keys = []
        for k in keys:
            hid_code = JS_TO_HID_KEYCODE.get(k)
            if hid_code:
                hid_keys.append(hid_code)

        # Press
        self._modifier_state = mod_byte
        self._pressed_keys = hid_keys[:6]
        await self._send_report()

        # Brief hold
        await asyncio.sleep(0.05)

        # Release
        await self.release_all()

    async def _send_report(self):
        """Send the 8-byte HID keyboard report."""
        if self._fd is None:
            return

        keys = self._pressed_keys[:6]
        while len(keys) < 6:
            keys.append(0)

        report = struct.pack(
            'BBBBBBBB',
            self._modifier_state,   # Modifier bitmask
            0x00,                   # Reserved
            keys[0], keys[1], keys[2],
            keys[3], keys[4], keys[5]
        )

        try:
            import os
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: os.write(self._fd, report)
            )
        except Exception as e:
            logger.error(f"Failed to send keyboard report: {e}")

    @property
    def is_available(self) -> bool:
        return self._available


class HIDMouse:
    """
    USB HID Mouse emulation with ABSOLUTE positioning.
    Sends 7-byte HID reports to /dev/hidg1.

    Report format (7 bytes):
      [0]   Button bitmask (bit0=left, bit1=right, bit2=middle)
      [1-2] X absolute position (0-32767, little-endian uint16)
      [3-4] Y absolute position (0-32767, little-endian uint16)
      [5]   Vertical scroll wheel (signed int8)
      [6]   Horizontal scroll wheel (signed int8)

    Absolute positioning maps the full range [0, 32767] to the target display.
    """

    # Absolute coordinate range for HID absolute mouse
    ABS_MAX = 32767

    def __init__(self, device: str = "/dev/hidg1", target_width: int = 1920, target_height: int = 1080):
        self.device = device
        self.target_width = target_width
        self.target_height = target_height
        self._fd: Optional[int] = None
        self._buttons = 0
        self._available = False

    async def open(self):
        """Open the HID mouse device."""
        try:
            import os
            self._fd = os.open(self.device, os.O_WRONLY | os.O_NONBLOCK)
            self._available = True
            logger.info(f"HID Mouse opened: {self.device}")
        except FileNotFoundError:
            logger.warning(f"HID mouse device not found: {self.device} (run setup_gadget.sh)")
            self._available = False
        except PermissionError:
            logger.error(f"Permission denied for {self.device}")
            self._available = False
        except Exception as e:
            logger.error(f"Failed to open HID mouse: {e}")
            self._available = False

    async def close(self):
        """Close the HID mouse device."""
        if self._fd is not None:
            import os
            os.close(self._fd)
            self._fd = None
            self._available = False

    async def move(self, x_pct: float, y_pct: float):
        """
        Move mouse to absolute position.
        x_pct, y_pct: position as percentage (0.0 - 1.0) of the target screen.
        """
        if not self._available:
            return

        abs_x = int(x_pct * self.ABS_MAX)
        abs_y = int(y_pct * self.ABS_MAX)
        abs_x = max(0, min(self.ABS_MAX, abs_x))
        abs_y = max(0, min(self.ABS_MAX, abs_y))

        await self._send_report(abs_x, abs_y, 0, 0)

    async def click(self, x_pct: float, y_pct: float, button: int = 0):
        """
        Click at absolute position.
        button: 0=left, 1=right, 2=middle
        """
        if not self._available:
            return

        abs_x = int(x_pct * self.ABS_MAX)
        abs_y = int(y_pct * self.ABS_MAX)
        abs_x = max(0, min(self.ABS_MAX, abs_x))
        abs_y = max(0, min(self.ABS_MAX, abs_y))

        btn_mask = 1 << button

        # Press
        self._buttons |= btn_mask
        await self._send_report(abs_x, abs_y, 0, 0)

        await asyncio.sleep(0.02)

        # Release
        self._buttons &= ~btn_mask
        await self._send_report(abs_x, abs_y, 0, 0)

    async def button_down(self, x_pct: float, y_pct: float, button: int = 0):
        """Mouse button press (without release)."""
        if not self._available:
            return
        abs_x = int(max(0, min(1, x_pct)) * self.ABS_MAX)
        abs_y = int(max(0, min(1, y_pct)) * self.ABS_MAX)
        self._buttons |= (1 << button)
        await self._send_report(abs_x, abs_y, 0, 0)

    async def button_up(self, x_pct: float, y_pct: float, button: int = 0):
        """Mouse button release."""
        if not self._available:
            return
        abs_x = int(max(0, min(1, x_pct)) * self.ABS_MAX)
        abs_y = int(max(0, min(1, y_pct)) * self.ABS_MAX)
        self._buttons &= ~(1 << button)
        await self._send_report(abs_x, abs_y, 0, 0)

    async def scroll(self, x_pct: float, y_pct: float, delta_y: int, delta_x: int = 0):
        """
        Scroll wheel event.
        delta_y: vertical scroll (-127 to 127, negative = down)
        delta_x: horizontal scroll (-127 to 127)
        """
        if not self._available:
            return
        abs_x = int(max(0, min(1, x_pct)) * self.ABS_MAX)
        abs_y = int(max(0, min(1, y_pct)) * self.ABS_MAX)
        delta_y = max(-127, min(127, delta_y))
        delta_x = max(-127, min(127, delta_x))
        await self._send_report(abs_x, abs_y, delta_y, delta_x)

    async def _send_report(self, abs_x: int, abs_y: int, scroll_y: int = 0, scroll_x: int = 0):
        """Send the 7-byte HID mouse report."""
        if self._fd is None:
            return

        report = struct.pack(
            '<BHHbb',
            self._buttons,     # Button bitmask
            abs_x,             # X absolute (uint16 LE)
            abs_y,             # Y absolute (uint16 LE)
            scroll_y,          # Vertical scroll (int8)
            scroll_x,          # Horizontal scroll (int8)
        )

        try:
            import os
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: os.write(self._fd, report)
            )
        except Exception as e:
            logger.error(f"Failed to send mouse report: {e}")

    @property
    def is_available(self) -> bool:
        return self._available


class HIDManager:
    """Manages both keyboard and mouse HID devices."""

    def __init__(self, config: dict):
        kb_device = config.get("keyboard_device", "/dev/hidg0")
        mouse_device = config.get("mouse_device", "/dev/hidg1")
        target_w = config.get("target_width", 1920)
        target_h = config.get("target_height", 1080)

        self.keyboard = HIDKeyboard(device=kb_device)
        self.mouse = HIDMouse(device=mouse_device, target_width=target_w, target_height=target_h)

    async def start(self):
        """Open both HID devices."""
        await self.keyboard.open()
        await self.mouse.open()

    async def stop(self):
        """Close both HID devices."""
        await self.keyboard.release_all()
        await self.keyboard.close()
        await self.mouse.close()

    async def handle_ws_message(self, data: dict):
        """
        Process a WebSocket HID message from the browser.

        Message format:
          Keyboard: {"type": "keydown"|"keyup", "code": "KeyA"}
          Mouse move: {"type": "mousemove", "x": 0.5, "y": 0.3}
          Mouse click: {"type": "mousedown"|"mouseup", "x": 0.5, "y": 0.3, "button": 0}
          Mouse scroll: {"type": "wheel", "x": 0.5, "y": 0.3, "deltaY": -3}
          Combo: {"type": "combo", "modifiers": ["ControlLeft","AltLeft"], "keys": ["Delete"]}
        """
        msg_type = data.get("type")

        if msg_type == "keydown":
            await self.keyboard.key_down(data.get("code", ""))
        elif msg_type == "keyup":
            await self.keyboard.key_up(data.get("code", ""))
        elif msg_type == "mousemove":
            await self.mouse.move(data.get("x", 0), data.get("y", 0))
        elif msg_type == "mousedown":
            await self.mouse.button_down(
                data.get("x", 0), data.get("y", 0), data.get("button", 0)
            )
        elif msg_type == "mouseup":
            await self.mouse.button_up(
                data.get("x", 0), data.get("y", 0), data.get("button", 0)
            )
        elif msg_type == "click":
            await self.mouse.click(
                data.get("x", 0), data.get("y", 0), data.get("button", 0)
            )
        elif msg_type == "wheel":
            await self.mouse.scroll(
                data.get("x", 0), data.get("y", 0),
                data.get("deltaY", 0), data.get("deltaX", 0)
            )
        elif msg_type == "combo":
            await self.keyboard.send_combo(
                data.get("modifiers", []), data.get("keys", [])
            )
        elif msg_type == "releaseall":
            await self.keyboard.release_all()

    def get_status(self) -> dict:
        return {
            "keyboard": {
                "available": self.keyboard.is_available,
                "device": self.keyboard.device,
            },
            "mouse": {
                "available": self.mouse.is_available,
                "device": self.mouse.device,
            },
        }
