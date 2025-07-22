"""
ERPFTS (ERP Fit To Standard) - Phase1 MVP
Knowledge RAG System for ERP Standard Frameworks

This package provides the core functionality for the ERP Fit To Standard
knowledge management and retrieval-augmented generation system.
"""

__version__ = "1.0.0"
__title__ = "ERPFTS Phase1 MVP"
__description__ = "ERP Fit To Standard - Knowledge RAG System"
__author__ = "ERPFTS Development Team"
__license__ = "MIT"

# Core modules
from .core.config import settings
from .core.exceptions import ERPFTSError, ConfigurationError, ValidationError

__all__ = [
    "settings",
    "ERPFTSError",
    "ConfigurationError", 
    "ValidationError",
]