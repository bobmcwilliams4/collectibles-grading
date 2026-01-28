"""
Microservices Architecture
Service mesh implementation for distributed comic grading system
"""

import asyncio
import hashlib
import json
import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type
import uuid

logger = logging.getLogger(__name__)


# =============================================================================
# SERVICE DISCOVERY
# =============================================================================

class ServiceStatus(Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceInstance:
    """Represents a service instance"""
    service_id: str
    service_name: str
    host: str
    port: int
    version: str = "1.0.0"
    status: ServiceStatus = ServiceStatus.UNKNOWN
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    weight: float = 1.0  # For weighted load balancing


class ServiceRegistry:
    """
    Service Discovery Registry

    Manages service registration, discovery, and health tracking
    for the microservices architecture.
    """

    def __init__(self):
        self._services: Dict[str, List[ServiceInstance]] = {}
        self._health_checks: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()

    async def register(self, instance: ServiceInstance):
        """Register a service instance"""
        async with self._lock:
            if instance.service_name not in self._services:
                self._services[instance.service_name] = []

            # Check for existing registration
            existing = next(
                (s for s in self._services[instance.service_name]
                 if s.service_id == instance.service_id),
                None
            )

            if existing:
                # Update existing
                existing.host = instance.host
                existing.port = instance.port
                existing.status = instance.status
                existing.last_heartbeat = datetime.utcnow()
            else:
                self._services[instance.service_name].append(instance)

            logger.info(f"Registered service: {instance.service_name} at {instance.host}:{instance.port}")

    async def deregister(self, service_id: str):
        """Deregister a service instance"""
        async with self._lock:
            for service_name, instances in self._services.items():
                self._services[service_name] = [
                    i for i in instances if i.service_id != service_id
                ]
            logger.info(f"Deregistered service: {service_id}")

    async def discover(
        self,
        service_name: str,
        healthy_only: bool = True
    ) -> List[ServiceInstance]:
        """Discover service instances"""
        async with self._lock:
            instances = self._services.get(service_name, [])

            if healthy_only:
                instances = [
                    i for i in instances
                    if i.status in (ServiceStatus.HEALTHY, ServiceStatus.DEGRADED)
                ]

            return instances

    async def heartbeat(self, service_id: str, status: ServiceStatus = ServiceStatus.HEALTHY):
        """Update service heartbeat"""
        async with self._lock:
            for instances in self._services.values():
                for instance in instances:
                    if instance.service_id == service_id:
                        instance.last_heartbeat = datetime.utcnow()
                        instance.status = status
                        return

    async def health_check_all(self):
        """Run health checks on all services"""
        tasks = []
        for service_name, instances in self._services.items():
            for instance in instances:
                if instance.service_id in self._health_checks:
                    tasks.append(self._run_health_check(instance))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_health_check(self, instance: ServiceInstance):
        """Run health check for a single instance"""
        try:
            check_func = self._health_checks.get(instance.service_id)
            if check_func:
                healthy = await check_func()
                instance.status = ServiceStatus.HEALTHY if healthy else ServiceStatus.UNHEALTHY
                instance.last_heartbeat = datetime.utcnow()
        except Exception as e:
            logger.error(f"Health check failed for {instance.service_id}: {e}")
            instance.status = ServiceStatus.UNHEALTHY

    def register_health_check(self, service_id: str, check_func: Callable):
        """Register a health check function for a service"""
        self._health_checks[service_id] = check_func


# =============================================================================
# LOAD BALANCING
# =============================================================================

class LoadBalancerStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    WEIGHTED = "weighted"
    LEAST_CONNECTIONS = "least_connections"


class LoadBalancer:
    """
    Load Balancer for service instances

    Supports multiple load balancing strategies.
    """

    def __init__(self, strategy: LoadBalancerStrategy = LoadBalancerStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self._counters: Dict[str, int] = {}
        self._connections: Dict[str, int] = {}

    def select(self, instances: List[ServiceInstance]) -> Optional[ServiceInstance]:
        """Select an instance based on the configured strategy"""
        if not instances:
            return None

        healthy = [i for i in instances if i.status == ServiceStatus.HEALTHY]
        if not healthy:
            healthy = instances  # Fall back to all instances

        if self.strategy == LoadBalancerStrategy.ROUND_ROBIN:
            return self._round_robin(healthy)
        elif self.strategy == LoadBalancerStrategy.RANDOM:
            return self._random(healthy)
        elif self.strategy == LoadBalancerStrategy.WEIGHTED:
            return self._weighted(healthy)
        elif self.strategy == LoadBalancerStrategy.LEAST_CONNECTIONS:
            return self._least_connections(healthy)

        return healthy[0]

    def _round_robin(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Round robin selection"""
        key = instances[0].service_name if instances else "default"
        counter = self._counters.get(key, 0)
        instance = instances[counter % len(instances)]
        self._counters[key] = counter + 1
        return instance

    def _random(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Random selection"""
        return random.choice(instances)

    def _weighted(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Weighted selection based on instance weights"""
        total_weight = sum(i.weight for i in instances)
        r = random.uniform(0, total_weight)
        cumulative = 0

        for instance in instances:
            cumulative += instance.weight
            if r <= cumulative:
                return instance

        return instances[-1]

    def _least_connections(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Select instance with least connections"""
        return min(
            instances,
            key=lambda i: self._connections.get(i.service_id, 0)
        )

    def increment_connections(self, service_id: str):
        """Increment connection count for an instance"""
        self._connections[service_id] = self._connections.get(service_id, 0) + 1

    def decrement_connections(self, service_id: str):
        """Decrement connection count for an instance"""
        self._connections[service_id] = max(0, self._connections.get(service_id, 0) - 1)


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """
    Circuit Breaker Pattern Implementation

    Prevents cascading failures in distributed systems.
    """
    name: str
    failure_threshold: int = 5
    recovery_timeout: int = 30  # seconds
    half_open_requests: int = 3

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure: Optional[datetime] = None
    half_open_successes: int = 0

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.half_open_successes = 0
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker {self.name} is open"
                )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_successes += 1
            if self.half_open_successes >= self.half_open_requests:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit breaker {self.name} closed")
        else:
            self.failure_count = max(0, self.failure_count - 1)

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure = datetime.utcnow()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.name} opened (half-open failure)")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.name} opened (threshold reached)")

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit"""
        if self.last_failure is None:
            return True
        elapsed = (datetime.utcnow() - self.last_failure).total_seconds()
        return elapsed >= self.recovery_timeout


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


# =============================================================================
# SERVICE CLIENTS
# =============================================================================

class BaseServiceClient(ABC):
    """Base class for microservice clients"""

    def __init__(
        self,
        service_name: str,
        registry: ServiceRegistry,
        load_balancer: LoadBalancer = None
    ):
        self.service_name = service_name
        self.registry = registry
        self.load_balancer = load_balancer or LoadBalancer()
        self.circuit_breaker = CircuitBreaker(name=f"{service_name}_circuit")

    async def call(self, method: str, **kwargs) -> Any:
        """Call a service method with load balancing and circuit breaking"""
        instances = await self.registry.discover(self.service_name)

        if not instances:
            raise ServiceUnavailableError(f"No instances available for {self.service_name}")

        instance = self.load_balancer.select(instances)

        try:
            self.load_balancer.increment_connections(instance.service_id)
            result = await self.circuit_breaker.call(
                self._make_request,
                instance, method, **kwargs
            )
            return result
        finally:
            self.load_balancer.decrement_connections(instance.service_id)

    @abstractmethod
    async def _make_request(
        self,
        instance: ServiceInstance,
        method: str,
        **kwargs
    ) -> Any:
        """Make actual request to service instance"""
        pass


class ServiceUnavailableError(Exception):
    """Raised when no service instances are available"""
    pass


# =============================================================================
# MICROSERVICE DEFINITIONS
# =============================================================================

@dataclass
class GradingServiceConfig:
    """Configuration for grading microservice"""
    providers: List[str] = field(default_factory=lambda: ['claude', 'gemini', 'openrouter'])
    timeout_seconds: float = 30.0
    consensus_threshold: float = 0.85


@dataclass
class PricingServiceConfig:
    """Configuration for pricing microservice"""
    sources: List[str] = field(default_factory=lambda: ['gpa', 'heritage', 'ebay'])
    cache_ttl_hours: int = 1


@dataclass
class ImageServiceConfig:
    """Configuration for image processing microservice"""
    max_resolution: int = 4000
    generate_webp: bool = True
    quality: int = 85


class MicroserviceDefinitions:
    """
    Microservice Architecture Definition

    Defines the structure of the distributed comic grading system
    broken into independent microservices.
    """

    SERVICES = {
        'grading-service': {
            'description': 'AI-powered comic grading with multi-provider consensus',
            'endpoints': [
                {'path': '/grade', 'method': 'POST', 'description': 'Grade a comic'},
                {'path': '/grade/batch', 'method': 'POST', 'description': 'Batch grade comics'},
                {'path': '/providers/health', 'method': 'GET', 'description': 'Get provider health'},
            ],
            'dependencies': ['image-service', 'cache-service'],
            'config': GradingServiceConfig
        },
        'pricing-service': {
            'description': 'Price aggregation from multiple sources',
            'endpoints': [
                {'path': '/price', 'method': 'POST', 'description': 'Get pricing data'},
                {'path': '/price/history', 'method': 'GET', 'description': 'Get price history'},
            ],
            'dependencies': ['cache-service'],
            'config': PricingServiceConfig
        },
        'image-service': {
            'description': 'Image processing and optimization',
            'endpoints': [
                {'path': '/process', 'method': 'POST', 'description': 'Process image'},
                {'path': '/resize', 'method': 'POST', 'description': 'Resize image'},
                {'path': '/analyze', 'method': 'POST', 'description': 'Analyze image quality'},
            ],
            'dependencies': [],
            'config': ImageServiceConfig
        },
        'cache-service': {
            'description': 'Distributed caching with Redis',
            'endpoints': [
                {'path': '/get', 'method': 'GET', 'description': 'Get cached value'},
                {'path': '/set', 'method': 'POST', 'description': 'Set cached value'},
                {'path': '/invalidate', 'method': 'DELETE', 'description': 'Invalidate cache'},
            ],
            'dependencies': [],
            'config': None
        },
        'auth-service': {
            'description': 'Authentication and authorization',
            'endpoints': [
                {'path': '/login', 'method': 'POST', 'description': 'User login'},
                {'path': '/verify', 'method': 'POST', 'description': 'Verify token'},
                {'path': '/api-keys', 'method': 'GET', 'description': 'List API keys'},
            ],
            'dependencies': [],
            'config': None
        },
        'gateway-service': {
            'description': 'API Gateway for routing and rate limiting',
            'endpoints': [
                {'path': '/*', 'method': '*', 'description': 'Route to backend services'},
            ],
            'dependencies': ['auth-service', 'grading-service', 'pricing-service', 'image-service'],
            'config': None
        }
    }

    @classmethod
    def get_service_definition(cls, service_name: str) -> Optional[Dict]:
        """Get definition for a service"""
        return cls.SERVICES.get(service_name)

    @classmethod
    def get_all_services(cls) -> Dict:
        """Get all service definitions"""
        return cls.SERVICES

    @classmethod
    def get_dependency_order(cls) -> List[str]:
        """Get services in dependency order (for startup)"""
        visited = set()
        order = []

        def visit(service_name: str):
            if service_name in visited:
                return
            visited.add(service_name)

            service = cls.SERVICES.get(service_name, {})
            for dep in service.get('dependencies', []):
                visit(dep)

            order.append(service_name)

        for service_name in cls.SERVICES:
            visit(service_name)

        return order


# =============================================================================
# MESSAGE BROKER INTERFACE
# =============================================================================

class MessageBroker(ABC):
    """Abstract message broker for inter-service communication"""

    @abstractmethod
    async def publish(self, topic: str, message: Dict[str, Any]):
        """Publish message to topic"""
        pass

    @abstractmethod
    async def subscribe(self, topic: str, handler: Callable):
        """Subscribe to topic"""
        pass

    @abstractmethod
    async def unsubscribe(self, topic: str):
        """Unsubscribe from topic"""
        pass


class InMemoryMessageBroker(MessageBroker):
    """In-memory message broker for development/testing"""

    def __init__(self):
        self._topics: Dict[str, List[Callable]] = {}

    async def publish(self, topic: str, message: Dict[str, Any]):
        """Publish message to topic"""
        handlers = self._topics.get(topic, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Handler error for topic {topic}: {e}")

    async def subscribe(self, topic: str, handler: Callable):
        """Subscribe to topic"""
        if topic not in self._topics:
            self._topics[topic] = []
        self._topics[topic].append(handler)

    async def unsubscribe(self, topic: str):
        """Unsubscribe from topic"""
        self._topics.pop(topic, None)


# =============================================================================
# SAGA PATTERN FOR DISTRIBUTED TRANSACTIONS
# =============================================================================

@dataclass
class SagaStep:
    """A step in a saga"""
    name: str
    action: Callable
    compensation: Callable
    data: Dict[str, Any] = field(default_factory=dict)


class Saga:
    """
    Saga Pattern Implementation

    Manages distributed transactions across microservices
    with automatic compensation on failure.
    """

    def __init__(self, saga_id: str = None):
        self.saga_id = saga_id or str(uuid.uuid4())
        self.steps: List[SagaStep] = []
        self.completed_steps: List[SagaStep] = []

    def add_step(
        self,
        name: str,
        action: Callable,
        compensation: Callable
    ) -> 'Saga':
        """Add a step to the saga"""
        self.steps.append(SagaStep(name=name, action=action, compensation=compensation))
        return self

    async def execute(self) -> Dict[str, Any]:
        """Execute the saga"""
        results = {}

        try:
            for step in self.steps:
                logger.info(f"Saga {self.saga_id}: Executing step {step.name}")
                result = await step.action()
                step.data['result'] = result
                results[step.name] = result
                self.completed_steps.append(step)

            logger.info(f"Saga {self.saga_id}: Completed successfully")
            return {'success': True, 'results': results}

        except Exception as e:
            logger.error(f"Saga {self.saga_id}: Failed at step - {e}")
            await self._compensate()
            return {'success': False, 'error': str(e)}

    async def _compensate(self):
        """Execute compensation for completed steps in reverse order"""
        for step in reversed(self.completed_steps):
            try:
                logger.info(f"Saga {self.saga_id}: Compensating step {step.name}")
                await step.compensation(step.data.get('result'))
            except Exception as e:
                logger.error(f"Saga {self.saga_id}: Compensation failed for {step.name}: {e}")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_registry: Optional[ServiceRegistry] = None
_message_broker: Optional[MessageBroker] = None


def get_service_registry() -> ServiceRegistry:
    """Get or create service registry"""
    global _registry
    if _registry is None:
        _registry = ServiceRegistry()
    return _registry


def get_message_broker() -> MessageBroker:
    """Get or create message broker"""
    global _message_broker
    if _message_broker is None:
        _message_broker = InMemoryMessageBroker()
    return _message_broker


# Export
__all__ = [
    'ServiceStatus',
    'ServiceInstance',
    'ServiceRegistry',
    'LoadBalancerStrategy',
    'LoadBalancer',
    'CircuitState',
    'CircuitBreaker',
    'CircuitBreakerOpenError',
    'BaseServiceClient',
    'ServiceUnavailableError',
    'MicroserviceDefinitions',
    'MessageBroker',
    'InMemoryMessageBroker',
    'Saga',
    'SagaStep',
    'get_service_registry',
    'get_message_broker',
]
