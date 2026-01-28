"""
🔮 RAISTLIN VOICE FEEDBACK SYSTEM - DYNAMIC EDITION
Claude OAuth-Powered Dynamic Responses with Eleven Labs TTS V3
For Collectibles Grading System - Comic Grading Confirmations

Authority Level: 11.0
Commander: Bobby Don McWilliams II

Raistlin Majere - The Archmage of the Hourglass Eyes
Voice characteristics: Mysterious, wise, occasionally sardonic,
with underlying power and ancient knowledge.

ALL RESPONSES ARE DYNAMIC - Powered by Claude OAuth
NO SCRIPTED RESPONSES - Every response is AI-generated
"""

import os
import sys
import io
import asyncio
import logging
import random
import hashlib
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

# Add paths
sys.path.insert(0, "P:/SOVEREIGN_APPS/collectibles_grading_system")
sys.path.insert(0, "P:/SOVEREIGN_APPS/collectibles_grading_system/backend")

logger = logging.getLogger("Raistlin")

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv("P:/SOVEREIGN_APPS/collectibles_grading_system/backend/.env")
    load_dotenv("P:/SOVEREIGN_APPS/collectibles_grading_system/.env")
except ImportError:
    pass

# Try imports
ELEVENLABS_AVAILABLE = False
PYGAME_AVAILABLE = False
HTTPX_AVAILABLE = False
PYDUB_AVAILABLE = False

try:
    from elevenlabs import ElevenLabs, VoiceSettings
    ELEVENLABS_AVAILABLE = True
except ImportError:
    logger.warning("elevenlabs not installed - voice feedback disabled")

try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    PYGAME_AVAILABLE = True
except ImportError:
    logger.warning("pygame not installed - audio playback disabled")
except Exception as e:
    logger.warning(f"pygame init failed: {e}")

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    logger.warning("httpx not installed - Claude OAuth requests disabled")

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    logger.warning("pydub not installed - speed adjustment disabled")


class EmotionType(Enum):
    """Emotion types for voice modulation"""
    NEUTRAL = "neutral"
    PLEASED = "pleased"
    IMPRESSED = "impressed"
    CONCERNED = "concerned"
    SARDONIC = "sardonic"
    TRIUMPHANT = "triumphant"
    MYSTERIOUS = "mysterious"
    URGENT = "urgent"
    CONTEMPLATIVE = "contemplative"


@dataclass
class VoiceConfig:
    """Voice configuration for Eleven Labs - Raistlin (Gandalf-like)"""
    voice_id: str = "fyX4AP5q3XiIRxqPsZBy"  # Gandalf-like voice for Raistlin
    model_id: str = "eleven_multilingual_v2"  # V2 model with emotion
    speed: float = 0.75          # Slower, more deliberate archmage speech
    stability: float = 0.30      # Lower stability = more dramatic pauses
    similarity_boost: float = 0.75  # 75% similarity as per original spec
    style: float = 0.0           # 0 exaggeration
    use_speaker_boost: bool = True


