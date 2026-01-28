"""
OAuth Token Manager
Manages API tokens with secure storage and automatic refresh
Integrates with Promethian Vault for secure key retrieval
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
import base64
import hashlib

logger = logging.getLogger(__name__)

# Import vault integration (lazy loading to prevent circular imports)
_vault = None


def _get_vault():
    """Lazy load vault integration"""
    global _vault
    if _vault is None:
        try:
            from .vault_integration import get_vault
            _vault = get_vault()
        except Exception as e:
            logger.debug(f"Vault not available: {e}")
            _vault = False  # Mark as unavailable
    return _vault if _vault else None


class OAuthManager:
    """
    Secure OAuth Token Management

    Features:
    - Encrypted token storage
    - Automatic token refresh
    - Multiple provider support
    - Expiry tracking
    - Secure key derivation
    """

    def __init__(
        self,
        config_path: str = "P:/SOVEREIGN_APPS/collectibles_grading_system/config/oauth_config.json",
        secret_key: str = None
    ):
        self.config_path = Path(config_path)
        self.secret_key = secret_key or self._get_machine_key()
        self._fernet = Fernet(self._derive_key(self.secret_key))

        self._tokens: Dict[str, Dict] = {}
        self._load_tokens()

    def _get_machine_key(self) -> str:
        """Get unique machine identifier for encryption"""
        # Use combination of environment variables for machine-specific key
        machine_id = os.environ.get('COMPUTERNAME', '') + os.environ.get('USERNAME', '')
        return machine_id or 'default_key_change_me'

    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password"""
        # Use SHA256 to get consistent 32-byte key
        key_bytes = hashlib.sha256(password.encode()).digest()
        return base64.urlsafe_b64encode(key_bytes)

    def _load_tokens(self):
        """Load encrypted tokens from file"""
        if not self.config_path.exists():
            self._tokens = {}
            return

        try:
            with open(self.config_path, 'r') as f:
                encrypted_data = json.load(f)

            for provider, data in encrypted_data.items():
                if isinstance(data, dict) and 'encrypted_token' in data:
                    try:
                        decrypted = self._fernet.decrypt(
                            data['encrypted_token'].encode()
                        ).decode()
                        self._tokens[provider] = {
                            'token': decrypted,
                            'expires_at': data.get('expires_at'),
                            'refresh_token': self._decrypt_if_present(data.get('encrypted_refresh')),
                            'token_type': data.get('token_type', 'Bearer')
                        }
                    except Exception as e:
                        logger.warning(f"Failed to decrypt token for {provider}: {e}")
                else:
                    # Unencrypted token (legacy)
                    self._tokens[provider] = data

        except Exception as e:
            logger.error(f"Failed to load OAuth config: {e}")
            self._tokens = {}

    def _save_tokens(self):
        """Save encrypted tokens to file"""
        encrypted_data = {}

        for provider, data in self._tokens.items():
            if isinstance(data, dict) and 'token' in data:
                encrypted_data[provider] = {
                    'encrypted_token': self._fernet.encrypt(data['token'].encode()).decode(),
                    'expires_at': data.get('expires_at'),
                    'encrypted_refresh': self._encrypt_if_present(data.get('refresh_token')),
                    'token_type': data.get('token_type', 'Bearer')
                }
            else:
                encrypted_data[provider] = data

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(encrypted_data, f, indent=2)

    def _encrypt_if_present(self, value: Optional[str]) -> Optional[str]:
        """Encrypt value if not None"""
        if value:
            return self._fernet.encrypt(value.encode()).decode()
        return None

    def _decrypt_if_present(self, value: Optional[str]) -> Optional[str]:
        """Decrypt value if not None"""
        if value:
            try:
                return self._fernet.decrypt(value.encode()).decode()
            except:
                return None
        return None

    def get_token(self, provider: str = 'anthropic') -> Optional[str]:
        """
        Get token for provider

        Priority order:
        1. Promethian Vault (most secure)
        2. Environment variables
        3. Local encrypted storage

        Args:
            provider: API provider name

        Returns:
            Token string or None
        """
        # Provider to key name mapping
        env_vars = {
            'anthropic': 'ANTHROPIC_API_KEY',
            'google': 'GOOGLE_API_KEY',
            'gemini': 'GEMINI_API_KEY',
            'openrouter': 'OPENROUTER_API_KEY',
            'huggingface': 'HUGGINGFACE_API_KEY',
            'groq': 'GROQ_API_KEY',
            'gocollect': 'GOCOLLECT_API_KEY',
            'heritage': 'HERITAGE_API_KEY',
            'ebay': 'EBAY_API_KEY'
        }

        key_name = env_vars.get(provider)

        # Priority 1: Try Promethian Vault first
        vault = _get_vault()
        if vault and vault.is_available() and key_name:
            vault_token = vault.get_key(key_name)
            if vault_token:
                logger.debug(f"Retrieved {provider} token from Promethian Vault")
                return vault_token

        # Priority 2: Check environment variables
        if key_name:
            env_token = os.environ.get(key_name)
            if env_token:
                logger.debug(f"Retrieved {provider} token from environment")
                return env_token

        # Priority 3: Check stored tokens
        if provider in self._tokens:
            token_data = self._tokens[provider]

            # Check expiry
            if isinstance(token_data, dict):
                expires_at = token_data.get('expires_at')
                if expires_at:
                    expiry = datetime.fromisoformat(expires_at)
                    if expiry <= datetime.utcnow():
                        # Token expired, try refresh
                        if token_data.get('refresh_token'):
                            refreshed = self._refresh_token(provider)
                            if refreshed:
                                return refreshed
                        logger.warning(f"Token expired for {provider}")
                        return None

                return token_data.get('token')

            return token_data

        return None

    def set_token(
        self,
        provider: str,
        token: str,
        expires_in: int = None,
        refresh_token: str = None,
        token_type: str = 'Bearer'
    ):
        """
        Store token for provider

        Args:
            provider: API provider name
            token: Access token
            expires_in: Token lifetime in seconds
            refresh_token: Refresh token for renewal
            token_type: Token type (default: Bearer)
        """
        expires_at = None
        if expires_in:
            expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()

        self._tokens[provider] = {
            'token': token,
            'expires_at': expires_at,
            'refresh_token': refresh_token,
            'token_type': token_type
        }

        self._save_tokens()
        logger.info(f"Token stored for {provider}")

    def _refresh_token(self, provider: str) -> Optional[str]:
        """Attempt to refresh expired token"""
        token_data = self._tokens.get(provider, {})
        refresh_token = token_data.get('refresh_token')

        if not refresh_token:
            return None

        # Provider-specific refresh logic would go here
        # For now, just return None (manual refresh required)
        logger.info(f"Token refresh required for {provider}")
        return None

    def remove_token(self, provider: str):
        """Remove token for provider"""
        if provider in self._tokens:
            del self._tokens[provider]
            self._save_tokens()
            logger.info(f"Token removed for {provider}")

    def get_all_providers(self) -> list:
        """Get list of configured providers"""
        return list(self._tokens.keys())

    def check_token_status(self, provider: str) -> Dict[str, Any]:
        """
        Check token status

        Returns:
            Dict with status info
        """
        if provider not in self._tokens:
            return {
                'configured': False,
                'valid': False,
                'expires_at': None,
                'has_refresh': False
            }

        token_data = self._tokens.get(provider, {})

        if isinstance(token_data, str):
            return {
                'configured': True,
                'valid': True,
                'expires_at': None,
                'has_refresh': False
            }

        expires_at = token_data.get('expires_at')
        is_valid = True

        if expires_at:
            expiry = datetime.fromisoformat(expires_at)
            is_valid = expiry > datetime.utcnow()

        return {
            'configured': True,
            'valid': is_valid,
            'expires_at': expires_at,
            'has_refresh': bool(token_data.get('refresh_token'))
        }

    def get_authorization_header(self, provider: str) -> Optional[Dict[str, str]]:
        """
        Get authorization header for API requests

        Returns:
            Dict with Authorization header
        """
        token = self.get_token(provider)
        if not token:
            return None

        token_data = self._tokens.get(provider, {})
        token_type = 'Bearer'

        if isinstance(token_data, dict):
            token_type = token_data.get('token_type', 'Bearer')

        return {'Authorization': f'{token_type} {token}'}


# Global instance
oauth_manager = OAuthManager()


def get_token(provider: str = 'anthropic') -> Optional[str]:
    """Convenience function to get token"""
    return oauth_manager.get_token(provider)


def set_token(provider: str, token: str, **kwargs):
    """Convenience function to set token"""
    oauth_manager.set_token(provider, token, **kwargs)
