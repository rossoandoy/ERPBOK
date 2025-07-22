"""
FastAPI main application for ERPFTS Phase1 MVP

Provides the main FastAPI application with all routes, middleware,
performance monitoring, and configuration for the ERP Fit To Standard knowledge system.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import uvicorn
from loguru import logger

from ..core.config import settings
from ..core.exceptions import ERPFTSError, RateLimitExceeded
from ..core.performance import get_resource_manager
from .middleware import PerformanceMiddleware, add_performance_headers, handle_rate_limit_errors
from .routes import health, documents, search, knowledge, performance


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with resource monitoring."""
    # Startup
    logger.info("Starting ERPFTS Phase1 MVP API")
    settings.ensure_directories()
    
    # Start resource monitoring
    resource_manager = get_resource_manager()
    await resource_manager.start_monitoring()
    
    logger.info(f"API server starting on {settings.api_host}:{settings.api_port}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ERPFTS Phase1 MVP API")
    
    # Stop resource monitoring
    await resource_manager.stop_monitoring()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="ERP Fit To Standard - Knowledge RAG System API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add performance middleware
app.add_middleware(PerformanceMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(ERPFTSError)
async def erpfts_exception_handler(request: Request, exc: ERPFTSError):
    """Handle custom ERPFTS exceptions."""
    logger.error(f"ERPFTS Error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=exc.to_dict(),
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded exceptions."""
    logger.warning(f"Rate limit exceeded for {request.client.host}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "RateLimitExceeded",
            "message": str(exc),
            "retry_after": getattr(exc, 'retry_after', 60),
            "type": "rate_limit"
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.error(f"Validation Error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Request validation failed",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
        },
    )


# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(performance.router, prefix="/performance", tags=["Performance"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["Knowledge"])


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


def run_server():
    """Run the FastAPI server."""
    uvicorn.run(
        "erpfts.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run_server()