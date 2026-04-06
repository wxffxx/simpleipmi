"""
SI BMC — ESP32-S3 OTA Flasher module
Controls EN + GPIO0 pins to put ESP32-S3 into download mode,
then uses esptool.py to flash firmware via the existing UART connection.

Hardware requirements:
  - ARM GPIO → ESP32-S3 EN (with 10kΩ pull-up to 3.3V)
  - ARM GPIO → ESP32-S3 GPIO0 (with 10kΩ pull-up to 3.3V)

Flash sequence:
  1. Close HID serial connection
  2. Pull GPIO0 LOW (select download mode)
  3. Pull EN LOW then HIGH (reset ESP32-S3 into bootloader)
  4. Run esptool.py to flash firmware binary
  5. Release GPIO0 HIGH (normal boot mode)
  6. Pull EN LOW then HIGH (reset into application)
  7. Reopen HID serial connection
"""

import asyncio
import os
import shutil
import time
import logging
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger("si-bmc.flasher")

# GPIO control paths (Linux sysfs)
GPIO_EXPORT = "/sys/class/gpio/export"
GPIO_UNEXPORT = "/sys/class/gpio/unexport"
GPIO_BASE = "/sys/class/gpio/gpio{}"


class GPIOPin:
    """Minimal sysfs GPIO control for ESP32-S3 EN/GPIO0 pins."""

    def __init__(self, linux_gpio: int, name: str = ""):
        self.gpio_num = linux_gpio
        self.name = name
        self._exported = False

    def setup(self):
        """Export and configure GPIO as output, default HIGH."""
        gpio_dir = GPIO_BASE.format(self.gpio_num)
        try:
            if not os.path.exists(gpio_dir):
                with open(GPIO_EXPORT, 'w') as f:
                    f.write(str(self.gpio_num))
                # Wait for sysfs node to appear
                for _ in range(10):
                    if os.path.exists(gpio_dir):
                        break
                    time.sleep(0.05)

            # Set direction to output, default HIGH
            with open(os.path.join(gpio_dir, "direction"), 'w') as f:
                f.write("high")

            self._exported = True
            logger.debug(f"GPIO {self.name} ({self.gpio_num}) configured as output HIGH")
        except Exception as e:
            logger.error(f"Failed to setup GPIO {self.name} ({self.gpio_num}): {e}")
            raise

    def set_high(self):
        """Set GPIO output HIGH."""
        if not self._exported:
            return
        try:
            with open(os.path.join(GPIO_BASE.format(self.gpio_num), "value"), 'w') as f:
                f.write("1")
        except Exception as e:
            logger.error(f"GPIO {self.name} set HIGH failed: {e}")

    def set_low(self):
        """Set GPIO output LOW."""
        if not self._exported:
            return
        try:
            with open(os.path.join(GPIO_BASE.format(self.gpio_num), "value"), 'w') as f:
                f.write("0")
        except Exception as e:
            logger.error(f"GPIO {self.name} set LOW failed: {e}")

    def cleanup(self):
        """Set HIGH (safe default) and unexport."""
        if self._exported:
            self.set_high()
            try:
                with open(GPIO_UNEXPORT, 'w') as f:
                    f.write(str(self.gpio_num))
            except Exception:
                pass
            self._exported = False


