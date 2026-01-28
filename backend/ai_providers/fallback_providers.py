"""
Fallback AI Providers - OpenRouter Free Models & Ollama Local
Provides fallback capabilities for all AI providers when primary APIs are unavailable.

Fallback Chain:
1. Primary API (provider-specific)
2. OpenRouter Free Vision/Text Models (cloud)
3. Ollama Local Models (local)

This module is imported by other AI provider modules to provide fallback functionality.
"""

import asyncio
import aiohttp
import base64
import json
import logging
import os
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"

# ═══════════════════════════════════════════════════════════════════════════════
# FREE OPENROUTER MODELS (Updated December 2025)
# ═══════════════════════════════════════════════════════════════════════════════

# Vision-capable free models (for grading)
FREE_VISION_MODELS = [
    "qwen/qwen2.5-vl-72b-instruct:free",          # Best quality - GPT-4o equivalent
    "meta-llama/llama-4-maverick:free",           # Llama 4 Maverick - 17B/400B MoE
    "mistralai/mistral-small-3.1-24b-instruct:free",  # Mistral Small 3.1 multimodal
    "qwen/qwen2.5-vl-32b-instruct:free",          # Qwen 2.5 VL 32B
    "google/gemma-3-27b-it:free",                 # Gemma 3 27B
    "meta-llama/llama-3.2-11b-vision-instruct:free",  # Llama 3.2 Vision
    "google/gemma-3-12b-it:free",                 # Gemma 3 12B - lighter
    "moonshotai/kimi-vl-a3b-thinking:free",       # Kimi-VL
    "google/gemma-3-4b-it:free",                  # Gemma 3 4B - fastest
]

# Text-only free models (for research)
FREE_TEXT_MODELS = [
    "meta-llama/llama-4-maverick:free",
    "google/gemma-3-27b-it:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "qwen/qwen3-235b-a22b:free",
    "deepseek/deepseek-chat-v3-0324:free",
    "meta-llama/llama-4-scout:free",
]

# ═══════════════════════════════════════════════════════════════════════════════
# OLLAMA LOCAL MODELS
# ═══════════════════════════════════════════════════════════════════════════════

OLLAMA_VISION_MODELS = [
    "llava:13b",           # Best local vision model
    "llava:7b",            # Lighter vision model
    "llama3.2-vision",     # If installed
    "bakllava",            # Another vision option
]

OLLAMA_TEXT_MODELS = [
    "llama3.2",
    "llama3.1",
    "mistral",
    "codellama",
    "qwen2.5",
]

# ═══════════════════════════════════════════════════════════════════════════════
# CGC GRADING SCALE
# ═══════════════════════════════════════════════════════════════════════════════

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
    """Get CGC grade label from numeric grade"""
    closest = min(CGC_GRADES.keys(), key=lambda x: abs(x - grade))
    return CGC_GRADES[closest]


def parse_json_response(text: str) -> Optional[Dict]:
    """Extract and parse JSON from AI response text"""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    json_patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
        r'\{[\s\S]*\}'
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                clean = match.strip()
                if not clean.startswith('{'):
                    start = clean.find('{')
                    if start >= 0:
                        clean = clean[start:]
                return json.loads(clean)
            except json.JSONDecodeError:
                continue

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# OPENROUTER FALLBACK FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def openrouter_text_fallback(prompt: str, timeout: int = 60) -> Optional[str]:
    """
    Use OpenRouter free text models as fallback for research/text tasks.
    Tries multiple models until one succeeds.
    """
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        logger.debug("No OPENROUTER_API_KEY - skipping OpenRouter fallback")
        return None

    for model in FREE_TEXT_MODELS:
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://collectibles-grading.local"
            }
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 2000
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    OPENROUTER_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                        if content:
                            logger.info(f"OpenRouter fallback succeeded with {model}")
                            return content
        except Exception as e:
            logger.debug(f"OpenRouter {model} failed: {e}")
            continue

    return None


async def openrouter_vision_fallback(
    image_base64: str,
    prompt: str,
    timeout: int = 90
) -> Optional[Dict[str, Any]]:
    """
    Use OpenRouter free vision models as fallback for grading.
    Tries multiple vision models until one succeeds.
    """
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        logger.debug("No OPENROUTER_API_KEY - skipping OpenRouter vision fallback")
        return None

    for model in FREE_VISION_MODELS:
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://collectibles-grading.local"
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
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            },
                            {"type": "text", "text": prompt}
                        ]
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 2000
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    OPENROUTER_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                        if content:
                            logger.info(f"OpenRouter vision fallback succeeded with {model}")
                            parsed = parse_json_response(content)
                            if parsed:
                                parsed['provider'] = f'OpenRouter ({model.split("/")[-1].split(":")[0]})'
                                parsed['fallback'] = True
                                return parsed
                            return {'raw_response': content[:500], 'provider': f'OpenRouter ({model})'}
        except Exception as e:
            logger.debug(f"OpenRouter vision {model} failed: {e}")
            continue

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# OLLAMA LOCAL FALLBACK FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def ollama_text_fallback(prompt: str, timeout: int = 120) -> Optional[str]:
    """
    Use local Ollama as fallback for text/research tasks.
    """
    for model in OLLAMA_TEXT_MODELS:
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2}
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    OLLAMA_API_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        response = result.get('response', '')
                        if response:
                            logger.info(f"Ollama text fallback succeeded with {model}")
                            return response
        except Exception as e:
            logger.debug(f"Ollama {model} failed: {e}")
            continue

    return None


