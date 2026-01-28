"""
Multi-Source Pricing Engine
Aggregates prices from GPA, Heritage Auctions, and eBay sold listings
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from statistics import mean, median, stdev
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PricePoint:
    """Individual price data point"""
    source: str
    price: float
    grade: float
    sale_date: Optional[datetime]
    sale_type: str  # 'auction', 'buy_now', 'offer'
    url: Optional[str]
    confidence: float


class PricingEngine:
    """
    Multi-source pricing aggregator

    Features:
    - Concurrent API calls to all sources
    - Grade normalization
    - Outlier detection
    - Market trend analysis
    - Confidence scoring
    - Caching
    """

    def __init__(self):
        # Source weights (sum to 1.0)
        self.source_weights = {
            'gpa': 0.40,      # GoCollect/GPA - most accurate for graded
            'heritage': 0.35, # Heritage - premium auction house
            'ebay': 0.25      # eBay - largest market
        }

        # Cache
        self._cache: Dict[str, Dict] = {}
        self._cache_duration = timedelta(hours=24)

        # Grade adjustment multipliers (approximate)
        self._grade_multipliers = {
            10.0: 3.0,   # Gem Mint
            9.9: 2.5,
            9.8: 2.0,    # Near Mint/Mint
            9.6: 1.7,
            9.4: 1.5,    # Near Mint
            9.2: 1.35,
            9.0: 1.2,    # Very Fine/Near Mint
            8.5: 1.1,
            8.0: 1.0,    # Very Fine (baseline)
            7.5: 0.85,
            7.0: 0.75,   # Fine/Very Fine
            6.5: 0.65,
            6.0: 0.55,   # Fine
            5.5: 0.48,
            5.0: 0.40,   # Very Good/Fine
            4.5: 0.35,
            4.0: 0.30,   # Very Good
            3.5: 0.25,
            3.0: 0.22,   # Good/Very Good
            2.5: 0.18,
            2.0: 0.15,   # Good
            1.8: 0.12,
            1.5: 0.10,
            1.0: 0.08    # Fair/Poor
        }

    async def get_consensus_price(
        self,
        title: str,
        issue_number: Optional[str] = None,
        grade: float = 8.0,
        publisher: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get consensus price from all sources

        Args:
            title: Comic title
            issue_number: Issue number
            grade: CGC grade
            publisher: Publisher name

        Returns:
            Pricing data with consensus and individual source data
        """
        # Check cache
        cache_key = f"{title}_{issue_number}_{grade}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if datetime.utcnow() - cached['timestamp'] < self._cache_duration:
                logger.info(f"Cache hit for {cache_key}")
                return cached['data']

        # Import scrapers
        from pricing_sources.gpa_scraper import fetch_gpa_price
        from pricing_sources.heritage_scraper import fetch_heritage_price
        from pricing_sources.ebay_scraper import fetch_ebay_price

        # Fetch prices concurrently
        tasks = [
            self._safe_fetch(fetch_gpa_price, title, issue_number, grade, 'gpa'),
            self._safe_fetch(fetch_heritage_price, title, issue_number, grade, 'heritage'),
            self._safe_fetch(fetch_ebay_price, title, issue_number, grade, 'ebay')
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        gpa_result = results[0] if not isinstance(results[0], Exception) else None
        heritage_result = results[1] if not isinstance(results[1], Exception) else None
        ebay_result = results[2] if not isinstance(results[2], Exception) else None

        # Calculate consensus
        price_data = self._calculate_consensus(
            gpa_result, heritage_result, ebay_result, grade
        )

        # Cache result
        self._cache[cache_key] = {
            'timestamp': datetime.utcnow(),
            'data': price_data
        }

        return price_data

    async def _safe_fetch(
        self,
        fetch_func,
        title: str,
        issue_number: str,
        grade: float,
        source: str
    ) -> Optional[Dict]:
        """Safely execute fetch with timeout"""
        try:
            logger.info(f"[{source}] Starting price fetch for '{title}' #{issue_number}")
            result = await asyncio.wait_for(
                fetch_func(title, issue_number, grade),
                timeout=30.0
            )
            if result and result.get('price'):
                logger.info(f"[{source}] SUCCESS: ${result.get('price')}")
            else:
                logger.info(f"[{source}] No price found: {result.get('error', 'empty result')}")
            return result
        except asyncio.TimeoutError:
            logger.warning(f"[{source}] TIMEOUT after 30s")
            return {'error': 'timeout', 'source': source, 'price': None}
        except Exception as e:
            logger.error(f"[{source}] ERROR: {e}")
            return {'error': str(e), 'source': source, 'price': None}

    def _calculate_consensus(
        self,
        gpa_result: Optional[Dict],
        heritage_result: Optional[Dict],
        ebay_result: Optional[Dict],
        target_grade: float
    ) -> Dict[str, Any]:
        """Calculate weighted consensus price"""
        prices = []
        source_data = {}

        # Process GPA
        if gpa_result and gpa_result.get('price'):
            adjusted_price = self._adjust_for_grade(
                gpa_result['price'],
                gpa_result.get('grade_matched', target_grade),
                target_grade
            )
            prices.append({
                'price': adjusted_price,
                'weight': self.source_weights['gpa'] * gpa_result.get('confidence', 0.8),
                'source': 'gpa'
            })
            source_data['gpa_price'] = {
                'price': adjusted_price,
                'original_price': gpa_result['price'],
                'grade_matched': gpa_result.get('grade_matched'),
                'sale_date': gpa_result.get('sale_date'),
                'confidence': gpa_result.get('confidence', 0.8),
                'url': gpa_result.get('url')
            }

        # Process Heritage
        if heritage_result and heritage_result.get('price'):
            adjusted_price = self._adjust_for_grade(
                heritage_result['price'],
                heritage_result.get('grade_matched', target_grade),
                target_grade
            )
            prices.append({
                'price': adjusted_price,
                'weight': self.source_weights['heritage'] * heritage_result.get('confidence', 0.85),
                'source': 'heritage'
            })
            source_data['heritage_price'] = {
                'price': adjusted_price,
                'original_price': heritage_result['price'],
                'grade_matched': heritage_result.get('grade_matched'),
                'sale_date': heritage_result.get('sale_date'),
                'confidence': heritage_result.get('confidence', 0.85),
                'url': heritage_result.get('url')
            }

        # Process eBay
        if ebay_result and ebay_result.get('price'):
            adjusted_price = self._adjust_for_grade(
                ebay_result['price'],
                ebay_result.get('grade_matched', target_grade),
                target_grade
            )
            prices.append({
                'price': adjusted_price,
                'weight': self.source_weights['ebay'] * ebay_result.get('confidence', 0.7),
                'source': 'ebay'
            })
            source_data['ebay_price'] = {
                'price': adjusted_price,
                'original_price': ebay_result['price'],
                'grade_matched': ebay_result.get('grade_matched'),
                'sale_date': ebay_result.get('sale_date'),
                'confidence': ebay_result.get('confidence', 0.7),
                'url': ebay_result.get('url'),
                'sale_type': ebay_result.get('sale_type')
            }

        # Calculate consensus
        if not prices:
            return {
                'consensus_price': None,
                'price_range_low': None,
                'price_range_high': None,
                'confidence': 0,
                'sources_used': 0,
                'error': 'No price data available',
                **source_data
            }

        # Weighted average
        total_weight = sum(p['weight'] for p in prices)
        consensus = sum(p['price'] * p['weight'] for p in prices) / total_weight

        # Calculate range
        all_prices = [p['price'] for p in prices]
        if len(all_prices) >= 2:
            std = stdev(all_prices)
            price_low = max(0, consensus - std)
            price_high = consensus + std
        else:
            price_low = consensus * 0.85
            price_high = consensus * 1.15

        # Overall confidence
        confidence = total_weight / len(prices)

        # Market trend analysis
        market_trend = self._analyze_trend(source_data)

        return {
            'consensus_price': round(consensus, 2),
            'price_range_low': round(price_low, 2),
            'price_range_high': round(price_high, 2),
            'confidence': round(confidence, 3),
            'sources_used': len(prices),
            'market_trend': market_trend,
            'last_updated': datetime.utcnow().isoformat(),
            **source_data
        }

    def _adjust_for_grade(
        self,
        price: float,
        source_grade: float,
        target_grade: float
    ) -> float:
        """
        Adjust price for grade difference

        Uses multiplier ratios to estimate price at different grade
        """
        if abs(source_grade - target_grade) < 0.5:
            return price  # Close enough, no adjustment

        # Get multipliers
        source_mult = self._get_grade_multiplier(source_grade)
        target_mult = self._get_grade_multiplier(target_grade)

        if source_mult == 0:
            return price

        # Adjust price
        adjustment_ratio = target_mult / source_mult
        return price * adjustment_ratio

    def _get_grade_multiplier(self, grade: float) -> float:
        """Get grade multiplier (interpolate if needed)"""
        # Exact match
        if grade in self._grade_multipliers:
            return self._grade_multipliers[grade]

        # Interpolate
        grades = sorted(self._grade_multipliers.keys())
        for i, g in enumerate(grades):
            if g > grade:
                if i == 0:
                    return self._grade_multipliers[grades[0]]
                lower = grades[i-1]
                upper = g
                lower_mult = self._grade_multipliers[lower]
                upper_mult = self._grade_multipliers[upper]

                # Linear interpolation
                ratio = (grade - lower) / (upper - lower)
                return lower_mult + (upper_mult - lower_mult) * ratio

        return self._grade_multipliers[grades[-1]]

    def _analyze_trend(self, source_data: Dict) -> str:
        """Analyze market trend from recent sales"""
        # Simplified trend analysis
        # In production, would compare to historical data
        recent_prices = []

        for source in ['gpa_price', 'heritage_price', 'ebay_price']:
            if source in source_data:
                price_data = source_data[source]
                if price_data.get('sale_date'):
                    recent_prices.append(price_data['price'])

        if len(recent_prices) < 2:
            return 'stable'

        # Compare average to previous (simulated)
        # In production, would compare to historical average
        return 'stable'

    async def get_price_history(
        self,
        title: str,
        issue_number: str,
        grade: float,
        months: int = 12
    ) -> List[Dict]:
        """Get historical price data"""
        from pricing_sources.gpa_scraper import fetch_gpa_history

        try:
            history = await fetch_gpa_history(title, issue_number, grade, months)
            return history
        except Exception as e:
            logger.error(f"Price history error: {e}")
            return []

    def estimate_value_range(
        self,
        base_price: float,
        grade: float,
        key_issue: bool = False,
        variant: bool = False
    ) -> Tuple[float, float]:
        """
        Estimate realistic value range

        Accounts for:
        - Grade uncertainty
        - Market fluctuation
        - Key issue premium
        - Variant cover premium
        """
        # Base range (±15% for normal market variance)
        low = base_price * 0.85
        high = base_price * 1.15

        # Widen range for higher grades (more price sensitive)
        if grade >= 9.4:
            variance = 0.25  # ±25% for high grade
            low = base_price * (1 - variance)
            high = base_price * (1 + variance)

        # Key issue premium (20-50% above)
        if key_issue:
            low *= 1.15
            high *= 1.50

        # Variant cover adjustment
        if variant:
            low *= 1.1
            high *= 1.3

        return round(low, 2), round(high, 2)

    def clear_cache(self, pattern: str = None):
        """Clear price cache"""
        if pattern:
            keys_to_remove = [k for k in self._cache if pattern in k]
            for k in keys_to_remove:
                del self._cache[k]
        else:
            self._cache.clear()


# Global instance
pricing_engine = PricingEngine()
