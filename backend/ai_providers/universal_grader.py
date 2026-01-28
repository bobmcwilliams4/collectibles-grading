"""
Universal Collectibles Grader - Multi-Type AI Grading System
Supports: Comics, Trading Cards, Coins, Stamps, Vinyl Records, Action Figures, Video Games

This module provides AI-powered grading for all collectible types using the same
multi-AI consensus approach as the comic book grader, with type-specific grading
scales and criteria.
"""

import asyncio
import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

# Load grading standards for each collectible type
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"

def load_grading_standards(collectible_type: str) -> Dict[str, Any]:
    """Load grading standards JSON for the specified collectible type"""
    type_map = {
        "comics": "grading_standards.json",
        "trading_cards": "trading_cards_grading_standards.json",
        "baseball_cards": "trading_cards_grading_standards.json",
        "sports_cards": "trading_cards_grading_standards.json",
        "coins": "coins_grading_standards.json",
        "stamps": "stamps_grading_standards.json",
        "vinyl": "vinyl_grading_standards.json",
        "vinyl_records": "vinyl_grading_standards.json",
        "action_figures": "action_figures_grading_standards.json",
        "toys": "action_figures_grading_standards.json",
        "video_games": "video_games_grading_standards.json",
    }

    filename = type_map.get(collectible_type, "grading_standards.json")
    filepath = CONFIG_DIR / filename

    if filepath.exists():
        with open(filepath, 'r') as f:
            return json.load(f)
    else:
        logger.warning(f"Grading standards not found: {filepath}")
        return {}


# Grading scale mappings for each collectible type
GRADING_SCALES = {
    "trading_cards": {
        "scale_name": "PSA/BGS",
        "min_grade": 1,
        "max_grade": 10,
        "grades": {
            10: "Gem Mint", 9.5: "Gem Mint (BGS)", 9: "Mint",
            8.5: "NM-MT+", 8: "Near Mint-Mint", 7.5: "NM+",
            7: "Near Mint", 6: "Excellent-Mint", 5: "Excellent",
            4: "Very Good-Excellent", 3: "Very Good", 2: "Good", 1: "Poor"
        }
    },
    "coins": {
        "scale_name": "Sheldon Scale",
        "min_grade": 1,
        "max_grade": 70,
        "grades": {
            70: "MS-70 Perfect", 69: "MS-69 Near Perfect", 68: "MS-68 Superb Gem",
            67: "MS-67 Superb Gem", 66: "MS-66 Gem", 65: "MS-65 Gem",
            64: "MS-64 Choice", 63: "MS-63 Choice", 62: "MS-62", 61: "MS-61", 60: "MS-60",
            58: "AU-58", 55: "AU-55", 53: "AU-53", 50: "AU-50",
            45: "EF-45", 40: "EF-40", 35: "VF-35", 30: "VF-30", 25: "VF-25", 20: "VF-20",
            15: "F-15", 12: "F-12", 10: "VG-10", 8: "VG-8",
            6: "G-6", 4: "G-4", 3: "AG-3", 2: "FR-2", 1: "PO-1"
        }
    },
    "stamps": {
        "scale_name": "Philatelic Grade",
        "min_grade": 40,
        "max_grade": 98,
        "grades": {
            98: "Superb", 95: "Extremely Fine", 90: "XF-Superb",
            85: "Very Fine", 80: "F-VF", 75: "Fine-Very Fine",
            70: "Fine", 60: "Very Good", 50: "Good", 40: "Average"
        }
    },
    "vinyl": {
        "scale_name": "Goldmine",
        "min_grade": 0,
        "max_grade": 10,
        "grades": {
            10: "Mint", 9: "Near Mint", 8: "VG+", 7: "VG++",
            6: "Very Good", 5: "VG-", 4: "Good+", 3: "Good",
            2: "Good-", 1: "Fair", 0: "Poor"
        }
    },
    "action_figures": {
        "scale_name": "AFA",
        "min_grade": 20,
        "max_grade": 100,
        "grades": {
            100: "Uncirculated Perfect", 95: "Uncirculated Mint+",
            90: "Uncirculated Mint", 85: "NM+", 80: "Near Mint",
            75: "Excellent+", 70: "Excellent", 60: "Very Good",
            50: "Good", 40: "Fair", 30: "Poor", 20: "Very Poor"
        }
    },
    "video_games": {
        "scale_name": "VGA/WATA",
        "min_grade": 1,
        "max_grade": 10,
        "grades": {
            10: "Gem Mint", 9.8: "NM/MT", 9.6: "NM+", 9.4: "Near Mint",
            9.2: "NM-", 9.0: "VF/NM", 8.5: "VF+", 8.0: "Very Fine",
            7.5: "VF-", 7.0: "F/VF", 6.5: "Fine+", 6.0: "Fine",
            5.0: "VG/F", 4.0: "Very Good", 3.0: "Good", 2.0: "Fair", 1.0: "Poor"
        }
    }
}


