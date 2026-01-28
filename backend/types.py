"""
EPOCGS Type Definitions - Python Edition
Complete type system for EPOCGS collectibles grading across all platforms

Synced from: P:/SOVEREIGN_APPS/website/lib/grading.ts
Author: CLAUDE_SECONDARY
Date: 2026-01-06
"""

from typing import Optional, List, Dict, Any, Literal, TypedDict
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


# ============================================================================
# ITEM TYPES
# ============================================================================

class ItemType(str, Enum):
    """Collectible item types supported by EPOCGS"""
    COMIC = "comic"
    CARD = "card"
    COIN = "coin"
    STAMP = "stamp"
    VINYL = "vinyl"
    TOY = "toy"                    # NEW
    GAMING_SYSTEM = "gaming_system"  # NEW
    VIDEO_GAME = "video_game"      # NEW


class ListingStatus(str, Enum):
    """Marketplace listing status"""
    NOT_LISTED = "not_listed"
    LISTED = "listed"
    SOLD = "sold"
    CANCELLED = "cancelled"


class PackagingCondition(str, Enum):
    """Toy packaging condition"""
    MINT = "mint"
    OPENED = "opened"
    DAMAGED = "damaged"


class WorkingCondition(str, Enum):
    """Gaming system working condition"""
    TESTED_WORKING = "tested_working"
    UNTESTED = "untested"
    FOR_PARTS = "for_parts"


class Region(str, Enum):
    """Gaming system/game region"""
    NTSC = "ntsc"
    PAL = "pal"
    NTSC_J = "ntsc-j"


class GameFormat(str, Enum):
    """Video game format"""
    CARTRIDGE = "cartridge"
    DISC = "disc"
    DIGITAL = "digital"


# ============================================================================
# MARKET RESEARCH
# ============================================================================

class EbaySale(BaseModel):
    """Individual eBay sold listing"""
    title: str
    price: float
    sold_date: str
    condition: Optional[str] = None
    url: str


class MarketResearch(BaseModel):
    """Market research data from external APIs"""
    ebay_avg_sold: float = 0.0
    ebay_recent_sales: List[EbaySale] = []
    amazon_current_price: Optional[float] = None
    mercari_avg_sold: Optional[float] = None
    price_charting_value: Optional[float] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    data_sources: List[str] = []


# ============================================================================
# GRADED ITEMS
# ============================================================================

class GradedItem(BaseModel):
    """
    Core graded item document
    Supports all 8 item types: comics, cards, coins, stamps, vinyl, toys, gaming systems, video games
    """
    id: str
    owner_id: str
    collection_id: Optional[str] = None

    # Item Details
    item_type: ItemType
    title: str
    subtitle: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None

    # Type-specific fields (Comics)
    issue_number: Optional[str] = None
    variant_cover: Optional[str] = None
    key_issue: Optional[bool] = None
    writer: Optional[str] = None
    artist: Optional[str] = None

    # Type-specific fields (Toys)
    manufacturer: Optional[str] = None
    series: Optional[str] = None
    character: Optional[str] = None
    variant: Optional[str] = None
    packaging_condition: Optional[PackagingCondition] = None
    accessories_complete: Optional[bool] = None
    license: Optional[str] = None

    # Type-specific fields (Gaming Systems)
    platform: Optional[str] = None
    model: Optional[str] = None
    region: Optional[Region] = None
    complete_in_box: Optional[bool] = None
    includes_controllers: Optional[bool] = None
    controller_count: Optional[int] = None
    includes_cables: Optional[bool] = None
    working_condition: Optional[WorkingCondition] = None

    # Type-specific fields (Video Games)
    developer: Optional[str] = None
    genre: Optional[str] = None
    format: Optional[GameFormat] = None
    includes_manual: Optional[bool] = None
    includes_case: Optional[bool] = None
    case_condition: Optional[str] = None
    disc_condition: Optional[str] = None
    label_condition: Optional[str] = None
    special_edition: Optional[bool] = None
    esrb_rating: Optional[str] = None

    # Grading Data
    consensus_grade: float = Field(ge=0.0, le=10.0)
    grade_label: str
    grade_confidence: float = Field(ge=0.0, le=1.0)
    front_grade: Optional[float] = None
    back_grade: Optional[float] = None
    defects: List[str] = []

    # AI Grading Results (stored as JSON)
    claude_grade_data: Optional[Dict[str, Any]] = None
    gemini_grade_data: Optional[Dict[str, Any]] = None
    gpt4_grade_data: Optional[Dict[str, Any]] = None

    # Pricing & Market Data
    consensus_price: Optional[float] = None
    price_range_low: Optional[float] = None
    price_range_high: Optional[float] = None

    # AI Market Research
    market_research: Optional[MarketResearch] = None

    # Price Ceiling (prevent gouging)
    suggested_max_price: Optional[float] = None
    price_verified: bool = False

    # Images
    front_image_url: Optional[str] = None
    back_image_url: Optional[str] = None
    additional_images: List[str] = []

    # Marketplace Linking
    marketplace_listing_id: Optional[str] = None
    listing_status: ListingStatus = ListingStatus.NOT_LISTED
    listed_at: Optional[datetime] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_graded: Optional[datetime] = None

    class Config:
        use_enum_values = True


