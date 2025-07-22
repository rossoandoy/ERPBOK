"""
Utilities package for ERPFTS Phase1 MVP

Provides common utility functions for authentication, text processing,
file handling, and other helper functions.
"""

from .auth import *
from .text_processing import *
from .file_utils import *

__all__ = [
    # Authentication utilities
    "get_password_hash",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    
    # Text processing utilities  
    "clean_text",
    "chunk_text",
    "detect_language",
    "calculate_content_hash",
    
    # File utilities
    "get_file_type",
    "validate_file",
    "save_uploaded_file",
    "get_file_size",
]