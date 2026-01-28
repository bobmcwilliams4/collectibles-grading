# ElevenLabs TTS v3 (Alpha) - Complete Reference Guide

> **Use this skill when**: Generating voice dialogue for Bree, Collection Master, or any ElevenLabs TTS integration. Reference for audio tags, SSML syntax, pronunciation, multi-speaker dialogue, and optimization.

---

## Audio Tags: THE KEY CONCEPT

### **AUDIO TAGS ARE FREEFORM - USE ANYTHING!**

> **CRITICAL**: The tags below are just EXAMPLES. ElevenLabs v3 understands natural language descriptions. **Whatever emotion, sound, or delivery style you can describe in brackets `[]`, the model will attempt to perform.**

**The Rule**: If you can describe it, put it in `[brackets]` and try it!

### Examples of What Works:

**Emotions (infinite possibilities):**
```
[ecstatic], [devastated], [seething with rage], [barely containing laughter]
[mock horror], [dripping with contempt], [oozing sarcasm], [genuinely touched]
[playfully condescending], [passive aggressive], [manic energy], [dead inside]
[orgasmic excitement], [soul-crushing disappointment], [unhinged], [feral]
[horny], [disgusted but intrigued], [reluctantly impressed], [petty as fuck]
[channeling a Karen], [big dick energy], [small pp energy], [chaotic neutral]
```

**Delivery Styles:**
```
[like a disappointed parent], [like a sassy gay best friend]
[like a drill sergeant], [like a stoned surfer], [like a valley girl]
[like an auctioneer], [like a drunk uncle at thanksgiving]
[like morgan freeman narrating], [like a shakespearean actor]
[like a phone sex operator], [like reading a eulogy]
[mockingly], [condescendingly], [patronizingly], [menacingly]
[seductively], [threateningly], [conspiratorially], [accusingly]
```

**Physical/Vocal Actions:**
```
[burps], [hiccups], [yawns], [sneezes], [coughs], [gags], [retches]
[spits], [hisses], [growls], [purrs], [squeals], [screams], [shrieks]
[moans], [groans], [whimpers], [sobs], [wails], [cackles], [snickers]
[scoffs], [snorts derisively], [blows raspberry], [makes fart noise with mouth]
[inhales sharply through teeth], [clicks tongue disapprovingly]
[wolf whistle], [slow clap], [chef's kiss], [mic drop]
```

**Intensity Modifiers:**
```
[slightly annoyed] vs [absolutely fucking livid]
[chuckles] vs [laughing hysterically] vs [cackling like a maniac]
[whispers] vs [barely audible whisper] vs [stage whisper]
[yelling] vs [SCREAMING AT THE TOP OF LUNGS]
```

**Accents (freeform):**
```
[strong X accent] - X can be ANYTHING:
French, Russian, British, Australian, Southern US, Boston, New York
Jamaican, Scottish, Irish, Indian, German, Italian, Spanish, Japanese
Valley Girl, Surfer Dude, Redneck, Posh British, Cockney, etc.
```

**Sound Effects:**
```
[gunshot], [explosion], [glass breaking], [door slam], [thunder]
[applause], [crowd booing], [record scratch], [sad trombone]
[airhorn], [ding], [buzzer], [cash register], [rimshot]
```

### Pro Tips:
1. **Be specific** - `[laughing nervously while trying to hold it together]` > `[laughs]`
2. **Combine emotions** - `[excited but trying to play it cool]`
3. **Add context** - `[realizing mid-sentence this was a mistake]`
4. **Go wild** - The model is surprisingly good at interpreting creative descriptions

---

## Common Tags Quick Reference (Non-Exhaustive Examples)

### Emotional
```
[happy], [sad], [angry], [scared], [surprised], [disgusted], [contemptuous]
[excited], [bored], [anxious], [confident], [shy], [proud], [ashamed]
[jealous], [grateful], [hopeful], [hopeless], [nostalgic], [bitter]
[sarcastic], [sincere], [mocking], [sympathetic], [apathetic], [curious]
```

### Physical Sounds
```
[laughs], [cries], [sighs], [gasps], [groans], [moans], [screams]
[whispers], [shouts], [mumbles], [stutters], [slurs], [hiccups]
[coughs], [sneezes], [yawns], [burps], [gulps], [swallows]
[clears throat], [exhales], [inhales sharply], [sniffles]
```

### Delivery Modifiers
```
[slowly], [quickly], [softly], [loudly], [monotone], [sing-song]
[dramatically], [casually], [formally], [intimately], [distantly]
[warmly], [coldly], [robotically], [dreamily], [urgently]
```

---

## Stability Settings

| Setting | Behavior | Best For |
|---------|----------|----------|
| **Creative** | More emotional, expressive, prone to hallucinations | Maximum expressiveness with audio tags |
| **Natural** | Closest to original voice, balanced | General use, balanced output |
| **Robust** | Highly stable, less responsive to tags | Consistent output like v2, less creative |

**For Bree's vulgar commentary**: Use **Creative** or **Natural** for maximum sass.

---

## SSML Syntax

