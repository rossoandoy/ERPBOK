"""
Performance monitoring and optimization utilities for ERPFTS Phase1 MVP.

Implements performance metrics collection, query optimization,
and resource monitoring for system scalability.
"""

import asyncio
import time
import psutil
import functools
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta

from loguru import logger

from src.erpfts.core.config import settings


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    operation: str
    start_time: float
    end_time: float
    duration: float = field(init=False)
    memory_before: float = 0.0
    memory_after: float = 0.0
    cpu_percent: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.duration = self.end_time - self.start_time


class PerformanceMonitor:
    """System performance monitoring and metrics collection."""
    
    def __init__(self, max_metrics: int = 10000):
        self.metrics: deque[PerformanceMetrics] = deque(maxlen=max_metrics)
        self.operation_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "count": 0,
            "total_duration": 0.0,
            "min_duration": float('inf'),
            "max_duration": 0.0,
            "errors": 0,
            "last_executed": None
        })
        self._lock = asyncio.Lock()
    
    async def record_metrics(self, metrics: PerformanceMetrics):
        """Record performance metrics."""
        async with self._lock:
            self.metrics.append(metrics)
            
            # Update operation statistics
            stats = self.operation_stats[metrics.operation]
            stats["count"] += 1
            stats["total_duration"] += metrics.duration
            stats["min_duration"] = min(stats["min_duration"], metrics.duration)
            stats["max_duration"] = max(stats["max_duration"], metrics.duration)
            stats["last_executed"] = datetime.fromtimestamp(metrics.end_time)
            
            if metrics.error:
                stats["errors"] += 1
    
    async def get_operation_stats(self, operation: str = None) -> Dict[str, Any]:
        """Get performance statistics for operations."""
        async with self._lock:
            if operation:
                stats = self.operation_stats.get(operation, {})
                if stats and stats["count"] > 0:
                    stats["avg_duration"] = stats["total_duration"] / stats["count"]
                    stats["error_rate"] = stats["errors"] / stats["count"]
                return dict(stats)
            else:
                result = {}
                for op, stats in self.operation_stats.items():
                    if stats["count"] > 0:
                        op_stats = dict(stats)
                        op_stats["avg_duration"] = stats["total_duration"] / stats["count"]
                        op_stats["error_rate"] = stats["errors"] / stats["count"]
                        result[op] = op_stats
                return result
    
    async def get_recent_metrics(
        self, 
        operation: str = None, 
        minutes: int = 60
    ) -> List[PerformanceMetrics]:
        """Get recent metrics within specified time window."""
        cutoff_time = time.time() - (minutes * 60)
        
        async with self._lock:
            recent_metrics = []
            for metric in self.metrics:
                if metric.end_time >= cutoff_time:
                    if operation is None or metric.operation == operation:
                        recent_metrics.append(metric)
            
            return recent_metrics
    
    async def get_slow_operations(
        self, 
        threshold_seconds: float = 1.0,
        limit: int = 100
    ) -> List[PerformanceMetrics]:
        """Get operations that exceeded duration threshold."""
        async with self._lock:
            slow_ops = []
            for metric in self.metrics:
                if metric.duration >= threshold_seconds and not metric.error:
                    slow_ops.append(metric)
                    if len(slow_ops) >= limit:
                        break
            
            return sorted(slow_ops, key=lambda m: m.duration, reverse=True)
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get current system health metrics."""
        try:
            # CPU and memory usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network I/O
            network = psutil.net_io_counters()
            
            # Process info
            process = psutil.Process()
            process_memory = process.memory_info()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count(),
                    "load_avg": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                },
                "process": {
                    "memory_rss": process_memory.rss,
                    "memory_vms": process_memory.vms,
                    "cpu_percent": process.cpu_percent(),
                    "num_threads": process.num_threads(),
                    "open_files": len(process.open_files()),
                    "connections": len(process.connections())
                }
            }
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}


# Global performance monitor instance
performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global performance_monitor
    
    if performance_monitor is None:
        performance_monitor = PerformanceMonitor()
    
    return performance_monitor


@asynccontextmanager
async def measure_performance(
    operation: str,
    metadata: Dict[str, Any] = None,
    track_memory: bool = True
):
    """Context manager to measure operation performance."""
    monitor = get_performance_monitor()
    
    start_time = time.time()
    memory_before = 0.0
    error = None
    
    if track_memory:
        try:
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
        except Exception as e:
            logger.warning(f"Could not get memory info: {e}")
    
    try:
        yield
    except Exception as e:
        error = str(e)
        raise
    finally:
        end_time = time.time()
        memory_after = 0.0
        cpu_percent = 0.0
        
        if track_memory:
            try:
                process = psutil.Process()
                memory_after = process.memory_info().rss / 1024 / 1024  # MB
                cpu_percent = process.cpu_percent()
            except Exception as e:
                logger.warning(f"Could not get final system info: {e}")
        
        metrics = PerformanceMetrics(
            operation=operation,
            start_time=start_time,
            end_time=end_time,
            memory_before=memory_before,
            memory_after=memory_after,
            cpu_percent=cpu_percent,
            error=error,
            metadata=metadata or {}
        )
        
        await monitor.record_metrics(metrics)


def performance_tracked(operation: str = None, track_memory: bool = True):
    """Decorator to track function performance."""
    def decorator(func: Callable):
        op_name = operation or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            async with measure_performance(op_name, track_memory=track_memory):
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to handle the async context manager
            async def _run():
                async with measure_performance(op_name, track_memory=track_memory):
                    return func(*args, **kwargs)
            
            # If we're in an async context, run it
            try:
                loop = asyncio.get_running_loop()
                task = loop.create_task(_run())
                return loop.run_until_complete(task)
            except RuntimeError:
                # No event loop running, create one
                return asyncio.run(_run())
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class QueryOptimizer:
    """Database query optimization utilities."""
    
    def __init__(self):
        self.query_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "count": 0,
            "total_duration": 0.0,
            "avg_duration": 0.0,
            "slow_queries": []
        })
        self._lock = asyncio.Lock()
    
    async def record_query(
        self, 
        query_hash: str, 
        duration: float, 
        query_text: str = None,
        result_count: int = None
    ):
        """Record query performance."""
        async with self._lock:
            stats = self.query_stats[query_hash]
            stats["count"] += 1
            stats["total_duration"] += duration
            stats["avg_duration"] = stats["total_duration"] / stats["count"]
            
            if query_text:
                stats["query_text"] = query_text
            if result_count is not None:
                stats["last_result_count"] = result_count
            
            # Track slow queries
            if duration > settings.slow_query_threshold:
                slow_query = {
                    "duration": duration,
                    "timestamp": datetime.now().isoformat(),
                    "query_text": query_text,
                    "result_count": result_count
                }
                stats["slow_queries"].append(slow_query)
                
                # Keep only recent slow queries
                if len(stats["slow_queries"]) > 10:
                    stats["slow_queries"] = stats["slow_queries"][-10:]
    
    async def get_slow_queries(self, min_duration: float = None) -> List[Dict[str, Any]]:
        """Get slow query statistics."""
        if min_duration is None:
            min_duration = settings.slow_query_threshold
        
        async with self._lock:
            slow_queries = []
            for query_hash, stats in self.query_stats.items():
                if stats["avg_duration"] >= min_duration:
                    slow_queries.append({
                        "query_hash": query_hash,
                        "avg_duration": stats["avg_duration"],
                        "count": stats["count"],
                        "total_duration": stats["total_duration"],
                        "query_text": stats.get("query_text"),
                        "recent_slow_queries": stats["slow_queries"]
                    })
            
            return sorted(slow_queries, key=lambda x: x["avg_duration"], reverse=True)
    
    async def get_query_recommendations(self) -> List[Dict[str, Any]]:
        """Get query optimization recommendations."""
        recommendations = []
        slow_queries = await self.get_slow_queries()
        
        for query_info in slow_queries:
            recommendations.append({
                "type": "slow_query",
                "priority": "high" if query_info["avg_duration"] > 5.0 else "medium",
                "description": f"Query with hash {query_info['query_hash']} has average duration of {query_info['avg_duration']:.2f}s",
                "suggestion": "Consider adding indexes, optimizing joins, or implementing caching",
                "query_hash": query_info["query_hash"],
                "avg_duration": query_info["avg_duration"],
                "execution_count": query_info["count"]
            })
        
        return recommendations


class ResourceManager:
    """System resource management and monitoring."""
    
    def __init__(self):
        self.resource_alerts: List[Dict[str, Any]] = []
        self.monitoring_active = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self, interval: int = 60):
        """Start resource monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info("Resource monitoring started")
    
    async def stop_monitoring(self):
        """Stop resource monitoring."""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        self.monitoring_active = False
        logger.info("Resource monitoring stopped")
    
    async def _monitor_loop(self, interval: int):
        """Resource monitoring loop."""
        while self.monitoring_active:
            try:
                await self._check_resources()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(interval)
    
    async def _check_resources(self):
        """Check system resources and generate alerts."""
        try:
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > settings.memory_alert_threshold:
                alert = {
                    "type": "memory",
                    "level": "warning" if memory.percent < 90 else "critical",
                    "value": memory.percent,
                    "threshold": settings.memory_alert_threshold,
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Memory usage at {memory.percent:.1f}%"
                }
                await self._add_alert(alert)
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > settings.cpu_alert_threshold:
                alert = {
                    "type": "cpu",
                    "level": "warning" if cpu_percent < 90 else "critical",
                    "value": cpu_percent,
                    "threshold": settings.cpu_alert_threshold,
                    "timestamp": datetime.now().isoformat(),
                    "message": f"CPU usage at {cpu_percent:.1f}%"
                }
                await self._add_alert(alert)
            
            # Check disk space
            disk = psutil.disk_usage('/')
            if disk.percent > settings.disk_alert_threshold:
                alert = {
                    "type": "disk",
                    "level": "warning" if disk.percent < 95 else "critical",
                    "value": disk.percent,
                    "threshold": settings.disk_alert_threshold,
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Disk usage at {disk.percent:.1f}%"
                }
                await self._add_alert(alert)
                
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
    
    async def _add_alert(self, alert: Dict[str, Any]):
        """Add resource alert."""
        # Avoid duplicate alerts (same type within 5 minutes)
        now = datetime.now()
        cutoff = now - timedelta(minutes=5)
        
        recent_alerts = [
            a for a in self.resource_alerts
            if a["type"] == alert["type"] and 
            datetime.fromisoformat(a["timestamp"]) > cutoff
        ]
        
        if not recent_alerts:
            self.resource_alerts.append(alert)
            logger.warning(f"Resource alert: {alert['message']}")
            
            # Keep only recent alerts (last 100)
            if len(self.resource_alerts) > 100:
                self.resource_alerts = self.resource_alerts[-100:]
    
    async def get_alerts(self, level: str = None) -> List[Dict[str, Any]]:
        """Get resource alerts."""
        if level:
            return [alert for alert in self.resource_alerts if alert["level"] == level]
        return list(self.resource_alerts)
    
    async def clear_alerts(self, alert_type: str = None):
        """Clear resource alerts."""
        if alert_type:
            self.resource_alerts = [
                alert for alert in self.resource_alerts 
                if alert["type"] != alert_type
            ]
        else:
            self.resource_alerts.clear()


# Global instances
query_optimizer: Optional[QueryOptimizer] = None
resource_manager: Optional[ResourceManager] = None


def get_query_optimizer() -> QueryOptimizer:
    """Get global query optimizer instance."""
    global query_optimizer
    
    if query_optimizer is None:
        query_optimizer = QueryOptimizer()
    
    return query_optimizer


def get_resource_manager() -> ResourceManager:
    """Get global resource manager instance."""
    global resource_manager
    
    if resource_manager is None:
        resource_manager = ResourceManager()
    
    return resource_manager