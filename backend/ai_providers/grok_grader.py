"""
xAI Grok Vision Grader - Uses Grok's vision models for comic grading
Requires XAI_API_KEY or GROK_API_KEY in environment
"""

import asyncio
import aiohttp
import json
import logging
import os
import re
from typing import Dict, Any, Optional
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACK PROVIDERS - OpenRouter Free Vision & Ollama Local
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from .fallback_providers import (
        openrouter_vision_fallback,
        ollama_vision_fallback,
        grade_with_fallback as fallback_grade
    )
    FALLBACK_AVAILABLE = True
except ImportError:
    FALLBACK_AVAILABLE = False

# Load .env file at import time (override system env vars)
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        load_dotenv(env_file, override=True)
except ImportError:
    pass  # dotenv not installed

logger = logging.getLogger(__name__)

# xAI Grok API endpoint (OpenAI-compatible)
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

# CGC Grading Scale
CGC_GRADES = {
    10.0: "Gem Mint", 9.9: "Mint", 9.8: "Near Mint/Mint",
    9.6: "Near Mint+", 9.4: "Near Mint", 9.2: "Near Mint-",
    9.0: "Very Fine/Near Mint", 8.5: "Very Fine+", 8.0: "Very Fine",
    7.5: "Very Fine-", 7.0: "Fine/Very Fine", 6.5: "Fine+",
    6.0: "Fine", 5.5: "Fine-", 5.0: "Very Good/Fine",
    4.5: "Very Good+", 4.0: "Very Good", 3.5: "Very Good-",
    3.0: "Good/Very Good", 2.5: "Good+", 2.0: "Good",
    1.8: "Good-", 1.5: "Fair/Good", 1.0: "Fair", 0.5: "Poor"
}

def get_grade_label(grade: float) -> str:
    closest = min(CGC_GRADES.keys(), key=lambda x: abs(x - grade))
    return CGC_GRADES[closest]


def get_api_key() -> Optional[str]:
    """Get xAI/Grok API key from environment"""
    # Try XAI_API_KEY first, then GROK_API_KEY
    api_key = os.environ.get('XAI_API_KEY') or os.environ.get('GROK_API_KEY')
    if api_key:
        logger.info("Using xAI/Grok API key from environment")
        return api_key
    return None


GRADING_PROMPT = """You are a professional CGC-certified comic book grader with decades of experience AND a comic book historian with pricing knowledge.
Analyze this comic book cover image and provide a detailed condition assessment, comprehensive comic metadata, AND ESTIMATED MARKET VALUE.

GRADING SCALE (CGC 10-point scale):
- 10.0 Gem Mint: Perfect, flawless
- 9.8-9.9 Near Mint/Mint: Near perfect
- 9.4-9.6 Near Mint: Minor imperfections only
- 8.0-9.2 Very Fine: Light wear, minor defects
- 6.0-7.5 Fine: Moderate wear, creases allowed
- 4.0-5.5 Very Good: Significant wear
- 2.0-3.5 Good: Heavy wear
- 0.5-1.8 Fair/Poor: Major defects

BE STRINGENT - Most circulated comics grade 4.0-7.5. 9.0+ is RARE.

Examine:
1. COVER: Tears, creases, folds, stains, fading
2. SPINE: Stress marks, color breaks, rolling
3. CORNERS: Blunting, bends
4. EDGES: Wear, chips
5. STAPLES: Rust, missing

COMIC IDENTIFICATION (CRITICAL):
- title: The main series name (e.g., "Amazing Spider-Man", "Batman", "X-Men")
- issue_number: The specific ISSUE NUMBER of this comic (just the number, e.g., "129")
- publisher: DC Comics, Marvel Comics, Image, etc.
- year: Publication year

COMPREHENSIVE METADATA (Identify from cover or your knowledge):
- volume, cover_date, cover_price, story_title
- writer, cover_artist, interior_artist, editor
- genre, characters (especially first appearances)
- page_count, format, series_type, era, country, language

KEY ISSUE STATUS:
- is_key_issue: Is this significant?
- key_reasons: first appearance, death, origin, iconic cover
- first_appearances: List any character debuts

PRICING (Estimate current collector market values):
- estimated_value_raw: USD value for raw/ungraded at this grade
- estimated_value_graded: USD value if CGC graded at this grade
- value_range: Low to high estimates

Respond in EXACT JSON format:
{
    "grade": <0.5-10.0>,
    "grade_label": "<CGC label>",
    "confidence": <0.0-1.0>,
    "defects": [
        {"type": "<defect>", "severity": "<trace|minor|moderate|major>", "location": "<where>", "penalty": <0.1-2.0>}
    ],
    "reasoning": "<explanation>",
    "comic_info": {
        "title": "<series name>",
        "issue_number": "<issue # only>",
        "publisher": "<publisher>",
        "year": "<year>",
        "volume": "<volume # or null>",
        "cover_date": "<month year>",
        "cover_price": "<original price>",
        "story_title": "<main story or null>",
        "writer": ["<writer name>"],
        "cover_artist": "<cover artist or null>",
        "interior_artist": "<artist or null>",
        "editor": "<editor or null>",
        "genre": ["<genre>"],
        "characters": ["<character>"],
        "page_count": <number or null>,
        "format": "<format type>",
        "series_type": "<ongoing|limited|one-shot|annual>",
        "era": "<Golden|Silver|Bronze|Copper|Modern Age>",
        "country": "<country>",
        "language": "<language>"
    },
    "key_issue_info": {
        "is_key_issue": <true/false>,
        "key_reasons": ["<reason>"],
        "first_appearances": ["<character>"],
        "notable_events": ["<event>"]
    },
    "pricing": {
        "estimated_value_raw": "<USD value for raw/ungraded at this grade>",
        "estimated_value_graded": "<USD value if CGC graded at this grade>",
        "value_range_low": "<low estimate USD>",
        "value_range_high": "<high estimate USD>",
        "pricing_notes": "<factors affecting value>"
    }
}"""