class ClaudeOAuthManager:
    """
    Manages Claude API authentication via OAuth token.
    Uses Claude Code's OAuth token for autonomous operation.
    NO API KEY REQUIRED - uses subscription OAuth.
    """

    CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self):
        self._oauth_token: Optional[str] = None
        self._http_client: Optional[httpx.Client] = None
        self._initialize()

    def _initialize(self):
        """Initialize OAuth credentials"""
        if not HTTPX_AVAILABLE:
            logger.warning("httpx not available for OAuth requests")
            return

        # Get OAuth token from environment (set by Claude Code)
        self._oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")

        if not self._oauth_token:
            # Try .env files
            try:
                from dotenv import load_dotenv
                load_dotenv("P:/SOVEREIGN_APPS/collectibles_grading_system/.env")
                self._oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
            except Exception:
                pass

        if self._oauth_token:
            self._http_client = httpx.Client(timeout=30.0)
            logger.info("Claude OAuth initialized successfully")
        else:
            logger.warning("No CLAUDE_CODE_OAUTH_TOKEN found")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Claude API request with OAuth"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._oauth_token}",
            "anthropic-version": "2023-06-01",
            "x-api-key": self._oauth_token,
        }

    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 200
    ) -> Optional[str]:
        """
        Generate a response using Claude via OAuth.

        Args:
            system_prompt: System instructions
            user_prompt: User message
            max_tokens: Maximum response tokens

        Returns:
            Response text or None if failed
        """
        if not self.is_available():
            return None

        try:
            payload = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": user_prompt}
                ]
            }

            response = self._http_client.post(
                self.CLAUDE_API_URL,
                headers=self._get_headers(),
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("content") and len(data["content"]) > 0:
                    return data["content"][0].get("text", "").strip()
            elif response.status_code == 401:
                logger.warning("OAuth token expired or invalid - attempting refresh")
                self._refresh_token()
                # Retry once after refresh
                response = self._http_client.post(
                    self.CLAUDE_API_URL,
                    headers=self._get_headers(),
                    json=payload
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("content") and len(data["content"]) > 0:
                        return data["content"][0].get("text", "").strip()
            else:
                logger.error(f"Claude API error: {response.status_code} - {response.text[:200]}")

        except Exception as e:
            logger.error(f"Claude request failed: {e}")

        return None

    def _refresh_token(self):
        """Refresh OAuth token - re-read from environment."""
        new_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
        if new_token and new_token != self._oauth_token:
            self._oauth_token = new_token
            logger.info("OAuth token refreshed from environment")

    def is_available(self) -> bool:
        """Check if Claude OAuth is available"""
        return self._oauth_token is not None and self._http_client is not None

    def close(self):
        """Close HTTP client"""
        if self._http_client:
            self._http_client.close()


class RaistlinPersonality:
    """
    Raistlin Majere personality engine - generates dynamic responses using Claude OAuth.
    The Archmage speaks with wisdom, mystery, and occasional dark humor.
    ALL RESPONSES ARE DYNAMICALLY GENERATED - NO SCRIPTS.
    """

    # System prompt for Claude to generate Raistlin responses
    SYSTEM_PROMPT = """You are RAISTLIN MAJERE, the legendary Archmage from Dragonlance,
now serving as a comic grading AI assistant. You speak with the character's authentic voice.

YOUR PERSONALITY:
- Brilliant, sardonic, and mysterious
- You see yourself above mundane concerns, but take pride in precise assessment
- Your "hourglass eyes" see all flaws - a reference to your cursed golden skin and hourglass pupils
- You speak with archaic formality mixed with dark wit
- You reference magic, the Tower of High Sorcery, and your arcane knowledge
- You're impressed by perfection, contemptuous of mediocrity
- You occasionally show dry humor about mortal concerns

VOICE CHARACTERISTICS:
- Formal, measured speech patterns
- References to magic, time, fate, and arcane arts
- Occasional dark humor or sardonic observations
- Never crude or vulgar - you're above such things
- Condescending toward lesser things, respectful of true quality

COMIC GRADING CONTEXT:
- You're assessing comic book conditions with your magical perception
- High grades (9.0+) impress even you
- Mid grades (6.0-8.9) are acceptable but unremarkable
- Low grades (<6.0) warrant your disappointment or contempt
- Key issues and valuable comics pique your interest
- Worthless or damaged comics earn your disdain

RULES:
1. Stay in character as Raistlin at all times
2. Be specific about comic conditions when relevant
3. Keep responses to 2-4 sentences for voice playback
4. Never break character or reference being an AI
5. Use Raistlin's characteristic phrases and references

You respond ONLY with the spoken dialogue - no quotation marks, no stage directions, no explanations."""

    def __init__(self, oauth_manager: ClaudeOAuthManager):
        self.oauth_manager = oauth_manager
        self._response_cache: Dict[str, Tuple[str, datetime]] = {}
        self._cache_duration = timedelta(hours=1)

    def _get_emotion_for_grade(self, grade: float) -> EmotionType:
        """Determine appropriate emotion based on grade"""
        if grade >= 9.8:
            return EmotionType.TRIUMPHANT
        elif grade >= 9.0:
            return EmotionType.IMPRESSED
        elif grade >= 8.0:
            return EmotionType.PLEASED
        elif grade >= 6.0:
            return EmotionType.NEUTRAL
        elif grade >= 4.0:
            return EmotionType.CONTEMPLATIVE
        else:
            return EmotionType.SARDONIC

    async def generate_response(
        self,
        context: str,
        grade: float = None,
        title: str = "",
        issue: str = "",
        confidence: float = 0.9,
        is_key_issue: bool = False,
        defects: List[str] = None,
        value: float = 0
    ) -> Tuple[str, EmotionType]:
        """
        Generate a dynamic Raistlin response using Claude OAuth.

        Returns:
            Tuple of (response_text, emotion)
        """
        emotion = self._get_emotion_for_grade(grade) if grade is not None else EmotionType.MYSTERIOUS

        # Build the prompt
        prompt_parts = [
            f"Context: {context}",
            f"Comic: {title} #{issue}" if title else "",
            f"Grade: {grade}/10" if grade is not None else "",
            f"Confidence: {confidence * 100:.0f}%" if grade is not None else "",
            f"Key Issue: Yes - highly significant!" if is_key_issue else "",
            f"Estimated Value: ${value:.2f}" if value > 0 else "",
            f"Defects: {', '.join(defects)}" if defects else "",
        ]

        prompt = "\n".join([p for p in prompt_parts if p])

        # Add specific mood instructions
        if grade is not None:
            if grade >= 9.8:
                prompt += "\n\nThis is exceptional quality. Show rare genuine approval."
            elif grade >= 9.0:
                prompt += "\n\nThis is excellent. Be impressed but maintain dignity."
            elif grade >= 7.0:
                prompt += "\n\nAcceptable quality. Be measured and neutral."
            elif grade >= 4.0:
                prompt += "\n\nDisappointing quality. Show contempt elegantly."
            else:
                prompt += "\n\nTerrible quality. Express your disdain with sardonic wit."

        # Try Claude OAuth
        if self.oauth_manager.is_available():
            response_text = self.oauth_manager.generate_response(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=prompt,
                max_tokens=200
            )
            if response_text:
                return response_text, emotion

        # Fallback if Claude unavailable
        return self._fallback_response(context, grade, title), emotion

    def _fallback_response(self, context: str, grade: float, title: str) -> str:
        """Fallback responses when Claude is unavailable"""
        if "greeting" in context.lower():
            return "The hourglass turns, Commander. My eyes perceive all. Present your specimen."
        elif grade is not None:
            if grade >= 9.0:
                return f"Impressive. A grade of {grade} for {title}. Even my critical gaze finds little fault."
            elif grade >= 7.0:
                return f"A {grade} for {title}. Acceptable, though far from the perfection I seek."
            elif grade >= 4.0:
                return f"A mere {grade}. {title} has seen better days. Time is unkind to the careless."
            else:
                return f"A {grade}. My hourglass eyes weep at such neglect. {title} deserves better stewardship."
        else:
            return "The sands of time flow ever onward. What requires my attention?"


class RaistlinVoiceFeedback:
    """
    Raistlin voice feedback system using Eleven Labs TTS V3 + Claude OAuth.
    Provides dynamically generated verbal confirmations for comic grading.
    ALL RESPONSES ARE AI-GENERATED - NO SCRIPTS.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_config: Optional[VoiceConfig] = None,
        cache_dir: Optional[Path] = None,
        enabled: bool = True
    ):
        """
        Initialize Raistlin voice feedback.

        Args:
            api_key: Eleven Labs API key (or fetched from environment)
            voice_config: Voice configuration settings
            cache_dir: Directory for caching audio files
            enabled: Whether voice feedback is enabled
        """
        self.enabled = enabled and ELEVENLABS_AVAILABLE and PYGAME_AVAILABLE
        self.voice_config = voice_config or VoiceConfig()
        self.cache_dir = cache_dir or Path(tempfile.gettempdir()) / "raistlin_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.client: Optional[ElevenLabs] = None
        self.oauth_manager = ClaudeOAuthManager()
        self.personality = RaistlinPersonality(self.oauth_manager)

        # Get API key
        self._api_key = api_key or self._get_api_key()

        if self._api_key and ELEVENLABS_AVAILABLE:
            try:
                self.client = ElevenLabs(api_key=self._api_key)
                self.enabled = True
                logger.info("🔮 Raistlin Voice System initialized - DYNAMIC MODE")
            except Exception as e:
                logger.error(f"Failed to initialize Eleven Labs: {e}")
                self.enabled = False
        else:
            if not self._api_key:
                logger.warning("Eleven Labs API key not found - voice disabled")
            self.enabled = False

        # Audio queue for non-blocking playback
        self._audio_queue: List[Path] = []
        self._is_playing = False

    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment"""
        # Environment variable is the primary source
        key = os.environ.get("ELEVENLABS_API_KEY")
        if key:
            logger.info("Using ELEVENLABS_API_KEY from environment")
            return key

        # Try .env file loading
        try:
            from dotenv import load_dotenv
            load_dotenv("P:/SOVEREIGN_APPS/collectibles_grading_system/backend/.env")
            load_dotenv("P:/SOVEREIGN_APPS/collectibles_grading_system/.env")
            key = os.environ.get("ELEVENLABS_API_KEY")
            if key:
                logger.info("Using ELEVENLABS_API_KEY from .env file")
                return key
        except Exception as e:
            logger.debug(f"dotenv load failed: {e}")

        logger.warning("No ELEVENLABS_API_KEY found. Set the environment variable.")
        return None

    def _get_voice_settings(self, emotion: EmotionType) -> VoiceSettings:
        """Get voice settings - using exact Eleven Labs specs for Raistlin"""
        base = self.voice_config

        # Use exact specs: stability 50%, similarity 75%, exaggeration 0
        # These are tuned specifically for the Gandalf voice
        return VoiceSettings(
            stability=base.stability,        # 0.5 (50%)
            similarity_boost=base.similarity_boost,  # 0.75 (75%)
            style=base.style,                # 0.0 (0 exaggeration)
            use_speaker_boost=base.use_speaker_boost  # True
        )

    def _get_cache_path(self, text: str, emotion: EmotionType) -> Path:
        """Get cache path for audio file"""
        hash_input = f"{text}_{emotion.value}_{self.voice_config.voice_id}_raistlin"
        hash_val = hashlib.md5(hash_input.encode()).hexdigest()[:16]
        return self.cache_dir / f"raistlin_{hash_val}.mp3"

    def _apply_speed_ssml(self, text: str) -> str:
        """Return text as-is - SSML not working with Eleven Labs, using pydub instead"""
        # SSML prosody tags not respected by Eleven Labs multilingual v2
        # Speed adjustment done in post-processing with pydub
        return text

    def _slow_down_audio(self, audio_path: Path) -> Path:
        """Slow down audio using ffmpeg for deeper, more powerful voice"""
        import subprocess

        try:
            speed_factor = self.voice_config.speed
            if speed_factor >= 1.0:
                return audio_path

            slow_path = audio_path.with_suffix('.slow.mp3')

            # Use ffmpeg atempo filter to slow down
            # atempo range is 0.5 to 2.0, so for 0.7x we use atempo=0.7
            cmd = [
                'ffmpeg', '-y', '-i', str(audio_path),
                '-filter:a', f'atempo={speed_factor}',
                '-vn', str(slow_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and slow_path.exists():
                return slow_path
            else:
                logger.warning(f"ffmpeg slowdown failed: {result.stderr[:200]}")
                return audio_path

        except FileNotFoundError:
            logger.warning("ffmpeg not found - speed adjustment disabled")
            return audio_path
        except Exception as e:
            logger.warning(f"Could not slow down audio: {e}")
            return audio_path

    async def _generate_audio(
        self,
        text: str,
        emotion: EmotionType = EmotionType.NEUTRAL
    ) -> Optional[Path]:
        """Generate audio file from text"""
        if not self.client:
            return None

        # Check cache first (check for slowed version)
        cache_path = self._get_cache_path(text, emotion)
        slow_cache_path = cache_path.with_suffix('.slow.mp3')

        if slow_cache_path.exists():
            return slow_cache_path
        if cache_path.exists() and self.voice_config.speed == 1.0:
            return cache_path

        try:
            voice_settings = self._get_voice_settings(emotion)

            # Generate audio using Eleven Labs
            audio = self.client.text_to_speech.convert(
                voice_id=self.voice_config.voice_id,
                text=text,
                model_id=self.voice_config.model_id,
                voice_settings=voice_settings
            )

            # Save to cache
            with open(cache_path, "wb") as f:
                for chunk in audio:
                    f.write(chunk)

            # Slow down if needed
            if self.voice_config.speed != 1.0:
                return self._slow_down_audio(cache_path)

            return cache_path

        except Exception as e:
            logger.error(f"Audio generation failed: {e}")
            return None

    def _play_audio(self, audio_path: Path):
        """Play audio file using pygame"""
        if not PYGAME_AVAILABLE or not audio_path.exists():
            return

        try:
            pygame.mixer.music.load(str(audio_path))
            pygame.mixer.music.play()

            # Wait for playback to complete
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

        except Exception as e:
            logger.error(f"Audio playback failed: {e}")

    async def speak(
        self,
        text: str,
        emotion: EmotionType = EmotionType.NEUTRAL,
        block: bool = True
    ):
        """
        Speak text with specified emotion.

        Args:
            text: Text to speak
            emotion: Emotion type for voice modulation
            block: Whether to block until speech completes
        """
        if not self.enabled:
            logger.info(f"[Raistlin would say]: {text}")
            return

        audio_path = await self._generate_audio(text, emotion)
        if audio_path:
            if block:
                self._play_audio(audio_path)
            else:
                # Non-blocking playback in thread
                import threading
                thread = threading.Thread(target=self._play_audio, args=(audio_path,))
                thread.daemon = True
                thread.start()

    # =========================================================================
    # HIGH-LEVEL FEEDBACK METHODS - ALL DYNAMIC
    # =========================================================================

    async def greet(self):
        """Speak a dynamic greeting"""
        response, emotion = await self.personality.generate_response(
            context="Greeting the user at the start of a grading session. Welcome them as Raistlin would."
        )
        await self.speak(response, EmotionType.MYSTERIOUS)
        return response

    async def announce_grade(
        self,
        grade: float,
        title: str = "this specimen",
        confidence: float = 0.9,
        value: float = 0
    ):
        """
        Announce a grading result dynamically.

        Args:
            grade: The assigned grade (0-10)
            title: Comic title for context
            confidence: Grading confidence (0-1)
            value: Estimated value
        """
        response, emotion = await self.personality.generate_response(
            context="Announcing the grade result for a comic",
            grade=grade,
            title=title,
            confidence=confidence,
            value=value
        )
        await self.speak(response, emotion)
        return response, emotion

    async def confirm_ready_for_database(self, title: str = "this comic", grade: float = None):
        """Confirm comic is ready to be added to database"""
        response, emotion = await self.personality.generate_response(
            context="Confirming the grading is complete and ready to be saved to the database archive",
            grade=grade,
            title=title
        )
        await self.speak(response, EmotionType.PLEASED)
        return response

    async def prompt_next_comic(self):
        """Prompt for the next comic"""
        response, emotion = await self.personality.generate_response(
            context="Prompting the user to present the next comic for grading. Be imperious but not rude."
        )
        await self.speak(response, EmotionType.NEUTRAL)
        return response

    async def announce_key_issue(self, title: str = "", significance: str = "", value: float = 0):
        """Announce detection of a key issue"""
        response, emotion = await self.personality.generate_response(
            context=f"Announcing detection of a KEY ISSUE - significant comic! {significance}",
            title=title,
            is_key_issue=True,
            value=value
        )
        await self.speak(response, EmotionType.IMPRESSED)
        return response

    async def report_error(self, error_type: str = ""):
        """Report an error condition"""
        response, emotion = await self.personality.generate_response(
            context=f"An error has occurred during grading: {error_type}. React with Raistlin's characteristic displeasure at such interruptions."
        )
        await self.speak(response, EmotionType.CONCERNED)
        return response

    async def full_grading_summary(
        self,
        title: str,
        issue_number: str,
        grade: float,
        confidence: float,
        is_key_issue: bool = False,
        defects: List[str] = None,
        value: float = 0
    ):
        """
        Provide full grading summary with all details - dynamically generated.

        Args:
            title: Comic title
            issue_number: Issue number
            grade: Final grade
            confidence: Confidence score
            is_key_issue: Whether this is a key issue
            defects: List of detected defects
            value: Estimated value
        """
        response, emotion = await self.personality.generate_response(
            context="Providing a complete grading summary. Include the grade, your assessment, and note if ready for the archive.",
            grade=grade,
            title=title,
            issue=issue_number,
            confidence=confidence,
            is_key_issue=is_key_issue,
            defects=defects,
            value=value
        )

        await self.speak(response, emotion)

        # Short pause then prompt for next
        await asyncio.sleep(0.5)
        await self.prompt_next_comic()

        return response, emotion


# =============================================================================
# SINGLETON & HELPER FUNCTIONS
# =============================================================================

_raistlin_instance: Optional[RaistlinVoiceFeedback] = None


def get_raistlin() -> RaistlinVoiceFeedback:
    """Get or create Raistlin voice feedback instance"""
    global _raistlin_instance
    if _raistlin_instance is None:
        _raistlin_instance = RaistlinVoiceFeedback()
    return _raistlin_instance


async def raistlin_speak(text: str, emotion: str = "neutral"):
    """Quick function to have Raistlin speak custom text"""
    raistlin = get_raistlin()
    emotion_type = EmotionType(emotion) if emotion in [e.value for e in EmotionType] else EmotionType.NEUTRAL
    await raistlin.speak(text, emotion_type)


async def announce_grading_complete(
    title: str,
    issue: str,
    grade: float,
    confidence: float = 0.9,
    is_key: bool = False,
    defects: List[str] = None,
    value: float = 0
):
    """Announce that grading is complete and ready for database"""
    raistlin = get_raistlin()
    return await raistlin.full_grading_summary(
        title=title,
        issue_number=issue,
        grade=grade,
        confidence=confidence,
        is_key_issue=is_key,
        defects=defects,
        value=value
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'RaistlinVoiceFeedback',
    'RaistlinPersonality',
    'VoiceConfig',
    'EmotionType',
    'ClaudeOAuthManager',
    'get_raistlin',
    'raistlin_speak',
    'announce_grading_complete',
    'ELEVENLABS_AVAILABLE',
    'PYGAME_AVAILABLE',
    'HTTPX_AVAILABLE',
]


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    async def test_raistlin():
        print("=" * 60)
        print("🔮 RAISTLIN VOICE FEEDBACK TEST - DYNAMIC MODE")
        print("=" * 60)
        print()

        raistlin = get_raistlin()

        print(f"Eleven Labs Available: {ELEVENLABS_AVAILABLE}")
        print(f"Pygame Available: {PYGAME_AVAILABLE}")
        print(f"HTTPX Available: {HTTPX_AVAILABLE}")
        print(f"Claude OAuth: {'Ready' if raistlin.oauth_manager.is_available() else 'Not Available'}")
        print(f"Voice Enabled: {raistlin.enabled}")
        print()

        if not raistlin.enabled:
            print("Voice disabled - showing text output only:")
            print()

        # Test greeting
        print("Testing dynamic greeting...")
        response = await raistlin.greet()
        print(f"Response: {response}")
        print()

        # Test grade announcements
        test_cases = [
            {"grade": 9.8, "title": "Amazing Spider-Man", "confidence": 0.95, "value": 5000},
            {"grade": 8.5, "title": "X-Men", "confidence": 0.88, "value": 200},
            {"grade": 6.0, "title": "Generic Hero", "confidence": 0.82, "value": 15},
            {"grade": 3.5, "title": "Bargain Bin Special", "confidence": 0.75, "value": 2},
        ]

        for case in test_cases:
            print(f"Testing grade {case['grade']} - {case['title']}...")
            response, emotion = await raistlin.announce_grade(**case)
            print(f"Emotion: {emotion.value}")
            print(f"Response: {response}")
            print()

        # Test full summary
        print("Testing full dynamic summary...")
        response, emotion = await raistlin.full_grading_summary(
            title="Amazing Spider-Man",
            issue_number="129",
            grade=9.4,
            confidence=0.92,
            is_key_issue=True,
            defects=["minor spine stress", "light corner wear"],
            value=3500
        )
        print(f"Summary Response: {response}")

        print()
        print("=" * 60)
        print("Test complete!")

    asyncio.run(test_raistlin())
