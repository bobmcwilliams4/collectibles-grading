"""
Professional Grading Features
CGC census lookup, variant cover tracking, and signature series support
"""

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class CGCLabelType(Enum):
    """CGC label types"""
    BLUE = "blue"           # Standard grade
    YELLOW = "yellow"       # Signature Series
    GREEN = "green"         # Qualified
    PURPLE = "purple"       # Restored
    NG = "ng"               # No Grade


class VariantType(Enum):
    """Comic variant types"""
    REGULAR = "regular"
    NEWSSTAND = "newsstand"
    DIRECT = "direct"
    VARIANT_COVER = "variant_cover"
    INCENTIVE = "incentive"           # 1:10, 1:25, etc.
    SKETCH = "sketch"
    VIRGIN = "virgin"                 # No trade dress
    FOIL = "foil"
    CHROMIUM = "chromium"
    DIE_CUT = "die_cut"
    HOLOGRAM = "hologram"
    GLOW_IN_DARK = "glow_in_dark"
    LENTICULAR = "lenticular"
    ASHCAN = "ashcan"
    SECOND_PRINT = "second_print"
    THIRD_PRINT = "third_print"
    FACSIMILE = "facsimile"


class SignatureType(Enum):
    """Types of signatures"""
    WRITER = "writer"
    PENCILER = "penciler"
    INKER = "inker"
    COLORIST = "colorist"
    LETTERER = "letterer"
    EDITOR = "editor"
    CREATOR = "creator"           # For creator-owned works
    COVER_ARTIST = "cover_artist"
    OTHER = "other"


@dataclass
class CGCCensusEntry:
    """CGC census data for a specific issue"""
    title: str
    issue_number: str
    variant: str = ""

    # Census counts by grade
    total_graded: int = 0
    grade_distribution: Dict[str, int] = field(default_factory=dict)

    # Key metrics
    highest_grade: float = 0.0
    highest_grade_count: int = 0
    average_grade: float = 0.0

    # Population at key grades
    pop_98: int = 0
    pop_96: int = 0
    pop_94: int = 0
    pop_90: int = 0

    # Universal vs qualified
    universal_count: int = 0
    qualified_count: int = 0
    restored_count: int = 0
    signature_series_count: int = 0

    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class VariantInfo:
    """Detailed variant cover information"""
    variant_type: VariantType
    cover_artist: str = ""
    ratio: str = ""              # e.g., "1:25"
    retailer_exclusive: str = "" # e.g., "Midtown Comics"
    convention: str = ""         # e.g., "SDCC 2024"
    description: str = ""
    print_run: int = 0           # If known
    relative_rarity: str = ""    # common/uncommon/rare/ultra-rare


@dataclass
class SignatureInfo:
    """Signature information"""
    signer_name: str
    signature_type: SignatureType
    authenticated: bool = False
    authentication_service: str = ""  # CGC, CBCS, etc.
    signing_date: Optional[datetime] = None
    signing_location: str = ""
    verified_by: str = ""
    notes: str = ""


@dataclass
class ProfessionalGrade:
    """Professional grading service submission"""
    service: str                # CGC, CBCS, PGX
    cert_number: str
    grade: float
    label_type: CGCLabelType
    page_quality: str
    graded_date: datetime
    signatures: List[SignatureInfo] = field(default_factory=list)
    notes: str = ""


@dataclass
class KeyIssueInfo:
    """Key issue designation information"""
    is_key: bool = False
    key_type: str = ""          # First appearance, origin, death, etc.
    key_character: str = ""
    key_significance: str = ""
    overstreet_key_rank: str = ""  # Bronze, Silver, Gold, Platinum
    market_impact: float = 1.0  # Multiplier for standard value


# =============================================================================
# CGC CENSUS SERVICE
# =============================================================================

