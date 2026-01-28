"""
Auto-Capture System
Smart snapshot timing with stability detection and quality validation
"""

import cv2
import numpy as np
import time
from typing import Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path
from datetime import datetime

from .border_detector import ComicBorderDetector
from .quality_scorer import ImageQualityScorer
from .voice_feedback import VoiceFeedback

logger = logging.getLogger(__name__)


class CaptureState(Enum):
    """Capture state machine states"""
    NO_COMIC = "no_comic"
    POSITIONING = "positioning"
    STABILIZING = "stabilizing"
    QUALITY_CHECK = "quality_check"
    READY = "ready"
    CAPTURED = "captured"
    POOR_QUALITY = "poor_quality"


@dataclass
class CaptureResult:
    """Result of capture attempt"""
    success: bool
    state: CaptureState
    message: str
    image: Optional[np.ndarray] = None
    quality_score: Optional[Dict] = None
    detection: Optional[Dict] = None
    capture_metadata: Optional[Dict] = None


class AutoCaptureSystem:
    """
    Intelligent auto-capture system

    Features:
    - Comic detection and tracking
    - Stability detection
    - Quality validation
    - Voice feedback
    - Automatic capture timing
    - Front/back capture workflow
    """

    def __init__(
        self,
        output_dir: str = "P:/SOVEREIGN_APPS/collectibles_grading_system/images/captures",
        quality_threshold: float = 0.85,
        stability_frames: int = 8,
        voice_enabled: bool = True
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.quality_threshold = quality_threshold
        self.stability_frames_required = stability_frames
        self.voice_enabled = voice_enabled

        # Components
        self.border_detector = ComicBorderDetector()
        self.quality_scorer = ImageQualityScorer()
        self.voice = VoiceFeedback() if voice_enabled else None

        # State
        self.current_state = CaptureState.NO_COMIC
        self.stable_frame_count = 0
        self.last_detection: Optional[Dict] = None
        self.last_quality_check: Optional[Dict] = None

        # Capture workflow
        self.capture_mode = "front"  # "front" or "back"
        self.front_captured = False
        self.back_captured = False

        # Callbacks
        self._on_capture: Optional[Callable] = None
        self._on_state_change: Optional[Callable] = None

        # Timing
        self.last_voice_time = 0
        self.voice_cooldown = 2.0  # seconds

        # Session
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.captures_in_session = 0

    def process_frame(self, frame: np.ndarray) -> CaptureResult:
        """
        Process single frame through capture pipeline

        Args:
            frame: BGR image frame

        Returns:
            CaptureResult with state and data
        """
        # Detect comic
        detection = self.border_detector.detect_comic(frame)

        if not detection:
            return self._handle_no_detection(frame)

        # Check position quality
        if detection['confidence'] < 0.6:
            return self._handle_positioning(frame, detection)

        # Check stability
        if not self._check_stability(detection):
            return self._handle_stabilizing(frame, detection)

        # Quality check
        cropped = self.border_detector.get_cropped_comic(frame, detection)
        quality = self.quality_scorer.score_image(cropped)

        if not quality['passed']:
            return self._handle_poor_quality(frame, detection, quality)

        # Ready to capture
        return self._handle_ready(frame, detection, quality, cropped)

    def _handle_no_detection(self, frame: np.ndarray) -> CaptureResult:
        """Handle state when no comic detected"""
        self._transition_state(CaptureState.NO_COMIC)
        self.stable_frame_count = 0
        self.border_detector.reset_tracking()

        message = f"Position {self.capture_mode} cover in frame"
        self._speak_with_cooldown(message)

        return CaptureResult(
            success=False,
            state=CaptureState.NO_COMIC,
            message=message,
            detection=None
        )

    def _handle_positioning(
        self,
        frame: np.ndarray,
        detection: Dict
    ) -> CaptureResult:
        """Handle positioning state"""
        self._transition_state(CaptureState.POSITIONING)
        self.stable_frame_count = 0

        message = "Adjust position - center comic in frame"
        self._speak_with_cooldown(message)

        return CaptureResult(
            success=False,
            state=CaptureState.POSITIONING,
            message=message,
            detection=detection
        )

    def _handle_stabilizing(
        self,
        frame: np.ndarray,
        detection: Dict
    ) -> CaptureResult:
        """Handle stabilizing state"""
        self._transition_state(CaptureState.STABILIZING)

        progress = f"{self.stable_frame_count}/{self.stability_frames_required}"
        message = f"Hold steady... {progress}"

        if self.stable_frame_count == 1:
            self._speak("Hold steady")

        return CaptureResult(
            success=False,
            state=CaptureState.STABILIZING,
            message=message,
            detection=detection
        )

    def _handle_poor_quality(
        self,
        frame: np.ndarray,
        detection: Dict,
        quality: Dict
    ) -> CaptureResult:
        """Handle poor quality state"""
        self._transition_state(CaptureState.POOR_QUALITY)

        message = quality['recommendation']
        self._speak_with_cooldown(message)

        return CaptureResult(
            success=False,
            state=CaptureState.POOR_QUALITY,
            message=message,
            detection=detection,
            quality_score=quality
        )

    def _handle_ready(
        self,
        frame: np.ndarray,
        detection: Dict,
        quality: Dict,
        cropped: np.ndarray
    ) -> CaptureResult:
        """Handle ready to capture state"""
        self._transition_state(CaptureState.READY)
        self.last_quality_check = quality

        message = f"Ready - capturing {self.capture_mode} cover"

        return CaptureResult(
            success=True,
            state=CaptureState.READY,
            message=message,
            image=cropped,
            detection=detection,
            quality_score=quality
        )

    def capture(self, result: CaptureResult) -> Optional[Dict]:
        """
        Execute capture and save image

        Args:
            result: CaptureResult from process_frame

        Returns:
            Capture metadata or None
        """
        if not result.success or result.image is None:
            return None

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{self.session_id}_{self.capture_mode}_{timestamp}.jpg"
        filepath = self.output_dir / filename

        # Save image
        cv2.imwrite(str(filepath), result.image, [cv2.IMWRITE_JPEG_QUALITY, 95])

        # Voice feedback
        self._speak("Captured", force=True)

        # Update state
        if self.capture_mode == "front":
            self.front_captured = True
            self.capture_mode = "back"
            self._speak("Flip to back cover")
        else:
            self.back_captured = True

        self.captures_in_session += 1
        self.stable_frame_count = 0
        self._transition_state(CaptureState.CAPTURED)

        # Prepare metadata
        metadata = {
            'filename': filename,
            'filepath': str(filepath),
            'side': 'front' if self.front_captured and not self.back_captured else 'back',
            'quality_score': result.quality_score,
            'detection_confidence': result.detection.get('confidence', 0) if result.detection else 0,
            'timestamp': timestamp,
            'session_id': self.session_id,
            'image_dimensions': (result.image.shape[1], result.image.shape[0])
        }

        # Callback
        if self._on_capture:
            self._on_capture(metadata)

        return metadata

    def _check_stability(self, detection: Dict) -> bool:
        """Check if detection is stable"""
        if self.last_detection is None:
            self.last_detection = detection
            self.stable_frame_count = 1
            return False

        # Compare to last detection
        x, y, w, h = detection['bbox']
        lx, ly, lw, lh = self.last_detection['bbox']

        position_diff = abs(x - lx) + abs(y - ly)
        size_diff = abs(w - lw) + abs(h - lh)

        self.last_detection = detection

        # Check if stable
        if position_diff < 15 and size_diff < 15:
            self.stable_frame_count += 1
        else:
            self.stable_frame_count = 1

        return self.stable_frame_count >= self.stability_frames_required

    def _transition_state(self, new_state: CaptureState):
        """Handle state transition"""
        if new_state != self.current_state:
            old_state = self.current_state
            self.current_state = new_state

            logger.debug(f"State: {old_state.value} -> {new_state.value}")

            if self._on_state_change:
                self._on_state_change(old_state, new_state)

    def _speak(self, message: str, force: bool = False):
        """Speak message via voice feedback"""
        if self.voice and self.voice_enabled:
            self.voice.speak(message, force)

    def _speak_with_cooldown(self, message: str):
        """Speak message with cooldown to avoid repetition"""
        now = time.time()
        if now - self.last_voice_time >= self.voice_cooldown:
            self._speak(message)
            self.last_voice_time = now

    def get_overlay_frame(
        self,
        frame: np.ndarray,
        result: CaptureResult
    ) -> np.ndarray:
        """
        Generate frame with visual overlay

        Args:
            frame: Original frame
            result: Capture result

        Returns:
            Frame with overlay
        """
        # Draw border detection
        overlay = self.border_detector.draw_overlay(
            frame,
            result.detection,
            result.message
        )

        # Add quality overlay if available
        if result.quality_score:
            overlay = self.quality_scorer.get_quality_overlay(
                overlay,
                result.quality_score
            )

        # Add capture mode indicator
        h, w = overlay.shape[:2]
        mode_text = f"Capturing: {self.capture_mode.upper()}"
        cv2.putText(
            overlay,
            mode_text,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2
        )

        # Status indicator
        if result.state == CaptureState.READY:
            cv2.putText(
                overlay,
                "READY - Press SPACE to capture",
                (20, h - 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

        return overlay

    def reset_session(self):
        """Reset for new comic"""
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.capture_mode = "front"
        self.front_captured = False
        self.back_captured = False
        self.captures_in_session = 0
        self.stable_frame_count = 0
        self.last_detection = None
        self.border_detector.reset_tracking()
        self.current_state = CaptureState.NO_COMIC

        if self.voice:
            self.voice.speak("Ready for new comic", force=True)

    def is_complete(self) -> bool:
        """Check if both front and back captured"""
        return self.front_captured and self.back_captured

    def set_capture_callback(self, callback: Callable):
        """Set callback for capture events"""
        self._on_capture = callback

    def set_state_callback(self, callback: Callable):
        """Set callback for state changes"""
        self._on_state_change = callback

    def get_session_info(self) -> Dict:
        """Get current session information"""
        return {
            'session_id': self.session_id,
            'capture_mode': self.capture_mode,
            'front_captured': self.front_captured,
            'back_captured': self.back_captured,
            'captures_in_session': self.captures_in_session,
            'current_state': self.current_state.value,
            'quality_threshold': self.quality_threshold
        }


class BatchAutoCaptureSystem(AutoCaptureSystem):
    """Extended auto-capture for batch processing multiple comics"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.comics_captured = 0
        self.batch_captures = []  # List of (front_path, back_path) tuples

    def complete_comic(self) -> Optional[Tuple[str, str]]:
        """
        Mark current comic as complete

        Returns:
            Tuple of (front_path, back_path) or None
        """
        if not self.is_complete():
            return None

        # Find captured files
        front_files = list(self.output_dir.glob(f"{self.session_id}_front_*.jpg"))
        back_files = list(self.output_dir.glob(f"{self.session_id}_back_*.jpg"))

        if front_files and back_files:
            front_path = str(max(front_files, key=lambda p: p.stat().st_mtime))
            back_path = str(max(back_files, key=lambda p: p.stat().st_mtime))

            self.batch_captures.append((front_path, back_path))
            self.comics_captured += 1

            # Reset for next comic
            self.reset_session()

            if self.voice:
                self.voice.announce_progress(
                    self.comics_captured,
                    "comics captured"
                )

            return (front_path, back_path)

        return None

    def get_batch_results(self) -> Dict:
        """Get batch capture results"""
        return {
            'comics_captured': self.comics_captured,
            'captures': self.batch_captures
        }
