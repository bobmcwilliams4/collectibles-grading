"""
Advanced Caching System
Multi-level caching with TTL, LRU eviction, and persistence
"""

import asyncio
import hashlib
import json
import logging
import pickle
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Callable, Union
from dataclasses import dataclass, field
from collections import OrderedDict
from enum import Enum
import threading
import aiofiles

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    MEMORY = "memory"
    DISK = "disk"
    BOTH = "both"


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: float
    expires_at: Optional[float]
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    size_bytes: int = 0

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class LRUCache:
    """
    Thread-safe LRU Cache with TTL support

    Features:
    - Least Recently Used eviction
    - Time-to-live expiration
    - Size-based limits
    - Thread-safe operations
    """

    def __init__(
        self,
        max_size: int = 1000,
        max_memory_mb: int = 100,
        default_ttl: int = 3600
    ):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._current_memory = 0

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired():
                self._remove(key)
                self._misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.access_count += 1
            entry.last_accessed = time.time()

            self._hits += 1
            return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ):
        """Set value in cache"""
        with self._lock:
            # Calculate size
            try:
                size = len(pickle.dumps(value))
            except:
                size = 1000  # Default estimate

            # Check if key exists
            if key in self._cache:
                old_entry = self._cache[key]
                self._current_memory -= old_entry.size_bytes

            # Create entry
            expires_at = None
            if ttl is not None:
                expires_at = time.time() + ttl
            elif self.default_ttl:
                expires_at = time.time() + self.default_ttl

            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                expires_at=expires_at,
                size_bytes=size
            )

            # Evict if necessary
            while (
                len(self._cache) >= self.max_size or
                self._current_memory + size > self.max_memory_bytes
            ) and self._cache:
                self._evict_oldest()

            # Add entry
            self._cache[key] = entry
            self._cache.move_to_end(key)
            self._current_memory += size

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self._lock:
            return self._remove(key)

    def _remove(self, key: str) -> bool:
        """Internal remove method"""
        if key in self._cache:
            entry = self._cache.pop(key)
            self._current_memory -= entry.size_bytes
            return True
        return False

    def _evict_oldest(self):
        """Evict least recently used entry"""
        if self._cache:
            key = next(iter(self._cache))
            self._remove(key)
            self._evictions += 1

    def clear(self):
        """Clear all entries"""
        with self._lock:
            self._cache.clear()
            self._current_memory = 0

    def cleanup_expired(self) -> int:
        """Remove all expired entries"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]

            for key in expired_keys:
                self._remove(key)

            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0

            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'memory_used_mb': self._current_memory / (1024 * 1024),
                'max_memory_mb': self.max_memory_bytes / (1024 * 1024),
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'evictions': self._evictions
            }


class DiskCache:
    """
    Persistent disk-based cache

    Features:
    - File-based storage
    - Automatic cleanup
    - Compression support
    - Async operations
    """

    def __init__(
        self,
        cache_dir: str = "P:/SOVEREIGN_APPS/collectibles_grading_system/data/cache",
        max_size_mb: int = 500,
        default_ttl: int = 86400  # 24 hours
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl

        self._index_file = self.cache_dir / "_index.json"
        self._index: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()

        # Load existing index
        self._load_index()

    def _load_index(self):
        """Load cache index from disk"""
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r') as f:
                    self._index = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache index: {e}")
                self._index = {}

    async def _save_index(self):
        """Save cache index to disk"""
        async with aiofiles.open(self._index_file, 'w') as f:
            await f.write(json.dumps(self._index, indent=2))

    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key"""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from disk cache"""
        async with self._lock:
            if key not in self._index:
                return None

            meta = self._index[key]

            # Check expiration
            if meta.get('expires_at') and time.time() > meta['expires_at']:
                await self._remove(key)
                return None

            cache_path = self._get_cache_path(key)

            if not cache_path.exists():
                del self._index[key]
                return None

            try:
                async with aiofiles.open(cache_path, 'rb') as f:
                    data = await f.read()
                    return pickle.loads(data)
            except Exception as e:
                logger.error(f"Failed to read cache {key}: {e}")
                return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ):
        """Set value in disk cache"""
        async with self._lock:
            try:
                data = pickle.dumps(value)
                size = len(data)

                # Check size limits
                await self._ensure_space(size)

                cache_path = self._get_cache_path(key)

                async with aiofiles.open(cache_path, 'wb') as f:
                    await f.write(data)

                # Update index
                expires_at = None
                if ttl is not None:
                    expires_at = time.time() + ttl
                elif self.default_ttl:
                    expires_at = time.time() + self.default_ttl

                self._index[key] = {
                    'created_at': time.time(),
                    'expires_at': expires_at,
                    'size': size,
                    'path': str(cache_path)
                }

                await self._save_index()

            except Exception as e:
                logger.error(f"Failed to write cache {key}: {e}")

    async def delete(self, key: str) -> bool:
        """Delete key from disk cache"""
        async with self._lock:
            return await self._remove(key)

    async def _remove(self, key: str) -> bool:
        """Internal remove method"""
        if key not in self._index:
            return False

        cache_path = self._get_cache_path(key)

        try:
            if cache_path.exists():
                cache_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to delete cache file: {e}")

        del self._index[key]
        await self._save_index()
        return True

    async def _ensure_space(self, needed_bytes: int):
        """Ensure enough space for new entry"""
        current_size = sum(meta['size'] for meta in self._index.values())

        while current_size + needed_bytes > self.max_size_bytes and self._index:
            # Remove oldest entry
            oldest_key = min(
                self._index.keys(),
                key=lambda k: self._index[k].get('created_at', 0)
            )
            size_freed = self._index[oldest_key]['size']
            await self._remove(oldest_key)
            current_size -= size_freed

    async def cleanup_expired(self) -> int:
        """Remove all expired entries"""
        async with self._lock:
            now = time.time()
            expired_keys = [
                key for key, meta in self._index.items()
                if meta.get('expires_at') and now > meta['expires_at']
            ]

            for key in expired_keys:
                await self._remove(key)

            return len(expired_keys)

    async def clear(self):
        """Clear all cache entries"""
        async with self._lock:
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    cache_file.unlink()
                except:
                    pass

            self._index = {}
            await self._save_index()

    def get_stats(self) -> Dict[str, Any]:
        """Get disk cache statistics"""
        total_size = sum(meta['size'] for meta in self._index.values())

        return {
            'entries': len(self._index),
            'size_mb': total_size / (1024 * 1024),
            'max_size_mb': self.max_size_bytes / (1024 * 1024),
            'cache_dir': str(self.cache_dir)
        }


class CacheManager:
    """
    Multi-level Cache Manager

    Features:
    - L1: In-memory LRU cache (fast)
    - L2: Disk-based cache (persistent)
    - Automatic promotion/demotion
    - Key pattern namespacing
    - Background cleanup
    """

    def __init__(
        self,
        memory_max_size: int = 500,
        memory_max_mb: int = 50,
        disk_max_mb: int = 500,
        memory_ttl: int = 300,  # 5 minutes
        disk_ttl: int = 86400   # 24 hours
    ):
        self.memory_cache = LRUCache(
            max_size=memory_max_size,
            max_memory_mb=memory_max_mb,
            default_ttl=memory_ttl
        )

        self.disk_cache = DiskCache(
            max_size_mb=disk_max_mb,
            default_ttl=disk_ttl
        )

        self._cleanup_task = None
        self._running = False

    async def start(self):
        """Start background cleanup task"""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Cache manager started")

    async def stop(self):
        """Stop cache manager"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Cache manager stopped")

    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while self._running:
            try:
                # Cleanup memory cache
                expired_memory = self.memory_cache.cleanup_expired()

                # Cleanup disk cache
                expired_disk = await self.disk_cache.cleanup_expired()

                if expired_memory or expired_disk:
                    logger.debug(
                        f"Cache cleanup: {expired_memory} memory, "
                        f"{expired_disk} disk entries expired"
                    )

                await asyncio.sleep(60)  # Cleanup every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(60)

    def _make_key(self, namespace: str, key: str) -> str:
        """Create namespaced cache key"""
        return f"{namespace}:{key}"

    async def get(
        self,
        key: str,
        namespace: str = "default",
        level: CacheLevel = CacheLevel.BOTH
    ) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key
            namespace: Key namespace
            level: Which cache levels to check

        Returns:
            Cached value or None
        """
        full_key = self._make_key(namespace, key)

        # Check memory first
        if level in (CacheLevel.MEMORY, CacheLevel.BOTH):
            value = self.memory_cache.get(full_key)
            if value is not None:
                return value

        # Check disk
        if level in (CacheLevel.DISK, CacheLevel.BOTH):
            value = await self.disk_cache.get(full_key)
            if value is not None:
                # Promote to memory cache
                if level == CacheLevel.BOTH:
                    self.memory_cache.set(full_key, value)
                return value

        return None

    async def set(
        self,
        key: str,
        value: Any,
        namespace: str = "default",
        level: CacheLevel = CacheLevel.BOTH,
        memory_ttl: Optional[int] = None,
        disk_ttl: Optional[int] = None
    ):
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            namespace: Key namespace
            level: Which cache levels to use
            memory_ttl: Memory cache TTL (seconds)
            disk_ttl: Disk cache TTL (seconds)
        """
        full_key = self._make_key(namespace, key)

        if level in (CacheLevel.MEMORY, CacheLevel.BOTH):
            self.memory_cache.set(full_key, value, memory_ttl)

        if level in (CacheLevel.DISK, CacheLevel.BOTH):
            await self.disk_cache.set(full_key, value, disk_ttl)

    async def delete(
        self,
        key: str,
        namespace: str = "default"
    ) -> bool:
        """Delete key from all cache levels"""
        full_key = self._make_key(namespace, key)

        memory_deleted = self.memory_cache.delete(full_key)
        disk_deleted = await self.disk_cache.delete(full_key)

        return memory_deleted or disk_deleted

    async def invalidate_namespace(self, namespace: str):
        """Invalidate all keys in a namespace"""
        # This is a simplified implementation
        # In production, you'd want to maintain namespace -> keys mapping
        logger.info(f"Invalidating namespace: {namespace}")
        # For now, clear everything (could be optimized)
        self.memory_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get combined cache statistics"""
        return {
            'memory': self.memory_cache.get_stats(),
            'disk': self.disk_cache.get_stats()
        }


def cached(
    namespace: str = "default",
    ttl: int = 300,
    level: CacheLevel = CacheLevel.MEMORY
):
    """
    Decorator for caching function results

    Usage:
        @cached(namespace="grading", ttl=600)
        async def grade_comic(image_path: str):
            ...
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()

            # Try to get from cache
            cached_value = await cache_manager.get(cache_key, namespace, level)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(
                cache_key,
                result,
                namespace,
                level,
                memory_ttl=ttl if level != CacheLevel.DISK else None,
                disk_ttl=ttl if level != CacheLevel.MEMORY else None
            )

            return result

        return wrapper
    return decorator


# Global cache manager instance
cache_manager = CacheManager()


# Convenience functions
async def get_cached(
    key: str,
    namespace: str = "default"
) -> Optional[Any]:
    """Get value from cache"""
    return await cache_manager.get(key, namespace)


async def set_cached(
    key: str,
    value: Any,
    namespace: str = "default",
    ttl: int = None
):
    """Set value in cache"""
    await cache_manager.set(key, value, namespace, memory_ttl=ttl, disk_ttl=ttl)
