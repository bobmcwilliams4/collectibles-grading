"""
🧙 COLLECTION MASTER VOICE FEEDBACK SYSTEM
Gandalf-Inspired Wise Collector Personality with Eleven Labs TTS
For Collectibles Grading System - Comic Grading Narration

Authority Level: 11.0
Commander: Bobby Don McWilliams II

COLLECTION MASTER - The Wise Guardian of Collections
Voice characteristics: Gandalf-like, warm but authoritative,
wise counsel mixed with occasional dry wit and wonder.

ALL RESPONSES ARE DYNAMIC - Powered by Claude OAuth
"""

import os
import sys
import asyncio
import logging
import hashlib
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Add paths
sys.path.insert(0, "P:/SOVEREIGN_APPS/collectibles_grading_system/backend")

logger = logging.getLogger("CollectionMaster")

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv("P:/SOVEREIGN_APPS/collectibles_grading_system/backend/.env")
    load_dotenv("P:/SOVEREIGN_APPS/collectibles_grading_system/.env")
except ImportError:
    pass

# Import flags
ELEVENLABS_AVAILABLE = False
HTTPX_AVAILABLE = False

try:
    from elevenlabs import ElevenLabs, VoiceSettings
    ELEVENLABS_AVAILABLE = True
except ImportError:
    logger.warning("elevenlabs not installed")

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    logger.warning("httpx not installed")


class MasterEmotion(Enum):
    """Emotion types for Collection Master"""
    WONDER = "wonder"           # High grades, rare finds
    APPROVAL = "approval"       # Good condition
    THOUGHTFUL = "thoughtful"   # Mid grades, analysis
    CONCERNED = "concerned"     # Defects found
    DISAPPOINTED = "disappointed"  # Low grades
    URGENT = "urgent"           # Key issues, action needed


@dataclass
class MasterVoiceConfig:
    """Voice config - Gandalf-like wise elder"""
    voice_id: str = "fyX4AP5q3XiIRxqPsZBy"  # Gandalf voice
    model_id: str = "eleven_multilingual_v2"
    speed: float = 0.85           # Measured, wise pace
    stability: float = 0.45       # Some variation for naturalness
    similarity_boost: float = 0.80
    style: float = 0.15           # Slight dramatic flair


# Emotion to voice settings mapping
EMOTION_VOICE_SETTINGS = {
    MasterEmotion.WONDER: {"stability": 0.35, "style": 0.25, "speed": 0.90},
    MasterEmotion.APPROVAL: {"stability": 0.50, "style": 0.15, "speed": 0.85},
    MasterEmotion.THOUGHTFUL: {"stability": 0.55, "style": 0.10, "speed": 0.80},
    MasterEmotion.CONCERNED: {"stability": 0.45, "style": 0.20, "speed": 0.82},
    MasterEmotion.DISAPPOINTED: {"stability": 0.50, "style": 0.25, "speed": 0.78},
    MasterEmotion.URGENT: {"stability": 0.30, "style": 0.30, "speed": 0.95},
}


