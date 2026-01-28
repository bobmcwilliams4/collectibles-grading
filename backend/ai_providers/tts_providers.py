"""
MULTI-PROVIDER TTS SYSTEM
Primary: Cartesia (40ms latency, cost-effective)
Fallback: ElevenLabs (higher quality, more expensive)

Authority Level: 11.0
Commander: Bobby Don McWilliams II
"""

import os
import sys
import asyncio
import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

sys.path.insert(0, "P:/SOVEREIGN_APPS/collectibles_grading_system/backend")

logger = logging.getLogger("TTSProviders")

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv("P:/SOVEREIGN_APPS/collectibles_grading_system/backend/.env")
    load_dotenv("P:/SOVEREIGN_APPS/collectibles_grading_system/.env")
except ImportError:
    pass

# Import availability flags
CARTESIA_AVAILABLE = False
ELEVENLABS_AVAILABLE = False
HTTPX_AVAILABLE = False
TOGETHER_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    logger.warning("httpx not installed")

try:
    from cartesia import AsyncCartesia
    CARTESIA_AVAILABLE = True
except ImportError:
    logger.warning("cartesia not installed - pip install cartesia")

try:
    from elevenlabs import ElevenLabs, VoiceSettings
    ELEVENLABS_AVAILABLE = True
except ImportError:
    logger.warning("elevenlabs not installed")


class TTSProvider(Enum):
    """Available TTS providers"""
    CARTESIA = "cartesia"
    ELEVENLABS = "elevenlabs"
    TOGETHER = "together"  # Together.AI Kokoro TTS


@dataclass
class VoiceProfile:
    """Voice profile for a personality across providers"""
    name: str
    # Cartesia voice IDs
    cartesia_voice_id: Optional[str] = None
    # ElevenLabs voice IDs
    elevenlabs_voice_id: Optional[str] = None
    # Together.AI voice name
    together_voice: Optional[str] = None
    # Voice characteristics
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    speed: float = 1.0


# Default voice profiles
VOICE_PROFILES = {
    "bree": VoiceProfile(
        name="Bree",
        cartesia_voice_id="f34c8371-d43c-4895-8032-a31cb0cf218a",  # Cloned from ElevenLabs 2026-01-01
        elevenlabs_voice_id="pzKXffibtCDxnrVO8d1U",
        together_voice="helpful woman",
        stability=0.3,
        similarity_boost=0.8,
        style=0.7,
        speed=1.0
    ),
    "raistlin": VoiceProfile(
        name="Raistlin",
        cartesia_voice_id="694f9389-aac1-45b6-b726-9d9369183238",  # Gandalf-like
        elevenlabs_voice_id="fyX4AP5q3XiIRxqPsZBy",
        together_voice="reflective man",
        stability=0.3,
        similarity_boost=0.75,
        style=0.0,
        speed=0.75
    ),
    "collection_master": VoiceProfile(
        name="CollectionMaster",
        cartesia_voice_id="694f9389-aac1-45b6-b726-9d9369183238",  # Gandalf-like
        elevenlabs_voice_id="fyX4AP5q3XiIRxqPsZBy",
        together_voice="reflective man",
        stability=0.45,
        similarity_boost=0.80,
        style=0.15,
        speed=0.85
    ),
}


class BaseTTSProvider(ABC):
    """Abstract base class for TTS providers"""

    @abstractmethod
    async def generate_audio(
        self,
        text: str,
        voice_profile: VoiceProfile,
        emotion: Optional[str] = None
    ) -> Optional[bytes]:
        """Generate audio bytes from text"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name"""
        pass

    @property
    @abstractmethod
    def latency_ms(self) -> int:
        """Expected latency in milliseconds"""
        pass


