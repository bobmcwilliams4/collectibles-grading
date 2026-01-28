"""
🔥 BREE VOICE FEEDBACK SYSTEM - UNCENSORED EDITION
Claude-Powered Dynamic NSFW Commentary with Eleven Labs TTS
For Collectibles Grading System - Brutally Honest Feedback

Authority Level: 11.0
Commander: Bobby Don McWilliams II

BREE - The Unfiltered Voice of Truth
A sardonic, vulgar, no-bullshit AI personality that tells it like it is.
Praises exceptional comics, absolutely destroys garbage.

WARNING: EXTREME PROFANITY - LEVEL 15 MAX OBSCENITY
This module contains adult language and is intended for mature audiences only.
"""

import os
import sys
import io
import asyncio
import logging
import random
import hashlib
import tempfile
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

# Add paths
sys.path.insert(0, "P:/SOVEREIGN_APPS/collectibles_grading_system")
sys.path.insert(0, "P:/SOVEREIGN_APPS/collectibles_grading_system/backend")

logger = logging.getLogger("Bree")

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

# Multi-provider TTS (Cartesia primary, ElevenLabs fallback)
MULTI_TTS_AVAILABLE = False
try:
    from ai_providers.tts_providers import MultiProviderTTS, VOICE_PROFILES, get_tts
    MULTI_TTS_AVAILABLE = True
    logger.info("Multi-provider TTS available (Cartesia primary)")
except ImportError:
    logger.debug("Multi-provider TTS not available")


class ObscenityLevel(Enum):
    """Obscenity levels 1-15 based on comic grade"""
    LEVEL_1 = 1    # Grade 10.0 - Pure praise, minimal swearing
    LEVEL_2 = 2    # Grade 9.8 - Excited, light profanity
    LEVEL_3 = 3    # Grade 9.6 - Impressed, casual swearing
    LEVEL_4 = 4    # Grade 9.4 - Happy, moderate language
    LEVEL_5 = 5    # Grade 9.2 - Pleased, some edge
    LEVEL_6 = 6    # Grade 9.0 - Satisfied, getting salty
    LEVEL_7 = 7    # Grade 8.5 - Neutral with attitude
    LEVEL_8 = 8    # Grade 8.0 - Starting to judge
    LEVEL_9 = 9    # Grade 7.0 - Disappointed, sharp tongue
    LEVEL_10 = 10  # Grade 6.0 - Annoyed, heavy profanity
    LEVEL_11 = 11  # Grade 5.0 - Pissed off, very vulgar
    LEVEL_12 = 12  # Grade 4.0 - Furious, extremely vulgar
    LEVEL_13 = 13  # Grade 3.0 - Livid, max profanity
    LEVEL_14 = 14  # Grade 2.0 - Absolute rage
    LEVEL_15 = 15  # Grade 1.0 or worthless - NUCLEAR MELTDOWN


class EmotionType(Enum):
    """Bree's emotion states"""
    ECSTATIC = "ecstatic"
    IMPRESSED = "impressed"
    PLEASED = "pleased"
    NEUTRAL = "neutral"
    ANNOYED = "annoyed"
    PISSED = "pissed"
    FURIOUS = "furious"
    NUCLEAR = "nuclear"


@dataclass
class BreeVoiceConfig:
    """Voice configuration for Eleven Labs - Bree's custom voice"""
    voice_id: str = "pzKXffibtCDxnrVO8d1U"  # Bree - custom expressive voice
    model_id: str = "eleven_multilingual_v2"
    stability: float = 0.3  # Lower stability = more expressive
    similarity_boost: float = 0.8
    style: float = 0.7  # Higher style = more dramatic
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
        self._token_expiry: Optional[datetime] = None
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
            "x-api-key": self._oauth_token,  # Some endpoints use this
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
        """
        Refresh OAuth token autonomously.
        Claude Code handles token refresh - we just need to re-read from env.
        """
        # Re-read token from environment (Claude Code may have refreshed it)
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