class CGCCensusService:
    """
    CGC Census lookup and tracking

    Features:
    - Census data retrieval
    - Population analysis
    - Rarity scoring
    - Grade distribution insights
    """

    # Census cache
    _cache: Dict[str, CGCCensusEntry] = {}
    _cache_ttl_hours = 24

    def __init__(self):
        self._census_data: Dict[str, CGCCensusEntry] = {}
        self._load_cached_data()

    def _load_cached_data(self):
        """Load cached census data from disk"""
        # In production, this would load from database/file
        pass

    def _generate_census_key(
        self,
        title: str,
        issue_number: str,
        variant: str = ""
    ) -> str:
        """Generate unique key for census lookup"""
        key_str = f"{title.lower()}|{issue_number}|{variant.lower()}"
        return hashlib.md5(key_str.encode()).hexdigest()

    async def get_census_data(
        self,
        title: str,
        issue_number: str,
        variant: str = ""
    ) -> Optional[CGCCensusEntry]:
        """
        Get CGC census data for an issue

        Args:
            title: Comic title
            issue_number: Issue number
            variant: Variant description

        Returns:
            CGCCensusEntry if found
        """
        cache_key = self._generate_census_key(title, issue_number, variant)

        # Check cache
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if (datetime.utcnow() - entry.last_updated).hours < self._cache_ttl_hours:
                return entry

        # In production, would fetch from CGC API or scrape census
        # For now, return simulated data
        return await self._simulate_census_lookup(title, issue_number, variant)

    async def _simulate_census_lookup(
        self,
        title: str,
        issue_number: str,
        variant: str
    ) -> CGCCensusEntry:
        """Simulate census lookup (placeholder for actual API)"""
        # This would be replaced with actual CGC census lookup
        import random

        total = random.randint(100, 5000)

        return CGCCensusEntry(
            title=title,
            issue_number=issue_number,
            variant=variant,
            total_graded=total,
            highest_grade=9.8 if random.random() > 0.3 else 9.6,
            highest_grade_count=random.randint(1, 20),
            average_grade=round(7.5 + random.random() * 2, 1),
            pop_98=random.randint(0, int(total * 0.05)),
            pop_96=random.randint(0, int(total * 0.1)),
            pop_94=random.randint(0, int(total * 0.15)),
            pop_90=random.randint(0, int(total * 0.25)),
            universal_count=int(total * 0.85),
            qualified_count=int(total * 0.05),
            restored_count=int(total * 0.05),
            signature_series_count=int(total * 0.05)
        )

    def calculate_rarity_score(
        self,
        census: CGCCensusEntry,
        target_grade: float
    ) -> Dict[str, Any]:
        """
        Calculate rarity score for a comic at a specific grade

        Returns score 1-100 where higher = rarer
        """
        if census.total_graded == 0:
            return {'score': 100, 'label': 'Unknown', 'percentile': 0}

        # Get count at or above target grade
        higher_grades = 0
        for grade_str, count in census.grade_distribution.items():
            try:
                grade = float(grade_str)
                if grade >= target_grade:
                    higher_grades += count
            except ValueError:
                pass

        # Calculate percentile
        percentile = (1 - (higher_grades / census.total_graded)) * 100

        # Determine rarity label
        if percentile >= 99:
            label = "Ultra Rare"
            score = 100
        elif percentile >= 95:
            label = "Very Rare"
            score = 95
        elif percentile >= 90:
            label = "Rare"
            score = 85
        elif percentile >= 75:
            label = "Uncommon"
            score = 70
        elif percentile >= 50:
            label = "Average"
            score = 50
        else:
            label = "Common"
            score = 30

        return {
            'score': score,
            'label': label,
            'percentile': percentile,
            'count_at_grade': higher_grades,
            'total_population': census.total_graded
        }


# =============================================================================
# VARIANT TRACKER
# =============================================================================

