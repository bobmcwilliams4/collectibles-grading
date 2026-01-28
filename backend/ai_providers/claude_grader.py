"""
Claude Vision Grader - Uses Anthropic's Claude API for comic grading
Supports multiple authentication methods:
1. CLAUDE_CODE_OAUTH_TOKEN - Uses Claude CLI subprocess (FREE with subscription!)
2. OAuth token from P:/SOVEREIGN_APPS/collectibles_grading_system/config/Claude_code_oauths.txt - Uses CLI
3. ANTHROPIC_API_KEY environment variable - Uses direct API (paid)
4. OAuth token from ~/.claude/.credentials.json - Uses CLI
5. Promethian Vault integration
6. Config file (ai_config.json)

NOTE: OAuth tokens (sk-ant-oat01-...) work via Claude CLI subprocess.
      API keys (sk-ant-api...) work via direct Anthropic API.
"""

import asyncio
import aiohttp
import base64
import json
import logging
import os
import re
import subprocess
import time
from typing import Dict, Any, Optional, Tuple
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

# Load .env file at import time (override system env vars)
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        load_dotenv(env_file, override=True)
except ImportError:
    pass  # dotenv not installed

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# Git Bash paths for Windows (needed for Claude CLI)
GIT_BASH_PATHS = [
    "H:/Tools/Git/usr/bin/bash.exe",
    "C:/Program Files/Git/usr/bin/bash.exe",
    "C:/Program Files (x86)/Git/usr/bin/bash.exe",
]

# Claude CLI paths for Windows
CLAUDE_CLI_PATHS = [
    os.path.expandvars(r"%APPDATA%\npm\claude.cmd"),
    os.path.expandvars(r"%APPDATA%\npm\claude"),
    "C:/Users/bobmc/AppData/Roaming/npm/claude.cmd",
    "claude",  # fallback to PATH
]


def get_claude_cli_path() -> str:
    """Find the Claude CLI executable path"""
    for path in CLAUDE_CLI_PATHS:
        expanded = os.path.expandvars(path)
        if Path(expanded).exists():
            return expanded
    return "claude"  # fallback

# OAuth Token File Paths
OAUTH_TOKEN_FILE = Path("P:/SOVEREIGN_APPS/collectibles_grading_system/config/Claude_code_oauths.txt")
CLAUDE_CREDENTIALS_FILE = Path.home() / ".claude" / ".credentials.json"

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


def get_oauth_from_credentials_file() -> Optional[str]:
    """Extract OAuth token from Claude Code credentials file"""
    if not CLAUDE_CREDENTIALS_FILE.exists():
        return None

    try:
        with open(CLAUDE_CREDENTIALS_FILE, 'r') as f:
            creds = json.load(f)
            oauth = creds.get('claudeAiOauth', {})
            access_token = oauth.get('accessToken')
            expires_at = oauth.get('expiresAt', 0)

            # Check if token is expired (with 5-minute buffer)
            current_time = int(time.time() * 1000)
            buffer = 5 * 60 * 1000  # 5 minutes

            if current_time < (expires_at - buffer):
                logger.info("Using OAuth token from ~/.claude/.credentials.json")
                return access_token
            else:
                logger.warning("OAuth token from credentials file is expired")
    except Exception as e:
        logger.error(f"Error reading credentials file: {e}")

    return None


def get_oauth_from_token_file() -> Optional[str]:
    """Read OAuth token from dedicated token file - searches for sk-ant- pattern"""
    if not OAUTH_TOKEN_FILE.exists():
        return None

    try:
        content = OAUTH_TOKEN_FILE.read_text()
        # Search for token pattern in the file (may have documentation)
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('sk-ant-oat') or line.startswith('sk-ant-api'):
                logger.info("Using OAuth token from P:/SOVEREIGN_APPS/collectibles_grading_system/config/Claude_code_oauths.txt")
                return line
    except Exception as e:
        logger.error(f"Error reading OAuth token file: {e}")

    return None


def get_api_from_vault() -> Optional[str]:
    """Try to get API key from Promethian Vault using the correct paths"""
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

        # Try to retrieve the Anthropic API key (note: use exact key name from vault)
        result = vault.retrieve("ANTHROPIC_API_KEY_api_key")

        if result.get("success") and result.get("secret_value"):
            logger.info("Using API key from Promethian Vault")
            return result["secret_value"]

    except ImportError as e:
        logger.debug(f"Promethian Vault not available: {e}")
    except Exception as e:
        logger.debug(f"Vault retrieval failed: {e}")

    return None


def is_oauth_token(token: str) -> bool:
    """Check if token is an OAuth token (vs API key)"""
    return token.startswith('sk-ant-oat')


