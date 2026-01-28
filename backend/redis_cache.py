"""
Redis Caching Layer
High-performance distributed caching for AI grading results and pricing data
"""

import asyncio
import hashlib
import json
import logging
import pickle
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union
from functools import wraps
import os

logger = logging.getLogger(__name__)

# Try to import redis, but provide fallback
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis package not installed - using in-memory cache fallback")


# =============================================================================
# CONFIGURATION
# =============================================================================

REDIS_CONFIG = {
    'host': os.environ.get('REDIS_HOST', 'localhost'),
    'port': int(os.environ.get('REDIS_PORT', 6379)),
    'db': int(os.environ.get('REDIS_DB', 0)),
    'password': os.environ.get('REDIS_PASSWORD', None),
    'decode_responses': False,  # We'll handle encoding ourselves
    'socket_timeout': 5,
    'socket_connect_timeout': 5,
}

# Cache TTL configurations (in seconds)
CACHE_TTL = {
    'grade_result': 86400 * 7,      # 7 days - AI grading results
    'price_data': 3600,              # 1 hour - pricing data changes frequently
    'price_history': 86400,          # 1 day - historical pricing
    'provider_health': 300,          # 5 minutes - provider status
    'comic_metadata': 86400 * 30,    # 30 days - comic details rarely change
    'search_results': 300,           # 5 minutes - search results
    'statistics': 60,                # 1 minute - system stats
    'user_session': 3600,            # 1 hour - user session data
    'rate_limit': 60,                # 1 minute - rate limit windows
    'default': 3600,                 # 1 hour default
}

# Cache key prefixes for organization
KEY_PREFIX = {
    'grade': 'cgk:grade:',
    'price': 'cgk:price:',
    'price_history': 'cgk:pricehist:',
    'provider': 'cgk:provider:',
    'comic': 'cgk:comic:',
    'search': 'cgk:search:',
    'stats': 'cgk:stats:',
    'session': 'cgk:session:',
    'rate': 'cgk:rate:',
}


# =============================================================================
# IN-MEMORY FALLBACK CACHE
# =============================================================================

class InMemoryCache:
    """Fallback in-memory cache when Redis is unavailable"""

    def __init__(self, max_size: int = 10000):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self._max_size = max_size
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[bytes]:
        async with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if expiry is None or datetime.utcnow() < expiry:
                    return value
                else:
                    del self._cache[key]
            return None

    async def set(self, key: str, value: bytes, ex: int = None) -> bool:
        async with self._lock:
            # Evict oldest entries if at capacity
            if len(self._cache) >= self._max_size:
                # Remove 10% of oldest entries
                entries = sorted(self._cache.items(), key=lambda x: x[1][1] or datetime.max)
                for k, _ in entries[:int(self._max_size * 0.1)]:
                    del self._cache[k]

            expiry = datetime.utcnow() + timedelta(seconds=ex) if ex else None
            self._cache[key] = (value, expiry)
            return True

    async def delete(self, key: str) -> int:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return 1
            return 0

    async def exists(self, key: str) -> int:
        async with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if expiry is None or datetime.utcnow() < expiry:
                    return 1
                del self._cache[key]
            return 0

    async def keys(self, pattern: str) -> List[str]:
        async with self._lock:
            import fnmatch
            # Convert Redis pattern to fnmatch pattern
            pattern = pattern.replace('*', '**')
            return [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]

    async def mget(self, keys: List[str]) -> List[Optional[bytes]]:
        return [await self.get(k) for k in keys]

    async def mset(self, mapping: Dict[str, bytes]) -> bool:
        for k, v in mapping.items():
            await self.set(k, v)
        return True

    async def incr(self, key: str) -> int:
        async with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                try:
                    new_val = int(value) + 1
                    self._cache[key] = (str(new_val).encode(), expiry)
                    return new_val
                except (ValueError, TypeError):
                    pass
            self._cache[key] = (b'1', None)
            return 1

    async def expire(self, key: str, seconds: int) -> bool:
        async with self._lock:
            if key in self._cache:
                value, _ = self._cache[key]
                expiry = datetime.utcnow() + timedelta(seconds=seconds)
                self._cache[key] = (value, expiry)
                return True
            return False

    async def ttl(self, key: str) -> int:
        async with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if expiry is None:
                    return -1
                remaining = (expiry - datetime.utcnow()).total_seconds()
                return max(0, int(remaining))
            return -2

    async def flushdb(self) -> bool:
        async with self._lock:
            self._cache.clear()
            return True

    async def info(self) -> Dict[str, Any]:
        async with self._lock:
            return {
                'type': 'in-memory',
                'keys': len(self._cache),
                'max_size': self._max_size
            }

    async def ping(self) -> bool:
        return True

    async def close(self):
        pass


