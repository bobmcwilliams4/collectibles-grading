"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║         CLAUDE CHAT INTEGRATION - OAUTH + OPENROUTER FALLBACK               ║
║           Commander Bobby Don McWilliams II - Authority Level 11.0           ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Complete solution for Claude chat with autonomous OAuth refresh + fallback.
"""

import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import httpx

from claude_oauth_manager import get_oauth_manager, ensure_claude_auth

logger = logging.getLogger(__name__)


class ClaudeChatHandler:
    """
    Handles Claude chat with smart routing:
    1. Primary: Claude CLI with OAuth (subscription)
    2. Fallback: OpenRouter (also has Claude models)
    """
    
    def __init__(self):
        self.oauth_manager = get_oauth_manager()
        self.openrouter_key = os.getenv('OPENROUTER_API_KEY')
        
    async def chat(
        self,
        message: str,
        system_prompt: str = "",
        context: str = "",
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Send chat message to Claude with automatic fallback.
        
        Returns:
            {
                'success': bool,
                'response': str,
                'method': 'oauth_cli' | 'openrouter_fallback' | 'error',
                'usage': dict
            }
        """
        
        # Build full prompt
        full_prompt = ""
        if system_prompt:
            full_prompt += system_prompt + "\n\n"
        if context:
            full_prompt += context + "\n\n"
        full_prompt += f"User: {message}"
        
        # Try OAuth CLI first
        try:
            # Ensure token is valid before attempting
            if ensure_claude_auth():
                result = await self._chat_oauth_cli(full_prompt, max_tokens)
                if result['success']:
                    return result
                    
                # Check if it's an auth error
                if 'authentication' in result.get('error', '').lower():
                    logger.warning("OAuth auth error, trying fallback...")
                else:
                    # Other error, return it
                    return result
        except Exception as e:
            logger.error(f"OAuth CLI failed: {e}")
        
        # Fallback to OpenRouter
        logger.info("Using OpenRouter fallback for Claude chat")
        return await self._chat_openrouter_fallback(message, system_prompt, context, max_tokens)
    
    async def _chat_oauth_cli(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """Use Claude CLI with OAuth subscription"""
        try:
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
                claude_cli = "claude"
            
            # Build command
            cmd = [claude_cli, '-p', '--output-format', 'json']
            
            # Remove API key to force OAuth
            clean_env = os.environ.copy()
            clean_env.pop('ANTHROPIC_API_KEY', None)
            
            # Run subprocess
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=120,
                env=clean_env
            )
            
            if result.returncode == 0 and result.stdout:
                # Parse JSON response
                import json
                try:
                    data = json.loads(result.stdout)
                    response_text = data.get('result', result.stdout)
                except:
                    response_text = result.stdout
                
                return {
                    'success': True,
                    'response': response_text,
                    'method': 'oauth_cli',
                    'usage': {
                        'subscription': True,
                        'cost': 0.0
                    }
                }
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                return {
                    'success': False,
                    'error': error_msg,
                    'method': 'oauth_cli'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': "Request timed out",
                'method': 'oauth_cli'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'method': 'oauth_cli'
            }
    
    async def _chat_openrouter_fallback(
        self,
        message: str,
        system_prompt: str,
        context: str,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Use OpenRouter as fallback (also has Claude models)"""
        
        if not self.openrouter_key:
            return {
                'success': False,
                'error': "OpenRouter API key not configured",
                'method': 'openrouter_fallback'
            }
        
        try:
            # Build messages
            messages = []
            if system_prompt or context:
                system_content = system_prompt
                if context:
                    system_content += "\n\n" + context
                messages.append({"role": "system", "content": system_content})
            messages.append({"role": "user", "content": message})
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openrouter_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://collectibles-grading.local",
                        "X-Title": "Comic Grading Assistant"
                    },
                    json={
                        "model": "anthropic/claude-3.5-sonnet:beta",
                        "messages": messages,
                        "max_tokens": max_tokens
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data['choices'][0]['message']['content']
                    usage = data.get('usage', {})
                    
                    return {
                        'success': True,
                        'response': response_text,
                        'method': 'openrouter_fallback',
                        'usage': usage
                    }
                else:
                    return {
                        'success': False,
                        'error': f"OpenRouter error: {response.status_code}",
                        'method': 'openrouter_fallback'
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'error': f"OpenRouter fallback failed: {str(e)}",
                'method': 'openrouter_fallback'
            }


# Global instance
_chat_handler = None

def get_chat_handler() -> ClaudeChatHandler:
    """Get or create global chat handler"""
    global _chat_handler
    if _chat_handler is None:
        _chat_handler = ClaudeChatHandler()
    return _chat_handler
