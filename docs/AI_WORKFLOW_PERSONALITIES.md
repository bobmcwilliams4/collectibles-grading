# COLLECTIBLES GRADING - AI WORKFLOW & PERSONALITIES

## AI PROVIDERS INVOLVED (Current System)

### 1. VISION GRADING AIs (Analyze Comic Images)

| Provider      | Model                                         | Role                         | Icon  | Status  |
|---------------|-----------------------------------------------|------------------------------|-------|---------|
| Google Gemini | gemini-2.0-flash                              | Primary vision grader        | 💎    | WORKING |
| xAI Grok      | grok-2-vision-1212                            | Secondary vision grader      | 🤖    | WORKING |
| Groq          | meta-llama/llama-4-scout-17b                  | Fast inference grader        | ⚡     | WORKING |
| OpenRouter    | qwen2.5-vl-72b, llama-3.2-vision, gemma-3-27b | Multi-model consensus (FREE) | 🦙/🌐 | WORKING |
| DeepSeek      | deepseek-vl                                   | Budget vision grader         | -     | WORKING |

### 2. RESEARCH & PRICING AIs

| Provider              | Model               | Role                                                 | Status  |
|-----------------------|---------------------|------------------------------------------------------|---------|
| Perplexity            | sonar               | Web search for market prices, CGC census, sales data | WORKING |
| OpenRouter (fallback) | gemma-3-27b-it:free | Research when Perplexity unavailable                 | WORKING |

### 3. VOICE PERSONALITY AIs

| Provider           | Role                                           | Voice Engine           |
|--------------------|------------------------------------------------|------------------------|
| Claude (via OAuth) | Generates dynamic dialogue for Bree & Raistlin | Anthropic API          |
| ElevenLabs         | Text-to-speech synthesis                       | eleven_multilingual_v2 |

---

## THE TWO AI PERSONALITIES

### BREE - The Unfiltered Truth-Teller

**File:** backend/bree_voice_feedback.py  
**Voice ID:** pzKXffibtCDxnrVO8d1U (custom expressive voice)  
**Obscenity Level:** 1-15 scale based on grade

**Personality:**
- Brutally honest, vulgar, no-BS
- LOVES high-grade valuable comics - praises enthusiastically
- DESPISES garbage comics - verbally destroys them
- 15-point obscenity scale that increases as comic quality DECREASES
- Uses Claude OAuth to generate dynamic responses (not scripted)

**Emotion States:**
| State     | Grade    | Level   | Example                           |
|-----------|----------|---------|-----------------------------------|
| ECSTATIC  | 9.8+     | 1-2     | "Holy shit, that's beautiful!"    |
| IMPRESSED | 9.4+     | 3-4     | "Damn, respect."                  |
| PLEASED   | 9.0+     | 5-6     | "Not bad, not great."             |
| NEUTRAL   | 8.0+     | 7-8     | "Meh, whatever."                  |
| ANNOYED   | 7.0+     | 9-10    | "This is mediocre bullshit."      |
| PISSED    | 5.0+     | 11-12   | Heavy profanity                   |
| FURIOUS   | 3.0+     | 13-14   | Extreme vulgarity                 |
| NUCLEAR   | <2.0     | 15      | "ARE YOU FUCKING KIDDING ME?!"    |

---

### RAISTLIN MAJERE - The Archmage Grader

**File:** backend/raistlin_voice_feedback.py  
**Voice ID:** fyX4AP5q3XiIRxqPsZBy (Gandalf-like deep voice)  
**Character:** From Dragonlance fantasy series

**Personality:**
- Brilliant, sardonic, mysterious archmage
- Speaks with archaic formality + dark wit
- References "hourglass eyes" that see all flaws
- Impressed by perfection, contemptuous of mediocrity
- Uses Claude OAuth to generate dynamic in-character dialogue

**Emotion States:**
| State         | Grade | Description                    |
|---------------|-------|--------------------------------|
| TRIUMPHANT    | 9.8+  | Rare genuine approval          |
| IMPRESSED     | 9.0+  | Maintains dignity but impressed|
| PLEASED       | 8.0+  | Acceptable quality             |
| NEUTRAL       | 6.0+  | Measured, unremarkable         |
| CONTEMPLATIVE | 4.0+  | Philosophical disappointment   |
| SARDONIC      | <4.0  | Disdain with dark wit          |

---