# =============================================================================
# REDIS CACHE MANAGER
# =============================================================================

class RedisCacheManager:
    """Redis-based cache manager with automatic fallback"""

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    async def initialize(self):
        """Initialize Redis connection or fallback"""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            self._redis = None
            self._fallback = InMemoryCache()
            self._stats = {
                'hits': 0,
                'misses': 0,
                'errors': 0,
                'sets': 0
            }

            if REDIS_AVAILABLE:
                try:
                    self._redis = await aioredis.from_url(
                        f"redis://{REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}/{REDIS_CONFIG['db']}",
                        password=REDIS_CONFIG['password'],
                        socket_timeout=REDIS_CONFIG['socket_timeout'],
                        socket_connect_timeout=REDIS_CONFIG['socket_connect_timeout'],
                    )
                    # Test connection
                    await self._redis.ping()
                    logger.info(f"Connected to Redis at {REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}")
                except Exception as e:
                    logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
                    self._redis = None

            self._initialized = True

    @property
    def client(self):
        """Get the active cache client (Redis or fallback)"""
        return self._redis if self._redis else self._fallback

    @property
    def is_redis(self) -> bool:
        """Check if using Redis or fallback"""
        return self._redis is not None

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            data = await self.client.get(key)
            if data:
                self._stats['hits'] += 1
                return pickle.loads(data)
            self._stats['misses'] += 1
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self._stats['errors'] += 1
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = None,
        cache_type: str = 'default'
    ) -> bool:
        """Set value in cache"""
        try:
            ttl = ttl or CACHE_TTL.get(cache_type, CACHE_TTL['default'])
            data = pickle.dumps(value)
            await self.client.set(key, data, ex=ttl)
            self._stats['sets'] += 1
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            self._stats['errors'] += 1
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values"""
        try:
            values = await self.client.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value:
                    result[key] = pickle.loads(value)
                    self._stats['hits'] += 1
                else:
                    self._stats['misses'] += 1
            return result
        except Exception as e:
            logger.error(f"Cache mget error: {e}")
            self._stats['errors'] += 1
            return {}

    async def set_many(
        self,
        mapping: Dict[str, Any],
        ttl: int = None,
        cache_type: str = 'default'
    ) -> bool:
        """Set multiple values"""
        try:
            ttl = ttl or CACHE_TTL.get(cache_type, CACHE_TTL['default'])
            serialized = {k: pickle.dumps(v) for k, v in mapping.items()}
            await self.client.mset(serialized)
            # Set TTL for each key
            for key in serialized.keys():
                await self.client.expire(key, ttl)
            self._stats['sets'] += len(mapping)
            return True
        except Exception as e:
            logger.error(f"Cache mset error: {e}")
            self._stats['errors'] += 1
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            if self._redis:
                keys = []
                async for key in self._redis.scan_iter(match=pattern):
                    keys.append(key)
                if keys:
                    await self._redis.delete(*keys)
                return len(keys)
            else:
                keys = await self._fallback.keys(pattern)
                for key in keys:
                    await self._fallback.delete(key)
                return len(keys)
        except Exception as e:
            logger.error(f"Cache invalidate error: {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            info = await self.client.info() if self._redis else {'type': 'in-memory'}
            return {
                'backend': 'redis' if self._redis else 'in-memory',
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'errors': self._stats['errors'],
                'sets': self._stats['sets'],
                'hit_rate': self._stats['hits'] / max(1, self._stats['hits'] + self._stats['misses']),
                'redis_info': info if self._redis else None
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return self._stats

    async def health_check(self) -> Dict[str, Any]:
        """Check cache health"""
        try:
            start = datetime.utcnow()
            await self.client.ping()
            latency = (datetime.utcnow() - start).total_seconds() * 1000

            return {
                'healthy': True,
                'backend': 'redis' if self._redis else 'in-memory',
                'latency_ms': latency
            }
        except Exception as e:
            return {
                'healthy': False,
                'backend': 'redis' if self._redis else 'in-memory',
                'error': str(e)
            }

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()


# =============================================================================
# CACHE KEY GENERATORS
# =============================================================================

def generate_grade_key(comic_id: int, image_hash: str = None) -> str:
    """Generate cache key for grade result"""
    if image_hash:
        return f"{KEY_PREFIX['grade']}{comic_id}:{image_hash}"
    return f"{KEY_PREFIX['grade']}{comic_id}"


def generate_price_key(title: str, issue: str, grade: float) -> str:
    """Generate cache key for price data"""
    key_data = f"{title}:{issue}:{grade}"
    key_hash = hashlib.md5(key_data.encode()).hexdigest()[:16]
    return f"{KEY_PREFIX['price']}{key_hash}"


def generate_search_key(query: Dict[str, Any]) -> str:
    """Generate cache key for search results"""
    query_str = json.dumps(query, sort_keys=True)
    key_hash = hashlib.md5(query_str.encode()).hexdigest()[:16]
    return f"{KEY_PREFIX['search']}{key_hash}"


def generate_provider_key(provider: str) -> str:
    """Generate cache key for provider health"""
    return f"{KEY_PREFIX['provider']}{provider}"


def generate_comic_key(comic_id: int) -> str:
    """Generate cache key for comic metadata"""
    return f"{KEY_PREFIX['comic']}{comic_id}"


def generate_image_hash(image_path: str) -> str:
    """Generate hash from image file for cache invalidation"""
    try:
        with open(image_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()[:16]
    except Exception:
        return ""


# =============================================================================
# CACHE DECORATORS
# =============================================================================

def cached(
    key_func: Callable = None,
    cache_type: str = 'default',
    ttl: int = None,
    invalidate_on: List[str] = None
):
    """
    Decorator for caching function results

    Args:
        key_func: Function to generate cache key from args
        cache_type: Type of cache TTL to use
        ttl: Override TTL in seconds
        invalidate_on: List of events that invalidate this cache
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = await get_cache()

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key from function name and args
                arg_str = f"{args}:{kwargs}"
                arg_hash = hashlib.md5(arg_str.encode()).hexdigest()[:16]
                cache_key = f"cgk:func:{func.__name__}:{arg_hash}"

            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            if result is not None:
                await cache.set(cache_key, result, ttl=ttl, cache_type=cache_type)
                logger.debug(f"Cache set: {cache_key}")

            return result

        return wrapper
    return decorator


