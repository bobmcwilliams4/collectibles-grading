"""
Enhanced Image Processing Module v2
Multi-resolution processing, WebP support, and image deduplication
"""

import asyncio
import hashlib
import io
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import struct

logger = logging.getLogger(__name__)

# Try to import image libraries
try:
    from PIL import Image, ImageFilter, ImageEnhance, ExifTags
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow not installed - image processing will be limited")

try:
    import imagehash
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False
    logger.warning("imagehash not installed - perceptual hashing disabled")


class ImageFormat(Enum):
    """Supported image formats"""
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    TIFF = "tiff"
    BMP = "bmp"


class ResolutionTier(Enum):
    """Image resolution tiers"""
    THUMBNAIL = "thumbnail"      # 200px - for previews
    SMALL = "small"              # 500px - for listings
    MEDIUM = "medium"            # 1000px - for AI grading
    LARGE = "large"              # 2000px - for detail analysis
    ORIGINAL = "original"        # Full resolution


@dataclass
class ImageMetadata:
    """Comprehensive image metadata"""
    file_path: str
    file_size: int
    width: int
    height: int
    format: ImageFormat
    color_mode: str
    has_alpha: bool = False
    dpi: Optional[Tuple[int, int]] = None
    exif_data: Dict[str, Any] = field(default_factory=dict)

    # Quality metrics
    sharpness_score: float = 0.0
    brightness_score: float = 0.0
    contrast_score: float = 0.0
    overall_quality: float = 0.0

    # Hashes for deduplication
    md5_hash: str = ""
    perceptual_hash: str = ""
    average_hash: str = ""

    # Processing metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    processing_time_ms: float = 0.0


@dataclass
class ProcessedImage:
    """Result of image processing"""
    original_path: str
    processed_paths: Dict[ResolutionTier, str] = field(default_factory=dict)
    webp_paths: Dict[ResolutionTier, str] = field(default_factory=dict)
    metadata: Optional[ImageMetadata] = None
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    success: bool = True
    errors: List[str] = field(default_factory=list)


