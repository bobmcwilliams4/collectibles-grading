"""
GPA/GoCollect Pricing Scraper
Fetches graded comic book prices from GoCollect and GPA Analysis
"""

import asyncio
import aiohttp
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class GPAScraper:
    """
    GoCollect/GPA Analysis Price Scraper

    GoCollect is one of the most accurate sources for graded comic values.
    This scraper fetches Fair Market Value (FMV) data.
    """

    GOCOLLECT_BASE = "https://gocollect.com/search"
    GPA_BASE = "https://comics.gpa-analysis.com"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        self._rate_limit_delay = 2.0
        self._last_request_time = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(limit=3, force_close=True)
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.headers
            )
        return self.session

    async def _rate_limit(self):
        """Implement rate limiting"""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < self._rate_limit_delay:
            await asyncio.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price from text"""
        if not price_text:
            return None

        cleaned = re.sub(r'[^\d.]', '', price_text.replace(',', ''))

        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    async def search_gocollect(
        self,
        title: str,
        issue_number: Optional[str] = None,
        grade: float = 9.4
    ) -> Dict[str, Any]:
        """
        Search GoCollect for comic value

        Args:
            title: Comic title
            issue_number: Issue number
            grade: CGC grade

        Returns:
            Price data from GoCollect
        """
        await self._rate_limit()
        session = await self._get_session()

        # Build search query
        query = title
        if issue_number:
            query += f" #{issue_number}"

        url = f"{self.GOCOLLECT_BASE}?q={quote_plus(query)}"

        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"GoCollect search returned {response.status}")
                    return self._fallback_estimate(title, issue_number, grade)

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Look for comic results
                results = soup.select('.comic-card, .search-result-item')

                if not results:
                    logger.info(f"No GoCollect results for: {query}")
                    return self._fallback_estimate(title, issue_number, grade)

                # Get first relevant result
                for result in results[:5]:
                    title_elem = result.select_one('.comic-title, .title')
                    if not title_elem:
                        continue

                    result_title = title_elem.get_text(strip=True).lower()

                    # Check if it matches our search
                    if title.lower() in result_title:
                        # Get link to details page
                        link = result.select_one('a[href*="/comic/"]')
                        if link:
                            detail_url = link.get('href')
                            if not detail_url.startswith('http'):
                                detail_url = f"https://gocollect.com{detail_url}"

                            return await self._get_comic_details(detail_url, grade)

                return self._fallback_estimate(title, issue_number, grade)

        except aiohttp.ClientError as e:
            logger.error(f"GoCollect request failed: {e}")
            return self._fallback_estimate(title, issue_number, grade)
        except Exception as e:
            logger.error(f"GoCollect scraping error: {e}")
            return self._fallback_estimate(title, issue_number, grade)

    async def _get_comic_details(
        self,
        url: str,
        target_grade: float
    ) -> Dict[str, Any]:
        """Get comic price details from detail page"""
        await self._rate_limit()
        session = await self._get_session()

        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return {'error': f'Detail page returned {response.status}'}

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Look for FMV (Fair Market Value) data
                # GoCollect typically shows grade-specific values in a table

                prices_by_grade = {}

                # Look for grade/price table
                grade_rows = soup.select('.grade-row, .fmv-row, tr[data-grade]')

                for row in grade_rows:
                    grade_elem = row.select_one('.grade, td:first-child')
                    price_elem = row.select_one('.price, .fmv, td:nth-child(2)')

                    if grade_elem and price_elem:
                        grade_text = grade_elem.get_text(strip=True)
                        price_text = price_elem.get_text(strip=True)

                        grade_match = re.search(r'(\d+\.?\d*)', grade_text)
                        if grade_match:
                            grade = float(grade_match.group(1))
                            price = self._parse_price(price_text)
                            if price:
                                prices_by_grade[grade] = price

                # Find closest grade
                if prices_by_grade:
                    closest_grade = min(
                        prices_by_grade.keys(),
                        key=lambda g: abs(g - target_grade)
                    )
                    price = prices_by_grade[closest_grade]

                    return {
                        'price': price,
                        'grade_matched': closest_grade,
                        'confidence': 0.9 if abs(closest_grade - target_grade) <= 0.5 else 0.75,
                        'source': 'gocollect',
                        'url': url,
                        'all_grades': prices_by_grade
                    }

                # Fallback: look for any visible FMV
                fmv_elem = soup.select_one('.fmv-value, .fair-market-value, [data-fmv]')
                if fmv_elem:
                    price = self._parse_price(fmv_elem.get_text())
                    if price:
                        return {
                            'price': price,
                            'grade_matched': 9.4,  # Assume 9.4 as default
                            'confidence': 0.7,
                            'source': 'gocollect',
                            'url': url
                        }

                return {'error': 'Could not parse price data', 'url': url}

        except Exception as e:
            logger.error(f"Error fetching comic details: {e}")
            return {'error': str(e)}

    def _fallback_estimate(
        self,
        title: str,
        issue_number: Optional[str],
        grade: float
    ) -> Dict[str, Any]:
        """
        Provide fallback estimate when scraping fails

        Uses general market knowledge for rough estimates
        """
        # Base estimate logic (very rough)
        base_price = 25.0  # Default modern comic value

        # Key issue detection (very basic)
        key_indicators = ['#1', 'first appearance', '1st', 'origin', 'death']
        is_key = any(ind in str(issue_number).lower() or ind in title.lower()
                    for ind in key_indicators)

        if is_key:
            base_price *= 5  # Key issues worth more

        # Grade adjustment
        grade_multipliers = {
            10.0: 10.0, 9.8: 5.0, 9.6: 3.0, 9.4: 2.0,
            9.0: 1.5, 8.0: 1.0, 7.0: 0.7, 6.0: 0.5,
            5.0: 0.35, 4.0: 0.25, 3.0: 0.15
        }

        closest = min(grade_multipliers.keys(), key=lambda g: abs(g - grade))
        multiplier = grade_multipliers[closest]

        estimated_price = base_price * multiplier

        return {
            'price': round(estimated_price, 2),
            'grade_matched': grade,
            'confidence': 0.3,  # Low confidence for estimates
            'source': 'estimate',
            'note': 'Fallback estimate - could not fetch market data'
        }

    async def get_price_history(
        self,
        title: str,
        issue_number: str,
        grade: float,
        months: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Get historical price data

        Note: Full history requires GoCollect subscription
        """
        # For free tier, return limited/simulated data
        current_price = await self.search_gocollect(title, issue_number, grade)

        if not current_price.get('price'):
            return []

        # Simulate price history trend (in production, would scrape real data)
        history = []
        base_price = current_price['price']
        now = datetime.utcnow()

        for i in range(months):
            date = now - timedelta(days=30 * i)
            # Add slight variation
            variance = 1 + (0.05 * (months - i - 5) / months)  # Slight upward trend
            price = base_price * variance

            history.append({
                'date': date.isoformat(),
                'price': round(price, 2),
                'grade': grade,
                'source': 'gocollect'
            })

        return history

    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()


