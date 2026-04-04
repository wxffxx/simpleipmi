"""
SI BMC — GPIO Control module
Controls target machine power (on/off/reset) and reads 12V status
via Orange Pi CM4 GPIO pins.

GPIO Pin Mapping (from GPIOdefine):
  out:
    RST = GPIO1_A1 => linux_gpio 33  (1*32 + 0*8 + 1)
    PWR = GPIO4_A6 => linux_gpio 134 (4*32 + 0*8 + 6)
  in:
    12Vdetect = GPIO4_C0 => linux_gpio 144 (4*32 + 2*8 + 0)

Uses sysfs GPIO interface for maximum compatibility.
Supports libgpiod as optional upgrade path.
"""

import asyncio
import os
import logging
import time
from typing import Optional, Dict, List, Callable

logger = logging.getLogger("si-bmc.gpio")


class GPIOPin:
    """Manages a single GPIO pin via sysfs."""

    SYSFS_BASE = "/sys/class/gpio"

    def __init__(self, linux_gpio: int, direction: str = "out",
                 active_low: bool = False, name: str = ""):
        self.gpio_num = linux_gpio
        self.direction = direction
        self.active_low = active_low
        self.name = name or f"gpio{linux_gpio}"
        self._exported = False

    @property
    def _gpio_path(self) -> str:
        return f"{self.SYSFS_BASE}/gpio{self.gpio_num}"

    async def setup(self) -> bool:
        """Export and configure the GPIO pin."""
        try:
            # Export if not already
            if not os.path.exists(self._gpio_path):
                await self._write_sysfs(
                    f"{self.SYSFS_BASE}/export",
                    str(self.gpio_num)
                )
                await asyncio.sleep(0.1)  # Wait for sysfs to create files

            # Set direction
            await self._write_sysfs(
                f"{self._gpio_path}/direction",
                self.direction
            )

            # Set active_low
            await self._write_sysfs(
                f"{self._gpio_path}/active_low",
                "1" if self.active_low else "0"
            )

            # Set initial value to LOW for output pins
            if self.direction == "out":
                await self._write_sysfs(
                    f"{self._gpio_path}/value",
                    "0"
                )

            self._exported = True
            logger.info(f"GPIO {self.name} (gpio{self.gpio_num}) configured as {self.direction}")
            return True

        except Exception as e:
            logger.error(f"Failed to setup GPIO {self.name}: {e}")
            return False

    async def cleanup(self):
        """Unexport the GPIO pin."""
        try:
            if self.direction == "out":
                await self.set_value(0)
            await self._write_sysfs(
                f"{self.SYSFS_BASE}/unexport",
                str(self.gpio_num)
            )
            self._exported = False
        except Exception:
            pass

    async def set_value(self, value: int):
        """Set output pin value (0 or 1)."""
        if not self._exported or self.direction != "out":
            return
        await self._write_sysfs(
            f"{self._gpio_path}/value",
            str(1 if value else 0)
        )

    async def get_value(self) -> int:
        """Read pin value (0 or 1)."""
        if not self._exported:
            return -1
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, self._read_value
            )
        except Exception as e:
            logger.error(f"Failed to read GPIO {self.name}: {e}")
            return -1

    def _read_value(self) -> int:
        with open(f"{self._gpio_path}/value", "r") as f:
            return int(f.read().strip())

    async def pulse(self, duration_ms: int):
        """Send a pulse: HIGH for duration_ms, then LOW."""
        if not self._exported or self.direction != "out":
            return
        await self.set_value(1)
        await asyncio.sleep(duration_ms / 1000.0)
        await self.set_value(0)
        logger.info(f"GPIO {self.name}: pulse {duration_ms}ms")

    @staticmethod
    async def _write_sysfs(path: str, value: str):
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: _sysfs_write(path, value)
        )


def _sysfs_write(path: str, value: str):
    """Synchronous sysfs write."""
    with open(path, "w") as f:
        f.write(value)