class EnhancedImageProcessor:
    """
    Enhanced image processor with multi-resolution and WebP support

    Features:
    - Multi-resolution image generation
    - WebP conversion for size optimization
    - Perceptual hash-based deduplication
    - Quality scoring
    - Batch processing support
    """

    # Resolution configurations
    RESOLUTIONS = {
        ResolutionTier.THUMBNAIL: 200,
        ResolutionTier.SMALL: 500,
        ResolutionTier.MEDIUM: 1000,
        ResolutionTier.LARGE: 2000
    }

    # Quality settings
    JPEG_QUALITY = 90
    WEBP_QUALITY = 85
    WEBP_LOSSLESS = False

    # Deduplication threshold (0-64, lower = more similar)
    DUPLICATE_THRESHOLD = 8

    def __init__(
        self,
        output_dir: str = None,
        generate_webp: bool = True,
        enable_dedup: bool = True
    ):
        self.output_dir = Path(output_dir or "P:/SOVEREIGN_APPS/collectibles_grading_system/images/processed")
        self.generate_webp = generate_webp
        self.enable_dedup = enable_dedup

        # Ensure output directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for tier in ResolutionTier:
            (self.output_dir / tier.value).mkdir(exist_ok=True)
            if generate_webp:
                (self.output_dir / f"{tier.value}_webp").mkdir(exist_ok=True)

        # Hash index for deduplication
        self._hash_index: Dict[str, str] = {}  # perceptual_hash -> original_path
        self._load_hash_index()

    def _load_hash_index(self):
        """Load existing hash index from disk"""
        index_path = self.output_dir / "hash_index.json"
        if index_path.exists():
            try:
                import json
                with open(index_path, 'r') as f:
                    self._hash_index = json.load(f)
                logger.info(f"Loaded {len(self._hash_index)} hashes from index")
            except Exception as e:
                logger.warning(f"Could not load hash index: {e}")

    def _save_hash_index(self):
        """Save hash index to disk"""
        index_path = self.output_dir / "hash_index.json"
        try:
            import json
            with open(index_path, 'w') as f:
                json.dump(self._hash_index, f)
        except Exception as e:
            logger.warning(f"Could not save hash index: {e}")

    async def process_image(
        self,
        image_path: str,
        comic_id: int = None,
        side: str = "front",
        generate_all_sizes: bool = True
    ) -> ProcessedImage:
        """
        Process a single image with multi-resolution and WebP generation

        Args:
            image_path: Path to source image
            comic_id: Optional comic ID for naming
            side: 'front' or 'back'
            generate_all_sizes: Generate all resolution tiers

        Returns:
            ProcessedImage result
        """
        start_time = datetime.utcnow()
        result = ProcessedImage(original_path=image_path)

        if not PIL_AVAILABLE:
            result.success = False
            result.errors.append("Pillow not installed")
            return result

        try:
            # Load image
            img = Image.open(image_path)

            # Extract metadata
            result.metadata = await self._extract_metadata(image_path, img)

            # Check for duplicates
            if self.enable_dedup and result.metadata.perceptual_hash:
                duplicate = self._check_duplicate(result.metadata.perceptual_hash)
                if duplicate:
                    result.is_duplicate = True
                    result.duplicate_of = duplicate
                    logger.info(f"Duplicate detected: {image_path} matches {duplicate}")
                    return result

            # Generate base filename
            base_name = f"{comic_id}_{side}" if comic_id else Path(image_path).stem

            # Store original
            original_path = self._save_image(
                img,
                base_name,
                ResolutionTier.ORIGINAL,
                preserve_format=True
            )
            result.processed_paths[ResolutionTier.ORIGINAL] = original_path

            # Generate resolutions
            if generate_all_sizes:
                for tier, max_size in self.RESOLUTIONS.items():
                    # Skip if image is smaller than target
                    if img.width <= max_size and img.height <= max_size:
                        result.processed_paths[tier] = original_path
                        continue

                    # Resize image
                    resized = self._resize_image(img, max_size)

                    # Save JPEG
                    jpeg_path = self._save_image(resized, base_name, tier)
                    result.processed_paths[tier] = jpeg_path

                    # Generate WebP if enabled
                    if self.generate_webp:
                        webp_path = self._save_webp(resized, base_name, tier)
                        result.webp_paths[tier] = webp_path

            # Update hash index
            if result.metadata.perceptual_hash:
                self._hash_index[result.metadata.perceptual_hash] = image_path
                self._save_hash_index()

            # Calculate processing time
            result.metadata.processing_time_ms = (
                datetime.utcnow() - start_time
            ).total_seconds() * 1000

            return result

        except Exception as e:
            logger.error(f"Image processing error: {e}")
            result.success = False
            result.errors.append(str(e))
            return result

    async def _extract_metadata(
        self,
        image_path: str,
        img: Image.Image
    ) -> ImageMetadata:
        """Extract comprehensive image metadata"""
        file_path = Path(image_path)

        # Basic file info
        file_size = file_path.stat().st_size

        # Format detection
        format_map = {
            'JPEG': ImageFormat.JPEG,
            'PNG': ImageFormat.PNG,
            'WEBP': ImageFormat.WEBP,
            'TIFF': ImageFormat.TIFF,
            'BMP': ImageFormat.BMP
        }
        img_format = format_map.get(img.format, ImageFormat.JPEG)

        # Extract EXIF data
        exif_data = {}
        try:
            if hasattr(img, '_getexif') and img._getexif():
                raw_exif = img._getexif()
                for tag_id, value in raw_exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='ignore')
                        except:
                            value = str(value)
                    exif_data[tag_name] = value
        except Exception as e:
            logger.debug(f"Could not extract EXIF: {e}")

        # DPI extraction
        dpi = img.info.get('dpi', (72, 72))

        # Calculate hashes
        md5_hash = self._calculate_md5(image_path)
        perceptual_hash = self._calculate_perceptual_hash(img)
        average_hash = self._calculate_average_hash(img)

        # Quality scoring
        sharpness = self._calculate_sharpness(img)
        brightness = self._calculate_brightness(img)
        contrast = self._calculate_contrast(img)
        overall_quality = (sharpness * 0.4 + brightness * 0.3 + contrast * 0.3)

        return ImageMetadata(
            file_path=str(image_path),
            file_size=file_size,
            width=img.width,
            height=img.height,
            format=img_format,
            color_mode=img.mode,
            has_alpha='A' in img.mode,
            dpi=dpi,
            exif_data=exif_data,
            sharpness_score=sharpness,
            brightness_score=brightness,
            contrast_score=contrast,
            overall_quality=overall_quality,
            md5_hash=md5_hash,
            perceptual_hash=perceptual_hash,
            average_hash=average_hash
        )

    def _calculate_md5(self, file_path: str) -> str:
        """Calculate MD5 hash of file"""
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)
        return md5.hexdigest()

    def _calculate_perceptual_hash(self, img: Image.Image) -> str:
        """Calculate perceptual hash for image similarity"""
        if not IMAGEHASH_AVAILABLE:
            return ""
        try:
            return str(imagehash.phash(img))
        except Exception as e:
            logger.debug(f"Perceptual hash error: {e}")
            return ""

    def _calculate_average_hash(self, img: Image.Image) -> str:
        """Calculate average hash for quick comparison"""
        if not IMAGEHASH_AVAILABLE:
            return ""
        try:
            return str(imagehash.average_hash(img))
        except Exception as e:
            logger.debug(f"Average hash error: {e}")
            return ""

    def _calculate_sharpness(self, img: Image.Image) -> float:
        """Calculate image sharpness score (0-100)"""
        try:
            # Convert to grayscale
            gray = img.convert('L')

            # Apply Laplacian filter
            laplacian = gray.filter(ImageFilter.FIND_EDGES)

            # Calculate variance (measure of sharpness)
            import statistics
            pixels = list(laplacian.getdata())
            if not pixels:
                return 50.0

            variance = statistics.variance(pixels) if len(pixels) > 1 else 0
            # Normalize to 0-100 scale
            return min(100, variance / 50)
        except Exception:
            return 50.0

    def _calculate_brightness(self, img: Image.Image) -> float:
        """Calculate image brightness score (0-100)"""
        try:
            gray = img.convert('L')
            pixels = list(gray.getdata())
            if not pixels:
                return 50.0

            avg_brightness = sum(pixels) / len(pixels)
            # Convert to 0-100 score (128 is ideal)
            deviation = abs(avg_brightness - 128)
            return max(0, 100 - (deviation / 1.28))
        except Exception:
            return 50.0

    def _calculate_contrast(self, img: Image.Image) -> float:
        """Calculate image contrast score (0-100)"""
        try:
            gray = img.convert('L')
            pixels = list(gray.getdata())
            if not pixels:
                return 50.0

            min_val = min(pixels)
            max_val = max(pixels)
            contrast_range = max_val - min_val

            # Ideal contrast range is around 200
            return min(100, (contrast_range / 2))
        except Exception:
            return 50.0

    def _resize_image(
        self,
        img: Image.Image,
        max_size: int
    ) -> Image.Image:
        """Resize image maintaining aspect ratio"""
        # Calculate new dimensions
        ratio = min(max_size / img.width, max_size / img.height)
        new_width = int(img.width * ratio)
        new_height = int(img.height * ratio)

        # Use high-quality resampling
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _save_image(
        self,
        img: Image.Image,
        base_name: str,
        tier: ResolutionTier,
        preserve_format: bool = False
    ) -> str:
        """Save image in JPEG format"""
        output_dir = self.output_dir / tier.value
        output_path = output_dir / f"{base_name}.jpg"

        # Convert to RGB if necessary (removes alpha)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        img.save(output_path, 'JPEG', quality=self.JPEG_QUALITY, optimize=True)
        return str(output_path)

    def _save_webp(
        self,
        img: Image.Image,
        base_name: str,
        tier: ResolutionTier
    ) -> str:
        """Save image in WebP format"""
        output_dir = self.output_dir / f"{tier.value}_webp"
        output_path = output_dir / f"{base_name}.webp"

        # WebP supports both RGB and RGBA
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')

        img.save(
            output_path,
            'WEBP',
            quality=self.WEBP_QUALITY,
            lossless=self.WEBP_LOSSLESS,
            method=6  # Highest compression effort
        )
        return str(output_path)

    def _check_duplicate(self, perceptual_hash: str) -> Optional[str]:
        """Check if image is a duplicate based on perceptual hash"""
        if not IMAGEHASH_AVAILABLE or not perceptual_hash:
            return None

        try:
            new_hash = imagehash.hex_to_hash(perceptual_hash)

            for existing_hash, existing_path in self._hash_index.items():
                existing = imagehash.hex_to_hash(existing_hash)
                difference = new_hash - existing
                if difference <= self.DUPLICATE_THRESHOLD:
                    return existing_path

            return None
        except Exception as e:
            logger.debug(f"Duplicate check error: {e}")
            return None

    async def process_batch(
        self,
        image_paths: List[str],
        comic_ids: List[int] = None,
        sides: List[str] = None,
        concurrency: int = 4
    ) -> List[ProcessedImage]:
        """
        Process multiple images in parallel

        Args:
            image_paths: List of image paths
            comic_ids: Optional list of comic IDs
            sides: Optional list of sides ('front'/'back')
            concurrency: Max concurrent operations

        Returns:
            List of ProcessedImage results
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def process_with_limit(idx: int, path: str):
            async with semaphore:
                comic_id = comic_ids[idx] if comic_ids and idx < len(comic_ids) else None
                side = sides[idx] if sides and idx < len(sides) else "front"
                return await self.process_image(path, comic_id, side)

        tasks = [
            process_with_limit(i, path)
            for i, path in enumerate(image_paths)
        ]

        return await asyncio.gather(*tasks)

    def get_optimized_path(
        self,
        comic_id: int,
        side: str,
        tier: ResolutionTier = ResolutionTier.MEDIUM,
        prefer_webp: bool = True
    ) -> Optional[str]:
        """
        Get optimal image path for a comic

        Args:
            comic_id: Comic ID
            side: 'front' or 'back'
            tier: Resolution tier
            prefer_webp: Prefer WebP format if available

        Returns:
            Path to optimized image or None
        """
        base_name = f"{comic_id}_{side}"

        if prefer_webp and self.generate_webp:
            webp_path = self.output_dir / f"{tier.value}_webp" / f"{base_name}.webp"
            if webp_path.exists():
                return str(webp_path)

        jpeg_path = self.output_dir / tier.value / f"{base_name}.jpg"
        if jpeg_path.exists():
            return str(jpeg_path)

        return None

    def cleanup_duplicates(self) -> Dict[str, int]:
        """Remove duplicate images and return cleanup statistics"""
        stats = {
            'checked': 0,
            'duplicates_found': 0,
            'space_freed_bytes': 0
        }

        # This would implement duplicate cleanup logic
        # For safety, this is a placeholder that doesn't delete files
        logger.info("Duplicate cleanup would run here (currently disabled for safety)")

        return stats

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage usage statistics"""
        total_size = 0
        file_counts = {}

        for tier in ResolutionTier:
            tier_dir = self.output_dir / tier.value
            if tier_dir.exists():
                files = list(tier_dir.glob('*'))
                count = len(files)
                size = sum(f.stat().st_size for f in files if f.is_file())
                file_counts[tier.value] = {'count': count, 'size_bytes': size}
                total_size += size

            # Check WebP variants
            webp_dir = self.output_dir / f"{tier.value}_webp"
            if webp_dir.exists():
                files = list(webp_dir.glob('*'))
                count = len(files)
                size = sum(f.stat().st_size for f in files if f.is_file())
                file_counts[f"{tier.value}_webp"] = {'count': count, 'size_bytes': size}
                total_size += size

        return {
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'by_tier': file_counts,
            'hash_index_size': len(self._hash_index)
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_processor: Optional[EnhancedImageProcessor] = None


def get_image_processor() -> EnhancedImageProcessor:
    """Get or create image processor instance"""
    global _processor
    if _processor is None:
        _processor = EnhancedImageProcessor()
    return _processor


async def process_comic_image(
    image_path: str,
    comic_id: int,
    side: str = "front"
) -> ProcessedImage:
    """Convenience function for processing a single comic image"""
    processor = get_image_processor()
    return await processor.process_image(image_path, comic_id, side)


# Export public interface
__all__ = [
    'ImageFormat',
    'ResolutionTier',
    'ImageMetadata',
    'ProcessedImage',
    'EnhancedImageProcessor',
    'get_image_processor',
    'process_comic_image',
]