class ESP32Flasher:
    """
    Manages OTA firmware flashing of ESP32-S3 via UART.

    Uses ARM GPIO pins to control ESP32-S3's EN and GPIO0 pins,
    putting it into serial download mode for esptool.py flashing.
    """

    # esptool default flash parameters for ESP32-S3
    CHIP_TYPE = "esp32s3"
    FLASH_MODE = "dio"
    FLASH_FREQ = "80m"
    FLASH_SIZE = "detect"
    BAUD_RATE = 921600  # Flash baud (faster than protocol baud)

    def __init__(self, config: dict):
        self._en_gpio = config.get("en_gpio", None)       # Linux GPIO number for EN
        self._boot_gpio = config.get("boot_gpio", None)    # Linux GPIO number for GPIO0
        self._serial_port = config.get("serial_port", None) # Will be set dynamically
        self._firmware_dir = config.get("firmware_dir", "/opt/si-bmc/firmware")

        self._en_pin: Optional[GPIOPin] = None
        self._boot_pin: Optional[GPIOPin] = None
        self._available = False
        self._flashing = False
        self._flash_progress = ""
        self._last_flash_result: Optional[dict] = None

        # Reference to HID manager (set externally before use)
        self._hid_manager = None

    def set_hid_manager(self, hid_manager):
        """Set reference to HID manager for connection management."""
        self._hid_manager = hid_manager

    def set_serial_port(self, port: str):
        """Update the serial port (called by HID manager when port changes)."""
        self._serial_port = port

    async def setup(self):
        """Initialize GPIO pins for EN and GPIO0 control."""
        if self._en_gpio is None or self._boot_gpio is None:
            logger.warning("ESP32 flasher: EN or BOOT GPIO not configured, OTA disabled")
            self._available = False
            return

        try:
            self._en_pin = GPIOPin(self._en_gpio, "ESP32_EN")
            self._boot_pin = GPIOPin(self._boot_gpio, "ESP32_BOOT")

            await asyncio.get_event_loop().run_in_executor(
                None, self._en_pin.setup)
            await asyncio.get_event_loop().run_in_executor(
                None, self._boot_pin.setup)

            # Check esptool is available
            esptool_path = shutil.which("esptool.py") or shutil.which("esptool")
            if esptool_path is None:
                # Try as python module
                try:
                    result = subprocess.run(
                        ["python3", "-m", "esptool", "version"],
                        capture_output=True, timeout=5
                    )
                    if result.returncode != 0:
                        raise FileNotFoundError
                except Exception:
                    logger.warning("esptool not found. Install with: pip install esptool")
                    self._available = False
                    return

            self._available = True
            # Ensure firmware directory exists
            os.makedirs(self._firmware_dir, exist_ok=True)
            logger.info(f"ESP32 flasher ready (EN=GPIO{self._en_gpio}, BOOT=GPIO{self._boot_gpio})")
        except Exception as e:
            logger.error(f"ESP32 flasher setup failed: {e}")
            self._available = False

    async def cleanup(self):
        """Release GPIO resources."""
        if self._en_pin:
            self._en_pin.cleanup()
        if self._boot_pin:
            self._boot_pin.cleanup()

    async def _enter_download_mode(self):
        """
        Put ESP32-S3 into serial download mode.

        Sequence (matches USB-Serial chip behavior):
          1. Hold GPIO0 LOW (select download mode)
          2. Pulse EN LOW→HIGH (reset chip)
          3. ESP32-S3 boots into ROM bootloader
        """
        logger.info("Entering ESP32-S3 download mode...")

        def _sequence():
            # Step 1: Pull GPIO0 LOW (boot mode = download)
            self._boot_pin.set_low()
            time.sleep(0.1)

            # Step 2: Reset pulse — EN LOW then HIGH
            self._en_pin.set_low()
            time.sleep(0.1)
            self._en_pin.set_high()

            # Step 3: Wait for bootloader to initialize
            time.sleep(0.5)

        await asyncio.get_event_loop().run_in_executor(None, _sequence)
        logger.info("ESP32-S3 should now be in download mode")

    async def _exit_download_mode(self):
        """
        Exit download mode and boot normally.

        Sequence:
          1. Release GPIO0 HIGH (normal boot mode)
          2. Pulse EN LOW→HIGH (reset into application)
        """
        logger.info("Resetting ESP32-S3 to normal mode...")

        def _sequence():
            # Step 1: Release GPIO0 (normal boot)
            self._boot_pin.set_high()
            time.sleep(0.1)

            # Step 2: Reset pulse
            self._en_pin.set_low()
            time.sleep(0.1)
            self._en_pin.set_high()

            # Step 3: Wait for application to start
            time.sleep(1.0)

        await asyncio.get_event_loop().run_in_executor(None, _sequence)
        logger.info("ESP32-S3 reset complete")

    async def flash_firmware(self, firmware_path: str) -> dict:
        """
        Flash a firmware binary to ESP32-S3.

        Args:
            firmware_path: Path to the .bin firmware file

        Returns:
            dict with "ok", "message", and optionally "error"
        """
        if not self._available:
            return {"ok": False, "error": "ESP32 flasher not available (check GPIO config)"}

        if self._flashing:
            return {"ok": False, "error": "Flash already in progress"}

        if not os.path.exists(firmware_path):
            return {"ok": False, "error": f"Firmware file not found: {firmware_path}"}

        if not self._serial_port:
            return {"ok": False, "error": "No serial port configured"}

        file_size = os.path.getsize(firmware_path)
        if file_size > 4 * 1024 * 1024:  # 4MB max
            return {"ok": False, "error": f"Firmware too large: {file_size} bytes (max 4MB)"}

        self._flashing = True
        self._flash_progress = "Starting..."

        try:
            # Step 1: Close HID serial connection
            self._flash_progress = "Closing HID connection..."
            if self._hid_manager:
                await self._hid_manager.stop()
            await asyncio.sleep(0.5)

            # Step 2: Enter download mode
            self._flash_progress = "Entering download mode..."
            await self._enter_download_mode()

            # Step 3: Run esptool.py
            self._flash_progress = "Flashing firmware..."
            result = await self._run_esptool(firmware_path)

            if result["ok"]:
                self._flash_progress = "Resetting ESP32-S3..."

                # Step 4: Exit download mode
                await self._exit_download_mode()

                # Step 5: Reopen HID connection
                self._flash_progress = "Reconnecting HID..."
                if self._hid_manager:
                    await self._hid_manager.start()

                self._flash_progress = "Complete!"
                result["message"] = f"Firmware flashed successfully ({file_size} bytes)"
            else:
                # Flash failed — still try to recover
                self._flash_progress = "Flash failed, recovering..."
                await self._exit_download_mode()
                if self._hid_manager:
                    await self._hid_manager.start()
                self._flash_progress = f"Failed: {result.get('error', 'unknown')}"

            self._last_flash_result = result
            return result

        except Exception as e:
            logger.error(f"Flash error: {e}")
            # Emergency recovery
            try:
                await self._exit_download_mode()
                if self._hid_manager:
                    await self._hid_manager.start()
            except Exception:
                pass
            self._flash_progress = f"Error: {e}"
            return {"ok": False, "error": str(e)}
        finally:
            self._flashing = False

    async def _run_esptool(self, firmware_path: str) -> dict:
        """Execute esptool.py to flash the firmware."""
        cmd = [
            "python3", "-m", "esptool",
            "--chip", self.CHIP_TYPE,
            "--port", self._serial_port,
            "--baud", str(self.BAUD_RATE),
            "--before", "no_reset",      # We handle reset via GPIO
            "--after", "no_reset",       # We handle reset via GPIO
            "write_flash",
            "--flash_mode", self.FLASH_MODE,
            "--flash_freq", self.FLASH_FREQ,
            "--flash_size", self.FLASH_SIZE,
            "0x0", firmware_path,
        ]

        logger.info(f"Running: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            output_lines = []
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded = line.decode('utf-8', errors='replace').strip()
                output_lines.append(decoded)
                logger.info(f"esptool: {decoded}")

                # Update progress from esptool output
                if "Connecting" in decoded:
                    self._flash_progress = "Connecting to bootloader..."
                elif "Chip is" in decoded:
                    self._flash_progress = f"Connected: {decoded}"
                elif "Writing" in decoded and "%" in decoded:
                    self._flash_progress = decoded
                elif "Hash of data verified" in decoded:
                    self._flash_progress = "Verifying..."

            returncode = await process.wait()

            if returncode == 0:
                return {"ok": True, "output": output_lines}
            else:
                return {
                    "ok": False,
                    "error": f"esptool exited with code {returncode}",
                    "output": output_lines,
                }

        except FileNotFoundError:
            return {"ok": False, "error": "esptool not found. Install with: pip install esptool"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def reset_esp32(self) -> dict:
        """Reset ESP32-S3 without flashing (just EN pulse)."""
        if not self._available:
            return {"ok": False, "error": "Flasher not available"}

        if self._hid_manager:
            await self._hid_manager.stop()

        def _reset():
            self._en_pin.set_low()
            time.sleep(0.1)
            self._en_pin.set_high()
            time.sleep(1.0)

        await asyncio.get_event_loop().run_in_executor(None, _reset)

        if self._hid_manager:
            await self._hid_manager.start()

        return {"ok": True, "message": "ESP32-S3 reset complete"}

    def get_status(self) -> dict:
        """Get flasher status."""
        return {
            "available": self._available,
            "flashing": self._flashing,
            "progress": self._flash_progress,
            "en_gpio": self._en_gpio,
            "boot_gpio": self._boot_gpio,
            "serial_port": self._serial_port,
            "last_result": self._last_flash_result,
        }
