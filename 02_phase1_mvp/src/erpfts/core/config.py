"""
Configuration management for ERPFTS Phase1 MVP

Provides centralized configuration using Pydantic settings with environment
variable support and validation.
"""

from pathlib import Path
from typing import Optional, List
from pydantic import BaseSettings, Field, validator
from pydantic_settings import BaseSettings as PydanticSettings


class ERPFTSSettings(PydanticSettings):
    """
    ERPFTS Phase1 MVP Configuration Settings
    
    Environment variables can be used to override defaults:
    - ERPFTS_DATABASE_URL
    - ERPFTS_CHROMA_HOST
    - ERPFTS_LOG_LEVEL
    etc.
    """
    
    # Application Settings
    app_name: str = "ERPFTS Phase1 MVP"
    app_version: str = "1.0.0"
    debug: bool = Field(False, description="Enable debug mode")
    log_level: str = Field("INFO", description="Logging level")
    
    # API Settings
    api_host: str = Field("localhost", description="API server host")
    api_port: int = Field(8000, description="API server port")
    api_reload: bool = Field(False, description="Enable API auto-reload")
    
    # UI Settings
    ui_host: str = Field("localhost", description="Streamlit UI host")
    ui_port: int = Field(8501, description="Streamlit UI port")
    ui_title: str = "ERP Fit To Standard - Knowledge Search"
    
    # Database Settings
    database_url: str = Field(
        "sqlite:///./data/erpfts.db",
        description="Database connection URL"
    )
    database_echo: bool = Field(False, description="Echo SQL queries")
    
    # ChromaDB Settings
    chroma_host: str = Field("localhost", description="ChromaDB host")
    chroma_port: int = Field(8000, description="ChromaDB port")
    chroma_collection_name: str = Field(
        "erpfts_knowledge", 
        description="ChromaDB collection name"
    )
    chroma_persist_directory: str = Field(
        "./data/chroma", 
        description="ChromaDB persistence directory"
    )
    
    # Embedding Settings
    embedding_model: str = Field(
        "intfloat/multilingual-e5-large",
        description="Sentence transformer model for embeddings"
    )
    embedding_dimension: int = Field(1024, description="Embedding vector dimension")
    embedding_batch_size: int = Field(32, description="Batch size for embedding generation")
    
    # Document Processing Settings
    max_file_size_mb: int = Field(50, description="Maximum file size in MB")
    chunk_size: int = Field(1000, description="Text chunk size for processing")
    chunk_overlap: int = Field(200, description="Overlap between chunks")
    supported_file_types: List[str] = Field(
        [".pdf", ".docx", ".txt", ".html"],
        description="Supported file types for ingestion"
    )
    
    # Search Settings
    search_top_k: int = Field(10, description="Number of top search results")
    search_similarity_threshold: float = Field(
        0.7, 
        description="Minimum similarity threshold for search results"
    )
    
    # Web Scraping Settings
    scraping_user_agent: str = Field(
        "ERPFTS-Bot/1.0 (+https://erpfts.local/bot)",
        description="User agent for web scraping"
    )
    scraping_delay_seconds: float = Field(1.0, description="Delay between requests")
    scraping_timeout_seconds: int = Field(30, description="Request timeout")
    
    # Storage Settings
    storage_root: str = Field("./data", description="Root storage directory")
    upload_directory: str = Field("uploads", description="Upload directory name")
    cache_directory: str = Field("cache", description="Cache directory name")
    
    # Security Settings
    secret_key: str = Field(
        "your-secret-key-change-in-production",
        description="Secret key for JWT tokens"
    )
    access_token_expire_minutes: int = Field(
        30,
        description="Access token expiration time in minutes"
    )
    
    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()
    
    @validator("database_url")
    def validate_database_url(cls, v):
        if not v.startswith(("sqlite://", "postgresql://", "mysql://")):
            raise ValueError("Database URL must start with sqlite://, postgresql://, or mysql://")
        return v
    
    @validator("search_similarity_threshold")
    def validate_similarity_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Similarity threshold must be between 0.0 and 1.0")
        return v
    
    @property
    def storage_path(self) -> Path:
        """Get the storage root path."""
        return Path(self.storage_root)
    
    @property
    def upload_path(self) -> Path:
        """Get the upload directory path."""
        return self.storage_path / self.upload_directory
    
    @property
    def cache_path(self) -> Path:
        """Get the cache directory path."""
        return self.storage_path / self.cache_directory
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            self.storage_path,
            self.upload_path,
            self.cache_path,
            Path(self.chroma_persist_directory),
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    class Config:
        env_prefix = "ERPFTS_"
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = ERPFTSSettings()