"""
SSH Channel Manager — Remote shell access to Ubuntu target machines.

Provides:
  - SSH connection management (asyncssh)
  - Command execution
  - File transfer (SFTP)
  - Connection health monitoring
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger("cortex.channels.ssh")


class SSHChannelManager:
    """
    Manages SSH connection to the target Ubuntu machine.

    Usage:
        ssh = SSHChannelManager({"ip": "192.168.1.100", "username": "ubuntu"})
        await ssh.connect()
        output = await ssh.run("uname -a")
        await ssh.close()
    """

    def __init__(self, config: dict):
        self.target_ip = config.get("ip", "")
        self.port = config.get("port", 22)
        self.username = config.get("username", "root")
        self.key_file = config.get("key_file")
        self.password = config.get("password")
        self.client = None
        self._connect_lock = asyncio.Lock()

    async def connect(self, timeout: int = 10) -> bool:
        """
        Establish SSH connection to target machine.
        Returns True on success, False on failure.
        """
        if not self.target_ip:
            logger.warning("SSH: No target IP configured")
            return False

        async with self._connect_lock:
            try:
                import asyncssh

                connect_kwargs = {
                    "host": self.target_ip,
                    "port": self.port,
                    "username": self.username,
                    "known_hosts": None,  # Accept any host key (KVM scenario)
                    "connect_timeout": timeout,
                }

                if self.key_file:
                    connect_kwargs["client_keys"] = [self.key_file]
                if self.password:
                    connect_kwargs["password"] = self.password

                self.client = await asyncssh.connect(**connect_kwargs)
                logger.info(f"SSH connected to {self.username}@{self.target_ip}:{self.port}")
                return True

            except ImportError:
                logger.error("asyncssh not installed. Run: pip install asyncssh")
                return False
            except Exception as e:
                logger.warning(f"SSH connection failed: {e}")
                self.client = None
                return False

    async def run(self, command: str, timeout: int = 30) -> str:
        """
        Execute a command on the target machine via SSH.
        Returns stdout as string.
        Raises ConnectionError if not connected.
        """
        if not self.has_shell:
            raise ConnectionError("SSH not connected")

        try:
            result = await asyncio.wait_for(
                self.client.run(command),
                timeout=timeout,
            )
            return result.stdout or ""
        except asyncio.TimeoutError:
            raise TimeoutError(f"SSH command timed out after {timeout}s: {command}")
        except Exception as e:
            # Connection might have dropped
            logger.error(f"SSH command failed: {e}")
            self.client = None
            raise

    async def run_check(self, command: str, timeout: int = 30) -> tuple[bool, str]:
        """
        Execute a command and return (success, output).
        success = True if exit code is 0.
        Never raises — returns (False, error_msg) on failure.
        """
        try:
            if not self.has_shell:
                return False, "SSH not connected"

            result = await asyncio.wait_for(
                self.client.run(command),
                timeout=timeout,
            )
            success = result.exit_status == 0
            output = result.stdout or result.stderr or ""
            return success, output.strip()
        except Exception as e:
            return False, str(e)

    async def upload(self, local_path: str, remote_path: str) -> None:
        """Upload a file to the target machine via SFTP."""
        if not self.has_shell:
            raise ConnectionError("SSH not connected")

        async with self.client.start_sftp_client() as sftp:
            await sftp.put(local_path, remote_path)
            logger.info(f"Uploaded {local_path} → {remote_path}")

    async def download(self, remote_path: str, local_path: str) -> None:
        """Download a file from the target machine via SFTP."""
        if not self.has_shell:
            raise ConnectionError("SSH not connected")

        async with self.client.start_sftp_client() as sftp:
            await sftp.get(remote_path, local_path)
            logger.info(f"Downloaded {remote_path} → {local_path}")

    @property
    def has_shell(self) -> bool:
        """Whether SSH connection is active."""
        if self.client is None:
            return False
        # asyncssh: is_closed() is a METHOD, not a property
        try:
            return not self.client.is_closed()
        except TypeError:
            # Fallback: some versions may use it as property
            return not self.client.is_closed

    async def ensure_connected(self) -> bool:
        """Connect if not already connected. Returns True if connected."""
        if self.has_shell:
            # Quick health check
            try:
                await self.run("echo ok", timeout=5)
                return True
            except Exception:
                self.client = None

        return await self.connect()

    async def close(self) -> None:
        """Close SSH connection."""
        if self.client:
            self.client.close()
            await self.client.wait_closed()
            self.client = None
            logger.info("SSH connection closed")

    def get_status(self) -> dict:
        """Get connection status."""
        return {
            "connected": self.has_shell,
            "target": f"{self.username}@{self.target_ip}:{self.port}" if self.target_ip else "not configured",
        }