class VariantTracker:
    """
    Track and identify comic book variants

    Features:
    - Variant type detection
    - Rarity assessment
    - Cover artist identification
    - Ratio variant tracking
    """

    # Common variant indicators
    VARIANT_PATTERNS = {
        r'1:(\d+)': 'incentive',
        r'newsstand': 'newsstand',
        r'direct': 'direct',
        r'sketch': 'sketch',
        r'virgin': 'virgin',
        r'foil': 'foil',
        r'chromium': 'chromium',
        r'die[- ]?cut': 'die_cut',
        r'hologram': 'hologram',
        r'glow': 'glow_in_dark',
        r'lenticular': 'lenticular',
        r'ashcan': 'ashcan',
        r'2nd print|second print': 'second_print',
        r'3rd print|third print': 'third_print',
        r'facsimile': 'facsimile',
        r'sdcc|nycc|eccc|wondercon': 'convention',
    }

    # Known retailer exclusives
    RETAILER_EXCLUSIVES = [
        'Midtown Comics', 'Unknown Comics', 'Comic Mint',
        'Frankie\'s Comics', 'Big Time Collectibles', 'KRS Comics',
        'Comics Elite', 'Torpedo Comics', 'Scorpion Comics'
    ]

    def detect_variant_type(
        self,
        variant_description: str
    ) -> Tuple[VariantType, Dict[str, Any]]:
        """
        Detect variant type from description

        Args:
            variant_description: Text description of variant

        Returns:
            Tuple of (VariantType, additional_info)
        """
        desc_lower = variant_description.lower()
        info = {}

        # Check for ratio variants
        ratio_match = re.search(r'1:(\d+)', variant_description)
        if ratio_match:
            info['ratio'] = f"1:{ratio_match.group(1)}"
            info['ratio_number'] = int(ratio_match.group(1))
            return VariantType.INCENTIVE, info

        # Check patterns
        for pattern, variant_name in self.VARIANT_PATTERNS.items():
            if re.search(pattern, desc_lower):
                variant_type = VariantType[variant_name.upper()] if variant_name.upper() in VariantType.__members__ else VariantType.VARIANT_COVER
                return variant_type, info

        # Check retailer exclusives
        for retailer in self.RETAILER_EXCLUSIVES:
            if retailer.lower() in desc_lower:
                info['retailer_exclusive'] = retailer
                return VariantType.VARIANT_COVER, info

        # Default to variant cover if has "variant" or "cover"
        if 'variant' in desc_lower or 'cover' in desc_lower:
            return VariantType.VARIANT_COVER, info

        return VariantType.REGULAR, info

    def estimate_rarity(
        self,
        variant_type: VariantType,
        ratio: str = None
    ) -> str:
        """Estimate relative rarity of variant"""
        # Ratio-based rarity
        if ratio:
            match = re.search(r'1:(\d+)', ratio)
            if match:
                ratio_num = int(match.group(1))
                if ratio_num >= 500:
                    return "ultra-rare"
                elif ratio_num >= 100:
                    return "rare"
                elif ratio_num >= 25:
                    return "uncommon"
                else:
                    return "common"

        # Type-based rarity
        rarity_map = {
            VariantType.REGULAR: "common",
            VariantType.NEWSSTAND: "uncommon",  # Modern newsstand
            VariantType.DIRECT: "common",
            VariantType.VARIANT_COVER: "uncommon",
            VariantType.INCENTIVE: "uncommon",  # Default for incentives
            VariantType.SKETCH: "rare",
            VariantType.VIRGIN: "uncommon",
            VariantType.FOIL: "uncommon",
            VariantType.CHROMIUM: "uncommon",
            VariantType.DIE_CUT: "uncommon",
            VariantType.HOLOGRAM: "uncommon",
            VariantType.GLOW_IN_DARK: "rare",
            VariantType.LENTICULAR: "uncommon",
            VariantType.ASHCAN: "rare",
            VariantType.SECOND_PRINT: "common",
            VariantType.THIRD_PRINT: "common",
            VariantType.FACSIMILE: "common",
        }

        return rarity_map.get(variant_type, "unknown")


# =============================================================================
# SIGNATURE SERIES MANAGER
# =============================================================================

