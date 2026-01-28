"""
Comic Border Detector
Advanced edge detection and perspective correction for comic books
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict
import logging

logger = logging.getLogger(__name__)


class ComicBorderDetector:
    """
    Detects and tracks comic book borders in video frames

    Features:
    - Multi-algorithm edge detection
    - Perspective correction
    - Aspect ratio validation
    - Tracking for stability
    - Visual overlay generation
    """

    # Standard comic dimensions (width/height ratio)
    COMIC_ASPECT_RATIOS = {
        'golden_age': (7.5, 10.5),    # ~0.714
        'silver_age': (7.125, 10.25), # ~0.695
        'modern_age': (6.625, 10.25), # ~0.646
        'magazine': (8.5, 11),        # ~0.773
        'treasury': (10, 13.5)        # ~0.741
    }

    def __init__(self):
        # Detection parameters
        self.min_area_ratio = 0.05   # Minimum comic area relative to frame
        self.max_area_ratio = 0.95   # Maximum comic area relative to frame
        self.aspect_tolerance = 0.2   # Aspect ratio tolerance

        # Valid aspect ratio range for comics
        self.min_aspect = 0.55  # Widest acceptable
        self.max_aspect = 0.85  # Tallest acceptable

        # Tracking
        self.last_detection: Optional[Dict] = None
        self.detection_history: List[Dict] = []
        self.max_history = 10

        # Colors for overlay
        self.colors = {
            'detected': (0, 255, 0),      # Green
            'tracking': (255, 255, 0),    # Yellow
            'quality_low': (0, 165, 255), # Orange
            'no_detect': (0, 0, 255)      # Red
        }

    def detect_comic(self, frame: np.ndarray) -> Optional[Dict]:
        """
        Detect comic book in frame

        Args:
            frame: BGR image frame

        Returns:
            Detection dictionary or None
        """
        height, width = frame.shape[:2]
        frame_area = height * width

        # Try multiple detection methods
        detections = []

        # Method 1: Canny edge detection
        canny_result = self._detect_with_canny(frame)
        if canny_result:
            detections.append(canny_result)

        # Method 2: Adaptive threshold
        thresh_result = self._detect_with_threshold(frame)
        if thresh_result:
            detections.append(thresh_result)

        # Method 3: Color-based detection (white background)
        color_result = self._detect_with_color(frame)
        if color_result:
            detections.append(color_result)

        if not detections:
            self.last_detection = None
            return None

        # Choose best detection
        best = self._choose_best_detection(detections, frame_area)

        if best:
            # Update tracking history
            self._update_history(best)
            self.last_detection = best

        return best

    def _detect_with_canny(self, frame: np.ndarray) -> Optional[Dict]:
        """Detect using Canny edge detection"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Adaptive Canny thresholds
        median_val = np.median(blurred)
        lower = int(max(0, 0.7 * median_val))
        upper = int(min(255, 1.3 * median_val))

        edges = cv2.Canny(blurred, lower, upper)

        # Dilate to connect edges
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=2)

        return self._find_rectangle(edges, frame.shape, 'canny')

    def _detect_with_threshold(self, frame: np.ndarray) -> Optional[Dict]:
        """Detect using adaptive thresholding"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Adaptive threshold
        thresh = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11, 2
        )

        # Morphological operations
        kernel = np.ones((5, 5), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

        return self._find_rectangle(thresh, frame.shape, 'threshold')

    def _detect_with_color(self, frame: np.ndarray) -> Optional[Dict]:
        """Detect using color segmentation (assumes light background)"""
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Define range for white/light colors (background)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 30, 255])

        # Create mask for background
        bg_mask = cv2.inRange(hsv, lower_white, upper_white)

        # Invert to get foreground (comic)
        fg_mask = cv2.bitwise_not(bg_mask)

        # Clean up
        kernel = np.ones((7, 7), np.uint8)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)

        return self._find_rectangle(fg_mask, frame.shape, 'color')

    def _find_rectangle(
        self,
        binary_image: np.ndarray,
        frame_shape: Tuple,
        method: str
    ) -> Optional[Dict]:
        """Find rectangular contour in binary image"""
        contours, _ = cv2.findContours(
            binary_image,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return None

        height, width = frame_shape[:2]
        frame_area = height * width
        min_area = frame_area * self.min_area_ratio
        max_area = frame_area * self.max_area_ratio

        best_contour = None
        best_score = 0

        for contour in contours:
            area = cv2.contourArea(contour)

            # Area filter
            if area < min_area or area > max_area:
                continue

            # Approximate contour
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

            # Should have 4 corners (or close to it)
            if len(approx) < 4 or len(approx) > 8:
                continue

            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0

            # Aspect ratio filter
            if not (self.min_aspect <= aspect_ratio <= self.max_aspect):
                continue

            # Calculate rectangularity score
            rect_area = w * h
            rectangularity = area / rect_area if rect_area > 0 else 0

            # Score based on rectangularity and area
            score = rectangularity * (area / frame_area)

            if score > best_score:
                best_score = score
                best_contour = {
                    'contour': contour,
                    'approx': approx,
                    'bbox': (x, y, w, h),
                    'area': area,
                    'aspect_ratio': aspect_ratio,
                    'rectangularity': rectangularity,
                    'score': score,
                    'method': method
                }

        if best_contour:
            # Get perspective points
            best_contour['corners'] = self._get_corner_points(best_contour['contour'])
            best_contour['confidence'] = min(1.0, best_score * 2)

        return best_contour

    def _get_corner_points(self, contour) -> np.ndarray:
        """Get 4 corner points for perspective correction"""
        # Get bounding rectangle
        rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rect)
        box = np.int0(box)

        # Order points: top-left, top-right, bottom-right, bottom-left
        pts = box.reshape(4, 2)

        # Sort by y coordinate
        pts = pts[np.argsort(pts[:, 1])]

        # Top two points
        top = pts[:2]
        top = top[np.argsort(top[:, 0])]

        # Bottom two points
        bottom = pts[2:]
        bottom = bottom[np.argsort(bottom[:, 0])]

        return np.array([top[0], top[1], bottom[1], bottom[0]], dtype=np.float32)

    def _choose_best_detection(
        self,
        detections: List[Dict],
        frame_area: int
    ) -> Optional[Dict]:
        """Choose best detection from multiple methods"""
        if not detections:
            return None

        # Use tracking history for smoothing
        if self.detection_history:
            last_bbox = self.detection_history[-1]['bbox']

            # Prefer detections close to last position
            for d in detections:
                x, y, w, h = d['bbox']
                last_x, last_y, last_w, last_h = last_bbox

                # Position similarity
                pos_diff = abs(x - last_x) + abs(y - last_y)
                size_diff = abs(w - last_w) + abs(h - last_h)

                # Boost score for consistent detections
                if pos_diff < 50 and size_diff < 50:
                    d['score'] *= 1.3

        # Return highest scoring detection
        best = max(detections, key=lambda d: d['score'])
        return best if best['score'] > 0.1 else None

    def _update_history(self, detection: Dict):
        """Update detection history for tracking"""
        self.detection_history.append({
            'bbox': detection['bbox'],
            'confidence': detection['confidence']
        })

        # Keep limited history
        while len(self.detection_history) > self.max_history:
            self.detection_history.pop(0)

    def is_stable(self, frames: int = 5, threshold: float = 20) -> bool:
        """Check if detection is stable across recent frames"""
        if len(self.detection_history) < frames:
            return False

        recent = self.detection_history[-frames:]
        bboxes = [h['bbox'] for h in recent]

        # Calculate variance in position
        x_vals = [b[0] for b in bboxes]
        y_vals = [b[1] for b in bboxes]

        x_var = max(x_vals) - min(x_vals)
        y_var = max(y_vals) - min(y_vals)

        return x_var < threshold and y_var < threshold

    def get_stability_score(self) -> float:
        """Get stability score (0-1)"""
        if len(self.detection_history) < 3:
            return 0.0

        recent = self.detection_history[-5:]
        bboxes = [h['bbox'] for h in recent]

        # Calculate variance
        x_vals = [b[0] for b in bboxes]
        y_vals = [b[1] for b in bboxes]
        w_vals = [b[2] for b in bboxes]

        x_var = max(x_vals) - min(x_vals)
        y_var = max(y_vals) - min(y_vals)
        avg_w = sum(w_vals) / len(w_vals)

        # Normalize by width
        relative_movement = (x_var + y_var) / avg_w if avg_w > 0 else 1

        return max(0, 1 - relative_movement)

    def draw_overlay(
        self,
        frame: np.ndarray,
        detection: Optional[Dict] = None,
        status: str = "",
        show_info: bool = True
    ) -> np.ndarray:
        """
        Draw detection overlay on frame

        Args:
            frame: Image frame
            detection: Detection dictionary
            status: Status text to display
            show_info: Show detection info

        Returns:
            Frame with overlay
        """
        overlay = frame.copy()

        if detection:
            x, y, w, h = detection['bbox']
            confidence = detection.get('confidence', 0)

            # Choose color based on quality
            if confidence > 0.85:
                color = self.colors['detected']
            elif confidence > 0.6:
                color = self.colors['tracking']
            else:
                color = self.colors['quality_low']

            # Draw border
            cv2.rectangle(overlay, (x, y), (x + w, y + h), color, 3)

            # Draw corners
            corner_length = 30
            corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
            for i, (cx, cy) in enumerate(corners):
                if i == 0:  # Top-left
                    cv2.line(overlay, (cx, cy), (cx + corner_length, cy), color, 4)
                    cv2.line(overlay, (cx, cy), (cx, cy + corner_length), color, 4)
                elif i == 1:  # Top-right
                    cv2.line(overlay, (cx, cy), (cx - corner_length, cy), color, 4)
                    cv2.line(overlay, (cx, cy), (cx, cy + corner_length), color, 4)
                elif i == 2:  # Bottom-right
                    cv2.line(overlay, (cx, cy), (cx - corner_length, cy), color, 4)
                    cv2.line(overlay, (cx, cy), (cx, cy - corner_length), color, 4)
                else:  # Bottom-left
                    cv2.line(overlay, (cx, cy), (cx + corner_length, cy), color, 4)
                    cv2.line(overlay, (cx, cy), (cx, cy - corner_length), color, 4)

            # Status text
            if status:
                text = f"{status} | Quality: {confidence*100:.0f}%"
                cv2.putText(
                    overlay, text,
                    (x, y - 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, color, 2
                )

            # Info panel
            if show_info:
                info_y = y + h + 25
                info_lines = [
                    f"Size: {w}x{h}",
                    f"Aspect: {detection.get('aspect_ratio', 0):.2f}",
                    f"Method: {detection.get('method', 'unknown')}"
                ]
                for i, line in enumerate(info_lines):
                    cv2.putText(
                        overlay, line,
                        (x, info_y + i * 20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, color, 1
                    )

        else:
            # No detection - show guide
            h, w = frame.shape[:2]
            center_x, center_y = w // 2, h // 2

            # Draw guide rectangle
            guide_w = int(w * 0.6)
            guide_h = int(guide_w / 0.67)  # Comic aspect ratio
            x1 = center_x - guide_w // 2
            y1 = center_y - guide_h // 2

            cv2.rectangle(
                overlay,
                (x1, y1), (x1 + guide_w, y1 + guide_h),
                self.colors['no_detect'],
                2,
                cv2.LINE_AA
            )

            cv2.putText(
                overlay,
                "Position comic in frame",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7, self.colors['no_detect'], 2
            )

        return overlay

    def get_cropped_comic(
        self,
        frame: np.ndarray,
        detection: Dict,
        apply_perspective: bool = True
    ) -> np.ndarray:
        """
        Get cropped and perspective-corrected comic image

        Args:
            frame: Full frame
            detection: Detection dictionary
            apply_perspective: Apply perspective correction

        Returns:
            Cropped comic image
        """
        if apply_perspective and 'corners' in detection:
            corners = detection['corners']
            x, y, w, h = detection['bbox']

            # Target size
            target_w = w
            target_h = int(target_w / 0.67)  # Standard comic ratio

            # Target points
            target_pts = np.array([
                [0, 0],
                [target_w, 0],
                [target_w, target_h],
                [0, target_h]
            ], dtype=np.float32)

            # Perspective transform
            matrix = cv2.getPerspectiveTransform(corners, target_pts)
            warped = cv2.warpPerspective(frame, matrix, (target_w, target_h))

            return warped
        else:
            # Simple crop
            x, y, w, h = detection['bbox']
            return frame[y:y+h, x:x+w]

    def reset_tracking(self):
        """Reset tracking history"""
        self.last_detection = None
        self.detection_history.clear()
