"""
Claude Code CLI Integration
Wrapper for Claude Code CLI for autonomous grading operations
"""

import subprocess
import json
import logging
import os
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class ClaudeCodeCLI:
    """
    Claude Code CLI Integration

    Features:
    - Direct CLI execution
    - Multi-image analysis
    - Structured JSON output
    - Error handling and retries
    - Session management
    """

    def __init__(self, oauth_token: str = None):
        self.oauth_token = oauth_token
        self._cli_path = self._find_cli()
        self._model = "claude-sonnet-4-20250514"

        if oauth_token:
            os.environ['ANTHROPIC_API_KEY'] = oauth_token

    def _find_cli(self) -> str:
        """Find Claude Code CLI executable"""
        # Common installation paths
        paths = [
            "claude",  # If in PATH
            "claude-code",
            str(Path.home() / ".local" / "bin" / "claude"),
            str(Path.home() / "AppData" / "Local" / "Programs" / "claude" / "claude.exe"),
            "/usr/local/bin/claude"
        ]

        for path in paths:
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        # Default to 'claude' and hope it's in PATH
        return "claude"

    async def grade_comic(
        self,
        front_image: str,
        back_image: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Grade comic using Claude Code CLI

        Args:
            front_image: Path to front cover image
            back_image: Optional path to back cover image
            metadata: Comic metadata

        Returns:
            Grading result dictionary
        """
        metadata = metadata or {}

        prompt = self._build_grading_prompt(metadata)

        # Build command
        cmd = [
            self._cli_path,
            "--print",  # Print response to stdout
            "--model", self._model,
            "--output-format", "json"
        ]

        # Add images
        cmd.extend(["--image", front_image])
        if back_image and Path(back_image).exists():
            cmd.extend(["--image", back_image])

        # Add prompt
        cmd.extend(["--prompt", prompt])

        try:
            # Run asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60.0
            )

            if process.returncode == 0:
                response_text = stdout.decode('utf-8')
                return self._parse_response(response_text)
            else:
                error_msg = stderr.decode('utf-8')
                logger.error(f"Claude CLI error: {error_msg}")
                return {
                    'provider': 'claude_cli',
                    'grade': None,
                    'error': error_msg
                }

        except asyncio.TimeoutError:
            logger.error("Claude CLI timeout")
            return {
                'provider': 'claude_cli',
                'grade': None,
                'error': 'Timeout'
            }

        except Exception as e:
            logger.error(f"Claude CLI execution error: {e}")
            return {
                'provider': 'claude_cli',
                'grade': None,
                'error': str(e)
            }

    def grade_comic_sync(
        self,
        front_image: str,
        back_image: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Synchronous version of grade_comic"""
        metadata = metadata or {}

        prompt = self._build_grading_prompt(metadata)

        cmd = [
            self._cli_path,
            "--print",
            "--model", self._model
        ]

        cmd.extend(["--image", front_image])
        if back_image and Path(back_image).exists():
            cmd.extend(["--image", back_image])

        cmd.extend(["--prompt", prompt])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return self._parse_response(result.stdout)
            else:
                return {
                    'provider': 'claude_cli',
                    'grade': None,
                    'error': result.stderr
                }

        except subprocess.TimeoutExpired:
            return {
                'provider': 'claude_cli',
                'grade': None,
                'error': 'Timeout'
            }

        except Exception as e:
            return {
                'provider': 'claude_cli',
                'grade': None,
                'error': str(e)
            }

    def _build_grading_prompt(self, metadata: Dict) -> str:
        """Build grading prompt"""
        prompt = """Analyze these comic book images for CGC grading.

GRADING CRITERIA:
1. Cover condition (tears, creases, spine stress)
2. Edge and corner wear
3. Color preservation
4. Structural integrity (staples, pages)
5. Cleanliness (writing, tape, stains)

GRADE SCALE:
10.0 = Gem Mint | 9.8 = Near Mint/Mint | 9.4 = Near Mint
8.0 = Very Fine | 6.0 = Fine | 4.0 = Very Good | 2.0 = Good

Return valid JSON:
{
    "grade": 8.5,
    "confidence": 0.90,
    "front_grade": 8.5,
    "back_grade": 8.5,
    "defects": [
        {"type": "defect_type", "severity": "minor/moderate/major", "location": "where"}
    ],
    "reasoning": "explanation",
    "key_issue_premium": false
}"""

        if metadata.get('title'):
            prompt += f"\n\nComic: {metadata['title']}"
            if metadata.get('issue_number'):
                prompt += f" #{metadata['issue_number']}"
        if metadata.get('publisher'):
            prompt += f"\nPublisher: {metadata['publisher']}"
        if metadata.get('key_issue'):
            prompt += "\nNote: This is a KEY ISSUE - grade carefully"

        return prompt

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude CLI response"""
        import re

        # Try direct JSON parse
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from response
        patterns = [
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*([\s\S]*?)\s*```',
            r'\{[\s\S]*"grade"[\s\S]*\}'
        ]

        for pattern in patterns:
            match = re.search(pattern, response_text)
            if match:
                try:
                    json_str = match.group(1) if '```' in pattern else match.group(0)
                    result = json.loads(json_str)
                    result['provider'] = 'claude_cli'
                    return result
                except:
                    continue

        # If all parsing fails, try to extract grade
        grade_match = re.search(r'"grade"\s*:\s*(\d+\.?\d*)', response_text)
        if grade_match:
            return {
                'provider': 'claude_cli',
                'grade': float(grade_match.group(1)),
                'confidence': 0.5,
                'defects': [],
                'reasoning': 'Extracted from partial response',
                'raw_response': response_text[:500]
            }

        return {
            'provider': 'claude_cli',
            'grade': None,
            'error': 'Failed to parse response',
            'raw_response': response_text[:500]
        }

    async def batch_grade(
        self,
        comics: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Batch grade multiple comics

        Args:
            comics: List of dicts with 'front' and optional 'back' image paths

        Returns:
            List of grading results
        """
        results = []

        for comic in comics:
            result = await self.grade_comic(
                comic['front'],
                comic.get('back'),
                comic.get('metadata')
            )
            results.append(result)

            # Small delay between requests
            await asyncio.sleep(0.5)

        return results

    def analyze_defects(
        self,
        image_path: str,
        initial_grade: float = None
    ) -> Dict[str, Any]:
        """
        Detailed defect analysis

        Args:
            image_path: Path to comic image
            initial_grade: Initial grade for context

        Returns:
            Detailed defect analysis
        """
        prompt = f"""Provide detailed defect analysis for this comic book image.

Initial Grade: {initial_grade or 'Unknown'}

For EACH defect:
1. Type (spine_stress, tear, crease, etc.)
2. Severity (trace, minor, moderate, major, severe)
3. Exact location (use quadrants or clock positions)
4. Impact on grade (-0.1 to -3.0)
5. Visibility (obvious/moderate/subtle)

Also analyze:
- Signs of cleaning or pressing
- Restoration attempts
- Page quality assessment

Return detailed JSON."""

        return self.grade_comic_sync(image_path, metadata={'detail_prompt': prompt})

    def get_cli_version(self) -> str:
        """Get Claude CLI version"""
        try:
            result = subprocess.run(
                [self._cli_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip()
        except:
            return "Unknown"


# Global instance
claude_cli = ClaudeCodeCLI()


async def autonomous_grade(
    front_path: str,
    back_path: str = None,
    metadata: Dict = None
) -> Dict[str, Any]:
    """Convenience function for autonomous grading"""
    return await claude_cli.grade_comic(front_path, back_path, metadata)
