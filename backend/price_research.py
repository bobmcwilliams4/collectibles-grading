"""
Price Research Service - Python Edition
Searches external marketplaces (eBay, PriceCharting) for sold listings
to determine fair market value and prevent price gouging.

Features:
- eBay Finding API integration (completed/sold items)
- PriceCharting API for video games/systems
- Automatic price ceiling calculation (1.5x avg)
- Recent sales comparison data
- Retry logic with exponential backoff
- Error handling with graceful degradation

Synced from: P:/SOVEREIGN_APPS/website/lib/price-research.ts
Author: CLAUDE_SECONDARY
Date: 2026-01-06
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import statistics
from pathlib import Path
from loguru import logger

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    logger.warning("httpx not installed. Install: pip install httpx")
    HTTPX_AVAILABLE = False

from .types import (
    MarketResearch,
    EbaySale,
    RecentSale,
    ItemType
)


# ============================================================================
# CONFIGURATION
# ============================================================================

EBAY_FINDING_API_URL = 'https://svcs.ebay.com/services/search/FindingService/v1'
PRICECHARTING_API_URL = 'https://www.pricecharting.com/api/product'

# Load API keys from environment or vault
def _load_api_keys():
    """Load API keys from environment variables or vault"""
    vault_path = Path("O:/ECHO_OMEGA_PRIME/.promethian_vault")

    ebay_app_id = os.getenv('EBAY_APP_ID')
    pricecharting_key = os.getenv('PRICECHARTING_API_KEY')

    # Try vault if env vars not set
    if not pricecharting_key and vault_path.exists():
        try:
            key_file = vault_path / "pricecharting_api_key.txt"
            if key_file.exists():
                pricecharting_key = key_file.read_text().strip()
        except Exception as e:
            logger.warning(f"Failed to read PriceCharting key from vault: {e}")

    return ebay_app_id, pricecharting_key

EBAY_APP_ID, PRICECHARTING_API_KEY = _load_api_keys()

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_MS = 1000

# Price ceiling multiplier
PRICE_CEILING_MULTIPLIER = 1.5


# ============================================================================
# MAIN RESEARCH FUNCTION
# ============================================================================

async def research_market_price(
    item_title: str,
    item_type: ItemType,
    year: Optional[int] = None
) -> MarketResearch:
    """
    Research market price for an item by searching external APIs

    Args:
        item_title: Item title to search for
        item_type: Type of item (for PriceCharting routing)
        year: Publication/release year (optional, improves search accuracy)

    Returns:
        Market research data with average prices and recent sales
    """
    if not HTTPX_AVAILABLE:
        logger.error("httpx not installed, cannot perform price research")
        return MarketResearch()

    results = MarketResearch(
        ebay_avg_sold=0.0,
        ebay_recent_sales=[],
        data_sources=[],
        last_updated=datetime.utcnow()
    )

    # 1. Search eBay for completed/sold listings
    try:
        logger.info(f"Searching eBay for: {item_title}")
        ebay_results = await search_ebay_sold(item_title, year)

        if ebay_results:
            results.ebay_avg_sold = calculate_average([r.price for r in ebay_results])
            results.ebay_recent_sales = ebay_results[:10]  # Top 10 most recent
            results.data_sources.append('ebay')
            logger.success(f"eBay found {len(ebay_results)} sold items, avg: ${results.ebay_avg_sold}")
        else:
            logger.info(f"eBay found no sold items for: {item_title}")
    except Exception as e:
        logger.error(f"eBay search failed: {e}")
        # Continue - eBay failure shouldn't block other sources

    # 2. Search PriceCharting (for games/systems only)
    if item_type in [ItemType.VIDEO_GAME, ItemType.GAMING_SYSTEM]:
        try:
            logger.info(f"Searching PriceCharting for: {item_title}")
            pc_result = await search_price_charting(item_title)

            if pc_result:
                results.price_charting_value = pc_result.get('loose_price') or pc_result.get('cib_price')
                results.data_sources.append('pricecharting')
                logger.success(f"PriceCharting value: ${results.price_charting_value}")
            else:
                logger.info(f"PriceCharting found no data for: {item_title}")
        except Exception as e:
            logger.error(f"PriceCharting search failed: {e}")
            # Continue - graceful degradation

    # 3. Calculate suggested max price (1.5x average)
    avg_price = results.ebay_avg_sold or results.price_charting_value or 0.0
    results.suggested_max_price = calculate_suggested_max_price(avg_price)

    logger.info(f"Final results: avg=${avg_price}, suggested_max=${results.suggested_max_price}")

    return results


# ============================================================================
# EBAY FINDING API
# ============================================================================

async def search_ebay_sold(title: str, year: Optional[int] = None) -> List[EbaySale]:
    """
    Search eBay for completed/sold items

    Uses eBay Finding API findCompletedItems operation with SoldItemsOnly filter

    Args:
        title: Item title to search
        year: Optional year to improve search accuracy

    Returns:
        List of sold items with prices
    """
    if not EBAY_APP_ID:
        logger.warning("EBAY_APP_ID not set, skipping eBay search")
        return []

    search_query = f"{title} {year}" if year else title

    params = {
        'OPERATION-NAME': 'findCompletedItems',
        'SERVICE-VERSION': '1.0.0',
        'SECURITY-APPNAME': EBAY_APP_ID,
        'RESPONSE-DATA-FORMAT': 'JSON',
        'REST-PAYLOAD': 'true',
        'keywords': search_query,
        'itemFilter(0).name': 'SoldItemsOnly',
        'itemFilter(0).value': 'true',
        'itemFilter(1).name': 'Condition',
        'itemFilter(1).value': 'Used',
        'sortOrder': 'EndTimeSoonest',
        'paginationInput.entriesPerPage': '100'
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await retry_request(
                lambda: client.get(EBAY_FINDING_API_URL, params=params)
            )

        data = response.json()
        items = data.get('findCompletedItemsResponse', [{}])[0] \
                    .get('searchResult', [{}])[0] \
                    .get('item', [])

        sales = []
        for item in items:
            try:
                sale = EbaySale(
                    title=item['title'][0],
                    price=float(item['sellingStatus'][0]['currentPrice'][0]['__value__']),
                    sold_date=item['listingInfo'][0]['endTime'][0],
                    condition=item.get('condition', [{}])[0].get('conditionDisplayName', [None])[0],
                    url=item['viewItemURL'][0]
                )
                sales.append(sale)
            except (KeyError, IndexError, ValueError) as e:
                logger.debug(f"Failed to parse eBay item: {e}")
                continue

        return sales
    except Exception as e:
        logger.error(f"eBay API error: {e}")
        return []


# ============================================================================
# PRICECHARTING API
# ============================================================================

async def search_price_charting(title: str) -> Optional[Dict[str, float]]:
    """
    Search PriceCharting for video game/system pricing

    Args:
        title: Game or system title

    Returns:
        Dict with loose_price, cib_price, new_price or None if not found
    """
    if not PRICECHARTING_API_KEY:
        logger.warning("PRICECHARTING_API_KEY not set, skipping PriceCharting search")
        return None

    params = {
        't': PRICECHARTING_API_KEY,
        'q': title
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await retry_request(
                lambda: client.get(PRICECHARTING_API_URL, params=params)
            )

        data = response.json()
        products = data.get('products', [])

        if not products:
            return None

        # Take first result (most relevant)
        product = products[0]

        return {
            'loose_price': float(product.get('loose-price', 0) or 0),
            'cib_price': float(product.get('cib-price', 0) or 0),
            'new_price': float(product.get('new-price', 0) or 0)
        }
    except Exception as e:
        logger.error(f"PriceCharting API error: {e}")
        return None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def calculate_average(prices: List[float]) -> float:
    """
    Calculate average of an array of prices, filtering outliers

    Outliers are defined as prices > 3x median or < 0.33x median
    """
    if not prices:
        return 0.0

    # Filter out outliers
    sorted_prices = sorted(prices)
    median = statistics.median(sorted_prices)

    filtered = [p for p in prices if median * 0.33 <= p <= median * 3]

    if not filtered:
        return 0.0

    return round(sum(filtered) / len(filtered), 2)


def calculate_suggested_max_price(market_avg: float) -> float:
    """Calculate suggested max price (1.5x market average)"""
    return round(market_avg * PRICE_CEILING_MULTIPLIER, 2)


async def retry_request(request_fn, retries: int = MAX_RETRIES):
    """
    Retry a request with exponential backoff

    Args:
        request_fn: Async function that returns httpx.Response
        retries: Number of retry attempts

    Returns:
        httpx.Response

    Raises:
        Last exception if all retries fail
    """
    last_error = None

    for i in range(retries):
        try:
            return await request_fn()
        except Exception as e:
            last_error = e

            if i < retries - 1:
                delay = (RETRY_DELAY_MS / 1000) * (2 ** i)  # Exponential backoff
                logger.warning(f"Request failed, retrying in {delay}s...")
                await asyncio.sleep(delay)

    raise last_error


# ============================================================================
# PRICE VERIFICATION HELPERS
# ============================================================================

def verify_price(proposed_price: float, market_research: MarketResearch) -> Dict[str, Any]:
    """
    Verify if a user's proposed price is reasonable

    Args:
        proposed_price: User's asking price
        market_research: Market research data

    Returns:
        Dict with is_reasonable, price_delta, price_delta_percent, warning
    """
    market_avg = market_research.ebay_avg_sold or market_research.price_charting_value or 0.0

    if market_avg == 0:
        # No market data available - can't verify
        return {
            'is_reasonable': True,
            'price_delta': 0.0,
            'price_delta_percent': 0.0
        }

    price_delta = proposed_price - market_avg
    price_delta_percent = round((price_delta / market_avg) * 100)
    is_reasonable = abs(price_delta_percent) <= 50  # Within 50%

    warning = None

    if price_delta_percent > 50:
        warning = (
            f"Your price (${proposed_price}) is {price_delta_percent}% above market average (${market_avg}). "
            f"Consider pricing at ${market_research.suggested_max_price} or less for faster sales."
        )
    elif price_delta_percent < -50:
        warning = (
            f"Your price (${proposed_price}) is {abs(price_delta_percent)}% below market average (${market_avg}). "
            f"You may be undervaluing your item."
        )

    return {
        'is_reasonable': is_reasonable,
        'price_delta': price_delta,
        'price_delta_percent': price_delta_percent,
        'warning': warning
    }


def format_recent_sales(market_research: MarketResearch) -> List[RecentSale]:
    """Convert MarketResearch to RecentSale format for marketplace display"""
    sales: List[RecentSale] = []

    # Add eBay sales
    for sale in market_research.ebay_recent_sales:
        sales.append(RecentSale(
            title=sale.title,
            price=sale.price,
            sold_date=sale.sold_date,
            source='eBay',
            url=sale.url
        ))

    # Add PriceCharting data point (if available)
    if market_research.price_charting_value:
        sales.append(RecentSale(
            title='PriceCharting Average',
            price=market_research.price_charting_value,
            sold_date=datetime.utcnow().isoformat(),
            source='PriceCharting',
            url='https://www.pricecharting.com'
        ))

    return sales


# ============================================================================
# SYNC FUNCTIONS (for async compatibility with existing codebase)
# ============================================================================

def research_market_price_sync(
    item_title: str,
    item_type: ItemType,
    year: Optional[int] = None
) -> MarketResearch:
    """
    Synchronous wrapper for research_market_price

    For use in non-async contexts
    """
    return asyncio.run(research_market_price(item_title, item_type, year))
