"""
Ollama Vision Grader - Real AI Vision for Comic Grading
Uses local Ollama models with vision capabilities (llava, llama3.2-vision, etc.)
"""

import asyncio
import aiohttp
import base64
import json
import logging
import re
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"

# CGC Grading Scale
CGC_GRADES = {
    10.0: "Gem Mint",
    9.9: "Mint",
    9.8: "Near Mint/Mint",
    9.6: "Near Mint+",
    9.4: "Near Mint",
    9.2: "Near Mint-",
    9.0: "Very Fine/Near Mint",
    8.5: "Very Fine+",
    8.0: "Very Fine",
    7.5: "Very Fine-",
    7.0: "Fine/Very Fine",
    6.5: "Fine+",
    6.0: "Fine",
    5.5: "Fine-",
    5.0: "Very Good/Fine",
    4.5: "Very Good+",
    4.0: "Very Good",
    3.5: "Very Good-",
    3.0: "Good/Very Good",
    2.5: "Good+",
    2.0: "Good",
    1.8: "Good-",
    1.5: "Fair/Good",
    1.0: "Fair",
    0.5: "Poor"
}

def get_grade_label(grade: float) -> str:
    """Get CGC label for a numeric grade"""
    closest = min(CGC_GRADES.keys(), key=lambda x: abs(x - grade))
    return CGC_GRADES[closest]


async def check_ollama_available() -> bool:
    """Check if Ollama is running"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                return resp.status == 200
    except:
        return False


async def get_available_vision_models() -> List[str]:
    """Get list of available vision-capable models"""
    vision_models = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OLLAMA_BASE_URL}/api/tags") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for model in data.get('models', []):
                        name = model.get('name', '').lower()
                        # Vision-capable models
                        if any(v in name for v in ['llava', 'vision', 'minicpm', 'bakllava']):
                            vision_models.append(model['name'])
    except Exception as e:
        logger.error(f"Error getting vision models: {e}")
    return vision_models


async def grade_with_ollama_vision(
    image_base64: str,
    model: str = "llava:7b",
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Grade a comic cover using Ollama vision model

    Args:
        image_base64: Base64-encoded image (without data URL prefix)
        model: Ollama model to use (must be vision-capable)
        metadata: Optional comic metadata

    Returns:
        Grading result with grade, defects, reasoning
    """
    metadata = metadata or {}

    # Grading prompt - stringent CGC-style grading with comprehensive metadata
    prompt = """You are a professional comic book grader with CGC certification expertise AND a comic book historian.
Analyze this comic book cover image and provide a detailed condition assessment AND comprehensive comic metadata.

GRADING SCALE (CGC 10-point scale):
- 10.0 Gem Mint: Perfect, no defects
- 9.8-9.9 Near Mint/Mint: Nearly perfect
- 9.4-9.6 Near Mint: Minor imperfections
- 8.0-9.2 Very Fine: Light wear, minor defects
- 6.0-7.5 Fine: Moderate wear, creases allowed
- 4.0-5.5 Very Good: Significant wear, small tears
- 2.0-3.5 Good: Heavy wear, pieces missing OK
- 0.5-1.8 Fair/Poor: Major defects, incomplete

BE STRINGENT - Most circulated comics grade 4.0-7.5. A 9.0+ is RARE.

Examine for these defects:
1. COVER: Tears, creases, folds, stains, fading, fingerprints
2. SPINE: Stress marks, color breaks, rolling, splits
3. CORNERS: Blunting, bends, dogears
4. EDGES: Wear, chips, foxing
5. STAPLES: Rust, missing, loose
6. OVERALL: Yellowing, brittleness, writing/stamps

COMIC IDENTIFICATION (CRITICAL):
- title: The main series name (e.g., "Amazing Spider-Man", "Batman", "X-Men")
- issue_number: The specific ISSUE NUMBER of this comic (usually a number like "129", "361", "1"). This is typically printed near the title or in a corner box. Look for "#" followed by a number. DO NOT confuse with volume numbers, variant letters, cover prices, or other numbers.
- publisher: DC Comics, Marvel Comics, Image, etc.
- year: Publication year (often in corner box or indicia)

COMPREHENSIVE METADATA (Identify from cover or your knowledge):
- volume, cover_date, cover_price, story_title
- writer, cover_artist, interior_artist
- characters (especially first appearances)
- era: Golden Age (1938-1956), Silver Age (1956-1970), Bronze Age (1970-1985), Copper Age (1985-1991), Modern Age (1991+)

KEY ISSUE STATUS:
- is_key_issue: Is this significant?
- key_reasons: first appearance, death, origin, iconic cover
- first_appearances: List any character debuts

Respond in this EXACT JSON format:
{
    "grade": <number 0.5-10.0>,
    "grade_label": "<CGC label>",
    "confidence": <0.0-1.0>,
    "defects": [
        {"type": "<defect type>", "severity": "<trace|minor|moderate|major>", "location": "<where>", "penalty": <0.1-2.0>}
    ],
    "reasoning": "<detailed explanation>",
    "comic_info": {
        "title": "<series name>",
        "issue_number": "<issue # only, e.g. 129>",
        "publisher": "<publisher>",
        "year": "<year>",
        "volume": "<volume # or null>",
        "cover_date": "<month year>",
        "cover_price": "<original price>",
        "writer": ["<writer name>"],
        "cover_artist": "<cover artist or null>",
        "characters": ["<character>"],
        "era": "<era name>"
    },
    "key_issue_info": {
        "is_key_issue": <true/false>,
        "key_reasons": ["<reason>"],
        "first_appearances": ["<character>"],
        "notable_events": ["<event>"]
    }
}"""

    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": model,
                "prompt": prompt,
                "images": [image_base64],
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 1500
                }
            }

            # Increase timeout for vision processing - first request loads model
            async with session.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300)  # 5 minutes for first load
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Ollama API error: {error_text}")

                result = await resp.json()
                response_text = result.get('response', '')

                # Try to parse JSON from response
                grading_result = parse_grading_response(response_text)
                grading_result['model'] = model
                grading_result['provider'] = 'Ollama'
                grading_result['raw_response'] = response_text[:500]

                return grading_result

    except asyncio.TimeoutError:
        logger.error(f"Timeout grading with {model}")
        return create_error_result(model, "Timeout - model took too long")
    except Exception as e:
        logger.error(f"Error grading with {model}: {e}")
        return create_error_result(model, str(e))


