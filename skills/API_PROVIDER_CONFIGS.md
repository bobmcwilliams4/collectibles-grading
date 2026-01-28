# API PROVIDER CONFIGURATIONS - QUICK REFERENCE

## Authority Level 11.0 | Collectibles Grading System Skill

---

## PROVIDER STATUS OVERVIEW

| Provider | Status | Vision | Rate Limit | Cost |
|----------|--------|--------|------------|------|
| Google Gemini | ✅ WORKING | Yes | 60/min | FREE |
| xAI Grok | ✅ WORKING | Yes | 60/min | Paid |
| Groq | ✅ WORKING | Yes | 30/min | FREE |
| OpenRouter | ✅ WORKING | Yes | Varies | FREE models |
| Perplexity | ✅ WORKING | No | 50/min | Paid |
| DeepSeek | ✅ WORKING | Yes | 60/min | Cheap |
| Claude OAuth | ✅ WORKING | No | Token-based | Subscription |
| Anthropic API | ❌ EXPIRED | Yes | N/A | Expired |
| OpenAI | ❌ EXPIRED | Yes | N/A | Expired |

---

## GOOGLE GEMINI (PRIMARY VISION)

### Configuration

```python
GEMINI_CONFIG = {
    "model": "gemini-2.0-flash",
    "api_base": "https://generativelanguage.googleapis.com/v1beta",
    "max_tokens": 4096,
    "temperature": 0.3,
    "vision_enabled": True
}
```

### Request Format

```python
import google.generativeai as genai

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

model = genai.GenerativeModel("gemini-2.0-flash")

# Vision request
response = model.generate_content([
    "Grade this comic book image...",
    {"mime_type": "image/jpeg", "data": base64_image}
])
```

### Rate Limits

| Tier | RPM | TPM | Daily |
|------|-----|-----|-------|
| Free | 60 | 1M | Unlimited |
| Paid | 1000 | 4M | Unlimited |

### Error Responses

```python
# Common errors
"429 RESOURCE_EXHAUSTED" -> Rate limited, wait 60s
"400 INVALID_ARGUMENT" -> Bad image format
"500 INTERNAL" -> Retry with exponential backoff
```

---

## XAI GROK (SECONDARY VISION)

### Configuration

```python
GROK_CONFIG = {
    "model": "grok-2-vision-1212",
    "api_base": "https://api.x.ai/v1",
    "max_tokens": 4096,
    "temperature": 0.3,
    "vision_enabled": True
}
```

### Request Format

```python
import httpx

headers = {
    "Authorization": f"Bearer {os.environ['XAI_API_KEY']}",
    "Content-Type": "application/json"
}

payload = {
    "model": "grok-2-vision-1212",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "Grade this comic..."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
    }],
    "max_tokens": 4096
}

response = httpx.post("https://api.x.ai/v1/chat/completions", json=payload, headers=headers)
```

### Rate Limits

| Model | RPM | Context |
|-------|-----|---------|
| grok-2-vision | 60 | 32K |
| grok-2 | 60 | 128K |

---

## GROQ (FAST INFERENCE)

### Configuration

```python
GROQ_CONFIG = {
    "model": "meta-llama/llama-4-scout-17b",
    "api_base": "https://api.groq.com/openai/v1",
    "max_tokens": 4096,
    "temperature": 0.3,
    "vision_enabled": True
}
```

### Request Format

```python
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

response = client.chat.completions.create(
    model="meta-llama/llama-4-scout-17b",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Grade this comic..."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
    }],
    max_tokens=4096
)
```

### Rate Limits

| Model | RPM | TPM |
|-------|-----|-----|
| llama-4-scout | 30 | 14.4K |
| llama-3.2-vision | 30 | 7K |

---

## OPENROUTER (FREE MODELS)

### Configuration

```python
OPENROUTER_CONFIG = {
    "api_base": "https://openrouter.ai/api/v1",
    "free_vision_models": [
        "qwen/qwen2.5-vl-72b-instruct:free",
        "meta-llama/llama-3.2-11b-vision-instruct:free",
        "google/gemma-3-27b-it:free",
        "mistralai/mistral-small-3.1-24b-instruct:free"
    ],
    "max_tokens": 4096,
    "temperature": 0.3
}
```

### Request Format

```python
import httpx

headers = {
    "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://collectibles-grading.local",
    "X-Title": "Collectibles Grading System"
}

payload = {
    "model": "qwen/qwen2.5-vl-72b-instruct:free",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "Grade this comic..."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
    }],
    "max_tokens": 4096
}

response = httpx.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
```

### Free Vision Models

| Model | Context | Quality |
|-------|---------|---------|
| qwen2.5-vl-72b | 32K | Excellent |
| llama-3.2-11b-vision | 128K | Good |
| gemma-3-27b-it | 128K | Good |
| mistral-small-3.1 | 32K | Fair |

### Rate Limits (Free Tier)

- 20 requests/minute
- 200 requests/day per model
- Rotate models to increase throughput

---

## PERPLEXITY (RESEARCH/PRICING)

### Configuration

