"""
OpenRouter Vision Grader - Uses free vision models for comic grading

Updated December 2025: Correct model IDs from OpenRouter API
- Some models use :free suffix, others don't
- Verified from https://openrouter.ai/models

Supports multiple authentication methods:
1. OPENROUTER_API_KEY environment variable
2. Promethian Vault integration
3. Config file (ai_config.json)
"""

import asyncio
import aiohttp
import base64
import json
import logging
import os
import re
from typing import Dict, Any, Optional, List
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

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Free vision models on OpenRouter (December 2025)
# UPDATED: Using correct model IDs verified from OpenRouter API errors
# See: https://openrouter.ai/models for current available models
FREE_VISION_MODELS = [
    # Google Gemini 2.0 Flash (FREE - uses :free suffix)
    "google/gemini-2.0-flash-exp:free",               # Primary - vision capable, free tier
    # Llama 3.2 Vision - use paid model (11B vision not free)
    "meta-llama/llama-3.2-11b-vision-instruct:free",  # May have limited availability
    # Qwen2 VL - correct model ID format
    "qwen/qwen2-vl-7b-instruct:free",                 # Qwen2 Vision 7B (if available)
]

# Fallback models when free ones fail
PAID_VISION_MODELS = [
    "google/gemini-2.0-flash-exp:free",               # Free Gemini
    "anthropic/claude-3-haiku",                       # Cheap paid fallback
    "openai/gpt-4o-mini",                             # Cheap paid fallback
]

# All free vision models for maximum coverage
ALL_FREE_VISION_MODELS = FREE_VISION_MODELS.copy()

# Primary model for single grading calls (most reliable)
PRIMARY_VISION_MODEL = "google/gemini-2.0-flash-exp:free"

# Fast models for quick grading
FAST_VISION_MODELS = [
    "google/gemini-2.0-flash-exp:free",
]

# High-quality models for detailed grading
QUALITY_VISION_MODELS = [
    "google/gemini-2.0-flash-exp:free",
]

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


def get_api_from_vault() -> Optional[str]:
    """Try to get OpenRouter API key from Promethian Vault using correct paths"""
    import sys
    # Skip vault on Python 3.13+ - causes sys.modules corruption
    if sys.version_info >= (3, 13):
        logger.debug("Vault disabled on Python 3.13+ - using env vars only")
        return None

    try:
        import os
        from dotenv import load_dotenv

        # Correct vault paths from documentation
        vault_module_path = Path("P:/SOVEREIGN_APPS/collectibles_grading_system")
        vault_db_path = Path("P:/SOVEREIGN_APPS/collectibles_grading_system/.promethian_vault")
        env_file = Path("P:/SOVEREIGN_APPS/collectibles_grading_system/.env")

        # Load environment for vault password
        if env_file.exists():
            load_dotenv(env_file)

        # Add vault module to path
        if vault_module_path.exists() and str(vault_module_path) not in sys.path:
            sys.path.insert(0, str(vault_module_path))

        # Also check I:/DOCUMENTATION/PROMETHIAN_VAULT as backup
        backup_vault_path = Path("I:/DOCUMENTATION/PROMETHIAN_VAULT")
        if backup_vault_path.exists() and str(backup_vault_path) not in sys.path:
            sys.path.insert(0, str(backup_vault_path))

        from vault_addon import PromethianVault

        # Initialize vault with proper paths
        vault = PromethianVault(
            vault_path=str(vault_db_path),
            master_password=os.getenv("VAULT_MASTER_PASSWORD")
        )

        # Check vault status first
        status = vault.status()
        if status.get('status') == 'LOCKED':
            logger.warning("Promethian Vault is locked")
            return None

        # Try to retrieve the OpenRouter API key (note: use exact key name from vault)
        result = vault.retrieve("OPENROUTER_API_KEY_api_key")

        if result.get("success") and result.get("secret_value"):
            logger.info("Using OpenRouter API key from Promethian Vault")
            return result["secret_value"]

    except ImportError as e:
        logger.debug(f"Promethian Vault not available: {e}")
    except Exception as e:
        logger.debug(f"Vault retrieval failed: {e}")

    return None


