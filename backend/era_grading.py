"""
Era-Specific Grading System
Generates specialized grading prompts based on comic book era
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ComicEra(Enum):
    """Comic book historical eras"""
    PLATINUM = "platinum"
    GOLDEN = "golden"
    SILVER = "silver"
    BRONZE = "bronze"
    COPPER = "copper"
    MODERN = "modern"


@dataclass
class EraConfig:
    """Configuration for a comic era"""
    name: str
    years: str
    start_year: int
    end_year: int
    description: str
    weight_adjustments: Dict[str, float]
    common_defects: List[str]
    grading_notes: str
    prompt_additions: List[str]


@dataclass
class DefectImpact:
    """Impact of a defect on grade"""
    category: str
    defect_type: str
    severity: str
    grade_impact: float


class EraGradingSystem:
    """
    Era-specific comic book grading system

    Provides specialized grading prompts and criteria based on the comic's era,
    with appropriate weight adjustments and defect considerations.
    """

    def __init__(self, config_path: str = None):
        self.config_path = config_path or str(
            Path(__file__).parent.parent / "config" / "era_grading_prompts.json"
        )
        self._config: Dict[str, Any] = {}
        self._eras: Dict[str, EraConfig] = {}
        self._load_config()

    def _load_config(self):
        """Load era grading configuration"""
        try:
            with open(self.config_path, 'r') as f:
                self._config = json.load(f)

            # Parse era configurations
            for era_key, era_data in self._config.get('eras', {}).items():
                years = era_data.get('years', '0-0')
                year_match = re.match(r'(\d{4})-(\d{4}|present)', years)
                if year_match:
                    start = int(year_match.group(1))
                    end = int(year_match.group(2)) if year_match.group(2) != 'present' else datetime.now().year
                else:
                    start, end = 0, 0

                self._eras[era_key] = EraConfig(
                    name=era_data.get('name', ''),
                    years=years,
                    start_year=start,
                    end_year=end,
                    description=era_data.get('description', ''),
                    weight_adjustments=era_data.get('weight_adjustments', {}),
                    common_defects=era_data.get('common_defects', []),
                    grading_notes=era_data.get('grading_notes', ''),
                    prompt_additions=era_data.get('prompt_additions', [])
                )

            logger.info(f"Loaded {len(self._eras)} era configurations")

        except FileNotFoundError:
            logger.warning(f"Era config not found at {self.config_path}, using defaults")
            self._create_default_config()
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing era config: {e}")
            self._create_default_config()

    def _create_default_config(self):
        """Create default era configurations"""
        self._eras = {
            'golden': EraConfig(
                name='Golden Age',
                years='1938-1956',
                start_year=1938,
                end_year=1956,
                description='First superhero comics',
                weight_adjustments={'paper_quality': 0.12, 'staple_condition': 0.12},
                common_defects=['Marvel chipping', 'Spine roll', 'Rusty staples'],
                grading_notes='Be lenient on paper quality due to era standards',
                prompt_additions=['Check for Marvel chipping', 'Assess staple rust']
            ),
            'silver': EraConfig(
                name='Silver Age',
                years='1956-1970',
                start_year=1956,
                end_year=1970,
                description='Marvel Comics revolution',
                weight_adjustments={'color_retention': 0.15, 'cover_gloss': 0.15},
                common_defects=['Subscription creases', 'Value stamp clipping'],
                grading_notes='Cover gloss is key differentiator',
                prompt_additions=['Check Marvel value stamps', 'Examine cover gloss']
            ),
            'bronze': EraConfig(
                name='Bronze Age',
                years='1970-1984',
                start_year=1970,
                end_year=1984,
                description='Mature themes era',
                weight_adjustments={'cover_gloss': 0.18, 'structural_integrity': 0.10},
                common_defects=['Spine stress', 'Reading creases'],
                grading_notes='Newsstand vs direct market distinction',
                prompt_additions=['Check spine stress lines', 'Distinguish edition types']
            ),
            'modern': EraConfig(
                name='Modern Age',
                years='1991-present',
                start_year=1991,
                end_year=datetime.now().year,
                description='Current era',
                weight_adjustments={'cover_gloss': 0.22, 'paper_quality': 0.03},
                common_defects=['Manufacturing defects', 'Shipping damage'],
                grading_notes='High standards expected - scrutinize minor defects',
                prompt_additions=['Check for manufacturing defects', 'Assess centering']
            )
        }

    def detect_era(
        self,
        publication_year: int = None,
        publisher: str = None,
        title: str = None,
        issue_number: str = None
    ) -> ComicEra:
        """
        Detect comic era from metadata

        Args:
            publication_year: Year of publication
            publisher: Publisher name
            title: Comic title
            issue_number: Issue number

        Returns:
            Detected ComicEra
        """
        # If we have a publication year, use it directly
        if publication_year:
            for era_key, era_config in self._eras.items():
                if era_config.start_year <= publication_year <= era_config.end_year:
                    return ComicEra(era_key)

        # Try keyword detection from title/publisher
        keywords = self._config.get('era_detection_keywords', {})
        search_text = f"{publisher or ''} {title or ''} {issue_number or ''}".lower()

        for era_key, era_keywords in keywords.items():
            for keyword in era_keywords:
                if keyword.lower() in search_text:
                    return ComicEra(era_key)

        # Default to modern if can't determine
        return ComicEra.MODERN

    def get_era_config(self, era: ComicEra) -> Optional[EraConfig]:
        """Get configuration for an era"""
        return self._eras.get(era.value)

    def generate_grading_prompt(
        self,
        era: ComicEra,
        metadata: Dict[str, Any] = None,
        include_base: bool = True
    ) -> str:
        """
        Generate era-specific grading prompt

        Args:
            era: Comic era
            metadata: Additional comic metadata
            include_base: Include base grading instructions

        Returns:
            Complete grading prompt string
        """
        era_config = self.get_era_config(era)
        if not era_config:
            era_config = self._eras.get('modern')

        prompt_parts = []

        # Base system prompt
        if include_base:
            base = self._config.get('base_grading_prompt', {})
            prompt_parts.append(base.get('system', ''))
            prompt_parts.append("\n\n## Base Grading Instructions:")
            for instruction in base.get('instructions', []):
                prompt_parts.append(f"- {instruction}")

        # Era-specific context
        prompt_parts.append(f"\n\n## Era Context: {era_config.name} ({era_config.years})")
        prompt_parts.append(f"\n{era_config.description}")
        prompt_parts.append(f"\n\n### Era-Specific Grading Notes:\n{era_config.grading_notes}")

        # Common defects for this era
        prompt_parts.append(f"\n\n### Common {era_config.name} Defects to Check:")
        for defect in era_config.common_defects:
            prompt_parts.append(f"- {defect}")

        # Era-specific instructions
        prompt_parts.append(f"\n\n### {era_config.name} Specific Instructions:")
        for addition in era_config.prompt_additions:
            prompt_parts.append(f"- {addition}")

        # Metadata context if provided
        if metadata:
            prompt_parts.append("\n\n## Comic Being Graded:")
            if metadata.get('title'):
                prompt_parts.append(f"- Title: {metadata['title']}")
            if metadata.get('issue_number'):
                prompt_parts.append(f"- Issue: #{metadata['issue_number']}")
            if metadata.get('publisher'):
                prompt_parts.append(f"- Publisher: {metadata['publisher']}")
            if metadata.get('publication_year'):
                prompt_parts.append(f"- Year: {metadata['publication_year']}")
            if metadata.get('key_issue'):
                prompt_parts.append(f"- Key Issue Notes: {metadata['key_issue']}")

        # Response format
        prompt_parts.append("\n\n## Required Response Format:")
        prompt_parts.append("""