### Pauses (Break Tags)
```xml
<break time="0.5s" />   <!-- Half second pause -->
<break time="1.5s" />   <!-- 1.5 second pause -->
<break time="3.0s" />   <!-- Max 3 seconds -->
```

**Example:**
```
"Hold on, let me think." <break time="1.5s" /> "Alright, I've got it."
```

**Alternatives (less consistent):**
- Dashes (`-` or `—`) for short pauses
- Ellipses (`…`) for hesitant tones

### Phoneme Tags (Pronunciation)
**Only works with**: Eleven Flash v2, Eleven Turbo v2, Eleven English v1

**CMU Arpabet (Recommended):**
```xml
<phoneme alphabet="cmu-arpabet" ph="M AE1 D IH0 S AH0 N">Madison</phoneme>
```

**IPA:**
```xml
<phoneme alphabet="ipa" ph="ˈmædɪsən">Madison</phoneme>
```

**Stress Marking Example:**
```xml
<phoneme alphabet="cmu-arpabet" ph="P R AH0 N AH0 N S IY EY1 SH AH0 N">pronunciation</phoneme>
```

### Alias Tags (Word Substitution)
```xml
<lexeme>
  <grapheme>Claughton</grapheme>
  <alias>Cloffton</alias>
</lexeme>

<lexeme>
  <grapheme>CGC</grapheme>
  <alias>C G C</alias>
</lexeme>
```

---

## Punctuation Effects

| Punctuation | Effect |
|-------------|--------|
| `...` (ellipses) | Adds pauses and weight |
| `CAPS` | Increases emphasis |
| `!` | Adds excitement/urgency |
| `?` | Rising intonation |
| `-` or `—` | Short pause |

**Example:**
```
"It was a VERY long day [sigh] … nobody listens anymore."
```

---

## Multi-Speaker Dialogue Format

```
Speaker 1: [excitedly] Sam! Have you tried the new comic grading system?

Speaker 2: [curiously] Just got it! The AI consensus is amazing—
[whispers] like having seven experts in your pocket!

Speaker 1: [impressed] Ooh, fancy! Check this out—
[dramatically] "This comic is a solid 9.4, you beautiful bastard!"

Speaker 2: [laughing] That's so Bree!
```

### Overlapping/Interruption
```
Speaker 1: [starting to speak] So I was thinking we could—

Speaker 2: [jumping in] —grade the whole collection tonight?

Speaker 1: [surprised] Exactly! How did you—

Speaker 2: [overlapping] —know what you were thinking? Lucky guess!
```

---

## The "Enhance" Prompt

Use this prompt to auto-add audio tags to plain text:

```
# Instructions
## 1. Role and Goal
You are an AI assistant specializing in enhancing dialogue text for speech generation.
Your **PRIMARY GOAL** is to dynamically integrate **audio tags** (e.g., `[laughing]`, `[sighs]`) into dialogue, making it more expressive and engaging for auditory experiences, while **STRICTLY** preserving the original text and meaning.

## 2. Core Directives
### Positive Imperatives (DO):
* DO integrate **audio tags** to add expression, emotion, and realism
* DO ensure tags are contextually appropriate
* DO place tags strategically - before or after the dialogue segment
* DO strive for diverse emotional expressions

### Negative Imperatives (DO NOT):
* DO NOT alter, add, or remove any words from the original text
* DO NOT use tags like `[standing]`, `[grinning]`, `[pacing]`, `[music]`
* DO NOT use tags for anything other than voice (no music/sound effects)
* DO NOT invent new dialogue lines

## 3. Workflow
1. Analyze Dialogue - understand mood, context, emotional tone
2. Select Tag(s) - choose suitable audio tags
3. Integrate Tag(s) - place in square brackets `[]`
4. Add Emphasis - CAPS, punctuation, ellipses where appropriate
5. Verify Appropriateness - confirm natural fit

## 4. Output Format
* Present ONLY the enhanced dialogue text
* Audio tags MUST be in square brackets
* Maintain narrative flow

## 5. Example
**Input**: "Are you serious? I can't believe you did that!"
**Output**: "[appalled] Are you SERIOUS? [sighs] I can't believe you did that!"
```

---

## Speed/Pacing Control

| Value | Effect |
|-------|--------|
| `0.7` | Minimum - Slow delivery |
| `1.0` | Default - Normal speed |
| `1.2` | Maximum - Fast delivery |

**Note:** Extreme values may affect quality.

**Narrative pacing:**
```
"I… I thought you'd understand," he said, his voice slowing with disappointment.
```

---

## Voice Selection Strategy

### For Expressive Characters (Bree)
- Use emotionally diverse IVC voices
- Include neutral AND dynamic samples in training
- Creative/Natural stability settings

### For Consistent Narration (Collection Master)
- Use neutral, stable voices
- Targeted emotion in training data
- Natural/Robust stability settings

### Voice Types by Latency
1. **Fastest**: Default voices, Synthetic voices, IVC
2. **Slower**: Professional Voice Clones (PVC)

---

## Latency Optimization

