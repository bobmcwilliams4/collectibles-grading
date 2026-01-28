"""
Promethian Vault Integration
Secure API key retrieval from the Prometheus Prime Vault system

NOTE: Vault is DISABLED on Python 3.13+ due to sys.modules corruption from
the GS343 Gateway/PROMETHEUS_PRIME cryptography initialization.
"""

import os
import sys
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)

# VAULT PERMANENTLY DISABLED - The PROMETHEUS_PRIME vault_addon imports gs343_gateway
# which imports universal_enhancements which imports phoenix_auto_heal.py.
# The phoenix_auto_heal._optimize_memory() calls sys.modules.clear() which corrupts
# Python's import system and breaks builtins.open.
_VAULT_DISABLED = True  # ALWAYS DISABLED - See comment above
if _VAULT_DISABLED:
    logger.warning("Vault DISABLED - using environment variables only")

# Vault configuration
VAULT_PATH = r"X:\ECHO_PRIME\PROMETHEUS_PRIME\.promethian_vault"
VAULT_ENV_PATH = r"X:\ECHO_PRIME\PROMETHEUS_PRIME\.env"
PROMETHEUS_PRIME_PATH = r"X:\ECHO_PRIME\PROMETHEUS_PRIME"


class VaultIntegration:
    """
    Promethian Vault Integration for Collectibles Grading System

    Provides secure retrieval of API keys from the Pentagon-level encrypted vault.

    Features:
    - Automatic vault initialization
    - Key caching for performance
    - Fallback to environment variables
    - Error handling and logging
    - Batch key retrieval
    """

    # API key mappings: our config key -> vault secret name
    KEY_MAPPINGS = {
        # AI Providers
        'ANTHROPIC_API_KEY': 'ANTHROPIC_API_KEY_api_key',
        'GOOGLE_API_KEY': 'GOOGLE_API_KEY_api_key',
        'GEMINI_API_KEY': 'GEMINI_API_KEY_api_key',
        'OPENAI_API_KEY': 'OPENAI_API_KEY_api_key',
        'OPENROUTER_API_KEY': 'OPENROUTER_API_KEY_api_key',
        'HUGGINGFACE_API_KEY': 'HUGGINGFACE_API_KEY_api_key',
        'GROQ_API_KEY': 'GROQ_API_KEY_api_key',

        # Pricing Sources
        'GOCOLLECT_API_KEY': 'GOCOLLECT_API_KEY_api_key',
        'HERITAGE_API_KEY': 'HERITAGE_API_KEY_api_key',
        'EBAY_API_KEY': 'EBAY_API_KEY_api_key',
        'EBAY_CLIENT_ID': 'EBAY_CLIENT_ID_api_key',
        'EBAY_CLIENT_SECRET': 'EBAY_CLIENT_SECRET_api_key',

        # Additional Services
        'GITHUB_PAT': 'GITHUB_PAT_api_key',
        'ELEVENLABS_API_KEY': 'ELEVENLABS_API_KEY_api_key',
    }

    # Honeypot traps - NEVER access these
    HONEYPOTS = [
        'admin_password',
        'root_key',
        'master_secret',
        'production_api_key'
    ]

    def __init__(
        self,
        vault_path: str = VAULT_PATH,
        env_path: str = VAULT_ENV_PATH,
        auto_init: bool = True
    ):
        self.vault_path = Path(vault_path)
        self.env_path = Path(env_path)
        self.vault = None
        self._key_cache: Dict[str, str] = {}
        self._initialized = False

        # CRITICAL: Skip vault init entirely if disabled
        # This prevents GS343/PROMETHEUS imports that corrupt sys.modules
        if _VAULT_DISABLED:
            logger.info("Vault DISABLED - skipping initialization, using env vars only")
            return
            
        if auto_init:
            self._initialize_vault()

    def _initialize_vault(self) -> bool:
        """Initialize connection to Promethian Vault"""
        # Python 3.13+ compatibility: SKIP vault initialization entirely
        # The GS343 Gateway/PROMETHEUS_PRIME cryptography causes sys.modules corruption
        if _VAULT_DISABLED:
            logger.info("Vault initialization SKIPPED on Python 3.13+ - using env vars only")
            return False

        try:
            # Add Prometheus Prime to path
            if PROMETHEUS_PRIME_PATH not in sys.path:
                sys.path.insert(0, PROMETHEUS_PRIME_PATH)

            # Load master password from .env
            from dotenv import load_dotenv
            load_dotenv(str(self.env_path))

            master_password = os.getenv("VAULT_MASTER_PASSWORD")
            if not master_password:
                logger.warning("VAULT_MASTER_PASSWORD not found in environment")
                return False

            # Import and initialize vault
            from vault_addon import PromethianVault

            self.vault = PromethianVault(
                vault_path=str(self.vault_path),
                master_password=master_password
            )

            # Check vault status
            status = self.vault.status()
            if status.get('status') == 'LOCKED':
                logger.error("Vault is LOCKED - cannot retrieve keys")
                return False

            self._initialized = True
            logger.info(f"Promethian Vault initialized - {status.get('total_secrets', 0)} secrets available")
            return True

        except ImportError as e:
            logger.warning(f"Vault module not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize vault: {e}")
            return False

    def is_available(self) -> bool:
        """Check if vault is available and initialized"""
        return self._initialized and self.vault is not None

    def get_key(self, key_name: str, use_cache: bool = True) -> Optional[str]:
        """
        Retrieve an API key from the vault

        Args:
            key_name: The key name (e.g., 'ANTHROPIC_API_KEY')
            use_cache: Whether to use cached values

        Returns:
            The API key value or None if not found
        """
        # Check if this is a honeypot
        if key_name.lower() in [h.lower() for h in self.HONEYPOTS]:
            logger.warning(f"Attempted access to honeypot key: {key_name}")
            return None

        # Check cache first
        if use_cache and key_name in self._key_cache:
            return self._key_cache[key_name]

        # Get vault secret name
        vault_key = self.KEY_MAPPINGS.get(key_name, f"{key_name}_api_key")

        # Try vault first
        if self.is_available():
            try:
                result = self.vault.retrieve(vault_key)
                if result.get('success'):
                    value = result['secret_value']
                    self._key_cache[key_name] = value
                    logger.debug(f"Retrieved {key_name} from vault")
                    return value
                else:
                    logger.debug(f"Key {key_name} not found in vault: {result.get('error')}")
            except Exception as e:
                logger.warning(f"Vault retrieval error for {key_name}: {e}")

        # Fallback to environment variable
        env_value = os.environ.get(key_name)
        if env_value:
            logger.debug(f"Using {key_name} from environment")
            self._key_cache[key_name] = env_value
            return env_value

        logger.warning(f"Key {key_name} not found in vault or environment")
        return None

    def get_keys(self, key_names: List[str]) -> Dict[str, Optional[str]]:
        """
        Retrieve multiple API keys at once

        Args:
            key_names: List of key names to retrieve

        Returns:
            Dictionary of key_name -> value (or None if not found)
        """
        result = {}
        for key_name in key_names:
            result[key_name] = self.get_key(key_name)
        return result

    def load_all_ai_keys(self) -> Dict[str, Optional[str]]:
        """Load all AI provider API keys"""
        ai_keys = [
            'ANTHROPIC_API_KEY',
            'GOOGLE_API_KEY',
            'OPENAI_API_KEY',
            'OPENROUTER_API_KEY',
            'HUGGINGFACE_API_KEY',
            'GROQ_API_KEY'
        ]
        return self.get_keys(ai_keys)

    def load_all_pricing_keys(self) -> Dict[str, Optional[str]]:
        """Load all pricing source API keys"""
        pricing_keys = [
            'GOCOLLECT_API_KEY',
            'HERITAGE_API_KEY',
            'EBAY_API_KEY',
            'EBAY_CLIENT_ID',
            'EBAY_CLIENT_SECRET'
        ]
        return self.get_keys(pricing_keys)

    def load_to_environment(self, key_names: List[str] = None) -> int:
        """
        Load keys from vault into environment variables

        Args:
            key_names: Specific keys to load, or None for all mapped keys

        Returns:
            Number of keys successfully loaded
        """
        if key_names is None:
            key_names = list(self.KEY_MAPPINGS.keys())

        loaded = 0
        for key_name in key_names:
            value = self.get_key(key_name)
            if value:
                os.environ[key_name] = value
                loaded += 1

        logger.info(f"Loaded {loaded}/{len(key_names)} keys to environment")
        return loaded

    def get_vault_status(self) -> Dict[str, Any]:
        """Get current vault status"""
        if not self.is_available():
            return {
                'available': False,
                'status': 'NOT_INITIALIZED',
                'error': 'Vault not initialized'
            }

        try:
            status = self.vault.status()
            return {
                'available': True,
                'status': status.get('status', 'UNKNOWN'),
                'total_secrets': status.get('total_secrets', 0),
                'vault_path': str(self.vault_path),
                'cached_keys': len(self._key_cache)
            }
        except Exception as e:
            return {
                'available': False,
                'status': 'ERROR',
                'error': str(e)
            }

    def list_available_keys(self) -> List[str]:
        """List all available key names in the vault"""
        if not self.is_available():
            return []

        try:
            result = self.vault.list()
            if result.get('success'):
                return [s['secret_name'] for s in result.get('secrets', [])]
            return []
        except Exception as e:
            logger.error(f"Failed to list vault keys: {e}")
            return []

    def search_keys(self, pattern: str) -> List[str]:
        """Search for keys matching a pattern"""
        all_keys = self.list_available_keys()
        pattern_lower = pattern.lower()
        return [k for k in all_keys if pattern_lower in k.lower()]

    def clear_cache(self):
        """Clear the key cache"""
        self._key_cache.clear()
        logger.debug("Key cache cleared")

    def store_key(
        self,
        service: str,
        api_key: str,
        tags: List[str] = None
    ) -> bool:
        """
        Store a new API key in the vault

        Args:
            service: Service name (e.g., 'NEW_SERVICE')
            api_key: The API key value
            tags: Optional tags for the key

        Returns:
            True if successful
        """
        if not self.is_available():
            logger.error("Cannot store key - vault not available")
            return False

        try:
            result = self.vault.store_api_key(
                service=service,
                api_key=api_key,
                tags=tags or []
            )
            if result.get('success'):
                logger.info(f"Stored API key for {service}")
                # Update mapping
                self.KEY_MAPPINGS[f"{service}_API_KEY"] = f"{service}_API_KEY_api_key"
                return True
            else:
                logger.error(f"Failed to store key: {result.get('error')}")
                return False
        except Exception as e:
            logger.error(f"Error storing key: {e}")
            return False


# Global vault instance
_vault_instance: Optional[VaultIntegration] = None


def get_vault() -> VaultIntegration:
    """Get or create the global vault instance"""
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = VaultIntegration()
    return _vault_instance


def get_api_key(key_name: str) -> Optional[str]:
    """Convenience function to get an API key"""
    return get_vault().get_key(key_name)


def load_keys_to_env() -> int:
    """Load all API keys to environment variables"""
    return get_vault().load_to_environment()


# Auto-initialize helper for imports
def initialize_vault() -> bool:
    """Initialize vault and return status"""
    vault = get_vault()
    return vault.is_available()