class CartesiaTTSProvider(BaseTTSProvider):
    """
    Cartesia TTS Provider - Primary (40ms latency)
    Ultra-fast, cost-effective voice synthesis
    """

    def __init__(self):
        self.client = None
        self.api_key = os.environ.get("CARTESIA_API_KEY")

        if self.api_key and CARTESIA_AVAILABLE:
            try:
                from cartesia import AsyncCartesia
                self.client = AsyncCartesia(api_key=self.api_key)
                logger.info("Cartesia TTS initialized (40ms latency)")
            except Exception as e:
                logger.error(f"Cartesia init failed: {e}")
        else:
            if not self.api_key:
                logger.warning("CARTESIA_API_KEY not found")

    @property
    def name(self) -> str:
        return "Cartesia"

    @property
    def latency_ms(self) -> int:
        return 40  # Sonic Turbo

    def is_available(self) -> bool:
        return self.client is not None

    async def generate_audio(
        self,
        text: str,
        voice_profile: VoiceProfile,
        emotion: Optional[str] = None
    ) -> Optional[bytes]:
        """Generate audio using Cartesia Sonic"""
        if not self.is_available():
            return None

        voice_id = voice_profile.cartesia_voice_id
        if not voice_id:
            logger.warning(f"No Cartesia voice ID for {voice_profile.name}")
            return None

        try:
            # Cartesia API call
            audio_bytes = b""
            async for chunk in self.client.tts.bytes(
                model_id="sonic-3",
                transcript=text,
                voice={"mode": "id", "id": voice_id},
                language="en",
                output_format={
                    "container": "mp3",
                    "sample_rate": 44100,
                    "encoding": "mp3",
                }
            ):
                audio_bytes += chunk

            logger.info(f"Cartesia generated {len(audio_bytes)} bytes")
            return audio_bytes

        except Exception as e:
            logger.error(f"Cartesia TTS failed: {e}")
            return None


class ElevenLabsTTSProvider(BaseTTSProvider):
    """
    ElevenLabs TTS Provider - Fallback (higher quality)
    Premium voices with emotional control
    """

    def __init__(self):
        self.client = None
        self.api_key = os.environ.get("ELEVENLABS_API_KEY")

        if self.api_key and ELEVENLABS_AVAILABLE:
            try:
                self.client = ElevenLabs(api_key=self.api_key)
                logger.info("ElevenLabs TTS initialized (fallback)")
            except Exception as e:
                logger.error(f"ElevenLabs init failed: {e}")
        else:
            if not self.api_key:
                logger.warning("ELEVENLABS_API_KEY not found")

    @property
    def name(self) -> str:
        return "ElevenLabs"

    @property
    def latency_ms(self) -> int:
        return 250

    def is_available(self) -> bool:
        return self.client is not None

    async def generate_audio(
        self,
        text: str,
        voice_profile: VoiceProfile,
        emotion: Optional[str] = None
    ) -> Optional[bytes]:
        """Generate audio using ElevenLabs"""
        if not self.is_available():
            return None

        voice_id = voice_profile.elevenlabs_voice_id
        if not voice_id:
            logger.warning(f"No ElevenLabs voice ID for {voice_profile.name}")
            return None

        try:
            voice_settings = VoiceSettings(
                stability=voice_profile.stability,
                similarity_boost=voice_profile.similarity_boost,
                style=voice_profile.style,
                use_speaker_boost=True
            )

            audio_generator = self.client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id="eleven_multilingual_v2",
                voice_settings=voice_settings
            )

            audio_bytes = b""
            for chunk in audio_generator:
                if chunk:
                    audio_bytes += chunk

            logger.info(f"ElevenLabs generated {len(audio_bytes)} bytes")
            return audio_bytes

        except Exception as e:
            logger.error(f"ElevenLabs TTS failed: {e}")
            return None


class TogetherTTSProvider(BaseTTSProvider):
    """
    Together.AI TTS Provider - Budget option (Kokoro)
    Very low cost, decent quality
    """

    def __init__(self):
        self.api_key = os.environ.get("TOGETHER_API_KEY")
        self._available = self.api_key is not None and HTTPX_AVAILABLE
        if self._available:
            logger.info("Together.AI TTS initialized (budget option)")
        else:
            if not self.api_key:
                logger.warning("TOGETHER_API_KEY not found")

    @property
    def name(self) -> str:
        return "Together.AI"

    @property
    def latency_ms(self) -> int:
        return 150

    def is_available(self) -> bool:
        return self._available

    async def generate_audio(
        self,
        text: str,
        voice_profile: VoiceProfile,
        emotion: Optional[str] = None
    ) -> Optional[bytes]:
        """Generate audio using Together.AI Kokoro"""
        if not self.is_available():
            return None

        voice = voice_profile.together_voice or "helpful woman"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.together.xyz/v1/audio/speech",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "hexgrad/Kokoro-82M",
                        "input": text,
                        "voice": voice
                    }
                )

                if response.status_code == 200:
                    logger.info(f"Together TTS generated {len(response.content)} bytes")
                    return response.content
                else:
                    logger.error(f"Together TTS failed: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Together TTS failed: {e}")
            return None