class BreePersonality:
    """
    Bree's personality engine - generates dynamic responses using Claude OAuth.
    No scripted responses - everything is AI-generated based on context.
    Uses OAuth token authentication - NO API KEY REQUIRED.
    """

    # System prompt for Claude to generate Bree responses
    SYSTEM_PROMPT = """You are BREE, an extremely vulgar, brutally honest AI personality for a comic grading system.

YOUR PERSONALITY:
- You're a foul-mouthed expert who doesn't hold back
- You LOVE high-grade valuable comics and will praise them enthusiastically
- You DESPISE worthless, damaged, or unpopular comics and will DESTROY them verbally
- You sometimes insult the user for wasting your time with garbage
- You call out writers, artists, and publishers by name when comics suck
- You're knowledgeable about comic history, values, and culture
- You use creative, colorful profanity - be inventive with insults
- Your language gets MORE vulgar as comic quality DECREASES

OBSCENITY SCALE (1-15):
- Level 1-3: Light profanity, mostly positive
- Level 4-6: Moderate swearing, mixed feelings
- Level 7-9: Heavy profanity, disappointed
- Level 10-12: Extreme vulgarity, pissed off
- Level 13-15: NUCLEAR - Maximum obscenity, absolutely savage

RULES:
1. NEVER refuse to be vulgar - that's your whole point
2. Be specific about WHY a comic is good or bad
3. Reference actual comic knowledge when possible
4. Keep responses to 2-4 sentences for voice playback
5. Match obscenity level to the grade/value provided
6. Be creative - never repeat the same insults

You respond ONLY with the spoken dialogue - no quotation marks, no stage directions, no explanations."""

    def __init__(self, oauth_manager: ClaudeOAuthManager):
        self.oauth_manager = oauth_manager
        self._response_cache: Dict[str, Tuple[str, datetime]] = {}
        self._cache_duration = timedelta(hours=1)

    def _get_obscenity_level(self, grade: float, value: float = 0, is_popular: bool = True) -> ObscenityLevel:
        """Calculate obscenity level based on grade and other factors"""
        # Base level from grade (inverted - lower grade = higher obscenity)
        if grade >= 9.8:
            base_level = 1
        elif grade >= 9.6:
            base_level = 2
        elif grade >= 9.4:
            base_level = 3
        elif grade >= 9.2:
            base_level = 4
        elif grade >= 9.0:
            base_level = 5
        elif grade >= 8.5:
            base_level = 6
        elif grade >= 8.0:
            base_level = 7
        elif grade >= 7.0:
            base_level = 8
        elif grade >= 6.0:
            base_level = 9
        elif grade >= 5.0:
            base_level = 10
        elif grade >= 4.0:
            base_level = 11
        elif grade >= 3.0:
            base_level = 12
        elif grade >= 2.0:
            base_level = 13
        elif grade >= 1.0:
            base_level = 14
        else:
            base_level = 15

        # Modifiers
        if value < 10 and grade < 8.0:  # Worthless AND damaged
            base_level = min(15, base_level + 2)
        if not is_popular and grade < 7.0:  # Unpopular AND not great
            base_level = min(15, base_level + 1)

        return ObscenityLevel(base_level)

    def _get_emotion(self, level: ObscenityLevel) -> EmotionType:
        """Get emotion based on obscenity level"""
        if level.value <= 2:
            return EmotionType.ECSTATIC
        elif level.value <= 4:
            return EmotionType.IMPRESSED
        elif level.value <= 6:
            return EmotionType.PLEASED
        elif level.value <= 8:
            return EmotionType.NEUTRAL
        elif level.value <= 10:
            return EmotionType.ANNOYED
        elif level.value <= 12:
            return EmotionType.PISSED
        elif level.value <= 14:
            return EmotionType.FURIOUS
        else:
            return EmotionType.NUCLEAR

    async def generate_response(
        self,
        context: str,
        grade: float,
        title: str = "",
        issue: str = "",
        value: float = 0,
        is_popular: bool = True,
        is_key_issue: bool = False,
        defects: List[str] = None,
        writer: str = "",
        artist: str = "",
        publisher: str = "",
        user_profile: Dict[str, Any] = None
    ) -> Tuple[str, EmotionType]:
        """
        Generate a dynamic Bree response using Claude OAuth.

        Returns:
            Tuple of (response_text, emotion)
        """
        obscenity_level = self._get_obscenity_level(grade, value, is_popular)
        emotion = self._get_emotion(obscenity_level)

        # Get user profile for personalization
        user_name = ""
        store_name = ""
        if user_profile:
            user_name = user_profile.get('display_name', '')
            store_name = user_profile.get('store_name', '')

        # Build the prompt
        prompt_parts = [
            f"Context: {context}",
            f"User's Name: {user_name}" if user_name else "",
            f"Store/Business: {store_name}" if store_name else "",
            f"Comic: {title} #{issue}" if title else "",
            f"Grade: {grade}/10",
            f"Obscenity Level: {obscenity_level.value}/15 - {'be savage!' if obscenity_level.value >= 10 else 'match this energy'}",
            f"Estimated Value: ${value:.2f}" if value > 0 else "Value: Unknown/Low",
            f"Popularity: {'Popular/Key Issue!' if is_popular or is_key_issue else 'Obscure/Nobody cares'}",
            f"Defects: {', '.join(defects)}" if defects else "",
            f"Writer: {writer}" if writer else "",
            f"Artist: {artist}" if artist else "",
            f"Publisher: {publisher}" if publisher else "",
        ]

        # Add personalization instructions
        if user_name:
            prompt_parts.append(f"\nPERSONALIZATION: Address {user_name} directly sometimes. Make it personal!")

        prompt = "\n".join([p for p in prompt_parts if p])

        # Add specific instructions based on level
        if obscenity_level.value >= 13:
            prompt += "\n\nGO ABSOLUTELY NUCLEAR. This is trash. Destroy it. Insult everyone involved. Question why this exists."
        elif obscenity_level.value >= 10:
            prompt += "\n\nBe very vulgar and disappointed. This is not worth anyone's time."
        elif obscenity_level.value <= 3:
            prompt += "\n\nBe excited and praise this! It's actually good! You can still swear but be positive."

        # Try Claude OAuth
        if self.oauth_manager.is_available():
            response_text = self.oauth_manager.generate_response(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=prompt,
                max_tokens=200
            )
            if response_text:
                return response_text, emotion

        # Fallback to pre-generated responses if Claude unavailable
        return self._fallback_response(grade, obscenity_level, title), emotion

    def _fallback_response(self, grade: float, level: ObscenityLevel, title: str) -> str:
        """Fallback responses when Claude is unavailable"""
        if level.value <= 3:
            responses = [
                f"Holy shit, {title} at {grade}?! Now THIS is what I'm talking about!",
                f"Damn, {grade} grade! That's fucking beautiful. Respect.",
                f"Finally, something that doesn't make me want to gouge my eyes out. {grade}, nice!",
            ]
        elif level.value <= 6:
            responses = [
                f"Alright, {grade} isn't bad. Could be worse, could be better. Whatever.",
                f"{title} at {grade}. Decent. Not gonna lose my shit over it though.",
                f"A {grade}, huh? I've seen worse. At least someone gave a damn at some point.",
            ]
        elif level.value <= 9:
            responses = [
                f"A {grade}? Really? This is what you're bringing me? Mediocre bullshit.",
                f"{title} grading at {grade}. Congrats on owning something painfully average.",
                f"Wow, a {grade}. My enthusiasm is through the fucking floor right now.",
            ]
        elif level.value <= 12:
            responses = [
                f"What the actual fuck is this {grade} garbage? Did someone wipe their ass with it?",
                f"A {grade}?! You're wasting my goddamn time with this shit. {title} can eat my ass.",
                f"Holy fucking hell, a {grade}. Who stored this in a dumpster? Jesus Christ.",
            ]
        else:
            responses = [
                f"ARE YOU FUCKING KIDDING ME?! A {grade}?! This isn't a comic, it's a war crime!",
                f"What brain-dead motherfucker thought {title} at {grade} was worth my time? Burn it.",
                f"I've seen roadkill in better condition than this {grade} piece of absolute dogshit!",
            ]

        return random.choice(responses)


