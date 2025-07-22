"""
FastAPI REST API module for ERPFTS Phase1 MVP

Provides RESTful endpoints for document ingestion, knowledge search,
and system management.
"""

from .main import app

__all__ = ["app"]