def invalidate_cache(patterns: List[str]):
    """
    Decorator to invalidate cache patterns after function execution

    Args:
        patterns: List of cache key patterns to invalidate
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Invalidate cache patterns
            cache = await get_cache()
            for pattern in patterns:
                # Allow pattern to use args/kwargs for dynamic invalidation
                if callable(pattern):
                    actual_pattern = pattern(*args, **kwargs)
                else:
                    actual_pattern = pattern
                await cache.invalidate_pattern(actual_pattern)

            return result

        return wrapper
    return decorator


# =============================================================================
# SPECIALIZED CACHE OPERATIONS
# =============================================================================

class GradeCache:
    """Specialized cache for AI grading results"""

    def __init__(self, cache: RedisCacheManager):
        self._cache = cache

    async def get_grade(
        self,
        comic_id: int,
        image_hash: str = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached grade result"""
        key = generate_grade_key(comic_id, image_hash)
        return await self._cache.get(key)

    async def set_grade(
        self,
        comic_id: int,
        grade_result: Dict[str, Any],
        image_hash: str = None
    ):
        """Cache grade result"""
        key = generate_grade_key(comic_id, image_hash)
        await self._cache.set(key, grade_result, cache_type='grade_result')

    async def invalidate_grade(self, comic_id: int):
        """Invalidate all cached grades for a comic"""
        pattern = f"{KEY_PREFIX['grade']}{comic_id}:*"
        await self._cache.invalidate_pattern(pattern)


