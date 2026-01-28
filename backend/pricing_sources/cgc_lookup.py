"""
CGC Census and Price Lookup
Fetches graded comic data from CGC's public census and price guide
"""

import asyncio
import aiohttp
import logging
import re
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class CGCLookup:
    """
    CGC Census and Price Lookup

    Fetches data from:
    - CGC Census (population counts by grade)
    - CGC Pricing (Fair Market Values when available)
    """

    CENSUS_SEARCH_URL = "https://www.cgccomics.com/census/search/"
    CENSUS_DETAIL_URL = "https://www.cgccomics.com/census/"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        self._rate_limit_delay = 1.5
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

    async def search_census(
        self,
        title: str,
        issue_number: Optional[str] = None,
        target_grade: float = 9.4
    ) -> Dict[str, Any]:
        """
        Search CGC Census for comic population data

        Args:
            title: Comic title
            issue_number: Issue number
            target_grade: Target grade to look up

        Returns:
            Census data including population counts and any available pricing
        """
        await self._rate_limit()
        session = await self._get_session()

        # Build search query
        query = title
        if issue_number and issue_number not in ['??', 'Unknown', None]:
            query += f" {issue_number}"

        search_url = f"{self.CENSUS_SEARCH_URL}?search={quote_plus(query)}"
        logger.info(f"[CGC] Searching census: {query}")

        try:
            async with session.get(search_url) as response:
                if response.status != 200:
                    logger.warning(f"[CGC] Census search returned {response.status}")
                    return {'error': f'HTTP {response.status}', 'source': 'cgc'}

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Look for search results
                # CGC census shows results in a table or card format
                results = soup.select('.census-result, .search-result, tr.result-row, .comic-row')

                if not results:
                    # Try alternative selectors
                    results = soup.select('table tr')[1:11]  # Skip header, get first 10 rows

                if not results:
                    logger.info(f"[CGC] No census results for: {query}")
                    return self._estimate_from_grade(title, issue_number, target_grade)

                # Process results to find best match
                best_match = None
                best_score = 0

                for result in results[:10]:
                    result_text = result.get_text(' ', strip=True).lower()

                    # Score based on title and issue match
                    score = 0
                    title_lower = title.lower()

                    if title_lower in result_text:
                        score += 10

                    # Check for issue number match
                    if issue_number and issue_number not in ['??', 'Unknown']:
                        # Look for issue number patterns
                        issue_patterns = [
                            f"#{issue_number}",
                            f"# {issue_number}",
                            f"issue {issue_number}",
                            f"no. {issue_number}",
                            f"no.{issue_number}",
                        ]
                        for pattern in issue_patterns:
                            if pattern in result_text:
                                score += 5
                                break

                    if score > best_score:
                        best_score = score
                        best_match = result

                if best_match and best_score >= 5:
                    # Try to get detail link
                    link = best_match.select_one('a[href*="/census/"]')
                    if link:
                        detail_url = link.get('href')
                        if not detail_url.startswith('http'):
                            detail_url = f"https://www.cgccomics.com{detail_url}"

                        return await self._get_census_detail(detail_url, target_grade)

                    # Try to extract data from search results directly
                    return self._extract_from_result(best_match, target_grade)

                return self._estimate_from_grade(title, issue_number, target_grade)

        except aiohttp.ClientError as e:
            logger.error(f"[CGC] Request failed: {e}")
            return {'error': str(e), 'source': 'cgc'}
        except Exception as e:
            logger.error(f"[CGC] Scraping error: {e}")
            return {'error': str(e), 'source': 'cgc'}

    async def _get_census_detail(
        self,
        url: str,
        target_grade: float
    ) -> Dict[str, Any]:
        """Get detailed census data from detail page"""
        await self._rate_limit()
        session = await self._get_session()

        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return {'error': f'Detail page returned {response.status}', 'source': 'cgc'}

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                result = {
                    'source': 'cgc_census',
                    'url': url,
                    'population_by_grade': {},
                    'total_graded': 0
                }

                # Look for population data by grade
                # CGC census typically shows grades in columns or rows

                # Try to find grade/count pairs
                grade_cells = soup.select('[data-grade], .grade-cell, td.grade')
                count_cells = soup.select('[data-count], .count-cell, td.count')

                # Alternative: look for table with grade data
                tables = soup.select('table')
                for table in tables:
                    rows = table.select('tr')
                    for row in rows:
                        cells = row.select('td, th')
                        if len(cells) >= 2:
                            # First cell might be grade, second might be count
                            cell_text = cells[0].get_text(strip=True)
                            grade_match = re.match(r'^(\d+\.?\d*)$', cell_text)
                            if grade_match:
                                grade = float(grade_match.group(1))
                                if 0.5 <= grade <= 10.0:
                                    count_text = cells[1].get_text(strip=True)
                                    count_match = re.search(r'(\d+)', count_text.replace(',', ''))
                                    if count_match:
                                        count = int(count_match.group(1))
                                        result['population_by_grade'][grade] = count
                                        result['total_graded'] += count

                # Look for price data if available (CGC shows FMV for some comics)
                price_elem = soup.select_one('.price, .fmv, .fair-market-value, [data-price]')
                if price_elem:
                    price = self._parse_price(price_elem.get_text())
                    if price:
                        result['price'] = price
                        result['confidence'] = 0.85

                # Get population at target grade
                if result['population_by_grade']:
                    closest_grade = min(
                        result['population_by_grade'].keys(),
                        key=lambda g: abs(g - target_grade)
                    )
                    result['grade_matched'] = closest_grade
                    result['population_at_grade'] = result['population_by_grade'].get(closest_grade, 0)

                    # Calculate rarity score based on population
                    pop = result['population_at_grade']
                    if pop <= 10:
                        result['rarity'] = 'Ultra Rare'
                        result['rarity_score'] = 0.95
                    elif pop <= 50:
                        result['rarity'] = 'Very Rare'
                        result['rarity_score'] = 0.8
                    elif pop <= 200:
                        result['rarity'] = 'Rare'
                        result['rarity_score'] = 0.6
                    elif pop <= 1000:
                        result['rarity'] = 'Uncommon'
                        result['rarity_score'] = 0.4
                    else:
                        result['rarity'] = 'Common'
                        result['rarity_score'] = 0.2

                if not result.get('price') and result['population_by_grade']:
                    # Estimate price based on rarity if no FMV available
                    result.update(self._estimate_from_grade(
                        '', '', target_grade,
                        rarity_score=result.get('rarity_score', 0.3)
                    ))
                    result['note'] = 'Price estimated from census rarity'

                return result

        except Exception as e:
            logger.error(f"[CGC] Error fetching census detail: {e}")
            return {'error': str(e), 'source': 'cgc'}

    def _extract_from_result(
        self,
        result_elem,
        target_grade: float
    ) -> Dict[str, Any]:
        """Extract data directly from search result element"""
        result = {
            'source': 'cgc_census',
            'grade_matched': target_grade,
            'confidence': 0.5
        }

        # Try to find population count
        text = result_elem.get_text(' ', strip=True)
        pop_match = re.search(r'(\d+)\s*(?:graded|copies|total)', text, re.IGNORECASE)
        if pop_match:
            result['total_graded'] = int(pop_match.group(1))

        # Return with estimate
        result.update(self._estimate_from_grade('', '', target_grade))
        return result

    def _estimate_from_grade(
        self,
        title: str,
        issue_number: Optional[str],
        grade: float,
        rarity_score: float = 0.3
    ) -> Dict[str, Any]:
        """
        Estimate price based on grade using CGC market data patterns

        This uses general CGC market knowledge when direct data isn't available
        """
        # Base multipliers by grade (based on typical CGC market patterns)
        grade_multipliers = {
            10.0: 25.0,   # Gem Mint - extremely rare
            9.9: 15.0,    # Mint
            9.8: 8.0,     # Near Mint/Mint
            9.6: 4.0,     # Near Mint+
            9.4: 2.5,     # Near Mint
            9.2: 1.8,     # Near Mint-
            9.0: 1.5,     # Very Fine/Near Mint
            8.5: 1.3,     # Very Fine+
            8.0: 1.0,     # Very Fine (baseline)
            7.5: 0.8,     # Very Fine-
            7.0: 0.65,    # Fine/Very Fine
            6.5: 0.55,    # Fine+
            6.0: 0.45,    # Fine
            5.5: 0.38,    # Fine-
            5.0: 0.32,    # Very Good/Fine
            4.5: 0.27,    # Very Good+
            4.0: 0.22,    # Very Good
            3.5: 0.18,    # Very Good-
            3.0: 0.15,    # Good/Very Good
            2.5: 0.12,    # Good+
            2.0: 0.10,    # Good
            1.5: 0.08,    # Fair/Good
            1.0: 0.06,    # Fair
            0.5: 0.04,    # Poor
        }

        # Find closest grade
        closest = min(grade_multipliers.keys(), key=lambda g: abs(g - grade))
        multiplier = grade_multipliers[closest]

        # Base price for a generic modern graded comic (VF 8.0)
        base_price = 40.0  # Typical CGC slab with modern comic

        # Adjust for rarity
        rarity_multiplier = 1 + (rarity_score * 2)  # 1x to 3x based on rarity

        estimated_price = base_price * multiplier * rarity_multiplier

        return {
            'price': round(estimated_price, 2),
            'grade_matched': grade,
            'confidence': 0.3,  # Low confidence for estimates
            'source': 'cgc_estimate',
            'note': 'Estimated based on CGC grade multipliers'
        }

    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()


# Global instance
_lookup: Optional[CGCLookup] = None


def _get_lookup() -> CGCLookup:
    global _lookup
    if _lookup is None:
        _lookup = CGCLookup()
    return _lookup


async def fetch_cgc_data(
    title: str,
    issue_number: Optional[str] = None,
    grade: float = 9.4
) -> Dict[str, Any]:
    """
    Fetch CGC census and price data for a comic

    Args:
        title: Comic title
        issue_number: Issue number
        grade: Target CGC grade

    Returns:
        Dictionary with census data, population, and estimated/actual price
    """
    lookup = _get_lookup()

    try:
        result = await lookup.search_census(title, issue_number, grade)
        logger.info(f"[CGC] Result for {title} #{issue_number} @ {grade}: {result.get('price', 'N/A')}")
        return result
    except Exception as e:
        logger.error(f"[CGC] Lookup failed: {e}")
        return {
            'price': None,
            'confidence': 0,
            'error': str(e),
            'source': 'cgc'
        }


# Cleanup
import atexit

def _cleanup():
    global _lookup
    if _lookup:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_lookup.close())
            else:
                loop.run_until_complete(_lookup.close())
        except Exception:
            pass

atexit.register(_cleanup)
