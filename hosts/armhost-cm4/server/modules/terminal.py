"""
SI BMC — Web Terminal Module
Provides a PTY-based terminal via WebSocket for browser console access.
"""

import os
import pty
import select
import subprocess
import struct
import fcntl
import termios
import asyncio
import logging
from typing import Optional

logger = logging.getLogger("si-bmc.terminal")


class WebTerminal:
    """Manages a PTY subprocess for web terminal sessions."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.shell = self.config.get("shell", "/bin/bash")
        self.sessions = {}  # session_id -> TerminalSession
        self.max_sessions = self.config.get("max_sessions", 5)

    def create_session(self, session_id: str, cols: int = 120, rows: int = 40) -> bool:
        """Create a new terminal session with a PTY."""
        if session_id in self.sessions:
            logger.warning(f"Session {session_id} already exists")
            return True

        if len(self.sessions) >= self.max_sessions:
            logger.error(f"Max sessions ({self.max_sessions}) reached")
            return False

        try:
            # Create PTY
            master_fd, slave_fd = pty.openpty()

            # Set terminal size
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

            # Spawn shell
            env = os.environ.copy()
            env["TERM"] = "xterm-256color"
            env["COLUMNS"] = str(cols)
            env["LINES"] = str(rows)

            process = subprocess.Popen(
                [self.shell, "--login"],
                preexec_fn=os.setsid,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=env,
                close_fds=True,
            )

            os.close(slave_fd)  # Parent doesn't need the slave

            # Set master to non-blocking
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            self.sessions[session_id] = TerminalSession(
                session_id=session_id,
                master_fd=master_fd,
                process=process,
                cols=cols,
                rows=rows,
            )

            logger.info(f"Terminal session created: {session_id} ({cols}x{rows})")
            return True

        except Exception as e:
            logger.error(f"Failed to create terminal session: {e}")
            return False

    def write(self, session_id: str, data: str) -> bool:
        """Write data (user input) to the terminal."""
        session = self.sessions.get(session_id)
        if not session:
            return False

        try:
            os.write(session.master_fd, data.encode("utf-8"))
            return True
        except (OSError, IOError):
            return False

    def read(self, session_id: str, max_bytes: int = 65536) -> Optional[str]:
        """Read available output from the terminal (non-blocking)."""
        session = self.sessions.get(session_id)
        if not session:
            return None

        try:
            ready, _, _ = select.select([session.master_fd], [], [], 0)
            if ready:
                data = os.read(session.master_fd, max_bytes)
                if data:
                    return data.decode("utf-8", errors="replace")
            return ""
        except (OSError, IOError):
            return None

    def resize(self, session_id: str, cols: int, rows: int) -> bool:
        """Resize the terminal."""
        session = self.sessions.get(session_id)
        if not session:
            return False

        try:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(session.master_fd, termios.TIOCSWINSZ, winsize)
            session.cols = cols
            session.rows = rows
            return True
        except (OSError, IOError):
            return False

    def close_session(self, session_id: str):
        """Close and clean up a terminal session."""
        session = self.sessions.pop(session_id, None)
        if not session:
            return

        try:
            os.close(session.master_fd)
        except OSError:
            pass

        try:
            session.process.terminate()
            session.process.wait(timeout=3)
        except Exception:
            try:
                session.process.kill()
            except Exception:
                pass

        logger.info(f"Terminal session closed: {session_id}")

    def is_alive(self, session_id: str) -> bool:
        """Check if a terminal session is still running."""
        session = self.sessions.get(session_id)
        if not session:
            return False
        return session.process.poll() is None

    def cleanup(self):
        """Close all terminal sessions."""
        for sid in list(self.sessions.keys()):
            self.close_session(sid)


class TerminalSession:
    """Represents a single terminal session."""

    def __init__(self, session_id: str, master_fd: int,
                 process: subprocess.Popen, cols: int, rows: int):
        self.session_id = session_id
        self.master_fd = master_fd
        self.process = process
        self.cols = cols
        self.rows = rows
