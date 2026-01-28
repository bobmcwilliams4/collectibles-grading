"""
Cohere Research Module - Semantic Analysis for Comic Research
Uses Cohere's Command R+ for semantic understanding and RAG-style research.
Great for: comic history, significance analysis, metadata extraction from text.
"""

import asyncio
import aiohttp
import json
import logging
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACK PROVIDERS - OpenRouter Free & Ollama Local
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from .fallback_providers import (
        openrouter_text_fallback,
        ollama_text_fallback,
        parse_json_response as fallback_parse_json
    )
    FALLBACK_AVAILABLE = True
except ImportError:
    FALLBACK_AVAILABLE = False

# Load .env file at import time
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        load_dotenv(env_file, override=True)
except ImportError:
    pass

logger = logging.getLogger(__name__)

COHERE_API_URL = "https://api.cohere.ai/v1/chat"


def get_api_key() -> Optional[str]:
    """Get Cohere API key from environment"""
    api_key = os.environ.get('COHERE_API_KEY')
    if api_key:
        logger.info("Using COHERE_API_KEY from environment")
        return api_key
    return None


async def research_comic_history(
    title: str,
    issue_number: str,
    publisher: Optional[str] = None
) -> Dict[str, Any]:
    """
    Research comic history and significance using Cohere.

    Args:
        title: Comic series title
        issue_number: Issue number
        publisher: Optional publisher name

    Returns:
        Dict with history, significance, key events
    """
    api_key = get_api_key()
    if not api_key:
        return {
            'error': 'COHERE_API_KEY not configured',
            'history': {},
            'metadata': {}
        }

    # Build research prompt
    comic_query = f"{title} #{issue_number}"
    if publisher:
        comic_query += f" ({publisher})"

    prompt = f"""You are a comic book historian and expert. Research the following comic book and provide detailed information:

COMIC: {comic_query}

Please provide:
1. PUBLICATION HISTORY: When was this issue published? What era (Golden/Silver/Bronze/Copper/Modern)?
2. CREATIVE TEAM: Writer(s), artist(s), cover artist, inker, letterer, editor
3. STORY SUMMARY: Brief plot summary of this issue
4. KEY SIGNIFICANCE: Is this a key issue? Why? (first appearances, deaths, origins, iconic covers, crossovers)
5. CHARACTERS: Main characters featured, any first appearances
6. MARKET NOTES: Is this issue sought after by collectors? Why?

Respond in JSON format:
{{
    "publication": {{
        "date": "<month year>",
        "era": "<era name>",
        "volume": "<volume number if applicable>",
        "cover_price": "<original price>"
    }},
    "creative_team": {{
        "writer": ["<name>"],
        "penciler": "<name>",
        "inker": "<name>",
        "cover_artist": "<name>",
        "letterer": "<name>",
        "editor": "<name>"
    }},
    "story": {{
        "title": "<story title>",
        "summary": "<brief summary>",
        "genres": ["<genre>"]
    }},
    "significance": {{
        "is_key_issue": <true/false>,
        "key_reasons": ["<reason>"],
        "first_appearances": ["<character>"],
        "notable_events": ["<event>"],
        "collector_notes": "<why collectors want this>"
    }},
    "characters": {{
        "featured": ["<character>"],
        "villains": ["<villain>"],
        "supporting": ["<character>"]
    }}
}}"""

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "command-r-plus",
            "message": prompt,
            "temperature": 0.3,
            "connectors": [{"id": "web-search"}]  # Enable web search for up-to-date info
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                COHERE_API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    response_text = result.get('text', '')

                    # Parse JSON from response
                    parsed = parse_research_response(response_text)
                    parsed['source'] = 'cohere'
                    parsed['model'] = 'command-r-plus'

                    return parsed
                else:
                    error_text = await resp.text()
                    logger.error(f"Cohere API error: {error_text}")
                    return {
                        'error': f"Cohere API error: {resp.status}",
                        'history': {},
                        'metadata': {}
                    }

    except Exception as e:
        logger.error(f"Cohere research error: {e}")
        return {
            'error': str(e),
            'history': {},
            'metadata': {}
        }