class CollectionMaster:
    """
    The Collection Master - Gandalf-like wise guardian of collectibles.
    Provides grading narration with warmth and wisdom.
    """

    def __init__(self):
        self.config = MasterVoiceConfig()
        self.enabled = False
        self.client = None
        self.cache_dir = Path("P:/SOVEREIGN_APPS/collectibles_grading_system/cache/master_voice")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize ElevenLabs
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if api_key and ELEVENLABS_AVAILABLE:
            try:
                self.client = ElevenLabs(api_key=api_key)
                self.enabled = True
                logger.info("🧙 Collection Master voice system initialized")
            except Exception as e:
                logger.error(f"ElevenLabs init failed: {e}")
        else:
            logger.warning("Collection Master disabled - no API key or library")

    def get_emotion_for_grade(self, grade: float) -> MasterEmotion:
        """Map grade to appropriate emotion"""
        if grade >= 9.6:
            return MasterEmotion.WONDER
        elif grade >= 8.5:
            return MasterEmotion.APPROVAL
        elif grade >= 6.0:
            return MasterEmotion.THOUGHTFUL
        elif grade >= 4.0:
            return MasterEmotion.CONCERNED
        else:
            return MasterEmotion.DISAPPOINTED

    def _get_cache_path(self, text: str, emotion: MasterEmotion) -> Path:
        """Generate cache path for audio"""
        cache_key = hashlib.md5(f"{text}_{emotion.value}".encode()).hexdigest()
        return self.cache_dir / f"master_{cache_key}.mp3"

    async def generate_audio(self, text: str, emotion: MasterEmotion = MasterEmotion.THOUGHTFUL) -> Optional[Path]:
        """Generate TTS audio for text"""
        if not self.enabled or not self.client:
            logger.warning("Collection Master not enabled")
            return None

        # Check cache first
        cache_path = self._get_cache_path(text, emotion)
        if cache_path.exists():
            logger.info(f"🧙 Using cached audio: {cache_path.name}")
            return cache_path

        try:
            # Get emotion-specific settings
            settings = EMOTION_VOICE_SETTINGS.get(emotion, {})
            stability = settings.get("stability", self.config.stability)
            style = settings.get("style", self.config.style)

            voice_settings = VoiceSettings(
                stability=stability,
                similarity_boost=self.config.similarity_boost,
                style=style,
                use_speaker_boost=True
            )

            # Generate audio
            logger.info(f"🧙 Generating voice: {text[:50]}... [{emotion.value}]")
            
            audio_generator = self.client.text_to_speech.convert(
                voice_id=self.config.voice_id,
                model_id=self.config.model_id,
                text=text,
                voice_settings=voice_settings
            )

            # Collect audio bytes
            audio_bytes = b""
            for chunk in audio_generator:
                if chunk:
                    audio_bytes += chunk

            if audio_bytes:
                # Save to cache
                with open(cache_path, "wb") as f:
                    f.write(audio_bytes)
                logger.info(f"🧙 Audio saved: {cache_path.name} ({len(audio_bytes)} bytes)")
                return cache_path
            else:
                logger.error("No audio data received")
                return None

        except Exception as e:
            logger.error(f"🧙 Audio generation failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def generate_grading_commentary(
        self,
        grade: float,
        title: str,
        issue: str,
        defects: list = None,
        is_key_issue: bool = False,
        key_reasons: list = None
    ) -> tuple[str, MasterEmotion]:
        """
        Generate dynamic Gandalf-style commentary using Claude OAuth.
        Returns (commentary_text, emotion)
        """
        emotion = self.get_emotion_for_grade(grade)
        
        # Build context
        defect_text = ", ".join(defects) if defects else "none detected"
        key_text = f"KEY ISSUE: {', '.join(key_reasons)}" if is_key_issue and key_reasons else ""

        # Try Claude OAuth for dynamic response
        if HTTPX_AVAILABLE:
            commentary = await self._generate_claude_commentary(
                grade, title, issue, defect_text, emotion, key_text
            )
            if commentary:
                return commentary, emotion

        # Fallback to templates
        return self._get_template_commentary(grade, title, issue, emotion, is_key_issue), emotion

    async def _generate_claude_commentary(
        self,
        grade: float,
        title: str,
        issue: str,
        defects: str,
        emotion: MasterEmotion,
        key_info: str
    ) -> Optional[str]:
        """Generate dynamic commentary via Claude OAuth"""
        
        # Get OAuth token
        token = None
        token_sources = [
            "P:/SOVEREIGN_APPS/collectibles_grading_system/.claude_oauth_token",
            os.path.expanduser("~/.claude/.credentials.json"),
        ]
        
        for source in token_sources:
            try:
                path = Path(source)
                if path.exists():
                    content = path.read_text().strip()
                    if ".json" in source:
                        import json
                        data = json.loads(content)
                        token = data.get("accessToken") or data.get("token")
                    else:
                        token = content
                    if token:
                        break
            except:
                continue
        
        if not token:
            token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
        
        if not token:
            return None

        prompt = f"""You are the COLLECTION MASTER - a wise, Gandalf-like guardian of collectibles.
Speak with warmth, wisdom, and occasional dry wit. Use measured, thoughtful speech.
Reference the passage of time, preservation, and the stories items carry.

Generate a SHORT (30-50 words) commentary for this grading result:

Comic: {title} #{issue}
Grade: {grade}
Defects: {defects}
{key_info}
Emotion: {emotion.value}

Speak as the Collection Master would - wise, warm, with gravitas.
NO quotation marks. Just the dialogue."""

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01"
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 150,
                        "messages": [{"role": "user", "content": prompt}]
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    text = data.get("content", [{}])[0].get("text", "").strip()
                    text = text.strip('"\'')
                    if text:
                        logger.info(f"🧙 Claude generated: {text[:50]}...")
                        return text
        except Exception as e:
            logger.warning(f"Claude OAuth failed: {e}")
        
        return None

    def _get_template_commentary(
        self,
        grade: float,
        title: str,
        issue: str,
        emotion: MasterEmotion,
        is_key: bool
    ) -> str:
        """Fallback template responses"""
        templates = {
            MasterEmotion.WONDER: [
                f"Remarkable. {title} number {issue} has weathered the ages magnificently. A treasure indeed.",
                f"Ah, what have we here? {title} {issue}, preserved as if by magic itself. Splendid.",
            ],
            MasterEmotion.APPROVAL: [
                f"A worthy specimen. {title} {issue} shows the care of its keeper.",
                f"Good, very good. This {title} has been well-guarded through the years.",
            ],
            MasterEmotion.THOUGHTFUL: [
                f"Hmm. {title} {issue} tells a story of time's passage. Let us examine further.",
                f"This one has seen some adventures. {title} {issue}, still standing.",
            ],
            MasterEmotion.CONCERNED: [
                f"I see the marks of time upon this one. {title} {issue} has endured much.",
                f"This copy has weathered storms, I think. But it survives.",
            ],
            MasterEmotion.DISAPPOINTED: [
                f"Alas. This {title} has not been treated kindly by fate.",
                f"Even the worn and weary have their place. But this one needs care.",
            ],
        }
        
        import random
        options = templates.get(emotion, templates[MasterEmotion.THOUGHTFUL])
        return random.choice(options)


# Singleton instance
_master_instance: Optional[CollectionMaster] = None


def get_collection_master() -> Optional[CollectionMaster]:
    """Get or create Collection Master singleton"""
    global _master_instance
    if _master_instance is None:
        _master_instance = CollectionMaster()
    return _master_instance


def init_collection_master() -> Optional[CollectionMaster]:
    """Initialize and return Collection Master"""
    return get_collection_master()
