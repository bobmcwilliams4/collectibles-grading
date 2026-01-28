"""
Parallel Grading Optimization
Optimizes AI grading by processing front/back covers in parallel
with intelligent provider selection and result aggregation
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class GradingSide(Enum):
    """Cover side being graded"""
    FRONT = "front"
    BACK = "back"
    COMBINED = "combined"


@dataclass
class ProviderResult:
    """Result from a single AI provider"""
    provider: str
    grade: float
    confidence: float
    defects: List[Dict[str, Any]]
    raw_response: Dict[str, Any]
    latency_ms: float
    success: bool
    error: Optional[str] = None
    side: GradingSide = GradingSide.COMBINED


@dataclass
class ParallelGradingResult:
    """Combined result from parallel grading"""
    front_results: List[ProviderResult] = field(default_factory=list)
    back_results: List[ProviderResult] = field(default_factory=list)
    consensus_grade: float = 0.0
    front_grade: float = 0.0
    back_grade: float = 0.0
    confidence: float = 0.0
    combined_defects: List[Dict[str, Any]] = field(default_factory=list)
    provider_agreement: float = 0.0
    total_latency_ms: float = 0.0
    parallel_efficiency: float = 0.0


@dataclass
class ProviderHealth:
    """Health metrics for an AI provider"""
    provider: str
    success_rate: float = 1.0
    avg_latency_ms: float = 1000.0
    recent_failures: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    total_requests: int = 0
    dynamic_weight: float = 1.0


class ParallelGradingEngine:
    """
    Parallel grading engine that optimizes AI provider usage

    Features:
    - Parallel front/back cover grading
    - Concurrent multi-provider grading
    - Dynamic provider selection based on health
    - Intelligent result aggregation
    - Automatic retry with fallback
    """

    # Default provider weights
    DEFAULT_WEIGHTS = {
        'claude': 0.35,
        'gemini': 0.25,
        'openrouter': 0.20,
        'huggingface': 0.15,
        'local': 0.05
    }

    # Front/back weight ratio (front is more important for grading)
    FRONT_WEIGHT = 0.70
    BACK_WEIGHT = 0.30

    # Minimum agreement threshold for consensus
    MIN_AGREEMENT = 0.85

    def __init__(
        self,
        providers: Dict[str, Callable] = None,
        weights: Dict[str, float] = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 2
    ):
        self.providers = providers or {}
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.timeout = timeout_seconds
        self.max_retries = max_retries

        # Provider health tracking
        self._provider_health: Dict[str, ProviderHealth] = {}
        for provider in self.weights:
            self._provider_health[provider] = ProviderHealth(provider=provider)

        # Results cache for deduplication
        self._recent_results: Dict[str, Tuple[datetime, Any]] = {}
        self._cache_ttl = timedelta(hours=1)

    def register_provider(
        self,
        name: str,
        grading_func: Callable,
        weight: float = 0.1
    ):
        """Register an AI grading provider"""
        self.providers[name] = grading_func
        self.weights[name] = weight
        self._provider_health[name] = ProviderHealth(provider=name)
        logger.info(f"Registered provider: {name} with weight {weight}")

    async def grade_parallel(
        self,
        front_image: str,
        back_image: str = None,
        metadata: Dict[str, Any] = None,
        era_prompt: str = None
    ) -> ParallelGradingResult:
        """
        Grade comic with parallel front/back processing

        Args:
            front_image: Path to front cover image
            back_image: Optional path to back cover image
            metadata: Comic metadata for context
            era_prompt: Era-specific grading prompt

        Returns:
            ParallelGradingResult with consensus grade
        """
        start_time = time.time()
        result = ParallelGradingResult()

        # Create tasks for parallel execution
        tasks = []

        # Front cover grading (always required)
        front_task = asyncio.create_task(
            self._grade_with_all_providers(
                front_image,
                GradingSide.FRONT,
                metadata,
                era_prompt
            )
        )
        tasks.append(('front', front_task))

        # Back cover grading (if provided)
        if back_image:
            back_task = asyncio.create_task(
                self._grade_with_all_providers(
                    back_image,
                    GradingSide.BACK,
                    metadata,
                    era_prompt
                )
            )
            tasks.append(('back', back_task))

        # Wait for all tasks to complete
        completed_tasks = await asyncio.gather(
            *[task for _, task in tasks],
            return_exceptions=True
        )

        # Process results
        for (side, _), task_result in zip(tasks, completed_tasks):
            if isinstance(task_result, Exception):
                logger.error(f"Error grading {side}: {task_result}")
                continue

            if side == 'front':
                result.front_results = task_result
            else:
                result.back_results = task_result

        # Calculate consensus
        result = self._calculate_consensus(result)

        # Calculate timing metrics
        result.total_latency_ms = (time.time() - start_time) * 1000

        # Calculate parallel efficiency
        if result.front_results:
            max_front_latency = max(r.latency_ms for r in result.front_results if r.success)
            max_back_latency = max((r.latency_ms for r in result.back_results if r.success), default=0)
            sequential_time = max_front_latency + max_back_latency
            if sequential_time > 0:
                result.parallel_efficiency = sequential_time / result.total_latency_ms

        return result

    async def _grade_with_all_providers(
        self,
        image_path: str,
        side: GradingSide,
        metadata: Dict[str, Any] = None,
        era_prompt: str = None
    ) -> List[ProviderResult]:
        """Grade image with all available providers in parallel"""
        results = []

        # Select providers based on health and availability
        active_providers = self._select_providers()

        # Create concurrent grading tasks
        tasks = []
        for provider_name in active_providers:
            if provider_name in self.providers:
                task = asyncio.create_task(
                    self._grade_with_provider(
                        provider_name,
                        image_path,
                        side,
                        metadata,
                        era_prompt
                    )
                )
                tasks.append((provider_name, task))

        # Wait for all providers with timeout
        try:
            completed = await asyncio.wait_for(
                asyncio.gather(*[t for _, t in tasks], return_exceptions=True),
                timeout=self.timeout
            )

            for (provider_name, _), result in zip(tasks, completed):
                if isinstance(result, Exception):
                    results.append(ProviderResult(
                        provider=provider_name,
                        grade=0,
                        confidence=0,
                        defects=[],
                        raw_response={},
                        latency_ms=0,
                        success=False,
                        error=str(result),
                        side=side
                    ))
                    self._record_failure(provider_name)
                else:
                    results.append(result)
                    if result.success:
                        self._record_success(provider_name, result.latency_ms)

        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for providers on {side.value}")
            # Return any results we got
            for provider_name, task in tasks:
                if task.done() and not task.cancelled():
                    try:
                        result = task.result()
                        if not isinstance(result, Exception):
                            results.append(result)
                    except Exception:
                        pass

        return results

    async def _grade_with_provider(
        self,
        provider_name: str,
        image_path: str,
        side: GradingSide,
        metadata: Dict[str, Any] = None,
        era_prompt: str = None,
        retry_count: int = 0
    ) -> ProviderResult:
        """Grade image with a single provider"""
        start_time = time.time()
        grading_func = self.providers.get(provider_name)

        if not grading_func:
            return ProviderResult(
                provider=provider_name,
                grade=0,
                confidence=0,
                defects=[],
                raw_response={},
                latency_ms=0,
                success=False,
                error="Provider not found",
                side=side
            )

        try:
            # Call the provider's grading function
            response = await grading_func(
                image_path=image_path,
                metadata=metadata,
                prompt=era_prompt,
                side=side.value
            )

            latency_ms = (time.time() - start_time) * 1000

            return ProviderResult(
                provider=provider_name,
                grade=response.get('grade', 0),
                confidence=response.get('confidence', 0),
                defects=response.get('defects', []),
                raw_response=response,
                latency_ms=latency_ms,
                success=True,
                side=side
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Provider {provider_name} error: {e}")

            # Retry logic
            if retry_count < self.max_retries:
                logger.info(f"Retrying {provider_name} (attempt {retry_count + 1})")
                await asyncio.sleep(0.5 * (retry_count + 1))  # Exponential backoff
                return await self._grade_with_provider(
                    provider_name, image_path, side, metadata, era_prompt, retry_count + 1
                )

            return ProviderResult(
                provider=provider_name,
                grade=0,
                confidence=0,
                defects=[],
                raw_response={},
                latency_ms=latency_ms,
                success=False,
                error=str(e),
                side=side
            )

    def _select_providers(self) -> List[str]:
        """Select providers based on health metrics"""
        available = []

        for provider, health in self._provider_health.items():
            # Skip providers with too many recent failures
            if health.recent_failures >= 3:
                if health.last_failure and \
                   datetime.utcnow() - health.last_failure < timedelta(minutes=5):
                    logger.debug(f"Skipping unhealthy provider: {provider}")
                    continue

            # Calculate dynamic weight based on health
            health.dynamic_weight = self.weights.get(provider, 0.1) * health.success_rate

            # Penalize slow providers
            if health.avg_latency_ms > 10000:  # > 10 seconds
                health.dynamic_weight *= 0.5

            available.append(provider)

        # Sort by dynamic weight (highest first)
        available.sort(
            key=lambda p: self._provider_health[p].dynamic_weight,
            reverse=True
        )

        return available

    def _calculate_consensus(self, result: ParallelGradingResult) -> ParallelGradingResult:
        """Calculate consensus grade from provider results"""
        # Calculate front grade
        front_grades = [r.grade for r in result.front_results if r.success and r.grade > 0]
        if front_grades:
            result.front_grade = self._weighted_average(
                result.front_results,
                [r for r in result.front_results if r.success]
            )

        # Calculate back grade
        back_grades = [r.grade for r in result.back_results if r.success and r.grade > 0]
        if back_grades:
            result.back_grade = self._weighted_average(
                result.back_results,
                [r for r in result.back_results if r.success]
            )

        # Combine front/back with weights
        if result.front_grade > 0 and result.back_grade > 0:
            result.consensus_grade = (
                result.front_grade * self.FRONT_WEIGHT +
                result.back_grade * self.BACK_WEIGHT
            )
        elif result.front_grade > 0:
            result.consensus_grade = result.front_grade
        else:
            result.consensus_grade = result.back_grade

        # Round to CGC scale
        result.consensus_grade = self._round_to_cgc_scale(result.consensus_grade)

        # Calculate provider agreement
        all_grades = front_grades + back_grades
        if len(all_grades) >= 2:
            grade_std = statistics.stdev(all_grades) if len(all_grades) > 1 else 0
            # Convert std dev to agreement percentage (lower std = higher agreement)
            result.provider_agreement = max(0, 1 - (grade_std / 2))

        # Calculate confidence based on agreement and number of providers
        successful_count = len([r for r in result.front_results + result.back_results if r.success])
        result.confidence = result.provider_agreement * min(1.0, successful_count / 4)

        # Combine defects from all results
        result.combined_defects = self._merge_defects(
            result.front_results,
            result.back_results
        )

        return result

    def _weighted_average(
        self,
        all_results: List[ProviderResult],
        successful_results: List[ProviderResult]
    ) -> float:
        """Calculate weighted average grade from provider results"""
        if not successful_results:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for result in successful_results:
            weight = self.weights.get(result.provider, 0.1)
            # Apply confidence as additional weight modifier
            weight *= result.confidence / 100 if result.confidence > 0 else 0.5
            # Apply health-based weight adjustment
            health = self._provider_health.get(result.provider)
            if health:
                weight *= health.dynamic_weight

            weighted_sum += result.grade * weight
            total_weight += weight

        if total_weight > 0:
            return weighted_sum / total_weight
        return 0.0

    def _merge_defects(
        self,
        front_results: List[ProviderResult],
        back_results: List[ProviderResult]
    ) -> List[Dict[str, Any]]:
        """Merge and deduplicate defects from all results"""
        all_defects = []
        seen_defects = set()

        for result in front_results + back_results:
            if not result.success:
                continue

            for defect in result.defects:
                # Create unique key for deduplication
                key = (
                    defect.get('category', ''),
                    defect.get('type', ''),
                    defect.get('location', '')
                )

                if key not in seen_defects:
                    seen_defects.add(key)
                    defect['confirmed_by'] = [result.provider]
                    defect['side'] = result.side.value
                    all_defects.append(defect)
                else:
                    # Add confirming provider to existing defect
                    for existing in all_defects:
                        if (existing.get('category') == defect.get('category') and
                            existing.get('type') == defect.get('type')):
                            if result.provider not in existing.get('confirmed_by', []):
                                existing['confirmed_by'].append(result.provider)
                            break

        # Filter to only defects confirmed by 2+ providers (for reliability)
        confirmed_defects = [
            d for d in all_defects
            if len(d.get('confirmed_by', [])) >= 2 or
               d.get('severity', '') == 'major'  # Always include major defects
        ]

        return confirmed_defects

    def _round_to_cgc_scale(self, grade: float) -> float:
        """Round grade to valid CGC scale value"""
        if grade >= 9.0:
            valid_grades = [9.0, 9.2, 9.4, 9.6, 9.8, 9.9, 10.0]
        else:
            valid_grades = [x / 2 for x in range(1, 18)]

        return min(valid_grades, key=lambda x: abs(x - grade))

    def _record_success(self, provider: str, latency_ms: float):
        """Record successful provider call"""
        health = self._provider_health.get(provider)
        if health:
            health.total_requests += 1
            health.last_success = datetime.utcnow()
            health.recent_failures = 0

            # Update rolling average latency
            if health.avg_latency_ms > 0:
                health.avg_latency_ms = (health.avg_latency_ms * 0.9) + (latency_ms * 0.1)
            else:
                health.avg_latency_ms = latency_ms

            # Update success rate
            health.success_rate = min(1.0, health.success_rate + 0.01)

    def _record_failure(self, provider: str):
        """Record failed provider call"""
        health = self._provider_health.get(provider)
        if health:
            health.total_requests += 1
            health.last_failure = datetime.utcnow()
            health.recent_failures += 1
            health.success_rate = max(0.1, health.success_rate - 0.1)

    def get_provider_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all providers"""
        return {
            provider: {
                'success_rate': health.success_rate,
                'avg_latency_ms': health.avg_latency_ms,
                'recent_failures': health.recent_failures,
                'total_requests': health.total_requests,
                'dynamic_weight': health.dynamic_weight,
                'last_success': health.last_success.isoformat() if health.last_success else None,
                'last_failure': health.last_failure.isoformat() if health.last_failure else None
            }
            for provider, health in self._provider_health.items()
        }

    def reset_provider_health(self, provider: str = None):
        """Reset health metrics for a provider or all providers"""
        if provider:
            if provider in self._provider_health:
                self._provider_health[provider] = ProviderHealth(provider=provider)
        else:
            for p in self._provider_health:
                self._provider_health[p] = ProviderHealth(provider=p)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_grading_engine: Optional[ParallelGradingEngine] = None


def get_parallel_grading_engine() -> ParallelGradingEngine:
    """Get or create parallel grading engine instance"""
    global _grading_engine
    if _grading_engine is None:
        _grading_engine = ParallelGradingEngine()
    return _grading_engine


async def grade_comic_parallel(
    front_image: str,
    back_image: str = None,
    metadata: Dict[str, Any] = None,
    era_prompt: str = None
) -> ParallelGradingResult:
    """Convenience function for parallel grading"""
    engine = get_parallel_grading_engine()
    return await engine.grade_parallel(front_image, back_image, metadata, era_prompt)


# Export public interface
__all__ = [
    'GradingSide',
    'ProviderResult',
    'ParallelGradingResult',
    'ProviderHealth',
    'ParallelGradingEngine',
    'get_parallel_grading_engine',
    'grade_comic_parallel',
]
