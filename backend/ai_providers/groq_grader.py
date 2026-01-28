"""
Groq Vision Grader - Fast inference using Groq's Llama Vision models
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

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

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
    """Get Groq API key from environment"""
    api_key = os.environ.get('GROQ_API_KEY')
    if api_key:
        logger.info("Using GROQ_API_KEY from environment")
        return api_key
    return None


GRADING_PROMPT = """You are an expert CGC-certified comic book grader and comic book historian.

Analyze this comic book cover image and provide:
1. A numerical grade from 0.5 to 10.0 (use half-point increments)
2. List any defects you see (spine stress, corner wear, color fading, tears, stains, etc.)
3. Your reasoning for the grade
4. COMPREHENSIVE COMIC METADATA (identify from cover or your knowledge)

CGC GRADING SCALE:
- 10.0 Gem Mint: Perfect in every way
- 9.8 Near Mint/Mint: Nearly perfect with minor imperfections
- 9.4 Near Mint: Nearly perfect, tiny handling defects allowed
- 9.0 Very Fine/Near Mint: Minor wear beginning to show
- 8.0 Very Fine: Minor wear apparent, still relatively flat and clean
- 7.0 Fine/Very Fine: Above-average copy with minor defects
- 6.0 Fine: Slight wear, still a nice copy
- 5.0 Very Good/Fine: Average used comic with some wear
- 4.0 Very Good: Shows significant wear but still complete
- 3.0 Good/Very Good: Shows heavy wear
- 2.0 Good: Heavily worn but complete
- 1.0 Fair: Very heavily worn, may have pieces missing

BE STRINGENT - Most circulated comics grade 4.0-7.5. 9.0+ is RARE.

COMIC IDENTIFICATION - Look for:
- title: Main series name (e.g., "Amazing Spider-Man", "Batman")
- issue_number: The ISSUE NUMBER only (not volume, not cover date)
- publisher: DC Comics, Marvel Comics, Image, etc.
- year: Publication year

COMPREHENSIVE METADATA (identify from cover or your knowledge):
- volume, cover_date, cover_price, story_title
- writer, cover_artist, interior_artist, editor
- genre, characters (especially first appearances)
- page_count, format, series_type, era, country, language

KEY ISSUE STATUS:
- is_key_issue: Is this significant?
- key_reasons: first appearance, death, origin, iconic cover
- first_appearances: List any character debuts

RESPOND IN THIS EXACT JSON FORMAT:
{
    "grade": <0.5-10.0>,
    "grade_label": "<CGC label>",
    "confidence": <0.0-1.0>,
    "defects": ["<defect 1>", "<defect 2>"],
    "reasoning": "<brief explanation>",
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
    }
}"""


# Available Groq Vision Models (December 2025)
GROQ_VISION_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",    # Llama 4 Scout - fast, reliable
    "meta-llama/llama-4-maverick-17b-128e-instruct", # Llama 4 Maverick - highest quality
    "llama-3.2-11b-vision-preview",                  # Llama 3.2 Vision - fallback
    "llama-3.2-90b-vision-preview",                  # Llama 3.2 90B - large fallback
]

PRIMARY_GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


async def grade_with_groq(
    image_base64: str,
    model: str = PRIMARY_GROQ_MODEL,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Grade a comic book image using Groq's vision models
    """
    api_key = get_api_key()
    if not api_key:
        return {
            'grade': 0,
            'error': 'GROQ_API_KEY not found in environment',
            'provider': 'Groq'
        }

    try:
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
                            "type": "text",
                            "text": GRADING_PROMPT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')

                    # Parse the response
                    try:
                        # Try to extract JSON from the response (allow nested objects)
                        json_match = re.search(r'\{[\s\S]*\}', content)
                        if json_match:
                            grading_data = json.loads(json_match.group())
                            grade = float(grading_data.get('grade', 6.0))
                            grade = max(0.5, min(10.0, round(grade * 2) / 2))

                            return {
                                'grade': grade,
                                'grade_label': grading_data.get('grade_label', get_grade_label(grade)),
                                'confidence': float(grading_data.get('confidence', 0.8)),
                                'defects': grading_data.get('defects', []),
                                'reasoning': grading_data.get('reasoning', ''),
                                'comic_info': grading_data.get('comic_info', {}),
                                'key_issue_info': grading_data.get('key_issue_info', {}),
                                'model': model,
                                'provider': 'Groq',
                                'icon': '⚡'
                            }
                    except json.JSONDecodeError:
                        pass

                    # Fallback: extract grade from text
                    grade = extract_grade_from_text(content)
                    return {
                        'grade': grade,
                        'grade_label': get_grade_label(grade),
                        'confidence': 0.7,
                        'defects': [],
                        'reasoning': content[:200],
                        'model': model,
                        'provider': 'Groq',
                        'icon': '⚡'
                    }
                else:
                    error_text = await resp.text()
                    logger.error(f"Groq API error: {error_text}")
                    return {
                        'grade': 0,
                        'error': f"Groq API error: {resp.status}",
                        'provider': 'Groq'
                    }
    except Exception as e:
        logger.error(f"Groq grading error: {e}")
        return {
            'grade': 0,
            'error': str(e),
            'provider': 'Groq'
        }


