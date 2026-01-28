"""
Advanced Image Processing Module
Enhancement, preprocessing, and quality optimization for comic grading
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ExifTags
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import hashlib
import logging
import base64
from io import BytesIO
from datetime import datetime

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Comprehensive Image Processing for Comic Book Grading"""

    def __init__(self, output_dir: str = "P:/SOVEREIGN_APPS/collectibles_grading_system/images/captures"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Quality thresholds
        self.min_resolution = (800, 1200)
        self.target_resolution = (1920, 2560)
        self.max_file_size_mb = 10
        self.jpeg_quality = 95

        # Enhancement defaults
        self.default_enhancements = {
            'auto_contrast': True,
            'denoise': True,
            'sharpen': True,
            'color_correct': True
        }

    def process_image(
        self,
        image_path: str,
        enhancements: Dict[str, bool] = None,
        target_size: Tuple[int, int] = None
    ) -> Dict[str, Any]:
        """
        Complete image processing pipeline

        Returns:
            Dict with processed image path, quality scores, and metadata
        """
        enhancements = enhancements or self.default_enhancements
        target_size = target_size or self.target_resolution

        result = {
            'success': False,
            'original_path': image_path,
            'processed_path': None,
            'quality_score': {},
            'metadata': {},
            'preprocessing_applied': [],
            'warnings': [],
            'errors': []
        }

        try:
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                result['errors'].append(f"Failed to load image: {image_path}")
                return result

            original_shape = img.shape
            result['metadata']['original_dimensions'] = (original_shape[1], original_shape[0])

            # Step 1: Fix orientation from EXIF
            img = self._fix_orientation(img, image_path)
            result['preprocessing_applied'].append('orientation_fix')

            # Step 2: Detect and crop comic borders
            cropped, crop_info = self._detect_and_crop(img)
            if cropped is not None:
                img = cropped
                result['metadata']['crop_info'] = crop_info
                result['preprocessing_applied'].append('auto_crop')

            # Step 3: Resize if needed
            if img.shape[0] > target_size[1] or img.shape[1] > target_size[0]:
                img = self._smart_resize(img, target_size)
                result['preprocessing_applied'].append('resize')

            # Step 4: Apply enhancements
            if enhancements.get('auto_contrast'):
                img = self._auto_contrast(img)
                result['preprocessing_applied'].append('auto_contrast')

            if enhancements.get('denoise'):
                img = self._denoise(img)
                result['preprocessing_applied'].append('denoise')

            if enhancements.get('sharpen'):
                img = self._sharpen(img)
                result['preprocessing_applied'].append('sharpen')

            if enhancements.get('color_correct'):
                img = self._color_correct(img)
                result['preprocessing_applied'].append('color_correct')

            # Step 5: Calculate quality score
            result['quality_score'] = self._calculate_quality_score(img)

            # Step 6: Generate hash for deduplication
            result['metadata']['image_hash'] = self._calculate_hash(img)

            # Step 7: Save processed image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"processed_{timestamp}.jpg"
            output_path = self.output_dir / filename

            cv2.imwrite(str(output_path), img, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])

            result['processed_path'] = str(output_path)
            result['metadata']['processed_dimensions'] = (img.shape[1], img.shape[0])
            result['metadata']['file_size_bytes'] = output_path.stat().st_size
            result['success'] = True

            logger.info(f"Image processed successfully: {output_path}")

        except Exception as e:
            logger.error(f"Image processing error: {e}")
            result['errors'].append(str(e))

        return result

    def _fix_orientation(self, img: np.ndarray, image_path: str) -> np.ndarray:
        """Fix image orientation based on EXIF data"""
        try:
            pil_img = Image.open(image_path)
            exif = pil_img._getexif()

            if exif:
                orientation_key = None
                for tag, value in ExifTags.TAGS.items():
                    if value == 'Orientation':
                        orientation_key = tag
                        break

                if orientation_key and orientation_key in exif:
                    orientation = exif[orientation_key]

                    if orientation == 3:
                        img = cv2.rotate(img, cv2.ROTATE_180)
                    elif orientation == 6:
                        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                    elif orientation == 8:
                        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

        except Exception as e:
            logger.debug(f"Could not read EXIF orientation: {e}")

        return img

    def _detect_and_crop(self, img: np.ndarray) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
        """
        Detect comic book borders and auto-crop
        Uses edge detection and contour analysis
        """
        crop_info = {'detected': False}

        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # Adaptive threshold for better edge detection
            edges = cv2.Canny(blurred, 30, 150)

            # Dilate to connect edges
            kernel = np.ones((5, 5), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=2)

            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if not contours:
                return None, crop_info

            # Find the largest rectangular contour
            best_contour = None
            best_area = 0
            min_area = img.shape[0] * img.shape[1] * 0.1  # At least 10% of image

            for contour in contours:
                area = cv2.contourArea(contour)
                if area < min_area:
                    continue

                # Approximate contour
                perimeter = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

                # Check if roughly rectangular (4-6 corners)
                if 4 <= len(approx) <= 6 and area > best_area:
                    best_area = area
                    best_contour = contour

            if best_contour is None:
                return None, crop_info

            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(best_contour)

            # Add small margin
            margin = 5
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(img.shape[1] - x, w + 2 * margin)
            h = min(img.shape[0] - y, h + 2 * margin)

            # Validate aspect ratio (comic books are typically 0.65-0.75)
            aspect_ratio = w / h if h > 0 else 0
            if not (0.55 <= aspect_ratio <= 0.85):
                return None, crop_info

            cropped = img[y:y+h, x:x+w]

            crop_info = {
                'detected': True,
                'x': x, 'y': y, 'w': w, 'h': h,
                'aspect_ratio': round(aspect_ratio, 3),
                'confidence': round(best_area / (img.shape[0] * img.shape[1]), 3)
            }

            return cropped, crop_info

        except Exception as e:
            logger.error(f"Border detection error: {e}")
            return None, crop_info

    def _smart_resize(self, img: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
        """Resize maintaining aspect ratio with high-quality interpolation"""
        h, w = img.shape[:2]
        target_w, target_h = target_size

        # Calculate scale to fit within target
        scale = min(target_w / w, target_h / h)

        if scale >= 1:
            return img  # No upscaling

        new_w = int(w * scale)
        new_h = int(h * scale)

        # Use LANCZOS for high-quality downscaling
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    def _auto_contrast(self, img: np.ndarray) -> np.ndarray:
        """Apply adaptive contrast enhancement"""
        # Convert to LAB color space
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)

        # Merge and convert back
        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    def _denoise(self, img: np.ndarray) -> np.ndarray:
        """Apply non-local means denoising"""
        return cv2.fastNlMeansDenoisingColored(img, None, 6, 6, 7, 21)

    def _sharpen(self, img: np.ndarray) -> np.ndarray:
        """Apply unsharp masking for sharpening"""
        gaussian = cv2.GaussianBlur(img, (0, 0), 2.0)
        return cv2.addWeighted(img, 1.5, gaussian, -0.5, 0)

    def _color_correct(self, img: np.ndarray) -> np.ndarray:
        """Apply automatic white balance correction"""
        # Simple gray world assumption
        result = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        avg_a = np.average(result[:, :, 1])
        avg_b = np.average(result[:, :, 2])
        result[:, :, 1] = result[:, :, 1] - ((avg_a - 128) * (result[:, :, 0] / 255.0) * 1.1)
        result[:, :, 2] = result[:, :, 2] - ((avg_b - 128) * (result[:, :, 0] / 255.0) * 1.1)
        return cv2.cvtColor(result, cv2.COLOR_LAB2BGR)

    def _calculate_quality_score(self, img: np.ndarray) -> Dict[str, Any]:
        """Comprehensive image quality assessment"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        scores = {}

        # Sharpness (Laplacian variance)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        scores['sharpness'] = min(laplacian_var / 1000, 1.0)

        # Brightness (histogram analysis)
        brightness = np.mean(gray)
        scores['brightness'] = 1.0 - abs(brightness - 127) / 127

        # Contrast (standard deviation)
        contrast = np.std(gray)
        scores['contrast'] = min(contrast / 70, 1.0)

        # Focus (edge density)
        edges = cv2.Canny(gray, 100, 200)
        edge_density = np.sum(edges > 0) / edges.size
        scores['focus'] = min(edge_density * 10, 1.0)

        # Noise estimation
        noise = self._estimate_noise(gray)
        scores['noise'] = max(0, 1.0 - (noise / 30))

        # Color saturation
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        saturation = np.mean(hsv[:, :, 1])
        scores['saturation'] = min(saturation / 128, 1.0)

        # Resolution score
        resolution = img.shape[0] * img.shape[1]
        scores['resolution'] = min(resolution / (1920 * 2560), 1.0)

        # Weighted overall score
        weights = {
            'sharpness': 0.25,
            'brightness': 0.10,
            'contrast': 0.15,
            'focus': 0.20,
            'noise': 0.10,
            'saturation': 0.10,
            'resolution': 0.10
        }

        overall = sum(scores[k] * weights[k] for k in weights)
        scores['overall_score'] = round(overall, 3)
        scores['pass_threshold'] = overall >= 0.85

        # Generate recommendation
        lowest_score = min(scores.items(), key=lambda x: x[1] if x[0] != 'overall_score' and x[0] != 'pass_threshold' else 1.0)
        recommendations = {
            'sharpness': "Image is blurry - improve focus or use higher resolution camera",
            'brightness': "Lighting issue - adjust to avoid over/under exposure",
            'contrast': "Low contrast - use solid background and better lighting",
            'focus': "Camera shake detected - stabilize camera before capture",
            'noise': "High noise - improve lighting conditions",
            'saturation': "Color saturation is low - check color settings",
            'resolution': "Resolution too low - use higher resolution capture"
        }

        if not scores['pass_threshold']:
            scores['recommendation'] = recommendations.get(lowest_score[0], "Improve image quality")
        else:
            scores['recommendation'] = "Image quality acceptable for grading"

        return scores

    def _estimate_noise(self, gray_image: np.ndarray) -> float:
        """Estimate image noise using median absolute deviation"""
        sobel = cv2.Sobel(gray_image, cv2.CV_64F, 1, 1, ksize=3)
        return np.median(np.abs(sobel)) * 1.4826

    def _calculate_hash(self, img: np.ndarray) -> str:
        """Calculate perceptual hash for image deduplication"""
        # Resize to 16x16 for hash
        small = cv2.resize(img, (16, 16), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        # Calculate mean
        mean = gray.mean()

        # Create hash
        bits = (gray > mean).flatten()
        hash_int = sum(b << i for i, b in enumerate(bits))

        return format(hash_int, '064x')

    def image_to_base64(self, image_path: str, max_size: int = 2048) -> str:
        """Convert image to base64 for API calls"""
        img = cv2.imread(image_path)

        # Resize if needed
        h, w = img.shape[:2]
        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)))

        # Encode to JPEG
        _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return base64.b64encode(buffer).decode('utf-8')

    def create_side_by_side(self, front_path: str, back_path: str, output_path: str = None) -> str:
        """Create side-by-side comparison image"""
        front = cv2.imread(front_path)
        back = cv2.imread(back_path)

        # Match heights
        target_height = min(front.shape[0], back.shape[0])

        front_scale = target_height / front.shape[0]
        back_scale = target_height / back.shape[0]

        front = cv2.resize(front, None, fx=front_scale, fy=front_scale)
        back = cv2.resize(back, None, fx=back_scale, fy=back_scale)

        # Create separator
        separator = np.ones((target_height, 10, 3), dtype=np.uint8) * 128

        # Combine
        combined = np.hstack([front, separator, back])

        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            output_path = str(self.output_dir / f"comparison_{timestamp}.jpg")

        cv2.imwrite(output_path, combined, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
        return output_path

    def highlight_defects(
        self,
        image_path: str,
        defects: List[Dict[str, Any]],
        output_path: str = None
    ) -> str:
        """
        Create annotated image with defect highlights

        defects format: [{'type': 'spine_stress', 'location': (x, y, w, h), 'severity': 'minor'}]
        """
        img = cv2.imread(image_path)

        severity_colors = {
            'trace': (0, 255, 0),      # Green
            'minor': (0, 255, 255),    # Yellow
            'moderate': (0, 165, 255), # Orange
            'major': (0, 0, 255),      # Red
            'severe': (128, 0, 128)    # Purple
        }

        for defect in defects:
            if 'location' in defect:
                x, y, w, h = defect['location']
                color = severity_colors.get(defect.get('severity', 'moderate'), (0, 165, 255))

                # Draw rectangle
                cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)

                # Add label
                label = f"{defect.get('type', 'defect')}: {defect.get('severity', '')}"
                cv2.putText(img, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            output_path = str(self.output_dir / f"annotated_{timestamp}.jpg")

        cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
        return output_path

    def batch_process(self, image_paths: List[str], **kwargs) -> List[Dict[str, Any]]:
        """Process multiple images"""
        results = []
        for path in image_paths:
            result = self.process_image(path, **kwargs)
            results.append(result)
        return results


# Global instance
image_processor = ImageProcessor()