class PriceCache:
    """Specialized cache for pricing data"""

    def __init__(self, cache: RedisCacheManager):
        self._cache = cache

    async def get_price(
        self,
        title: str,
        issue: str,
        grade: float
    ) -> Optional[Dict[str, Any]]:
        """Get cached price data"""
        key = generate_price_key(title, issue, grade)
        return await self._cache.get(key)

    async def set_price(
        self,
        title: str,
        issue: str,
        grade: float,
        price_data: Dict[str, Any]
    ):
        """Cache price data"""
        key = generate_price_key(title, issue, grade)
        await self._cache.set(key, price_data, cache_type='price_data')

    async def get_price_history(
        self,
        title: str,
        issue: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached price history"""
        key = f"{KEY_PREFIX['price_history']}{title}:{issue}"
        return await self._cache.get(key)

    async def set_price_history(
        self,
        title: str,
        issue: str,
        history: List[Dict[str, Any]]
    ):
        """Cache price history"""
        key = f"{KEY_PREFIX['price_history']}{title}:{issue}"
        await self._cache.set(key, history, cache_type='price_history')


class ProviderCache:
    """Specialized cache for AI provider health data"""

    def __init__(self, cache: RedisCacheManager):
        self._cache = cache

    async def get_health(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get cached provider health"""
        key = generate_provider_key(provider)
        return await self._cache.get(key)

    async def set_health(self, provider: str, health_data: Dict[str, Any]):
        """Cache provider health"""
        key = generate_provider_key(provider)
        await self._cache.set(key, health_data, cache_type='provider_health')

    async def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        """Get all provider health data"""
        pattern = f"{KEY_PREFIX['provider']}*"
        # This is a simplified version - in production would use scan
        return {}


# =============================================================================
# INITIALIZATION
# =============================================================================

_cache_instance: Optional[RedisCacheManager] = None


async def get_cache() -> RedisCacheManager:
    """Get or create cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCacheManager()
        await _cache_instance.initialize()
    return _cache_instance


async def initialize_cache() -> RedisCacheManager:
    """Initialize and return cache"""
    return await get_cache()


async def get_grade_cache() -> GradeCache:
    """Get grade cache instance"""
    cache = await get_cache()
    return GradeCache(cache)


async def get_price_cache() -> PriceCache:
    """Get price cache instance"""
    cache = await get_cache()
    return PriceCache(cache)


async def get_provider_cache() -> ProviderCache:
    """Get provider cache instance"""
    cache = await get_cache()
    return ProviderCache(cache)


# Export public interface
__all__ = [
    'RedisCacheManager',
    'get_cache',
    'initialize_cache',
    'cached',
    'invalidate_cache',
    'GradeCache',
    'PriceCache',
    'ProviderCache',
    'get_grade_cache',
    'get_price_cache',
    'get_provider_cache',
    'generate_grade_key',
    'generate_price_key',
    'generate_search_key',
    'generate_image_hash',
    'CACHE_TTL',
    'KEY_PREFIX',
]