FAST_OCR_PROMPT = """Look at this comic book cover. Extract ONLY the basic info as fast as possible.
RESPOND IN JSON ONLY - NO EXTRA TEXT:
{"title": "<series name>", "issue_number": "<issue # or null>", "publisher": "<publisher or null>"}"""


async def fast_ocr_extract(image_base64: str) -> Dict[str, Any]:
    """
    Ultra-fast OCR to extract just title, issue number, publisher.
    Uses Groq's fastest model with minimal prompt.
    Returns in ~1-2 seconds.
    """
    api_key = get_api_key()
    if not api_key:
        return {'title': 'Unknown', 'issue_number': None, 'publisher': None, 'error': 'No API key'}

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": PRIMARY_GROQ_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": FAST_OCR_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 150
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')

                    # Extract JSON
                    json_match = re.search(r'\{[^}]+\}', content)
                    if json_match:
                        data = json.loads(json_match.group())
                        return {
                            'title': data.get('title', 'Unknown'),
                            'issue_number': data.get('issue_number'),
                            'publisher': data.get('publisher'),
                            'provider': 'Groq-Fast'
                        }

                    return {'title': 'Unknown', 'issue_number': None, 'publisher': None}
                else:
                    logger.error(f"Fast OCR error: {resp.status}")
                    return {'title': 'Unknown', 'issue_number': None, 'publisher': None, 'error': f'API error {resp.status}'}
    except Exception as e:
        logger.error(f"Fast OCR exception: {e}")
        return {'title': 'Unknown', 'issue_number': None, 'publisher': None, 'error': str(e)}


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
# FALLBACK WRAPPER - Use free OpenRouter/Ollama when Groq unavailable
# ═══════════════════════════════════════════════════════════════════════════════

async def grade_with_groq_with_fallback(
    image_base64: str,
    metadata: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Grade comic with automatic fallback to free providers.

    Fallback chain: Groq -> OpenRouter Free Vision -> Ollama Vision
    """
    # Try primary provider first
    result = await grade_with_groq(image_base64, metadata=metadata, **kwargs)

    # If error and fallback available, try alternatives
    if (result.get('error') or result.get('grade', 0) == 0) and FALLBACK_AVAILABLE:
        logger.info(f"Groq grading failed, trying fallbacks...")

        # Use centralized fallback function
        fallback_result = await fallback_grade(
            image_base64=image_base64,
            prompt="Grade this comic book cover on CGC scale (0.5-10.0). Identify title, issue, defects.",
            primary_result=result
        )

        if fallback_result.get('grade', 0) > 0:
            fallback_result['original_provider'] = 'Groq'
            return fallback_result

    return result
