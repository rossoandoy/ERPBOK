"""
Rate limiting system for ERPFTS Phase1 MVP.

Implements sliding window rate limiting to protect against abuse and ensure
fair resource allocation across users and API endpoints.
"""

import asyncio
import time
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from loguru import logger

from src.erpfts.core.config import settings


class RateLimitType(str, Enum):
    """Types of rate limits."""
    PER_USER = "per_user"
    PER_IP = "per_ip"
    GLOBAL = "global"


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests: int  # Number of requests allowed
    window: int    # Time window in seconds
    burst: int = None  # Burst limit (optional)


class RateLimiterBackend:
    """Rate limiter backend using in-memory sliding window."""
    
    def __init__(self):
        self._windows: Dict[str, deque] = defaultdict(deque)
        self._lock = asyncio.Lock()
    
    async def is_allowed(
        self, 
        key: str, 
        config: RateLimitConfig,
        current_time: Optional[float] = None
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is allowed under rate limit.
        
        Returns:
            Tuple of (is_allowed, info_dict)
        """
        if current_time is None:
            current_time = time.time()
        
        async with self._lock:
            window = self._windows[key]
            window_start = current_time - config.window
            
            # Remove expired entries
            while window and window[0] < window_start:
                window.popleft()
            
            current_count = len(window)
            
            # Check if request is allowed
            if current_count >= config.requests:
                # Calculate retry after
                if window:
                    oldest_request = window[0]
                    retry_after = int(oldest_request + config.window - current_time) + 1
                else:
                    retry_after = config.window
                
                return False, {
                    "current_count": current_count,
                    "limit": config.requests,
                    "window": config.window,
                    "retry_after": retry_after,
                    "reset_time": current_time + retry_after
                }
            
            # Add current request to window
            window.append(current_time)
            
            return True, {
                "current_count": current_count + 1,
                "limit": config.requests,
                "window": config.window,
                "remaining": config.requests - current_count - 1,
                "reset_time": current_time + config.window
            }
    
    async def get_current_usage(self, key: str, window: int) -> int:
        """Get current usage count for a key."""
        current_time = time.time()
        window_start = current_time - window
        
        async with self._lock:
            request_window = self._windows[key]
            
            # Remove expired entries
            while request_window and request_window[0] < window_start:
                request_window.popleft()
            
            return len(request_window)
    
    async def reset_key(self, key: str) -> bool:
        """Reset rate limit for a key."""
        async with self._lock:
            if key in self._windows:
                self._windows[key].clear()
                return True
            return False
    
    async def cleanup_expired(self, max_age: int = 3600):
        """Clean up expired entries."""
        current_time = time.time()
        cutoff_time = current_time - max_age
        
        async with self._lock:
            keys_to_remove = []
            
            for key, window in self._windows.items():
                # Remove expired entries from this window
                while window and window[0] < cutoff_time:
                    window.popleft()
                
                # If window is empty, mark key for removal
                if not window:
                    keys_to_remove.append(key)
            
            # Remove empty windows
            for key in keys_to_remove:
                del self._windows[key]
            
            logger.debug(f"Cleaned up {len(keys_to_remove)} expired rate limit windows")


class RateLimiter:
    """Main rate limiter class."""
    
    def __init__(self):
        self.backend = RateLimiterBackend()
        self._configs: Dict[str, RateLimitConfig] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Default configurations
        self._setup_default_configs()
        
        # Start cleanup task
        if settings.rate_limit_cleanup_interval > 0:
            self._start_cleanup_task()
    
    def _setup_default_configs(self):
        """Setup default rate limit configurations."""
        self._configs.update({
            "search_per_user": RateLimitConfig(
                requests=settings.rate_limit_search_per_user_requests,
                window=settings.rate_limit_search_per_user_window
            ),
            "upload_per_user": RateLimitConfig(
                requests=settings.rate_limit_upload_per_user_requests,
                window=settings.rate_limit_upload_per_user_window
            ),
            "api_per_ip": RateLimitConfig(
                requests=settings.rate_limit_api_per_ip_requests,
                window=settings.rate_limit_api_per_ip_window
            ),
            "global_api": RateLimitConfig(
                requests=settings.rate_limit_global_requests,
                window=settings.rate_limit_global_window
            )
        })
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        async def cleanup_worker():
            while True:
                try:
                    await asyncio.sleep(settings.rate_limit_cleanup_interval)
                    await self.backend.cleanup_expired()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Rate limiter cleanup error: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_worker())
    
    async def check_limit(
        self,
        limit_type: str,
        identifier: str,
        config_override: Optional[RateLimitConfig] = None
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is within rate limit.
        
        Args:
            limit_type: Type of limit (e.g., 'search_per_user', 'api_per_ip')
            identifier: Unique identifier (user_id, ip_address, etc.)
            config_override: Optional config to override default
            
        Returns:
            Tuple of (is_allowed, info_dict)
        """
        config = config_override or self._configs.get(limit_type)
        if not config:
            logger.warning(f"No rate limit config found for type: {limit_type}")
            return True, {}
        
        key = f"{limit_type}:{identifier}"
        return await self.backend.is_allowed(key, config)
    
    async def check_search_limit(self, user_id: str) -> Tuple[bool, Dict[str, any]]:
        """Check search rate limit for user."""
        return await self.check_limit("search_per_user", user_id)
    
    async def check_upload_limit(self, user_id: str) -> Tuple[bool, Dict[str, any]]:
        """Check upload rate limit for user."""
        return await self.check_limit("upload_per_user", user_id)
    
    async def check_api_limit(self, ip_address: str) -> Tuple[bool, Dict[str, any]]:
        """Check API rate limit for IP address."""
        return await self.check_limit("api_per_ip", ip_address)
    
    async def check_global_limit(self) -> Tuple[bool, Dict[str, any]]:
        """Check global API rate limit."""
        return await self.check_limit("global_api", "global")
    
    async def get_usage_stats(self, limit_type: str, identifier: str) -> Dict[str, any]:
        """Get current usage statistics for a limit."""
        config = self._configs.get(limit_type)
        if not config:
            return {}
        
        key = f"{limit_type}:{identifier}"
        current_usage = await self.backend.get_current_usage(key, config.window)
        
        return {
            "current_usage": current_usage,
            "limit": config.requests,
            "window": config.window,
            "remaining": max(0, config.requests - current_usage)
        }
    
    async def reset_user_limits(self, user_id: str) -> Dict[str, bool]:
        """Reset all rate limits for a user."""
        results = {}
        
        for limit_type in ["search_per_user", "upload_per_user"]:
            key = f"{limit_type}:{user_id}"
            results[limit_type] = await self.backend.reset_key(key)
        
        return results
    
    async def reset_ip_limits(self, ip_address: str) -> bool:
        """Reset rate limits for an IP address."""
        key = f"api_per_ip:{ip_address}"
        return await self.backend.reset_key(key)
    
    def add_custom_limit(self, name: str, config: RateLimitConfig):
        """Add custom rate limit configuration."""
        self._configs[name] = config
        logger.info(f"Added custom rate limit: {name}")
    
    def remove_custom_limit(self, name: str) -> bool:
        """Remove custom rate limit configuration."""
        if name in self._configs and not name.startswith(("search_", "upload_", "api_", "global_")):
            del self._configs[name]
            logger.info(f"Removed custom rate limit: {name}")
            return True
        return False
    
    async def get_all_stats(self) -> Dict[str, any]:
        """Get comprehensive rate limiter statistics."""
        stats = {
            "configurations": {
                name: {
                    "requests": config.requests,
                    "window": config.window,
                    "burst": config.burst
                }
                for name, config in self._configs.items()
            },
            "backend_type": type(self.backend).__name__,
            "cleanup_running": self._cleanup_task and not self._cleanup_task.done(),
            "total_active_windows": len(self.backend._windows)
        }
        
        return stats
    
    async def shutdown(self):
        """Shutdown rate limiter and cleanup resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Rate limiter shutdown complete")


# Global rate limiter instance
rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    global rate_limiter
    
    if rate_limiter is None:
        rate_limiter = RateLimiter()
    
    return rate_limiter


# Decorator for easy rate limiting
def rate_limit(limit_type: str, identifier_func=None):
    """Decorator to apply rate limiting to functions."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            limiter = get_rate_limiter()
            
            # Get identifier
            if identifier_func:
                identifier = identifier_func(*args, **kwargs)
            else:
                # Default to first argument as identifier
                identifier = str(args[0]) if args else "default"
            
            # Check rate limit
            is_allowed, info = await limiter.check_limit(limit_type, identifier)
            
            if not is_allowed:
                from src.erpfts.core.exceptions import RateLimitExceeded
                raise RateLimitExceeded(
                    f"Rate limit exceeded for {limit_type}",
                    retry_after=info.get("retry_after", 60)
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator