"""
Search service for ERPFTS Phase1 MVP

Provides intelligent search functionality combining semantic similarity
with traditional text search and ranking, with performance optimization
through caching, rate limiting, and monitoring.
"""

import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from uuid import uuid4

from loguru import logger
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.exceptions import SearchError, RateLimitExceeded
from ..core.cache import get_cache_manager
from ..core.rate_limiter import get_rate_limiter
from ..core.performance import measure_performance, get_performance_monitor
from ..db.session import get_db_session
from ..models.database import Document, KnowledgeChunk, SearchHistory
from ..schemas.search import SearchRequest, SearchResult, SearchResponse
from ..utils.text_processing import clean_text, detect_language
from .embedding_service import EmbeddingService


class SearchService:
    """Service for knowledge search operations with performance optimization."""
    
    def __init__(self, db: Optional[Session] = None):
        """Initialize search service with performance components."""
        self.db = db or next(get_db_session())
        self.embedding_service = EmbeddingService(db=self.db)
        self.cache_manager = get_cache_manager()
        self.rate_limiter = get_rate_limiter()
        self.performance_monitor = get_performance_monitor()
    
    def _generate_cache_key(self, query: str, filters: Optional[Dict[str, Any]] = None) -> str:
        """Generate a cache key for search results."""
        query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
        
        if filters:
            # Sort filters for consistent hashing
            sorted_filters = sorted(filters.items())
            filters_str = str(sorted_filters)
            filters_hash = hashlib.md5(filters_str.encode('utf-8')).hexdigest()
            return f"{query_hash}:{filters_hash}"
        
        return query_hash
    
    async def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        top_k: int = None,
        threshold: float = None,
        filters: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True
    ) -> SearchResponse:
        """
        Perform intelligent search across the knowledge base with caching and rate limiting.
        
        Args:
            query: Search query string
            user_id: User ID for search history and rate limiting
            top_k: Number of results to return
            threshold: Minimum similarity threshold
            filters: Optional filters for search
            include_metadata: Whether to include document metadata
            
        Returns:
            SearchResponse with results and metadata
            
        Raises:
            SearchError: If search fails
            RateLimitExceeded: If rate limit is exceeded
        """
        async with measure_performance("search_service.search", {"query": query[:50]}):
            try:
                # Rate limiting check
                if user_id:
                    is_allowed, rate_info = await self.rate_limiter.check_search_limit(user_id)
                    if not is_allowed:
                        raise RateLimitExceeded(
                            "Search rate limit exceeded",
                            retry_after=rate_info.get("retry_after", 60)
                        )
                
                # Set default parameters
                top_k = top_k or settings.search_top_k
                threshold = threshold or settings.search_similarity_threshold
                
                # Clean and validate query
                cleaned_query = clean_text(query)
                if not cleaned_query.strip():
                    return SearchResponse(
                        results=[],
                        total_results=0,
                        query=query,
                        processing_time=0.0,
                        search_type="empty"
                    )
                
                # Check cache for existing results
                cache_key = self._generate_cache_key(cleaned_query, filters)
                cached_results = await self.cache_manager.get_search_results(cache_key)
                
                if cached_results:
                    logger.debug(f"Cache hit for search query: {query[:50]}...")
                    # Convert cached results back to SearchResponse
                    return SearchResponse(**cached_results)
                
                start_time = datetime.now()
                
                # Log search attempt
                if user_id:
                    await self._log_search(user_id, query)
                
                # Perform semantic search
                semantic_results = await self._semantic_search(
                    cleaned_query, top_k, threshold, filters
                )
                
                # Perform keyword search as fallback/supplement
                keyword_results = await self._keyword_search(
                    cleaned_query, top_k, filters
                )
                
                # Combine and rank results
                combined_results = await self._combine_results(
                    semantic_results, keyword_results, top_k
                )
                
                # Enrich results with metadata
                if include_metadata:
                    combined_results = await self._enrich_results(combined_results)
                
                # Calculate processing time
                processing_time = (datetime.now() - start_time).total_seconds()
                
                # Determine search type based on results
                search_type = self._determine_search_type(
                    semantic_results, keyword_results, combined_results
                )
                
                response = SearchResponse(
                    results=combined_results[:top_k],
                    total_results=len(combined_results),
                    query=query,
                    processing_time=processing_time,
                    search_type=search_type,
                    filters_applied=filters or {}
                )
                
                # Cache the results for future use
                await self.cache_manager.set_search_results(
                    cache_key,
                    response.dict(),
                    ttl=settings.cache_search_ttl
                )
                
                logger.info(
                    f"Search completed: query='{query[:50]}...', results={len(combined_results)}, "
                    f"time={processing_time:.2f}s, type={search_type}"
                )
                
                return response
                
            except RateLimitExceeded:
                # Re-raise rate limit exceptions
                raise
            except Exception as e:
                logger.error(f"Search failed for query '{query[:50]}...': {str(e)}")
                raise SearchError(f"Search operation failed: {str(e)}")
    
    async def _semantic_search(
        self,
        query: str,
        top_k: int,
        threshold: float,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic similarity search.
        
        Args:
            query: Cleaned search query
            top_k: Number of results
            threshold: Similarity threshold
            filters: Optional filters
            
        Returns:
            List of semantic search results
        """
        try:
            results = await self.embedding_service.search_similar(
                query=query,
                top_k=top_k * 2,  # Get more to allow for filtering
                threshold=threshold,
                filters=filters
            )
            
            # Convert to SearchResult format
            search_results = []
            for result in results:
                # Get chunk details from database
                chunk = self.db.query(KnowledgeChunk).filter(
                    KnowledgeChunk.id == result["id"]
                ).first()
                
                if chunk:
                    search_result = SearchResult(
                        chunk_id=result["id"],
                        document_id=result["metadata"]["document_id"],
                        content=result["content"],
                        similarity_score=float(result["similarity"]),
                        chunk_index=result["metadata"]["chunk_index"],
                        search_type="semantic",
                        highlight_positions=[],
                        metadata=result["metadata"]
                    )
                    search_results.append(search_result)
            
            return search_results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}")
            return []
    
    async def _keyword_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Perform keyword-based text search.
        
        Args:
            query: Search query
            top_k: Number of results
            filters: Optional filters
            
        Returns:
            List of keyword search results
        """
        try:
            # Tokenize query
            keywords = query.lower().split()
            
            # Build database query
            query_obj = self.db.query(KnowledgeChunk, Document).join(
                Document, KnowledgeChunk.document_id == Document.id
            )
            
            # Apply text search filters
            text_filters = []
            for keyword in keywords:
                text_filters.append(
                    KnowledgeChunk.content.ilike(f"%{keyword}%")
                )
            
            if text_filters:
                query_obj = query_obj.filter(or_(*text_filters))
            
            # Apply additional filters
            if filters:
                if "document_id" in filters:
                    query_obj = query_obj.filter(
                        KnowledgeChunk.document_id == filters["document_id"]
                    )
                if "language" in filters:
                    query_obj = query_obj.filter(
                        KnowledgeChunk.language == filters["language"]
                    )
            
            # Execute query
            results = query_obj.limit(top_k).all()
            
            # Convert to SearchResult format
            search_results = []
            for chunk, document in results:
                # Calculate simple keyword match score
                content_lower = chunk.content.lower()
                matches = sum(1 for keyword in keywords if keyword in content_lower)
                score = matches / len(keywords) if keywords else 0.0
                
                # Find highlight positions
                highlight_positions = self._find_keyword_positions(
                    chunk.content, keywords
                )
                
                search_result = SearchResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    content=chunk.content,
                    similarity_score=score,
                    chunk_index=chunk.chunk_index,
                    search_type="keyword",
                    highlight_positions=highlight_positions,
                    metadata={
                        "document_filename": document.filename,
                        "language": chunk.language,
                        "token_count": chunk.token_count
                    }
                )
                search_results.append(search_result)
            
            return search_results
            
        except Exception as e:
            logger.error(f"Keyword search failed: {str(e)}")
            return []
    
    def _find_keyword_positions(
        self, 
        content: str, 
        keywords: List[str]
    ) -> List[Tuple[int, int]]:
        """
        Find positions of keywords in content for highlighting.
        
        Args:
            content: Text content
            keywords: List of keywords to find
            
        Returns:
            List of (start, end) positions
        """
        positions = []
        content_lower = content.lower()
        
        for keyword in keywords:
            start_pos = 0
            while True:
                pos = content_lower.find(keyword, start_pos)
                if pos == -1:
                    break
                
                positions.append((pos, pos + len(keyword)))
                start_pos = pos + 1
        
        # Sort and merge overlapping positions
        positions.sort()
        merged = []
        for start, end in positions:
            if merged and start <= merged[-1][1]:
                # Overlapping - merge
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        
        return merged
    
    async def _combine_results(
        self,
        semantic_results: List[SearchResult],
        keyword_results: List[SearchResult],
        top_k: int
    ) -> List[SearchResult]:
        """
        Combine and rank semantic and keyword search results.
        
        Args:
            semantic_results: Results from semantic search
            keyword_results: Results from keyword search
            top_k: Number of top results to keep
            
        Returns:
            Combined and ranked results
        """
        try:
            # Create a map to avoid duplicates
            result_map = {}
            
            # Add semantic results with higher weight
            for result in semantic_results:
                result.combined_score = result.similarity_score * 0.7  # Semantic weight
                result_map[result.chunk_id] = result
            
            # Add keyword results, combining scores if duplicates
            for result in keyword_results:
                chunk_id = result.chunk_id
                if chunk_id in result_map:
                    # Combine scores
                    existing = result_map[chunk_id]
                    keyword_score = result.similarity_score * 0.3  # Keyword weight
                    existing.combined_score += keyword_score
                    existing.search_type = "hybrid"
                    
                    # Merge highlight positions
                    if result.highlight_positions:
                        existing.highlight_positions.extend(result.highlight_positions)
                        # Re-sort and merge
                        existing.highlight_positions = self._merge_positions(
                            existing.highlight_positions
                        )
                else:
                    # New result from keyword search only
                    result.combined_score = result.similarity_score * 0.3
                    result_map[chunk_id] = result
            
            # Sort by combined score
            combined_results = list(result_map.values())
            combined_results.sort(key=lambda x: x.combined_score, reverse=True)
            
            return combined_results[:top_k]
            
        except Exception as e:
            logger.error(f"Result combination failed: {str(e)}")
            # Return semantic results as fallback
            return semantic_results[:top_k]
    
    def _merge_positions(
        self, 
        positions: List[Tuple[int, int]]
    ) -> List[Tuple[int, int]]:
        """Merge overlapping highlight positions."""
        if not positions:
            return []
        
        positions.sort()
        merged = [positions[0]]
        
        for start, end in positions[1:]:
            if start <= merged[-1][1]:
                # Overlapping - merge
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        
        return merged
    
    async def _enrich_results(
        self, 
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Enrich search results with additional metadata.
        
        Args:
            results: List of search results
            
        Returns:
            Enriched results
        """
        try:
            # Get document details for all results
            document_ids = list(set(result.document_id for result in results))
            documents = self.db.query(Document).filter(
                Document.id.in_(document_ids)
            ).all()
            
            document_map = {doc.id: doc for doc in documents}
            
            # Enrich each result
            for result in results:
                document = document_map.get(result.document_id)
                if document:
                    result.metadata.update({
                        "document_filename": document.filename,
                        "document_created_at": document.created_at.isoformat(),
                        "document_language": document.language,
                        "document_source": document.source_type
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Result enrichment failed: {str(e)}")
            return results
    
    def _determine_search_type(
        self,
        semantic_results: List,
        keyword_results: List,
        combined_results: List
    ) -> str:
        """
        Determine the primary search type used.
        
        Args:
            semantic_results: Semantic search results
            keyword_results: Keyword search results
            combined_results: Final combined results
            
        Returns:
            Search type string
        """
        if not combined_results:
            return "no_results"
        
        if not semantic_results and keyword_results:
            return "keyword_only"
        
        if semantic_results and not keyword_results:
            return "semantic_only"
        
        if semantic_results and keyword_results:
            return "hybrid"
        
        return "unknown"
    
    async def _log_search(self, user_id: str, query: str) -> None:
        """
        Log search query to history.
        
        Args:
            user_id: User ID
            query: Search query
        """
        try:
            search_history = SearchHistory(
                id=str(uuid4()),
                user_id=user_id,
                query=query,
                language=detect_language(query)
            )
            
            self.db.add(search_history)
            self.db.commit()
            
        except Exception as e:
            # Don't fail search if logging fails
            logger.error(f"Failed to log search: {str(e)}")
            self.db.rollback()
    
    def get_search_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[SearchHistory]:
        """
        Get search history for a user.
        
        Args:
            user_id: User ID
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            List of search history entries
        """
        return self.db.query(SearchHistory).filter(
            SearchHistory.user_id == user_id
        ).order_by(
            SearchHistory.created_at.desc()
        ).offset(offset).limit(limit).all()
    
    def get_popular_searches(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get most popular search queries.
        
        Args:
            limit: Number of results
            
        Returns:
            List of popular queries with counts
        """
        try:
            results = self.db.query(
                SearchHistory.query,
                func.count(SearchHistory.id).label('count')
            ).group_by(
                SearchHistory.query
            ).order_by(
                func.count(SearchHistory.id).desc()
            ).limit(limit).all()
            
            return [
                {"query": query, "count": count}
                for query, count in results
            ]
            
        except Exception as e:
            logger.error(f"Failed to get popular searches: {str(e)}")
            return []