"""
eBay Sold Listings Scraper
Fetches sold/completed listing prices from eBay for collectibles pricing

Uses Playwright for headless browser rendering since eBay now uses
client-side JavaScript rendering for search results.
"""

import asyncio
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from statistics import mean, median

# Playwright for headless browser (eBay requires JS rendering)
try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logging.warning("Playwright not installed - eBay scraper will have limited functionality")

logger = logging.getLogger(__name__)

# eBay category IDs for common collectibles
EBAY_CATEGORIES = {
    'comics': '63',          # Comic Books
    'baseball_cards': '213',  # Baseball Cards
    'sports_cards': '212',    # Sports Trading Cards
    'trading_cards': '183050', # Trading Card Games
    'coins': '11116',         # Coins & Paper Money
    'stamps': '260',          # Stamps
    'action_figures': '246',  # Action Figures
    'toys': '220',            # Toys & Hobbies
    'art': '550',             # Art
    'vinyl': '176985',        # Vinyl Records
    'signed_books': '29223',  # Antiquarian & Collectible Books
}


class EbayScraper:
    """
    eBay Sold Listings Scraper

    Scrapes eBay's completed/sold listings to find real market prices.
    Uses Playwright headless browser since eBay requires JavaScript rendering.
    """

    BASE_URL = "https://www.ebay.com/sch/i.html"

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._rate_limit_delay = 2.0  # Seconds between requests
        self._last_request_time = 0
        self._browser_lock = asyncio.Lock()

    async def _get_browser(self) -> Browser:
        """Get or create Playwright browser instance"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not installed. Run: pip install playwright && python -m playwright install chromium")

        async with self._browser_lock:
            if self._browser is None or not self._browser.is_connected():
                logger.info("Starting Playwright browser...")
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                    ]
                )
                logger.info("Playwright browser started successfully")
        return self._browser

    async def _rate_limit(self):
        """Implement rate limiting"""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < self._rate_limit_delay:
            await asyncio.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    def _build_search_url(
        self,
        query: str,
        category: str = None,
        sold_only: bool = True,
        min_price: float = None,
        max_price: float = None,
        condition: str = None
    ) -> str:
        """Build eBay search URL with filters"""
        params = {
            '_nkw': quote_plus(query),
            '_sacat': EBAY_CATEGORIES.get(category, '0'),  # 0 = All Categories
            '_sop': '13',  # Sort by price + shipping lowest first
        }

        if sold_only:
            params['LH_Sold'] = '1'
            params['LH_Complete'] = '1'

        if min_price:
            params['_udlo'] = str(min_price)
        if max_price:
            params['_udhi'] = str(max_price)

        # Build URL
        url = self.BASE_URL + '?' + '&'.join(f"{k}={v}" for k, v in params.items())
        return url

    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price from eBay listing text"""
        if not price_text:
            return None

        # Remove currency symbols and commas
        cleaned = re.sub(r'[^\d.]', '', price_text.replace(',', ''))

        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """Parse sale date from listing"""
        if not date_text:
            return None

        try:
            # eBay typically shows "Sold Jun 15, 2024" format
            date_match = re.search(r'Sold\s+(\w+\s+\d+,?\s*\d*)', date_text)
            if date_match:
                date_str = date_match.group(1)
                # Try various formats
                for fmt in ['%b %d, %Y', '%b %d %Y', '%B %d, %Y', '%B %d %Y']:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
            return None
        except Exception:
            return None

    def _extract_grade_from_title(self, title: str) -> Optional[float]:
        """Extract CGC/PSA grade from listing title"""
        # Look for CGC/PSA grade patterns
        patterns = [
            r'CGC\s*(\d+\.?\d*)',
            r'PSA\s*(\d+)',
            r'(\d+\.?\d*)\s*(?:CGC|PSA)',
            r'graded\s*(\d+\.?\d*)',
            r'grade\s*(\d+\.?\d*)',
        ]

        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                try:
                    grade = float(match.group(1))
                    if 0.5 <= grade <= 10.0:
                        return grade
                except (ValueError, TypeError):
                    continue

        return None

    def _extract_json_listings(self, html: str, target_grade: float = None) -> List[Dict[str, Any]]:
        """
        Extract listing data from embedded JSON in the page.
        eBay often embeds structured data that's more reliable than HTML scraping.
        """
        import json

        listings = []

        try:
            # Look for JSON-LD structured data
            json_ld_matches = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
            for match in json_ld_matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict):
                        if data.get('@type') == 'ItemList' and data.get('itemListElement'):
                            for item in data['itemListElement'][:30]:
                                if isinstance(item, dict):
                                    item_data = item.get('item', item)
                                    if item_data.get('name') and item_data.get('offers'):
                                        offer = item_data['offers']
                                        price = offer.get('price') or offer.get('lowPrice')
                                        if price:
                                            try:
                                                price = float(str(price).replace(',', ''))
                                                title = item_data.get('name', '')
                                                grade = self._extract_grade_from_title(title)

                                                if target_grade and grade:
                                                    if abs(grade - target_grade) > 1.5:
                                                        continue

                                                listings.append({
                                                    'title': title,
                                                    'price': price,
                                                    'shipping': 0,
                                                    'total_price': price,
                                                    'grade': grade,
                                                    'sale_date': None,
                                                    'url': item_data.get('url'),
                                                    'source': 'ebay',
                                                    'sale_type': 'sold'
                                                })
                                            except (ValueError, TypeError):
                                                continue
                except json.JSONDecodeError:
                    continue

            if listings:
                logger.info(f"Extracted {len(listings)} listings from JSON-LD data")
                return listings

            # Look for embedded __INITIAL_STATE__ or similar patterns
            state_patterns = [
                r'window\.__PRELOADED_STATE__\s*=\s*({.*?});',
                r'__INITIAL_STATE__\s*=\s*({.*?});',
                r'"itemSummaries"\s*:\s*(\[.*?\])',
                # eBay 2024/2025 patterns
                r'"listingInfo"\s*:\s*(\[.*?\])',
                r'"searchResults"\s*:\s*({.*?})\s*,\s*"pagination"',
            ]

            for pattern in state_patterns:
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        # Handle different data structures
                        if isinstance(data, list):
                            items = data
                        elif isinstance(data, dict):
                            items = (data.get('itemSummaries', []) or
                                    data.get('items', []) or
                                    data.get('results', []) or
                                    data.get('listingInfo', []))
                        else:
                            continue

                        for item in items[:30]:
                            if isinstance(item, dict):
                                title = item.get('title', '') or item.get('name', '')
                                price_data = item.get('price', {}) or item.get('sellingStatus', {}).get('currentPrice', {})
                                if isinstance(price_data, dict):
                                    price = price_data.get('value') or price_data.get('__value__')
                                elif isinstance(price_data, (int, float)):
                                    price = price_data
                                elif isinstance(price_data, str):
                                    price = self._parse_price(price_data)
                                else:
                                    continue

                                if price:
                                    try:
                                        price = float(str(price).replace(',', ''))
                                        grade = self._extract_grade_from_title(title)

                                        if target_grade and grade:
                                            if abs(grade - target_grade) > 1.5:
                                                continue

                                        listings.append({
                                            'title': title,
                                            'price': price,
                                            'shipping': 0,
                                            'total_price': price,
                                            'grade': grade,
                                            'sale_date': None,
                                            'url': item.get('itemWebUrl', item.get('url', item.get('viewItemURL'))),
                                            'source': 'ebay',
                                            'sale_type': 'sold'
                                        })
                                    except (ValueError, TypeError):
                                        continue
                    except json.JSONDecodeError:
                        continue

            if listings:
                logger.info(f"Extracted {len(listings)} listings from embedded JSON state")

        except Exception as e:
            logger.debug(f"Error extracting JSON listings: {e}")

        return listings

    async def search_sold_listings(
        self,
        query: str,
        category: str = None,
        target_grade: float = None,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search eBay sold listings using Playwright headless browser

        Args:
            query: Search query (e.g., "Amazing Spider-Man 300 CGC")
            category: Category type (comics, coins, etc.)
            target_grade: Target grade to filter results
            max_results: Maximum number of results to return

        Returns:
            List of sold listing data
        """
        await self._rate_limit()

        url = self._build_search_url(query, category, sold_only=True)
        logger.info(f"Searching eBay sold listings with Playwright: {query}")
        logger.info(f"URL: {url}")

        try:
            browser = await self._get_browser()
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
            )
            page = await context.new_page()

            # Navigate to eBay search page
            await page.goto(url, wait_until='networkidle', timeout=30000)

            # Wait for the search results to load
            try:
                await page.wait_for_selector('.srp-results, .s-item, [data-view="mi:1686|iid:1"]', timeout=10000)
            except Exception as e:
                logger.warning(f"Timeout waiting for search results selector: {e}")

            # Give extra time for JavaScript rendering
            await asyncio.sleep(2)

            # Get page HTML after JavaScript rendering
            html = await page.content()
            await context.close()

            soup = BeautifulSoup(html, 'html.parser')

            listings = []

            # Log page info for debugging
            logger.debug(f"eBay response length: {len(html)} chars")

            # Try to extract JSON data first (eBay often embeds this)
            json_listings = self._extract_json_listings(html, target_grade)
            if json_listings:
                logger.info(f"Extracted {len(json_listings)} listings from JSON data")
                return json_listings[:max_results]

            # Find listing items using multiple selector strategies
            # eBay 2024/2025 uses various item container classes
            item_selectors = [
                'li.s-item',
                '.s-item__wrapper',
                '.srp-results .s-item',
                '[data-viewport] .s-item',
                '.srp-river-results .s-item',
                '.srp-results li[data-view]',
                'ul.srp-results > li',
                '.b-list__items_nofooter li',
                'div[data-testid="search-result"]',
            ]

            items = []
            for selector in item_selectors:
                items = soup.select(selector)
                # Filter out placeholder items
                items = [i for i in items if not i.select_one('.s-item__pl-on-bottom')]
                if items and len(items) > 0:
                    logger.debug(f"Found {len(items)} items with selector: {selector}")
                    break

            if not items:
                # Try to find any element with item data
                logger.warning(f"No items found with standard selectors")
                # Debug: log page title and check for CAPTCHA/block
                title_elem = soup.select_one('title')
                if title_elem:
                    page_title = title_elem.get_text()
                    logger.info(f"eBay page title: {page_title}")
                    if 'security' in page_title.lower() or 'captcha' in page_title.lower():
                        logger.error("eBay returned CAPTCHA/security page - may be rate limited")
                # Log total number of elements for debugging
                all_items = soup.select('[class*="item"]')
                logger.info(f"Total elements with 'item' in class: {len(all_items)}")
                # Log some page content for debugging
                body = soup.select_one('body')
                if body:
                    # Check for specific eBay indicators
                    srp_main = soup.select_one('.srp-main')
                    logger.info(f"Found .srp-main: {srp_main is not None}")
                    srp_results = soup.select_one('.srp-results')
                    logger.info(f"Found .srp-results: {srp_results is not None}")
                    body_text = body.get_text()[:1000]
                    logger.debug(f"Page body preview: {body_text}")

            for item in items[:max_results * 2]:  # Get extra for filtering
                try:
                    # Skip ads/promotions
                    if item.select_one('.s-item__ad-badge, .SPONSORED, [data-testid="ad"]'):
                        continue

                    # Get title using multiple selectors (2024/2025 eBay structure)
                    title_elem = (
                        item.select_one('.s-item__title span[role="heading"]') or
                        item.select_one('.s-item__title') or
                        item.select_one('[data-testid="item-title"]') or
                        item.select_one('h3.s-item__title') or
                        item.select_one('h3') or
                        item.select_one('[role="heading"]') or
                        item.select_one('.lvtitle') or
                        item.select_one('a.s-item__link')
                    )
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)

                    # Skip placeholder items
                    if 'shop on ebay' in title.lower() or not title or title == '--':
                        continue

                    # Get price using multiple selectors (2024/2025 eBay structure)
                    price_elem = (
                        item.select_one('.s-item__price') or
                        item.select_one('[data-testid="item-price"]') or
                        item.select_one('.s-item__detail--primary .POSITIVE') or
                        item.select_one('.prc') or
                        item.select_one('[itemprop="price"]') or
                        item.select_one('.amt') or
                        item.select_one('span.POSITIVE')
                    )
                    if not price_elem:
                        continue
                    price_text = price_elem.get_text(strip=True)
                    # Handle price ranges (e.g., "$10.00 to $20.00")
                    if ' to ' in price_text:
                        # Take the first price
                        price_text = price_text.split(' to ')[0]
                    price = self._parse_price(price_text)
                    if not price or price < 1:
                        continue

                    # Get shipping cost
                    shipping_elem = item.select_one('.s-item__shipping, .s-item__freeXDays, .ship, [data-testid="item-shipping"]')
                    shipping_cost = 0.0
                    if shipping_elem:
                        shipping_text = shipping_elem.get_text(strip=True).lower()
                        if 'free' not in shipping_text:
                            shipping_cost = self._parse_price(shipping_text) or 0.0

                    # Get sale date (for sold items)
                    sold_elem = item.select_one('.s-item__title--tagblock, .s-item__caption, .BOLD, .s-item__endedDate, [data-testid="sold-date"]')
                    sale_date = self._parse_date(sold_elem.get_text() if sold_elem else '')

                    # Get URL
                    link_elem = item.select_one('.s-item__link, a[href*="/itm/"]')
                    item_url = link_elem.get('href') if link_elem else None

                    # Extract grade from title
                    grade = self._extract_grade_from_title(title)

                    # Filter by grade if target specified
                    if target_grade and grade:
                        grade_diff = abs(grade - target_grade)
                        if grade_diff > 1.5:  # Skip if grade difference too large
                            continue

                    listing_data = {
                        'title': title,
                        'price': price,
                        'shipping': shipping_cost,
                        'total_price': price + shipping_cost,
                        'grade': grade,
                        'sale_date': sale_date.isoformat() if sale_date else None,
                        'url': item_url,
                        'source': 'ebay',
                        'sale_type': 'sold'
                    }

                    listings.append(listing_data)

                    if len(listings) >= max_results:
                        break

                except Exception as e:
                    logger.debug(f"Error parsing listing: {e}")
                    continue

            # If still no listings, try regex extraction as last resort
            if not listings:
                listings = self._extract_listings_regex(html, target_grade)
                if listings:
                    logger.info(f"Extracted {len(listings)} listings via regex fallback")

            logger.info(f"Found {len(listings)} sold listings for '{query}'")
            return listings

        except Exception as e:
            logger.error(f"eBay scraping error: {e}")
            return []

    def _extract_listings_regex(self, html: str, target_grade: float = None) -> List[Dict[str, Any]]:
        """
        Fallback regex-based extraction when HTML structure parsing fails.
        Extracts listing data from raw HTML using patterns.
        """
        listings = []

        try:
            # Pattern to match eBay item blocks - look for title and price patterns
            # eBay often has patterns like: title in <span role="heading"> and price in class="s-item__price"

            # Find all potential listing blocks between item markers
            item_patterns = [
                # Look for itm/ URLs followed by title and price
                r'href="https://www\.ebay\.com/itm/[^"]+[^>]*>([^<]+)</a>.*?\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
                # Alternative pattern for sold items
                r'role="heading"[^>]*>([^<]+)</span>.*?class="s-item__price"[^>]*>\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
            ]

            for pattern in item_patterns:
                matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
                for match in matches[:30]:
                    title = match[0].strip() if len(match) > 0 else ''
                    price_str = match[1].replace(',', '') if len(match) > 1 else '0'

                    # Skip placeholder/ad items
                    if not title or 'shop on ebay' in title.lower():
                        continue

                    try:
                        price = float(price_str)
                        if price < 1:
                            continue

                        grade = self._extract_grade_from_title(title)

                        # Filter by grade if target specified
                        if target_grade and grade:
                            if abs(grade - target_grade) > 1.5:
                                continue

                        listings.append({
                            'title': title,
                            'price': price,
                            'shipping': 0,
                            'total_price': price,
                            'grade': grade,
                            'sale_date': None,
                            'url': None,
                            'source': 'ebay',
                            'sale_type': 'sold'
                        })
                    except (ValueError, TypeError):
                        continue

                if listings:
                    break

        except Exception as e:
            logger.debug(f"Regex extraction failed: {e}")

        return listings[:20]  # Limit results

    async def get_price_analysis(
        self,
        query: str,
        category: str = None,
        target_grade: float = None
    ) -> Dict[str, Any]:
        """
        Get price analysis from sold listings

        Returns:
            Dictionary with price statistics and confidence score
        """
        listings = await self.search_sold_listings(
            query, category, target_grade, max_results=30
        )

        if not listings:
            return {
                'price': None,
                'confidence': 0,
                'error': 'No sold listings found',
                'listings_count': 0
            }

        # Calculate statistics
        prices = [l['total_price'] for l in listings]
        grades = [l['grade'] for l in listings if l['grade']]

        avg_price = mean(prices)
        med_price = median(prices)
        min_price = min(prices)
        max_price = max(prices)

        # Calculate confidence based on:
        # - Number of listings found
        # - Price consistency (lower std dev = higher confidence)
        # - Grade match accuracy

        confidence = min(1.0, len(listings) / 15)  # Max 1.0 at 15+ listings

        if len(prices) > 1:
            from statistics import stdev
            price_std = stdev(prices)
            price_cv = price_std / avg_price if avg_price > 0 else 1
            # Lower CV = more consistent = higher confidence
            consistency_factor = max(0.5, 1 - min(price_cv, 0.5))
            confidence *= consistency_factor

        # Grade match bonus
        if target_grade and grades:
            grade_diffs = [abs(g - target_grade) for g in grades]
            avg_diff = mean(grade_diffs)
            grade_factor = max(0.7, 1 - (avg_diff * 0.1))
            confidence *= grade_factor

        return {
            'price': round(med_price, 2),  # Use median for robustness
            'average_price': round(avg_price, 2),
            'median_price': round(med_price, 2),
            'min_price': round(min_price, 2),
            'max_price': round(max_price, 2),
            'grade_matched': round(mean(grades), 1) if grades else None,
            'confidence': round(confidence, 3),
            'listings_count': len(listings),
            'sale_type': 'auction',
            'source': 'ebay',
            'recent_sales': listings[:5]  # Include top 5 recent sales
        }

    async def close(self):
        """Close the Playwright browser"""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None


# Global scraper instance
_scraper: Optional[EbayScraper] = None


def _get_scraper() -> EbayScraper:
    """Get or create global scraper instance"""
    global _scraper
    if _scraper is None:
        _scraper = EbayScraper()
    return _scraper


async def fetch_ebay_price(
    title: str,
    issue_number: Optional[str] = None,
    grade: float = 8.0,
    category: str = 'comics'
) -> Dict[str, Any]:
    """
    Fetch eBay sold price for a collectible

    Args:
        title: Item title (e.g., "Amazing Spider-Man")
        issue_number: Issue number for comics/magazines
        grade: Target grade
        category: Category type

    Returns:
        Price data dictionary
    """
    scraper = _get_scraper()

    # Try multiple search strategies with fallback
    search_queries = []

    # Strategy 1: Graded search (CGC/CBCS)
    query_parts = [title]
    if issue_number and issue_number not in ['??', 'Unknown', None]:
        query_parts.append(f"#{issue_number}")
    if grade and grade >= 8.0:
        search_queries.append(' '.join(query_parts + [f"CGC {grade}"]))
    elif grade:
        search_queries.append(' '.join(query_parts + ["CGC"]))

    # Strategy 2: Just title and issue (raw comics)
    if issue_number and issue_number not in ['??', 'Unknown', None]:
        search_queries.append(f"{title} #{issue_number}")

    # Strategy 3: Just title (broader search)
    search_queries.append(title)

    # Try each search strategy until we get results
    for query in search_queries:
        try:
            logger.info(f"Trying eBay search: {query}")
            result = await scraper.get_price_analysis(query, category, grade)
            if result and result.get('listings_count', 0) > 0:
                logger.info(f"Found {result.get('listings_count')} listings with query: {query}")
                return result
        except Exception as e:
            logger.debug(f"Search failed for '{query}': {e}")
            continue

    # No results from any strategy
    logger.warning(f"No eBay listings found for any search strategy")
    return {
        'price': None,
        'confidence': 0,
        'error': 'No sold listings found',
        'listings_count': 0,
        'source': 'ebay'
    }


async def fetch_ebay_sold_listings(
    query: str,
    category: str = None,
    grade: float = None,
    max_results: int = 20
) -> List[Dict[str, Any]]:
    """
    Fetch raw sold listings from eBay

    Args:
        query: Search query
        category: Category type
        grade: Target grade filter
        max_results: Max listings to return

    Returns:
        List of sold listing data
    """
    scraper = _get_scraper()
    return await scraper.search_sold_listings(query, category, grade, max_results)


# Cleanup on module unload
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


# ===== SWARM BRAIN WRAPPER FUNCTIONS =====
# These functions are called by the swarm brain orchestrator

async def search_ebay_sold(query: str, grade: float = None, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Wrapper for swarm brain - search eBay sold listings.

    Args:
        query: Search query (e.g., "Amazing Spider-Man #300 CGC 9.8")
        grade: Optional grade filter
        max_results: Maximum results to return

    Returns:
        List of sold listing data
    """
    return await fetch_ebay_sold_listings(query, 'comics', grade, max_results)


async def search_ebay_listings(query: str, grade: float = None, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Search eBay active/current listings (not sold).

    Args:
        query: Search query
        grade: Optional grade filter
        max_results: Maximum results to return

    Returns:
        List of active listing data
    """
    scraper = _get_scraper()
    await scraper._rate_limit()

    # Build URL without sold_only filter
    url = scraper._build_search_url(query, 'comics', sold_only=False)
    logger.info(f"Searching eBay active listings: {query}")

    try:
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not available for eBay scraping")
            return []

        browser = await scraper._get_browser()
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
        )
        page = await context.new_page()

        await page.goto(url, wait_until='networkidle', timeout=30000)

        try:
            await page.wait_for_selector('.srp-results, .s-item', timeout=10000)
        except Exception:
            pass

        await asyncio.sleep(2)
        html = await page.content()
        await context.close()

        soup = BeautifulSoup(html, 'html.parser')
        listings = []

        # Try JSON extraction first
        json_listings = scraper._extract_json_listings(html, grade)
        if json_listings:
            # Mark as active listings
            for listing in json_listings:
                listing['sale_type'] = 'listed'
            return json_listings[:max_results]

        # HTML parsing fallback
        item_selectors = [
            'li.s-item',
            '.s-item__wrapper',
            '.srp-results .s-item',
        ]

        items = []
        for selector in item_selectors:
            items = soup.select(selector)
            items = [i for i in items if not i.select_one('.s-item__pl-on-bottom')]
            if items:
                break

        for item in items[:max_results * 2]:
            try:
                if item.select_one('.s-item__ad-badge, .SPONSORED'):
                    continue

                title_elem = (
                    item.select_one('.s-item__title span[role="heading"]') or
                    item.select_one('.s-item__title') or
                    item.select_one('h3')
                )
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)

                if 'shop on ebay' in title.lower() or not title:
                    continue

                price_elem = (
                    item.select_one('.s-item__price') or
                    item.select_one('[data-testid="item-price"]')
                )
                if not price_elem:
                    continue
                price_text = price_elem.get_text(strip=True)
                if ' to ' in price_text:
                    price_text = price_text.split(' to ')[0]
                price = scraper._parse_price(price_text)
                if not price or price < 1:
                    continue

                # Shipping
                shipping_elem = item.select_one('.s-item__shipping, .s-item__freeXDays')
                shipping_cost = 0.0
                if shipping_elem:
                    shipping_text = shipping_elem.get_text(strip=True).lower()
                    if 'free' not in shipping_text:
                        shipping_cost = scraper._parse_price(shipping_text) or 0.0

                # URL
                link_elem = item.select_one('.s-item__link, a[href*="/itm/"]')
                item_url = link_elem.get('href') if link_elem else None

                # Grade
                item_grade = scraper._extract_grade_from_title(title)

                if grade and item_grade:
                    if abs(item_grade - grade) > 1.5:
                        continue

                listings.append({
                    'title': title,
                    'price': price,
                    'shipping': shipping_cost,
                    'total_price': price + shipping_cost,
                    'grade': item_grade,
                    'url': item_url,
                    'source': 'ebay',
                    'sale_type': 'listed'
                })

                if len(listings) >= max_results:
                    break

            except Exception as e:
                logger.debug(f"Error parsing active listing: {e}")
                continue

        logger.info(f"Found {len(listings)} active listings for '{query}'")
        return listings

    except Exception as e:
        logger.error(f"eBay active listings error: {e}")
        return []
