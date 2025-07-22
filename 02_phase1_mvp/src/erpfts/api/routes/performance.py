"""
Performance monitoring endpoints for ERPFTS Phase1 MVP.

Provides endpoints for system health, performance metrics, and resource monitoring.
"""

from fastapi import APIRouter, HTTPException, status
from loguru import logger
from typing import Dict, Any

from ...core.performance import get_performance_monitor, get_resource_manager
from ...core.cache import get_cache_manager
from ...core.rate_limiter import get_rate_limiter

router = APIRouter()


@router.get("/metrics")
async def get_performance_metrics() -> Dict[str, Any]:
    """Get current performance metrics."""
    try:
        performance_monitor = get_performance_monitor()
        metrics = performance_monitor.get_metrics()
        
        return {
            "status": "success",
            "metrics": metrics,
            "timestamp": metrics.get("timestamp")
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance metrics"
        )


@router.get("/resource-usage")
async def get_resource_usage() -> Dict[str, Any]:
    """Get current system resource usage."""
    try:
        resource_manager = get_resource_manager()
        usage = resource_manager.get_current_usage()
        
        return {
            "status": "success",
            "resource_usage": usage,
            "alerts": resource_manager.check_resource_alerts()
        }
        
    except Exception as e:
        logger.error(f"Failed to get resource usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resource usage"
        )


@router.get("/cache-status")
async def get_cache_status() -> Dict[str, Any]:
    """Get cache system status and statistics."""
    try:
        cache_manager = get_cache_manager()
        stats = await cache_manager.get_stats()
        
        return {
            "status": "success",
            "cache_stats": stats,
            "backend_type": cache_manager.backend.__class__.__name__
        }
        
    except Exception as e:
        logger.error(f"Failed to get cache status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache status"
        )


@router.get("/rate-limits")
async def get_rate_limit_status() -> Dict[str, Any]:
    """Get rate limiting status and configuration."""
    try:
        rate_limiter = get_rate_limiter()
        
        return {
            "status": "success",
            "rate_limits": {
                "search_limit": rate_limiter.search_config.__dict__,
                "upload_limit": rate_limiter.upload_config.__dict__,
                "api_limit": rate_limiter.api_config.__dict__,
                "global_limit": rate_limiter.global_config.__dict__
            },
            "active_limits": len(rate_limiter._windows)
        }
        
    except Exception as e:
        logger.error(f"Failed to get rate limit status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rate limit status"
        )


@router.post("/cache/clear")
async def clear_cache() -> Dict[str, Any]:
    """Clear all cached data."""
    try:
        cache_manager = get_cache_manager()
        await cache_manager.clear_all()
        
        logger.info("Cache cleared manually")
        return {
            "status": "success",
            "message": "Cache cleared successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )


@router.get("/system-health")
async def get_system_health() -> Dict[str, Any]:
    """Get comprehensive system health check."""
    try:
        # Get all monitoring components
        performance_monitor = get_performance_monitor()
        resource_manager = get_resource_manager()
        cache_manager = get_cache_manager()
        
        # Collect health data
        health_data = {
            "status": "healthy",
            "timestamp": performance_monitor.get_metrics().get("timestamp"),
            "components": {}
        }
        
        # Performance metrics health
        metrics = performance_monitor.get_metrics()
        health_data["components"]["performance"] = {
            "status": "healthy",
            "total_operations": metrics.get("total_operations", 0),
            "average_duration": metrics.get("average_duration", 0),
            "operations_per_second": metrics.get("operations_per_second", 0)
        }
        
        # Resource usage health
        usage = resource_manager.get_current_usage()
        resource_status = "healthy"
        alerts = resource_manager.check_resource_alerts()
        
        if alerts:
            resource_status = "warning"
            if any(alert["severity"] == "critical" for alert in alerts):
                resource_status = "critical"
                health_data["status"] = "degraded"
        
        health_data["components"]["resources"] = {
            "status": resource_status,
            "cpu_usage": usage.get("cpu_percent", 0),
            "memory_usage": usage.get("memory_percent", 0),
            "alerts": len(alerts)
        }
        
        # Cache health
        try:
            cache_stats = await cache_manager.get_stats()
            cache_status = "healthy"
            
            # Check cache hit rate
            hit_rate = cache_stats.get("hit_rate", 0)
            if hit_rate < 0.3:  # Less than 30% hit rate might indicate issues
                cache_status = "warning"
            
            health_data["components"]["cache"] = {
                "status": cache_status,
                "hit_rate": hit_rate,
                "total_hits": cache_stats.get("hits", 0),
                "total_misses": cache_stats.get("misses", 0)
            }
        except Exception as e:
            health_data["components"]["cache"] = {
                "status": "error",
                "error": str(e)
            }
            health_data["status"] = "degraded"
        
        return health_data
        
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Health check failed"
        }