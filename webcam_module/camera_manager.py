"""
Camera Manager
Advanced webcam control with multiple camera support and optimal settings
"""

import cv2
import numpy as np
from typing import Optional, List, Dict, Tuple, Callable
import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CameraCapability(Enum):
    """Camera capability flags"""
    AUTOFOCUS = "autofocus"
    AUTO_EXPOSURE = "auto_exposure"
    MANUAL_FOCUS = "manual_focus"
    MANUAL_EXPOSURE = "manual_exposure"
    WHITE_BALANCE = "white_balance"
    ZOOM = "zoom"
    PAN_TILT = "pan_tilt"


@dataclass
class CameraInfo:
    """Camera information"""
    index: int
    name: str
    max_resolution: Tuple[int, int]
    capabilities: List[CameraCapability]
    is_available: bool


class CameraManager:
    """
    Advanced Camera Manager

    Features:
    - Multi-camera support with auto-detection
    - Optimal resolution selection
    - Auto-focus and exposure control
    - Frame buffering for smooth capture
    - Background capture thread
    """

    # Preferred resolutions in order of preference
    PREFERRED_RESOLUTIONS = [
        (3840, 2160),  # 4K
        (2560, 1440),  # 2K
        (1920, 1080),  # Full HD
        (1280, 720),   # HD
        (640, 480)     # VGA fallback
    ]

    def __init__(
        self,
        camera_index: int = 0,
        resolution: Tuple[int, int] = (1920, 1080),
        fps: int = 30,
        buffer_size: int = 5
    ):
        self.camera_index = camera_index
        self.requested_resolution = resolution
        self.fps = fps
        self.buffer_size = buffer_size

        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.actual_resolution = (0, 0)

        # Frame buffer for smooth capture
        self._frame_buffer: List[np.ndarray] = []
        self._buffer_lock = threading.Lock()
        self._capture_thread: Optional[threading.Thread] = None

        # Callbacks
        self._frame_callbacks: List[Callable] = []

        # Stats
        self.frames_captured = 0
        self.last_frame_time = 0
        self.actual_fps = 0

    def start(self, use_threading: bool = True) -> bool:
        """
        Start camera capture

        Args:
            use_threading: Use background thread for capture

        Returns:
            True if successful
        """
        if self.is_running:
            return True

        try:
            # Open camera
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)  # DirectShow on Windows

            if not self.cap.isOpened():
                # Try without DirectShow
                self.cap = cv2.VideoCapture(self.camera_index)

            if not self.cap.isOpened():
                logger.error(f"Failed to open camera {self.camera_index}")
                return False

            # Set optimal resolution
            self._set_resolution(self.requested_resolution)

            # Configure camera settings
            self._configure_camera()

            # Get actual resolution
            self.actual_resolution = (
                int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            )

            logger.info(f"Camera opened: {self.actual_resolution[0]}x{self.actual_resolution[1]}")

            self.is_running = True

            # Start capture thread if requested
            if use_threading:
                self._start_capture_thread()

            return True

        except Exception as e:
            logger.error(f"Camera start error: {e}")
            return False

    def stop(self):
        """Stop camera capture"""
        self.is_running = False

        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None

        if self.cap:
            self.cap.release()
            self.cap = None

        with self._buffer_lock:
            self._frame_buffer.clear()

        logger.info("Camera stopped")

    def get_frame(self) -> Optional[np.ndarray]:
        """
        Get current frame

        Returns:
            Frame as numpy array or None
        """
        if not self.is_running:
            return None

        # Try buffer first
        with self._buffer_lock:
            if self._frame_buffer:
                return self._frame_buffer[-1].copy()

        # Direct capture if no buffered frames
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return frame

        return None

    def capture_high_quality(self) -> Optional[np.ndarray]:
        """
        Capture high-quality frame with averaging for noise reduction

        Returns:
            Averaged frame from multiple captures
        """
        if not self.is_running:
            return None

        frames = []
        for _ in range(3):  # Capture 3 frames
            if self.cap:
                ret, frame = self.cap.read()
                if ret:
                    frames.append(frame.astype(np.float32))
            time.sleep(0.05)  # 50ms between captures

        if not frames:
            return None

        # Average frames for noise reduction
        averaged = np.mean(frames, axis=0).astype(np.uint8)
        return averaged

    def _set_resolution(self, resolution: Tuple[int, int]):
        """Set camera resolution"""
        if not self.cap:
            return

        # Try requested resolution first
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

        # Verify
        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if (actual_w, actual_h) != resolution:
            logger.warning(f"Requested {resolution}, got ({actual_w}, {actual_h})")

            # Try preferred resolutions
            for res in self.PREFERRED_RESOLUTIONS:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, res[0])
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, res[1])
                actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                if actual_w >= res[0] * 0.9:  # Within 90% of requested
                    break

    def _configure_camera(self):
        """Configure camera for optimal quality"""
        if not self.cap:
            return

        # Set FPS
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

        # Enable autofocus
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)

        # Enable auto exposure
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)

        # Set buffer size (minimize latency)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)

        # Set fourcc for better quality
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        self.cap.set(cv2.CAP_PROP_FOURCC, fourcc)

        # Brightness and contrast (auto is usually best)
        # self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 128)
        # self.cap.set(cv2.CAP_PROP_CONTRAST, 128)

    def _start_capture_thread(self):
        """Start background capture thread"""
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True
        )
        self._capture_thread.start()

    def _capture_loop(self):
        """Background capture loop"""
        frame_interval = 1.0 / self.fps

        while self.is_running:
            start_time = time.time()

            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()

                if ret:
                    # Add to buffer
                    with self._buffer_lock:
                        self._frame_buffer.append(frame)
                        # Keep buffer size limited
                        while len(self._frame_buffer) > self.buffer_size:
                            self._frame_buffer.pop(0)

                    # Update stats
                    self.frames_captured += 1
                    if self.last_frame_time > 0:
                        self.actual_fps = 1.0 / (start_time - self.last_frame_time)
                    self.last_frame_time = start_time

                    # Call registered callbacks
                    for callback in self._frame_callbacks:
                        try:
                            callback(frame)
                        except Exception as e:
                            logger.error(f"Frame callback error: {e}")

            # Maintain frame rate
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def add_frame_callback(self, callback: Callable):
        """Add callback for new frames"""
        self._frame_callbacks.append(callback)

    def remove_frame_callback(self, callback: Callable):
        """Remove frame callback"""
        if callback in self._frame_callbacks:
            self._frame_callbacks.remove(callback)

    def set_manual_focus(self, focus_value: int):
        """Set manual focus (0-255)"""
        if self.cap:
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            self.cap.set(cv2.CAP_PROP_FOCUS, focus_value)

    def set_autofocus(self):
        """Enable autofocus"""
        if self.cap:
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)

    def set_exposure(self, exposure_value: int):
        """Set manual exposure"""
        if self.cap:
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0)
            self.cap.set(cv2.CAP_PROP_EXPOSURE, exposure_value)

    def set_auto_exposure(self):
        """Enable auto exposure"""
        if self.cap:
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)

    def get_camera_info(self) -> Dict:
        """Get current camera information"""
        if not self.cap:
            return {}

        return {
            'index': self.camera_index,
            'resolution': self.actual_resolution,
            'fps': self.actual_fps,
            'frames_captured': self.frames_captured,
            'is_running': self.is_running,
            'backend': self.cap.getBackendName() if self.cap else None
        }

    @staticmethod
    def get_available_cameras() -> List[CameraInfo]:
        """
        Detect all available cameras

        Returns:
            List of CameraInfo objects
        """
        cameras = []

        for i in range(10):  # Check first 10 indices
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                # Get max resolution
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 9999)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 9999)
                max_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                max_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                # Check capabilities
                capabilities = []
                if cap.get(cv2.CAP_PROP_AUTOFOCUS) >= 0:
                    capabilities.append(CameraCapability.AUTOFOCUS)
                if cap.get(cv2.CAP_PROP_AUTO_EXPOSURE) >= 0:
                    capabilities.append(CameraCapability.AUTO_EXPOSURE)

                cameras.append(CameraInfo(
                    index=i,
                    name=f"Camera {i}",
                    max_resolution=(max_w, max_h),
                    capabilities=capabilities,
                    is_available=True
                ))

                cap.release()

        return cameras

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


# Convenience function
def get_best_camera() -> int:
    """Get index of best available camera (highest resolution)"""
    cameras = CameraManager.get_available_cameras()
    if not cameras:
        return 0

    # Sort by resolution
    cameras.sort(key=lambda c: c.max_resolution[0] * c.max_resolution[1], reverse=True)
    return cameras[0].index
