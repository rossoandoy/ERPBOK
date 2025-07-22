"""
Exception classes for ERPFTS Phase1 MVP

Provides a hierarchy of custom exceptions for proper error handling
and debugging throughout the application.
"""

from typing import Optional, Dict, Any


class ERPFTSError(Exception):
    """Base exception class for ERPFTS application errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        
    def __str__(self) -> str:
        error_str = self.message
        if self.error_code:
            error_str = f"[{self.error_code}] {error_str}"
        return error_str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
        }


class ConfigurationError(ERPFTSError):
    """Exception raised for configuration-related errors."""
    pass


class ValidationError(ERPFTSError):
    """Exception raised for data validation errors."""
    pass


class DatabaseError(ERPFTSError):
    """Exception raised for database-related errors."""
    pass


class VectorDatabaseError(ERPFTSError):
    """Exception raised for ChromaDB/vector database errors."""
    pass


class DocumentProcessingError(ERPFTSError):
    """Exception raised during document processing."""
    pass


class EmbeddingError(ERPFTSError):
    """Exception raised during embedding generation."""
    pass


class SearchError(ERPFTSError):
    """Exception raised during search operations."""
    pass


class AuthenticationError(ERPFTSError):
    """Exception raised for authentication failures."""
    pass


class AuthorizationError(ERPFTSError):
    """Exception raised for authorization failures."""
    pass


class ExternalServiceError(ERPFTSError):
    """Exception raised for external service communication errors."""
    pass


class WebScrapingError(ERPFTSError):
    """Exception raised during web scraping operations."""
    pass


class FileStorageError(ERPFTSError):
    """Exception raised for file storage operations."""
    pass