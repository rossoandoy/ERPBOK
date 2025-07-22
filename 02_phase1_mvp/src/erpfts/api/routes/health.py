"""
Health check routes for ERPFTS Phase1 MVP

Provides health check endpoints for monitoring system status
and dependencies.
"""

from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime
import sys
import platform

from ...core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str
    environment: Dict[str, Any]
    dependencies: Dict[str, str]


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version=settings.app_version,
        environment={
            "python_version": sys.version,
            "platform": platform.platform(),
            "debug": settings.debug,
        },
        dependencies={
            "database": "sqlite",  # TODO: Check actual database connection
            "vector_db": "chromadb",  # TODO: Check ChromaDB connection
        },
    )


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint for Kubernetes/orchestration."""
    # TODO: Implement actual readiness checks
    # - Database connectivity
    # - ChromaDB connectivity
    # - Required directories exist
    # - Embedding model loaded
    
    return {
        "status": "ready",
        "timestamp": datetime.now(),
        "checks": {
            "database": "ok",
            "vector_database": "ok",
            "storage": "ok",
            "embedding_model": "ok",
        },
    }


@router.get("/live")
async def liveness_check():
    """Liveness check endpoint for Kubernetes/orchestration."""
    return {
        "status": "alive",
        "timestamp": datetime.now(),
    }