async def grade_with_grok(
    image_input: str,
    model: str = "grok-2-vision-1212",
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Grade a comic book image using xAI Grok's vision models

    Args:
        image_input: Either a file path OR base64-encoded image data
        model: Grok model to use (grok-2-vision-1212)
        metadata: Optional comic metadata

    Returns:
        Grading result dict
    """
    # Import centralized base64 utility
    try:
        from .base64_utils import clean_and_validate_base64
    except ImportError:
        from ai_providers.base64_utils import clean_and_validate_base64

    api_key = get_api_key()
    if not api_key:
        return {
            'grade': 0,
            'error': 'XAI_API_KEY/GROK_API_KEY not found in environment',
            'provider': 'xAI Grok'
        }

    try:
        # Use centralized base64 cleaning utility
        clean_base64, error = clean_and_validate_base64(image_input)
        if error:
            return {
                'error': f'Image processing error: {error}',
                'grade': 0,
                'provider': 'xAI Grok'
            }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{clean_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": GRADING_PROMPT
                        }
                    ]
                }
            ],
            "temperature": 0.3,
            "max_tokens": 2000
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                GROK_API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')

                    # Parse the response
                    grading_result = parse_grading_response(content)
                    grading_result['model'] = model
                    grading_result['provider'] = 'xAI Grok'
                    grading_result['icon'] = '🤖'

                    return grading_result
                else:
                    error_text = await resp.text()
                    logger.error(f"Grok API error: {error_text}")
                    return {
                        'grade': 0,
                        'error': f"Grok API error: {resp.status}",
                        'provider': 'xAI Grok'
                    }
    except Exception as e:
        logger.error(f"Grok grading error: {e}")
        return {
            'grade': 0,
            'error': str(e),
            'provider': 'xAI Grok'
        }


def parse_grading_response(response_text: str) -> Dict[str, Any]:
    """Parse AI response into structured data"""
    try:
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            data = json.loads(json_match.group())
            grade = float(data.get('grade', 6.0))
            grade = max(0.5, min(10.0, grade))
            grade = round(grade * 2) / 2

            return {
                'grade': grade,
                'grade_label': data.get('grade_label', get_grade_label(grade)),
                'confidence': float(data.get('confidence', 0.85)),
                'defects': data.get('defects', []),
                'reasoning': data.get('reasoning', ''),
                'comic_info': data.get('comic_info', {}),
                'key_issue_info': data.get('key_issue_info', {})
            }
    except json.JSONDecodeError:
        pass

    # Fallback - extract grade from text
    grade = extract_grade_from_text(response_text)
    return {
        'grade': grade,
        'grade_label': get_grade_label(grade),
        'confidence': 0.6,
        'defects': [],
        'reasoning': response_text[:500],
        'comic_info': {},
        'key_issue_info': {}
    }


def extract_grade_from_text(text: str) -> float:
    """Extract grade from text response"""
    patterns = [
        r'grade[:\s]+(\d+\.?\d*)',
        r'(\d+\.?\d*)\s*/\s*10',
        r'(\d+\.?\d*)\s+(?:out of|\/)\s*10',
    ]

    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            grade = float(match.group(1))
            if 0 <= grade <= 10:
                return round(grade * 2) / 2

    return 6.0  # Default grade

# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACK WRAPPER - Use free OpenRouter/Ollama when Grok/xAI unavailable
# ═══════════════════════════════════════════════════════════════════════════════

async def grade_with_grok_with_fallback(
    image_base64: str,
    metadata: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Grade comic with automatic fallback to free providers.

    Fallback chain: Grok/xAI -> OpenRouter Free Vision -> Ollama Vision
    """
    # Try primary provider first
    result = await grade_with_grok(image_base64, metadata=metadata, **kwargs)

    # If error and fallback available, try alternatives
    if (result.get('error') or result.get('grade', 0) == 0) and FALLBACK_AVAILABLE:
        logger.info(f"Grok/xAI grading failed, trying fallbacks...")

        # Use centralized fallback function
        fallback_result = await fallback_grade(
            image_base64=image_base64,
            prompt="Grade this comic book cover on CGC scale (0.5-10.0). Identify title, issue, defects.",
            primary_result=result
        )

        if fallback_result.get('grade', 0) > 0:
            fallback_result['original_provider'] = 'Grok/xAI'
            return fallback_result

    return result
