"""
Perplexity Research Engine - Web Search for Comic Pricing and Information
Uses Perplexity API for real-time market research, CGC census, and sales data

Works alongside vision graders to provide comprehensive valuation
"""

import asyncio
import aiohttp
import json
import logging
import os
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

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

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


def get_api_key() -> Optional[str]:
    """Get Perplexity API key from environment"""
    return os.environ.get('PERPLEXITY_API_KEY') or os.environ.get('PPLX_API_KEY')


async def research_comic_pricing(
    title: str,
    issue_number: str,
    grade: float,
    publisher: Optional[str] = None,
    year: Optional[str] = None,
    is_key_issue: bool = False
) -> Dict[str, Any]:
    """
    Research comic pricing using Perplexity web search
    
    Searches for:
    - Recent eBay sold listings
    - GoCollect/GPA price data
    - Heritage Auctions results
    - CGC census population
    - Market trends
    
    Args:
        title: Comic series name
        issue_number: Issue number
        grade: CGC grade (0.5-10.0)
        publisher: Publisher name
        year: Publication year
        is_key_issue: Whether this is a key issue
        
    Returns:
        Comprehensive pricing research results
    """
    api_key = get_api_key()
    if not api_key:
        return {
            'error': 'PERPLEXITY_API_KEY not configured',
            'prices': {},
            'provider': 'Perplexity'
        }
    
    # Build search query
    search_query = f"{title} #{issue_number}"
    if publisher:
        search_query += f" {publisher}"
    if year:
        search_query += f" {year}"
    
    grade_label = get_grade_label(grade)
    
    prompt = f"""Research the current market value and pricing data for this comic book:

COMIC: {search_query}
GRADE: CGC {grade} ({grade_label})
{"KEY ISSUE: Yes - prioritize key issue pricing" if is_key_issue else ""}

Search and provide SPECIFIC data from these sources:

1. EBAY SOLD LISTINGS (last 90 days):
   - Search: "{title} {issue_number} CGC {grade}" sold listings
   - List 3-5 recent sales with dates and prices
   - Note Buy It Now vs auction prices

2. GOCOLLECT / GPA ANALYTICS:
   - Fair Market Value (FMV) at grade {grade}
   - Price trend (up/down/stable)
   - Recent sales data from GPA

3. HERITAGE AUCTIONS:
   - Recent auction results for this comic
   - Record sale price if notable

4. CGC CENSUS:
   - Population at grade {grade}
   - Total graded copies
   - Population higher grades

5. MARKET ANALYSIS:
   - Current demand level (hot/stable/cold)
   - Investment potential
   - Price trajectory

Respond in EXACT JSON format:
{{
    "title": "{title}",
    "issue_number": "{issue_number}",
    "grade": {grade},
    "grade_label": "{grade_label}",
    "ebay_sales": [
        {{"price": <number>, "date": "<date>", "type": "auction|buy_now", "url": "<url or null>"}}
    ],
    "gocollect": {{
        "fmv": <number or null>,
        "trend": "up|down|stable",
        "trend_percent": <percent change or null>
    }},
    "heritage": {{
        "recent_sale": <number or null>,
        "sale_date": "<date or null>",
        "record_price": <number or null>
    }},
    "cgc_census": {{
        "population_at_grade": <number or null>,
        "total_graded": <number or null>,
        "population_higher": <number or null>
    }},
    "market_analysis": {{
        "demand": "hot|stable|cold",
        "investment_rating": "strong buy|buy|hold|sell",
        "notes": "<analysis>"
    }},
    "estimated_value": {{
        "low": <number>,
        "mid": <number>,
        "high": <number>,
        "confidence": <0.0-1.0>
    }},
    "sources_cited": ["<source urls>"]
}}"""

    try:
        payload = {
            "model": "sonar",  # Perplexity's search model
            "messages": [
                {
                    "role": "system",
                    "content": "You are a comic book market analyst. Provide accurate, specific pricing data from real sources. Always cite your sources."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": 0.2,
            "max_tokens": 2000,
            "return_citations": True,
            "search_recency_filter": "month"  # Focus on recent data
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                PERPLEXITY_API_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Perplexity API error: {error_text}")
                    return {
                        'error': f'Perplexity API error: {resp.status}',
                        'prices': {},
                        'provider': 'Perplexity'
                    }
                
                result = await resp.json()
                
                # Extract response text
                response_text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                citations = result.get('citations', [])
                
                # Parse JSON from response
                pricing_data = parse_json_response(response_text)
                
                if pricing_data:
                    pricing_data['provider'] = 'Perplexity'
                    pricing_data['research_timestamp'] = datetime.now().isoformat()
                    pricing_data['citations'] = citations
                    return pricing_data
                else:
                    return {
                        'error': 'Failed to parse pricing data',
                        'raw_response': response_text[:500],
                        'provider': 'Perplexity'
                    }
                    
    except asyncio.TimeoutError:
        logger.error("Perplexity request timed out")
        return {'error': 'Request timed out', 'provider': 'Perplexity'}
    except Exception as e:
        logger.error(f"Perplexity research error: {e}")
        return {'error': str(e), 'provider': 'Perplexity'}


async def research_comic_info(
    title: str,
    issue_number: str,
    publisher: Optional[str] = None
) -> Dict[str, Any]:
    """
    Research comprehensive comic information using Perplexity
    
    Fills in metadata that vision graders might miss:
    - Full creative team
    - Story details  
    - Key issue status
    - Historical significance
    
    Returns:
        Comic information dict matching SKILL.md catalog fields
    """
    api_key = get_api_key()
    if not api_key:
        return {'error': 'PERPLEXITY_API_KEY not configured'}
    
    search_query = f"{title} #{issue_number}"
    if publisher:
        search_query += f" {publisher}"
    
    prompt = f"""Research comprehensive information about this comic book:

COMIC: {search_query}

Provide detailed metadata matching professional cataloging standards:

1. PUBLICATION INFO:
   - Full series title and volume
   - Cover date and on-sale date
   - Publisher imprint
   - Original cover price
   
2. CREATIVE TEAM:
   - Writer(s)
   - Penciler(s) / Interior artist
   - Inker(s)
   - Colorist(s)
   - Letterer(s)
   - Cover artist
   - Editor(s)
   
3. STORY CONTENT:
   - Story title(s)
   - Featured characters
   - Villains/antagonists
   - Supporting cast
   - Plot summary (brief)
   
4. KEY ISSUE STATUS:
   - Is this a key issue? Why?
   - First appearances
   - Character deaths/returns
   - Origin stories
   - Iconic covers
   - Crossover significance
   
5. HISTORICAL CONTEXT:
   - Era (Golden/Silver/Bronze/Copper/Modern Age)
   - Industry significance
   - Awards/recognition
   - Reprints/collected editions

Respond in EXACT JSON format:
{{
    "title": "<series name>",
    "issue_number": "<issue>",
    "volume": <number or 1>,
    "publisher": "<publisher>",
    "imprint": "<imprint or null>",
    "cover_date": "<month year>",
    "on_sale_date": "<date or null>",
    "cover_price": "<price>",
    "creative_team": {{
        "writer": ["<name>"],
        "penciler": ["<name>"],
        "inker": ["<name>"],
        "colorist": ["<name>"],
        "letterer": ["<name>"],
        "cover_artist": "<name>",
        "editor": ["<name>"]
    }},
    "story": {{
        "title": "<story title>",
        "characters": ["<character>"],
        "villains": ["<villain>"],
        "summary": "<brief plot>"
    }},
    "key_issue": {{
        "is_key": <true/false>,
        "reasons": ["<reason>"],
        "first_appearances": ["<character>"],
        "deaths": ["<character or null>"],
        "origins": ["<character or null>"],
        "iconic_cover": <true/false>,
        "crossover": "<crossover name or null>"
    }},
    "historical": {{
        "era": "<era name>",
        "significance": "<why notable>",
        "awards": ["<award or null>"],
        "collected_in": ["<tpb/omnibus name>"]
    }},
    "page_count": <number>,
    "format": "<standard|giant-size|annual|etc>",
    "country": "USA",
    "language": "English"
}}"""

    try:
        payload = {
            "model": "sonar",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a comic book historian and cataloger. Provide accurate, detailed information from authoritative sources like Grand Comics Database, Comic Vine, and official publisher data."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.2,
            "max_tokens": 2000,
            "return_citations": True
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                PERPLEXITY_API_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Perplexity API error: {error_text}")
                    return {'error': f'API error: {resp.status}'}
                
                result = await resp.json()
                response_text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                comic_info = parse_json_response(response_text)
                if comic_info:
                    comic_info['provider'] = 'Perplexity'
                    comic_info['research_timestamp'] = datetime.now().isoformat()
                    return comic_info
                    
                return {'error': 'Failed to parse response', 'raw': response_text[:500]}
                
    except Exception as e:
        logger.error(f"Comic info research error: {e}")
        return {'error': str(e)}


def parse_json_response(text: str) -> Optional[Dict]:
    """Extract and parse JSON from AI response text"""
    try:
        # Try direct parse first
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON block in response
    json_patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
        r'\{[\s\S]*\}'
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                # Clean up the match
                clean = match.strip()
                if not clean.startswith('{'):
                    # Find the JSON object
                    start = clean.find('{')
                    if start >= 0:
                        clean = clean[start:]
                
                return json.loads(clean)
            except json.JSONDecodeError:
                continue
    
    return None


def get_grade_label(grade: float) -> str:
    """Get CGC grade label"""
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
    closest = min(CGC_GRADES.keys(), key=lambda x: abs(x - grade))
    return CGC_GRADES[closest]


# Convenience function for full research
async def full_comic_research(
    title: str,
    issue_number: str,
    grade: float,
    publisher: Optional[str] = None,
    year: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run both pricing and info research in parallel
    
    Returns combined results for comprehensive grading report
    """
    pricing_task = research_comic_pricing(
        title=title,
        issue_number=issue_number,
        grade=grade,
        publisher=publisher,
        year=year
    )
    
    info_task = research_comic_info(
        title=title,
        issue_number=issue_number,
        publisher=publisher
    )
    
    pricing_result, info_result = await asyncio.gather(
        pricing_task,
        info_task,
        return_exceptions=True
    )
    
    # Handle exceptions
    if isinstance(pricing_result, Exception):
        pricing_result = {'error': str(pricing_result)}
    if isinstance(info_result, Exception):
        info_result = {'error': str(info_result)}
    
    return {
        'pricing': pricing_result,
        'comic_info': info_result,
        'research_complete': True,
        'timestamp': datetime.now().isoformat()
    }



# Quick price lookup - alias for research_comic_pricing with minimal parameters
async def quick_price_lookup(
    title: str,
    issue_number: str,
    grade: float = 9.2
) -> Dict[str, Any]:
    """
    Quick price lookup using Perplexity
    
    Simplified wrapper for research_comic_pricing with minimal parameters.
    Useful for quick estimates without full metadata.
    
    Args:
        title: Comic title
        issue_number: Issue number
        grade: CGC grade (default 9.2 for estimate)
    
    Returns:
        Dict with pricing data
    """
    return await research_comic_pricing(
        title=title,
        issue_number=issue_number,
        grade=grade
    )

# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACK WRAPPER - Use free OpenRouter/Ollama when Perplexity unavailable
# ═══════════════════════════════════════════════════════════════════════════════

async def research_comic_pricing_with_fallback(
    title: str,
    issue_number: str,
    grade: float,
    publisher: Optional[str] = None,
    year: Optional[str] = None,
    is_key_issue: bool = False
) -> Dict[str, Any]:
    """
    Research pricing with automatic fallback to free providers.

    Fallback chain: Perplexity -> OpenRouter Free -> Ollama Local
    """
    # Try primary first
    result = await research_comic_pricing(title, issue_number, grade, publisher, year, is_key_issue)

    # If error and fallback available, try alternatives
    if result.get('error') and FALLBACK_AVAILABLE:
        logger.info("Perplexity unavailable, trying OpenRouter fallback...")

        # Build simplified prompt for fallback
        prompt = f"""Research pricing for: {title} #{issue_number} (CGC {grade})
Publisher: {publisher or 'Unknown'}, Year: {year or 'Unknown'}
Key issue: {is_key_issue}

Provide JSON with: ebay_sales, estimated_value (low/mid/high), market_analysis"""

        # Try OpenRouter
        response = await openrouter_text_fallback(prompt)
        if response:
            parsed = fallback_parse_json(response)
            if parsed:
                parsed['provider'] = 'OpenRouter (Perplexity fallback)'
                parsed['fallback'] = True
                parsed['timestamp'] = datetime.now().isoformat()
                return parsed

        # Try Ollama
        logger.info("OpenRouter unavailable, trying Ollama fallback...")
        response = await ollama_text_fallback(prompt)
        if response:
            parsed = fallback_parse_json(response)
            if parsed:
                parsed['provider'] = 'Ollama (Perplexity fallback)'
                parsed['fallback'] = True
                parsed['timestamp'] = datetime.now().isoformat()
                return parsed

    return result
