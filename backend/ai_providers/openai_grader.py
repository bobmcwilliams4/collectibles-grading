"""
OpenAI Vision Grader - GPT-4 Vision for comic book grading
"""

import asyncio
import aiohttp
import json
import logging
import os
import re
from typing import Dict, Any, Optional
from pathlib import Path

# Load .env file at import time (override system env vars)
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        load_dotenv(env_file, override=True)
except ImportError:
    pass  # dotenv not installed

logger = logging.getLogger(__name__)

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

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
    """Get OpenAI API key from environment"""
    api_key = os.environ.get('OPENAI_API_KEY')
    if api_key:
        logger.info("Using OPENAI_API_KEY from environment")
        return api_key
    return None


GRADING_PROMPT = """You are an expert comic book grader following the CGC grading scale (0.5 to 10.0).

Analyze this comic book cover image and provide:
1. A numerical grade from 0.5 to 10.0 (use half-point increments: 0.5, 1.0, 1.5, etc.)
2. List any defects you see (spine stress, corner wear, color fading, tears, stains, etc.)
3. Your reasoning for the grade

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

RESPOND IN THIS EXACT JSON FORMAT:
{
    "grade": <number from 0.5 to 10.0>,
    "grade_label": "<label like 'Near Mint' or 'Very Fine'>",
    "confidence": <number from 0.0 to 1.0>,
    "defects": ["<defect 1>", "<defect 2>"],
    "reasoning": "<brief explanation>"
}"""


async def grade_with_openai(
    image_base64: str,
    model: str = "gpt-4o",
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Grade a comic book image using OpenAI's GPT-4 Vision
    """
    api_key = get_api_key()
    if not api_key:
        return {
            'grade': 0,
            'error': 'OPENAI_API_KEY not found in environment',
            'provider': 'OpenAI'
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
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": "high"
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
                OPENAI_API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')

                    # Parse the response
                    try:
                        # Try to extract JSON from the response
                        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                        if json_match:
                            grading_data = json.loads(json_match.group())
                            grade = float(grading_data.get('grade', 6.0))
                            grade = max(0.5, min(10.0, round(grade * 2) / 2))

                            return {
                                'grade': grade,
                                'grade_label': grading_data.get('grade_label', get_grade_label(grade)),
                                'confidence': float(grading_data.get('confidence', 0.85)),
                                'defects': grading_data.get('defects', []),
                                'reasoning': grading_data.get('reasoning', ''),
                                'model': model,
                                'provider': 'OpenAI',
                                'icon': '🧠'
                            }
                    except json.JSONDecodeError:
                        pass

                    # Fallback: extract grade from text
                    grade = extract_grade_from_text(content)
                    return {
                        'grade': grade,
                        'grade_label': get_grade_label(grade),
                        'confidence': 0.75,
                        'defects': [],
                        'reasoning': content[:200],
                        'model': model,
                        'provider': 'OpenAI',
                        'icon': '🧠'
                    }
                else:
                    error_text = await resp.text()
                    logger.error(f"OpenAI API error: {error_text}")
                    return {
                        'grade': 0,
                        'error': f"OpenAI API error: {resp.status}",
                        'provider': 'OpenAI'
                    }
    except Exception as e:
        logger.error(f"OpenAI grading error: {e}")
        return {
            'grade': 0,
            'error': str(e),
            'provider': 'OpenAI'
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