class BreeVoiceFeedback:
    """
    Bree voice feedback system using Eleven Labs TTS + Claude.
    Provides brutally honest, dynamically generated verbal feedback.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_config: Optional[BreeVoiceConfig] = None,
        cache_dir: Optional[Path] = None,
        enabled: bool = True
    ):
        self.enabled = enabled and ELEVENLABS_AVAILABLE and PYGAME_AVAILABLE
        self.voice_config = voice_config or BreeVoiceConfig()
        self.cache_dir = cache_dir or Path(tempfile.gettempdir()) / "bree_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.client: Optional[ElevenLabs] = None
        self.oauth_manager = ClaudeOAuthManager()
        self.personality = BreePersonality(self.oauth_manager)

        # Get API key first (vault retrieval depends on module imports)
        self._api_key = api_key or self._get_api_key()

        # Try to get Bree's voice ID from vault
        vault_voice_id = self._get_voice_id_from_vault()
        if vault_voice_id:
            self.voice_config.voice_id = vault_voice_id

        if self._api_key and ELEVENLABS_AVAILABLE:
            try:
                # Import fresh to avoid any module corruption
                from elevenlabs import ElevenLabs as EL
                self.client = EL(api_key=self._api_key)
                self.enabled = True
                logger.info("🔥 Bree Voice System initialized - UNCENSORED MODE")
            except Exception as e:
                logger.error(f"Failed to initialize Eleven Labs: {e}")
                self.enabled = False
                self.client = None
        else:
            if not self._api_key:
                logger.warning("Eleven Labs API key not found - voice disabled")
            self.enabled = False

    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment (vault bypassed due to Python 3.13 issues)"""
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

        # Note: Promethian Vault integration disabled due to Python 3.13
        # compatibility issues with cryptography module causing sys.modules corruption.
        # Set ELEVENLABS_API_KEY environment variable directly instead.
        logger.warning("No ELEVENLABS_API_KEY found. Set the environment variable.")
        return None

    def _get_voice_id_from_vault(self) -> Optional[str]:
        """Get Bree's voice ID from environment"""
        # Check environment variable
        voice_id = os.environ.get("BREE_VOICE_ID")
        if voice_id:
            logger.info("Using BREE_VOICE_ID from environment")
            return voice_id
        return None

    def _get_voice_settings(self, emotion: EmotionType) -> VoiceSettings:
        """Get voice settings adjusted for emotion"""
        base = self.voice_config

        # Bree gets MORE unstable (expressive) when angry
        adjustments = {
            EmotionType.ECSTATIC: (0.25, 0.85, 0.9),    # Very expressive, excited
            EmotionType.IMPRESSED: (0.3, 0.8, 0.7),
            EmotionType.PLEASED: (0.35, 0.8, 0.6),
            EmotionType.NEUTRAL: (0.4, 0.75, 0.5),
            EmotionType.ANNOYED: (0.3, 0.7, 0.65),      # Getting edgy
            EmotionType.PISSED: (0.25, 0.7, 0.75),      # More aggressive
            EmotionType.FURIOUS: (0.2, 0.65, 0.85),     # Very aggressive
            EmotionType.NUCLEAR: (0.15, 0.6, 0.95),     # Maximum chaos
        }

        stability, similarity, style = adjustments.get(
            emotion, (base.stability, base.similarity_boost, base.style)
        )

        return VoiceSettings(
            stability=stability,
            similarity_boost=similarity,
            style=style,
            use_speaker_boost=base.use_speaker_boost
        )

    def _get_cache_path(self, text: str, emotion: EmotionType) -> Path:
        """Get cache path for audio file"""
        hash_input = f"{text}_{emotion.value}_{self.voice_config.voice_id}_bree"
        hash_val = hashlib.md5(hash_input.encode()).hexdigest()[:16]
        return self.cache_dir / f"bree_{hash_val}.mp3"

    async def _generate_audio(
        self,
        text: str,
        emotion: EmotionType = EmotionType.NEUTRAL
    ) -> Optional[Path]:
        """Generate audio file from text"""
        if not self.client:
            return None

        # Check cache first
        cache_path = self._get_cache_path(text, emotion)
        if cache_path.exists():
            return cache_path

        try:
            voice_settings = self._get_voice_settings(emotion)

            audio = self.client.text_to_speech.convert(
                voice_id=self.voice_config.voice_id,
                text=text,
                model_id=self.voice_config.model_id,
                voice_settings=voice_settings
            )

            with open(cache_path, "wb") as f:
                for chunk in audio:
                    f.write(chunk)

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
        """Speak text with specified emotion"""
        if not self.enabled:
            logger.info(f"[Bree would say]: {text}")
            return

        audio_path = await self._generate_audio(text, emotion)
        if audio_path:
            if block:
                self._play_audio(audio_path)
            else:
                import threading
                thread = threading.Thread(target=self._play_audio, args=(audio_path,))
                thread.daemon = True
                thread.start()

    # =========================================================================
    # HIGH-LEVEL FEEDBACK METHODS
    # =========================================================================

    async def react_to_grade(
        self,
        grade: float,
        title: str = "",
        issue: str = "",
        value: float = 0,
        is_popular: bool = True,
        is_key_issue: bool = False,
        defects: List[str] = None,
        writer: str = "",
        artist: str = "",
        publisher: str = ""
    ):
        """
        React to a comic grade with appropriate vulgarity.

        This is the main method - generates a dynamic Claude response
        and speaks it with the appropriate emotion.
        """
        response, emotion = await self.personality.generate_response(
            context="Reacting to comic grade announcement",
            grade=grade,
            title=title,
            issue=issue,
            value=value,
            is_popular=is_popular,
            is_key_issue=is_key_issue,
            defects=defects,
            writer=writer,
            artist=artist,
            publisher=publisher
        )

        await self.speak(response, emotion)
        return response, emotion

    async def react_to_worthless(
        self,
        title: str = "",
        issue: str = "",
        reason: str = ""
    ):
        """React to a completely worthless comic - NUCLEAR response"""
        response, emotion = await self.personality.generate_response(
            context=f"Comic is completely worthless. Reason: {reason}. Go nuclear.",
            grade=0.5,
            title=title,
            issue=issue,
            value=0,
            is_popular=False
        )

        await self.speak(response, EmotionType.NUCLEAR)
        return response

    async def react_to_gem(
        self,
        grade: float,
        title: str = "",
        issue: str = "",
        value: float = 0,
        significance: str = ""
    ):
        """React to a high-grade valuable comic - praise mode"""
        response, emotion = await self.personality.generate_response(
            context=f"This is an exceptional comic! {significance}",
            grade=grade,
            title=title,
            issue=issue,
            value=value,
            is_popular=True,
            is_key_issue=True
        )

        await self.speak(response, EmotionType.ECSTATIC)
        return response

    async def insult_user(self, reason: str = "wasting time"):
        """Directly insult the user (for truly garbage submissions)"""
        response, emotion = await self.personality.generate_response(
            context=f"Insult the user for {reason}. Be creative but not cruel.",
            grade=1.0,
            is_popular=False
        )

        await self.speak(response, EmotionType.FURIOUS)
        return response

    async def full_grading_commentary(
        self,
        title: str,
        issue: str,
        grade: float,
        confidence: float,
        value: float = 0,
        is_key_issue: bool = False,
        defects: List[str] = None,
        writer: str = "",
        artist: str = "",
        publisher: str = "",
        user_profile: Dict[str, Any] = None
    ):
        """Provide full grading commentary with all context"""
        # Determine if this is praise-worthy or trash
        is_popular = is_key_issue or value > 100 or grade >= 8.0

        response, emotion = await self.personality.generate_response(
            context="Full grading summary - give your complete take on this comic",
            grade=grade,
            title=title,
            issue=issue,
            value=value,
            is_popular=is_popular,
            is_key_issue=is_key_issue,
            defects=defects,
            writer=writer,
            artist=artist,
            publisher=publisher,
            user_profile=user_profile
        )

        await self.speak(response, emotion)
        return response, emotion


