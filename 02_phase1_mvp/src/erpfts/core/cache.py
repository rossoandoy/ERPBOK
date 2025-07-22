"""
Caching system for ERPFTS Phase1 MVP.

Implements multi-level caching for search results, embeddings, and document metadata
to improve performance and reduce database load.
"""

import json
import pickle
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

import redis
from loguru import logger

from src.erpfts.core.config import settings


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    async def clear(self, pattern: str = "*") -> int:
        """Clear cache entries matching pattern."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend for development and testing."""
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        # Check expiration
        if entry.get("expires_at") and datetime.now() > entry["expires_at"]:
            await self.delete(key)
            return None
        
        return entry["value"]
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in memory cache."""
        # Evict old entries if cache is full
        if len(self._cache) >= self._max_size:
            # Simple FIFO eviction
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        expires_at = None
        if ttl:
            expires_at = datetime.now() + timedelta(seconds=ttl)
        
        self._cache[key] = {
            "value": value,
            "created_at": datetime.now(),
            "expires_at": expires_at
        }
        
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete value from memory cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    async def clear(self, pattern: str = "*") -> int:
        """Clear cache entries matching pattern."""
        if pattern == "*":
            count = len(self._cache)
            self._cache.clear()
            return count
        
        # Simple pattern matching (only supports '*' wildcard)
        keys_to_delete = []
        for key in self._cache.keys():
            if pattern.replace("*", "") in key:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self._cache[key]
        
        return len(keys_to_delete)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in memory cache."""
        return key in self._cache


