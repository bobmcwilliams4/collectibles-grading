"""
Configuration Loader with Promethian Vault Integration
Automatically loads API keys from the secure vault into configuration
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Load .env file at module import time (before any os.environ lookups)
try:
    from dotenv import load_dotenv
    # Load from backend directory .env (override system env vars)
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)
except ImportError:
    pass  # dotenv not installed, rely on environment variables

logger = logging.getLogger(__name__)

# Configuration paths
CONFIG_DIR = Path("P:/SOVEREIGN_APPS/collectibles_grading_system/config")
AI_CONFIG_PATH = CONFIG_DIR / "ai_config.json"
CAMERA_CONFIG_PATH = CONFIG_DIR / "camera_config.json"
GRADING_STANDARDS_PATH = CONFIG_DIR / "grading_standards.json"


@dataclass
class AIProviderConfig:
    """Configuration for an AI provider"""
    api_key: str
    model: str
    max_tokens: int
    temperature: float
    enabled: bool
    weight: float
    timeout_seconds: int


@dataclass
class PricingSourceConfig:
    """Configuration for a pricing source"""
    api_key: str
    enabled: bool
    client_id: Optional[str] = None
    client_secret: Optional[str] = None


class ConfigLoader:
    """
    Configuration Loader with Vault Integration

    Features:
    - Loads configuration from JSON files
    - Automatically retrieves API keys from Promethian Vault
    - Falls back to environment variables if vault unavailable
    - Provides type-safe configuration objects
    - Caches configuration for performance
    """

    def __init__(self, use_vault: bool = True):
        self.use_vault = use_vault
        self._vault = None
        self._ai_config: Optional[Dict] = None
        self._camera_config: Optional[Dict] = None
        self._grading_standards: Optional[Dict] = None

        if use_vault:
            self._init_vault()

    def _init_vault(self):
        """Initialize vault connection"""
        try:
            from .vault_integration import get_vault
            self._vault = get_vault()
            if self._vault.is_available():
                logger.info("Promethian Vault connected for configuration")
            else:
                logger.warning("Promethian Vault not available, using fallback")
        except Exception as e:
            logger.warning(f"Could not initialize vault: {e}")
            self._vault = None

    def _get_api_key(self, key_name: str) -> Optional[str]:
        """Get API key from vault or environment"""
        # Try vault first
        if self._vault and self._vault.is_available():
            key = self._vault.get_key(key_name)
            if key:
                return key

        # Fallback to environment
        return os.environ.get(key_name)

    def load_ai_config(self, reload: bool = False) -> Dict[str, Any]:
        """
        Load AI provider configuration with vault-sourced API keys

        Args:
            reload: Force reload from file

        Returns:
            Complete AI configuration dictionary
        """
        if self._ai_config and not reload:
            return self._ai_config

        # Load base config from file
        try:
            with open(AI_CONFIG_PATH, 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            logger.error(f"AI config not found at {AI_CONFIG_PATH}")
            config = {}

        # Inject API keys from vault
        key_mappings = {
            'anthropic': 'ANTHROPIC_API_KEY',
            'google': 'GOOGLE_API_KEY',
            'openrouter': 'OPENROUTER_API_KEY',
            'huggingface': 'HUGGINGFACE_API_KEY',
            'gocollect': 'GOCOLLECT_API_KEY',
            'heritage': 'HERITAGE_API_KEY',
        }

        for provider, key_name in key_mappings.items():
            if provider in config:
                api_key = self._get_api_key(key_name)
                if api_key:
                    config[provider]['api_key'] = api_key
                    logger.debug(f"Loaded {key_name} from vault")

        # Handle eBay special case (multiple keys)
        if 'ebay' in config:
            config['ebay']['client_id'] = self._get_api_key('EBAY_CLIENT_ID') or config['ebay'].get('client_id', '')
            config['ebay']['client_secret'] = self._get_api_key('EBAY_CLIENT_SECRET') or config['ebay'].get('client_secret', '')
            config['ebay']['api_token'] = self._get_api_key('EBAY_API_KEY') or config['ebay'].get('api_token', '')

        self._ai_config = config
        return config

    def load_camera_config(self, reload: bool = False) -> Dict[str, Any]:
        """Load camera configuration"""
        if self._camera_config and not reload:
            return self._camera_config

        try:
            with open(CAMERA_CONFIG_PATH, 'r') as f:
                self._camera_config = json.load(f)
        except FileNotFoundError:
            logger.error(f"Camera config not found at {CAMERA_CONFIG_PATH}")
            self._camera_config = self._default_camera_config()

        return self._camera_config

    def load_grading_standards(self, reload: bool = False) -> Dict[str, Any]:
        """Load CGC grading standards"""
        if self._grading_standards and not reload:
            return self._grading_standards

        try:
            with open(GRADING_STANDARDS_PATH, 'r') as f:
                self._grading_standards = json.load(f)
        except FileNotFoundError:
            logger.error(f"Grading standards not found at {GRADING_STANDARDS_PATH}")
            self._grading_standards = {}

        return self._grading_standards

    def get_provider_config(self, provider: str) -> Optional[AIProviderConfig]:
        """Get typed configuration for a specific AI provider"""
        config = self.load_ai_config()

        if provider not in config:
            return None

        p = config[provider]
        return AIProviderConfig(
            api_key=p.get('api_key', ''),
            model=p.get('model', ''),
            max_tokens=p.get('max_tokens', 1024),
            temperature=p.get('temperature', 0.1),
            enabled=p.get('enabled', False),
            weight=p.get('weight', 0.0),
            timeout_seconds=p.get('timeout_seconds', 30)
        )

    def get_pricing_config(self, source: str) -> Optional[PricingSourceConfig]:
        """Get configuration for a pricing source"""
        config = self.load_ai_config()

        if source not in config:
            return None

        s = config[source]

        if source == 'ebay':
            return PricingSourceConfig(
                api_key=s.get('api_token', ''),
                enabled=s.get('enabled', False),
                client_id=s.get('client_id'),
                client_secret=s.get('client_secret')
            )

        return PricingSourceConfig(
            api_key=s.get('api_key', ''),
            enabled=s.get('enabled', False)
        )

    def get_consensus_config(self) -> Dict[str, Any]:
        """Get consensus algorithm configuration"""
        config = self.load_ai_config()
        return config.get('consensus', {
            'min_providers': 3,
            'agreement_threshold': 0.85,
            'confidence_threshold': 0.80,
            'defect_confirmation_count': 2,
            'front_weight': 0.70,
            'back_weight': 0.30
        })

    def get_enabled_providers(self) -> list:
        """Get list of enabled AI providers"""
        config = self.load_ai_config()
        providers = ['anthropic', 'google', 'openrouter', 'huggingface', 'local_llm']

        enabled = []
        for p in providers:
            if p in config and config[p].get('enabled', False):
                # Also check if API key is available (except local_llm)
                if p == 'local_llm' or config[p].get('api_key'):
                    enabled.append(p)

        return enabled

    def get_vault_status(self) -> Dict[str, Any]:
        """Get vault connection status"""
        if not self._vault:
            return {'connected': False, 'reason': 'Vault not initialized'}

        return self._vault.get_vault_status()

    def reload_all(self):
        """Force reload all configurations"""
        self._ai_config = None
        self._camera_config = None
        self._grading_standards = None

        self.load_ai_config(reload=True)
        self.load_camera_config(reload=True)
        self.load_grading_standards(reload=True)

        logger.info("All configurations reloaded")

    def _default_camera_config(self) -> Dict[str, Any]:
        """Default camera configuration"""
        return {
            'default_camera': 0,
            'resolution': {'preferred': [1920, 1080]},
            'fps': 30,
            'capture': {
                'quality_threshold': 0.85,
                'stability_frames': 8,
                'jpeg_quality': 95
            }
        }

    def save_ai_config(self, config: Dict[str, Any]):
        """
        Save AI configuration to file

        Note: API keys are NOT saved to file - they remain in vault only
        """
        # Remove API keys before saving
        save_config = {}
        for key, value in config.items():
            if isinstance(value, dict):
                save_config[key] = {k: v for k, v in value.items() if k != 'api_key'}
                # Keep empty api_key placeholder
                if 'api_key' in value:
                    save_config[key]['api_key'] = ''
            else:
                save_config[key] = value

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(AI_CONFIG_PATH, 'w') as f:
            json.dump(save_config, f, indent=4)

        logger.info("AI configuration saved (API keys excluded)")


# Global config loader instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """Get or create global config loader"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def load_ai_config() -> Dict[str, Any]:
    """Convenience function to load AI config"""
    return get_config_loader().load_ai_config()


def get_api_key(provider: str) -> Optional[str]:
    """Convenience function to get API key for a provider"""
    config = get_config_loader().get_provider_config(provider)
    return config.api_key if config else None


# Auto-initialize on import
def initialize_config():
    """Initialize configuration with vault connection"""
    loader = get_config_loader()
    status = loader.get_vault_status()

    if status.get('available'):
        logger.info(f"Configuration initialized with Promethian Vault ({status.get('total_secrets', 0)} secrets)")
    else:
        logger.warning("Configuration initialized without vault - using environment variables")

    return loader
