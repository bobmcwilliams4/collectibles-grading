"""
CGC Comics Integration Module
Handles authentication and data retrieval from CGC Comics website
for census data, population reports, and price verification
"""

import asyncio
import aiohttp
import logging
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
from urllib.parse import urlencode
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class CGCIntegration:
    """
    CGC Comics Integration Handler

    Provides authenticated access to CGC data including:
    - Census data lookup
    - Population reports
    - Grading verification
    - Market value data
    """

    BASE_URL = "https://www.cgccomics.com"
    LOGIN_URL = f"{BASE_URL}/account/login/"  # Trailing slash required
    CENSUS_URL = f"{BASE_URL}/census"
    VERIFY_URL = f"{BASE_URL}/certlookup"

    # Session storage path
    SESSION_FILE = Path("P:/SOVEREIGN_APPS/collectibles_grading_system/cache/cgc_session.json")

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.authenticated = False
        self.session_expires: Optional[datetime] = None
        self.user_info: Dict[str, Any] = {}

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        self._rate_limit_delay = 2.0  # Respect CGC's servers
        self._last_request_time = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with cookie persistence"""
        if self.session is None or self.session.closed:
            # Create cookie jar for session persistence
            jar = aiohttp.CookieJar()

            # Try to load saved session
            if self.SESSION_FILE.exists():
                try:
                    with open(self.SESSION_FILE, 'r') as f:
                        saved = json.load(f)
                        expires = datetime.fromisoformat(saved.get('expires', '2000-01-01'))
                        if expires > datetime.now():
                            # Session still valid
                            for cookie_data in saved.get('cookies', []):
                                jar.update_cookies({cookie_data['name']: cookie_data['value']})
                            self.authenticated = saved.get('authenticated', False)
                            self.session_expires = expires
                            self.user_info = saved.get('user_info', {})
                except Exception as e:
                    logger.debug(f"Could not load saved CGC session: {e}")

            connector = aiohttp.TCPConnector(limit=3, force_close=True)
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.headers,
                cookie_jar=jar
            )

        return self.session

    async def _rate_limit(self):
        """Implement rate limiting to respect CGC's servers"""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < self._rate_limit_delay:
            await asyncio.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    def _save_session(self):
        """Save session state for persistence"""
        try:
            self.SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

            cookies = []
            if self.session and self.session.cookie_jar:
                for cookie in self.session.cookie_jar:
                    cookies.append({
                        'name': cookie.key,
                        'value': cookie.value
                    })

            session_data = {
                'authenticated': self.authenticated,
                'expires': self.session_expires.isoformat() if self.session_expires else None,
                'user_info': self.user_info,
                'cookies': cookies
            }

            with open(self.SESSION_FILE, 'w') as f:
                json.dump(session_data, f)

        except Exception as e:
            logger.error(f"Failed to save CGC session: {e}")

    async def login(self, username: str, password: str, remember: bool = True) -> Dict[str, Any]:
        """
        Authenticate with CGC Comics website

        Args:
            username: CGC account username or email
            password: CGC account password
            remember: Whether to save session for 7 days

        Returns:
            Authentication result with status and user info
        """
        await self._rate_limit()
        session = await self._get_session()

        try:
            # First, get the login page to obtain CSRF token
            async with session.get(self.LOGIN_URL) as response:
                if response.status != 200:
                    return {
                        'success': False,
                        'error': f'Could not access login page (status {response.status})'
                    }

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Look for CSRF token
                csrf_input = soup.find('input', {'name': '__RequestVerificationToken'})
                csrf_token = csrf_input['value'] if csrf_input else None

            await self._rate_limit()

            # Prepare login data - only include RememberMe if checked (checkbox behavior)
            login_data = {
                'Username': username,
                'Password': password,
            }

            # RememberMe checkbox should only be present when checked
            if remember:
                login_data['RememberMe'] = 'true'

            if csrf_token:
                login_data['__RequestVerificationToken'] = csrf_token

            # Add POST-specific headers
            post_headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': self.BASE_URL,
                'Referer': self.LOGIN_URL,
            }

            # Submit login
            async with session.post(
                self.LOGIN_URL,
                data=login_data,
                headers=post_headers,
                allow_redirects=True
            ) as response:

                final_url = str(response.url)
                html = await response.text()

                logger.debug(f"CGC login response - Status: {response.status}, Final URL: {final_url}")
                logger.debug(f"CGC response length: {len(html)} chars")

                # Check if login was successful by looking for logout link or account pages
                html_lower = html.lower()
                login_success_indicators = [
                    'logout' in html_lower,
                    'my account' in html_lower,
                    'account/logout' in html_lower,
                    'my-account' in final_url.lower(),
                    '/account' in final_url.lower() and 'login' not in final_url.lower()
                ]

                login_failure_indicators = [
                    'invalid username' in html_lower,
                    'invalid password' in html_lower,
                    'incorrect' in html_lower,
                    'login failed' in html_lower,
                    'authentication failed' in html_lower
                ]

                logger.debug(f"Success indicators: {login_success_indicators}")
                logger.debug(f"Failure indicators: {login_failure_indicators}")

                if any(login_success_indicators) and not any(login_failure_indicators):
                    self.authenticated = True
                    self.session_expires = datetime.now() + timedelta(days=7 if remember else 1)

                    # Try to extract user info
                    soup = BeautifulSoup(html, 'html.parser')
                    username_elem = soup.find(class_='username') or soup.find(class_='user-name')

                    self.user_info = {
                        'username': username,
                        'display_name': username_elem.get_text(strip=True) if username_elem else username,
                        'logged_in_at': datetime.now().isoformat()
                    }

                    self._save_session()

                    logger.info(f"CGC login successful for user: {username}")

                    return {
                        'success': True,
                        'message': 'Login successful',
                        'user': self.user_info,
                        'session_expires': self.session_expires.isoformat()
                    }

                elif any(login_failure_indicators):
                    return {
                        'success': False,
                        'error': 'Invalid username or password'
                    }

                else:
                    # Check if we're still on the login page (means login failed)
                    if 'login' in final_url.lower():
                        return {
                            'success': False,
                            'error': 'Login failed - credentials may be incorrect'
                        }
                    return {
                        'success': False,
                        'error': 'Login failed - unexpected response',
                        'debug_url': final_url
                    }

        except aiohttp.ClientError as e:
            logger.error(f"CGC login network error: {e}")
            return {
                'success': False,
                'error': f'Network error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"CGC login error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def logout(self) -> Dict[str, Any]:
        """Log out from CGC and clear session"""
        try:
            if self.session:
                await self._rate_limit()
                async with self.session.get(f"{self.BASE_URL}/account/logout") as response:
                    pass

            self.authenticated = False
            self.session_expires = None
            self.user_info = {}

            # Remove saved session
            if self.SESSION_FILE.exists():
                self.SESSION_FILE.unlink()

            return {'success': True, 'message': 'Logged out successfully'}

        except Exception as e:
            logger.error(f"CGC logout error: {e}")
            return {'success': False, 'error': str(e)}

    async def check_status(self) -> Dict[str, Any]:
        """Check current authentication status"""
        # Check if session is expired
        if self.session_expires and datetime.now() > self.session_expires:
            self.authenticated = False

        return {
            'authenticated': self.authenticated,
            'session_expires': self.session_expires.isoformat() if self.session_expires else None,
            'user': self.user_info if self.authenticated else None
        }

    async def verify_cert(self, cert_number: str) -> Dict[str, Any]:
        """
        Verify a CGC certification number and get details

        Args:
            cert_number: The CGC certification number

        Returns:
            Certification details if found
        """
        await self._rate_limit()
        session = await self._get_session()

        # Clean cert number
        cert_number = re.sub(r'[^0-9]', '', cert_number)

        if not cert_number:
            return {'success': False, 'error': 'Invalid certification number'}

        try:
            url = f"{self.VERIFY_URL}/{cert_number}"

            async with session.get(url) as response:
                if response.status != 200:
                    return {'success': False, 'error': 'Certification not found'}

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Parse certification details
                details = {}

                # Look for comic details
                title_elem = soup.find(class_='comic-title') or soup.find('h1')
                if title_elem:
                    details['title'] = title_elem.get_text(strip=True)

                grade_elem = soup.find(class_='grade') or soup.find(class_='cgc-grade')
                if grade_elem:
                    grade_text = grade_elem.get_text(strip=True)
                    grade_match = re.search(r'(\d+\.?\d*)', grade_text)
                    if grade_match:
                        details['grade'] = float(grade_match.group(1))

                # Look for additional info in tables or definition lists
                info_rows = soup.find_all(['tr', 'dt', 'dd'])
                for i, row in enumerate(info_rows):
                    text = row.get_text(strip=True).lower()
                    if 'issue' in text:
                        next_elem = info_rows[i+1] if i+1 < len(info_rows) else None
                        if next_elem:
                            details['issue_number'] = next_elem.get_text(strip=True)
                    elif 'publisher' in text:
                        next_elem = info_rows[i+1] if i+1 < len(info_rows) else None
                        if next_elem:
                            details['publisher'] = next_elem.get_text(strip=True)
                    elif 'page quality' in text or 'paper' in text:
                        next_elem = info_rows[i+1] if i+1 < len(info_rows) else None
                        if next_elem:
                            details['page_quality'] = next_elem.get_text(strip=True)

                details['cert_number'] = cert_number
                details['verified'] = True
                details['verified_at'] = datetime.now().isoformat()

                return {
                    'success': True,
                    'data': details
                }

        except Exception as e:
            logger.error(f"CGC cert verification error: {e}")
            return {'success': False, 'error': str(e)}

    async def get_census_data(
        self,
        title: str,
        issue_number: Optional[str] = None,
        publisher: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get census data for a comic from CGC

        Args:
            title: Comic title
            issue_number: Issue number
            publisher: Publisher name

        Returns:
            Census data including population counts by grade
        """
        await self._rate_limit()
        session = await self._get_session()

        try:
            # Build search query
            query = title
            if issue_number:
                query += f" #{issue_number}"

            search_url = f"{self.CENSUS_URL}?search={query}"

            async with session.get(search_url) as response:
                if response.status != 200:
                    return {'success': False, 'error': 'Census lookup failed'}

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Parse census results
                results = []

                # Look for census table rows
                table = soup.find('table', class_='census-table') or soup.find('table')
                if table:
                    rows = table.find_all('tr')[1:]  # Skip header
                    for row in rows[:10]:  # Limit results
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 3:
                            result = {
                                'title': cells[0].get_text(strip=True) if cells else None,
                                'total_graded': cells[-1].get_text(strip=True) if cells else None
                            }

                            # Parse grade population
                            grade_pop = {}
                            for i, cell in enumerate(cells[1:-1]):
                                text = cell.get_text(strip=True)
                                if text.isdigit():
                                    # Map column index to grade (varies by table layout)
                                    grade_pop[f'grade_{i}'] = int(text)

                            result['grade_population'] = grade_pop
                            results.append(result)

                return {
                    'success': True,
                    'query': query,
                    'results': results,
                    'source': 'cgc_census'
                }

        except Exception as e:
            logger.error(f"CGC census lookup error: {e}")
            return {'success': False, 'error': str(e)}

    async def get_market_value(
        self,
        title: str,
        issue_number: str,
        grade: float
    ) -> Dict[str, Any]:
        """
        Get market value data from CGC for a graded comic

        Note: Requires authenticated session for full pricing data

        Args:
            title: Comic title
            issue_number: Issue number
            grade: CGC grade

        Returns:
            Market value data if available
        """
        if not self.authenticated:
            return {
                'success': False,
                'error': 'Authentication required for market values',
                'requires_auth': True
            }

        await self._rate_limit()
        session = await self._get_session()

        try:
            # CGC's pricing is typically behind auth
            # This is a placeholder for the actual implementation
            # which would depend on CGC's specific endpoints

            return {
                'success': True,
                'title': title,
                'issue_number': issue_number,
                'grade': grade,
                'source': 'cgc',
                'note': 'Market value lookup requires CGC subscription',
                'authenticated': self.authenticated
            }

        except Exception as e:
            logger.error(f"CGC market value error: {e}")
            return {'success': False, 'error': str(e)}

    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()


# Global instance
_cgc: Optional[CGCIntegration] = None


def get_cgc() -> CGCIntegration:
    """Get or create the CGC integration instance"""
    global _cgc
    if _cgc is None:
        _cgc = CGCIntegration()
    return _cgc


# API functions for external use
async def cgc_login(username: str, password: str, remember: bool = True) -> Dict[str, Any]:
    """Login to CGC"""
    cgc = get_cgc()
    return await cgc.login(username, password, remember)


async def cgc_logout() -> Dict[str, Any]:
    """Logout from CGC"""
    cgc = get_cgc()
    return await cgc.logout()


async def cgc_status() -> Dict[str, Any]:
    """Get CGC authentication status"""
    cgc = get_cgc()
    return await cgc.check_status()


async def cgc_verify(cert_number: str) -> Dict[str, Any]:
    """Verify a CGC certification"""
    cgc = get_cgc()
    return await cgc.verify_cert(cert_number)


async def cgc_census(title: str, issue: Optional[str] = None) -> Dict[str, Any]:
    """Get census data"""
    cgc = get_cgc()
    return await cgc.get_census_data(title, issue)


# Cleanup
import atexit

def _cleanup():
    global _cgc
    if _cgc:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_cgc.close())
            else:
                loop.run_until_complete(_cgc.close())
        except Exception:
            pass

atexit.register(_cleanup)