```python
PERPLEXITY_CONFIG = {
    "model": "sonar",
    "api_base": "https://api.perplexity.ai",
    "max_tokens": 4096,
    "temperature": 0.2,
    "search_domain_filter": ["gocollect.com", "heritage.com", "ebay.com"]
}
```

### Request Format

```python
import httpx

headers = {
    "Authorization": f"Bearer {os.environ['PERPLEXITY_API_KEY']}",
    "Content-Type": "application/json"
}

payload = {
    "model": "sonar",
    "messages": [{
        "role": "user",
        "content": "Find recent sold prices for Amazing Spider-Man #129 CGC 9.4"
    }],
    "max_tokens": 4096,
    "search_domain_filter": ["gocollect.com", "heritage.com", "ebay.com"],
    "return_citations": True
}

response = httpx.post("https://api.perplexity.ai/chat/completions", json=payload, headers=headers)
```

### Models

| Model | Use Case | Context |
|-------|----------|---------|
| sonar | Web search | 127K |
| sonar-pro | Deep research | 200K |

---

## DEEPSEEK (BUDGET VISION)

### Configuration

```python
DEEPSEEK_CONFIG = {
    "model": "deepseek-vl",
    "api_base": "https://api.deepseek.com/v1",
    "max_tokens": 4096,
    "temperature": 0.3,
    "vision_enabled": True
}
```

### Request Format

```python
import httpx

headers = {
    "Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
    "Content-Type": "application/json"
}

payload = {
    "model": "deepseek-vl",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "Grade this comic..."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
    }],
    "max_tokens": 4096
}

response = httpx.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers)
```

### Pricing

| Model | Input | Output |
|-------|-------|--------|
| deepseek-vl | $0.14/M | $0.28/M |
| deepseek-chat | $0.07/M | $0.14/M |

---

## CLAUDE OAUTH (VOICE DIALOGUE)

### Configuration

```python
CLAUDE_OAUTH_CONFIG = {
    "model": "claude-sonnet-4-20250514",
    "api_base": "https://api.anthropic.com/v1",
    "max_tokens": 1024,
    "temperature": 0.8,
    "vision_enabled": False  # Use for text only
}
```

### Request Format

```python
import anthropic

client = anthropic.Anthropic(
    api_key=os.environ["CLAUDE_CODE_OAUTH_TOKEN"]  # OAuth token, not API key
)

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": f"Generate Bree's response for a {grade} grade {title} #{issue}..."
    }]
)
```

### Token-Based Limits

- Based on subscription tier
- ~45 messages/5 hours (Pro tier)
- Token refresh every 5 hours

---

## ERROR HANDLING PATTERNS

### Retry Logic

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError))
)
async def call_provider(provider, payload):
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            provider["url"],
            json=payload,
            headers=provider["headers"]
        )
        response.raise_for_status()
        return response.json()
```

### Fallback Chain

```python
PROVIDER_FALLBACK_ORDER = [
    "gemini",      # Primary - free, reliable
    "grok",        # Secondary - good quality
    "groq",        # Fast fallback
    "openrouter",  # Free models backup
    "deepseek"     # Budget backup
]

async def grade_with_fallback(image_base64):
    for provider in PROVIDER_FALLBACK_ORDER:
        try:
            result = await call_grader(provider, image_base64)
            if result and result.get("grade"):
                return result
        except Exception as e:
            log.warning(f"{provider} failed: {e}")
            continue
    raise Exception("All providers failed")
```

### Common Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 429 | Rate limited | Wait + retry |
| 400 | Bad request | Check payload |
| 401 | Auth failed | Check API key |
| 403 | Forbidden | Check permissions |
| 500 | Server error | Retry with backoff |
| 503 | Overloaded | Wait + fallback |

---

## ENVIRONMENT VARIABLES

```bash
# Vision Providers
GOOGLE_API_KEY=your_gemini_key
XAI_API_KEY=your_grok_key
GROQ_API_KEY=your_groq_key
OPENROUTER_API_KEY=your_openrouter_key
DEEPSEEK_API_KEY=your_deepseek_key

# Research Provider
PERPLEXITY_API_KEY=your_perplexity_key

# Voice/Dialogue
CLAUDE_CODE_OAUTH_TOKEN=your_oauth_token
ELEVENLABS_API_KEY=your_elevenlabs_key

# Expired (DO NOT USE)
# ANTHROPIC_API_KEY=expired
# OPENAI_API_KEY=expired
```

---

## PROVIDER SELECTION LOGIC

```python
def select_providers(task_type: str) -> list:
    """Select appropriate providers based on task"""
    
    if task_type == "vision_grading":
        return ["gemini", "grok", "groq", "openrouter"]
    
    elif task_type == "research_pricing":
        return ["perplexity"]  # Fallback: openrouter gemma
    
    elif task_type == "voice_dialogue":
        return ["claude_oauth"]
    
    elif task_type == "text_only":
        return ["groq", "openrouter"]
    
    return ["gemini"]  # Default
```

---

*Authority Level 11.0 | API Provider Configurations Skill*