async def analyze_comic_significance(
    title: str,
    issue_number: str,
    detected_characters: List[str] = None
) -> Dict[str, Any]:
    """
    Analyze if a comic is significant based on characters detected.
    Uses Cohere's semantic understanding to identify key issues.
    """
    api_key = get_api_key()
    if not api_key:
        return {'error': 'COHERE_API_KEY not configured'}

    characters_str = ", ".join(detected_characters) if detected_characters else "unknown"

    prompt = f"""You are a comic book expert. Analyze the significance of this comic:

Comic: {title} #{issue_number}
Characters detected on cover: {characters_str}

Questions to answer:
1. Is this potentially a FIRST APPEARANCE of any character?
2. Is this a DEATH or significant story event issue?
3. Is this an ICONIC COVER that collectors seek?
4. What is the estimated collector demand (low/medium/high/very high)?

Respond in JSON:
{{
    "is_key_issue": <true/false>,
    "confidence": <0.0-1.0>,
    "key_type": "<first_appearance|death|iconic_cover|crossover|origin|none>",
    "key_details": "<specific reason>",
    "collector_demand": "<low|medium|high|very_high>",
    "price_impact": "<how much this affects value>"
}}"""

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "command-r-plus",
            "message": prompt,
            "temperature": 0.2
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                COHERE_API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    response_text = result.get('text', '')

                    # Parse JSON
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', response_text)
                    if json_match:
                        return json.loads(json_match.group())

                    return {'raw_response': response_text[:500]}
                else:
                    return {'error': f"API error: {resp.status}"}

    except Exception as e:
        logger.error(f"Cohere significance analysis error: {e}")
        return {'error': str(e)}


async def semantic_metadata_extraction(
    raw_text: str,
    context: str = "comic book"
) -> Dict[str, Any]:
    """
    Use Cohere to extract structured metadata from raw text.
    Useful for parsing OCR results or unstructured descriptions.
    """
    api_key = get_api_key()
    if not api_key:
        return {'error': 'COHERE_API_KEY not configured'}

    prompt = f"""Extract structured metadata from the following {context} text:

TEXT:
{raw_text}

Extract and return JSON with:
{{
    "title": "<detected title>",
    "issue_number": "<issue number>",
    "publisher": "<publisher>",
    "date": "<publication date>",
    "price": "<cover price>",
    "characters": ["<character names>"],
    "creators": ["<creator names>"],
    "other_text": ["<other relevant text>"]
}}

Only include fields you can confidently extract. Use null for uncertain fields."""

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "command-r",  # Lighter model for extraction
            "message": prompt,
            "temperature": 0.1
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                COHERE_API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    response_text = result.get('text', '')

                    import re
                    json_match = re.search(r'\{[\s\S]*\}', response_text)
                    if json_match:
                        return json.loads(json_match.group())

                    return {'raw_response': response_text[:500]}
                else:
                    return {'error': f"API error: {resp.status}"}

    except Exception as e:
        logger.error(f"Cohere extraction error: {e}")
        return {'error': str(e)}


def parse_research_response(response_text: str) -> Dict[str, Any]:
    """Parse Cohere research response into structured data"""
    import re

    try:
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            data = json.loads(json_match.group())

            # Restructure for swarm compatibility
            return {
                'history': {
                    'publication': data.get('publication', {}),
                    'story': data.get('story', {}),
                    'significance': data.get('significance', {})
                },
                'metadata': {
                    'creative_team': data.get('creative_team', {}),
                    'characters': data.get('characters', {})
                },
                'key_issue_info': data.get('significance', {})
            }
    except json.JSONDecodeError:
        pass

    # Fallback
    return {
        'history': {'raw_response': response_text[:1000]},
        'metadata': {}
    }

# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACK WRAPPER - Use free OpenRouter/Ollama when Cohere unavailable
# ═══════════════════════════════════════════════════════════════════════════════

async def research_comic_history_with_fallback(
    title: str,
    issue_number: str,
    publisher: Optional[str] = None
) -> Dict[str, Any]:
    """
    Research comic history with automatic fallback to free providers.

    Fallback chain: Cohere -> OpenRouter Free -> Ollama Local
    """
    result = await research_comic_history(title, issue_number, publisher)

    if result.get('error') and FALLBACK_AVAILABLE:
        logger.info("Cohere unavailable, trying OpenRouter fallback...")

        prompt = f"""Research comic book history and significance:
Comic: {title} #{issue_number} ({publisher or 'Unknown publisher'})

Provide JSON with: publication date/era, creative_team, story summary,
key_issue status, first appearances, characters featured."""

        response = await openrouter_text_fallback(prompt)
        if response:
            parsed = fallback_parse_json(response)
            if parsed:
                parsed['source'] = 'OpenRouter (Cohere fallback)'
                parsed['fallback'] = True
                return parsed

        logger.info("OpenRouter unavailable, trying Ollama fallback...")
        response = await ollama_text_fallback(prompt)
        if response:
            parsed = fallback_parse_json(response)
            if parsed:
                parsed['source'] = 'Ollama (Cohere fallback)'
                parsed['fallback'] = True
                return parsed

    return result
