"""
SI BMC — System Information module
Collects Orange Pi CM4 system metrics for dashboard display.
"""

import asyncio
import os
import time
import logging
from typing import Optional

logger = logging.getLogger("si-bmc.sysinfo")


class SystemInfo:
    """Collects and caches system information."""

    def __init__(self):
        self._cache = {}
        self._cache_time = 0
        self._cache_ttl = 1.0  # Cache for 1 second

    async def get_all(self) -> dict:
        """Get all system information."""
        now = time.time()
        if now - self._cache_time < self._cache_ttl and self._cache:
            return self._cache

        info = await asyncio.get_event_loop().run_in_executor(
            None, self._collect_info
        )
        self._cache = info
        self._cache_time = now
        return info

    def _collect_info(self) -> dict:
        """Collect system info synchronously."""
        info = {
            "cpu": self._get_cpu_info(),
            "memory": self._get_memory_info(),
            "temperature": self._get_temperature(),
            "disk": self._get_disk_info(),
            "network": self._get_network_info(),
            "uptime": self._get_uptime(),
            "load": self._get_load_average(),
            "hostname": self._get_hostname(),
        }
        return info

    def _get_cpu_info(self) -> dict:
        try:
            import psutil
            cpu_pct = psutil.cpu_percent(interval=0)
            cpu_count = psutil.cpu_count()
            freq = psutil.cpu_freq()
            return {
                "usage_percent": cpu_pct,
                "cores": cpu_count,
                "freq_mhz": round(freq.current, 0) if freq else 0,
                "freq_max_mhz": round(freq.max, 0) if freq else 0,
            }
        except Exception:
            return self._get_cpu_info_fallback()

    def _get_cpu_info_fallback(self) -> dict:
        """Fallback CPU info from /proc."""
        try:
            with open("/proc/stat") as f:
                line = f.readline()
            parts = line.split()
            # Simplified CPU usage
            total = sum(int(x) for x in parts[1:])
            idle = int(parts[4])
            usage = round(100 * (1 - idle / total), 1) if total > 0 else 0

            cores = 0
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("processor"):
                        cores += 1

            return {"usage_percent": usage, "cores": cores, "freq_mhz": 0, "freq_max_mhz": 0}
        except Exception:
            return {"usage_percent": 0, "cores": 0, "freq_mhz": 0, "freq_max_mhz": 0}

    def _get_memory_info(self) -> dict:
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                "total_mb": round(mem.total / 1024 / 1024),
                "used_mb": round(mem.used / 1024 / 1024),
                "available_mb": round(mem.available / 1024 / 1024),
                "usage_percent": mem.percent,
            }
        except Exception:
            return self._get_memory_info_fallback()

    def _get_memory_info_fallback(self) -> dict:
        try:
            with open("/proc/meminfo") as f:
                lines = f.readlines()
            mem = {}
            for line in lines:
                parts = line.split()
                if parts[0] in ("MemTotal:", "MemFree:", "MemAvailable:"):
                    mem[parts[0].rstrip(":")] = int(parts[1])

            total = mem.get("MemTotal", 0)
            avail = mem.get("MemAvailable", 0)
            used = total - avail
            usage = round(100 * used / total, 1) if total > 0 else 0

            return {
                "total_mb": round(total / 1024),
                "used_mb": round(used / 1024),
                "available_mb": round(avail / 1024),
                "usage_percent": usage,
            }
        except Exception:
            return {"total_mb": 0, "used_mb": 0, "available_mb": 0, "usage_percent": 0}

    def _get_temperature(self) -> dict:
        """Read SoC temperature from thermal zone."""
        try:
            # Try RK3566 thermal zone
            for zone in range(5):
                path = f"/sys/class/thermal/thermal_zone{zone}/temp"
                if os.path.exists(path):
                    with open(path) as f:
                        temp = int(f.read().strip()) / 1000.0
                    return {"celsius": round(temp, 1), "source": f"thermal_zone{zone}"}

            # Try psutil as fallback
            import psutil
            temps = psutil.sensors_temperatures()
            for name, entries in temps.items():
                if entries:
                    return {"celsius": round(entries[0].current, 1), "source": name}

            return {"celsius": 0, "source": "unavailable"}
        except Exception:
            return {"celsius": 0, "source": "unavailable"}

    def _get_disk_info(self) -> dict:
        try:
            import psutil
            disk = psutil.disk_usage("/")
            return {
                "total_gb": round(disk.total / 1024 / 1024 / 1024, 1),
                "used_gb": round(disk.used / 1024 / 1024 / 1024, 1),
                "free_gb": round(disk.free / 1024 / 1024 / 1024, 1),
                "usage_percent": round(disk.percent, 1),
            }
        except Exception:
            return {"total_gb": 0, "used_gb": 0, "free_gb": 0, "usage_percent": 0}

    def _get_network_info(self) -> dict:
        """Get network interface information."""
        try:
            import psutil
            stats = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()
            io = psutil.net_io_counters(pernic=True)

            interfaces = {}
            for name in stats:
                if name == "lo":
                    continue
                iface = {"up": stats[name].isup, "speed": stats[name].speed}

                # Get IPv4 address
                if name in addrs:
                    for addr in addrs[name]:
                        if addr.family == 2:  # AF_INET
                            iface["ipv4"] = addr.address
                            break

                # Get traffic
                if name in io:
                    iface["bytes_sent"] = io[name].bytes_sent
                    iface["bytes_recv"] = io[name].bytes_recv

                interfaces[name] = iface

            return interfaces
        except Exception:
            return {}

    def _get_uptime(self) -> dict:
        try:
            with open("/proc/uptime") as f:
                uptime_sec = float(f.read().split()[0])
            days = int(uptime_sec // 86400)
            hours = int((uptime_sec % 86400) // 3600)
            minutes = int((uptime_sec % 3600) // 60)
            return {
                "seconds": round(uptime_sec),
                "formatted": f"{days}d {hours}h {minutes}m",
            }
        except Exception:
            return {"seconds": 0, "formatted": "N/A"}

    def _get_load_average(self) -> dict:
        try:
            load = os.getloadavg()
            return {
                "1min": round(load[0], 2),
                "5min": round(load[1], 2),
                "15min": round(load[2], 2),
            }
        except Exception:
            return {"1min": 0, "5min": 0, "15min": 0}

    def _get_hostname(self) -> str:
        try:
            import socket
            return socket.gethostname()
        except Exception:
            return "unknown"