def get_git_bash_path() -> Optional[str]:
    """Find Git Bash executable path for Windows CLI subprocess"""
    # Check environment variable first
    custom_path = os.environ.get('CLAUDE_CODE_GIT_BASH_PATH')
    if custom_path and Path(custom_path).exists():
        return custom_path

    # Check common paths
    for path in GIT_BASH_PATHS:
        if Path(path).exists():
            return path

    return None


def get_auth_token() -> Tuple[Optional[str], str]:
    """
    Get Claude authentication token and its type.

    Returns:
        Tuple of (token, auth_type) where auth_type is 'oauth' or 'api_key'
        OAuth tokens use CLI subprocess, API keys use direct API calls.
    """
    # 1. Check CLAUDE_CODE_OAUTH_TOKEN environment variable FIRST (preferred - FREE!)
    oauth_token = os.environ.get('CLAUDE_CODE_OAUTH_TOKEN')
    if oauth_token:
        logger.info("Using CLAUDE_CODE_OAUTH_TOKEN from environment (OAuth/CLI mode)")
        return oauth_token, 'oauth'

    # 2. Check OAuth token file
    oauth_token = get_oauth_from_token_file()
    if oauth_token:
        return oauth_token, 'oauth'

    # 3. Check Claude credentials file
    oauth_token = get_oauth_from_credentials_file()
    if oauth_token:
        return oauth_token, 'oauth'

    # 4. Check ANTHROPIC_API_KEY (uses direct API - may have cost)
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if api_key:
        logger.info("Using ANTHROPIC_API_KEY from environment (API mode)")
        return api_key, 'api_key'

    # 5. Try Promethian Vault
    vault_key = get_api_from_vault()
    if vault_key:
        auth_type = 'oauth' if is_oauth_token(vault_key) else 'api_key'
        return vault_key, auth_type

    # 6. Check config file
    config_path = Path(__file__).parent.parent / "config" / "ai_config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
                api_key = config.get('anthropic', {}).get('api_key')
                if api_key:
                    logger.info("Using API key from ai_config.json")
                    auth_type = 'oauth' if is_oauth_token(api_key) else 'api_key'
                    return api_key, auth_type
        except (json.JSONDecodeError, KeyError, IOError) as e:
            logger.debug(f"Config file error: {e}")

    logger.warning("No Claude API key found in any source")
    return None, 'none'


def get_api_key() -> Optional[str]:
    """Legacy function - returns just the token for backwards compatibility"""
    token, _ = get_auth_token()
    return token


