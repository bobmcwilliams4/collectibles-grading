"""
Provider Health Tracking and Dynamic Confidence System
Monitors AI provider performance and adjusts weights dynamically
"""

import asyncio
import logging
import statistics
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Provider health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


@dataclass
class ProviderMetrics:
    """Detailed metrics for a provider"""
    provider_name: str
    status: HealthStatus = HealthStatus.HEALTHY

    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeout_requests: int = 0

    # Latency metrics (rolling window)
    latency_history: deque = field(default_factory=lambda: deque(maxlen=100))
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0

    # Quality metrics
    grade_accuracy_scores: deque = field(default_factory=lambda: deque(maxlen=50))
    avg_confidence: float = 0.0
    agreement_rate: float = 0.0  # How often this provider agrees with consensus

    # Time tracking
    last_request: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    downtime_start: Optional[datetime] = None
    total_downtime_seconds: float = 0.0

    # Dynamic weights
    base_weight: float = 0.1
    dynamic_weight: float = 0.1
    weight_adjustment_reason: str = ""

    # Circuit breaker
    consecutive_failures: int = 0
    circuit_open: bool = False
    circuit_open_until: Optional[datetime] = None


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    provider: str
    healthy: bool
    latency_ms: float
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ProviderHealthTracker:
    """
    Tracks and manages AI provider health with dynamic weight adjustment

    Features:
    - Real-time health monitoring
    - Circuit breaker pattern for failing providers
    - Dynamic weight adjustment based on performance
    - Latency percentile tracking
    - Grade accuracy correlation
    """

    # Thresholds
    LATENCY_WARNING_MS = 5000  # 5 seconds
    LATENCY_CRITICAL_MS = 15000  # 15 seconds
    FAILURE_THRESHOLD = 0.3  # 30% failure rate triggers degraded
    CIRCUIT_BREAKER_THRESHOLD = 5  # Consecutive failures to open circuit
    CIRCUIT_BREAKER_TIMEOUT = 60  # Seconds before trying again

    # Weight adjustment bounds
    MIN_WEIGHT = 0.01
    MAX_WEIGHT = 0.50

    def __init__(
        self,
        base_weights: Dict[str, float] = None,
        persistence_path: str = None
    ):
        self._metrics: Dict[str, ProviderMetrics] = {}
        self._base_weights = base_weights or {
            'claude': 0.35,
            'gemini': 0.25,
            'openrouter': 0.20,
            'huggingface': 0.15,
            'local': 0.05
        }
        self._persistence_path = persistence_path
        self._lock = asyncio.Lock()

        # Initialize metrics for known providers
        for provider, weight in self._base_weights.items():
            self._metrics[provider] = ProviderMetrics(
                provider_name=provider,
                base_weight=weight,
                dynamic_weight=weight
            )

        # Load persisted state if available
        self._load_state()

    def _load_state(self):
        """Load persisted health state"""
        if not self._persistence_path:
            return

        try:
            path = Path(self._persistence_path)
            if path.exists():
                with open(path, 'r') as f:
                    state = json.load(f)
                    for provider, data in state.items():
                        if provider in self._metrics:
                            metrics = self._metrics[provider]
                            metrics.total_requests = data.get('total_requests', 0)
                            metrics.successful_requests = data.get('successful_requests', 0)
                            metrics.failed_requests = data.get('failed_requests', 0)
                            metrics.avg_latency_ms = data.get('avg_latency_ms', 0)
                            metrics.dynamic_weight = data.get('dynamic_weight', metrics.base_weight)
                logger.info(f"Loaded health state from {self._persistence_path}")
        except Exception as e:
            logger.warning(f"Could not load health state: {e}")

    def _save_state(self):
        """Persist health state"""
        if not self._persistence_path:
            return

        try:
            state = {}
            for provider, metrics in self._metrics.items():
                state[provider] = {
                    'total_requests': metrics.total_requests,
                    'successful_requests': metrics.successful_requests,
                    'failed_requests': metrics.failed_requests,
                    'avg_latency_ms': metrics.avg_latency_ms,
                    'dynamic_weight': metrics.dynamic_weight
                }

            path = Path(self._persistence_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            logger.warning(f"Could not save health state: {e}")

    async def record_request(
        self,
        provider: str,
        success: bool,
        latency_ms: float,
        grade: float = None,
        confidence: float = None,
        consensus_grade: float = None,
        error: str = None,
        timeout: bool = False
    ):
        """
        Record a provider request and update metrics

        Args:
            provider: Provider name
            success: Whether request succeeded
            latency_ms: Request latency in milliseconds
            grade: Grade returned by provider
            confidence: Confidence score returned
            consensus_grade: Final consensus grade for comparison
            error: Error message if failed
            timeout: Whether request timed out
        """
        async with self._lock:
            if provider not in self._metrics:
                self._metrics[provider] = ProviderMetrics(
                    provider_name=provider,
                    base_weight=self._base_weights.get(provider, 0.1),
                    dynamic_weight=self._base_weights.get(provider, 0.1)
                )

            metrics = self._metrics[provider]
            metrics.total_requests += 1
            metrics.last_request = datetime.utcnow()

            if success:
                metrics.successful_requests += 1
                metrics.last_success = datetime.utcnow()
                metrics.consecutive_failures = 0

                # Update latency metrics
                metrics.latency_history.append(latency_ms)
                self._update_latency_percentiles(metrics)

                # Update quality metrics
                if confidence is not None:
                    if metrics.avg_confidence == 0:
                        metrics.avg_confidence = confidence
                    else:
                        metrics.avg_confidence = (metrics.avg_confidence * 0.9) + (confidence * 0.1)

                # Calculate grade accuracy if consensus available
                if grade is not None and consensus_grade is not None:
                    accuracy = 1 - abs(grade - consensus_grade) / 10
                    metrics.grade_accuracy_scores.append(accuracy)
                    metrics.agreement_rate = statistics.mean(metrics.grade_accuracy_scores)

                # Close circuit if it was open
                if metrics.circuit_open:
                    logger.info(f"Circuit closed for provider {provider}")
                    metrics.circuit_open = False
                    metrics.circuit_open_until = None
                    if metrics.downtime_start:
                        metrics.total_downtime_seconds += (
                            datetime.utcnow() - metrics.downtime_start
                        ).total_seconds()
                        metrics.downtime_start = None

            else:
                metrics.failed_requests += 1
                metrics.last_failure = datetime.utcnow()
                metrics.consecutive_failures += 1

                if timeout:
                    metrics.timeout_requests += 1

                # Check circuit breaker
                if metrics.consecutive_failures >= self.CIRCUIT_BREAKER_THRESHOLD:
                    if not metrics.circuit_open:
                        logger.warning(f"Opening circuit for provider {provider}")
                        metrics.circuit_open = True
                        metrics.circuit_open_until = datetime.utcnow() + timedelta(
                            seconds=self.CIRCUIT_BREAKER_TIMEOUT
                        )
                        metrics.downtime_start = datetime.utcnow()

            # Update status and weights
            self._update_status(metrics)
            self._update_dynamic_weight(metrics)

            # Periodically save state
            if metrics.total_requests % 10 == 0:
                self._save_state()

    def _update_latency_percentiles(self, metrics: ProviderMetrics):
        """Update latency percentile metrics"""
        if not metrics.latency_history:
            return

        latencies = sorted(metrics.latency_history)
        n = len(latencies)

        metrics.avg_latency_ms = statistics.mean(latencies)
        metrics.p50_latency_ms = latencies[n // 2]
        metrics.p95_latency_ms = latencies[int(n * 0.95)] if n >= 20 else latencies[-1]
        metrics.p99_latency_ms = latencies[int(n * 0.99)] if n >= 100 else latencies[-1]

    def _update_status(self, metrics: ProviderMetrics):
        """Update provider health status"""
        if metrics.circuit_open:
            metrics.status = HealthStatus.OFFLINE
            return

        # Calculate failure rate
        if metrics.total_requests > 0:
            failure_rate = metrics.failed_requests / metrics.total_requests
        else:
            failure_rate = 0

        # Determine status
        if failure_rate >= 0.5:
            metrics.status = HealthStatus.UNHEALTHY
        elif failure_rate >= self.FAILURE_THRESHOLD:
            metrics.status = HealthStatus.DEGRADED
        elif metrics.avg_latency_ms > self.LATENCY_CRITICAL_MS:
            metrics.status = HealthStatus.DEGRADED
        elif metrics.avg_latency_ms > self.LATENCY_WARNING_MS:
            metrics.status = HealthStatus.DEGRADED
        else:
            metrics.status = HealthStatus.HEALTHY

    def _update_dynamic_weight(self, metrics: ProviderMetrics):
        """Update dynamic weight based on performance"""
        base = metrics.base_weight
        adjustment = 1.0
        reasons = []

        # Adjust for failure rate
        if metrics.total_requests > 10:
            success_rate = metrics.successful_requests / metrics.total_requests
            if success_rate < 0.9:
                adjustment *= success_rate
                reasons.append(f"success_rate={success_rate:.2f}")

        # Adjust for latency
        if metrics.avg_latency_ms > self.LATENCY_CRITICAL_MS:
            adjustment *= 0.5
            reasons.append(f"high_latency={metrics.avg_latency_ms:.0f}ms")
        elif metrics.avg_latency_ms > self.LATENCY_WARNING_MS:
            adjustment *= 0.8
            reasons.append(f"elevated_latency={metrics.avg_latency_ms:.0f}ms")

        # Adjust for grade accuracy
        if metrics.grade_accuracy_scores:
            accuracy = metrics.agreement_rate
            if accuracy < 0.8:
                adjustment *= accuracy
                reasons.append(f"accuracy={accuracy:.2f}")

        # Adjust for confidence
        if metrics.avg_confidence > 0 and metrics.avg_confidence < 70:
            adjustment *= 0.9
            reasons.append(f"low_confidence={metrics.avg_confidence:.0f}")

        # Circuit breaker penalty
        if metrics.circuit_open:
            adjustment = 0
            reasons.append("circuit_open")

        # Apply adjustment within bounds
        new_weight = base * adjustment
        metrics.dynamic_weight = max(self.MIN_WEIGHT, min(self.MAX_WEIGHT, new_weight))
        metrics.weight_adjustment_reason = "; ".join(reasons) if reasons else "optimal"

    def is_provider_available(self, provider: str) -> bool:
        """Check if provider is available for requests"""
        if provider not in self._metrics:
            return True

        metrics = self._metrics[provider]

        # Check circuit breaker
        if metrics.circuit_open:
            if metrics.circuit_open_until and datetime.utcnow() > metrics.circuit_open_until:
                # Allow a test request
                return True
            return False

        return metrics.status != HealthStatus.OFFLINE

    def get_dynamic_weights(self) -> Dict[str, float]:
        """Get current dynamic weights for all providers"""
        weights = {}
        total = 0

        for provider, metrics in self._metrics.items():
            if self.is_provider_available(provider):
                weights[provider] = metrics.dynamic_weight
                total += metrics.dynamic_weight

        # Normalize weights to sum to 1.0
        if total > 0:
            weights = {p: w / total for p, w in weights.items()}

        return weights

    def get_provider_status(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get detailed status for a provider"""
        if provider not in self._metrics:
            return None

        metrics = self._metrics[provider]
        return {
            'provider': provider,
            'status': metrics.status.value,
            'total_requests': metrics.total_requests,
            'successful_requests': metrics.successful_requests,
            'failed_requests': metrics.failed_requests,
            'timeout_requests': metrics.timeout_requests,
            'success_rate': (
                metrics.successful_requests / metrics.total_requests
                if metrics.total_requests > 0 else 0
            ),
            'latency': {
                'avg_ms': metrics.avg_latency_ms,
                'p50_ms': metrics.p50_latency_ms,
                'p95_ms': metrics.p95_latency_ms,
                'p99_ms': metrics.p99_latency_ms
            },
            'quality': {
                'avg_confidence': metrics.avg_confidence,
                'agreement_rate': metrics.agreement_rate
            },
            'weights': {
                'base': metrics.base_weight,
                'dynamic': metrics.dynamic_weight,
                'adjustment_reason': metrics.weight_adjustment_reason
            },
            'circuit_breaker': {
                'open': metrics.circuit_open,
                'consecutive_failures': metrics.consecutive_failures,
                'open_until': metrics.circuit_open_until.isoformat() if metrics.circuit_open_until else None
            },
            'last_request': metrics.last_request.isoformat() if metrics.last_request else None,
            'last_success': metrics.last_success.isoformat() if metrics.last_success else None,
            'last_failure': metrics.last_failure.isoformat() if metrics.last_failure else None,
            'total_downtime_seconds': metrics.total_downtime_seconds
        }

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all providers"""
        return {
            provider: self.get_provider_status(provider)
            for provider in self._metrics
        }

    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary"""
        statuses = [m.status for m in self._metrics.values()]

        healthy_count = sum(1 for s in statuses if s == HealthStatus.HEALTHY)
        degraded_count = sum(1 for s in statuses if s == HealthStatus.DEGRADED)
        unhealthy_count = sum(1 for s in statuses if s == HealthStatus.UNHEALTHY)
        offline_count = sum(1 for s in statuses if s == HealthStatus.OFFLINE)

        # Calculate overall health score
        total = len(statuses)
        if total > 0:
            health_score = (
                (healthy_count * 1.0) +
                (degraded_count * 0.5) +
                (unhealthy_count * 0.2) +
                (offline_count * 0.0)
            ) / total
        else:
            health_score = 1.0

        return {
            'overall_score': health_score,
            'healthy_providers': healthy_count,
            'degraded_providers': degraded_count,
            'unhealthy_providers': unhealthy_count,
            'offline_providers': offline_count,
            'total_providers': total,
            'dynamic_weights': self.get_dynamic_weights()
        }

    async def health_check(
        self,
        provider: str,
        check_func: Callable
    ) -> HealthCheckResult:
        """
        Perform health check on a provider

        Args:
            provider: Provider name
            check_func: Async function to check provider health

        Returns:
            HealthCheckResult
        """
        start = datetime.utcnow()
        try:
            await asyncio.wait_for(check_func(), timeout=10.0)
            latency = (datetime.utcnow() - start).total_seconds() * 1000

            return HealthCheckResult(
                provider=provider,
                healthy=True,
                latency_ms=latency
            )
        except asyncio.TimeoutError:
            return HealthCheckResult(
                provider=provider,
                healthy=False,
                latency_ms=10000,
                error="Timeout"
            )
        except Exception as e:
            latency = (datetime.utcnow() - start).total_seconds() * 1000
            return HealthCheckResult(
                provider=provider,
                healthy=False,
                latency_ms=latency,
                error=str(e)
            )

    def reset_provider(self, provider: str):
        """Reset metrics for a provider"""
        if provider in self._metrics:
            base_weight = self._metrics[provider].base_weight
            self._metrics[provider] = ProviderMetrics(
                provider_name=provider,
                base_weight=base_weight,
                dynamic_weight=base_weight
            )
            logger.info(f"Reset metrics for provider {provider}")

    def reset_all(self):
        """Reset all provider metrics"""
        for provider in self._metrics:
            self.reset_provider(provider)


# =============================================================================
# DYNAMIC CONFIDENCE CALCULATOR
# =============================================================================

class DynamicConfidenceCalculator:
    """
    Calculates dynamic confidence scores for grading results
    based on provider health and consensus metrics
    """

    def __init__(self, health_tracker: ProviderHealthTracker):
        self.health_tracker = health_tracker

    def calculate_confidence(
        self,
        grades: Dict[str, float],
        provider_confidences: Dict[str, float] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate overall confidence for a grading consensus

        Args:
            grades: Dict of provider -> grade
            provider_confidences: Optional dict of provider -> confidence score

        Returns:
            Tuple of (confidence_score, confidence_details)
        """
        if not grades:
            return 0.0, {'error': 'No grades provided'}

        provider_confidences = provider_confidences or {}
        weights = self.health_tracker.get_dynamic_weights()

        # Base confidence from provider agreement
        grade_values = list(grades.values())
        if len(grade_values) > 1:
            grade_std = statistics.stdev(grade_values)
            agreement_confidence = max(0, 1 - (grade_std / 2))
        else:
            agreement_confidence = 0.7  # Lower confidence for single provider

        # Weight by provider health
        health_factor = 0.0
        total_weight = 0.0
        for provider, grade in grades.items():
            weight = weights.get(provider, 0.1)
            status = self.health_tracker.get_provider_status(provider)
            if status:
                health_multiplier = {
                    'healthy': 1.0,
                    'degraded': 0.7,
                    'unhealthy': 0.3,
                    'offline': 0.0
                }.get(status['status'], 0.5)
                health_factor += weight * health_multiplier
                total_weight += weight

        if total_weight > 0:
            health_confidence = health_factor / total_weight
        else:
            health_confidence = 0.5

        # Factor in individual provider confidences
        if provider_confidences:
            weighted_conf = sum(
                (conf / 100) * weights.get(p, 0.1)
                for p, conf in provider_confidences.items()
            )
            provider_conf_factor = weighted_conf / max(sum(weights.values()), 0.1)
        else:
            provider_conf_factor = 0.7

        # Combine factors
        overall_confidence = (
            agreement_confidence * 0.4 +
            health_confidence * 0.3 +
            provider_conf_factor * 0.3
        )

        details = {
            'agreement_confidence': agreement_confidence,
            'health_confidence': health_confidence,
            'provider_confidence_factor': provider_conf_factor,
            'num_providers': len(grades),
            'grade_std_dev': statistics.stdev(grade_values) if len(grade_values) > 1 else 0,
            'weights_used': weights
        }

        return overall_confidence * 100, details


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_health_tracker: Optional[ProviderHealthTracker] = None


def get_health_tracker() -> ProviderHealthTracker:
    """Get or create health tracker instance"""
    global _health_tracker
    if _health_tracker is None:
        _health_tracker = ProviderHealthTracker(
            persistence_path="P:/SOVEREIGN_APPS/collectibles_grading_system/data/provider_health.json"
        )
    return _health_tracker


def get_confidence_calculator() -> DynamicConfidenceCalculator:
    """Get confidence calculator instance"""
    tracker = get_health_tracker()
    return DynamicConfidenceCalculator(tracker)


# Export public interface
__all__ = [
    'HealthStatus',
    'ProviderMetrics',
    'HealthCheckResult',
    'ProviderHealthTracker',
    'DynamicConfidenceCalculator',
    'get_health_tracker',
    'get_confidence_calculator',
]
