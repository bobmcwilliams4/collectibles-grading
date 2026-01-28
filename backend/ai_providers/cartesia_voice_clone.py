"""
CARTESIA VOICE CLONING UTILITY
Clone existing voices (like Bree from ElevenLabs) to Cartesia

Uses Cartesia's Instant Voice Clone API for fast voice creation
from audio samples.

Authority Level: 11.0
Commander: Bobby Don McWilliams II
"""

import os
import sys
import asyncio
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

sys.path.insert(0, "P:/SOVEREIGN_APPS/collectibles_grading_system/backend")

logger = logging.getLogger("CartesiaVoiceClone")

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv("P:/SOVEREIGN_APPS/collectibles_grading_system/backend/.env")
    load_dotenv("P:/SOVEREIGN_APPS/collectibles_grading_system/.env")
except ImportError:
    pass

HTTPX_AVAILABLE = False
CARTESIA_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    logger.warning("httpx not installed")

try:
    from cartesia import Cartesia
    CARTESIA_AVAILABLE = True
except ImportError:
    logger.warning("cartesia not installed")


class CartesiaVoiceCloner:
    """
    Clone voices to Cartesia using audio samples

    Workflow:
    1. Generate sample audio from ElevenLabs (Bree's voice)
    2. Use Cartesia's voice cloning API to create new voice
    3. Save the new voice ID for use in multi-provider TTS
    """

    CARTESIA_API_URL = "https://api.cartesia.ai"

    def __init__(self):
        self.api_key = os.environ.get("CARTESIA_API_KEY")
        self.samples_dir = Path("P:/SOVEREIGN_APPS/collectibles_grading_system/cache/voice_samples")
        self.samples_dir.mkdir(parents=True, exist_ok=True)
        self.voices_config_path = Path("P:/SOVEREIGN_APPS/collectibles_grading_system/backend/ai_providers/cartesia_voices.json")

        if self.api_key:
            logger.info("Cartesia Voice Cloner initialized")
        else:
            logger.warning("CARTESIA_API_KEY not found")

    def is_available(self) -> bool:
        """Check if cloner is available"""
        return self.api_key is not None and HTTPX_AVAILABLE

    async def generate_elevenlabs_samples(
        self,
        voice_name: str = "bree",
        voice_id: str = "pzKXffibtCDxnrVO8d1U",
        sample_texts: List[str] = None
    ) -> List[Path]:
        """
        Generate voice samples from ElevenLabs for cloning

        Args:
            voice_name: Name for the voice samples
            voice_id: ElevenLabs voice ID
            sample_texts: List of texts to generate samples from

        Returns:
            List of paths to generated audio files
        """
        elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY")
        if not elevenlabs_key:
            logger.error("ELEVENLABS_API_KEY not found - cannot generate samples")
            return []

        if sample_texts is None:
            # Default Bree-style samples with emotional range
            sample_texts = [
                "Holy shit, a 9.8 grade! Now THAT is what I'm talking about. Absolutely gorgeous specimen.",
                "Are you fucking kidding me with this 2.0 garbage? Who stored this in a dumpster?",
                "Alright, an 8.5 isn't bad at all. Could be better, could be a hell of a lot worse.",
                "This comic is absolutely stunning. The colors are pristine, the spine is tight. Beautiful.",
                "What brain-dead moron thought this was worth grading? It's barely holding together!",
            ]

        sample_paths = []

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                for i, text in enumerate(sample_texts):
                    logger.info(f"Generating sample {i+1}/{len(sample_texts)} for {voice_name}...")

                    response = await client.post(
                        "https://api.elevenlabs.io/v1/text-to-speech/" + voice_id,
                        headers={
                            "xi-api-key": elevenlabs_key,
                            "Content-Type": "application/json"
                        },
                        json={
                            "text": text,
                            "model_id": "eleven_multilingual_v2",
                            "voice_settings": {
                                "stability": 0.3,
                                "similarity_boost": 0.8,
                                "style": 0.7
                            }
                        }
                    )

                    if response.status_code == 200:
                        sample_path = self.samples_dir / f"{voice_name}_sample_{i+1}.mp3"
                        with open(sample_path, "wb") as f:
                            f.write(response.content)
                        sample_paths.append(sample_path)
                        logger.info(f"Saved: {sample_path.name}")
                    else:
                        logger.error(f"ElevenLabs error: {response.status_code}")

        except Exception as e:
            logger.error(f"Sample generation failed: {e}")

        return sample_paths

    async def clone_voice_to_cartesia(
        self,
        voice_name: str,
        sample_paths: List[Path],
        description: str = ""
    ) -> Optional[str]:
        """
        Clone a voice to Cartesia using audio samples

        Args:
            voice_name: Name for the new voice
            sample_paths: Paths to audio sample files
            description: Voice description

        Returns:
            New Cartesia voice ID or None
        """
        if not self.api_key:
            logger.error("CARTESIA_API_KEY not found")
            return None

        if not sample_paths:
            logger.error("No sample paths provided")
            return None

        # Find the first valid sample file
        sample_path = None
        for path in sample_paths:
            if path.exists():
                sample_path = path
                break

        if not sample_path:
            logger.error("No valid sample files found")
            return None

        try:
            from cartesia import Cartesia
            client = Cartesia(api_key=self.api_key)

            logger.info(f"Cloning voice from: {sample_path}")

            # Use the official SDK to clone
            voice = client.voices.clone(
                clip=str(sample_path),
                name=voice_name,
                language="en",
                mode="similarity",
                description=description or f"Cloned voice: {voice_name}",
                enhance=True
            )

            voice_id = voice.id
            logger.info(f"Voice cloned successfully! ID: {voice_id}")

            # Save to config
            await self._save_voice_config(voice_name, voice_id, description)

            return voice_id

        except Exception as e:
            logger.error(f"Voice cloning failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def _save_voice_config(self, voice_name: str, voice_id: str, description: str = ""):
        """Save voice configuration to JSON"""
        config = {}
        if self.voices_config_path.exists():
            try:
                config = json.loads(self.voices_config_path.read_text())
            except:
                pass

        config[voice_name.lower()] = {
            "cartesia_voice_id": voice_id,
            "description": description,
            "source": "cloned_from_elevenlabs"
        }

        self.voices_config_path.write_text(json.dumps(config, indent=2))
        logger.info(f"Saved voice config: {self.voices_config_path}")

    async def clone_bree_to_cartesia(self) -> Optional[str]:
        """
        Convenience method to clone Bree's voice from ElevenLabs to Cartesia

        Returns:
            New Cartesia voice ID or None
        """
        logger.info("=" * 50)
        logger.info("CLONING BREE VOICE TO CARTESIA")
        logger.info("=" * 50)

        # Step 1: Generate samples from ElevenLabs
        logger.info("\n[Step 1] Generating ElevenLabs samples...")
        sample_paths = await self.generate_elevenlabs_samples(
            voice_name="bree",
            voice_id="pzKXffibtCDxnrVO8d1U",  # Bree's ElevenLabs voice
        )

        if not sample_paths:
            logger.error("Failed to generate samples")
            return None

        logger.info(f"Generated {len(sample_paths)} samples")

        # Step 2: Clone to Cartesia
        logger.info("\n[Step 2] Cloning to Cartesia...")
        voice_id = await self.clone_voice_to_cartesia(
            voice_name="Bree",
            sample_paths=sample_paths,
            description="Bree - Vulgar but expert comic grader. Expressive, sarcastic, with colorful language."
        )

        if voice_id:
            logger.info("\n" + "=" * 50)
            logger.info(f"SUCCESS! Bree voice cloned to Cartesia")
            logger.info(f"Voice ID: {voice_id}")
            logger.info("=" * 50)

            # Update the tts_providers.py voice profile
            logger.info("\nRemember to update VOICE_PROFILES in tts_providers.py:")
            logger.info(f'    cartesia_voice_id="{voice_id}",')

        return voice_id

    async def list_cartesia_voices(self) -> List[Dict]:
        """List all available Cartesia voices"""
        if not self.is_available():
            return []

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.CARTESIA_API_URL}/voices",
                    headers={
                        "X-API-Key": self.api_key,
                        "Cartesia-Version": "2024-06-01"
                    }
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to list voices: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"List voices failed: {e}")
            return []


# Singleton
_cloner_instance: Optional[CartesiaVoiceCloner] = None


def get_cloner() -> CartesiaVoiceCloner:
    """Get or create cloner singleton"""
    global _cloner_instance
    if _cloner_instance is None:
        _cloner_instance = CartesiaVoiceCloner()
    return _cloner_instance


async def clone_bree() -> Optional[str]:
    """Quick function to clone Bree to Cartesia"""
    cloner = get_cloner()
    return await cloner.clone_bree_to_cartesia()


if __name__ == "__main__":
    async def main():
        print("=" * 60)
        print("CARTESIA VOICE CLONING UTILITY")
        print("=" * 60)
        print()

        cloner = get_cloner()

        if not cloner.is_available():
            print("ERROR: Cartesia cloner not available")
            print("Make sure CARTESIA_API_KEY is set")
            return

        # Clone Bree
        voice_id = await clone_bree()

        if voice_id:
            print(f"\nBree voice cloned successfully!")
            print(f"Voice ID: {voice_id}")
        else:
            print("\nFailed to clone Bree voice")

    asyncio.run(main())