def get_api_key() -> Optional[str]:
    """
    Get OpenRouter API key using priority-based fallback:
    1. OPENROUTER_API_KEY environment variable
    2. Promethian Vault
    3. Config file (ai_config.json)
    """
    # 1. Check environment first
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if api_key:
        logger.info("Using OPENROUTER_API_KEY from environment")
        return api_key

    # 2. Try Promethian Vault
    vault_key = get_api_from_vault()
    if vault_key:
        return vault_key

    # 3. Check config file
    config_path = Path(__file__).parent.parent / "config" / "ai_config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
                api_key = config.get('openrouter', {}).get('api_key')
                if api_key:
                    logger.info("Using OpenRouter API key from ai_config.json")
                    return api_key
        except:
            pass

    logger.warning("No OpenRouter API key found - will use free models only")
    return None


async def grade_with_openrouter(
    image_input: str,
    model: str = PRIMARY_VISION_MODEL,
    metadata: Optional[Dict] = None,
    cover_side: str = 'front'
) -> Dict[str, Any]:
    """
    Grade a comic cover using OpenRouter's vision models

    Args:
        image_input: Either a file path OR base64-encoded image data
        model: OpenRouter model to use
        metadata: Optional comic metadata
        cover_side: 'front' or 'back'

    Returns:
        Grading result dict
    """
    api_key = get_api_key()
    if not api_key:
        return {
            'error': 'OPENROUTER_API_KEY not configured',
            'grade': 0,
            'model': model,
            'provider': 'OpenRouter'
        }

    metadata = metadata or {}
    model_short = model.split('/')[-1].split(':')[0]
    
    # Convert file path to base64 if needed
    image_base64 = image_input
    if os.path.exists(image_input):
        try:
            with open(image_input, 'rb') as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            return {
                'error': f'Failed to read image file: {e}',
                'grade': 0,
                'model': model,
                'provider': 'OpenRouter'
            }
    elif image_input.startswith('data:'):
        image_base64 = image_input.split(',', 1)[1] if ',' in image_input else image_input

    # Clean base64 - remove whitespace and fix padding
    image_base64 = image_base64.strip().replace('\n', '').replace('\r', '').replace(' ', '')
    # Fix base64 padding if needed
    padding_needed = 4 - (len(image_base64) % 4)
    if padding_needed != 4:
        image_base64 += '=' * padding_needed

    prompt = f"""You are a professional CGC-certified comic book grader with decades of experience AND a comic book historian.
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
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://collectibles-grading.local",
            "X-Title": "Comic Grading App"
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
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.3
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"OpenRouter API error: {error_text}")
                    return {
                        'error': f'OpenRouter API error: {resp.status}',
                        'grade': 0,
                        'model': model_short,
                        'provider': 'OpenRouter'
                    }

                result = await resp.json()
                response_text = result.get('choices', [{}])[0].get('message', {}).get('content', '')

                # Parse JSON from response
                grading_result = parse_grading_response(response_text)
                grading_result['model'] = model_short
                grading_result['provider'] = 'OpenRouter'
                grading_result['icon'] = '🦙' if 'llama' in model.lower() else '🌐'

                return grading_result

    except asyncio.TimeoutError:
        return {'error': 'Timeout', 'grade': 0, 'model': model_short, 'provider': 'OpenRouter'}
    except Exception as e:
        logger.error(f"OpenRouter grading error: {e}")
        return {'error': str(e), 'grade': 0, 'model': model_short, 'provider': 'OpenRouter'}


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
                'confidence': float(data.get('confidence', 0.8)),
                'defects': data.get('defects', []),
                'reasoning': data.get('reasoning', ''),
                'comic_info': data.get('comic_info', {}),
                'key_issue_info': data.get('key_issue_info', {})
            }
    except json.JSONDecodeError:
        pass

    # Fallback - try to extract grade from text
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
    """Extract numeric grade from text response"""
    patterns = [
        r'grade[:\s]+([\d.]+)',
        r'([\d.]+)\s*/\s*10',
        r'score[:\s]+([\d.]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            grade = float(match.group(1))
            if 0 <= grade <= 10:
                return round(grade * 2) / 2

    return 6.0


async def grade_with_llama_vision(image_base64: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """Grade using Llama 3.2 Vision via OpenRouter (free)"""
    return await grade_with_openrouter(
        image_base64,
        "meta-llama/llama-3.2-11b-vision-instruct",
        metadata
    )


async def grade_with_qwen_vision(image_base64: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """Grade using Qwen2 VL via OpenRouter (free)"""
    return await grade_with_openrouter(
        image_base64,
        "qwen/qwen-2-vl-7b-instruct",
        metadata
    )


async def grade_with_gemini_flash(image_base64: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """Grade using Gemini 2.0 Flash via OpenRouter (free)"""
    return await grade_with_openrouter(
        image_base64,
        "google/gemini-2.0-flash-exp:free",
        metadata
    )


async def multi_model_openrouter_grade(
    image_base64: str,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Grade using multiple free OpenRouter vision models and calculate consensus
    """
    # Use free vision models
    models = FREE_VISION_MODELS

    # Run grading tasks in parallel
    tasks = [grade_with_openrouter(image_base64, model, metadata) for model in models]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter valid results
    valid_results = []
    ai_grades = {}

    for i, result in enumerate(results):
        if isinstance(result, dict) and not result.get('error') and result.get('grade', 0) > 0:
            valid_results.append(result)
            model_id = models[i].replace('/', '_').replace(':', '_').replace('-', '_')
            ai_grades[model_id] = {
                'grade': result['grade'],
                'confidence': result.get('confidence', 0.7),
                'model_name': result.get('model', models[i]),
                'provider': 'OpenRouter',
                'icon': result.get('icon', '🌐'),
                'reasoning': result.get('reasoning', ''),
                'defects_found': result.get('defects', [])
            }

    if not valid_results:
        return {
            'error': 'All grading attempts failed',
            'consensus_grade': 0,
            'ai_grades': ai_grades
        }

    # Calculate consensus
    grades = [r['grade'] for r in valid_results]
    avg_grade = sum(grades) / len(grades)
    min_grade = min(grades)

    # Weighted consensus (favor stricter grades)
    consensus = round(((avg_grade * 0.6) + (min_grade * 0.4)) * 2) / 2

    # Combine defects from all models
    all_defects = []
    for result in valid_results:
        all_defects.extend(result.get('defects', []))

    # Get comic info from first successful result
    comic_info = valid_results[0].get('comic_info', {})

    return {
        'consensus_grade': consensus,
        'grade_label': get_grade_label(consensus),
        'confidence': calculate_confidence(grades),
        'ai_grades': ai_grades,
        'defects': dedupe_defects(all_defects),
        'comic': comic_info,
        'model_count': len(valid_results),
        'grading_notes': f'Consensus from {len(valid_results)} free AI models via OpenRouter'
    }


def calculate_confidence(grades: List[float]) -> float:
    """Calculate confidence based on grade agreement"""
    if len(grades) < 2:
        return 0.7

    avg = sum(grades) / len(grades)
    variance = sum((g - avg) ** 2 for g in grades) / len(grades)
    std_dev = variance ** 0.5

    return max(0.5, min(0.98, 1 - (std_dev / 3)))


def dedupe_defects(defects: List[Dict]) -> List[Dict]:
    """Remove duplicate defects"""
    seen = set()
    unique = []
    for d in defects:
        key = (d.get('type', ''), d.get('location', ''))
        if key not in seen:
            seen.add(key)
            unique.append(d)
    return unique
