#!/usr/bin/env python3
"""
Add Fallback AI Integration to All Provider Files
Adds imports and wrapper functions for fallback to OpenRouter & Ollama
"""

import os
import re

AI_PROVIDERS_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════════════════════
# RESEARCH PROVIDERS - Add fallback to text-based research functions
# ═══════════════════════════════════════════════════════════════════════════════

def add_fallback_to_perplexity():
    """Add fallback imports and wrapper to perplexity_research.py"""
    filepath = os.path.join(AI_PROVIDERS_DIR, "perplexity_research.py")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if already has fallback
    if "fallback_providers" in content:
        print("perplexity_research.py - already has fallback imports")
        return

    # Add import after datetime import
    import_block = """from datetime import datetime

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
"""

    content = content.replace("from datetime import datetime\n", import_block)

    # Add fallback wrapper function at end
    fallback_wrapper = """

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
    \"\"\"
    Research pricing with automatic fallback to free providers.

    Fallback chain: Perplexity -> OpenRouter Free -> Ollama Local
    \"\"\"
    # Try primary first
    result = await research_comic_pricing(title, issue_number, grade, publisher, year, is_key_issue)

    # If error and fallback available, try alternatives
    if result.get('error') and FALLBACK_AVAILABLE:
        logger.info("Perplexity unavailable, trying OpenRouter fallback...")

        # Build simplified prompt for fallback
        prompt = f\"\"\"Research pricing for: {title} #{issue_number} (CGC {grade})
Publisher: {publisher or 'Unknown'}, Year: {year or 'Unknown'}
Key issue: {is_key_issue}

Provide JSON with: ebay_sales, estimated_value (low/mid/high), market_analysis\"\"\"

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
"""

    content = content.rstrip() + fallback_wrapper

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print("perplexity_research.py - added fallback imports and wrapper")


def add_fallback_to_cohere():
    """Add fallback imports and wrapper to cohere_research.py"""
    filepath = os.path.join(AI_PROVIDERS_DIR, "cohere_research.py")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if "fallback_providers" in content:
        print("cohere_research.py - already has fallback imports")
        return

    # Add import after pathlib import
    import_block = """from pathlib import Path

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
"""

    content = content.replace("from pathlib import Path\n", import_block)

    # Add fallback wrapper function at end
    fallback_wrapper = """

# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACK WRAPPER - Use free OpenRouter/Ollama when Cohere unavailable
# ═══════════════════════════════════════════════════════════════════════════════

async def research_comic_history_with_fallback(
    title: str,
    issue_number: str,
    publisher: Optional[str] = None
) -> Dict[str, Any]:
    \"\"\"
    Research comic history with automatic fallback to free providers.

    Fallback chain: Cohere -> OpenRouter Free -> Ollama Local
    \"\"\"
    result = await research_comic_history(title, issue_number, publisher)

    if result.get('error') and FALLBACK_AVAILABLE:
        logger.info("Cohere unavailable, trying OpenRouter fallback...")

        prompt = f\"\"\"Research comic book history and significance:
Comic: {title} #{issue_number} ({publisher or 'Unknown publisher'})

Provide JSON with: publication date/era, creative_team, story summary,
key_issue status, first appearances, characters featured.\"\"\"

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
"""

    content = content.rstrip() + fallback_wrapper

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print("cohere_research.py - added fallback imports and wrapper")


# ═══════════════════════════════════════════════════════════════════════════════
# VISION GRADERS - Add fallback to vision-based grading functions
# ═══════════════════════════════════════════════════════════════════════════════

def add_fallback_to_grader(filename: str, provider_name: str, main_function: str):
    """Generic function to add fallback to a grader file"""
    filepath = os.path.join(AI_PROVIDERS_DIR, filename)

    if not os.path.exists(filepath):
        print(f"{filename} - FILE NOT FOUND")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if "fallback_providers" in content:
        print(f"{filename} - already has fallback imports")
        return

    # Find a good place to add imports (after pathlib import)
    import_block = f"""from pathlib import Path

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
"""

    if "from pathlib import Path" in content:
        content = content.replace("from pathlib import Path\n", import_block)
    else:
        # Add after logging import
        content = content.replace(
            "logger = logging.getLogger(__name__)",
            f"logger = logging.getLogger(__name__)\n\n# Fallback providers\ntry:\n    from .fallback_providers import openrouter_vision_fallback, ollama_vision_fallback, grade_with_fallback as fallback_grade\n    FALLBACK_AVAILABLE = True\nexcept ImportError:\n    FALLBACK_AVAILABLE = False"
        )

    # Add fallback wrapper at end
    fallback_wrapper = f"""

# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACK WRAPPER - Use free OpenRouter/Ollama when {provider_name} unavailable
# ═══════════════════════════════════════════════════════════════════════════════

async def {main_function}_with_fallback(
    image_base64: str,
    metadata: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    \"\"\"
    Grade comic with automatic fallback to free providers.

    Fallback chain: {provider_name} -> OpenRouter Free Vision -> Ollama Vision
    \"\"\"
    # Try primary provider first
    result = await {main_function}(image_base64, metadata=metadata, **kwargs)

    # If error and fallback available, try alternatives
    if (result.get('error') or result.get('grade', 0) == 0) and FALLBACK_AVAILABLE:
        logger.info(f"{provider_name} grading failed, trying fallbacks...")

        # Use centralized fallback function
        fallback_result = await fallback_grade(
            image_base64=image_base64,
            prompt="Grade this comic book cover on CGC scale (0.5-10.0). Identify title, issue, defects.",
            primary_result=result
        )

        if fallback_result.get('grade', 0) > 0:
            fallback_result['original_provider'] = '{provider_name}'
            return fallback_result

    return result
"""

    content = content.rstrip() + fallback_wrapper

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"{filename} - added fallback imports and wrapper")


def main():
    """Add fallbacks to all AI provider files"""
    print("=" * 60)
    print("Adding Fallback AI Integration to All Providers")
    print("=" * 60)

    # Research providers
    print("\n[RESEARCH PROVIDERS]")
    add_fallback_to_perplexity()
    add_fallback_to_cohere()

    # Vision graders
    print("\n[VISION GRADERS]")
    graders = [
        ("claude_grader.py", "Claude/Anthropic", "grade_with_claude"),
        ("gemini_grader.py", "Gemini/Google", "grade_with_gemini"),
        ("grok_grader.py", "Grok/xAI", "grade_with_grok"),
        ("groq_grader.py", "Groq", "grade_with_groq"),
        ("huggingface_grader.py", "HuggingFace", "grade_with_huggingface"),
        ("deepseek_grader.py", "DeepSeek", "grade_with_deepseek"),
        ("cloudflare_grader.py", "Cloudflare", "grade_with_cloudflare"),
    ]

    for filename, provider, func in graders:
        add_fallback_to_grader(filename, provider, func)

    print("\n" + "=" * 60)
    print("DONE - All providers now have fallback capability!")
    print("Fallback chain: Primary API -> OpenRouter Free -> Ollama Local")
    print("=" * 60)


if __name__ == "__main__":
    main()