## COMPLETE GRADING WORKFLOW

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER UPLOADS IMAGE                           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  IMAGE PREPROCESSING                            │
│  • Auto contrast correction                                     │
│  • Denoising (Non-Local Means)                                  │
│  • Quality scoring (blur/focus detection)                       │
│  • Base64 encoding for API transmission                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              PARALLEL AI GRADING (asyncio)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ GEMINI   │  │  GROK    │  │  GROQ    │  │OPENROUTER│        │
│  │ 💎       │  │  🤖      │  │  ⚡       │  │  🌐      │        │
│  │          │  │          │  │          │  │ (4 free  │        │
│  │ Primary  │  │Secondary │  │  Fast    │  │ models)  │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │             │             │              │               │
│       └─────────────┼─────────────┼──────────────┘               │
│                     ▼                                            │
│           ┌─────────────────────┐                               │
│           │ Each AI returns:    │                               │
│           │ • grade (0.5-10.0)  │                               │
│           │ • grade_label       │                               │
│           │ • confidence        │                               │
│           │ • defects[]         │                               │
│           │ • reasoning         │                               │
│           │ • comic_info{}      │                               │
│           │ • key_issue_info{}  │                               │
│           └─────────────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  CONSENSUS CALCULATION                          │
├─────────────────────────────────────────────────────────────────┤
│  • Weighted average: 60% avg grade + 40% min grade              │
│  • Round to nearest 0.5 (CGC scale)                             │
│  • Combine defects from all models (deduplicate)                │
│  • Calculate confidence from grade agreement                     │
│  • Merge comic_info from first successful result                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                PRICE RESEARCH (if enabled)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────┐    ┌─────────────────────┐                 │
│  │  PERPLEXITY    │───▶│ Web search for:     │                 │
│  │  (Primary)     │    │ • eBay sold prices  │                 │
│  │                │    │ • Heritage Auctions │                 │
│  └────────────────┘    │ • GoCollect data    │                 │
│          │             │ • CGC census        │                 │
│          ▼ (fallback)  │ • Market trends     │                 │
│  ┌────────────────┐    └─────────────────────┘                 │
│  │  OPENROUTER    │                                            │
│  │  gemma-3-27b   │                                            │
│  └────────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VOICE FEEDBACK                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           CLAUDE (via OAuth Token)                      │   │
│  │           Generates dynamic dialogue                    │   │
│  │           for selected personality                      │   │
│  └────────────────────────┬────────────────────────────────┘   │
│                           │                                     │
│           ┌───────────────┴───────────────┐                    │
│           ▼                               ▼                     │
│  ┌────────────────┐              ┌────────────────┐            │
│  │     BREE       │              │   RAISTLIN     │            │
│  │ Vulgar/Honest  │              │ Arcane/Mystic  │            │
│  │ 15-level scale │              │ Wizard persona │            │
│  └────────┬───────┘              └────────┬───────┘            │
│           │                               │                     │
│           └───────────────┬───────────────┘                    │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              ELEVENLABS TTS                             │   │
│  │         Text → Speech synthesis                         │   │
│  │         Emotion-adjusted voice settings                 │   │
│  └────────────────────────┬────────────────────────────────┘   │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              PYGAME AUDIO                               │   │
│  │         Play generated MP3 audio                        │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  DISPLAY RESULTS                                │
│  • Grade popup modal with all AI grades                         │
│  • Comprehensive metadata (title, issue, creative team, etc.)   │
│  • Key issue highlights                                         │
│  • Defects list with severity                                   │
│  • Price estimates at various grades                            │
│  • Save to catalog option                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## METADATA COLLECTED BY EACH AI

All vision graders now request this comprehensive data:

```json
{
  "grade": 8.5,
  "grade_label": "Very Fine+",
  "confidence": 0.85,
  "defects": [
    {"type": "spine stress", "severity": "minor", "location": "top spine", "penalty": 0.3}
  ],
  "reasoning": "Light wear on spine, corners sharp...",
  "comic_info": {
    "title": "Amazing Spider-Man",
    "issue_number": "129",
    "publisher": "Marvel Comics",
    "year": "1974",
    "volume": "1",
    "cover_date": "February 1974",
    "cover_price": "$0.20",
    "story_title": "The Punisher Strikes Twice!",
    "writer": ["Gerry Conway"],
    "cover_artist": "Gil Kane",
    "interior_artist": "Ross Andru",
    "editor": "Roy Thomas",
    "genre": ["Superhero", "Action"],
    "characters": ["Spider-Man", "Punisher", "Jackal"],
    "page_count": 32,
    "format": "Standard",
    "series_type": "ongoing",
    "era": "Bronze Age",
    "country": "USA",
    "language": "English"
  },
  "key_issue_info": {
    "is_key_issue": true,
    "key_reasons": ["First appearance of The Punisher"],
    "first_appearances": ["Punisher (Frank Castle)"],
    "notable_events": []
  }
}
```

---

## PROBLEMS ENCOUNTERED & SOLUTIONS

| Problem                              | Solution                                                     | Status |
|--------------------------------------|--------------------------------------------------------------|--------|
| Anthropic API key expired            | Switched to Claude OAuth token from Claude Code subscription | SOLVED |
| Python 3.13 + Promethian Vault crash | Disabled vault on Python 3.13+, use env vars directly        | SOLVED |
| JSON parse error in edit modal       | Added HTML attribute escaping with escapeAttr()              | SOLVED |
| DC Comics issue number confusion     | Added detailed prompt instructions about "OCT NO. 12" format | SOLVED |
| Hover popup not showing metadata     | Implemented comprehensive popup in renderComicsGrid()        | SOLVED |
| Voice personality responses scripted | Switched to dynamic Claude OAuth generation                  | SOLVED |

---

## API KEYS CURRENTLY WORKING

✅ GOOGLE_API_KEY (Gemini)  
✅ OPENROUTER_API_KEY (free models)  
✅ XAI_API_KEY / GROK_API_KEY  
✅ GROQ_API_KEY  
✅ PERPLEXITY_API_KEY  
✅ DEEPSEEK_API_KEY  
✅ ELEVENLABS_API_KEY (voice)  
✅ CLAUDE_CODE_OAUTH_TOKEN (voice dialogue)  
❌ ANTHROPIC_API_KEY (expired)  
❌ OPENAI_API_KEY (expired)
