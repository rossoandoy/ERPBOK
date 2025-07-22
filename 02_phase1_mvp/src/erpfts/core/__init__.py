"""
Core module for ERPFTS Phase1 MVP

Provides configuration, exceptions, and core business logic.
"""

from .config import settings
from .exceptions import ERPFTSError, ConfigurationError, ValidationError

__all__ = [
    "settings",
    "ERPFTSError",
    "ConfigurationError",
    "ValidationError",
]