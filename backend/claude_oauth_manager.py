"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║              CLAUDE OAUTH TOKEN MANAGER - AUTONOMOUS REFRESH                 ║
║           Commander Bobby Don McWilliams II - Authority Level 11.0           ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Solves the OAuth token expiration issue for Claude CLI in subprocess calls.
Auto-refreshes tokens by triggering Claude CLI interactive mode briefly.
"""

import json
import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ClaudeOAuthManager:
    """
    Manages Claude CLI OAuth tokens with automatic refresh.
    
    The Problem:
    - Claude CLI works interactively (has valid session)
    - Subprocess calls fail with expired token (401)
    - credentials.json shows stale tokens
    
    The Solution:
    - Monitor token expiration
    - Trigger interactive refresh when needed
    - Use OpenRouter as fallback during refresh
    """
    
    def __init__(self):
        self.creds_path = Path.home() / ".claude" / ".credentials.json"
        self.refresh_lock = threading.Lock()
        self.last_check = 0
        self.check_interval = 300  # Check every 5 minutes
        
    def get_credentials(self) -> Optional[Dict[str, Any]]:
        """Read Claude CLI credentials file"""
        try:
            if not self.creds_path.exists():
                logger.warning(f"Credentials file not found: {self.creds_path}")
                return None
                
            with open(self.creds_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading credentials: {e}")
            return None
    
    def is_token_expired(self, credentials: Optional[Dict] = None) -> bool:
        """Check if OAuth token is expired or will expire soon"""
        if credentials is None:
            credentials = self.get_credentials()
            
        if not credentials:
            return True
            
        oauth = credentials.get('claudeAiOauth', {})
        expires_at = oauth.get('expiresAt', 0)
        
        if not expires_at:
            return True
            
        # Check if expired or will expire within 1 hour
        expires_dt = datetime.fromtimestamp(expires_at / 1000)  # Convert ms to seconds
        buffer_time = datetime.now() + timedelta(hours=1)
        
        is_expired = expires_dt <= buffer_time
        
        if is_expired:
            logger.warning(f"Token expired or expiring soon: {expires_dt}")
        else:
            logger.info(f"Token valid until: {expires_dt}")
            
        return is_expired
    
    def refresh_token_interactive(self) -> bool:
        """
        Trigger token refresh by briefly launching Claude CLI interactively.
        
        This is the KEY INSIGHT: Claude CLI refreshes tokens automatically
        when run interactively, but NOT in subprocess mode with -p flag.
        
        Strategy: Launch interactive mode with a simple prompt, let it refresh,
        then kill it. The refreshed token stays in credentials.json.
        """
        with self.refresh_lock:
            try:
                logger.info("Attempting interactive token refresh...")
                
                # Find Claude CLI
                claude_paths = [
                    os.path.expandvars(r"%APPDATA%\npm\claude.cmd"),
                    os.path.expandvars(r"%APPDATA%\npm\claude"),
                    "claude"
                ]
                
                claude_cli = None
                for path in claude_paths:
                    if Path(path).exists():
                        claude_cli = path
                        break
                
                if not claude_cli:
                    logger.error("Claude CLI not found")
                    return False
                
                # Launch Claude interactively with minimal prompt
                # The CLI will refresh tokens automatically when it starts
                process = subprocess.Popen(
                    [claude_cli],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Give it a few seconds to initialize and refresh tokens
                time.sleep(5)
                
                # Send exit command
                try:
                    process.stdin.write("/exit\n")
                    process.stdin.flush()
                except:
                    pass
                
                # Wait for exit or kill after timeout
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                
                # Verify token was refreshed
                time.sleep(1)  # Give filesystem time to write
                if not self.is_token_expired():
                    logger.info("✓ Token refresh successful")
                    return True
                else:
                    logger.warning("Token still expired after refresh attempt")
                    return False
                    
            except Exception as e:
                logger.error(f"Interactive refresh failed: {e}")
                return False
    
    def ensure_valid_token(self, force_refresh: bool = False) -> bool:
        """
        Ensure we have a valid OAuth token.
        Auto-refreshes if expired or force_refresh=True.
        
        Returns True if token is valid, False otherwise.
        """
        # Rate limiting: don't check too frequently
        now = time.time()
        if not force_refresh and (now - self.last_check) < self.check_interval:
            return True
        
        self.last_check = now
        
        # Check if token is expired
        if force_refresh or self.is_token_expired():
            logger.info("Token needs refresh, attempting interactive refresh...")
            return self.refresh_token_interactive()
        
        return True
    
    def get_oauth_token(self) -> Optional[str]:
        """Get current OAuth access token if valid"""
        creds = self.get_credentials()
        if not creds:
            return None
            
        oauth = creds.get('claudeAiOauth', {})
        if self.is_token_expired(creds):
            return None
            
        return oauth.get('accessToken')


# Global instance
_oauth_manager = None

def get_oauth_manager() -> ClaudeOAuthManager:
    """Get or create global OAuth manager instance"""
    global _oauth_manager
    if _oauth_manager is None:
        _oauth_manager = ClaudeOAuthManager()
    return _oauth_manager


def ensure_claude_auth() -> bool:
    """
    Convenience function to ensure Claude CLI has valid auth.
    Call this before making Claude CLI subprocess calls.
    
    Usage:
        if not ensure_claude_auth():
            # Fallback to OpenRouter or show error
            pass
    """
    return get_oauth_manager().ensure_valid_token()


# Startup check - call this when backend starts
def initialize_claude_auth():
    """
    Initialize and validate Claude OAuth on backend startup.
    This ensures tokens are fresh before any requests come in.
    """
    manager = get_oauth_manager()
    
    logger.info("=== Claude OAuth Initialization ===")
    
    creds = manager.get_credentials()
    if not creds:
        logger.warning("No Claude credentials found - OAuth not configured")
        return False
    
    oauth = creds.get('claudeAiOauth', {})
    sub_type = oauth.get('subscriptionType', 'unknown')
    expires_at = oauth.get('expiresAt', 0)
    
    logger.info(f"Subscription: {sub_type}")
    logger.info(f"Token expires: {datetime.fromtimestamp(expires_at / 1000)}")
    
    if manager.is_token_expired():
        logger.warning("Token expired - forcing refresh...")
        success = manager.ensure_valid_token(force_refresh=True)
        if success:
            logger.info("✓ OAuth initialized successfully")
        else:
            logger.error("✗ OAuth refresh failed - Claude chat will use fallbacks")
        return success
    else:
        logger.info("✓ OAuth token valid")
        return True


if __name__ == "__main__":
    # Test the OAuth manager
    logging.basicConfig(level=logging.INFO)
    
    manager = get_oauth_manager()
    
    print("Current credentials:")
    creds = manager.get_credentials()
    if creds:
        oauth = creds.get('claudeAiOauth', {})
        print(f"  Subscription: {oauth.get('subscriptionType')}")
        print(f"  Expires: {datetime.fromtimestamp(oauth.get('expiresAt', 0) / 1000)}")
        print(f"  Expired: {manager.is_token_expired()}")
    
    print("\nTesting token refresh...")
    success = manager.ensure_valid_token(force_refresh=True)
    print(f"Refresh result: {success}")