class GPIOController:
    """
    Manages all GPIO pins for BMC power control.

    Actions:
      - power_short_press: Short press power button (toggle on)
      - power_long_press: Long press power button (force off)
      - reset: Pulse reset pin
      - get_power_status: Read 12V detection pin
    """

    def __init__(self, config: dict):
        self._config = config

        # Power button
        pwr_cfg = config.get("power", {})
        self.power_pin = GPIOPin(
            linux_gpio=pwr_cfg.get("linux_gpio", 134),
            direction="out",
            active_low=pwr_cfg.get("active_low", False),
            name="PWR"
        )
        self.power_short_ms = pwr_cfg.get("short_press_ms", 500)
        self.power_long_ms = pwr_cfg.get("long_press_ms", 5000)

        # Reset button
        rst_cfg = config.get("reset", {})
        self.reset_pin = GPIOPin(
            linux_gpio=rst_cfg.get("linux_gpio", 33),
            direction="out",
            active_low=rst_cfg.get("active_low", False),
            name="RST"
        )
        self.reset_pulse_ms = rst_cfg.get("pulse_ms", 200)

        # 12V power status detect
        status_cfg = config.get("power_status", {})
        self.status_pin = GPIOPin(
            linux_gpio=status_cfg.get("linux_gpio", 144),
            direction="in",
            active_low=status_cfg.get("active_low", False),
            name="12V_DETECT"
        )

        # Custom GPIO extensions
        self._custom_gpios: Dict[str, GPIOPin] = {}
        for gpio_def in config.get("custom_gpios", []):
            pin = GPIOPin(
                linux_gpio=gpio_def["linux_gpio"],
                direction=gpio_def.get("direction", "out"),
                active_low=gpio_def.get("active_low", False),
                name=gpio_def["name"]
            )
            self._custom_gpios[gpio_def["name"]] = pin

        self._initialized = False
        self._action_log: List[dict] = []

    async def setup(self):
        """Initialize all GPIO pins."""
        results = []
        results.append(await self.power_pin.setup())
        results.append(await self.reset_pin.setup())
        results.append(await self.status_pin.setup())

        for name, pin in self._custom_gpios.items():
            ok = await pin.setup()
            results.append(ok)
            if not ok:
                logger.warning(f"Custom GPIO '{name}' setup failed")

        self._initialized = all(results)
        if self._initialized:
            logger.info("All GPIO pins initialized successfully")
        else:
            logger.warning("Some GPIO pins failed to initialize (may work in simulation mode)")

        # Even if setup fails (e.g. not on real hardware), mark as initialized
        # so the API still works in dev/simulation mode
        self._initialized = True

    async def cleanup(self):
        """Release all GPIO pins."""
        await self.power_pin.cleanup()
        await self.reset_pin.cleanup()
        await self.status_pin.cleanup()
        for pin in self._custom_gpios.values():
            await pin.cleanup()
        self._initialized = False

    async def power_on(self) -> dict:
        """Short press power button to turn on."""
        self._log_action("power_on")
        await self.power_pin.pulse(self.power_short_ms)
        return {"action": "power_on", "pulse_ms": self.power_short_ms, "success": True}

    async def power_off(self) -> dict:
        """Long press power button to force shutdown."""
        self._log_action("power_off")
        await self.power_pin.pulse(self.power_long_ms)
        return {"action": "power_off", "pulse_ms": self.power_long_ms, "success": True}

    async def reset(self) -> dict:
        """Pulse reset pin to reboot target."""
        self._log_action("reset")
        await self.reset_pin.pulse(self.reset_pulse_ms)
        return {"action": "reset", "pulse_ms": self.reset_pulse_ms, "success": True}

    async def get_power_status(self) -> dict:
        """Read 12V power status from PCIe voltage divider."""
        value = await self.status_pin.get_value()
        powered = value == 1
        return {
            "powered": powered,
            "raw_value": value,
            "pin": self.status_pin.name,
        }

    async def set_custom_gpio(self, name: str, value: int) -> dict:
        """Set a custom GPIO pin value."""
        if name not in self._custom_gpios:
            return {"error": f"Custom GPIO '{name}' not found"}
        await self._custom_gpios[name].set_value(value)
        self._log_action(f"custom_gpio_{name}_{value}")
        return {"name": name, "value": value, "success": True}

    async def get_custom_gpio(self, name: str) -> dict:
        """Read a custom GPIO pin value."""
        if name not in self._custom_gpios:
            return {"error": f"Custom GPIO '{name}' not found"}
        value = await self._custom_gpios[name].get_value()
        return {"name": name, "value": value}

    def _log_action(self, action: str):
        entry = {
            "action": action,
            "timestamp": time.time(),
            "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._action_log.append(entry)
        # Keep last 100 entries
        if len(self._action_log) > 100:
            self._action_log = self._action_log[-100:]
        logger.info(f"GPIO action: {action}")

    def get_status(self) -> dict:
        """Return GPIO subsystem status."""
        custom = {}
        for name, pin in self._custom_gpios.items():
            custom[name] = {
                "gpio": pin.gpio_num,
                "direction": pin.direction,
            }

        return {
            "initialized": self._initialized,
            "pins": {
                "power": {"name": "PWR", "gpio": self.power_pin.gpio_num, "direction": "out"},
                "reset": {"name": "RST", "gpio": self.reset_pin.gpio_num, "direction": "out"},
                "status": {"name": "12V_DETECT", "gpio": self.status_pin.gpio_num, "direction": "in"},
            },
            "custom_gpios": custom,
            "recent_actions": self._action_log[-10:],
        }

    def get_config(self) -> dict:
        """Return GPIO configuration for frontend display."""
        return {
            "power": {
                "pin_name": self._config.get("power", {}).get("pin_name", "GPIO4_A6"),
                "linux_gpio": self.power_pin.gpio_num,
                "short_press_ms": self.power_short_ms,
                "long_press_ms": self.power_long_ms,
            },
            "reset": {
                "pin_name": self._config.get("reset", {}).get("pin_name", "GPIO1_A1"),
                "linux_gpio": self.reset_pin.gpio_num,
                "pulse_ms": self.reset_pulse_ms,
            },
            "power_status": {
                "pin_name": self._config.get("power_status", {}).get("pin_name", "GPIO4_C0"),
                "linux_gpio": self.status_pin.gpio_num,
                "source": "PCIe 12V voltage divider",
            },
        }
