"""
Performance monitoring and rate limiting middleware for ERPFTS Phase1 MVP.

Provides request performance tracking, rate limiting, and system monitoring
for all API endpoints.
"""

import time
import json
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from loguru import logger

from ...core.rate_limiter import get_rate_limiter
from ...core.performance import measure_performance, get_performance_monitor
from ...core.exceptions import RateLimitExceeded


class PerformanceMiddleware:
    """Middleware for performance monitoring and rate limiting."""
    
    def __init__(self, app: Callable):
        self.app = app
        self.rate_limiter = get_rate_limiter()
        self.performance_monitor = get_performance_monitor()
    
    async def __call__(self, scope: dict, receive: Callable, send: Callable):
        """Process request with performance monitoring and rate limiting."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Extract client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Check global rate limit
        is_allowed, rate_info = await self.rate_limiter.check_global_limit()
        if not is_allowed:
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "RateLimitExceeded",
                    "message": "Global rate limit exceeded",
                    "retry_after": rate_info.get("retry_after", 60),
                    "limit": rate_info.get("limit", 0),
                    "window": rate_info.get("window", 60)
                }
            )
            await response(scope, receive, send)
            return
        
        # Check IP-based rate limit
        is_allowed, rate_info = await self.rate_limiter.check_api_limit(client_ip)
        if not is_allowed:
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "RateLimitExceeded",
                    "message": "API rate limit exceeded for IP",
                    "retry_after": rate_info.get("retry_after", 60),
                    "limit": rate_info.get("limit", 0),
                    "window": rate_info.get("window", 60)
                }
            )
            await response(scope, receive, send)
            return
        
        # Create operation name for performance tracking
        operation = f"{request.method} {request.url.path}"
        
        # Track performance
        async with measure_performance(operation, {"client_ip": client_ip}):
            start_time = time.time()
            
            async def send_wrapper(message):
                """Wrapper to capture response information."""
                if message["type"] == "http.response.start":
                    # Add performance headers
                    headers = dict(message.get("headers", []))
                    
                    # Add rate limit headers
                    remaining = rate_info.get("remaining", 0)
                    limit = rate_info.get("limit", 0)
                    reset_time = rate_info.get("reset_time", time.time() + 60)
                    
                    headers[b"x-ratelimit-limit"] = str(limit).encode()
                    headers[b"x-ratelimit-remaining"] = str(remaining).encode()
                    headers[b"x-ratelimit-reset"] = str(int(reset_time)).encode()
                    
                    # Add processing time header
                    processing_time = time.time() - start_time
                    headers[b"x-processing-time"] = f"{processing_time:.3f}".encode()
                    
                    message["headers"] = list(headers.items())
                
                await send(message)
            
            try:
                await self.app(scope, receive, send_wrapper)
            except Exception as e:
                # Log the error for monitoring
                logger.error(f"Request failed: {operation} - {str(e)}")
                raise


async def add_performance_headers(request: Request, call_next):
    """Add performance-related headers to responses."""
    start_time = time.time()
    
    # Get client IP for rate limiting info
    client_ip = request.client.host if request.client else "unknown"
    rate_limiter = get_rate_limiter()
    
    # Get current rate limit status
    _, rate_info = await rate_limiter.check_api_limit(client_ip)
    
    response = await call_next(request)
    
    # Add performance headers
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Add rate limit headers
    if rate_info:
        response.headers["X-RateLimit-Limit"] = str(rate_info.get("limit", 0))
        response.headers["X-RateLimit-Remaining"] = str(rate_info.get("remaining", 0))
        if "reset_time" in rate_info:
            response.headers["X-RateLimit-Reset"] = str(int(rate_info["reset_time"]))
    
    return response


async def handle_rate_limit_errors(request: Request, call_next):
    """Handle rate limit exceeded errors."""
    try:
        response = await call_next(request)
        return response
    except RateLimitExceeded as e:
        logger.warning(f"Rate limit exceeded for {request.client.host}: {e}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "RateLimitExceeded",
                "message": str(e),
                "retry_after": getattr(e, 'retry_after', 60)
            }
        )