async def grade_with_claude_cli(
    image_base64: str,
    metadata: Optional[Dict] = None,
    cover_side: str = 'front'
) -> Dict[str, Any]:
    """
    Grade a comic cover using Claude CLI with OAuth (subscription mode - FREE!)

    This saves the image to a temp file and uses Claude CLI's --add-dir to read it.
    Uses your $200/month subscription instead of pay-per-use API.

    Args:
        image_base64: Base64-encoded image
        metadata: Optional comic metadata
        cover_side: 'front' or 'back'

    Returns:
        Grading result dict
    """
    import tempfile
    import base64

    metadata = metadata or {}

    # Build the grading prompt
    prompt = f'''You are a professional CGC-certified comic book grader.
Analyze the comic cover image at the path I provide and give a detailed condition assessment.

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

COMPREHENSIVE METADATA: Also identify volume, cover_date, cover_price, writer, cover_artist, interior_artist, characters, era.

KEY ISSUE STATUS: Identify if this is a key issue (first appearance, death, origin, iconic cover, etc.)

Respond in EXACT JSON format only (no markdown, no explanation):
{{"grade": <0.5-10.0>, "grade_label": "<CGC label>", "confidence": <0.0-1.0>, "defects": [{{"type": "<defect>", "severity": "<trace|minor|moderate|major>", "location": "<where>", "penalty": <0.1-2.0>}}], "reasoning": "<explanation>", "comic_info": {{"title": "<series name>", "issue_number": "<issue # only>", "publisher": "<publisher>", "year": "<year>", "volume": "<vol or null>", "cover_date": "<month year>", "cover_price": "<price>", "writer": ["<name>"], "cover_artist": "<artist>", "characters": ["<name>"], "era": "<era>"}}, "key_issue_info": {{"is_key_issue": <true/false>, "key_reasons": ["<reason>"], "first_appearances": ["<character>"], "notable_events": ["<event>"]}}}}'''

    try:
        # Save image to temp file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp.write(base64.b64decode(image_base64))
            temp_image_path = tmp.name

        # Get temp directory for --add-dir
        temp_dir = str(Path(temp_image_path).parent)

        # Build Claude CLI command with image reference
        full_prompt = f"Please read the image at {temp_image_path} and analyze it.\n\n{prompt}"

        # Get Claude CLI path
        claude_cli = get_claude_cli_path()

        # Run Claude CLI with print mode
        cmd = [
            claude_cli,
            '-p',  # Print mode (non-interactive)
            '--add-dir', temp_dir,  # Allow access to temp dir
            '--output-format', 'text',
            full_prompt
        ]

        logger.info(f"Running Claude CLI: {claude_cli} -p --add-dir {temp_dir} ...")

        # CRITICAL: Remove ANTHROPIC_API_KEY from environment to force OAuth mode
        # The Claude CLI checks for API key first, which will fail if expired
        # Removing it forces the CLI to use OAuth subscription authentication
        clean_env = os.environ.copy()
        if 'ANTHROPIC_API_KEY' in clean_env:
            del clean_env['ANTHROPIC_API_KEY']
            logger.info("Removed ANTHROPIC_API_KEY from subprocess env to force OAuth mode")

        # Run subprocess with clean environment
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            env=clean_env
        )

        # Clean up temp file
        try:
            os.unlink(temp_image_path)
        except:
            pass

        # Log full output for debugging
        logger.info(f"Claude CLI return code: {result.returncode}")
        logger.info(f"Claude CLI stdout: {result.stdout[:500] if result.stdout else 'empty'}")
        logger.info(f"Claude CLI stderr: {result.stderr[:500] if result.stderr else 'empty'}")

        if result.returncode == 0 and result.stdout:
            response_text = result.stdout.strip()
            logger.info(f"Claude CLI response received ({len(response_text)} chars)")

            # Parse the response
            grading_result = parse_grading_response(response_text)
            grading_result['model'] = 'claude-sonnet-4 (OAuth/CLI)'
            grading_result['provider'] = 'Anthropic (Subscription)'
            grading_result['icon'] = '🟣'
            grading_result['auth_mode'] = 'oauth_cli'

            return grading_result
        else:
            # Check both stdout and stderr for error info
            error_msg = result.stderr.strip() or result.stdout.strip() or f"Unknown CLI error (code {result.returncode})"
            logger.error(f"Claude CLI error: {error_msg}")
            return {
                'error': f'Claude CLI error: {error_msg}',
                'grade': 0,
                'model': 'claude-sonnet-4 (OAuth/CLI)',
                'provider': 'Anthropic (Subscription)'
            }

    except subprocess.TimeoutExpired:
        logger.error("Claude CLI timeout after 120s")
        return {
            'error': 'Claude CLI timeout',
            'grade': 0,
            'model': 'claude-sonnet-4 (OAuth/CLI)',
            'provider': 'Anthropic (Subscription)'
        }
    except Exception as e:
        logger.error(f"Claude CLI grading error: {e}")
        return {
            'error': str(e),
            'grade': 0,
            'model': 'claude-sonnet-4 (OAuth/CLI)',
            'provider': 'Anthropic (Subscription)'
        }


async def grade_with_claude(
    image_input: str,
    metadata: Optional[Dict] = None,
    cover_side: str = 'front'
) -> Dict[str, Any]:
    """
    Grade a comic cover using Claude's vision API

    Args:
        image_input: Either a file path OR base64-encoded image data
        metadata: Optional comic metadata
        cover_side: 'front' or 'back'

    Returns:
        Grading result dict

    Authentication:
        - OAuth tokens (sk-ant-oat...) use Claude CLI subprocess
        - API keys (sk-ant-api...) use Anthropic SDK directly
    """
    token, auth_type = get_auth_token()
    if not token:
        return {
            'error': 'No Claude authentication configured (need ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN)',
            'grade': 0,
            'model': 'claude-sonnet-4-20250514',
            'provider': 'Anthropic'
        }

    # Convert file path to base64 if needed
    image_base64 = image_input
    if os.path.exists(image_input):
        # It's a file path - read and encode
        try:
            with open(image_input, 'rb') as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            return {
                'error': f'Failed to read image file: {e}',
                'grade': 0,
                'model': 'claude-sonnet-4-20250514',
                'provider': 'Anthropic'
            }
    elif image_input.startswith('data:'):
        # Remove data URL prefix if present
        image_base64 = image_input.split(',', 1)[1] if ',' in image_input else image_input

    # OAuth tokens MUST use CLI subprocess - SDK doesn't accept them as api_key
    if auth_type == 'oauth':
        logger.info("Using Claude via CLI subprocess (OAuth mode)")
        return await grade_with_claude_cli(image_base64, metadata, cover_side)

    # API keys can use SDK directly
    logger.info(f"Using Claude via Anthropic SDK ({auth_type} mode)")

    metadata = metadata or {}

    prompt = f"""You are a professional CGC-certified comic book grader.
Analyze this {cover_side} cover image and provide a detailed condition assessment.

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
- writer: Writer(s) name(s) - use your comic knowledge
- cover_artist: Cover artist if known
- interior_artist: Interior penciler if known
- characters: Main characters featured (especially first appearances)
- era: Golden Age (1938-1956), Silver Age (1956-1970), Bronze Age (1970-1985), Copper Age (1985-1991), Modern Age (1991+)

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
        "writer": ["<writer name>"],
        "cover_artist": "<cover artist or null>",
        "interior_artist": "<interior artist or null>",
        "characters": ["<character name>"],
        "era": "<era name>"
    }},
    "key_issue_info": {{
        "is_key_issue": <true/false>,
        "key_reasons": ["<reason>"],
        "first_appearances": ["<character>"],
        "notable_events": ["<event>"]
    }}
}}"""

    try:
        # Use Anthropic SDK - works with both OAuth tokens and API keys
        import anthropic

        client = anthropic.Anthropic(api_key=token)

        # Call Claude with vision
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        response_text = response.content[0].text
        logger.info(f"Claude SDK response received ({len(response_text)} chars)")

        # Parse JSON from response
        grading_result = parse_grading_response(response_text)
        grading_result['model'] = 'claude-sonnet-4'
        grading_result['provider'] = 'Anthropic'
        grading_result['icon'] = '🟣'
        grading_result['auth_mode'] = auth_type

        return grading_result

    except asyncio.TimeoutError:
        return {'error': 'Timeout', 'grade': 0, 'model': 'claude-sonnet-4', 'provider': 'Anthropic'}
    except Exception as e:
        logger.error(f"Claude grading error: {e}")
        return {'error': str(e), 'grade': 0, 'model': 'claude-sonnet-4', 'provider': 'Anthropic'}