def parse_grading_response(response_text: str) -> Dict[str, Any]:
    """Parse the AI response into structured grading data"""
    # Try to extract JSON from the response
    try:
        # Look for JSON block in response
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            data = json.loads(json_match.group())

            # Validate and normalize
            grade = float(data.get('grade', 6.0))
            grade = max(0.5, min(10.0, grade))
            grade = round(grade * 2) / 2  # Round to 0.5

            return {
                'grade': grade,
                'grade_label': data.get('grade_label', get_grade_label(grade)),
                'confidence': float(data.get('confidence', 0.75)),
                'defects': data.get('defects', []),
                'reasoning': data.get('reasoning', 'Grade assessed based on visual analysis'),
                'comic_info': data.get('comic_info', {}),
                'key_issue_info': data.get('key_issue_info', {})
            }
    except json.JSONDecodeError:
        pass

    # Fallback: try to extract grade from text
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
    # Look for patterns like "grade: 7.5", "7.5/10", "Grade of 7.5"
    patterns = [
        r'grade[:\s]+(\d+\.?\d*)',
        r'(\d+\.?\d*)\s*/\s*10',
        r'(\d+\.?\d*)\s+(?:out of|/)\s*10',
        r'score[:\s]+(\d+\.?\d*)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            grade = float(match.group(1))
            if 0 <= grade <= 10:
                return round(grade * 2) / 2

    # Default conservative grade
    return 6.0


def create_error_result(model: str, error: str) -> Dict[str, Any]:
    """Create an error result"""
    return {
        'grade': 0,
        'grade_label': 'Error',
        'confidence': 0,
        'defects': [],
        'reasoning': f"Error: {error}",
        'comic_info': {},
        'key_issue_info': {},
        'model': model,
        'provider': 'Ollama',
        'error': error
    }


async def grade_with_llava(image_base64: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """Grade using LLaVA model"""
    return await grade_with_ollama_vision(image_base64, "llava:7b", metadata)


async def identify_comic_with_vision(image_base64: str, model: str = "llava:7b") -> Dict[str, Any]:
    """
    Identify comic title, issue, publisher from cover image
    """
    prompt = """Look at this comic book cover and identify:
1. Title of the comic
2. Issue number
3. Publisher (Marvel, DC, Image, etc.)
4. Year/date if visible
5. Any notable text visible on the cover

Respond in JSON format:
{
    "title": "<comic title>",
    "issue_number": "<issue #>",
    "publisher": "<publisher name>",
    "year": "<year if visible>",
    "cover_text": "<other visible text>",
    "confidence": <0.0-1.0>
}"""

    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": model,
                "prompt": prompt,
                "images": [image_base64],
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 500
                }
            }

            # Increase timeout for vision processing - first request loads model
            async with session.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=180)  # 3 minutes
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Ollama API error: {await resp.text()}")

                result = await resp.json()
                response_text = result.get('response', '')

                # Parse JSON from response
                try:
                    json_match = re.search(r'\{[\s\S]*\}', response_text)
                    if json_match:
                        return json.loads(json_match.group())
                except:
                    pass

                return {
                    'title': 'Unknown Comic',
                    'issue_number': '??',
                    'publisher': 'Unknown',
                    'year': 'Unknown',
                    'raw_response': response_text[:300],
                    'confidence': 0.3
                }

    except Exception as e:
        logger.error(f"Error identifying comic: {e}")
        return {
            'title': 'Identification Failed',
            'issue_number': '??',
            'publisher': 'Unknown',
            'year': 'Unknown',
            'error': str(e),
            'confidence': 0
        }


async def multi_model_grade(
    image_base64: str,
    models: Optional[List[str]] = None,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Grade using multiple models and calculate consensus
    """
    if models is None:
        # Try to find available vision models
        available = await get_available_vision_models()
        if not available:
            # Fallback to text models with image description
            models = ["llava:7b"]
        else:
            models = available[:3]  # Use up to 3 models

    # Run grading tasks in parallel
    tasks = [grade_with_ollama_vision(image_base64, model, metadata) for model in models]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter valid results
    valid_results = []
    ai_grades = {}

    for i, result in enumerate(results):
        if isinstance(result, dict) and not result.get('error'):
            valid_results.append(result)
            model_id = models[i].replace(':', '_').replace('/', '_')
            ai_grades[model_id] = {
                'grade': result['grade'],
                'confidence': result.get('confidence', 0.7),
                'model_name': models[i],
                'provider': 'Ollama',
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
        'grading_notes': f'Consensus from {len(valid_results)} AI models using Ollama'
    }


def calculate_confidence(grades: List[float]) -> float:
    """Calculate confidence based on grade agreement"""
    if len(grades) < 2:
        return 0.7

    avg = sum(grades) / len(grades)
    variance = sum((g - avg) ** 2 for g in grades) / len(grades)
    std_dev = variance ** 0.5

    # Lower std dev = higher confidence
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
