"""
Base64 Image Utilities for AI Vision Graders

Centralizes base64 image processing to ensure consistent handling
across all AI providers (Grok, Together, Hyperbolic, SambaNova, etc.)
"""

import base64
import os
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def clean_and_validate_base64(image_input: str) -> Tuple[str, Optional[str]]:
    """
    Clean and validate base64 image data for AI vision APIs.

    Args:
        image_input: Either a file path OR base64-encoded image data
                    (may include data URL prefix)

    Returns:
        Tuple of (clean_base64_string, error_message)
        If successful, error_message is None
        If failed, clean_base64_string is empty and error_message describes the issue
    """
    try:
        # Case 1: File path - read and encode
        if os.path.exists(image_input):
            try:
                with open(image_input, 'rb') as f:
                    image_data = f.read()

                if len(image_data) == 0:
                    return "", "Image file is empty"

                # Encode to base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                logger.debug(f"Encoded file to base64: {len(image_base64)} chars")
                return image_base64, None

            except Exception as e:
                return "", f"Failed to read image file: {e}"

        # Case 2: Already base64 (possibly with data URL prefix)
        clean_base64 = image_input

        # Remove data URL prefix if present
        # Formats: "data:image/jpeg;base64,..." or "data:image/png;base64,..."
        if clean_base64.startswith('data:'):
            if ',' in clean_base64:
                clean_base64 = clean_base64.split(',', 1)[1]
            else:
                # Malformed data URL - no comma separator
                logger.warning("Data URL missing comma separator")
                # Try to extract after 'base64' keyword
                if 'base64' in clean_base64.lower():
                    idx = clean_base64.lower().find('base64')
                    clean_base64 = clean_base64[idx + 6:].lstrip(';').lstrip(',')

        # Remove any whitespace/newlines that can corrupt base64
        clean_base64 = clean_base64.strip()
        clean_base64 = clean_base64.replace('\n', '')
        clean_base64 = clean_base64.replace('\r', '')
        clean_base64 = clean_base64.replace(' ', '')
        clean_base64 = clean_base64.replace('\t', '')

        # Remove any trailing data URL artifacts
        if ';' in clean_base64[:50]:  # Only check beginning
            clean_base64 = clean_base64.split(';')[-1]

        # Validate: base64 should only contain valid characters
        # Valid base64 chars: A-Z, a-z, 0-9, +, /, =
        import re
        if not re.match(r'^[A-Za-z0-9+/=]+$', clean_base64):
            # Try to extract valid base64 portion
            match = re.search(r'[A-Za-z0-9+/=]{100,}', clean_base64)
            if match:
                clean_base64 = match.group()
                logger.warning("Extracted valid base64 portion from corrupted data")
            else:
                return "", "Invalid base64 characters detected"

        # Fix base64 padding if needed
        # Base64 strings must be multiples of 4 characters
        remainder = len(clean_base64) % 4
        if remainder != 0:
            # Add padding characters
            padding_needed = 4 - remainder
            clean_base64 += '=' * padding_needed
            logger.debug(f"Added {padding_needed} padding characters")

        # Validate by attempting to decode
        try:
            decoded = base64.b64decode(clean_base64)
            if len(decoded) < 100:  # Too small to be a real image
                return "", "Decoded data too small to be a valid image"
            logger.debug(f"Base64 validation successful: {len(decoded)} bytes decoded")
        except Exception as e:
            return "", f"Base64 decode validation failed: {e}"

        return clean_base64, None

    except Exception as e:
        logger.error(f"Base64 cleaning error: {e}")
        return "", str(e)


def prepare_image_for_api(image_input: str, mime_type: str = "image/jpeg") -> Tuple[str, Optional[str]]:
    """
    Prepare image for API submission as a data URL.

    Args:
        image_input: File path or base64 string
        mime_type: MIME type for the data URL (default: image/jpeg)

    Returns:
        Tuple of (data_url, error_message)
    """
    clean_base64, error = clean_and_validate_base64(image_input)

    if error:
        return "", error

    data_url = f"data:{mime_type};base64,{clean_base64}"
    return data_url, None


def get_image_info(image_input: str) -> dict:
    """
    Get information about an image input.

    Returns dict with keys:
        - type: 'file', 'data_url', or 'base64'
        - size_bytes: approximate size
        - valid: boolean
        - error: error message if not valid
    """
    info = {
        'type': 'unknown',
        'size_bytes': 0,
        'valid': False,
        'error': None
    }

    if os.path.exists(image_input):
        info['type'] = 'file'
        try:
            info['size_bytes'] = os.path.getsize(image_input)
            info['valid'] = info['size_bytes'] > 0
        except:
            info['error'] = 'Cannot read file size'
    elif image_input.startswith('data:'):
        info['type'] = 'data_url'
        # Estimate size from base64 length
        if ',' in image_input:
            b64_part = image_input.split(',', 1)[1]
            info['size_bytes'] = int(len(b64_part) * 3 / 4)
        info['valid'] = info['size_bytes'] > 100
    else:
        info['type'] = 'base64'
        info['size_bytes'] = int(len(image_input) * 3 / 4)
        info['valid'] = info['size_bytes'] > 100

    # Validate
    clean, error = clean_and_validate_base64(image_input)
    if error:
        info['valid'] = False
        info['error'] = error

    return info