def get_grade_label(grade: float, collectible_type: str) -> str:
    """Get the label for a numeric grade based on collectible type"""
    scale = GRADING_SCALES.get(collectible_type, GRADING_SCALES.get("trading_cards"))
    grades = scale.get("grades", {})

    # Find closest grade in scale
    valid_grades = sorted(grades.keys(), reverse=True)
    for g in valid_grades:
        if grade >= g:
            return grades[g]
    return grades.get(min(grades.keys()), "Unknown")


def build_grading_prompt(collectible_type: str, metadata: Optional[Dict] = None) -> str:
    """Build a type-specific grading prompt for the AI"""

    metadata = metadata or {}
    standards = load_grading_standards(collectible_type)
    scale = GRADING_SCALES.get(collectible_type, GRADING_SCALES.get("trading_cards"))

    base_prompts = {
        "trading_cards": f"""You are a professional PSA/BGS-certified trading card grader.
Analyze this trading card image and provide a detailed condition assessment.

GRADING SCALE (PSA 1-10):
- 10 Gem Mint: Virtually perfect in every way
- 9 Mint: One minor flaw allowed
- 8 Near Mint-Mint: Minor wear visible
- 7 Near Mint: Slight surface wear
- 6 Excellent-Mint: Visible surface wear
- 5 Excellent: Moderate wear
- 4 Very Good-Excellent: Significant wear
- 3 Very Good: Heavy wear
- 2 Good: Major defects
- 1 Poor: Barely recognizable

EXAMINE THESE 4 ATTRIBUTES (BGS Subgrades):
1. CENTERING: Left/Right and Top/Bottom percentages
2. CORNERS: Sharpness, whitening, fraying
3. EDGES: Chipping, wear, color breaks
4. SURFACE: Scratches, print defects, stains, gloss

CARD IDENTIFICATION:
- Sport/Game type (Pokemon, Magic, Sports, etc.)
- Player/Character name
- Set name and year
- Card number
- Parallel/variant type if applicable
- Auto or Relic present?

Respond in EXACT JSON format:
{{"grade": <1-10>, "grade_label": "<PSA label>", "confidence": <0.0-1.0>,
"subgrades": {{"centering": <1-10>, "corners": <1-10>, "edges": <1-10>, "surface": <1-10>}},
"defects": [{{"type": "<defect>", "severity": "<trace|minor|moderate|major>", "location": "<where>", "penalty": <0.1-2.0>}}],
"reasoning": "<explanation>",
"item_info": {{"name": "<player/character>", "set": "<set name>", "year": "<year>", "card_number": "<number>", "sport_type": "<type>", "parallel": "<variant or null>", "auto": <true/false>, "relic": <true/false>}}}}""",

        "coins": f"""You are a professional PCGS/NGC coin grader using the Sheldon scale.
Analyze this coin image and provide a detailed condition assessment.

SHELDON SCALE (1-70):
- MS-70: Perfect Uncirculated - Flawless
- MS-65-69: Gem Uncirculated - Minor imperfections
- MS-60-64: Uncirculated - Contact marks present
- AU-50-58: About Uncirculated - Trace wear on high points
- EF-40-45: Extremely Fine - Light wear throughout
- VF-20-35: Very Fine - Moderate wear
- F-12-15: Fine - Even wear, clear design
- VG-8-10: Very Good - Well worn, major features clear
- G-4-6: Good - Heavily worn
- AG-3: About Good - Very heavily worn
- FR-2: Fair - Mostly outline visible
- PO-1: Poor - Barely identifiable

EXAMINE:
1. STRIKE: Weak, average, or full strike
2. LUSTER: Original, cleaned, or artificial
3. SURFACE PRESERVATION: Contact marks, hairlines, scratches
4. EYE APPEAL: Overall visual appearance
5. TONING: Natural or artificial, colors

COIN IDENTIFICATION:
- Country of origin
- Denomination
- Year/Date
- Mint mark if visible
- Design type (e.g., Morgan Dollar, Walking Liberty)

Respond in EXACT JSON format:
{{"grade": <1-70>, "grade_label": "<MS-XX or other>", "confidence": <0.0-1.0>,
"strike": "<weak|average|full>", "luster": "<original|cleaned|artificial>",
"defects": [{{"type": "<defect>", "severity": "<trace|minor|moderate|major>", "location": "<where>", "penalty": <1-20>}}],
"reasoning": "<explanation>",
"item_info": {{"country": "<country>", "denomination": "<denom>", "year": "<year>", "mint_mark": "<mark or null>", "design_type": "<type>", "composition": "<metal>", "proof": <true/false>}}}}""",

        "stamps": f"""You are a professional philatelist and stamp grader.
Analyze this stamp image and provide a detailed condition assessment.

PHILATELIC GRADING SCALE (40-98):
- 98 Superb: Virtually perfect centering and condition
- 95 Extremely Fine: Near perfect
- 85 Very Fine: Well-centered, minor flaws
- 80 Fine-Very Fine: Slightly off-center
- 70 Fine: Off-center but design clear
- 60 Very Good: Design may touch perfs
- 50 Good: Design cut by perfs
- 40 Average: Poor centering

EXAMINE:
1. CENTERING: Margin width all around
2. PERFORATIONS: Complete, short, blind perfs
3. GUM CONDITION (unused): OG, NH, LH, HH, NG
4. CANCELLATION (used): Light, heavy, manuscript
5. COLOR: Fresh, faded, oxidized
6. PAPER: Clean, stained, thinned

STAMP IDENTIFICATION:
- Country of issue
- Year of issue
- Scott catalog number if identifiable
- Denomination
- Topic/Design

Respond in EXACT JSON format:
{{"grade": <40-98>, "grade_label": "<grade name>", "confidence": <0.0-1.0>,
"gum_condition": "<MNH|OG|LH|HH|NG|Used>", "cancel_quality": "<light|moderate|heavy|null>",
"defects": [{{"type": "<defect>", "severity": "<trace|minor|moderate|major>", "location": "<where>", "penalty": <1-30>}}],
"reasoning": "<explanation>",
"item_info": {{"country": "<country>", "year": "<year>", "scott_number": "<number or null>", "denomination": "<value>", "topic": "<design subject>", "used": <true/false>}}}}""",

        "vinyl": f"""You are a professional vinyl record grader using the Goldmine grading standard.
Analyze this vinyl record (and/or cover) image and provide a detailed condition assessment.

GOLDMINE SCALE:
- M (Mint): Perfect, unplayed
- NM (Near Mint): Nearly perfect, minimal signs of handling
- VG+ (Very Good Plus): Shows some play, light surface noise
- VG (Very Good): Surface noise evident, light scratches
- G+ (Good Plus): Significant wear, plays through
- G (Good): Distortion during playback
- F (Fair): Major noise, skipping possible
- P (Poor): Barely playable

EXAMINE RECORD:
1. SCRATCHES: Hairline, light, deep, scuffs
2. WARPING: Slight, moderate, severe
3. SURFACE NOISE: Pops, clicks, hiss
4. SPINDLE MARKS: Present/absent
5. LABEL CONDITION: Clean, writing, tears

EXAMINE COVER:
1. RING WEAR: From record showing through
2. SEAM SPLITS: Location and length
3. CREASES and BENDS
4. STICKERS, WRITING, TAPE
5. GENERAL WEAR

RECORD IDENTIFICATION:
- Artist name
- Album title
- Label/Record company
- Catalog number
- Year of release
- Pressing info if visible

Respond in EXACT JSON format:
{{"record_grade": <0-10>, "cover_grade": <0-10>, "overall_grade": <0-10>, "grade_label": "<Goldmine label>", "confidence": <0.0-1.0>,
"defects": [{{"type": "<defect>", "severity": "<trace|minor|moderate|major>", "location": "<record|cover>", "penalty": <0.5-3.0>}}],
"reasoning": "<explanation>",
"item_info": {{"artist": "<artist>", "album": "<title>", "label": "<label>", "catalog_number": "<number>", "year": "<year>", "pressing": "<first/reissue/etc>"}}}}""",

        "action_figures": f"""You are a professional AFA (Action Figure Authority) grader.
Analyze this action figure (carded/boxed or loose) and provide a detailed condition assessment.

AFA GRADING SCALE (20-100):
- 100: Uncirculated Perfect - Factory fresh, flawless
- 95: Uncirculated Mint+ - Factory sealed, virtually flawless
- 90: Uncirculated Mint - Factory sealed, near perfect
- 85: Near Mint+ - Excellent condition
- 80: Near Mint - Great condition with minor flaws
- 75: Excellent+ - Light wear visible
- 70: Excellent - Moderate wear
- 60: Very Good - Significant wear
- 50: Good - Heavy wear
- 40: Fair - Major defects

AFA SUBGRADES (C/B/F):
- C (Card/Packaging): Bends, creases, yellowing, corners, edges
- B (Blister/Bubble): Clarity, dents, cracks, attachment
- F (Figure): Paint, accessories, factory defects

EXAMINE:
1. CARD/BOX: Corners, edges, creases, color
2. BLISTER/WINDOW: Clarity, dents, cracks, seal
3. FIGURE: Paint ops, joints, accessories complete
4. FACTORY SEALS: Intact or opened

FIGURE IDENTIFICATION:
- Toy line (Star Wars, GI Joe, Transformers, etc.)
- Character name
- Year/Wave
- Manufacturer
- Variant if applicable

Respond in EXACT JSON format:
{{"grade": <20-100>, "grade_label": "<AFA label>", "confidence": <0.0-1.0>,
"subgrades": {{"card": <20-100>, "blister": <20-100>, "figure": <20-100>}},
"sealed": <true/false>,
"defects": [{{"type": "<defect>", "severity": "<trace|minor|moderate|major>", "location": "<card|blister|figure>", "penalty": <1-20>}}],
"reasoning": "<explanation>",
"item_info": {{"line": "<toy line>", "character": "<name>", "year": "<year>", "manufacturer": "<company>", "variant": "<variant or null>", "accessories_complete": <true/false>}}}}""",

        "video_games": f"""You are a professional video game grader (VGA/WATA standards).
Analyze this video game (sealed or complete in box) and provide a detailed condition assessment.

WATA/VGA GRADING SCALE (1-10):
- 10: Gem Mint - Perfect condition
- 9.8: Near Mint/Mint - Virtually flawless
- 9.4-9.6: Near Mint - Minor imperfections
- 9.0-9.2: Very Fine/Near Mint - Light wear
- 8.0-8.5: Very Fine - Moderate wear
- 7.0-7.5: Fine/Very Fine - Noticeable wear
- 6.0-6.5: Fine - Significant wear
- 4.0-5.0: Very Good/Fair - Heavy wear
- 1.0-3.0: Poor - Major damage

SEAL GRADES (if sealed):
- A++: Exceptional factory seal
- A+: Excellent seal condition
- A: Very good seal
- B+/B: Good seal with wear
- C+/C: Fair seal, compromised

EXAMINE:
1. BOX: Corners, edges, crushing, flap condition
2. SEAL (if present): H-seam, Y-fold, integrity
3. CONTENTS (if CIB): Manual, inserts, cartridge/disc
4. OVERALL STRUCTURAL INTEGRITY

GAME IDENTIFICATION:
- Game title
- Platform (NES, SNES, PS1, etc.)
- Publisher
- Year
- Variant (first print, greatest hits, etc.)
- Sealed or Complete in Box

Respond in EXACT JSON format:
{{"grade": <1-10>, "grade_label": "<WATA label>", "seal_grade": "<A++|A+|A|B+|B|C+|C|NS>", "confidence": <0.0-1.0>,
"sealed": <true/false>,
"defects": [{{"type": "<defect>", "severity": "<trace|minor|moderate|major>", "location": "<box|seal|contents>", "penalty": <0.1-2.0>}}],
"reasoning": "<explanation>",
"item_info": {{"title": "<game title>", "platform": "<console>", "publisher": "<company>", "year": "<year>", "variant": "<first print|greatest hits|etc>", "cib": <true/false>, "manual": <true/false>}}}}"""
    }

    # Default to trading cards if type not found
    return base_prompts.get(collectible_type, base_prompts["trading_cards"])