class UserCollection(BaseModel):
    """User collection grouping multiple items"""
    id: str
    owner_id: str
    name: str
    description: Optional[str] = None
    item_type: str  # ItemType or 'mixed'

    # Stats (denormalized)
    total_items: int = 0
    total_value: float = 0.0
    average_grade: float = 0.0

    # Marketplace
    marketplace_listing_id: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# MARKETPLACE INTEGRATION
# ============================================================================

class GradeSummary(BaseModel):
    """Grade summary for marketplace display"""
    min_grade: Optional[float] = None
    max_grade: Optional[float] = None
    avg_grade: Optional[float] = None
    grade_range_display: Optional[str] = None


class RecentSale(BaseModel):
    """Recent sale comparison"""
    title: str
    price: float
    sold_date: str
    source: str
    url: str


class PriceVerification(BaseModel):
    """Price verification data"""
    user_price: float
    market_avg: float
    price_delta: float
    price_delta_percent: float
    is_reasonable: bool
    price_ceiling: float
    data_sources: List[str]
    recent_sales: List[RecentSale]
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class GradingData(BaseModel):
    """Grading data embedded in marketplace listing"""
    graded_item_id: Optional[str] = None
    graded_item_ids: Optional[List[str]] = None
    collection_id: Optional[str] = None
    listing_type: Literal["single", "batch", "collection", "none"]
    has_grading: bool = False
    grade_summary: Optional[GradeSummary] = None
    item_type: Optional[str] = None


# ============================================================================
# API REQUEST/RESPONSE TYPES
# ============================================================================

class CreateGradedItemRequest(BaseModel):
    """Request to create graded item"""
    item_type: ItemType
    title: str
    subtitle: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None

    # Grading data
    consensus_grade: float
    grade_label: str
    grade_confidence: float
    defects: List[str] = []

    # Images (base64 or URLs)
    front_image: Optional[str] = None
    back_image: Optional[str] = None
    additional_images: List[str] = []


class ResearchPriceRequest(BaseModel):
    """Request to research market price"""
    item_id: str


class ResearchPriceResponse(BaseModel):
    """Response from price research"""
    success: bool
    market_research: Optional[MarketResearch] = None
    error: Optional[str] = None


class PriceCheckRequest(BaseModel):
    """Request to check price before listing"""
    graded_item_id: str
    proposed_price: float


class PriceCheckResponse(BaseModel):
    """Response from price check"""
    success: bool
    proposed_price: float
    market_avg: float
    suggested_max: float
    is_reasonable: bool
    message: str
    recent_sales: List[RecentSale]
    error: Optional[str] = None


class MigrateGradingDataRequest(BaseModel):
    """Request to migrate comics.json to Firestore"""
    user_id: str
    collection_name: str
    auto_sync: bool = True


class MigrateGradingDataResponse(BaseModel):
    """Response from migration"""
    success: bool
    migrated_count: int
    collection_id: str
    total_value: float
    errors: List[str] = []


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

GRADE_LABELS = {
    0.5: 'POOR',
    1.0: 'FAIR',
    1.5: 'FAIR/GOOD',
    2.0: 'GOOD',
    2.5: 'GOOD+',
    3.0: 'GOOD/VERY GOOD',
    3.5: 'VERY GOOD-',
    4.0: 'VERY GOOD',
    4.5: 'VERY GOOD+',
    5.0: 'VERY GOOD/FINE',
    5.5: 'FINE-',
    6.0: 'FINE',
    6.5: 'FINE+',
    7.0: 'FINE/VERY FINE',
    7.5: 'VERY FINE-',
    8.0: 'VERY FINE',
    8.5: 'VERY FINE+',
    9.0: 'VERY FINE/NEAR MINT',
    9.2: 'NEAR MINT-',
    9.4: 'NEAR MINT',
    9.6: 'NEAR MINT+',
    9.8: 'NEAR MINT/MINT',
    10.0: 'GEM MINT'
}


def get_grade_label(grade: float) -> str:
    """Get grade label from numeric grade"""
    rounded = round(grade * 2) / 2  # Round to nearest 0.5
    return GRADE_LABELS.get(rounded, 'UNKNOWN')


def is_market_research_stale(research: MarketResearch) -> bool:
    """Check if market research is stale (>24h old)"""
    now = datetime.utcnow()
    hours_since_update = (now - research.last_updated).total_seconds() / 3600
    return hours_since_update > 24


def is_price_reasonable(user_price: float, market_avg: float) -> bool:
    """Check if price is reasonable (within 50% of market average)"""
    if market_avg == 0:
        return True  # No data, can't verify
    percent_diff = abs(((user_price - market_avg) / market_avg) * 100)
    return percent_diff <= 50


def calculate_suggested_max_price(market_avg: float) -> float:
    """Calculate suggested max price (1.5x market average)"""
    return round(market_avg * 1.5 * 100) / 100