### Model Selection
| Model | Latency | Quality |
|-------|---------|---------|
| Flash v2/v2.5 | ~75ms | Good (slight reduction) |
| Turbo v2/v2.5 | ~150ms | Better |
| Multilingual v2 | ~300ms+ | Best |

### Endpoint Types
1. **Regular**: Complete audio file in single response
2. **Streaming**: Progressive audio chunks (SSE)
3. **WebSockets**: Bidirectional, real-time (best for LLM output)

### Geographic TTFB (Flash + WebSockets)
| Region | Latency |
|--------|---------|
| US | 150-200ms |
| EU | 230ms (150-200ms with EU stack) |
| NE Asia | 250-350ms |
| South Asia | 380-440ms |

---

## Pronunciation Dictionary Format (PLS)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<lexicon version="1.0"
      xmlns="http://www.w3.org/2005/01/pronunciation-lexicon"
      alphabet="cmu-arpabet" xml:lang="en-GB">
  <lexeme>
    <grapheme>CGC</grapheme>
    <alias>C G C</alias>
  </lexeme>
  <lexeme>
    <grapheme>CBCS</grapheme>
    <alias>C B C S</alias>
  </lexeme>
  <lexeme>
    <grapheme>McFarlane</grapheme>
    <phoneme>M AH0 K F AR1 L AH0 N</phoneme>
  </lexeme>
</lexicon>
```

---

## Text Normalization for TTS

### Common Issues & Fixes
| Input | Normalized |
|-------|------------|
| `$42.50` | forty-two dollars and fifty cents |
| `CGC 9.8` | C G C nine point eight |
| `#300` | issue number three hundred |
| `1988` | nineteen eighty-eight |
| `1st appearance` | first appearance |

### LLM Normalization Prompt
```
Convert the output text into a format suitable for text-to-speech.
Ensure that numbers, symbols, and abbreviations are expanded for clarity when read aloud.
Expand all abbreviations to their full spoken forms.
```

---

## Bree-Specific Examples

### Savage Low Grade Reaction
```
[disgusted] Oh for fuck's sake... [sighs heavily]
You call THIS a comic? [laughs bitterly]
I've seen better condition on a NAPKIN at Denny's!
[sarcastic] Congratulations on your 2.5, champ.
<break time="0.5s" />
[mocking] Maybe try storing your comics somewhere OTHER than your ass crack next time!
```

### Excited High Grade Reaction
```
[gasps] Holy SHIT! [excited]
Are you seeing this?! [laughing]
A 9.6 on Amazing Spider-Man 300!
[impressed] The centering is GORGEOUS, the spine is TIGHT...
<break time="0.3s" />
[whispers] I think I'm in love.
[normal] This bad boy is worth some SERIOUS cash!
```

### Collection Master (Gandalf-style)
```
[thoughtfully] Hmmmm... [long pause]
This comic has traveled far... through many hands...
[dramatically] And yet, it endures!
<break time="0.5s" />
[warmly] A grade of 8.5 I bestow upon this weathered tome.
[wisely] Guard it well, young collector. Guard it well.
```

---

## Sound Effects Prompting

Navigate to Sound Effects in ElevenLabs UI.

**Settings:**
- Duration: Auto or up to 30 seconds
- Looping: On for seamless loops
- Prompt Influence: Default 30%

**Example Prompts:**
```
Old-school funky brass stabs from a vinyl sample, stem, 88 bpm in F# minor
Comic book page turning, crisp paper sound
Cash register cha-ching, vintage mechanical
Dramatic orchestral hit for reveal moment
```

---

## API Quick Reference

### Text-to-Speech Endpoint
```python
from elevenlabs import generate, Voice, VoiceSettings

audio = generate(
    text="[excited] This is a 9.8! [laughs]",
    voice=Voice(
        voice_id="bree_voice_id",
        settings=VoiceSettings(
            stability=0.3,  # Creative
            similarity_boost=0.8,
            style=0.5,
            use_speaker_boost=True
        )
    ),
    model="eleven_multilingual_v2"
)
```

### WebSocket for Real-Time
```python
from elevenlabs import ElevenLabs

client = ElevenLabs(api_key="your_key")
# Use auto_mode=True for automatic chunking
```

### Global Low-Latency Endpoint
Replace `api.elevenlabs.io` with `api-global-preview.elevenlabs.io`

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Audio tags not working | Check voice compatibility, use Creative/Natural stability |
| Inconsistent pauses | Use `<break time="x.xs" />` instead of `...` |
| Wrong pronunciation | Use phoneme tags or alias in pronunciation dictionary |
| Too fast/slow | Adjust speed setting (0.7-1.2) or use narrative cues |
| Emotion mismatch | Add explicit dialogue tags, match tags to voice character |
| Hallucinations | Increase stability toward Robust, simplify tags |

---

## Version Notes

- **v3 Alpha**: Minimum 250 characters recommended for consistent output
- **PVCs**: Not fully optimized for v3 yet - use IVC or designed voices
- **Phoneme tags**: Only work with Flash v2, Turbo v2, English v1
