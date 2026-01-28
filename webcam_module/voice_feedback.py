"""
Voice Feedback System
Text-to-speech feedback for grading workflow
"""

import logging
from typing import Optional, Dict, Any
from threading import Thread, Lock
from queue import Queue, Empty
import time

logger = logging.getLogger(__name__)


class VoiceFeedback:
    """
    Voice feedback for comic grading workflow

    Features:
    - Non-blocking speech
    - Message deduplication
    - Priority queue
    - Grade announcements
    - Progress updates
    """

    # CGC grade to label mapping
    GRADE_LABELS = {
        10.0: "Gem Mint",
        9.9: "Mint",
        9.8: "Near Mint Mint",
        9.6: "Near Mint Plus",
        9.4: "Near Mint",
        9.2: "Near Mint Minus",
        9.0: "Very Fine Near Mint",
        8.5: "Very Fine Plus",
        8.0: "Very Fine",
        7.5: "Very Fine Minus",
        7.0: "Fine Very Fine",
        6.5: "Fine Plus",
        6.0: "Fine",
        5.5: "Fine Minus",
        5.0: "Very Good Fine",
        4.5: "Very Good Plus",
        4.0: "Very Good",
        3.5: "Very Good Minus",
        3.0: "Good Very Good",
        2.5: "Good Plus",
        2.0: "Good",
        1.8: "Good Minus",
        1.5: "Fair Good",
        1.0: "Fair",
        0.5: "Poor"
    }

    def __init__(self, rate: int = 175, volume: float = 1.0):
        """
        Initialize voice feedback

        Args:
            rate: Speech rate (words per minute)
            volume: Volume (0.0 to 1.0)
        """
        self.rate = rate
        self.volume = volume
        self.engine = None
        self.initialized = False

        # Message queue for non-blocking speech
        self._queue: Queue = Queue()
        self._last_message: Optional[str] = None
        self._last_time: float = 0
        self._min_interval: float = 1.0  # Minimum seconds between same message

        # Thread control
        self._running = False
        self._thread: Optional[Thread] = None
        self._lock = Lock()

        # Initialize
        self._initialize()

    def _initialize(self):
        """Initialize TTS engine"""
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', self.rate)
            self.engine.setProperty('volume', self.volume)

            # Try to set a natural voice
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'english' in voice.name.lower() or 'david' in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    break

            self.initialized = True
            self._start_worker()
            logger.info("Voice feedback initialized")

        except ImportError:
            logger.warning("pyttsx3 not installed - voice feedback disabled")
            self.initialized = False

        except Exception as e:
            logger.error(f"Voice initialization failed: {e}")
            self.initialized = False

    def _start_worker(self):
        """Start background speech worker"""
        if self._thread is not None and self._thread.is_alive():
            return

        self._running = True
        self._thread = Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def _worker_loop(self):
        """Background worker for speech synthesis"""
        while self._running:
            try:
                message = self._queue.get(timeout=0.5)
                if message and self.engine:
                    with self._lock:
                        self.engine.say(message)
                        self.engine.runAndWait()
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Speech error: {e}")

    def speak(self, message: str, force: bool = False):
        """
        Speak a message (non-blocking)

        Args:
            message: Text to speak
            force: Bypass deduplication
        """
        if not self.initialized:
            return

        now = time.time()

        # Deduplication
        if not force:
            if message == self._last_message:
                if now - self._last_time < self._min_interval:
                    return

        self._last_message = message
        self._last_time = now

        # Add to queue
        self._queue.put(message)

    def announce_grade(self, grade: float, confidence: float = 0.0):
        """
        Announce grading result

        Args:
            grade: CGC grade (0.5 - 10.0)
            confidence: Confidence percentage
        """
        label = self._get_grade_label(grade)

        message = f"Graded {grade} out of 10. {label}."

        if confidence >= 0.9:
            message += " High confidence."
        elif confidence >= 0.7:
            message += f" Confidence {int(confidence * 100)} percent."
        elif confidence < 0.7:
            message += " Manual review recommended."

        self.speak(message, force=True)

    def announce_price(self, price: float, grade: float):
        """
        Announce pricing result

        Args:
            price: Estimated value
            grade: Associated grade
        """
        if price >= 1000:
            price_text = f"{int(price / 1000)} thousand {int(price % 1000)} dollars"
        else:
            price_text = f"{int(price)} dollars"

        message = f"Estimated value at grade {grade}: {price_text}"
        self.speak(message, force=True)

    def announce_defects(self, defects: list):
        """
        Announce detected defects

        Args:
            defects: List of defect dictionaries
        """
        if not defects:
            self.speak("No significant defects detected.", force=True)
            return

        # Summarize defects
        severity_counts = {'minor': 0, 'moderate': 0, 'major': 0}
        for d in defects:
            severity = d.get('severity', 'moderate')
            if severity in severity_counts:
                severity_counts[severity] += 1

        parts = []
        if severity_counts['major']:
            parts.append(f"{severity_counts['major']} major")
        if severity_counts['moderate']:
            parts.append(f"{severity_counts['moderate']} moderate")
        if severity_counts['minor']:
            parts.append(f"{severity_counts['minor']} minor")

        if parts:
            defect_summary = ", ".join(parts) + " defects detected."
            self.speak(defect_summary, force=True)

    def announce_progress(self, count: int, item_type: str = "comics"):
        """
        Announce batch progress

        Args:
            count: Number completed
            item_type: Type of items
        """
        message = f"{count} {item_type} completed."
        self.speak(message, force=True)

    def announce_capture(self, side: str):
        """Announce capture event"""
        if side == "front":
            self.speak("Front cover captured. Flip to back.", force=True)
        else:
            self.speak("Back cover captured. Ready for grading.", force=True)

    def guide_positioning(self, instruction: str):
        """
        Guide user for positioning

        Args:
            instruction: Positioning instruction
        """
        # Map common instructions to friendlier speech
        guides = {
            'center': "Center the comic in frame",
            'closer': "Move camera closer",
            'further': "Move camera back",
            'steady': "Hold steady",
            'lighting': "Adjust lighting",
            'flip': "Flip to back cover"
        }

        message = guides.get(instruction.lower(), instruction)
        self.speak(message)

    def countdown(self, seconds: int = 3):
        """
        Speak countdown

        Args:
            seconds: Number of seconds to count
        """
        for i in range(seconds, 0, -1):
            self.speak(str(i), force=True)
            time.sleep(1)
        self.speak("Capture", force=True)

    def error(self, message: str):
        """Announce error"""
        self.speak(f"Error. {message}", force=True)

    def success(self, message: str = "Complete"):
        """Announce success"""
        self.speak(message, force=True)

    def _get_grade_label(self, grade: float) -> str:
        """Get label for numeric grade"""
        # Find closest grade
        grades = sorted(self.GRADE_LABELS.keys(), reverse=True)
        for g in grades:
            if grade >= g:
                return self.GRADE_LABELS[g]
        return "Poor"

    def set_rate(self, rate: int):
        """Set speech rate"""
        self.rate = rate
        if self.engine:
            self.engine.setProperty('rate', rate)

    def set_volume(self, volume: float):
        """Set volume"""
        self.volume = max(0.0, min(1.0, volume))
        if self.engine:
            self.engine.setProperty('volume', self.volume)

    def stop(self):
        """Stop voice feedback"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

        if self.engine:
            try:
                self.engine.stop()
            except:
                pass

    def test(self):
        """Test voice output"""
        self.speak("Voice feedback is working.", force=True)

    def __del__(self):
        """Cleanup"""
        self.stop()


class SilentFeedback:
    """Silent feedback stub for when voice is disabled"""

    def speak(self, *args, **kwargs): pass
    def announce_grade(self, *args, **kwargs): pass
    def announce_price(self, *args, **kwargs): pass
    def announce_defects(self, *args, **kwargs): pass
    def announce_progress(self, *args, **kwargs): pass
    def announce_capture(self, *args, **kwargs): pass
    def guide_positioning(self, *args, **kwargs): pass
    def countdown(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
    def success(self, *args, **kwargs): pass
    def stop(self): pass
    def test(self): pass


def create_voice_feedback(enabled: bool = True) -> VoiceFeedback:
    """
    Factory function to create voice feedback

    Args:
        enabled: Whether to enable voice

    Returns:
        VoiceFeedback or SilentFeedback
    """
    if enabled:
        return VoiceFeedback()
    return SilentFeedback()