Please provide your assessment in the following JSON format:
{
    "grade": <numeric grade 0.5-10.0>,
    "grade_label": "<grade label e.g. 'Near Mint/Mint'>",
    "confidence": <confidence percentage 0-100>,
    "era_detected": "<detected era>",
    "defects": [
        {
            "category": "<cover|spine|staples|pages|corners>",
            "type": "<defect type>",
            "severity": "<minor|moderate|major>",
            "location": "<location description>",
            "impact": <grade impact>
        }
    ],
    "positive_attributes": ["<list of positive condition notes>"],
    "era_considerations": "<how era affected grading>",
    "restoration_detected": <true|false>,
    "restoration_notes": "<if applicable>",
    "page_quality": "<white|off-white|cream|tan|brown>",
    "cover_gloss": "<high|medium|low>",
    "overall_notes": "<summary assessment>"
}
""")

        return "\n".join(prompt_parts)

    def get_weight_adjustments(self, era: ComicEra) -> Dict[str, float]:
        """Get grading weight adjustments for era"""
        era_config = self.get_era_config(era)
        if era_config:
            return era_config.weight_adjustments
        return {}

    def calculate_adjusted_grade(
        self,
        base_grade: float,
        defects: List[DefectImpact],
        era: ComicEra
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate era-adjusted grade from defects

        Args:
            base_grade: Starting grade (typically 10.0)
            defects: List of detected defects
            era: Comic era

        Returns:
            Tuple of (final_grade, adjustment_details)
        """
        defect_categories = self._config.get('defect_categories', {})
        weight_adjustments = self.get_weight_adjustments(era)

        total_deduction = 0.0
        adjustment_details = {
            'base_grade': base_grade,
            'era': era.value,
            'defect_deductions': [],
            'weight_adjustments_applied': weight_adjustments
        }

        for defect in defects:
            # Get base impact from config
            category_defects = defect_categories.get(defect.category, {})
            defect_impacts = category_defects.get(defect.defect_type, {})
            base_impact = defect_impacts.get(defect.severity, defect.grade_impact)

            # Apply era weight adjustment if applicable
            era_weight = weight_adjustments.get(f"{defect.category}_condition", 1.0)
            adjusted_impact = base_impact * era_weight

            total_deduction += abs(adjusted_impact)
            adjustment_details['defect_deductions'].append({
                'defect': f"{defect.category}/{defect.defect_type}",
                'severity': defect.severity,
                'base_impact': base_impact,
                'era_weight': era_weight,
                'adjusted_impact': adjusted_impact
            })

        final_grade = max(0.5, base_grade - total_deduction)

        # Round to CGC scale (0.5 increments below 9.0, 0.2 increments above)
        final_grade = self._round_to_cgc_scale(final_grade)

        adjustment_details['total_deduction'] = total_deduction
        adjustment_details['final_grade'] = final_grade

        return final_grade, adjustment_details

    def _round_to_cgc_scale(self, grade: float) -> float:
        """Round grade to valid CGC scale value"""
        if grade >= 9.0:
            # 0.2 increments: 9.0, 9.2, 9.4, 9.6, 9.8, 9.9, 10.0
            valid_grades = [9.0, 9.2, 9.4, 9.6, 9.8, 9.9, 10.0]
        else:
            # 0.5 increments: 0.5, 1.0, 1.5, ..., 8.5
            valid_grades = [x / 2 for x in range(1, 18)]  # 0.5 to 8.5

        # Find closest valid grade
        return min(valid_grades, key=lambda x: abs(x - grade))

    def get_grade_label(self, grade: float) -> str:
        """Get grade label for numeric grade"""
        grade_scale = self._config.get('base_grading_prompt', {}).get('grade_scale', {})
        return grade_scale.get(str(grade), f"Grade {grade}")

    def get_common_defects(self, era: ComicEra) -> List[str]:
        """Get common defects for an era"""
        era_config = self.get_era_config(era)
        if era_config:
            return era_config.common_defects
        return []

    def validate_grade_for_era(
        self,
        grade: float,
        era: ComicEra,
        defects: List[DefectImpact]
    ) -> Dict[str, Any]:
        """
        Validate if a grade is reasonable for the era and defects

        Returns validation result with warnings
        """
        result = {
            'valid': True,
            'warnings': [],
            'suggestions': []
        }

        era_config = self.get_era_config(era)
        if not era_config:
            return result

        # Check if grade seems too high for number of defects
        if grade >= 9.8 and len(defects) > 0:
            result['warnings'].append(
                f"Grade {grade} is very high but {len(defects)} defects were noted"
            )

        # Era-specific validations
        if era == ComicEra.GOLDEN and grade >= 9.0:
            result['warnings'].append(
                "Golden Age 9.0+ grades are extremely rare - verify all defects carefully"
            )

        if era == ComicEra.PLATINUM and grade >= 8.0:
            result['warnings'].append(
                "Platinum Age 8.0+ grades are exceptionally rare"
            )

        # Check for missing common defects
        defect_types = {d.defect_type for d in defects}
        for common_defect in era_config.common_defects[:3]:  # Check top 3
            defect_key = common_defect.lower().split()[0]
            if defect_key not in str(defect_types).lower():
                result['suggestions'].append(
                    f"Consider checking for: {common_defect}"
                )

        return result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_grading_system: Optional[EraGradingSystem] = None


def get_era_grading_system() -> EraGradingSystem:
    """Get or create era grading system instance"""
    global _grading_system
    if _grading_system is None:
        _grading_system = EraGradingSystem()
    return _grading_system


def detect_comic_era(
    publication_year: int = None,
    publisher: str = None,
    title: str = None
) -> ComicEra:
    """Convenience function to detect comic era"""
    system = get_era_grading_system()
    return system.detect_era(publication_year, publisher, title)


def generate_era_prompt(
    era: ComicEra,
    metadata: Dict[str, Any] = None
) -> str:
    """Convenience function to generate era-specific prompt"""
    system = get_era_grading_system()
    return system.generate_grading_prompt(era, metadata)


# Export public interface
__all__ = [
    'ComicEra',
    'EraConfig',
    'DefectImpact',
    'EraGradingSystem',
    'get_era_grading_system',
    'detect_comic_era',
    'generate_era_prompt',
]