class SignatureSeriesManager:
    """
    Manage signature series information

    Features:
    - Signature verification tracking
    - Creator database
    - Authentication status
    - Signing event tracking
    """

    # Known creators database (sample)
    CREATORS_DB = {
        'stan lee': SignatureType.CREATOR,
        'jim lee': SignatureType.PENCILER,
        'todd mcfarlane': SignatureType.CREATOR,
        'rob liefeld': SignatureType.CREATOR,
        'frank miller': SignatureType.CREATOR,
        'neil gaiman': SignatureType.WRITER,
        'scott snyder': SignatureType.WRITER,
        'geoff johns': SignatureType.WRITER,
        'jim steranko': SignatureType.PENCILER,
        'alex ross': SignatureType.COVER_ARTIST,
        'artgerm': SignatureType.COVER_ARTIST,
        'stanley lau': SignatureType.COVER_ARTIST,  # Artgerm real name
    }

    def identify_signer(self, name: str) -> SignatureInfo:
        """
        Identify signer and determine signature type

        Args:
            name: Signer's name

        Returns:
            SignatureInfo with identified details
        """
        name_lower = name.lower().strip()

        # Check known creators
        sig_type = self.CREATORS_DB.get(name_lower, SignatureType.OTHER)

        return SignatureInfo(
            signer_name=name,
            signature_type=sig_type
        )

    def validate_signature_combo(
        self,
        signatures: List[SignatureInfo],
        comic_title: str,
        issue_number: str
    ) -> Dict[str, Any]:
        """
        Validate if signatures make sense for the comic

        Returns validation result with notes
        """
        result = {
            'valid': True,
            'warnings': [],
            'value_impact': 1.0
        }

        # Check for duplicate signers
        signer_names = [s.signer_name.lower() for s in signatures]
        if len(signer_names) != len(set(signer_names)):
            result['warnings'].append("Duplicate signer detected")

        # Multiple signatures increase value
        if len(signatures) > 1:
            result['value_impact'] = 1.0 + (len(signatures) * 0.1)

        # Authenticated signatures worth more
        authenticated_count = sum(1 for s in signatures if s.authenticated)
        if authenticated_count == len(signatures) and signatures:
            result['value_impact'] *= 1.25
        elif authenticated_count > 0:
            result['value_impact'] *= 1.1

        return result


# =============================================================================
# KEY ISSUE ANALYZER
# =============================================================================

class KeyIssueAnalyzer:
    """
    Analyze and identify key issues

    Features:
    - First appearance detection
    - Key event identification
    - Market impact calculation
    - Overstreet key ranking
    """

    # Sample key issue database
    KEY_ISSUES_DB = {
        ('amazing spider-man', '300'): KeyIssueInfo(
            is_key=True,
            key_type='First full appearance',
            key_character='Venom',
            key_significance='First full appearance of Venom (Eddie Brock)',
            overstreet_key_rank='Gold',
            market_impact=3.0
        ),
        ('new mutants', '98'): KeyIssueInfo(
            is_key=True,
            key_type='First appearance',
            key_character='Deadpool',
            key_significance='First appearance of Deadpool',
            overstreet_key_rank='Platinum',
            market_impact=5.0
        ),
        ('hulk', '181'): KeyIssueInfo(
            is_key=True,
            key_type='First full appearance',
            key_character='Wolverine',
            key_significance='First full appearance of Wolverine',
            overstreet_key_rank='Platinum',
            market_impact=10.0
        ),
    }

    # Key type value multipliers
    KEY_TYPE_MULTIPLIERS = {
        'First appearance': 2.5,
        'First full appearance': 3.0,
        'First cover appearance': 1.5,
        'Origin': 2.0,
        'Death': 1.8,
        'First team appearance': 2.0,
        'Key story arc': 1.5,
        'First issue': 1.3,
        'Last issue': 1.2,
    }

    def analyze_key_status(
        self,
        title: str,
        issue_number: str,
        notes: str = ""
    ) -> KeyIssueInfo:
        """
        Analyze if comic is a key issue

        Args:
            title: Comic title
            issue_number: Issue number
            notes: Any additional notes

        Returns:
            KeyIssueInfo with key status
        """
        # Normalize lookup key
        title_normalized = title.lower().strip()
        issue_normalized = str(issue_number).strip()
        lookup_key = (title_normalized, issue_normalized)

        # Check database
        if lookup_key in self.KEY_ISSUES_DB:
            return self.KEY_ISSUES_DB[lookup_key]

        # Check notes for key indicators
        notes_lower = notes.lower() if notes else ""
        for key_type, multiplier in self.KEY_TYPE_MULTIPLIERS.items():
            if key_type.lower() in notes_lower:
                return KeyIssueInfo(
                    is_key=True,
                    key_type=key_type,
                    key_significance=notes,
                    market_impact=multiplier
                )

        return KeyIssueInfo(is_key=False)

    def calculate_key_premium(
        self,
        key_info: KeyIssueInfo,
        base_value: float,
        grade: float
    ) -> float:
        """
        Calculate key issue premium on value

        Args:
            key_info: Key issue information
            base_value: Base market value
            grade: CGC grade

        Returns:
            Adjusted value with key premium
        """
        if not key_info.is_key:
            return base_value

        # Apply base multiplier
        premium = base_value * key_info.market_impact

        # Higher grades get exponential premium for keys
        if grade >= 9.8:
            premium *= 1.5
        elif grade >= 9.6:
            premium *= 1.3
        elif grade >= 9.4:
            premium *= 1.15

        return premium