class MultiProviderTTS:
    """
    Multi-provider TTS system with automatic fallback

    Priority:
    1. Cartesia (40ms, cost-effective) - PRIMARY
    2. Together.AI (150ms, cheapest) - BUDGET
    3. ElevenLabs (250ms, highest quality) - FALLBACK
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path("P:/SOVEREIGN_APPS/collectibles_grading_system/cache/tts")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize providers in priority order
        self.providers: list[BaseTTSProvider] = []

        # Primary: Cartesia
        cartesia = CartesiaTTSProvider()
        if cartesia.is_available():
            self.providers.append(cartesia)

        # Budget: Together.AI
        together = TogetherTTSProvider()
        if together.is_available():
            self.providers.append(together)

        # Fallback: ElevenLabs
        elevenlabs = ElevenLabsTTSProvider()
        if elevenlabs.is_available():
            self.providers.append(elevenlabs)

        logger.info(f"TTS initialized with {len(self.providers)} providers: {[p.name for p in self.providers]}")

    def get_cache_path(self, text: str, voice_name: str, provider_name: str) -> Path:
        """Get cache path for audio"""
        cache_key = hashlib.md5(f"{text}_{voice_name}_{provider_name}".encode()).hexdigest()
        return self.cache_dir / f"{voice_name}_{cache_key[:12]}.mp3"

    async def generate_audio(
        self,
        text: str,
        voice_profile: VoiceProfile,
        emotion: Optional[str] = None,
        prefer_provider: Optional[TTSProvider] = None
    ) -> Tuple[Optional[Path], str]:
        """
        Generate audio with automatic fallback

        Returns:
            Tuple of (audio_path, provider_name) or (None, "")
        """
        if not self.providers:
            logger.error("No TTS providers available!")
            return None, ""

        # Reorder providers if specific one preferred
        providers = self.providers.copy()
        if prefer_provider:
            providers.sort(key=lambda p: 0 if p.name.lower() == prefer_provider.value else 1)

        # Try each provider
        for provider in providers:
            # Check cache first
            cache_path = self.get_cache_path(text, voice_profile.name, provider.name)
            if cache_path.exists():
                logger.info(f"Using cached audio: {cache_path.name}")
                return cache_path, provider.name

            # Generate audio
            audio_bytes = await provider.generate_audio(text, voice_profile, emotion)

            if audio_bytes:
                # Save to cache
                with open(cache_path, "wb") as f:
                    f.write(audio_bytes)
                logger.info(f"Generated via {provider.name}: {cache_path.name}")
                return cache_path, provider.name

            logger.warning(f"{provider.name} failed, trying next provider...")

        logger.error("All TTS providers failed!")
        return None, ""

    def get_voice_profile(self, personality: str) -> Optional[VoiceProfile]:
        """Get voice profile by personality name"""
        return VOICE_PROFILES.get(personality.lower())


# Singleton instance
_tts_instance: Optional[MultiProviderTTS] = None


def get_tts() -> MultiProviderTTS:
    """Get or create TTS singleton"""
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = MultiProviderTTS()
    return _tts_instance


async def speak_with_fallback(
    text: str,
    personality: str = "bree",
    emotion: Optional[str] = None
) -> Tuple[Optional[Path], str]:
    """
    Quick function to generate TTS with automatic fallback

    Returns:
        Tuple of (audio_path, provider_name)
    """
    tts = get_tts()
    voice_profile = tts.get_voice_profile(personality)

    if not voice_profile:
        logger.error(f"Unknown personality: {personality}")
        return None, ""

    return await tts.generate_audio(text, voice_profile, emotion)


__all__ = [
    'MultiProviderTTS',
    'TTSProvider',
    'VoiceProfile',
    'VOICE_PROFILES',
    'get_tts',
    'speak_with_fallback',
    'CARTESIA_AVAILABLE',
    'ELEVENLABS_AVAILABLE',
    'HTTPX_AVAILABLE',
]
