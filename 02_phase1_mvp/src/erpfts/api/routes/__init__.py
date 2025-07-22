"""
API routes package for ERPFTS Phase1 MVP

Contains all FastAPI route definitions organized by functionality.
"""

from . import health, documents, search, knowledge

__all__ = [
    "health",
    "documents", 
    "search",
    "knowledge",
]