# =============================================================================
# PROFESSIONAL GRADING INTEGRATION
# =============================================================================

class ProfessionalGradingService:
    """
    Integration with professional grading services

    Features:
    - Cert number lookup
    - Grade verification
    - Label type identification
    - Submission tracking
    """

    def parse_cert_number(self, cert_str: str) -> Dict[str, Any]:
        """
        Parse and validate certification number

        Args:
            cert_str: Certification number string

        Returns:
            Parsed cert info
        """
        # CGC format: typically numeric with possible prefix
        # CBCS format: similar
        # PGX format: different pattern

        result = {
            'valid': False,
            'service': 'unknown',
            'cert_number': None,
            'original': cert_str
        }

        cert_clean = re.sub(r'[^0-9]', '', cert_str)

        if len(cert_clean) >= 7:
            result['valid'] = True
            result['cert_number'] = cert_clean

            # Identify service (simplified)
            if cert_str.lower().startswith('cgc'):
                result['service'] = 'CGC'
            elif cert_str.lower().startswith('cbcs'):
                result['service'] = 'CBCS'
            elif cert_str.lower().startswith('pgx'):
                result['service'] = 'PGX'
            else:
                result['service'] = 'CGC'  # Default assumption

        return result

    def identify_label_type(self, label_info: str) -> CGCLabelType:
        """Identify CGC label type from description"""
        label_lower = label_info.lower()

        if 'signature' in label_lower or 'yellow' in label_lower:
            return CGCLabelType.YELLOW
        elif 'qualified' in label_lower or 'green' in label_lower:
            return CGCLabelType.GREEN
        elif 'restored' in label_lower or 'purple' in label_lower:
            return CGCLabelType.PURPLE
        elif 'no grade' in label_lower or 'ng' in label_lower:
            return CGCLabelType.NG
        else:
            return CGCLabelType.BLUE


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_census_service: Optional[CGCCensusService] = None
_variant_tracker: Optional[VariantTracker] = None
_signature_manager: Optional[SignatureSeriesManager] = None
_key_analyzer: Optional[KeyIssueAnalyzer] = None
_grading_service: Optional[ProfessionalGradingService] = None


def get_census_service() -> CGCCensusService:
    global _census_service
    if _census_service is None:
        _census_service = CGCCensusService()
    return _census_service


def get_variant_tracker() -> VariantTracker:
    global _variant_tracker
    if _variant_tracker is None:
        _variant_tracker = VariantTracker()
    return _variant_tracker


def get_signature_manager() -> SignatureSeriesManager:
    global _signature_manager
    if _signature_manager is None:
        _signature_manager = SignatureSeriesManager()
    return _signature_manager


def get_key_analyzer() -> KeyIssueAnalyzer:
    global _key_analyzer
    if _key_analyzer is None:
        _key_analyzer = KeyIssueAnalyzer()
    return _key_analyzer


def get_grading_service() -> ProfessionalGradingService:
    global _grading_service
    if _grading_service is None:
        _grading_service = ProfessionalGradingService()
    return _grading_service


# Export
__all__ = [
    'CGCLabelType',
    'VariantType',
    'SignatureType',
    'CGCCensusEntry',
    'VariantInfo',
    'SignatureInfo',
    'ProfessionalGrade',
    'KeyIssueInfo',
    'CGCCensusService',
    'VariantTracker',
    'SignatureSeriesManager',
    'KeyIssueAnalyzer',
    'ProfessionalGradingService',
    'get_census_service',
    'get_variant_tracker',
    'get_signature_manager',
    'get_key_analyzer',
    'get_grading_service',
]
