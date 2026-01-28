"""
Multi-AI Consensus Grading Orchestrator
Runs multiple AI models in parallel and calculates weighted consensus

With Raistlin Voice Feedback Integration
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter
from datetime import datetime
from statistics import mean, stdev
from dataclasses import dataclass, field

from models import (
    Defect, DefectType, DefectSeverity, GradeLabel,
    ConsensusGrade, AIGradeResult
)

# Import grading events for Raistlin voice triggers
try:
    from grading_events import (
        emit_grading_started,
        emit_grading_complete,
        emit_ready_for_database,
        emit_key_issue_detected,
        emit_error,
        init_voice_triggers
    )
    EVENTS_AVAILABLE = True
except ImportError:
    EVENTS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class GraderConfig:
    """Configuration for individual AI graders"""
    enabled: bool = True
    weight: float = 1.0
    timeout_seconds: int = 30
    retry_attempts: int = 2
    min_confidence: float = 0.5


class ConsensusGrader:
    """
    Orchestrates multi-AI grading with consensus calculation

    Features:
    - Parallel execution of all AI providers
    - Weighted consensus based on provider confidence and quality
    - Defect confirmation (2+ models must agree)
    - Quality penalty adjustment
    - Manual review flagging for low agreement
    """

    def __init__(self, enable_voice_feedback: bool = True):
        # Provider weights (sum to 1.0 for each side)
        # Updated to match actual providers used in grade_comic()
        self.provider_weights = {
            'claude': 0.35,                  # Highest weight - most accurate
            'gemini': 0.25,                  # Google's model
            'openrouter': 0.15,              # Primary OpenRouter model
            'openrouter_qwen2': 0.10,        # Qwen 2.5 VL via OpenRouter
            'openrouter_llama-3': 0.05,      # Llama Vision via OpenRouter
            'openrouter_gemma-3-27b-it': 0.05,  # Gemma via OpenRouter
            'ollama': 0.05                   # Local backup
        }

        # Cover weights
        self.front_weight = 0.70
        self.back_weight = 0.30

        # Thresholds (lowered since we only have 3 main providers: Claude, Gemini, OpenRouter)
        self.min_providers = 2
        self.agreement_threshold = 0.85
        self.quality_threshold = 0.85
        self.confidence_threshold = 0.80

        # Defect confirmation (minimum providers that must agree)
        self.defect_confirmation_count = 2

        # Grade tolerance for agreement calculation
        self.grade_tolerance = 0.5

        # Initialize Raistlin voice triggers
        # NOTE: Voice triggers are now initialized in main.py startup
        # Do NOT init here to prevent double-speak
        self.voice_enabled = enable_voice_feedback and EVENTS_AVAILABLE
        # Commented out - main.py handles init
        # if self.voice_enabled:
        #     try:
        #         init_voice_triggers(enabled=True)
        #         logger.info("🔮 Raistlin voice feedback enabled")
        #     except Exception as e:
        #         logger.warning(f"Voice triggers init failed: {e}")
        #         self.voice_enabled = False

    async def grade_comic(
        self,
        front_image: str,
        back_image: Optional[str] = None,
        metadata: Dict[str, Any] = None,
        quality_scores: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        Main grading orchestrator

        Args:
            front_image: Path to front cover image
            back_image: Optional path to back cover image
            metadata: Comic metadata (title, publisher, etc.)
            quality_scores: Pre-calculated image quality scores

        Returns:
            Complete consensus grading result
        """
        start_time = time.time()
        metadata = metadata or {}
        quality_scores = quality_scores or {'front': 1.0, 'back': 1.0}

        title = metadata.get('title', 'Unknown')
        issue = metadata.get('issue', '')

        logger.info(f"Starting consensus grading for: {title}")

        # Emit grading started event (triggers Raistlin greeting)
        if self.voice_enabled:
            try:
                await emit_grading_started(title, issue, metadata)
            except Exception as e:
                logger.debug(f"Event emission failed: {e}")

        # Import AI providers - VISION CAPABLE ONLY
        from ai_providers.gemini_grader import grade_with_gemini
        from ai_providers.openrouter_grader import grade_with_openrouter, FREE_VISION_MODELS
        from ai_providers.grok_grader import grade_with_grok

        # NOTE: DeepSeek removed - text-only model, doesn't support vision/images

        # Optional: Try to import new vision providers
        try:
            from ai_providers.together_grader import grade_with_together
            has_together = True
        except ImportError:
            has_together = False

        try:
            from ai_providers.hyperbolic_grader import grade_with_hyperbolic
            has_hyperbolic = True
        except ImportError:
            has_hyperbolic = False

        try:
            from ai_providers.sambanova_grader import grade_with_sambanova
            has_sambanova = True
        except ImportError:
            has_sambanova = False

        # Optional: Try to import claude (may have expired key)
        try:
            from ai_providers.claude_grader import grade_with_claude
            has_claude = True
        except ImportError:
            has_claude = False

        # Optional: Try to import ollama for local LLM grading
        try:
            from ai_providers.ollama_vision_grader import grade_with_ollama
            has_ollama = True
        except ImportError:
            has_ollama = False

        # Helper to create OpenRouter grader with specific model
        # Uses **kwargs to accept metadata as keyword argument from _safe_grade
        def make_openrouter_grader(model_name):
            async def grader(image, metadata=None):
                return await grade_with_openrouter(image, model=model_name, metadata=metadata)
            return grader

        # Grade front cover (parallel execution with multiple providers)
        # Using VISION-CAPABLE models only
        front_tasks = [
            self._safe_grade(grade_with_gemini, front_image, 'gemini', 'front', metadata),
            self._safe_grade(grade_with_grok, front_image, 'grok', 'front', metadata),
        ]

        # Add new free vision providers
        if has_together:
            front_tasks.append(self._safe_grade(grade_with_together, front_image, 'together', 'front', metadata))
        if has_hyperbolic:
            front_tasks.append(self._safe_grade(grade_with_hyperbolic, front_image, 'hyperbolic', 'front', metadata))
        if has_sambanova:
            front_tasks.append(self._safe_grade(grade_with_sambanova, front_image, 'sambanova', 'front', metadata))

        # Add Claude if available (may fail due to expired key - that's OK)
        if has_claude:
            front_tasks.append(self._safe_grade(grade_with_claude, front_image, 'claude', 'front', metadata))

        # Add multiple OpenRouter models for better consensus (use first 3 free models)
        openrouter_models = FREE_VISION_MODELS[:3]
        for model in openrouter_models:
            model_short = model.split('/')[-1].split(':')[0]  # Extract short name
            front_tasks.append(
                self._safe_grade(
                    make_openrouter_grader(model),
                    front_image, f'openrouter_{model_short}', 'front', metadata
                )
            )

        if has_ollama:
            front_tasks.append(self._safe_grade(grade_with_ollama, front_image, 'ollama', 'front', metadata))

        front_results = await asyncio.gather(*front_tasks, return_exceptions=True)
        front_results = self._filter_valid_results(front_results)

        # Grade back cover if available
        back_results = []
        if back_image:
            back_tasks = [
                self._safe_grade(grade_with_gemini, back_image, 'gemini', 'back', metadata),
                self._safe_grade(grade_with_grok, back_image, 'grok', 'back', metadata),
            ]

            # Add new free vision providers
            if has_together:
                back_tasks.append(self._safe_grade(grade_with_together, back_image, 'together', 'back', metadata))
            if has_hyperbolic:
                back_tasks.append(self._safe_grade(grade_with_hyperbolic, back_image, 'hyperbolic', 'back', metadata))
            if has_sambanova:
                back_tasks.append(self._safe_grade(grade_with_sambanova, back_image, 'sambanova', 'back', metadata))

            # Add Claude if available
            if has_claude:
                back_tasks.append(self._safe_grade(grade_with_claude, back_image, 'claude', 'back', metadata))

            # Add multiple OpenRouter models for back cover too
            for model in openrouter_models:
                model_short = model.split('/')[-1].split(':')[0]
                back_tasks.append(
                    self._safe_grade(
                        make_openrouter_grader(model),
                        back_image, f'openrouter_{model_short}', 'back', metadata
                    )
                )

            if has_ollama:
                back_tasks.append(self._safe_grade(grade_with_ollama, back_image, 'ollama', 'back', metadata))

            back_results = await asyncio.gather(*back_tasks, return_exceptions=True)
            back_results = self._filter_valid_results(back_results)

        # Check minimum providers
        if len(front_results) < self.min_providers:
            error_msg = f"Only {len(front_results)} providers responded, minimum {self.min_providers} required"
            # Emit error event (triggers Raistlin error response)
            if self.voice_enabled:
                try:
                    await emit_error(error_msg, title, issue)
                except Exception:
                    pass
            return self._create_error_result("Insufficient AI responses", error_msg)

        # Calculate consensus
        result = self._calculate_consensus(
            front_results,
            back_results,
            quality_scores,
            metadata
        )

        # Merge comic_info from ALL vision graders using VOTING for key fields
        # This creates more accurate metadata by voting on issue_number, title, etc.
        comic_info = {}
        comic_info_sources = {}  # Track which providers contributed each field

        # Collect all values for voting on critical fields
        issue_number_votes = {}  # {normalized_issue: [providers...]}
        title_votes = {}         # {normalized_title: [providers...]}

        for r in front_results:
            provider_info = r.get('comic_info', {})
            provider_name = r.get('provider', 'unknown')

            # Collect issue_number votes
            issue_val = provider_info.get('issue_number')
            if issue_val and issue_val not in [None, '', 'null', 'Unknown', 'unknown']:
                # Normalize issue number (strip leading zeros, whitespace)
                from ai_providers.claude_grader import validate_issue_number
                normalized_issue = validate_issue_number(str(issue_val).strip())
                if normalized_issue:
                    if normalized_issue not in issue_number_votes:
                        issue_number_votes[normalized_issue] = []
                    issue_number_votes[normalized_issue].append(provider_name)

            # Collect title votes
            title_val = provider_info.get('title')
            if title_val and title_val not in [None, '', 'null', 'Unknown', 'unknown']:
                normalized_title = str(title_val).strip()
                if normalized_title not in title_votes:
                    title_votes[normalized_title] = []
                title_votes[normalized_title].append(provider_name)

            # For non-voting fields, use first-come-first-served
            for key, value in provider_info.items():
                if key in ['issue_number', 'title']:
                    continue  # These are handled by voting
                # Only use non-null, non-empty values
                if value and value not in [None, '', 'null', 'Unknown', 'unknown', []]:
                    if not comic_info.get(key):
                        comic_info[key] = value
                        comic_info_sources[key] = [provider_name]
                    elif key not in comic_info_sources:
                        comic_info_sources[key] = [provider_name]
                    elif provider_name not in comic_info_sources[key]:
                        comic_info_sources[key].append(provider_name)

        # Vote on issue_number - pick the one with most votes
        if issue_number_votes:
            winning_issue = max(issue_number_votes.items(), key=lambda x: len(x[1]))
            comic_info['issue_number'] = winning_issue[0]
            comic_info_sources['issue_number'] = winning_issue[1]
            # Log voting results for debugging
            logger.info(f"Issue number votes: {issue_number_votes}")
            logger.info(f"Winning issue: {winning_issue[0]} (votes: {len(winning_issue[1])})")

        # Vote on title - pick the one with most votes
        if title_votes:
            winning_title = max(title_votes.items(), key=lambda x: len(x[1]))
            comic_info['title'] = winning_title[0]
            comic_info_sources['title'] = winning_title[1]

        # Store sources for confidence tracking
        comic_info['_sources'] = comic_info_sources

        # Extract title/issue for research
        extracted_title = comic_info.get('title') or metadata.get('title', title)
        extracted_issue = comic_info.get('issue_number') or metadata.get('issue', issue)
        extracted_publisher = comic_info.get('publisher') or metadata.get('publisher')
        extracted_year = comic_info.get('year') or metadata.get('year')
        is_key = any(r.get('key_issue_info', {}).get('is_key_issue') for r in front_results)
        
        # Run Perplexity research in parallel (pricing + info)
        try:
            from ai_providers.perplexity_research import full_comic_research
            research_result = await full_comic_research(
                title=extracted_title,
                issue_number=extracted_issue,
                grade=result['consensus_grade'],
                publisher=extracted_publisher,
                year=extracted_year
            )
            result['market_research'] = research_result.get('pricing', {})
            result['supplemental_info'] = research_result.get('comic_info', {})
            logger.info(f"Market research complete for {extracted_title} #{extracted_issue}")
        except ImportError:
            logger.debug("Perplexity research module not available")
        except Exception as e:
            logger.warning(f"Market research failed: {e}")
            result['market_research'] = {'error': str(e)}

        # Merge key_issue_info from vision graders
        key_issue_info = {'is_key_issue': False, 'key_reasons': [], 'first_appearances': []}
        for r in front_results:
            ki = r.get('key_issue_info', {})
            if ki.get('is_key_issue'):
                key_issue_info['is_key_issue'] = True
                key_issue_info['key_reasons'].extend(ki.get('key_reasons', []))
                key_issue_info['first_appearances'].extend(ki.get('first_appearances', []))

        # Deduplicate
        key_issue_info['key_reasons'] = list(set(key_issue_info['key_reasons']))
        key_issue_info['first_appearances'] = list(set(key_issue_info['first_appearances']))

        # Aggregate AI pricing estimates from all providers
        ai_pricing_estimates = []
        for r in front_results:
            pricing = r.get('pricing', {})
            if pricing:
                # Parse price values (remove $ and commas)
                def parse_price(val):
                    if isinstance(val, (int, float)):
                        return float(val)
                    if isinstance(val, str):
                        try:
                            return float(val.replace('$', '').replace(',', '').strip())
                        except (ValueError, AttributeError):
                            return None
                    return None

                raw_price = parse_price(pricing.get('estimated_value_raw'))
                graded_price = parse_price(pricing.get('estimated_value_graded'))

                if raw_price or graded_price:
                    ai_pricing_estimates.append({
                        'provider': r.get('provider', 'unknown'),
                        'estimated_value_raw': raw_price,
                        'estimated_value_graded': graded_price,
                        'value_range_low': parse_price(pricing.get('value_range_low')),
                        'value_range_high': parse_price(pricing.get('value_range_high')),
                        'pricing_notes': pricing.get('pricing_notes', '')
                    })

        # Calculate consensus AI pricing if we have estimates
        if ai_pricing_estimates:
            raw_prices = [e['estimated_value_raw'] for e in ai_pricing_estimates if e.get('estimated_value_raw')]
            graded_prices = [e['estimated_value_graded'] for e in ai_pricing_estimates if e.get('estimated_value_graded')]

            result['ai_pricing'] = {
                'estimates': ai_pricing_estimates,
                'consensus_raw': round(mean(raw_prices), 2) if raw_prices else None,
                'consensus_graded': round(mean(graded_prices), 2) if graded_prices else None,
                'num_estimates': len(ai_pricing_estimates)
            }
            logger.info(f"AI pricing: raw=${result['ai_pricing'].get('consensus_raw')}, graded=${result['ai_pricing'].get('consensus_graded')} from {len(ai_pricing_estimates)} providers")

        result['comic_info'] = comic_info
        result['key_issue_info'] = key_issue_info

        # Add timing
        result['total_processing_time_ms'] = int((time.time() - start_time) * 1000)

        logger.info(f"Grading complete: {result['consensus_grade']} ({result['grade_label']})")

        # VOICE DISABLED - was causing double-speak
        # Voice feedback now handled by frontend only
        # if self.voice_enabled and result.get('consensus_grade') is not None:
        #     pass  # NO voice events from backend

        return result

    async def _safe_grade(
        self,
        grader_func,
        image_path: str,
        provider: str,
        side: str,
        metadata: Dict
    ) -> Dict[str, Any]:
        """Safely execute grader with timeout and error handling"""
        try:
            start = time.time()
            result = await asyncio.wait_for(
                grader_func(image_path, metadata=metadata),
                timeout=30.0
            )
            processing_time = int((time.time() - start) * 1000)

            return {
                'provider': provider,
                'side': side,
                'grade': result.get('grade', 0),
                'confidence': result.get('confidence', 0.5),
                'defects': result.get('defects', []),
                'reasoning': result.get('reasoning', ''),
                'comic_info': result.get('comic_info', {}),
                'key_issue_info': result.get('key_issue_info', {}),
                'pricing': result.get('pricing', {}),  # AI-estimated pricing
                'processing_time_ms': processing_time,
                'success': True
            }

        except asyncio.TimeoutError:
            logger.warning(f"{provider} timed out for {side} image")
            return {
                'provider': provider,
                'side': side,
                'success': False,
                'error': 'Timeout'
            }

        except Exception as e:
            logger.error(f"{provider} error: {e}")
            return {
                'provider': provider,
                'side': side,
                'success': False,
                'error': str(e)
            }

    def _filter_valid_results(self, results: List) -> List[Dict]:
        """Filter out failed results, exceptions, and zero grades"""
        valid = []
        for r in results:
            if isinstance(r, dict) and r.get('success') and 'grade' in r:
                # Also filter out grade 0 which indicates an error
                if r.get('grade', 0) > 0:
                    valid.append(r)
        return valid

    def _calculate_consensus(
        self,
        front_results: List[Dict],
        back_results: List[Dict],
        quality_scores: Dict[str, float],
        metadata: Dict
    ) -> Dict[str, Any]:
        """Calculate weighted consensus from all AI results"""

        # Extract grades and apply weights
        front_grades = []
        front_weights = []
        for r in front_results:
            grade = r['grade']
            provider = r['provider']
            confidence = r.get('confidence', 0.7)

            # Base weight + confidence adjustment
            weight = self.provider_weights.get(provider, 0.1) * confidence
            front_grades.append(grade)
            front_weights.append(weight)

        # Calculate weighted front average
        if front_weights:
            total_weight = sum(front_weights)
            front_avg = sum(g * w for g, w in zip(front_grades, front_weights)) / total_weight
        else:
            front_avg = 5.0  # Default if no valid grades

        # Calculate back average (if available)
        back_avg = front_avg  # Default to front if no back
        if back_results:
            back_grades = []
            back_weights = []
            for r in back_results:
                grade = r['grade']
                provider = r['provider']
                confidence = r.get('confidence', 0.7)
                weight = self.provider_weights.get(provider, 0.1) * confidence
                back_grades.append(grade)
                back_weights.append(weight)

            if back_weights:
                total_weight = sum(back_weights)
                back_avg = sum(g * w for g, w in zip(back_grades, back_weights)) / total_weight

        # Combine front and back with weights
        raw_consensus = (front_avg * self.front_weight) + (back_avg * self.back_weight)

        # Apply quality penalties
        quality_penalty = 0.0
        if quality_scores.get('front', 1.0) < self.quality_threshold:
            penalty = (self.quality_threshold - quality_scores['front']) * 0.5
            quality_penalty += penalty
        if quality_scores.get('back', 1.0) < self.quality_threshold:
            penalty = (self.quality_threshold - quality_scores['back']) * 0.2
            quality_penalty += penalty

        final_grade = max(0.5, min(10.0, raw_consensus - quality_penalty))
        final_grade = round(final_grade * 2) / 2  # Round to nearest 0.5

        # Calculate agreement and standard deviation
        all_grades = front_grades + [r['grade'] for r in back_results]
        std_deviation = stdev(all_grades) if len(all_grades) > 1 else 0

        # Agreement = percentage of grades within tolerance
        grades_in_tolerance = sum(1 for g in all_grades if abs(g - final_grade) <= self.grade_tolerance)
        agreement = grades_in_tolerance / len(all_grades) if all_grades else 0

        # Calculate confidence
        confidence = self._calculate_confidence(agreement, std_deviation, len(all_grades))

        # Process defects
        confirmed_defects = self._process_defects(front_results, back_results)

        # Determine if manual review needed
        needs_review, review_reason = self._check_manual_review(
            agreement, confidence, std_deviation, all_grades
        )

        # Build individual grades dictionary
        individual_grades = {}
        for r in front_results:
            individual_grades[f"{r['provider']}_front"] = r
        for r in back_results:
            individual_grades[f"{r['provider']}_back"] = r

        return {
            'consensus_grade': final_grade,
            'grade_label': ConsensusGrade.grade_to_label(final_grade).value,
            'confidence': round(confidence, 3),
            'front_grade': round(front_avg, 2),
            'back_grade': round(back_avg, 2),
            'agreement_percentage': round(agreement, 3),
            'standard_deviation': round(std_deviation, 3),
            'quality_adjusted': quality_penalty > 0,
            'quality_penalty': round(quality_penalty, 3),
            'confirmed_defects': confirmed_defects,
            'individual_grades': individual_grades,
            'requires_manual_review': needs_review,
            'review_reason': review_reason,
            'grading_timestamp': datetime.utcnow().isoformat()
        }

    def _calculate_confidence(
        self,
        agreement: float,
        std_deviation: float,
        num_providers: int
    ) -> float:
        """Calculate overall grading confidence"""
        # Base confidence from agreement
        confidence = agreement * 0.5

        # Bonus for low standard deviation
        if std_deviation < 0.5:
            confidence += 0.3
        elif std_deviation < 1.0:
            confidence += 0.2
        elif std_deviation < 1.5:
            confidence += 0.1

        # Bonus for more providers
        provider_bonus = min(0.2, (num_providers - self.min_providers) * 0.05)
        confidence += provider_bonus

        return min(1.0, confidence)

    def _process_defects(
        self,
        front_results: List[Dict],
        back_results: List[Dict]
    ) -> List[Dict]:
        """
        Process and confirm defects
        Only defects detected by 2+ providers are confirmed
        """
        all_defects = []

        # Collect all defects
        for r in front_results + back_results:
            for defect in r.get('defects', []):
                if isinstance(defect, str):
                    all_defects.append({
                        'type': defect,
                        'provider': r['provider'],
                        'side': r['side']
                    })
                elif isinstance(defect, dict):
                    defect['provider'] = r['provider']
                    defect['side'] = r['side']
                    all_defects.append(defect)

        # Count defect occurrences
        defect_counts = Counter()
        defect_details = {}

        for d in all_defects:
            defect_type = d.get('type', str(d))
            defect_counts[defect_type] += 1

            if defect_type not in defect_details:
                defect_details[defect_type] = {
                    'providers': [],
                    'severities': [],
                    'locations': []
                }

            defect_details[defect_type]['providers'].append(d.get('provider'))
            if 'severity' in d:
                defect_details[defect_type]['severities'].append(d['severity'])
            if 'location' in d:
                defect_details[defect_type]['locations'].append(d['location'])

        # Confirm defects with 2+ detections
        confirmed = []
        for defect_type, count in defect_counts.items():
            if count >= self.defect_confirmation_count:
                details = defect_details[defect_type]

                # Determine severity (use most common or worst)
                severity = 'moderate'
                if details['severities']:
                    severity = Counter(details['severities']).most_common(1)[0][0]

                confirmed.append({
                    'type': defect_type,
                    'severity': severity,
                    'detection_count': count,
                    'detected_by': list(set(details['providers'])),
                    'locations': list(set(details['locations'])) if details['locations'] else []
                })

        return confirmed

    def _check_manual_review(
        self,
        agreement: float,
        confidence: float,
        std_deviation: float,
        all_grades: List[float]
    ) -> Tuple[bool, Optional[str]]:
        """Determine if manual review is required"""
        reasons = []

        if agreement < self.agreement_threshold:
            reasons.append(f"Low agreement ({agreement:.1%})")

        if confidence < self.confidence_threshold:
            reasons.append(f"Low confidence ({confidence:.1%})")

        if std_deviation > 1.5:
            reasons.append(f"High variance (σ={std_deviation:.2f})")

        if len(all_grades) < self.min_providers:
            reasons.append(f"Insufficient providers ({len(all_grades)})")

        # Check for outliers
        if all_grades:
            mean_grade = mean(all_grades)
            outliers = [g for g in all_grades if abs(g - mean_grade) > 2.0]
            if outliers:
                reasons.append(f"Outlier grades detected")

        if reasons:
            return True, "; ".join(reasons)

        return False, None

    def _create_error_result(self, message: str, detail: str) -> Dict[str, Any]:
        """Create error result dictionary"""
        return {
            'consensus_grade': None,
            'grade_label': None,
            'confidence': 0,
            'error': message,
            'error_detail': detail,
            'requires_manual_review': True,
            'review_reason': f"{message}: {detail}",
            'grading_timestamp': datetime.utcnow().isoformat()
        }

    async def regrade_with_specific_providers(
        self,
        image_path: str,
        providers: List[str],
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """Regrade using only specific providers (for debugging/comparison)"""
        from ai_providers.claude_grader import grade_with_claude
        from ai_providers.gemini_grader import grade_with_gemini
        from ai_providers.openrouter_grader import grade_with_openrouter

        provider_map = {
            'claude': grade_with_claude,
            'gemini': grade_with_gemini,
            'openrouter': grade_with_openrouter,
        }

        # Optionally add ollama if available
        try:
            from ai_providers.ollama_vision_grader import grade_with_ollama
            provider_map['ollama'] = grade_with_ollama
        except ImportError:
            pass

        tasks = []
        for provider in providers:
            if provider in provider_map:
                tasks.append(self._safe_grade(
                    provider_map[provider],
                    image_path,
                    provider,
                    'front',
                    metadata or {}
                ))

        results = await asyncio.gather(*tasks)
        valid_results = self._filter_valid_results(results)

        return {
            'provider_results': valid_results,
            'average_grade': mean([r['grade'] for r in valid_results]) if valid_results else None
        }


# Global instance
consensus_grader = ConsensusGrader()