async def ollama_vision_fallback(
    image_base64: str,
    prompt: str,
    timeout: int = 180
) -> Optional[Dict[str, Any]]:
    """
    Use local Ollama vision models as fallback for grading.
    """
    for model in OLLAMA_VISION_MODELS:
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "images": [image_base64],
                "stream": False,
                "options": {"temperature": 0.3}
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    OLLAMA_API_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        response = result.get('response', '')
                        if response:
                            logger.info(f"Ollama vision fallback succeeded with {model}")
                            parsed = parse_json_response(response)
                            if parsed:
                                parsed['provider'] = f'Ollama ({model})'
                                parsed['fallback'] = True
                                return parsed
                            return {'raw_response': response[:500], 'provider': f'Ollama ({model})'}
        except Exception as e:
            logger.debug(f"Ollama vision {model} failed: {e}")
            continue

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED FALLBACK FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def research_with_fallback(
    prompt: str,
    primary_result: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Run research with automatic fallback chain.
    If primary_result has an error, try fallbacks.

    Args:
        prompt: The research prompt
        primary_result: Result from primary API (if available)

    Returns:
        Research result dict
    """
    # If primary succeeded, return it
    if primary_result and not primary_result.get('error'):
        return primary_result

    logger.info("Primary research unavailable, trying fallbacks...")

    # Try OpenRouter
    response = await openrouter_text_fallback(prompt)
    if response:
        parsed = parse_json_response(response)
        if parsed:
            parsed['provider'] = 'OpenRouter (fallback)'
            parsed['timestamp'] = datetime.now().isoformat()
            return parsed
        return {'raw_response': response[:1000], 'provider': 'OpenRouter (fallback)'}

    # Try Ollama
    logger.info("OpenRouter unavailable, trying Ollama...")
    response = await ollama_text_fallback(prompt)
    if response:
        parsed = parse_json_response(response)
        if parsed:
            parsed['provider'] = 'Ollama (fallback)'
            parsed['timestamp'] = datetime.now().isoformat()
            return parsed
        return {'raw_response': response[:1000], 'provider': 'Ollama (fallback)'}

    return {
        'error': 'All research providers unavailable (primary, OpenRouter, Ollama)',
        'provider': 'None'
    }


async def grade_with_fallback(
    image_base64: str,
    prompt: str,
    primary_result: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Run grading with automatic fallback chain.
    If primary_result has an error, try fallbacks.

    Args:
        image_base64: Base64-encoded image
        prompt: The grading prompt
        primary_result: Result from primary API (if available)

    Returns:
        Grading result dict
    """
    # If primary succeeded, return it
    if primary_result and not primary_result.get('error') and primary_result.get('grade', 0) > 0:
        return primary_result

    logger.info("Primary grading unavailable, trying fallbacks...")

    # Try OpenRouter vision
    result = await openrouter_vision_fallback(image_base64, prompt)
    if result and result.get('grade', result.get('grade_label')):
        return result

    # Try Ollama vision
    logger.info("OpenRouter vision unavailable, trying Ollama vision...")
    result = await ollama_vision_fallback(image_base64, prompt)
    if result and result.get('grade', result.get('grade_label')):
        return result

    return {
        'error': 'All grading providers unavailable (primary, OpenRouter, Ollama)',
        'grade': 0,
        'provider': 'None'
    }


# ═══════════════════════════════════════════════════════════════════════════════
# AVAILABILITY CHECK FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def check_openrouter_available() -> bool:
    """Check if OpenRouter API is configured and responsive"""
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        return False

    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                return resp.status == 200
    except:
        return False


async def check_ollama_available() -> bool:
    """Check if Ollama is running locally"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:11434/api/tags",
                timeout=aiohttp.ClientTimeout(total=2)
            ) as resp:
                return resp.status == 200
    except:
        return False


async def get_available_fallbacks() -> Dict[str, bool]:
    """Get status of all fallback providers"""
    openrouter, ollama = await asyncio.gather(
        check_openrouter_available(),
        check_ollama_available(),
        return_exceptions=True
    )

    return {
        'openrouter': isinstance(openrouter, bool) and openrouter,
        'ollama': isinstance(ollama, bool) and ollama
    }