async def grade_collectible(
    image_input: str,
    collectible_type: str,
    metadata: Optional[Dict] = None,
    providers: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Grade any collectible type using multi-AI consensus.

    Args:
        image_input: Base64 image data or file path
        collectible_type: Type of collectible (trading_cards, coins, stamps, etc.)
        metadata: Optional metadata about the item
        providers: Optional list of AI providers to use

    Returns:
        Grading result with consensus grade, defects, and item info
    """
    from .gemini_grader import grade_with_gemini
    from .openrouter_grader import grade_with_openrouter
    from .deepseek_grader import grade_with_deepseek
    from .grok_grader import grade_with_grok

    metadata = metadata or {}
    providers = providers or ["gemini", "openrouter", "deepseek", "grok"]

    # Get type-specific prompt
    prompt = build_grading_prompt(collectible_type, metadata)

    # Convert file path to base64 if needed
    image_base64 = image_input
    if os.path.exists(image_input):
        with open(image_input, 'rb') as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')
    elif image_input.startswith('data:'):
        image_base64 = image_input.split(',', 1)[1] if ',' in image_input else image_input

    # Collect grades from multiple providers
    results = []
    tasks = []

    async def call_provider(provider_name: str):
        try:
            if provider_name == "gemini":
                result = await grade_with_gemini(image_base64, metadata, prompt_override=prompt)
            elif provider_name == "openrouter":
                result = await grade_with_openrouter(image_base64, metadata, prompt_override=prompt)
            elif provider_name == "deepseek":
                result = await grade_with_deepseek(image_base64, metadata, prompt_override=prompt)
            elif provider_name == "grok":
                result = await grade_with_grok(image_base64, metadata, prompt_override=prompt)
            else:
                return None

            result['provider'] = provider_name
            return result
        except Exception as e:
            logger.error(f"{provider_name} grading failed: {e}")
            return None

    # Run providers in parallel
    tasks = [call_provider(p) for p in providers]
    provider_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter valid results
    for result in provider_results:
        if isinstance(result, dict) and result.get('grade', 0) > 0:
            results.append(result)

    if not results:
        return {
            'error': 'No AI providers returned valid grades',
            'grade': 0,
            'collectible_type': collectible_type
        }

    # Calculate consensus
    grades = [r.get('grade', 0) for r in results]
    avg_grade = sum(grades) / len(grades)

    # Get scale for this type
    scale = GRADING_SCALES.get(collectible_type, GRADING_SCALES.get("trading_cards"))

    # Normalize grade to scale
    min_grade = scale.get("min_grade", 1)
    max_grade = scale.get("max_grade", 10)
    normalized_grade = max(min_grade, min(max_grade, round(avg_grade * 2) / 2))

    # Get consensus on item info
    item_info = {}
    for result in results:
        info = result.get('item_info', {})
        for key, value in info.items():
            if value and key not in item_info:
                item_info[key] = value

    # Aggregate defects
    all_defects = []
    seen_defects = set()
    for result in results:
        for defect in result.get('defects', []):
            defect_key = (defect.get('type', ''), defect.get('location', ''))
            if defect_key not in seen_defects:
                seen_defects.add(defect_key)
                all_defects.append(defect)

    return {
        'grade': normalized_grade,
        'grade_label': get_grade_label(normalized_grade, collectible_type),
        'scale_name': scale.get("scale_name", "Unknown"),
        'confidence': sum(r.get('confidence', 0.7) for r in results) / len(results),
        'collectible_type': collectible_type,
        'item_info': item_info,
        'defects': all_defects[:10],  # Top 10 defects
        'reasoning': results[0].get('reasoning', '') if results else '',
        'subgrades': results[0].get('subgrades', {}),
        'provider_grades': [
            {'provider': r.get('provider', 'unknown'), 'grade': r.get('grade', 0)}
            for r in results
        ],
        'ai_sources_count': len(results)
    }


# Export convenience functions
async def grade_trading_card(image: str, metadata: Dict = None) -> Dict[str, Any]:
    return await grade_collectible(image, "trading_cards", metadata)

async def grade_coin(image: str, metadata: Dict = None) -> Dict[str, Any]:
    return await grade_collectible(image, "coins", metadata)

async def grade_stamp(image: str, metadata: Dict = None) -> Dict[str, Any]:
    return await grade_collectible(image, "stamps", metadata)

async def grade_vinyl(image: str, metadata: Dict = None) -> Dict[str, Any]:
    return await grade_collectible(image, "vinyl", metadata)

async def grade_action_figure(image: str, metadata: Dict = None) -> Dict[str, Any]:
    return await grade_collectible(image, "action_figures", metadata)

async def grade_video_game(image: str, metadata: Dict = None) -> Dict[str, Any]:
    return await grade_collectible(image, "video_games", metadata)
