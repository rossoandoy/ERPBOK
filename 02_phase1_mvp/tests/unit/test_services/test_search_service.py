"""
Unit tests for SearchService following TDD practices.

Tests search functionality, result ranking, and query processing.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from src.erpfts.services.search_service import SearchService
from src.erpfts.core.exceptions import SearchError
from src.erpfts.models.database import Document, KnowledgeChunk, SearchHistory
from src.erpfts.schemas.search import SearchResponse, SearchResult


@pytest.mark.unit
@pytest.mark.tdd
class TestSearchService:
    """Test suite for SearchService with TDD approach."""
    
    @pytest.fixture
    def search_service(self, db_session, mock_embedding_service):
        """Create SearchService instance for testing."""
        with patch('src.erpfts.services.search_service.EmbeddingService', return_value=mock_embedding_service):
            return SearchService(db=db_session)
    
    @pytest.fixture
    def sample_search_data(self, db_session, sample_documents_data):
        """Setup sample data for search tests."""
        # Create documents
        documents = []
        for doc_data in sample_documents_data["documents"]:
            document = Document(
                id=doc_data["id"],
                filename=doc_data["filename"],
                processing_status="completed",
                source_type=doc_data["source_type"],
                language=doc_data["language"]
            )
            db_session.add(document)
            documents.append(document)
        
        # Create chunks
        chunks = []
        for chunk_data in sample_documents_data["chunks"]:
            chunk = KnowledgeChunk(
                id=chunk_data["id"],
                document_id=chunk_data["document_id"],
                content=chunk_data["content"],
                chunk_index=chunk_data["chunk_index"],
                start_position=chunk_data["start_position"],
                end_position=chunk_data["end_position"],
                token_count=len(chunk_data["content"].split()),
                embedding_status="completed"
            )
            db_session.add(chunk)
            chunks.append(chunk)
        
        db_session.commit()
        return {"documents": documents, "chunks": chunks}
    
    @pytest.mark.red
    async def test_search_with_valid_query_returns_search_response(
        self, search_service, sample_search_data
    ):
        """
        RED: Test that search with valid query returns SearchResponse.
        
        This test should initially fail as the search implementation
        might not be complete.
        """
        # Arrange
        query = "ERP implementation"
        
        # Act
        result = await search_service.search(query)
        
        # Assert
        assert isinstance(result, SearchResponse)
        assert result.query == query
        assert result.total_results >= 0
        assert isinstance(result.results, list)
        assert result.processing_time >= 0.0
        assert result.search_type in ["semantic", "keyword", "hybrid", "no_results"]
    
    @pytest.mark.red
    async def test_search_with_empty_query_returns_empty_results(
        self, search_service
    ):
        """
        RED: Test that empty query returns appropriate response.
        """
        # Arrange
        query = ""
        
        # Act
        result = await search_service.search(query)
        
        # Assert
        assert isinstance(result, SearchResponse)
        assert result.total_results == 0
        assert len(result.results) == 0
        assert result.search_type == "empty"
    
    @pytest.mark.red
    async def test_search_with_user_id_logs_search_history(
        self, search_service, db_session
    ):
        """
        RED: Test that search with user_id creates search history record.
        """
        # Arrange
        query = "test query"
        user_id = "user_123"
        
        # Act
        await search_service.search(query, user_id=user_id)
        
        # Assert
        history_entries = db_session.query(SearchHistory).filter(
            SearchHistory.user_id == user_id,
            SearchHistory.query == query
        ).all()
        
        assert len(history_entries) == 1
        assert history_entries[0].user_id == user_id
        assert history_entries[0].query == query
    
    @pytest.mark.green
    async def test_semantic_search_returns_relevant_results(
        self, search_service, mock_embedding_service, sample_search_data
    ):
        """
        GREEN: Test semantic search functionality with mocked embedding service.
        
        Minimal implementation to make semantic search work.
        """
        # Arrange
        query = "ERP implementation best practices"
        
        # Configure mock to return sample results
        mock_embedding_service.search_similar.return_value = [
            {
                "id": "chunk_1",
                "content": "ERP implementation requires careful planning and stakeholder engagement.",
                "metadata": {"document_id": "doc_1", "chunk_index": 0, "language": "english", "token_count": 10},
                "similarity": 0.85
            }
        ]
        
        # Act
        results = await search_service._semantic_search(
            query=query, top_k=10, threshold=0.7, filters=None
        )
        
        # Assert
        assert len(results) > 0
        assert isinstance(results[0], SearchResult)
        assert results[0].chunk_id == "chunk_1"
        assert results[0].similarity_score == 0.85
        assert results[0].search_type == "semantic"
    
    @pytest.mark.green
    async def test_keyword_search_finds_matching_content(
        self, search_service, sample_search_data
    ):
        """
        GREEN: Test keyword search functionality.
        """
        # Arrange
        query = "ERP implementation"
        
        # Act
        results = await search_service._keyword_search(
            query=query, top_k=10, filters=None
        )
        
        # Assert
        assert len(results) > 0
        # Should find the chunk containing "ERP implementation"
        matching_result = next(
            (r for r in results if "ERP implementation" in r.content), None
        )
        assert matching_result is not None
        assert matching_result.search_type == "keyword"
        assert len(matching_result.highlight_positions) > 0
    
    @pytest.mark.refactor
    def test_find_keyword_positions_identifies_correct_positions(
        self, search_service
    ):
        """
        REFACTOR: Test keyword position finding for highlighting.
        
        Focus on the quality and accuracy of position detection.
        """
        # Arrange
        content = "ERP implementation requires careful planning. ERP systems are complex."
        keywords = ["ERP", "implementation", "systems"]
        
        # Act
        positions = search_service._find_keyword_positions(content, keywords)
        
        # Assert
        assert len(positions) > 0
        
        # Verify positions are correct
        erp_positions = [pos for pos in positions if content[pos[0]:pos[1]].lower() == "erp"]
        assert len(erp_positions) == 2  # "ERP" appears twice
        
        impl_positions = [pos for pos in positions if "implementation" in content[pos[0]:pos[1]].lower()]
        assert len(impl_positions) == 1  # "implementation" appears once
    
    @pytest.mark.refactor
    def test_merge_positions_handles_overlapping_highlights(
        self, search_service
    ):
        """
        REFACTOR: Test merging of overlapping highlight positions.
        """
        # Arrange
        positions = [(0, 5), (3, 8), (10, 15), (12, 18)]  # Some overlapping
        
        # Act
        merged = search_service._merge_positions(positions)
        
        # Assert
        assert len(merged) == 2  # Should merge overlapping positions
        assert merged[0] == (0, 8)  # First two merged
        assert merged[1] == (10, 18)  # Last two merged
    
    @pytest.mark.refactor
    async def test_combine_results_prioritizes_semantic_over_keyword(
        self, search_service
    ):
        """
        REFACTOR: Test result combination and scoring logic.
        """
        # Arrange
        semantic_results = [
            SearchResult(
                chunk_id="chunk_1",
                document_id="doc_1", 
                content="Semantic result",
                similarity_score=0.9,
                chunk_index=0,
                search_type="semantic",
                highlight_positions=[],
                metadata={}
            )
        ]
        
        keyword_results = [
            SearchResult(
                chunk_id="chunk_1",  # Same chunk
                document_id="doc_1",
                content="Semantic result", 
                similarity_score=0.6,
                chunk_index=0,
                search_type="keyword",
                highlight_positions=[(0, 8)],
                metadata={}
            ),
            SearchResult(
                chunk_id="chunk_2",
                document_id="doc_1",
                content="Keyword only result",
                similarity_score=0.5,
                chunk_index=1, 
                search_type="keyword",
                highlight_positions=[(8, 15)],
                metadata={}
            )
        ]
        
        # Act
        combined = await search_service._combine_results(
            semantic_results, keyword_results, top_k=10
        )
        
        # Assert
        assert len(combined) == 2
        
        # First result should be the hybrid one with higher combined score
        first_result = combined[0]
        assert first_result.chunk_id == "chunk_1"
        assert first_result.search_type == "hybrid"
        assert first_result.combined_score > 0.7  # Semantic weight + keyword weight
        
        # Second result should be keyword-only
        second_result = combined[1]
        assert second_result.chunk_id == "chunk_2"
        assert second_result.search_type == "keyword"
    
    @pytest.mark.refactor
    async def test_enrich_results_adds_document_metadata(
        self, search_service, sample_search_data
    ):
        """
        REFACTOR: Test result enrichment with document metadata.
        """
        # Arrange
        results = [
            SearchResult(
                chunk_id="chunk_1",
                document_id="doc_1",
                content="Test content",
                similarity_score=0.8,
                chunk_index=0,
                search_type="semantic",
                highlight_positions=[],
                metadata={}
            )
        ]
        
        # Act
        enriched = await search_service._enrich_results(results)
        
        # Assert
        assert len(enriched) == 1
        enriched_result = enriched[0]
        
        # Check that document metadata was added
        assert "document_filename" in enriched_result.metadata
        assert "document_created_at" in enriched_result.metadata
        assert "document_language" in enriched_result.metadata
        assert "document_source" in enriched_result.metadata
    
    @pytest.mark.integration
    def test_get_search_history_returns_user_searches(
        self, search_service, db_session
    ):
        """
        Integration test for search history retrieval.
        """
        # Arrange
        user_id = "test_user"
        search_entries = [
            SearchHistory(id=f"search_{i}", user_id=user_id, query=f"query {i}")
            for i in range(5)
        ]
        
        for entry in search_entries:
            db_session.add(entry)
        db_session.commit()
        
        # Act
        history = search_service.get_search_history(user_id, limit=3)
        
        # Assert
        assert len(history) == 3
        assert all(entry.user_id == user_id for entry in history)
        # Should be ordered by creation time (most recent first)
        assert history[0].query == "query 4"  # Most recent
    
    @pytest.mark.integration
    def test_get_popular_searches_returns_frequent_queries(
        self, search_service, db_session
    ):
        """
        Integration test for popular search queries.
        """
        # Arrange - Create search history with repeated queries
        queries_with_counts = [
            ("ERP implementation", 5),
            ("project management", 3), 
            ("change management", 2),
            ("technical guide", 1)
        ]
        
        for query, count in queries_with_counts:
            for i in range(count):
                entry = SearchHistory(
                    id=f"search_{query}_{i}",
                    user_id=f"user_{i}",
                    query=query
                )
                db_session.add(entry)
        
        db_session.commit()
        
        # Act
        popular = search_service.get_popular_searches(limit=3)
        
        # Assert
        assert len(popular) == 3
        
        # Should be ordered by frequency (most popular first)
        assert popular[0]["query"] == "ERP implementation"
        assert popular[0]["count"] == 5
        
        assert popular[1]["query"] == "project management"
        assert popular[1]["count"] == 3
        
        assert popular[2]["query"] == "change management"
        assert popular[2]["count"] == 2
    
    @pytest.mark.slow
    @pytest.mark.integration
    async def test_full_search_workflow_with_real_data(
        self, search_service, sample_search_data, mock_embedding_service
    ):
        """
        Slow integration test for complete search workflow.
        
        Tests the entire search process from query to enriched results.
        """
        # Arrange
        query = "ERP implementation planning"
        user_id = "integration_test_user"
        
        # Configure mock embedding service for consistent results
        mock_embedding_service.search_similar.return_value = [
            {
                "id": "chunk_1",
                "content": "ERP implementation requires careful planning and stakeholder engagement.",
                "metadata": {"document_id": "doc_1", "chunk_index": 0, "language": "english", "token_count": 10},
                "similarity": 0.85
            },
            {
                "id": "chunk_2", 
                "content": "Change management is critical for successful ERP deployment.",
                "metadata": {"document_id": "doc_1", "chunk_index": 1, "language": "english", "token_count": 9},
                "similarity": 0.75
            }
        ]
        
        # Act
        result = await search_service.search(
            query=query,
            user_id=user_id,
            top_k=5,
            threshold=0.7,
            include_metadata=True
        )
        
        # Assert - Response structure
        assert isinstance(result, SearchResponse)
        assert result.query == query
        assert result.total_results > 0
        assert len(result.results) > 0
        assert result.processing_time > 0.0
        assert result.search_type in ["semantic", "keyword", "hybrid"]
        
        # Assert - Results quality
        for search_result in result.results:
            assert isinstance(search_result, SearchResult)
            assert search_result.similarity_score >= 0.7  # Above threshold
            assert search_result.content
            assert search_result.metadata  # Should be enriched with doc metadata
        
        # Assert - Search history logged
        history = search_service.get_search_history(user_id, limit=1)
        assert len(history) == 1
        assert history[0].query == query