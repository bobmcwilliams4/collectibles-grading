"""
Image Quality Scorer
Multi-factor image quality assessment for grading accuracy
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class QualityMetric:
    """Individual quality metric"""
    name: str
    score: float  # 0.0 to 1.0
    weight: float
    pass_threshold: float
    passed: bool
    recommendation: Optional[str] = None


class ImageQualityScorer:
    """
    Comprehensive image quality assessment

    Evaluates:
    - Sharpness/focus
    - Brightness/exposure
    - Contrast
    - Noise level
    - Color saturation
    - Motion blur
    - Resolution adequacy
    - Lighting uniformity
    """

    def __init__(self):
        # Metric weights (sum to 1.0)
        self.weights = {
            'sharpness': 0.25,
            'brightness': 0.10,
            'contrast': 0.15,
            'focus': 0.20,
            'noise': 0.10,
            'saturation': 0.08,
            'blur': 0.07,
            'uniformity': 0.05
        }

        # Pass thresholds for each metric
        self.thresholds = {
            'sharpness': 0.6,
            'brightness': 0.5,
            'contrast': 0.5,
            'focus': 0.6,
            'noise': 0.5,
            'saturation': 0.4,
            'blur': 0.6,
            'uniformity': 0.4
        }

        # Target values for brightness
        self.target_brightness = 127  # Middle gray

    def score_image(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Comprehensive quality assessment

        Args:
            image: BGR image array

        Returns:
            Quality scores and recommendations
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        metrics = {}

        # 1. Sharpness (Laplacian variance)
        sharpness = self._calculate_sharpness(gray)
        metrics['sharpness'] = QualityMetric(
            name='Sharpness',
            score=sharpness,
            weight=self.weights['sharpness'],
            pass_threshold=self.thresholds['sharpness'],
            passed=sharpness >= self.thresholds['sharpness'],
            recommendation="Increase camera resolution or distance" if sharpness < self.thresholds['sharpness'] else None
        )

        # 2. Brightness
        brightness = self._calculate_brightness(gray)
        metrics['brightness'] = QualityMetric(
            name='Brightness',
            score=brightness,
            weight=self.weights['brightness'],
            pass_threshold=self.thresholds['brightness'],
            passed=brightness >= self.thresholds['brightness'],
            recommendation="Adjust lighting - image too dark or bright" if brightness < self.thresholds['brightness'] else None
        )

        # 3. Contrast
        contrast = self._calculate_contrast(gray)
        metrics['contrast'] = QualityMetric(
            name='Contrast',
            score=contrast,
            weight=self.weights['contrast'],
            pass_threshold=self.thresholds['contrast'],
            passed=contrast >= self.thresholds['contrast'],
            recommendation="Use solid background for better contrast" if contrast < self.thresholds['contrast'] else None
        )

        # 4. Focus (edge density)
        focus = self._calculate_focus(gray)
        metrics['focus'] = QualityMetric(
            name='Focus',
            score=focus,
            weight=self.weights['focus'],
            pass_threshold=self.thresholds['focus'],
            passed=focus >= self.thresholds['focus'],
            recommendation="Camera out of focus - adjust or use autofocus" if focus < self.thresholds['focus'] else None
        )

        # 5. Noise level
        noise = self._calculate_noise_score(gray)
        metrics['noise'] = QualityMetric(
            name='Noise',
            score=noise,
            weight=self.weights['noise'],
            pass_threshold=self.thresholds['noise'],
            passed=noise >= self.thresholds['noise'],
            recommendation="High noise - improve lighting conditions" if noise < self.thresholds['noise'] else None
        )

        # 6. Color saturation
        saturation = self._calculate_saturation(image)
        metrics['saturation'] = QualityMetric(
            name='Saturation',
            score=saturation,
            weight=self.weights['saturation'],
            pass_threshold=self.thresholds['saturation'],
            passed=saturation >= self.thresholds['saturation'],
            recommendation="Colors appear washed out" if saturation < self.thresholds['saturation'] else None
        )

        # 7. Motion blur detection
        blur = self._detect_motion_blur(gray)
        metrics['blur'] = QualityMetric(
            name='Motion Stability',
            score=blur,
            weight=self.weights['blur'],
            pass_threshold=self.thresholds['blur'],
            passed=blur >= self.thresholds['blur'],
            recommendation="Hold camera steady - motion blur detected" if blur < self.thresholds['blur'] else None
        )

        # 8. Lighting uniformity
        uniformity = self._calculate_uniformity(gray)
        metrics['uniformity'] = QualityMetric(
            name='Light Uniformity',
            score=uniformity,
            weight=self.weights['uniformity'],
            pass_threshold=self.thresholds['uniformity'],
            passed=uniformity >= self.thresholds['uniformity'],
            recommendation="Uneven lighting - avoid shadows" if uniformity < self.thresholds['uniformity'] else None
        )

        # Calculate overall score
        overall_score = sum(m.score * m.weight for m in metrics.values())

        # Get primary recommendation (lowest scoring critical metric)
        failed_metrics = [m for m in metrics.values() if not m.passed]
        failed_metrics.sort(key=lambda m: m.score * m.weight)

        primary_recommendation = None
        if failed_metrics:
            primary_recommendation = failed_metrics[0].recommendation

        # Determine pass/fail
        pass_threshold = 0.85
        passed = overall_score >= pass_threshold

        return {
            'overall_score': round(overall_score, 3),
            'pass_threshold': pass_threshold,
            'passed': passed,
            'metrics': {k: {
                'name': v.name,
                'score': round(v.score, 3),
                'passed': v.passed,
                'recommendation': v.recommendation
            } for k, v in metrics.items()},
            'recommendation': primary_recommendation or "Image quality acceptable",
            'grade_adjustment': self._calculate_grade_adjustment(overall_score)
        }

    def _calculate_sharpness(self, gray: np.ndarray) -> float:
        """Calculate sharpness using Laplacian variance"""
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()

        # Normalize (typical range 0-2000 for sharp images)
        score = min(variance / 1000, 1.0)
        return score

    def _calculate_brightness(self, gray: np.ndarray) -> float:
        """Calculate brightness score"""
        mean_brightness = np.mean(gray)

        # Score based on distance from target
        deviation = abs(mean_brightness - self.target_brightness)
        max_deviation = self.target_brightness  # Maximum possible deviation

        score = 1.0 - (deviation / max_deviation)
        return max(0, score)

    def _calculate_contrast(self, gray: np.ndarray) -> float:
        """Calculate contrast score"""
        std_dev = np.std(gray)

        # Normalize (good contrast typically 50-80)
        score = min(std_dev / 70, 1.0)
        return score

    def _calculate_focus(self, gray: np.ndarray) -> float:
        """Calculate focus score using edge density"""
        edges = cv2.Canny(gray, 100, 200)
        edge_density = np.sum(edges > 0) / edges.size

        # Normalize (well-focused images have 5-15% edge pixels)
        score = min(edge_density * 10, 1.0)
        return score

    def _calculate_noise_score(self, gray: np.ndarray) -> float:
        """Calculate noise score (inverse of noise level)"""
        # Estimate noise using median absolute deviation
        sobel = cv2.Sobel(gray, cv2.CV_64F, 1, 1, ksize=3)
        noise_estimate = np.median(np.abs(sobel)) * 1.4826

        # Invert (lower noise = higher score)
        score = max(0, 1.0 - (noise_estimate / 30))
        return score

    def _calculate_saturation(self, image: np.ndarray) -> float:
        """Calculate color saturation score"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        saturation_channel = hsv[:, :, 1]
        mean_saturation = np.mean(saturation_channel)

        # Normalize (typical good saturation 60-150)
        score = min(mean_saturation / 100, 1.0)
        return score

    def _detect_motion_blur(self, gray: np.ndarray) -> float:
        """Detect motion blur using FFT analysis"""
        # Compute FFT
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        magnitude_spectrum = np.abs(fshift)

        # Analyze frequency distribution
        rows, cols = gray.shape
        crow, ccol = rows // 2, cols // 2

        # High frequency content indicates sharp image
        mask = np.zeros((rows, cols), np.uint8)
        cv2.circle(mask, (ccol, crow), min(rows, cols) // 4, 1, -1)

        # Ratio of low to high frequency
        low_freq = np.sum(magnitude_spectrum * mask)
        high_freq = np.sum(magnitude_spectrum * (1 - mask))

        if low_freq == 0:
            return 1.0

        ratio = high_freq / low_freq

        # Higher ratio = sharper image
        score = min(ratio / 0.5, 1.0)
        return score

    def _calculate_uniformity(self, gray: np.ndarray) -> float:
        """Calculate lighting uniformity"""
        # Divide image into grid
        rows, cols = gray.shape
        grid_size = 4

        cell_h = rows // grid_size
        cell_w = cols // grid_size

        cell_means = []
        for i in range(grid_size):
            for j in range(grid_size):
                cell = gray[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
                cell_means.append(np.mean(cell))

        # Calculate coefficient of variation
        mean_val = np.mean(cell_means)
        std_val = np.std(cell_means)

        if mean_val == 0:
            return 0

        cv = std_val / mean_val

        # Lower CV = more uniform
        score = max(0, 1.0 - cv * 2)
        return score

    def _calculate_grade_adjustment(self, quality_score: float) -> float:
        """
        Calculate grade adjustment based on image quality

        Poor quality images may cause AI to miss defects,
        so we apply a conservative grade penalty
        """
        if quality_score >= 0.9:
            return 0  # No adjustment
        elif quality_score >= 0.85:
            return 0.1  # Minor penalty
        elif quality_score >= 0.7:
            return 0.3  # Moderate penalty
        elif quality_score >= 0.5:
            return 0.5  # Significant penalty
        else:
            return 1.0  # Major penalty

    def quick_score(self, image: np.ndarray) -> Tuple[float, bool]:
        """
        Quick quality check (faster, less comprehensive)

        Returns:
            Tuple of (score, passed)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Just check sharpness and brightness
        sharpness = self._calculate_sharpness(gray)
        brightness = self._calculate_brightness(gray)

        score = sharpness * 0.6 + brightness * 0.4
        passed = score >= 0.7

        return score, passed

    def get_quality_overlay(
        self,
        image: np.ndarray,
        scores: Dict[str, Any]
    ) -> np.ndarray:
        """Generate quality visualization overlay"""
        overlay = image.copy()
        h, w = image.shape[:2]

        # Draw quality bar
        bar_width = 200
        bar_height = 20
        bar_x = w - bar_width - 20
        bar_y = 20

        # Background
        cv2.rectangle(
            overlay,
            (bar_x, bar_y),
            (bar_x + bar_width, bar_y + bar_height),
            (50, 50, 50),
            -1
        )

        # Fill based on score
        fill_width = int(bar_width * scores['overall_score'])
        color = (0, 255, 0) if scores['passed'] else (0, 165, 255)
        cv2.rectangle(
            overlay,
            (bar_x, bar_y),
            (bar_x + fill_width, bar_y + bar_height),
            color,
            -1
        )

        # Border
        cv2.rectangle(
            overlay,
            (bar_x, bar_y),
            (bar_x + bar_width, bar_y + bar_height),
            (255, 255, 255),
            2
        )

        # Score text
        score_text = f"Quality: {scores['overall_score']*100:.0f}%"
        cv2.putText(
            overlay,
            score_text,
            (bar_x, bar_y - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )

        # Recommendation
        if not scores['passed'] and scores.get('recommendation'):
            cv2.putText(
                overlay,
                scores['recommendation'],
                (20, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 165, 255),
                2
            )

        return overlay
