"""
Webcam Capture Module
Real-time comic book capture with border detection, quality scoring, and voice feedback
"""

from .camera_manager import CameraManager
from .border_detector import ComicBorderDetector
from .quality_scorer import ImageQualityScorer
from .auto_capture import AutoCaptureSystem
from .voice_feedback import VoiceFeedback

__all__ = [
    'CameraManager',
    'ComicBorderDetector',
    'ImageQualityScorer',
    'AutoCaptureSystem',
    'VoiceFeedback'
]
