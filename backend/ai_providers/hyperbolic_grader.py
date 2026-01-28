"""
Hyperbolic AI Vision Grader - Free tier with $10 credit
https://app.hyperbolic.xyz - 60 requests/minute free tier
"""

import asyncio
import aiohttp
import json
import logging
import os
import re
from typing import Dict, Any, Optional
from pathlib import Path

# Load .env file
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        load_dotenv(env_file, override=True)
except ImportError:
    pass

logger = logging.getLogger(__name__)

HYPERBOLIC_API_URL = "https://api.hyperbolic.xyz/v1/chat/completions"

# Hyperbolic Vision Models (December 2025) - From docs.hyperbolic.xyz/docs/supported-models
HYPERBOLIC_VISION_MODELS = [
    "Qwen/Qwen2.5-VL-72B-Instruct",       # Qwen2.5 VL 72B - BF16
    "Qwen/Qwen2.5-VL-7B-Instruct",        # Qwen2.5 VL 7B - BF16, lightweight
    "mistralai/Pixtral-12B-2409",         # Pixtral 12B - BF16
]

PRIMARY_MODEL = "Qwen/Qwen2.5-VL-72B-Instruct"

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
    """Get Hyperbolic API key from environment"""
    api_key = os.environ.get('HYPERBOLIC_API_KEY')
    if api_key:
        logger.info("Using HYPERBOLIC_API_KEY from environment")
        return api_key
    return None


GRADING_PROMPT = """You are an expert CGC-certified comic book grader AND a comic book historian with pricing knowledge.

Analyze this comic book cover image and provide:
1. A numerical grade from 0.5 to 10.0 (use half-point increments)
2. List any defects you see (spine stress, corner wear, color fading, tears, stains, etc.)
3. Your reasoning for the grade
4. Complete comic identification and metadata
5. ESTIMATED MARKET VALUE based on current collector market

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
        "cover_date": "<month year>",
        "cover_price": "<original price>",
        "writer": ["<writer name>"],
        "cover_artist": "<artist name>",
        "characters": ["<character>"],
        "era": "<Golden|Silver|Bronze|Copper|Modern Age>"
    },
    "key_issue_info": {
        "is_key_issue": <true/false>,
        "key_reasons": ["<reason>"],
        "first_appearances": ["<character>"]
    },
    "pricing": {
        "estimated_value_raw": "<USD value for raw/ungraded at this grade>",
        "estimated_value_graded": "<USD value if CGC graded at this grade>",
        "value_range_low": "<low estimate USD>",
        "value_range_high": "<high estimate USD>",
        "pricing_notes": "<factors affecting value>"
    }
}"""


async def grade_with_hyperbolic(
    image_input: str,
    model: str = PRIMARY_MODEL,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Grade a comic book image using Hyperbolic's vision models

    Args:
        image_input: Either a file path OR base64-encoded image data
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
            'error': 'HYPERBOLIC_API_KEY not found in environment',
            'provider': 'Hyperbolic'
        }

    try:
        # Use centralized base64 cleaning utility
        clean_base64, error = clean_and_validate_base64(image_input)
        if error:
            return {
                'error': f'Image processing error: {error}',
                'grade': 0,
                'provider': 'Hyperbolic'
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
                            "type": "text",
                            "text": GRADING_PROMPT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{clean_base64}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.3,
            "max_tokens": 1500
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                HYPERBOLIC_API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')

                    # Parse the response
                    try:
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
                                'model': model,
                                'provider': 'Hyperbolic',
                                'icon': '🌀'
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
                        'provider': 'Hyperbolic',
                        'icon': '🌀'
                    }
                else:
                    error_text = await resp.text()
                    logger.error(f"Hyperbolic API error: {error_text}")

                    # Try fallback model
                    if model == PRIMARY_MODEL and len(HYPERBOLIC_VISION_MODELS) > 1:
                        logger.info("Trying fallback Hyperbolic model...")
                        return await grade_with_hyperbolic(
                            image_input,
                            model=HYPERBOLIC_VISION_MODELS[1],
                            metadata=metadata
                        )

                    return {
                        'grade': 0,
                        'error': f"Hyperbolic API error: {resp.status}",
                        'provider': 'Hyperbolic'
                    }
    except Exception as e:
        logger.error(f"Hyperbolic grading error: {e}")
        return {
            'grade': 0,
            'error': str(e),
            'provider': 'Hyperbolic'
        }


def extract_grade_from_text(text: str) -> float:
    """Extract grade from text response"""
    patterns = [
        r'grade[:\s]+([\d.]+)',
        r'([\d.]+)\s*/\s*10',
        r'([\d.]+)\s+(?:out of|\/)\s*10',
    ]

    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            grade = float(match.group(1))
            if 0 <= grade <= 10:
                return round(grade * 2) / 2

    return 6.0  # Default grade
