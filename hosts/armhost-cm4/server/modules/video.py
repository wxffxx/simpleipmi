"""
SI BMC — Video capture module
Captures MJPEG frames from MS2109 USB capture card via V4L2/OpenCV
and serves as an async MJPEG stream for the web frontend.
"""

import asyncio
import cv2
import time
import logging
from typing import AsyncGenerator, Optional

logger = logging.getLogger("si-bmc.video")


class VideoCapture:
    """Manages MS2109 video capture card and provides MJPEG streaming."""

    def __init__(self, config: dict):
        self.device = config.get("device", "/dev/video0")
        self.width = config.get("width", 1920)
        self.height = config.get("height", 1080)
        self.fps = config.get("fps", 30)
        self.jpeg_quality = config.get("jpeg_quality", 85)
        self.fallback_width = config.get("fallback_width", 1280)
        self.fallback_height = config.get("fallback_height", 720)
        self.fallback_fps = config.get("fallback_fps", 30)
        self.reconnect_interval = config.get("reconnect_interval", 3)

        self._cap: Optional[cv2.VideoCapture] = None
        self._lock = asyncio.Lock()
        self._running = False
        self._frame: Optional[bytes] = None
        self._frame_event = asyncio.Event()
        self._frame_count = 0
        self._fps_actual = 0.0
        self._last_fps_time = time.time()
        self._connected = False
        self._current_width = 0
        self._current_height = 0

    def _open_device(self) -> bool:
        """Open the video capture device with V4L2 backend."""
        try:
            if self._cap is not None:
                self._cap.release()

            self._cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
            if not self._cap.isOpened():
                logger.error(f"Failed to open video device: {self.device}")
                self._connected = False
                return False

            # Set MJPEG format (hardware-compressed by MS2109)
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            self._cap.set(cv2.CAP_PROP_FOURCC, fourcc)

            # Try primary resolution
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self._cap.set(cv2.CAP_PROP_FPS, self.fps)

            # Verify actual resolution
            actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            if actual_w != self.width or actual_h != self.height:
                logger.warning(
                    f"Requested {self.width}x{self.height} but got {actual_w}x{actual_h}, "
                    f"trying fallback {self.fallback_width}x{self.fallback_height}"
                )
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.fallback_width)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.fallback_height)
                self._cap.set(cv2.CAP_PROP_FPS, self.fallback_fps)
                actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            self._current_width = actual_w
            self._current_height = actual_h
            self._connected = True
            logger.info(f"Video device opened: {self.device} @ {actual_w}x{actual_h}")
            return True

        except Exception as e:
            logger.error(f"Error opening video device: {e}")
            self._connected = False
            return False

    async def start(self):
        """Start the video capture loop in background."""
        self._running = True
        asyncio.create_task(self._capture_loop())
        logger.info("Video capture started")

    async def stop(self):
        """Stop the video capture."""
        self._running = False
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._connected = False
        logger.info("Video capture stopped")

    async def _capture_loop(self):
        """Background loop that continuously grabs frames."""
        while self._running:
            if not self._connected:
                ok = await asyncio.get_event_loop().run_in_executor(
                    None, self._open_device
                )
                if not ok:
                    await asyncio.sleep(self.reconnect_interval)
                    continue

            try:
                ret, frame = await asyncio.get_event_loop().run_in_executor(
                    None, self._cap.read
                )
                if not ret or frame is None:
                    logger.warning("Failed to read frame, reconnecting...")
                    self._connected = False
                    continue

                # Encode to JPEG
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
                ret, buffer = cv2.imencode('.jpg', frame, encode_params)
                if ret:
                    self._frame = buffer.tobytes()
                    self._frame_event.set()
                    self._frame_event.clear()

                    # FPS calculation
                    self._frame_count += 1
                    now = time.time()
                    elapsed = now - self._last_fps_time
                    if elapsed >= 1.0:
                        self._fps_actual = self._frame_count / elapsed
                        self._frame_count = 0
                        self._last_fps_time = now

                # Slight yield to event loop
                await asyncio.sleep(0.001)

            except Exception as e:
                logger.error(f"Capture error: {e}")
                self._connected = False
                await asyncio.sleep(self.reconnect_interval)

    async def mjpeg_stream(self) -> AsyncGenerator[bytes, None]:
        """
        Async generator yielding MJPEG multipart frames.
        Used directly as a StreamingResponse body.
        """
        while self._running:
            if self._frame is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + self._frame
                    + b"\r\n"
                )
            # Target ~30fps = ~33ms per frame
            await asyncio.sleep(0.033)

    async def get_snapshot(self) -> Optional[bytes]:
        """Return a single JPEG frame."""
        return self._frame

    def get_status(self) -> dict:
        """Return current video capture status."""
        return {
            "connected": self._connected,
            "device": self.device,
            "resolution": f"{self._current_width}x{self._current_height}" if self._connected else "N/A",
            "width": self._current_width,
            "height": self._current_height,
            "fps_target": self.fps,
            "fps_actual": round(self._fps_actual, 1),
            "jpeg_quality": self.jpeg_quality,
        }

    async def set_quality(self, quality: int):
        """Dynamically adjust JPEG quality (1-100)."""
        self.jpeg_quality = max(1, min(100, quality))
        logger.info(f"JPEG quality set to {self.jpeg_quality}")
