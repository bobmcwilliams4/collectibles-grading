"""
Gemini Vision Grader - Uses Google's Gemini API for comic grading
Requires GOOGLE_API_KEY in environment or config
"""

import asyncio
import aiohttp
import base64
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

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

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
    """Get Gemini API key from environment or config"""
    # Check environment first
    api_key = os.environ.get('GOOGLE_API_KEY')
    if api_key:
        return api_key

    # Check config file
    config_path = Path(__file__).parent.parent / "config" / "ai_config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
                api_key = config.get('google', {}).get('api_key')
                if api_key:
                    return api_key
        except:
            pass

    return None


async def grade_with_gemini(
    image_input: str,
    metadata: Optional[Dict] = None,
    cover_side: str = 'front'
) -> Dict[str, Any]:
    """
    Grade a comic cover using Google Gemini's vision API

    Args:
        image_input: Either a file path OR base64-encoded image data
        metadata: Optional comic metadata
        cover_side: 'front' or 'back'

    Returns:
        Grading result dict
    """
    api_key = get_api_key()
    if not api_key:
        return {
            'error': 'GOOGLE_API_KEY not configured',
            'grade': 0,
            'model': 'gemini-2.0-flash',
            'provider': 'Google'
        }

    metadata = metadata or {}
    
    # Convert file path to base64 if needed
    image_base64 = image_input
    if os.path.exists(image_input):
        # It's a file path - read and encode
        try:
            with open(image_input, 'rb') as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            return {
                'error': f'Failed to read image file: {e}',
                'grade': 0,
                'model': 'gemini-2.0-flash', 
                'provider': 'Google'
            }
    elif image_input.startswith('data:'):
        # Remove data URL prefix if present
        image_base64 = image_input.split(',', 1)[1] if ',' in image_input else image_input

    prompt = f"""You are a professional CGC-certified comic book grader and comic book historian.
Analyze this {cover_side} cover image and provide a detailed condition assessment AND comprehensive comic metadata.

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

COMIC IDENTIFICATION (CRITICAL - READ CAREFULLY):
- title: The main series name (e.g., "Amazing Spider-Man", "Batman", "Teen Titans", "X-Men")
- issue_number: VERY IMPORTANT - Look for the ACTUAL ISSUE NUMBER printed on the cover.
  * WARNING: DC COMICS COVER DATE FORMAT - Many DC comics show "OCT NO. 12" or "JAN NO. 5"
    on the cover. The month (OCT, JAN, etc.) is the COVER DATE, NOT part of the issue number!
    In "OCT NO. 12", the issue number is "12", NOT "OCT" or "OCT 12".
  * Look for the ISSUE NUMBER separately from any month abbreviation
  * It is usually in the corner box (top left/right) or near the title with "#" symbol
  * Common patterns: "#12", "#129", "NO. 5", "ISSUE 42"
  * ONLY report the NUMBER itself (e.g., "12" not "#12", not "OCT NO. 12")
  * DO NOT USE: Cover dates (OCT, JAN, etc.), cover prices ($0.12, $0.25), volume numbers (Vol. 2),
    variant letters (A, B, C), barcode numbers, or years
  * If unsure, report "Unknown" rather than guessing wrong
- publisher: DC Comics, Marvel Comics, Image, etc.
- year: Publication year (often in corner box or indicia)

COMPREHENSIVE METADATA (Identify from cover or your knowledge):
- volume: Volume number if multi-volume series (e.g., "2" for Vol. 2)
- cover_date: Month and year from cover (e.g., "October 1974", "Jan 1985")
- cover_price: Original cover price (e.g., "$0.25", "$1.99", "12 cents")
- story_title: Main story title if visible or known
- writer: Writer(s) name(s) - use your comic knowledge
- cover_artist: Cover artist if known
- interior_artist: Interior penciler if known
- editor: Editor if known
- genre: Genre(s) - superhero, horror, western, romance, sci-fi, etc.
- characters: Main characters featured (especially first appearances)
- page_count: Standard page count for era (Golden Age ~64pp, Silver Age ~32pp, Modern ~22-32pp)
- format: Standard, Giant-Size, Annual, One-Shot, etc.
- upc_barcode: UPC/barcode number if visible
- indicia_title: Official indicia title if different from cover title
- series_type: Ongoing, Limited Series, One-Shot, Annual
- era: Golden Age (1938-1956), Silver Age (1956-1970), Bronze Age (1970-1985), Copper Age (1985-1991), Modern Age (1991+)
- country: Country of publication (USA, UK, etc.)
- language: Language of publication

KEY ISSUE STATUS:
- is_key_issue: Is this a significant/key issue?
- key_reasons: Why is it key? (first appearance, death, origin, iconic cover, etc.)
- first_appearances: List any first appearances of characters
- notable_events: Deaths, marriages, costume changes, crossovers

Respond in EXACT JSON format:
{{
    "grade": <0.5-10.0>,
    "grade_label": "<CGC label>",
    "confidence": <0.0-1.0>,
    "defects": [
        {{"type": "<defect>", "severity": "<trace|minor|moderate|major>", "location": "<where>", "penalty": <0.1-2.0>}}
    ],
    "reasoning": "<explanation>",
    "comic_info": {{
        "title": "<series name>",
        "issue_number": "<issue # only, e.g. 129>",
        "publisher": "<publisher>",
        "year": "<year>",
        "volume": "<volume # or null>",
        "cover_date": "<month year>",
        "cover_price": "<original price>",
        "story_title": "<main story title or null>",
        "writer": ["<writer name>"],
        "cover_artist": "<cover artist or null>",
        "interior_artist": "<interior artist or null>",
        "editor": "<editor or null>",
        "genre": ["<genre>"],
        "characters": ["<character name>"],
        "page_count": <number or null>,
        "format": "<format type>",
        "upc_barcode": "<barcode or null>",
        "indicia_title": "<indicia title or null>",
        "series_type": "<ongoing|limited|one-shot|annual>",
        "era": "<era name>",
        "country": "<country>",
        "language": "<language>"
    }},
    "key_issue_info": {{
        "is_key_issue": <true/false>,
        "key_reasons": ["<reason>"],
        "first_appearances": ["<character>"],
        "notable_events": ["<event>"]
    }}
}}"""

    try:
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 2000
            }
        }

        url = f"{GEMINI_API_URL}?key={api_key}"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Gemini API error: {error_text}")
                    return {
                        'error': f'Gemini API error: {resp.status}',
                        'grade': 0,
                        'model': 'gemini-2.0-flash',
                        'provider': 'Google'
                    }

                result = await resp.json()

                # Extract text from response
                response_text = ""
                if 'candidates' in result and len(result['candidates']) > 0:
                    parts = result['candidates'][0].get('content', {}).get('parts', [])
                    for part in parts:
                        if 'text' in part:
                            response_text += part['text']

                # Parse JSON from response
                grading_result = parse_grading_response(response_text)
                grading_result['model'] = 'gemini-2.0-flash'
                grading_result['provider'] = 'Google'
                grading_result['icon'] = '💎'

                return grading_result

    except asyncio.TimeoutError:
        return {'error': 'Timeout', 'grade': 0, 'model': 'gemini-2.0-flash', 'provider': 'Google'}
    except Exception as e:
        logger.error(f"Gemini grading error: {e}")
        return {'error': str(e), 'grade': 0, 'model': 'gemini-2.0-flash', 'provider': 'Google'}


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

    # Fallback
    return {
        'grade': 6.0,
        'grade_label': 'Fine',
        'confidence': 0.6,
        'defects': [],
        'reasoning': response_text[:500],
        'comic_info': {},
        'key_issue_info': {}
    }

# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACK WRAPPER - Use free OpenRouter/Ollama when Gemini/Google unavailable
# ═══════════════════════════════════════════════════════════════════════════════

async def grade_with_gemini_with_fallback(
    image_base64: str,
    metadata: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Grade comic with automatic fallback to free providers.

    Fallback chain: Gemini/Google -> OpenRouter Free Vision -> Ollama Vision
    """
    # Try primary provider first
    result = await grade_with_gemini(image_base64, metadata=metadata, **kwargs)

    # If error and fallback available, try alternatives
    if (result.get('error') or result.get('grade', 0) == 0) and FALLBACK_AVAILABLE:
        logger.info(f"Gemini/Google grading failed, trying fallbacks...")

        # Use centralized fallback function
        fallback_result = await fallback_grade(
            image_base64=image_base64,
            prompt="Grade this comic book cover on CGC scale (0.5-10.0). Identify title, issue, defects.",
            primary_result=result
        )

        if fallback_result.get('grade', 0) > 0:
            fallback_result['original_provider'] = 'Gemini/Google'
            return fallback_result

    return result
