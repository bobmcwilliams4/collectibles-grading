"""
HuggingFace Inference API Grader - Free vision inference
Uses HuggingFace's Inference API for vision models
Free tier: 1 request/second, 500K tokens/minute

Requires: HUGGINGFACE_API_KEY
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

# HuggingFace vision models available via Inference API
HUGGINGFACE_VISION_MODELS = [
    "meta-llama/Llama-3.2-11B-Vision-Instruct",
    "Qwen/Qwen2-VL-7B-Instruct",
    "microsoft/Phi-3.5-vision-instruct",
    "llava-hf/llava-1.5-7b-hf",
]

HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models"

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
    """Get HuggingFace API key from environment"""
    api_key = os.environ.get('HUGGINGFACE_API_KEY') or os.environ.get('HF_API_KEY')
    if api_key:
        logger.info("Using HUGGINGFACE_API_KEY from environment")
        return api_key
    return None


async def grade_with_huggingface(
    image_base64: str,
    model: str = "meta-llama/Llama-3.2-11B-Vision-Instruct",
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Grade a comic using HuggingFace Inference API

    Args:
        image_base64: Base64-encoded image
        model: HuggingFace model ID
        metadata: Optional comic metadata

    Returns:
        Grading result dict
    """
    api_key = get_api_key()

    if not api_key:
        return {
            'grade': 0,
            'error': 'HUGGINGFACE_API_KEY not configured',
            'provider': 'HuggingFace'
        }

    api_url = f"{HUGGINGFACE_API_URL}/{model}"

    prompt = """You are a professional CGC-certified comic book grader.
Analyze this comic book cover and provide a condition assessment.

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

Examine: cover, spine, corners, edges, staples.

Respond in JSON:
{
    "grade": <0.5-10.0>,
    "grade_label": "<CGC label>",
    "confidence": <0.0-1.0>,
    "defects": [{"type": "<defect>", "severity": "<severity>", "location": "<where>"}],
    "reasoning": "<explanation>",
    "comic_info": {"title": "<series>", "issue_number": "<issue #>", "publisher": "<publisher>"},
    "key_issue_info": {"is_key_issue": <true/false>, "key_reasons": ["<reason>"]}
}"""

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # HuggingFace Inference API format for vision models
        payload = {
            "inputs": {
                "image": f"data:image/jpeg;base64,{image_base64}",
                "text": prompt
            },
            "parameters": {
                "max_new_tokens": 1500,
                "temperature": 0.3
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()

                    # Handle different response formats
                    if isinstance(result, list) and len(result) > 0:
                        response_text = result[0].get('generated_text', '')
                    elif isinstance(result, dict):
                        response_text = result.get('generated_text', '') or result.get('text', '')
                    else:
                        response_text = str(result)

                    grading_result = parse_grading_response(response_text)
                    grading_result['model'] = model.split('/')[-1]
                    grading_result['provider'] = 'HuggingFace'
                    grading_result['icon'] = '🤗'
                    return grading_result

                elif resp.status == 503:
                    # Model loading - retry after delay
                    logger.info(f"HuggingFace model loading: {model}")
                    return {
                        'grade': 0,
                        'error': 'Model loading - retry in 30s',
                        'provider': 'HuggingFace'
                    }
                else:
                    error_text = await resp.text()
                    logger.error(f"HuggingFace API error: {error_text}")
                    return {
                        'grade': 0,
                        'error': f"API error: {resp.status}",
                        'provider': 'HuggingFace'
                    }

    except Exception as e:
        logger.error(f"HuggingFace grading error: {e}")
        return {
            'grade': 0,
            'error': str(e),
            'provider': 'HuggingFace'
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
                'confidence': float(data.get('confidence', 0.7)),
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


async def multi_model_huggingface_grade(
    image_base64: str,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Grade using multiple HuggingFace models and calculate consensus
    """
    models = HUGGINGFACE_VISION_MODELS[:3]  # Use top 3

    tasks = [grade_with_huggingface(image_base64, model, metadata) for model in models]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    valid_results = []
    ai_grades = {}

    for i, result in enumerate(results):
        if isinstance(result, dict) and not result.get('error') and result.get('grade', 0) > 0:
            valid_results.append(result)
            model_id = models[i].replace('/', '_')
            ai_grades[model_id] = {
                'grade': result['grade'],
                'confidence': result.get('confidence', 0.7),
                'model_name': result.get('model', models[i]),
                'provider': 'HuggingFace'
            }

    if not valid_results:
        return {
            'error': 'All HuggingFace grading attempts failed',
            'consensus_grade': 0,
            'ai_grades': ai_grades
        }

    grades = [r['grade'] for r in valid_results]
    avg_grade = sum(grades) / len(grades)
    consensus = round(avg_grade * 2) / 2

    return {
        'consensus_grade': consensus,
        'grade_label': get_grade_label(consensus),
        'ai_grades': ai_grades,
        'model_count': len(valid_results),
        'provider': 'HuggingFace'
    }


async def check_huggingface_available() -> bool:
    """Check if HuggingFace API is configured"""
    return get_api_key() is not None

# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACK WRAPPER - Use free OpenRouter/Ollama when HuggingFace unavailable
# ═══════════════════════════════════════════════════════════════════════════════

async def grade_with_huggingface_with_fallback(
    image_base64: str,
    metadata: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Grade comic with automatic fallback to free providers.

    Fallback chain: HuggingFace -> OpenRouter Free Vision -> Ollama Vision
    """
    # Try primary provider first
    result = await grade_with_huggingface(image_base64, metadata=metadata, **kwargs)

    # If error and fallback available, try alternatives
    if (result.get('error') or result.get('grade', 0) == 0) and FALLBACK_AVAILABLE:
        logger.info(f"HuggingFace grading failed, trying fallbacks...")

        # Use centralized fallback function
        fallback_result = await fallback_grade(
            image_base64=image_base64,
            prompt="Grade this comic book cover on CGC scale (0.5-10.0). Identify title, issue, defects.",
            primary_result=result
        )

        if fallback_result.get('grade', 0) > 0:
            fallback_result['original_provider'] = 'HuggingFace'
            return fallback_result

    return result
