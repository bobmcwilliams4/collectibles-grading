"""
AI Providers for Comic Grading
Real AI vision models using OpenRouter, Claude, Gemini
"""

from .ollama_vision_grader import (
    grade_with_ollama_vision,
    grade_with_llava,
    identify_comic_with_vision,
    multi_model_grade
)

from .openrouter_grader import (
    grade_with_openrouter,
    grade_with_llama_vision,
    grade_with_qwen_vision,
    multi_model_openrouter_grade
)

from .claude_grader import grade_with_claude
from .gemini_grader import grade_with_gemini
from .groq_grader import grade_with_groq
from .grok_grader import grade_with_grok
from .deepseek_grader import grade_with_deepseek
from .perplexity_research import research_comic_pricing as research_comic_price, research_comic_pricing, quick_price_lookup, full_comic_research
from .together_grader import grade_with_together
from .hyperbolic_grader import grade_with_hyperbolic
from .sambanova_grader import grade_with_sambanova

__all__ = [
    'grade_with_ollama_vision',
    'grade_with_llava',
    'identify_comic_with_vision',
    'multi_model_grade',
    'grade_with_openrouter',
    'grade_with_llama_vision',
    'grade_with_qwen_vision',
    'multi_model_openrouter_grade',
    'grade_with_claude',
    'grade_with_gemini',
    'grade_with_groq',
    'grade_with_grok',
    'grade_with_deepseek',
    'research_comic_price',
    'research_comic_pricing',
    'quick_price_lookup',
    'full_comic_research',
    'grade_with_together',
    'grade_with_hyperbolic',
    'grade_with_sambanova'
]
