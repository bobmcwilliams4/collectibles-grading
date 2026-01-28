"""
Cloudflare Workers AI Grader - Free vision inference
Uses Cloudflare's Workers AI with Llama 3.2 Vision models
Free tier: 10,000 neurons/day

Requires:
- CLOUDFLARE_ACCOUNT_ID
- CLOUDFLARE_API_TOKEN (with Workers AI permissions)
"""

import asyncio
import aiohttp
import json
import logging
import os
import re
from typing import Dict, Any, Optional, List
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

try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        load_dotenv(env_file, override=True)
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Cloudflare Workers AI vision models
CLOUDFLARE_VISION_MODELS = [
    "@cf/meta/llama-3.2-11b-vision-instruct",  # Primary vision model
]

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


def get_credentials() -> tuple:
    """Get Cloudflare credentials from environment"""
    account_id = os.environ.get('CLOUDFLARE_ACCOUNT_ID')
    api_token = os.environ.get('CLOUDFLARE_API_TOKEN')
    return account_id, api_token


async def grade_with_cloudflare(
    image_base64: str,
    model: str = "@cf/meta/llama-3.2-11b-vision-instruct",
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Grade a comic using Cloudflare Workers AI vision model

    Args:
        image_base64: Base64-encoded image
        model: Cloudflare model ID
        metadata: Optional comic metadata

    Returns:
        Grading result dict
    """
    account_id, api_token = get_credentials()

    if not account_id or not api_token:
        return {
            'grade': 0,
            'error': 'CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN not configured',
            'provider': 'Cloudflare'
        }

    api_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"

    prompt = """You are a professional CGC-certified comic book grader.
Analyze this comic book cover and provide a detailed condition assessment.

GRADING SCALE (CGC 10-point scale):
- 10.0 Gem Mint: Perfect
- 9.8-9.9 Near Mint/Mint: Nearly perfect
- 9.4-9.6 Near Mint: Minor imperfections
- 8.0-9.2 Very Fine: Light wear
- 6.0-7.5 Fine: Moderate wear
- 4.0-5.5 Very Good: Significant wear
- 2.0-3.5 Good: Heavy wear
- 0.5-1.8 Fair/Poor: Major defects

BE STRINGENT - Most comics grade 4.0-7.5. 9.0+ is RARE.

Examine: cover tears/creases, spine stress, corner wear, edge chips, staple rust.

Identify: title, issue number, publisher, year, key issue status.

Respond in JSON:
{
    "grade": <0.5-10.0>,
    "grade_label": "<CGC label>",
    "confidence": <0.0-1.0>,
    "defects": [{"type": "<defect>", "severity": "<severity>", "location": "<where>"}],
    "reasoning": "<explanation>",
    "comic_info": {
        "title": "<series>",
        "issue_number": "<issue #>",
        "publisher": "<publisher>",
        "year": "<year>"
    },
    "key_issue_info": {
        "is_key_issue": <true/false>,
        "key_reasons": ["<reason>"]
    }
}"""

    try:
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "image": [image_base64],
            "prompt": prompt,
            "max_tokens": 1500
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()

                    if result.get('success'):
                        response_text = result.get('result', {}).get('response', '')
                        grading_result = parse_grading_response(response_text)
                        grading_result['model'] = model.split('/')[-1]
                        grading_result['provider'] = 'Cloudflare'
                        grading_result['icon'] = '☁️'
                        return grading_result
                    else:
                        errors = result.get('errors', [])
                        return {
                            'grade': 0,
                            'error': str(errors),
                            'provider': 'Cloudflare'
                        }
                else:
                    error_text = await resp.text()
                    logger.error(f"Cloudflare API error: {error_text}")
                    return {
                        'grade': 0,
                        'error': f"API error: {resp.status}",
                        'provider': 'Cloudflare'
                    }

    except Exception as e:
        logger.error(f"Cloudflare grading error: {e}")
        return {
            'grade': 0,
            'error': str(e),
            'provider': 'Cloudflare'
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
                'confidence': float(data.get('confidence', 0.75)),
                'defects': data.get('defects', []),
                'reasoning': data.get('reasoning', ''),
                'comic_info': data.get('comic_info', {}),
                'key_issue_info': data.get('key_issue_info', {})
            }
    except json.JSONDecodeError:
        pass

    return {
        'grade': 6.0,
        'grade_label': 'Fine',
        'confidence': 0.5,
        'defects': [],
        'reasoning': response_text[:500],
        'comic_info': {},
        'key_issue_info': {}
    }


async def check_cloudflare_available() -> bool:
    """Check if Cloudflare credentials are configured"""
    account_id, api_token = get_credentials()
    return bool(account_id and api_token)

# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACK WRAPPER - Use free OpenRouter/Ollama when Cloudflare unavailable
# ═══════════════════════════════════════════════════════════════════════════════

async def grade_with_cloudflare_with_fallback(
    image_base64: str,
    metadata: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Grade comic with automatic fallback to free providers.

    Fallback chain: Cloudflare -> OpenRouter Free Vision -> Ollama Vision
    """
    # Try primary provider first
    result = await grade_with_cloudflare(image_base64, metadata=metadata, **kwargs)

    # If error and fallback available, try alternatives
    if (result.get('error') or result.get('grade', 0) == 0) and FALLBACK_AVAILABLE:
        logger.info(f"Cloudflare grading failed, trying fallbacks...")

        # Use centralized fallback function
        fallback_result = await fallback_grade(
            image_base64=image_base64,
            prompt="Grade this comic book cover on CGC scale (0.5-10.0). Identify title, issue, defects.",
            primary_result=result
        )

        if fallback_result.get('grade', 0) > 0:
            fallback_result['original_provider'] = 'Cloudflare'
            return fallback_result

    return result