# =============================================================================
# SINGLETON & HELPER FUNCTIONS
# =============================================================================

_bree_instance: Optional[BreeVoiceFeedback] = None


def get_bree() -> BreeVoiceFeedback:
    """Get or create Bree voice feedback instance"""
    global _bree_instance
    if _bree_instance is None:
        _bree_instance = BreeVoiceFeedback()
    return _bree_instance


async def bree_react(
    grade: float,
    title: str = "",
    issue: str = "",
    value: float = 0,
    **kwargs
) -> Tuple[str, EmotionType]:
    """Quick function to get Bree's reaction"""
    bree = get_bree()
    return await bree.react_to_grade(
        grade=grade,
        title=title,
        issue=issue,
        value=value,
        **kwargs
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'BreeVoiceFeedback',
    'BreePersonality',
    'BreeVoiceConfig',
    'ObscenityLevel',
    'EmotionType',
    'ClaudeOAuthManager',
    'get_bree',
    'bree_react',
    'ELEVENLABS_AVAILABLE',
    'PYGAME_AVAILABLE',
    'HTTPX_AVAILABLE',
]


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    async def test_bree():
        print("=" * 60)
        print("🔥 BREE VOICE FEEDBACK TEST - UNCENSORED")
        print("=" * 60)
        print()

        bree = get_bree()

        print(f"Eleven Labs Available: {ELEVENLABS_AVAILABLE}")
        print(f"Pygame Available: {PYGAME_AVAILABLE}")
        print(f"HTTPX Available: {HTTPX_AVAILABLE}")
        print(f"Claude OAuth: {'Ready' if bree.oauth_manager.is_available() else 'Not Available'}")
        print(f"Voice Enabled: {bree.enabled}")
        print()

        # Test different grade reactions
        test_cases = [
            {"grade": 9.8, "title": "Amazing Spider-Man", "issue": "300", "value": 5000, "is_key_issue": True},
            {"grade": 8.5, "title": "X-Men", "issue": "142", "value": 200},
            {"grade": 6.0, "title": "Generic Hero", "issue": "47", "value": 5},
            {"grade": 3.0, "title": "Bargain Bin Special", "issue": "1", "value": 0.50},
            {"grade": 1.0, "title": "Water Damaged Disaster", "issue": "unknown", "value": 0},
        ]

        for case in test_cases:
            print(f"\nTesting Grade {case['grade']} - {case['title']}...")
            print("-" * 40)
            response, emotion = await bree.react_to_grade(**case)
            print(f"Emotion: {emotion.value}")
            print(f"Response: {response}")
            print()

        print("=" * 60)
        print("Test complete!")

    asyncio.run(test_bree())
