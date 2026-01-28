"""
Metrics Collection Module
Prometheus-compatible metrics for monitoring and observability
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from functools import wraps

logger = logging.getLogger(__name__)

# Try to import prometheus_client
try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary, Info,
        generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed - using internal metrics")


# =============================================================================
# INTERNAL METRICS (FALLBACK)
# =============================================================================

@dataclass
class MetricValue:
    """Internal metric value holder"""
    value: float = 0.0
    count: int = 0
    sum: float = 0.0
    buckets: Dict[float, int] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.utcnow)


class InternalMetrics:
    """Internal metrics collection when Prometheus is unavailable"""

    def __init__(self):
        self._counters: Dict[str, Dict[tuple, float]] = defaultdict(lambda: defaultdict(float))
        self._gauges: Dict[str, Dict[tuple, float]] = defaultdict(lambda: defaultdict(float))
        self._histograms: Dict[str, Dict[tuple, List[float]]] = defaultdict(lambda: defaultdict(list))
        self._summaries: Dict[str, Dict[tuple, List[float]]] = defaultdict(lambda: defaultdict(list))

    def counter_inc(self, name: str, labels: Dict[str, str] = None, value: float = 1.0):
        label_key = tuple(sorted((labels or {}).items()))
        self._counters[name][label_key] += value

    def gauge_set(self, name: str, value: float, labels: Dict[str, str] = None):
        label_key = tuple(sorted((labels or {}).items()))
        self._gauges[name][label_key] = value

    def gauge_inc(self, name: str, labels: Dict[str, str] = None, value: float = 1.0):
        label_key = tuple(sorted((labels or {}).items()))
        self._gauges[name][label_key] += value

    def histogram_observe(self, name: str, value: float, labels: Dict[str, str] = None):
        label_key = tuple(sorted((labels or {}).items()))
        self._histograms[name][label_key].append(value)
        # Keep only last 1000 observations
        if len(self._histograms[name][label_key]) > 1000:
            self._histograms[name][label_key] = self._histograms[name][label_key][-1000:]

    def get_metrics(self) -> Dict[str, Any]:
        """Export all metrics as dictionary"""
        result = {
            'counters': {},
            'gauges': {},
            'histograms': {}
        }

        for name, values in self._counters.items():
            result['counters'][name] = {
                str(dict(labels)): val for labels, val in values.items()
            }

        for name, values in self._gauges.items():
            result['gauges'][name] = {
                str(dict(labels)): val for labels, val in values.items()
            }

        for name, values in self._histograms.items():
            result['histograms'][name] = {}
            for labels, observations in values.items():
                if observations:
                    result['histograms'][name][str(dict(labels))] = {
                        'count': len(observations),
                        'sum': sum(observations),
                        'avg': sum(observations) / len(observations),
                        'min': min(observations),
                        'max': max(observations)
                    }

        return result


# =============================================================================
# METRICS REGISTRY
# =============================================================================

class MetricsRegistry:
    """
    Central metrics registry for the application

    Provides both Prometheus-compatible and internal metrics collection.
    """

    def __init__(self, namespace: str = "collectibles"):
        self.namespace = namespace
        self._internal = InternalMetrics()

        if PROMETHEUS_AVAILABLE:
            self._registry = CollectorRegistry()
            self._setup_prometheus_metrics()
        else:
            self._registry = None

    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics"""
        # Request metrics
        self.http_requests_total = Counter(
            f'{self.namespace}_http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self._registry
        )

        self.http_request_duration = Histogram(
            f'{self.namespace}_http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self._registry
        )

        # Grading metrics
        self.grading_requests_total = Counter(
            f'{self.namespace}_grading_requests_total',
            'Total grading requests',
            ['provider', 'status'],
            registry=self._registry
        )

        self.grading_duration = Histogram(
            f'{self.namespace}_grading_duration_seconds',
            'Grading duration in seconds',
            ['provider'],
            buckets=[1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
            registry=self._registry
        )

        self.grading_confidence = Histogram(
            f'{self.namespace}_grading_confidence',
            'Grading confidence scores',
            ['provider'],
            buckets=[0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99],
            registry=self._registry
        )

        # Provider health metrics
        self.provider_status = Gauge(
            f'{self.namespace}_provider_status',
            'Provider health status (1=healthy, 0=unhealthy)',
            ['provider'],
            registry=self._registry
        )

        self.provider_latency = Summary(
            f'{self.namespace}_provider_latency_seconds',
            'Provider API latency',
            ['provider'],
            registry=self._registry
        )

        # Cache metrics
        self.cache_hits = Counter(
            f'{self.namespace}_cache_hits_total',
            'Cache hits',
            ['cache_type'],
            registry=self._registry
        )

        self.cache_misses = Counter(
            f'{self.namespace}_cache_misses_total',
            'Cache misses',
            ['cache_type'],
            registry=self._registry
        )

        # Database metrics
        self.db_queries_total = Counter(
            f'{self.namespace}_db_queries_total',
            'Total database queries',
            ['operation'],
            registry=self._registry
        )

        self.db_query_duration = Histogram(
            f'{self.namespace}_db_query_duration_seconds',
            'Database query duration',
            ['operation'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
            registry=self._registry
        )

        # Business metrics
        self.comics_total = Gauge(
            f'{self.namespace}_comics_total',
            'Total comics in system',
            registry=self._registry
        )

        self.comics_graded = Gauge(
            f'{self.namespace}_comics_graded_total',
            'Total graded comics',
            registry=self._registry
        )

        self.collection_value = Gauge(
            f'{self.namespace}_collection_value_usd',
            'Total collection value in USD',
            registry=self._registry
        )

        self.average_grade = Gauge(
            f'{self.namespace}_average_grade',
            'Average grade of collection',
            registry=self._registry
        )

        # System metrics
        self.active_connections = Gauge(
            f'{self.namespace}_active_connections',
            'Active WebSocket connections',
            registry=self._registry
        )

        self.background_tasks = Gauge(
            f'{self.namespace}_background_tasks',
            'Active background tasks',
            ['task_type'],
            registry=self._registry
        )

        # App info
        self.app_info = Info(
            f'{self.namespace}_app',
            'Application information',
            registry=self._registry
        )
        self.app_info.info({
            'version': '1.0.0',
            'python_version': '3.11',
            'environment': 'production'
        })

    # =========================================================================
    # METRIC RECORDING METHODS
    # =========================================================================

    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration: float
    ):
        """Record HTTP request metrics"""
        labels = {'method': method, 'endpoint': endpoint, 'status': str(status)}

        if PROMETHEUS_AVAILABLE:
            self.http_requests_total.labels(**labels).inc()
            self.http_request_duration.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
        else:
            self._internal.counter_inc('http_requests_total', labels)
            self._internal.histogram_observe(
                'http_request_duration',
                duration,
                {'method': method, 'endpoint': endpoint}
            )

    def record_grading(
        self,
        provider: str,
        success: bool,
        duration: float,
        confidence: float = None
    ):
        """Record grading operation metrics"""
        status = 'success' if success else 'failure'

        if PROMETHEUS_AVAILABLE:
            self.grading_requests_total.labels(provider=provider, status=status).inc()
            self.grading_duration.labels(provider=provider).observe(duration)
            if confidence is not None:
                self.grading_confidence.labels(provider=provider).observe(confidence)
        else:
            self._internal.counter_inc(
                'grading_requests_total',
                {'provider': provider, 'status': status}
            )
            self._internal.histogram_observe(
                'grading_duration',
                duration,
                {'provider': provider}
            )

    def record_provider_health(
        self,
        provider: str,
        healthy: bool,
        latency: float = None
    ):
        """Record provider health metrics"""
        if PROMETHEUS_AVAILABLE:
            self.provider_status.labels(provider=provider).set(1 if healthy else 0)
            if latency is not None:
                self.provider_latency.labels(provider=provider).observe(latency)
        else:
            self._internal.gauge_set(
                'provider_status',
                1.0 if healthy else 0.0,
                {'provider': provider}
            )

    def record_cache_access(self, cache_type: str, hit: bool):
        """Record cache access metrics"""
        if PROMETHEUS_AVAILABLE:
            if hit:
                self.cache_hits.labels(cache_type=cache_type).inc()
            else:
                self.cache_misses.labels(cache_type=cache_type).inc()
        else:
            metric_name = 'cache_hits' if hit else 'cache_misses'
            self._internal.counter_inc(metric_name, {'cache_type': cache_type})

    def record_db_query(self, operation: str, duration: float):
        """Record database query metrics"""
        if PROMETHEUS_AVAILABLE:
            self.db_queries_total.labels(operation=operation).inc()
            self.db_query_duration.labels(operation=operation).observe(duration)
        else:
            self._internal.counter_inc('db_queries_total', {'operation': operation})
            self._internal.histogram_observe(
                'db_query_duration',
                duration,
                {'operation': operation}
            )

    def update_business_metrics(
        self,
        total_comics: int = None,
        graded_comics: int = None,
        collection_value: float = None,
        average_grade: float = None
    ):
        """Update business metrics"""
        if PROMETHEUS_AVAILABLE:
            if total_comics is not None:
                self.comics_total.set(total_comics)
            if graded_comics is not None:
                self.comics_graded.set(graded_comics)
            if collection_value is not None:
                self.collection_value.set(collection_value)
            if average_grade is not None:
                self.average_grade.set(average_grade)
        else:
            if total_comics is not None:
                self._internal.gauge_set('comics_total', total_comics)
            if graded_comics is not None:
                self._internal.gauge_set('comics_graded', graded_comics)
            if collection_value is not None:
                self._internal.gauge_set('collection_value', collection_value)
            if average_grade is not None:
                self._internal.gauge_set('average_grade', average_grade)

    def set_active_connections(self, count: int):
        """Set active WebSocket connections"""
        if PROMETHEUS_AVAILABLE:
            self.active_connections.set(count)
        else:
            self._internal.gauge_set('active_connections', count)

    def record_background_task(self, task_type: str, delta: int = 1):
        """Record background task count change"""
        if PROMETHEUS_AVAILABLE:
            self.background_tasks.labels(task_type=task_type).inc(delta)
        else:
            self._internal.gauge_inc('background_tasks', {'task_type': task_type}, delta)

    # =========================================================================
    # EXPORT METHODS
    # =========================================================================

    def get_prometheus_metrics(self) -> tuple:
        """Get Prometheus-formatted metrics"""
        if PROMETHEUS_AVAILABLE:
            return generate_latest(self._registry), CONTENT_TYPE_LATEST
        return b'# Prometheus client not available\n', 'text/plain'

    def get_json_metrics(self) -> Dict[str, Any]:
        """Get metrics as JSON (for non-Prometheus systems)"""
        return self._internal.get_metrics()


# =============================================================================
# DECORATORS
# =============================================================================

def track_time(metric_name: str, labels: Dict[str, str] = None):
    """Decorator to track function execution time"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                metrics = get_metrics()
                metrics._internal.histogram_observe(metric_name, duration, labels)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                metrics = get_metrics()
                metrics._internal.histogram_observe(metric_name, duration, labels)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def count_calls(metric_name: str, labels: Dict[str, str] = None):
    """Decorator to count function calls"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            metrics = get_metrics()
            metrics._internal.counter_inc(metric_name, labels)
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            metrics = get_metrics()
            metrics._internal.counter_inc(metric_name, labels)
            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# =============================================================================
# MIDDLEWARE
# =============================================================================

async def metrics_middleware(request, call_next):
    """FastAPI middleware for request metrics"""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    # Normalize endpoint path
    endpoint = request.url.path
    # Replace numeric IDs with placeholder
    import re
    endpoint = re.sub(r'/\d+', '/{id}', endpoint)

    metrics = get_metrics()
    metrics.record_http_request(
        method=request.method,
        endpoint=endpoint,
        status=response.status_code,
        duration=duration
    )

    return response


# =============================================================================
# SINGLETON
# =============================================================================

_metrics_instance: Optional[MetricsRegistry] = None


def get_metrics() -> MetricsRegistry:
    """Get or create metrics registry instance"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsRegistry()
    return _metrics_instance


def initialize_metrics(namespace: str = "collectibles") -> MetricsRegistry:
    """Initialize metrics with custom namespace"""
    global _metrics_instance
    _metrics_instance = MetricsRegistry(namespace)
    return _metrics_instance


# Export
__all__ = [
    'MetricsRegistry',
    'get_metrics',
    'initialize_metrics',
    'track_time',
    'count_calls',
    'metrics_middleware',
    'PROMETHEUS_AVAILABLE',
]
