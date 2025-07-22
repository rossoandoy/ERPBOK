"""
Integration tests for search-related API endpoints.

Tests search functionality, query processing, result ranking,
and search history management through complete API workflows.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.erpfts.models.database import Document, KnowledgeChunk, SearchHistory


@pytest.mark.integration
@pytest.mark.api
class TestSearchEndpoints:
    """Integration tests for search API endpoints."""
    
    def test_search_basic_query_success(self, client: TestClient, sample_search_data):
        """Test basic search with valid query."""
        # Arrange
        search_payload = {
            "query": "ERP implementation",
            "top_k": 5,
            "threshold": 0.7
        }
        
        # Act
        with patch('src.erpfts.services.search_service.SearchService.search') as mock_search:
            # Mock search response
            from src.erpfts.schemas.search import SearchResponse, SearchResult
            mock_search.return_value = SearchResponse(
                query="ERP implementation",
                total_results=1,
                results=[
                    SearchResult(
                        chunk_id="chunk_1",
                        document_id="doc_1",
                        content="ERP implementation requires careful planning.",
                        similarity_score=0.85,
                        chunk_index=0,
                        search_type="semantic",
                        highlight_positions=[],
                        metadata={}
                    )
                ],
                processing_time=0.1,
                search_type="semantic"
            )
            
            response = client.post("/api/v1/search/", json=search_payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["query"] == "ERP implementation"
        assert data["total_results"] == 1
        assert len(data["results"]) == 1
        assert data["processing_time"] > 0.0
        assert data["search_type"] == "semantic"
        
        # Check result structure
        result = data["results"][0]
        assert result["chunk_id"] == "chunk_1"
        assert result["document_id"] == "doc_1"
        assert result["similarity_score"] == 0.85
    
    def test_search_empty_query(self, client: TestClient):
        """Test search with empty query."""
        # Arrange
        search_payload = {
            "query": "",
            "top_k": 5
        }
        
        # Act
        response = client.post("/api/v1/search/", json=search_payload)
        
        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "empty" in data["detail"].lower() or "required" in data["detail"].lower()
    
    def test_search_with_filters(self, client: TestClient, sample_search_data):
        """Test search with document type and language filters."""
        # Arrange
        search_payload = {
            "query": "technical implementation",
            "top_k": 10,
            "threshold": 0.6,
            "filters": {
                "document_type": "pdf",
                "language": "english"
            }
        }
        
        # Act
        with patch('src.erpfts.services.search_service.SearchService.search') as mock_search:
            from src.erpfts.schemas.search import SearchResponse
            mock_search.return_value = SearchResponse(
                query="technical implementation",
                total_results=0,
                results=[],
                processing_time=0.05,
                search_type="no_results"
            )
            
            response = client.post("/api/v1/search/", json=search_payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "technical implementation"
    
    def test_search_with_user_context(self, client: TestClient):
        """Test search with user context for history tracking."""
        # Arrange
        search_payload = {
            "query": "project management",
            "user_id": "user_123",
            "top_k": 5
        }
        
        # Act
        with patch('src.erpfts.services.search_service.SearchService.search') as mock_search:
            from src.erpfts.schemas.search import SearchResponse
            mock_search.return_value = SearchResponse(
                query="project management",
                total_results=0,
                results=[],
                processing_time=0.03,
                search_type="no_results"
            )
            
            response = client.post("/api/v1/search/", json=search_payload)
        
        # Assert
        assert response.status_code == 200
        # Verify search was called with user_id
        mock_search.assert_called_once()
        args, kwargs = mock_search.call_args
        assert kwargs.get('user_id') == "user_123"
    
    def test_search_invalid_parameters(self, client: TestClient):
        """Test search with invalid parameters."""
        # Arrange - negative top_k
        search_payload = {
            "query": "test query",
            "top_k": -1
        }
        
        # Act
        response = client.post("/api/v1/search/", json=search_payload)
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_search_threshold_validation(self, client: TestClient):
        """Test search with invalid threshold values."""
        # Arrange - threshold out of range
        search_payload = {
            "query": "test query",
            "threshold": 1.5  # Invalid: should be 0-1
        }
        
        # Act
        response = client.post("/api/v1/search/", json=search_payload)
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_get_search_history_success(self, client: TestClient, db_session):
        """Test retrieving user search history."""
        # Arrange
        user_id = "history_test_user"
        search_entries = [
            SearchHistory(
                id=f"search_{i}",
                user_id=user_id,
                query=f"test query {i}",
                result_count=i + 1
            )
            for i in range(3)
        ]
        
        for entry in search_entries:
            db_session.add(entry)
        db_session.commit()
        
        # Act
        response = client.get(f"/api/v1/search/history/{user_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert "history" in data
        assert len(data["history"]) == 3
        assert "total" in data
        
        # Verify history entry structure
        for entry in data["history"]:
            assert "query" in entry
            assert "timestamp" in entry
            assert "result_count" in entry
    
    def test_get_search_history_with_pagination(self, client: TestClient, db_session):
        """Test search history with pagination parameters."""
        # Arrange
        user_id = "pagination_test_user"
        search_entries = [
            SearchHistory(
                id=f"paginate_search_{i}",
                user_id=user_id,
                query=f"paginate query {i}"
            )
            for i in range(10)
        ]
        
        for entry in search_entries:
            db_session.add(entry)
        db_session.commit()
        
        # Act
        response = client.get(f"/api/v1/search/history/{user_id}?limit=5&offset=2")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["history"]) <= 5
        assert data["limit"] == 5
        assert data["offset"] == 2
    
    def test_get_search_history_user_not_found(self, client: TestClient):
        """Test search history for non-existent user."""
        # Act
        response = client.get("/api/v1/search/history/nonexistent_user")
        
        # Assert
        assert response.status_code == 200  # Returns empty history instead of 404
        data = response.json()
        assert data["history"] == []
        assert data["total"] == 0
    
    def test_get_popular_searches(self, client: TestClient, db_session):
        """Test retrieving popular search queries."""
        # Arrange - Create search history with repeated queries
        queries_with_counts = [
            ("ERP implementation", 5),
            ("project management", 3),
            ("change management", 2)
        ]
        
        for query, count in queries_with_counts:
            for i in range(count):
                entry = SearchHistory(
                    id=f"popular_{query}_{i}",
                    user_id=f"user_{i}",
                    query=query
                )
                db_session.add(entry)
        
        db_session.commit()
        
        # Act
        response = client.get("/api/v1/search/popular?limit=2")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert "popular_searches" in data
        assert len(data["popular_searches"]) <= 2
        
        # Verify ordering by popularity
        popular = data["popular_searches"]
        if len(popular) >= 2:
            assert popular[0]["count"] >= popular[1]["count"]
    
    def test_search_suggestions_endpoint(self, client: TestClient, db_session):
        """Test search query suggestions based on history."""
        # Arrange
        search_entries = [
            SearchHistory(id="suggest_1", user_id="user1", query="ERP implementation best practices"),
            SearchHistory(id="suggest_2", user_id="user2", query="ERP implementation guide"),
            SearchHistory(id="suggest_3", user_id="user3", query="implementation methodology"),
        ]
        
        for entry in search_entries:
            db_session.add(entry)
        db_session.commit()
        
        # Act
        response = client.get("/api/v1/search/suggestions?q=implementation")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        
        # Verify suggestions contain the query term
        for suggestion in data["suggestions"]:
            assert "implementation" in suggestion.lower()
    
    @pytest.mark.slow
    def test_search_performance_under_load(self, client: TestClient, sample_search_data):
        """Test search endpoint performance with multiple concurrent requests."""
        # Arrange
        search_payload = {
            "query": "performance test query",
            "top_k": 10
        }
        
        # Act - simulate multiple concurrent searches
        responses = []
        with patch('src.erpfts.services.search_service.SearchService.search') as mock_search:
            from src.erpfts.schemas.search import SearchResponse
            mock_search.return_value = SearchResponse(
                query="performance test query",
                total_results=0,
                results=[],
                processing_time=0.02,
                search_type="no_results"
            )
            
            for i in range(5):
                response = client.post("/api/v1/search/", json=search_payload)
                responses.append(response)
        
        # Assert
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "performance test query"
            assert data["processing_time"] < 1.0  # Should be fast
    
    def test_search_error_handling_service_unavailable(self, client: TestClient):
        """Test search error handling when service is unavailable."""
        # Arrange
        search_payload = {
            "query": "error test query",
            "top_k": 5
        }
        
        # Act - simulate service error
        with patch('src.erpfts.services.search_service.SearchService.search',
                  side_effect=Exception("Search service unavailable")):
            response = client.post("/api/v1/search/", json=search_payload)
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "error" in data["detail"].lower() or "unavailable" in data["detail"].lower()
    
    def test_search_with_special_characters(self, client: TestClient):
        """Test search handling of special characters and Unicode."""
        # Arrange
        search_payload = {
            "query": "システム実装 & 管理 (ERP) - 100%",
            "top_k": 5
        }
        
        # Act
        with patch('src.erpfts.services.search_service.SearchService.search') as mock_search:
            from src.erpfts.schemas.search import SearchResponse
            mock_search.return_value = SearchResponse(
                query="システム実装 & 管理 (ERP) - 100%",
                total_results=0,
                results=[],
                processing_time=0.04,
                search_type="no_results"
            )
            
            response = client.post("/api/v1/search/", json=search_payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "システム実装 & 管理 (ERP) - 100%"
    
    def test_search_result_highlighting(self, client: TestClient, sample_search_data):
        """Test search result highlighting functionality."""
        # Arrange
        search_payload = {
            "query": "implementation",
            "include_highlights": True,
            "top_k": 3
        }
        
        # Act
        with patch('src.erpfts.services.search_service.SearchService.search') as mock_search:
            from src.erpfts.schemas.search import SearchResponse, SearchResult
            mock_search.return_value = SearchResponse(
                query="implementation",
                total_results=1,
                results=[
                    SearchResult(
                        chunk_id="highlight_chunk",
                        document_id="highlight_doc",
                        content="ERP implementation requires careful planning and implementation.",
                        similarity_score=0.9,
                        chunk_index=0,
                        search_type="hybrid",
                        highlight_positions=[(4, 16), (52, 64)],  # "implementation" positions
                        metadata={}
                    )
                ],
                processing_time=0.08,
                search_type="hybrid"
            )
            
            response = client.post("/api/v1/search/", json=search_payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        result = data["results"][0]
        assert "highlight_positions" in result
        assert len(result["highlight_positions"]) == 2
        
        # Verify highlight positions are valid
        content = result["content"]
        for start, end in result["highlight_positions"]:
            highlighted_text = content[start:end]
            assert "implementation" in highlighted_text.lower()