def validate_issue_number(issue_num: str) -> str:
    """Clean and validate extracted issue number"""
    if not issue_num:
        return "Unknown"

    # Convert to string if needed
    issue_num = str(issue_num).strip()

    # Remove common prefixes
    cleaned = re.sub(r'^(#|NO\.?\s*|ISSUE\s*)', '', issue_num, flags=re.I)

    # Reject month names (common DC cover date confusion)
    months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    for month in months:
        if cleaned.upper().startswith(month):
            # Try to extract number after month
            match = re.search(r'\d+', cleaned)
            if match:
                return match.group()
            return "Unknown"

    return cleaned if cleaned else "Unknown"


def parse_grading_response(response_text: str) -> Dict[str, Any]:
    """Parse AI response into structured data"""
    try:
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            data = json.loads(json_match.group())
            grade = float(data.get('grade', 6.0))
            grade = max(0.5, min(10.0, grade))
            grade = round(grade * 2) / 2

            # Validate and clean issue number
            comic_info = data.get('comic_info', {})
            if comic_info.get('issue_number'):
                comic_info['issue_number'] = validate_issue_number(comic_info['issue_number'])

            return {
                'grade': grade,
                'grade_label': data.get('grade_label', get_grade_label(grade)),
                'confidence': float(data.get('confidence', 0.85)),
                'defects': data.get('defects', []),
                'reasoning': data.get('reasoning', ''),
                'comic_info': comic_info,
                'key_issue_info': data.get('key_issue_info', {})
            }
    except json.JSONDecodeError as e:
        logger.debug(f"JSON parse error: {e}")

    # Fallback
    return {
        'grade': 6.0,
        'grade_label': 'Fine',
        'confidence': 0.6,
        'defects': [],
        'reasoning': response_text[:500],
        'comic_info': {},
        'key_issue_info': {}
    }

# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACK WRAPPER - Use free OpenRouter/Ollama when Claude/Anthropic unavailable
# ═══════════════════════════════════════════════════════════════════════════════

async def grade_with_claude_with_fallback(
    image_base64: str,
    metadata: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Grade comic with automatic fallback to free providers.

    Fallback chain: Claude/Anthropic -> OpenRouter Free Vision -> Ollama Vision
    """
    # Try primary provider first
    result = await grade_with_claude(image_base64, metadata=metadata, **kwargs)

    # If error and fallback available, try alternatives
    if (result.get('error') or result.get('grade', 0) == 0) and FALLBACK_AVAILABLE:
        logger.info(f"Claude/Anthropic grading failed, trying fallbacks...")

        # Use centralized fallback function
        fallback_result = await fallback_grade(
            image_base64=image_base64,
            prompt="Grade this comic book cover on CGC scale (0.5-10.0). Identify title, issue, defects.",
            primary_result=result
        )

        if fallback_result.get('grade', 0) > 0:
            fallback_result['original_provider'] = 'Claude/Anthropic'
            return fallback_result

    return result
