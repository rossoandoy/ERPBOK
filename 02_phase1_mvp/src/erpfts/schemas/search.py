"""
Search-related Pydantic schemas for ERPFTS Phase1 MVP

Defines request/response models for search operations.
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Request schema for knowledge search."""
    
    query: str = Field(..., min_length=1, description="Search query text")
    top_k: int = Field(10, ge=1, le=100, description="Number of results to return")
    threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional search filters")
    include_metadata: bool = Field(True, description="Include document metadata in results")


class SearchResult(BaseModel):
    """Individual search result."""
    
    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: str = Field(..., description="Parent document identifier")
    content: str = Field(..., description="Chunk text content")
    similarity_score: float = Field(..., description="Similarity score")
    chunk_index: int = Field(..., description="Index of chunk within document")
    search_type: str = Field(..., description="Type of search used")
    highlight_positions: List[Tuple[int, int]] = Field(default=[], description="Text highlight positions")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")
    combined_score: Optional[float] = Field(None, description="Combined ranking score")


class SearchResponse(BaseModel):
    """Response schema for search operations."""
    
    results: List[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results found")
    query: str = Field(..., description="Original search query")
    processing_time: float = Field(..., description="Time taken to process search")
    search_type: str = Field(..., description="Primary search method used")
    filters_applied: Dict[str, Any] = Field(default={}, description="Filters applied to search")


class PopularQuery(BaseModel):
    """Popular search query model."""
    
    query: str = Field(..., description="Search query text")
    count: int = Field(..., description="Number of times searched")


class SearchStats(BaseModel):
    """Search statistics model."""
    
    total_searches: int = Field(..., description="Total number of searches")
    unique_queries: int = Field(..., description="Number of unique queries")
    avg_results_per_search: float = Field(..., description="Average results per search")
    popular_queries: List[PopularQuery] = Field(..., description="Most popular queries")