class RedisCacheBackend(CacheBackend):
    """Redis cache backend for production."""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        """Get Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        try:
            r = await self._get_redis()
            data = r.get(key)
            
            if data is None:
                return None
            
            # Try to deserialize JSON first, then pickle
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                try:
                    return pickle.loads(data.encode('latin1'))
                except (pickle.PickleError, AttributeError):
                    return data
                    
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache."""
        try:
            r = await self._get_redis()
            
            # Serialize value
            try:
                serialized = json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError):
                try:
                    serialized = pickle.dumps(value).decode('latin1')
                except (pickle.PickleError, AttributeError):
                    serialized = str(value)
            
            if ttl:
                return r.setex(key, ttl, serialized)
            else:
                return r.set(key, serialized)
                
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from Redis cache."""
        try:
            r = await self._get_redis()
            return bool(r.delete(key))
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False
    
    async def clear(self, pattern: str = "*") -> int:
        """Clear cache entries matching pattern."""
        try:
            r = await self._get_redis()
            keys = r.keys(pattern)
            if keys:
                return r.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache clear error for pattern {pattern}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        try:
            r = await self._get_redis()
            return bool(r.exists(key))
        except Exception as e:
            logger.warning(f"Cache exists check error for key {key}: {e}")
            return False


class CacheManager:
    """Centralized cache manager with multiple cache layers."""
    
    def __init__(self, backend: Optional[CacheBackend] = None):
        if backend:
            self.backend = backend
        elif settings.redis_url:
            self.backend = RedisCacheBackend(settings.redis_url)
        else:
            self.backend = MemoryCacheBackend(max_size=settings.cache_max_size)
    
    def _make_key(self, namespace: str, key: str) -> str:
        """Create namespaced cache key."""
        return f"erpfts:{namespace}:{key}"
    
    async def get_search_results(
        self, 
        query_hash: str, 
        filters_hash: str = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached search results."""
        key_parts = [query_hash]
        if filters_hash:
            key_parts.append(filters_hash)
        
        cache_key = self._make_key("search", ":".join(key_parts))
        return await self.backend.get(cache_key)
    
    async def set_search_results(
        self,
        query_hash: str,
        results: Dict[str, Any],
        filters_hash: str = None,
        ttl: int = 3600  # 1 hour
    ) -> bool:
        """Cache search results."""
        key_parts = [query_hash]
        if filters_hash:
            key_parts.append(filters_hash)
        
        cache_key = self._make_key("search", ":".join(key_parts))
        return await self.backend.set(cache_key, results, ttl)
    
    async def get_document_embeddings(self, document_id: str) -> Optional[List[List[float]]]:
        """Get cached document embeddings."""
        cache_key = self._make_key("embeddings", document_id)
        return await self.backend.get(cache_key)
    
    async def set_document_embeddings(
        self,
        document_id: str,
        embeddings: List[List[float]],
        ttl: int = 86400  # 24 hours
    ) -> bool:
        """Cache document embeddings."""
        cache_key = self._make_key("embeddings", document_id)
        return await self.backend.set(cache_key, embeddings, ttl)
    
    async def get_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get cached document metadata."""
        cache_key = self._make_key("metadata", document_id)
        return await self.backend.get(cache_key)
    
    async def set_document_metadata(
        self,
        document_id: str,
        metadata: Dict[str, Any],
        ttl: int = 7200  # 2 hours
    ) -> bool:
        """Cache document metadata."""
        cache_key = self._make_key("metadata", document_id)
        return await self.backend.set(cache_key, metadata, ttl)
    
    async def get_user_search_history(self, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached user search history."""
        cache_key = self._make_key("history", user_id)
        return await self.backend.get(cache_key)
    
    async def set_user_search_history(
        self,
        user_id: str,
        history: List[Dict[str, Any]],
        ttl: int = 1800  # 30 minutes
    ) -> bool:
        """Cache user search history."""
        cache_key = self._make_key("history", user_id)
        return await self.backend.set(cache_key, history, ttl)
    
    async def invalidate_document_caches(self, document_id: str) -> int:
        """Invalidate all caches related to a document."""
        count = 0
        
        # Clear document metadata
        if await self.backend.delete(self._make_key("metadata", document_id)):
            count += 1
        
        # Clear document embeddings
        if await self.backend.delete(self._make_key("embeddings", document_id)):
            count += 1
        
        # Clear related search results (this is approximate)
        count += await self.backend.clear(self._make_key("search", "*"))
        
        logger.info(f"Invalidated {count} cache entries for document {document_id}")
        return count
    
    async def invalidate_user_caches(self, user_id: str) -> int:
        """Invalidate all caches related to a user."""
        count = 0
        
        # Clear user search history
        if await self.backend.delete(self._make_key("history", user_id)):
            count += 1
        
        logger.info(f"Invalidated {count} cache entries for user {user_id}")
        return count
    
    async def clear_all_caches(self) -> int:
        """Clear all caches."""
        count = await self.backend.clear("erpfts:*")
        logger.info(f"Cleared {count} total cache entries")
        return count
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "backend_type": type(self.backend).__name__,
            "timestamp": datetime.now().isoformat()
        }
        
        if isinstance(self.backend, RedisCacheBackend):
            try:
                r = await self.backend._get_redis()
                info = r.info()
                stats.update({
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory", 0),
                    "used_memory_human": info.get("used_memory_human", "0B"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                })
                
                # Calculate hit rate
                hits = stats["keyspace_hits"]
                misses = stats["keyspace_misses"]
                total = hits + misses
                stats["hit_rate"] = (hits / total * 100) if total > 0 else 0
                
            except Exception as e:
                logger.warning(f"Error getting Redis stats: {e}")
                stats["error"] = str(e)
        
        elif isinstance(self.backend, MemoryCacheBackend):
            stats.update({
                "cache_size": len(self.backend._cache),
                "max_size": self.backend._max_size,
                "utilization": len(self.backend._cache) / self.backend._max_size * 100
            })
        
        return stats


# Global cache manager instance
cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance."""
    global cache_manager
    
    if cache_manager is None:
        cache_manager = CacheManager()
    
    return cache_manager


# Cache decorators for easy usage
def cache_result(namespace: str, key_func=None, ttl: int = 3600):
    """Decorator to cache function results."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            full_key = cache._make_key(namespace, cache_key)
            
            # Try to get from cache
            cached_result = await cache.backend.get(full_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.backend.set(full_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator