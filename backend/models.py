"""
Pydantic Models for Comic Grading System
Enhanced with comprehensive validation, serialization, and type safety
Implements COMPLETE CGC/CBCS Professional Grading Scale
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
import json


# =============================================================================
# CGC/CBCS OFFICIAL GRADING SCALE - COMPLETE IMPLEMENTATION
# =============================================================================

class GradeLabel(str, Enum):
    """
    CGC/CBCS Official Grade Labels with Exact Score Mappings
    Based on industry standard comic grading scale
    """
    GEM_MINT = "Gem Mint"              # 10.0 - Perfect. No flaws.
    MINT = "Mint"                       # 9.9  - Nearly perfect, virtually no flaws
    NEAR_MINT_MINT = "Near Mint/Mint"   # 9.8  - Nearly perfect, minor manufacturing defect allowed
    NEAR_MINT_PLUS = "Near Mint+"       # 9.6  - Minor wear, small manufacturing defects
    NEAR_MINT = "Near Mint"             # 9.4  - Minor wear beginning to show, minor defects
    NEAR_MINT_MINUS = "Near Mint-"      # 9.2  - Minor wear, minor creasing
    VERY_FINE_NEAR_MINT = "Very Fine/Near Mint"  # 9.0  - Minor wear, possible small crease
    VERY_FINE_PLUS = "Very Fine+"       # 8.5  - Slight wear, minor creases allowed
    VERY_FINE = "Very Fine"             # 8.0  - Minor wear, small creases, minor spine stress
    VERY_FINE_MINUS = "Very Fine-"      # 7.5  - Small creases, minor spine roll
    FINE_VERY_FINE = "Fine/Very Fine"   # 7.0  - Above average, minor wear visible
    FINE_PLUS = "Fine+"                 # 6.5  - Above average, slight wear
    FINE = "Fine"                       # 6.0  - Moderate wear, eye appeal still good
    FINE_MINUS = "Fine-"                # 5.5  - Moderate wear, creases visible
    VERY_GOOD_FINE = "Very Good/Fine"   # 5.0  - Average used comic, moderate creases
    VERY_GOOD_PLUS = "Very Good+"       # 4.5  - Shows wear, minor tears/pieces out
    VERY_GOOD = "Very Good"             # 4.0  - Shows significant wear
    VERY_GOOD_MINUS = "Very Good-"      # 3.5  - Obvious wear, possible small pieces missing
    GOOD_VERY_GOOD = "Good/Very Good"   # 3.0  - Heavy wear, readable but worn
    GOOD_PLUS = "Good+"                 # 2.5  - Heavily read, creases, minor soiling
    GOOD = "Good"                       # 2.0  - Heavily worn, possible tape/pieces missing
    GOOD_MINUS = "Good-"                # 1.8  - Very heavy wear, still complete
    FAIR_GOOD = "Fair/Good"             # 1.5  - Very worn, soiled, pieces may be missing
    FAIR = "Fair"                       # 1.0  - Heavy damage, may have coupons cut
    POOR = "Poor"                       # 0.5  - Barely holding together, major defects


class GradeQualifier(str, Enum):
    """
    CGC/CBCS Grade Qualifiers - Applied to graded comics with special conditions
    """
    RESTORED_AMATEUR = "A"      # Restored (Amateur) - Purple label
    RESTORED_PROFESSIONAL = "B" # Restored (Professional) - Purple label
    CONSERVED = "C"             # Conserved - Purple label
    QUALIFIED = "Qualified"     # Significant defect noted (writing, cut, etc.) - Green label
    SIGNATURE_SERIES = "SS"     # Signature Series (witnessed signature) - Yellow label


# Complete grade score to label mapping with exact CGC thresholds
CGC_GRADE_SCALE = {
    10.0: {"label": GradeLabel.GEM_MINT, "condition": "Perfect. No flaws."},
    9.9: {"label": GradeLabel.MINT, "condition": "Nearly perfect, virtually no flaws"},
    9.8: {"label": GradeLabel.NEAR_MINT_MINT, "condition": "Nearly perfect, minor manufacturing defect allowed"},
    9.6: {"label": GradeLabel.NEAR_MINT_PLUS, "condition": "Minor wear, small manufacturing defects"},
    9.4: {"label": GradeLabel.NEAR_MINT, "condition": "Minor wear beginning to show, minor defects"},
    9.2: {"label": GradeLabel.NEAR_MINT_MINUS, "condition": "Minor wear, minor creasing"},
    9.0: {"label": GradeLabel.VERY_FINE_NEAR_MINT, "condition": "Minor wear, possible small crease"},
    8.5: {"label": GradeLabel.VERY_FINE_PLUS, "condition": "Slight wear, minor creases allowed"},
    8.0: {"label": GradeLabel.VERY_FINE, "condition": "Minor wear, small creases, minor spine stress"},
    7.5: {"label": GradeLabel.VERY_FINE_MINUS, "condition": "Small creases, minor spine roll"},
    7.0: {"label": GradeLabel.FINE_VERY_FINE, "condition": "Above average, minor wear visible"},
    6.5: {"label": GradeLabel.FINE_PLUS, "condition": "Above average, slight wear"},
    6.0: {"label": GradeLabel.FINE, "condition": "Moderate wear, eye appeal still good"},
    5.5: {"label": GradeLabel.FINE_MINUS, "condition": "Moderate wear, creases visible"},
    5.0: {"label": GradeLabel.VERY_GOOD_FINE, "condition": "Average used comic, moderate creases"},
    4.5: {"label": GradeLabel.VERY_GOOD_PLUS, "condition": "Shows wear, minor tears/pieces out"},
    4.0: {"label": GradeLabel.VERY_GOOD, "condition": "Shows significant wear"},
    3.5: {"label": GradeLabel.VERY_GOOD_MINUS, "condition": "Obvious wear, possible small pieces missing"},
    3.0: {"label": GradeLabel.GOOD_VERY_GOOD, "condition": "Heavy wear, readable but worn"},
    2.5: {"label": GradeLabel.GOOD_PLUS, "condition": "Heavily read, creases, minor soiling"},
    2.0: {"label": GradeLabel.GOOD, "condition": "Heavily worn, possible tape/pieces missing"},
    1.8: {"label": GradeLabel.GOOD_MINUS, "condition": "Very heavy wear, still complete"},
    1.5: {"label": GradeLabel.FAIR_GOOD, "condition": "Very worn, soiled, pieces may be missing"},
    1.0: {"label": GradeLabel.FAIR, "condition": "Heavy damage, may have coupons cut"},
    0.5: {"label": GradeLabel.POOR, "condition": "Barely holding together, major defects"},
}


# =============================================================================
# KEY DEFECTS THAT KILL GRADE - CGC PROFESSIONAL STANDARDS
# =============================================================================

# Defect impact penalties (grade points deducted)
DEFECT_GRADE_IMPACTS = {
    "spine_roll": {"min": -1.0, "max": -2.0, "description": "Spine roll - curved spine from improper storage"},
    "color_breaking_crease": {"min": -1.0, "max": -3.0, "description": "Color breaking crease - crease that breaks color"},
    "tear": {"min": -2.0, "max": -4.0, "description": "Tear - paper torn"},
    "missing_pieces": {"min": -3.0, "max": -5.0, "description": "Missing pieces - chunks of comic missing"},
    "water_damage": {"min": -3.0, "max": -5.0, "description": "Water damage - staining/warping from moisture"},
    "writing_stamps": {"min": -2.0, "max": -4.0, "description": "Writing/stamps - ink marks on comic", "may_qualify": True},
    "restoration": {"min": 0.0, "max": 0.0, "description": "Restoration - separate purple label", "separate_label": True},
    "spine_stress": {"min": -0.5, "max": -1.5, "description": "Spine stress lines - stress marks along spine"},
    "spine_split": {"min": -1.5, "max": -3.0, "description": "Spine split - spine separating"},
    "cover_crease": {"min": -0.5, "max": -2.0, "description": "Cover crease - crease on cover"},
    "cover_tear": {"min": -1.5, "max": -3.0, "description": "Cover tear - tear on cover"},
    "cover_detached": {"min": -3.0, "max": -5.0, "description": "Cover detached - cover separated from staples"},
    "staple_rust": {"min": -0.5, "max": -1.5, "description": "Staple rust - oxidation on staples"},
    "staple_missing": {"min": -1.0, "max": -2.0, "description": "Staple missing - one or more staples gone"},
    "page_missing": {"min": -4.0, "max": -6.0, "description": "Page missing - pages removed/lost"},
    "tape": {"min": -1.5, "max": -3.0, "description": "Tape - tape applied to comic"},
    "tape_residue": {"min": -1.0, "max": -2.0, "description": "Tape residue - sticky residue from removed tape"},
    "staining": {"min": -1.0, "max": -3.0, "description": "Staining - discoloration from liquids/age"},
    "foxing": {"min": -0.5, "max": -1.5, "description": "Foxing - brown age spots"},
    "brittleness": {"min": -1.0, "max": -2.0, "description": "Brittleness - paper breaking down"},
    "trimming": {"min": 0.0, "max": 0.0, "description": "Trimming - comic edges cut", "separate_label": True},
    "corner_blunting": {"min": -0.3, "max": -1.0, "description": "Corner blunting - rounded/worn corners"},
    "edge_wear": {"min": -0.3, "max": -1.0, "description": "Edge wear - worn edges"},
    "subscription_crease": {"min": -0.5, "max": -1.5, "description": "Subscription crease - fold from mailing"},
}


class DefectType(str, Enum):
    """Comic Book Defect Categories"""
    # Cover Defects
    SPINE_STRESS = "spine_stress"
    SPINE_ROLL = "spine_roll"
    SPINE_SPLIT = "spine_split"
    COVER_TEAR = "cover_tear"
    COVER_CREASE = "cover_crease"
    COVER_DETACHED = "cover_detached"

    # Edge Defects
    EDGE_WEAR = "edge_wear"
    EDGE_CHIPPING = "edge_chipping"
    CORNER_BLUNTING = "corner_blunting"
    CORNER_CREASE = "corner_crease"

    # Color Defects
    COLOR_FADING = "color_fading"
    COLOR_BREAKING = "color_breaking"
    FOXING = "foxing"
    OXIDATION = "oxidation"

    # Structural Defects
    STAPLE_RUST = "staple_rust"
    STAPLE_MISSING = "staple_missing"
    STAPLE_LOOSE = "staple_loose"
    PAGE_MISSING = "page_missing"
    PAGE_LOOSE = "page_loose"
    CENTERFOLD_LOOSE = "centerfold_loose"

    # Contamination
    WRITING = "writing"
    TAPE = "tape"
    TAPE_RESIDUE = "tape_residue"
    WATER_DAMAGE = "water_damage"
    STAINING = "staining"
    DIRT = "dirt"

    # Other
    AMATEUR_RESTORATION = "amateur_restoration"
    PROFESSIONAL_RESTORATION = "professional_restoration"
    TRIMMING = "trimming"


class DefectSeverity(str, Enum):
    """Defect Severity Levels"""
    TRACE = "trace"  # Barely visible
    MINOR = "minor"  # Noticeable but minimal impact
    MODERATE = "moderate"  # Clear visibility, affects grade
    MAJOR = "major"  # Significant impact on grade
    SEVERE = "severe"  # Critical damage


class Defect(BaseModel):
    """Individual Defect Record"""
    type: DefectType
    severity: DefectSeverity
    location: Optional[str] = None  # "front_cover", "back_cover", "spine", "interior"
    description: Optional[str] = None
    grade_impact: float = Field(ge=-5.0, le=0.0, default=0.0)
    detected_by: List[str] = []  # Which AI models detected this
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)

    @validator('grade_impact')
    def validate_impact(cls, v):
        return round(v, 2)


class QualityScore(BaseModel):
    """Image Quality Assessment"""
    overall_score: float = Field(ge=0.0, le=1.0)
    sharpness: float = Field(ge=0.0, le=1.0)
    brightness: float = Field(ge=0.0, le=1.0)
    contrast: float = Field(ge=0.0, le=1.0)
    focus: float = Field(ge=0.0, le=1.0)
    noise: float = Field(ge=0.0, le=1.0)
    pass_threshold: bool = False
    recommendation: Optional[str] = None


class AIGradeResult(BaseModel):
    """Individual AI Provider Grade Result"""
    provider: str
    model: str
    grade: float = Field(ge=0.0, le=10.0)
    confidence: float = Field(ge=0.0, le=1.0)
    defects: List[Defect] = []
    reasoning: Optional[str] = None
    raw_response: Optional[str] = None
    processing_time_ms: int = 0
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConsensusGrade(BaseModel):
    """Multi-AI Consensus Grading Result"""
    consensus_grade: float = Field(ge=0.0, le=10.0)
    grade_label: GradeLabel
    confidence: float = Field(ge=0.0, le=1.0)

    front_grade: float = Field(ge=0.0, le=10.0)
    back_grade: float = Field(ge=0.0, le=10.0)

    individual_grades: Dict[str, AIGradeResult] = {}
    confirmed_defects: List[Defect] = []

    agreement_percentage: float = Field(ge=0.0, le=1.0)
    standard_deviation: float = Field(ge=0.0)

    quality_adjusted: bool = False
    quality_penalty: float = 0.0

    requires_manual_review: bool = False
    review_reason: Optional[str] = None

    grading_timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_processing_time_ms: int = 0

    @staticmethod
    def grade_to_label(grade: float) -> GradeLabel:
        """
        Convert numeric grade to CGC/CBCS label using OFFICIAL scale
        Uses exact CGC thresholds for accurate grading
        """
        if grade >= 10.0:
            return GradeLabel.GEM_MINT          # 10.0 - Perfect. No flaws.
        elif grade >= 9.9:
            return GradeLabel.MINT              # 9.9  - Nearly perfect, virtually no flaws
        elif grade >= 9.8:
            return GradeLabel.NEAR_MINT_MINT    # 9.8  - Nearly perfect, minor manufacturing defect allowed
        elif grade >= 9.6:
            return GradeLabel.NEAR_MINT_PLUS    # 9.6  - Minor wear, small manufacturing defects
        elif grade >= 9.4:
            return GradeLabel.NEAR_MINT         # 9.4  - Minor wear beginning to show, minor defects
        elif grade >= 9.2:
            return GradeLabel.NEAR_MINT_MINUS   # 9.2  - Minor wear, minor creasing
        elif grade >= 9.0:
            return GradeLabel.VERY_FINE_NEAR_MINT  # 9.0  - Minor wear, possible small crease
        elif grade >= 8.5:
            return GradeLabel.VERY_FINE_PLUS    # 8.5  - Slight wear, minor creases allowed
        elif grade >= 8.0:
            return GradeLabel.VERY_FINE         # 8.0  - Minor wear, small creases, minor spine stress
        elif grade >= 7.5:
            return GradeLabel.VERY_FINE_MINUS   # 7.5  - Small creases, minor spine roll
        elif grade >= 7.0:
            return GradeLabel.FINE_VERY_FINE    # 7.0  - Above average, minor wear visible
        elif grade >= 6.5:
            return GradeLabel.FINE_PLUS         # 6.5  - Above average, slight wear
        elif grade >= 6.0:
            return GradeLabel.FINE              # 6.0  - Moderate wear, eye appeal still good
        elif grade >= 5.5:
            return GradeLabel.FINE_MINUS        # 5.5  - Moderate wear, creases visible
        elif grade >= 5.0:
            return GradeLabel.VERY_GOOD_FINE    # 5.0  - Average used comic, moderate creases
        elif grade >= 4.5:
            return GradeLabel.VERY_GOOD_PLUS    # 4.5  - Shows wear, minor tears/pieces out
        elif grade >= 4.0:
            return GradeLabel.VERY_GOOD         # 4.0  - Shows significant wear
        elif grade >= 3.5:
            return GradeLabel.VERY_GOOD_MINUS   # 3.5  - Obvious wear, possible small pieces missing
        elif grade >= 3.0:
            return GradeLabel.GOOD_VERY_GOOD    # 3.0  - Heavy wear, readable but worn
        elif grade >= 2.5:
            return GradeLabel.GOOD_PLUS         # 2.5  - Heavily read, creases, minor soiling
        elif grade >= 2.0:
            return GradeLabel.GOOD              # 2.0  - Heavily worn, possible tape/pieces missing
        elif grade >= 1.8:
            return GradeLabel.GOOD_MINUS        # 1.8  - Very heavy wear, still complete
        elif grade >= 1.5:
            return GradeLabel.FAIR_GOOD         # 1.5  - Very worn, soiled, pieces may be missing
        elif grade >= 1.0:
            return GradeLabel.FAIR              # 1.0  - Heavy damage, may have coupons cut
        else:
            return GradeLabel.POOR              # 0.5  - Barely holding together, major defects

    @staticmethod
    def get_grade_condition(grade: float) -> str:
        """Get the condition description for a numeric grade"""
        # Find the closest matching grade in the scale
        grade_thresholds = sorted(CGC_GRADE_SCALE.keys(), reverse=True)
        for threshold in grade_thresholds:
            if grade >= threshold:
                return CGC_GRADE_SCALE[threshold]["condition"]
        return CGC_GRADE_SCALE[0.5]["condition"]

    @staticmethod
    def snap_to_cgc_grade(grade: float) -> float:
        """
        Snap a calculated grade to the nearest valid CGC grade point
        CGC only uses specific grade values, not arbitrary decimals
        """
        valid_grades = [10.0, 9.9, 9.8, 9.6, 9.4, 9.2, 9.0, 8.5, 8.0, 7.5, 7.0,
                       6.5, 6.0, 5.5, 5.0, 4.5, 4.0, 3.5, 3.0, 2.5, 2.0, 1.8,
                       1.5, 1.0, 0.5]
        # Find the closest valid grade (round down for strictness)
        for valid_grade in valid_grades:
            if grade >= valid_grade:
                return valid_grade
        return 0.5

    @staticmethod
    def calculate_defect_penalty(defect_type: str, severity: str) -> float:
        """
        Calculate grade penalty for a specific defect based on CGC standards
        Returns negative value to subtract from grade
        """
        if defect_type not in DEFECT_GRADE_IMPACTS:
            return 0.0

        impact = DEFECT_GRADE_IMPACTS[defect_type]
        severity_multipliers = {
            "trace": 0.2,
            "minor": 0.4,
            "moderate": 0.6,
            "major": 0.8,
            "severe": 1.0
        }
        multiplier = severity_multipliers.get(severity, 0.6)

        # Calculate penalty within min/max range based on severity
        penalty_range = impact["max"] - impact["min"]
        penalty = impact["min"] + (penalty_range * multiplier)

        return penalty


class PriceData(BaseModel):
    """Price Data from Single Source"""
    source: str
    price: Optional[float] = None
    grade_matched: float = 0.0
    sale_date: Optional[datetime] = None
    sale_type: Optional[str] = None  # "auction", "buy_now", "offer"
    url: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    error: Optional[str] = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class ConsensusPricing(BaseModel):
    """Multi-Source Price Consensus"""
    consensus_price: float = Field(ge=0.0)
    price_range_low: float = Field(ge=0.0)
    price_range_high: float = Field(ge=0.0)

    gpa_price: Optional[PriceData] = None
    heritage_price: Optional[PriceData] = None
    ebay_price: Optional[PriceData] = None

    sources_used: int = 0
    confidence: float = Field(ge=0.0, le=1.0)

    market_trend: Optional[str] = None  # "rising", "stable", "declining"
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class CaptureMetadata(BaseModel):
    """Webcam Capture Metadata"""
    camera_id: int = 0
    resolution: tuple = (1920, 1080)
    capture_timestamp: datetime = Field(default_factory=datetime.utcnow)

    border_detection_confidence: float = Field(ge=0.0, le=1.0)
    stability_frames: int = 0
    auto_captured: bool = True

    original_filename: str = ""
    processed_filename: str = ""

    image_dimensions: tuple = (0, 0)
    file_size_bytes: int = 0

    preprocessing_applied: List[str] = []  # ["crop", "enhance", "denoise"]


class ComicBase(BaseModel):
    """Base Comic Model"""
    title: str = Field(min_length=1, max_length=500)
    issue_number: Optional[str] = Field(max_length=50, default=None)
    publisher: Optional[str] = Field(max_length=200, default=None)
    publication_year: Optional[int] = Field(ge=1900, le=2100, default=None)

    variant_cover: bool = False
    variant_description: Optional[str] = None

    key_issue: bool = False
    key_issue_reason: Optional[str] = None

    notes: Optional[str] = None


class ComicCreate(ComicBase):
    """Comic Creation Model"""
    front_image_path: str
    back_image_path: Optional[str] = None


class ComicGradeRequest(BaseModel):
    """Request to Grade a Comic"""
    comic_id: Optional[int] = None
    front_image_path: str
    back_image_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    force_regrade: bool = False
    include_pricing: bool = True


class ComicFull(ComicBase):
    """Complete Comic Model with All Data"""
    id: int

    # Grading
    consensus_grade: Optional[ConsensusGrade] = None

    # Pricing
    pricing: Optional[ConsensusPricing] = None

    # Images
    front_image_path: Optional[str] = None
    back_image_path: Optional[str] = None
    front_quality_score: Optional[QualityScore] = None
    back_quality_score: Optional[QualityScore] = None
    front_capture_metadata: Optional[CaptureMetadata] = None
    back_capture_metadata: Optional[CaptureMetadata] = None

    # Timestamps
    date_added: datetime = Field(default_factory=datetime.utcnow)
    last_graded: Optional[datetime] = None
    last_priced: Optional[datetime] = None

    # Export
    published_to_portal: bool = False
    investor_notes: Optional[str] = None

    class Config:
        from_attributes = True


class ComicSearchQuery(BaseModel):
    """Search/Filter Query for Comics"""
    search_term: Optional[str] = None
    publisher: Optional[str] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    grade_min: Optional[float] = Field(ge=0.0, le=10.0, default=None)
    grade_max: Optional[float] = Field(ge=0.0, le=10.0, default=None)
    price_min: Optional[float] = Field(ge=0.0, default=None)
    price_max: Optional[float] = None
    key_issues_only: bool = False
    needs_manual_review: bool = False
    not_published: bool = False

    sort_by: str = "date_added"
    sort_order: str = "desc"

    limit: int = Field(ge=1, le=1000, default=50)
    offset: int = Field(ge=0, default=0)


class BatchGradeRequest(BaseModel):
    """Batch Grading Request"""
    comic_ids: List[int] = []
    include_pricing: bool = True
    force_regrade: bool = False


class BatchGradeResult(BaseModel):
    """Batch Grading Result"""
    total: int = 0
    successful: int = 0
    failed: int = 0
    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    total_time_seconds: float = 0.0


class ExportRequest(BaseModel):
    """Export Request for Investor Portal"""
    comic_ids: Optional[List[int]] = None  # None = all published
    format: str = "html"  # "html", "json", "csv"
    include_images: bool = True
    include_defect_details: bool = False


class SystemStats(BaseModel):
    """System Statistics"""
    total_comics: int = 0
    total_graded: int = 0
    awaiting_review: int = 0

    average_grade: float = 0.0
    total_estimated_value: float = 0.0

    grades_today: int = 0
    grades_this_week: int = 0
    grades_this_month: int = 0

    top_publishers: List[Dict[str, Any]] = []
    grade_distribution: Dict[str, int] = {}
    ai_provider_stats: List[Dict[str, Any]] = []

    last_updated: datetime = Field(default_factory=datetime.utcnow)


class WebhookEvent(BaseModel):
    """Webhook Event for External Integrations"""
    event_type: str  # "grade_complete", "price_update", "batch_complete"
    comic_id: Optional[int] = None
    data: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class APIResponse(BaseModel):
    """Standard API Response Wrapper"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    errors: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)
