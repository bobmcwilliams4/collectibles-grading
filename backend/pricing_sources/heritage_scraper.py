"""
Heritage Auctions Price Scraper
Fetches auction results from Heritage Auctions for premium collectibles pricing
"""

import asyncio
import aiohttp
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HeritageScraper:
    """
    Heritage Auctions Price Scraper

    Heritage is the premier auction house for collectibles.
    Their sales data represents high-end market values.
    """

    BASE_URL = "https://comics.ha.com/c/search-results.zx"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        self._rate_limit_delay = 2.5  # Be respectful to Heritage
        self._last_request_time = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(limit=2, force_close=True)
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

    def _extract_grade(self, text: str) -> Optional[float]:
        """Extract CGC grade from text"""
        patterns = [
            r'CGC\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*CGC',
            r'graded\s*(\d+\.?\d*)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    grade = float(match.group(1))
                    if 0.5 <= grade <= 10.0:
                        return grade
                except (ValueError, TypeError):
                    continue

        return None

    async def search_auctions(
        self,
        title: str,
        issue_number: Optional[str] = None,
        grade: float = 9.4,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search Heritage Auctions for sold items

        Args:
            title: Comic title
            issue_number: Issue number
            grade: Target CGC grade
            max_results: Maximum results to return

        Returns:
            List of auction results
        """
        await self._rate_limit()
        session = await self._get_session()

        # Build search query
        query = title
        if issue_number:
            query += f" #{issue_number}"
        query += f" CGC"

        # Heritage search URL
        url = f"{self.BASE_URL}?N=790+231+792&Ntt={quote_plus(query)}&type=saleprices-all"

        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Heritage search returned {response.status}")
                    return []

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                results = []

                # Find auction lot items
                lots = soup.select('.lot-item, .search-result, .auction-lot')

                for lot in lots[:max_results * 2]:
                    try:
                        # Get title
                        title_elem = lot.select_one('.lot-title, .item-title, h3 a')
                        if not title_elem:
                            continue
                        lot_title = title_elem.get_text(strip=True)

                        # Get price
                        price_elem = lot.select_one('.price-realized, .sold-price, .lot-price')
                        if not price_elem:
                            continue
                        price = self._parse_price(price_elem.get_text())
                        if not price or price < 1:
                            continue

                        # Extract grade from title
                        lot_grade = self._extract_grade(lot_title)

                        # Filter by grade proximity
                        if lot_grade and abs(lot_grade - grade) > 2.0:
                            continue

                        # Get auction date
                        date_elem = lot.select_one('.auction-date, .sale-date')
                        sale_date = None
                        if date_elem:
                            date_text = date_elem.get_text(strip=True)
                            try:
                                for fmt in ['%B %d, %Y', '%b %d, %Y', '%m/%d/%Y']:
                                    try:
                                        sale_date = datetime.strptime(date_text, fmt)
                                        break
                                    except ValueError:
                                        continue
                            except Exception:
                                pass

                        # Get lot URL
                        link = lot.select_one('a[href*="/itm/"]')
                        lot_url = None
                        if link:
                            lot_url = link.get('href')
                            if lot_url and not lot_url.startswith('http'):
                                lot_url = f"https://comics.ha.com{lot_url}"

                        results.append({
                            'title': lot_title,
                            'price': price,
                            'grade': lot_grade,
                            'sale_date': sale_date.isoformat() if sale_date else None,
                            'url': lot_url,
                            'source': 'heritage',
                            'sale_type': 'auction'
                        })

                        if len(results) >= max_results:
                            break

                    except Exception as e:
                        logger.debug(f"Error parsing Heritage lot: {e}")
                        continue

                return results

        except aiohttp.ClientError as e:
            logger.error(f"Heritage request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Heritage scraping error: {e}")
            return []

    async def get_price_analysis(
        self,
        title: str,
        issue_number: Optional[str] = None,
        grade: float = 9.4
    ) -> Dict[str, Any]:
        """
        Get price analysis from Heritage auction results

        Returns:
            Price data with statistics
        """
        results = await self.search_auctions(title, issue_number, grade, max_results=15)

        if not results:
            return {
                'price': None,
                'confidence': 0,
                'error': 'No Heritage auction results found',
                'source': 'heritage'
            }

        # Calculate statistics
        prices = [r['price'] for r in results]
        grades = [r['grade'] for r in results if r['grade']]

        from statistics import mean, median

        avg_price = mean(prices)
        med_price = median(prices)

        # Heritage prices tend to be premium, so use median
        final_price = med_price

        # Confidence based on results and grade match
        confidence = min(0.95, 0.6 + (len(results) * 0.03))

        if grades:
            grade_match = mean([abs(g - grade) for g in grades])
            if grade_match <= 0.5:
                confidence += 0.1
            elif grade_match > 1.5:
                confidence -= 0.15

        confidence = max(0.4, min(0.95, confidence))

        return {
            'price': round(final_price, 2),
            'average_price': round(avg_price, 2),
            'grade_matched': round(mean(grades), 1) if grades else grade,
            'confidence': round(confidence, 3),
            'sale_date': results[0].get('sale_date') if results else None,
            'url': results[0].get('url') if results else None,
            'results_count': len(results),
            'source': 'heritage',
            'recent_sales': results[:3]
        }

    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()


# Global instance
_scraper: Optional[HeritageScraper] = None


def _get_scraper() -> HeritageScraper:
    global _scraper
    if _scraper is None:
        _scraper = HeritageScraper()
    return _scraper


async def fetch_heritage_price(
    title: str,
    issue_number: Optional[str] = None,
    grade: float = 9.4
) -> Dict[str, Any]:
    """
    Fetch Heritage Auctions price for a collectible

    Args:
        title: Item title
        issue_number: Issue number
        grade: CGC grade

    Returns:
        Price data dictionary
    """
    scraper = _get_scraper()

    try:
        result = await scraper.get_price_analysis(title, issue_number, grade)
        return result
    except Exception as e:
        logger.error(f"Heritage price fetch failed: {e}")
        return {
            'price': None,
            'confidence': 0,
            'error': str(e),
            'source': 'heritage'
        }


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
