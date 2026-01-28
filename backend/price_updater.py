"""
Live Price Updater - Automated Market Price Updates
Runs several times daily to update pricing for all comics in the catalog.

Sources:
- eBay Sold Listings (historical avg)
- eBay Active Listings (current market)
- CGC Census/Price Guide data

Each comic displays:
- CGC Graded Price (at current grade)
- Historical Sold Avg (eBay completed sales)
- Current Market Avg (eBay active listings)
"""

import asyncio
import aiohttp
import json
import logging
import os
import re
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from urllib.parse import quote_plus
import random

# Load environment
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        load_dotenv(env_file, override=True)
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Database path
DB_PATH = "P:/SOVEREIGN_APPS/collectibles_grading_system/collectibles.db"

# Update schedule (hours)
UPDATE_INTERVAL_HOURS = 6  # Run every 6 hours

# Rate limiting
REQUESTS_PER_MINUTE = 30
REQUEST_DELAY = 60 / REQUESTS_PER_MINUTE


class EbayPriceScraper:
    """Scrapes eBay for comic book prices (sold and active listings)"""

    # eBay API-like endpoints (using browse API or scraping)
    EBAY_SEARCH_URL = "https://www.ebay.com/sch/i.html"

    # Headers to mimic browser
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }

    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.HEADERS)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def build_search_query(self, title: str, issue: str, grade: float = None, graded: bool = True) -> str:
        """Build eBay search query for a comic"""
        # Clean up title
        title = re.sub(r'[^\w\s]', '', title)

        query_parts = [title]
        if issue:
            query_parts.append(f"#{issue}")

        if graded and grade:
            # Search for CGC graded copies at similar grade
            grade_str = f"{grade:.1f}"
            query_parts.append(f"CGC {grade_str}")

        return ' '.join(query_parts)

    async def get_sold_listings(self, title: str, issue: str, grade: float = None) -> Dict[str, Any]:
        """Get completed/sold listings from eBay"""
        try:
            query = self.build_search_query(title, issue, grade, graded=True)

            params = {
                '_nkw': query,
                '_sacat': '63',  # Comic Books category
                'LH_Complete': '1',  # Completed listings
                'LH_Sold': '1',  # Sold only
                '_sop': '13',  # Sort by end date recent
                'rt': 'nc',
            }

            url = f"{self.EBAY_SEARCH_URL}?{'&'.join(f'{k}={quote_plus(str(v))}' for k, v in params.items())}"

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    return self._parse_sold_listings(html)
                else:
                    logger.warning(f"eBay sold listings request failed: {resp.status}")
                    return {'error': f"HTTP {resp.status}"}

        except Exception as e:
            logger.error(f"Error fetching eBay sold listings: {e}")
            return {'error': str(e)}

    async def get_active_listings(self, title: str, issue: str, grade: float = None) -> Dict[str, Any]:
        """Get current active listings from eBay"""
        try:
            query = self.build_search_query(title, issue, grade, graded=True)

            params = {
                '_nkw': query,
                '_sacat': '63',  # Comic Books category
                'LH_BIN': '1',  # Buy It Now only for better price accuracy
                '_sop': '15',  # Sort by price + shipping lowest first
                'rt': 'nc',
            }

            url = f"{self.EBAY_SEARCH_URL}?{'&'.join(f'{k}={quote_plus(str(v))}' for k, v in params.items())}"

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    return self._parse_active_listings(html)
                else:
                    logger.warning(f"eBay active listings request failed: {resp.status}")
                    return {'error': f"HTTP {resp.status}"}

        except Exception as e:
            logger.error(f"Error fetching eBay active listings: {e}")
            return {'error': str(e)}

    def _parse_sold_listings(self, html: str) -> Dict[str, Any]:
        """Parse sold listings from eBay HTML"""
        prices = []

        # Pattern to find sold prices
        # eBay uses various formats, try multiple patterns
        patterns = [
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $123.45 or $1,234.56
            r'US \$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # US $123.45
        ]

        # Look for sold price indicators
        sold_sections = re.findall(r's-item__price[^>]*>([^<]+)</span>', html)

        for section in sold_sections[:20]:  # Limit to first 20 results
            for pattern in patterns:
                match = re.search(pattern, section)
                if match:
                    price_str = match.group(1).replace(',', '')
                    try:
                        price = float(price_str)
                        if 1 <= price <= 100000:  # Sanity check
                            prices.append(price)
                            break
                    except ValueError:
                        continue

        if prices:
            return {
                'sold_count': len(prices),
                'avg_sold_price': round(sum(prices) / len(prices), 2),
                'min_sold_price': min(prices),
                'max_sold_price': max(prices),
                'median_sold_price': round(sorted(prices)[len(prices) // 2], 2),
                'prices': prices[:10],  # Store up to 10 recent prices
                'updated_at': datetime.utcnow().isoformat()
            }

        return {
            'sold_count': 0,
            'avg_sold_price': None,
            'error': 'No sold listings found',
            'updated_at': datetime.utcnow().isoformat()
        }

    def _parse_active_listings(self, html: str) -> Dict[str, Any]:
        """Parse active listings from eBay HTML"""
        prices = []

        patterns = [
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'US \$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        ]

        # Look for BIN prices
        price_sections = re.findall(r's-item__price[^>]*>([^<]+)</span>', html)

        for section in price_sections[:20]:
            for pattern in patterns:
                match = re.search(pattern, section)
                if match:
                    price_str = match.group(1).replace(',', '')
                    try:
                        price = float(price_str)
                        if 1 <= price <= 100000:
                            prices.append(price)
                            break
                    except ValueError:
                        continue

        if prices:
            return {
                'listing_count': len(prices),
                'avg_asking_price': round(sum(prices) / len(prices), 2),
                'min_asking_price': min(prices),
                'max_asking_price': max(prices),
                'median_asking_price': round(sorted(prices)[len(prices) // 2], 2),
                'prices': prices[:10],
                'updated_at': datetime.utcnow().isoformat()
            }

        return {
            'listing_count': 0,
            'avg_asking_price': None,
            'error': 'No active listings found',
            'updated_at': datetime.utcnow().isoformat()
        }


class CGCPriceGuide:
    """Fetch CGC price guide data"""

    # CGC doesn't have a public API, but we can estimate based on grade
    # These are approximate multipliers based on grade for typical comics
    GRADE_MULTIPLIERS = {
        10.0: 50.0,   # Gem Mint - extremely rare
        9.9: 25.0,    # Mint
        9.8: 10.0,    # Near Mint/Mint - highly desirable
        9.6: 5.0,     # Near Mint+
        9.4: 3.5,     # Near Mint
        9.2: 2.5,     # Near Mint-
        9.0: 2.0,     # VF/NM
        8.5: 1.5,     # VF+
        8.0: 1.25,    # VF
        7.5: 1.1,     # VF-
        7.0: 1.0,     # F/VF - Base grade
        6.5: 0.85,    # F+
        6.0: 0.75,    # F
        5.5: 0.65,    # F-
        5.0: 0.55,    # VG/F
        4.5: 0.45,    # VG+
        4.0: 0.35,    # VG
        3.5: 0.28,    # VG-
        3.0: 0.22,    # G/VG
        2.5: 0.18,    # G+
        2.0: 0.15,    # G
        1.8: 0.12,    # G-
        1.5: 0.10,    # F/G
        1.0: 0.08,    # Fair
        0.5: 0.05,    # Poor
    }

    # Base values for common comics (can be overridden by market data)
    DEFAULT_BASE_VALUE = 25.0  # Base value for a 7.0 grade

    @classmethod
    def estimate_graded_value(cls, grade: float, base_value: float = None) -> float:
        """Estimate CGC graded value based on grade"""
        if base_value is None:
            base_value = cls.DEFAULT_BASE_VALUE

        # Find closest grade multiplier
        grades = sorted(cls.GRADE_MULTIPLIERS.keys())
        closest_grade = min(grades, key=lambda x: abs(x - grade))
        multiplier = cls.GRADE_MULTIPLIERS[closest_grade]

        # Add premium for slabbing ($25-50 typical)
        slabbing_premium = 30.0

        return round((base_value * multiplier) + slabbing_premium, 2)

    @classmethod
    def get_grade_label(cls, grade: float) -> str:
        """Get CGC grade label"""
        labels = {
            10.0: "Gem Mint", 9.9: "Mint", 9.8: "Near Mint/Mint",
            9.6: "Near Mint+", 9.4: "Near Mint", 9.2: "Near Mint-",
            9.0: "Very Fine/Near Mint", 8.5: "Very Fine+", 8.0: "Very Fine",
            7.5: "Very Fine-", 7.0: "Fine/Very Fine", 6.5: "Fine+",
            6.0: "Fine", 5.5: "Fine-", 5.0: "Very Good/Fine",
            4.5: "Very Good+", 4.0: "Very Good", 3.5: "Very Good-",
            3.0: "Good/Very Good", 2.5: "Good+", 2.0: "Good",
            1.8: "Good-", 1.5: "Fair/Good", 1.0: "Fair", 0.5: "Poor"
        }
        closest = min(labels.keys(), key=lambda x: abs(x - grade))
        return labels[closest]


class PriceUpdateScheduler:
    """Manages scheduled price updates for the catalog"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.is_running = False
        self.last_run = None
        self.stats = {
            'total_updated': 0,
            'successful': 0,
            'failed': 0,
            'last_run': None,
            'next_run': None
        }

    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_comics_needing_update(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get comics that need price updates (oldest first)"""
        conn = self.get_connection()
        c = conn.cursor()

        # Get comics with grades, ordered by last_priced (oldest first) or NULL first
        c.execute('''
            SELECT id, title, issue_number, publisher, publication_year,
                   consensus_grade, consensus_price, last_priced,
                   ebay_price_data, gpa_price_data
            FROM comics
            WHERE consensus_grade IS NOT NULL
            AND title IS NOT NULL
            ORDER BY
                CASE WHEN last_priced IS NULL THEN 0 ELSE 1 END,
                last_priced ASC
            LIMIT ?
        ''', (limit,))

        comics = [dict(row) for row in c.fetchall()]
        conn.close()
        return comics

    def save_pricing_data(self, comic_id: int, pricing_data: Dict[str, Any]) -> bool:
        """Save updated pricing data to database"""
        conn = self.get_connection()
        c = conn.cursor()

        try:
            # Calculate consensus price from available data
            prices = []

            if pricing_data.get('ebay_sold', {}).get('avg_sold_price'):
                prices.append(pricing_data['ebay_sold']['avg_sold_price'])

            if pricing_data.get('ebay_active', {}).get('avg_asking_price'):
                # Active listings are usually higher, weight them less
                prices.append(pricing_data['ebay_active']['avg_asking_price'] * 0.85)

            if pricing_data.get('cgc_estimate'):
                prices.append(pricing_data['cgc_estimate'])

            consensus_price = round(sum(prices) / len(prices), 2) if prices else None

            # Determine price range
            all_prices = []
            if 'ebay_sold' in pricing_data and pricing_data['ebay_sold'].get('prices'):
                all_prices.extend(pricing_data['ebay_sold']['prices'])
            if 'ebay_active' in pricing_data and pricing_data['ebay_active'].get('prices'):
                all_prices.extend(pricing_data['ebay_active']['prices'])

            price_range_low = min(all_prices) if all_prices else None
            price_range_high = max(all_prices) if all_prices else None

            # Determine market trend based on sold vs asking
            market_trend = 'stable'
            if (pricing_data.get('ebay_sold', {}).get('avg_sold_price') and
                pricing_data.get('ebay_active', {}).get('avg_asking_price')):
                sold_avg = pricing_data['ebay_sold']['avg_sold_price']
                asking_avg = pricing_data['ebay_active']['avg_asking_price']
                diff_pct = ((asking_avg - sold_avg) / sold_avg) * 100
                if diff_pct > 15:
                    market_trend = 'rising'
                elif diff_pct < -10:
                    market_trend = 'falling'

            c.execute('''
                UPDATE comics SET
                    consensus_price = ?,
                    price_range_low = ?,
                    price_range_high = ?,
                    ebay_price_data = ?,
                    pricing_confidence = ?,
                    market_trend = ?,
                    last_priced = ?,
                    last_modified = ?
                WHERE id = ?
            ''', (
                consensus_price,
                price_range_low,
                price_range_high,
                json.dumps(pricing_data),
                0.8 if len(prices) >= 2 else 0.5,
                market_trend,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
                comic_id
            ))

            # Add to pricing history
            c.execute('''
                INSERT INTO pricing_history (comic_id, price_data)
                VALUES (?, ?)
            ''', (comic_id, json.dumps({
                'consensus_price': consensus_price,
                **pricing_data,
                'timestamp': datetime.utcnow().isoformat()
            })))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error saving pricing data for comic {comic_id}: {e}")
            conn.close()
            return False

    async def update_comic_prices(self, comic: Dict[str, Any]) -> Dict[str, Any]:
        """Update prices for a single comic"""
        title = comic.get('title', '')
        issue = comic.get('issue_number', '')
        grade = comic.get('consensus_grade', 7.0)

        pricing_data = {
            'comic_id': comic['id'],
            'title': title,
            'issue': issue,
            'grade': grade,
            'updated_at': datetime.utcnow().isoformat()
        }

        async with EbayPriceScraper() as scraper:
            # Get eBay sold listings
            await asyncio.sleep(REQUEST_DELAY)  # Rate limiting
            sold_data = await scraper.get_sold_listings(title, issue, grade)
            pricing_data['ebay_sold'] = sold_data

            # Get eBay active listings
            await asyncio.sleep(REQUEST_DELAY)
            active_data = await scraper.get_active_listings(title, issue, grade)
            pricing_data['ebay_active'] = active_data

        # Get CGC price estimate
        base_value = sold_data.get('avg_sold_price') or active_data.get('avg_asking_price') or 25.0
        pricing_data['cgc_estimate'] = CGCPriceGuide.estimate_graded_value(grade, base_value / CGCPriceGuide.GRADE_MULTIPLIERS.get(7.0, 1.0))

        return pricing_data

    async def run_update_cycle(self, batch_size: int = 50):
        """Run a full price update cycle"""
        if self.is_running:
            logger.warning("Price update already running, skipping")
            return

        self.is_running = True
        self.stats['last_run'] = datetime.utcnow().isoformat()

        try:
            logger.info("Starting price update cycle...")

            comics = self.get_comics_needing_update(limit=batch_size)
            logger.info(f"Found {len(comics)} comics to update")

            for comic in comics:
                try:
                    logger.info(f"Updating prices for: {comic['title']} #{comic.get('issue_number', '?')}")

                    pricing_data = await self.update_comic_prices(comic)

                    if self.save_pricing_data(comic['id'], pricing_data):
                        self.stats['successful'] += 1
                        self.stats['total_updated'] += 1

                        price = pricing_data.get('ebay_sold', {}).get('avg_sold_price') or pricing_data.get('cgc_estimate')
                        logger.info(f"  -> Price updated: ${price:.2f}" if price else "  -> No price data available")
                    else:
                        self.stats['failed'] += 1

                except Exception as e:
                    logger.error(f"Error updating comic {comic['id']}: {e}")
                    self.stats['failed'] += 1

                # Small delay between comics
                await asyncio.sleep(0.5)

            self.stats['next_run'] = (datetime.utcnow() + timedelta(hours=UPDATE_INTERVAL_HOURS)).isoformat()
            logger.info(f"Price update cycle complete. Updated: {self.stats['successful']}, Failed: {self.stats['failed']}")

        finally:
            self.is_running = False

    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        return {
            'is_running': self.is_running,
            'stats': self.stats,
            'update_interval_hours': UPDATE_INTERVAL_HOURS
        }


# Global scheduler instance
price_scheduler = PriceUpdateScheduler()


async def run_price_updates(batch_size: int = 50):
    """Run price updates (called by scheduler or API)"""
    await price_scheduler.run_update_cycle(batch_size)


def get_price_scheduler_status() -> Dict[str, Any]:
    """Get scheduler status"""
    return price_scheduler.get_status()


# Background task for continuous updates
async def background_price_updater():
    """Background task that runs price updates on schedule"""
    logger.info(f"Starting background price updater (interval: {UPDATE_INTERVAL_HOURS}h)")

    while True:
        try:
            await run_price_updates(batch_size=100)
        except Exception as e:
            logger.error(f"Background price update error: {e}")

        # Wait for next cycle
        await asyncio.sleep(UPDATE_INTERVAL_HOURS * 3600)


if __name__ == "__main__":
    # Test run
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_price_updates(batch_size=10))