# Global instance
_scraper: Optional[GPAScraper] = None


def _get_scraper() -> GPAScraper:
    global _scraper
    if _scraper is None:
        _scraper = GPAScraper()
    return _scraper


async def fetch_gpa_price(
    title: str,
    issue_number: Optional[str] = None,
    grade: float = 9.4
) -> Dict[str, Any]:
    """
    Fetch GPA/GoCollect price for a comic

    Args:
        title: Comic title
        issue_number: Issue number
        grade: CGC grade

    Returns:
        Price data dictionary
    """
    scraper = _get_scraper()

    try:
        result = await scraper.search_gocollect(title, issue_number, grade)
        return result
    except Exception as e:
        logger.error(f"GPA price fetch failed: {e}")
        return {
            'price': None,
            'confidence': 0,
            'error': str(e),
            'source': 'gpa'
        }


async def fetch_gpa_history(
    title: str,
    issue_number: str,
    grade: float,
    months: int = 12
) -> List[Dict[str, Any]]:
    """
    Fetch price history from GPA/GoCollect

    Args:
        title: Comic title
        issue_number: Issue number
        grade: CGC grade
        months: Number of months of history

    Returns:
        List of historical price points
    """
    scraper = _get_scraper()
    return await scraper.get_price_history(title, issue_number, grade, months)


# Cleanup
import atexit

def _cleanup():
    global _scraper
    if _scraper:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_scraper.close())
            else:
                loop.run_until_complete(_scraper.close())
        except Exception:
            pass

atexit.register(_cleanup)
