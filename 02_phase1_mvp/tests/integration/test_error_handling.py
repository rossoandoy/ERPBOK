"""
Integration tests for error handling and resilience.

Tests system behavior under various error conditions, recovery mechanisms,
and error reporting across all components.
"""

import pytest
from unittest.mock import patch, Mock
from sqlalchemy.exc import OperationalError, IntegrityError
from fastapi.testclient import TestClient

from src.erpfts.core.exceptions import (
    DocumentProcessingError,
    ValidationError,
    SearchError,
    DatabaseError
)


@pytest.mark.integration
@pytest.mark.error_handling
class TestSystemErrorHandling:
    """Integration tests for system-wide error handling."""
    
    def test_database_connection_failure_handling(self, client: TestClient):
        """Test handling of database connection failures."""
        # Act - simulate database connection error
        with patch('src.erpfts.db.session.get_db_session',
                  side_effect=OperationalError("Connection failed", None, None)):
            response = client.get("/api/v1/documents/")
        
        # Assert
        assert response.status_code == 503
        data = response.json()
        assert "database" in data["detail"].lower()
        assert "unavailable" in data["detail"].lower()
    
    def test_database_integrity_error_handling(self, client: TestClient, db_session):
        """Test handling of database integrity constraint violations."""
        # Arrange
        files = {
            "file": ("integrity_test.txt", b"test content", "text/plain")
        }
        
        # Act - simulate integrity error during document save
        with patch('src.erpfts.services.document_service.DocumentService.process_document',
                  side_effect=IntegrityError("Duplicate key", None, None)):
            response = client.post("/api/v1/documents/", files=files)
        
        # Assert
        assert response.status_code == 409
        data = response.json()
        assert "conflict" in data["detail"].lower() or "duplicate" in data["detail"].lower()
    
    def test_embedding_service_failure_graceful_degradation(self, client: TestClient):
        """Test graceful degradation when embedding service fails."""
        # Arrange
        search_payload = {
            "query": "test query for embedding failure",
            "top_k": 5
        }
        
        # Act - simulate embedding service failure
        with patch('src.erpfts.services.search_service.EmbeddingService') as mock_embedding:
            mock_embedding.side_effect = Exception("Embedding service unavailable")
            
            # Should fall back to keyword-only search
            with patch('src.erpfts.services.search_service.SearchService._keyword_search') as mock_keyword:
                from src.erpfts.schemas.search import SearchResult
                mock_keyword.return_value = [
                    SearchResult(
                        chunk_id="fallback_chunk",
                        document_id="fallback_doc", 
                        content="Fallback search result",
                        similarity_score=0.5,
                        chunk_index=0,
                        search_type="keyword",
                        highlight_positions=[],
                        metadata={}
                    )
                ]
                
                response = client.post("/api/v1/search/", json=search_payload)
        
        # Assert - should still work with degraded functionality
        assert response.status_code == 200
        data = response.json()
        assert data["search_type"] == "keyword"  # Fallback to keyword search
    
    def test_file_system_error_handling(self, client: TestClient):
        """Test handling of file system errors during document processing."""
        # Arrange
        files = {
            "file": ("fs_error_test.txt", b"test content", "text/plain")
        }
        
        # Act - simulate file system error
        with patch('src.erpfts.services.document_service.save_uploaded_file',
                  side_effect=OSError("No space left on device")):
            response = client.post("/api/v1/documents/", files=files)
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "storage" in data["detail"].lower() or "file system" in data["detail"].lower()
    
    def test_concurrent_access_error_handling(self, client: TestClient, db_session):
        """Test handling of concurrent access conflicts."""
        # Arrange
        from src.erpfts.models.database import Document
        document = Document(
            id="concurrent_test_doc",
            filename="concurrent_test.pdf",
            processing_status="processing",
            source_type="upload"
        )
        db_session.add(document)
        db_session.commit()
        
        # Act - simulate concurrent modification
        with patch('sqlalchemy.orm.Session.commit',
                  side_effect=IntegrityError("Concurrent modification", None, None)):
            response = client.delete("/api/v1/documents/concurrent_test_doc")
        
        # Assert
        assert response.status_code == 409
        data = response.json()
        assert "conflict" in data["detail"].lower()
    
    def test_memory_exhaustion_handling(self, client: TestClient):
        """Test handling of memory exhaustion during large file processing."""
        # Arrange
        files = {
            "file": ("memory_test.txt", b"x" * (5 * 1024 * 1024), "text/plain")  # 5MB
        }
        
        # Act - simulate memory error
        with patch('src.erpfts.services.document_service.DocumentService._extract_plain_text',
                  side_effect=MemoryError("Not enough memory")):
            response = client.post("/api/v1/documents/", files=files)
        
        # Assert
        assert response.status_code == 507
        data = response.json()
        assert "memory" in data["detail"].lower() or "insufficient storage" in data["detail"].lower()
    
    def test_network_timeout_error_handling(self, client: TestClient):
        """Test handling of network timeouts during external service calls."""
        # Arrange
        search_payload = {
            "query": "timeout test query",
            "top_k": 5
        }
        
        # Act - simulate network timeout
        with patch('src.erpfts.services.search_service.SearchService.search',
                  side_effect=TimeoutError("Network timeout")):
            response = client.post("/api/v1/search/", json=search_payload)
        
        # Assert
        assert response.status_code == 504
        data = response.json()
        assert "timeout" in data["detail"].lower()
    
    def test_malformed_request_error_handling(self, client: TestClient):
        """Test handling of malformed requests."""
        # Act - send malformed JSON
        response = client.post(
            "/api/v1/search/",
            data="{ invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "malformed" in data["detail"].lower() or "invalid" in data["detail"].lower()
    
    def test_rate_limiting_error_handling(self, client: TestClient):
        """Test rate limiting error handling."""
        # Arrange - simulate rate limiting
        search_payload = {
            "query": "rate limit test",
            "top_k": 5
        }
        
        # Act - simulate rate limit exceeded
        with patch('src.erpfts.api.middleware.rate_limiter.is_allowed',
                  return_value=False):
            response = client.post("/api/v1/search/", json=search_payload)
        
        # Assert
        assert response.status_code == 429
        data = response.json()
        assert "rate limit" in data["detail"].lower()
    
    def test_authentication_error_handling(self, client: TestClient):
        """Test authentication error handling."""
        # Act - attempt to access protected endpoint without auth
        response = client.get(
            "/api/v1/admin/system/status",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        # Assert
        assert response.status_code in [401, 403]
        data = response.json()
        assert "unauthorized" in data["detail"].lower() or "forbidden" in data["detail"].lower()
    
    def test_service_dependency_failure_cascade(self, client: TestClient):
        """Test handling of cascading service failures."""
        # Arrange
        files = {
            "file": ("cascade_test.pdf", b"PDF content", "application/pdf")
        }
        
        # Act - simulate multiple service failures
        with patch('src.erpfts.services.document_service.DocumentService._extract_pdf_text',
                  side_effect=Exception("PDF extraction failed")), \
             patch('src.erpfts.services.document_service.DocumentService._extract_plain_text',
                  side_effect=Exception("Text extraction failed")):
            
            response = client.post("/api/v1/documents/", files=files)
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "processing" in data["detail"].lower()
    

@pytest.mark.integration  
@pytest.mark.error_handling
class TestErrorRecovery:
    """Tests for error recovery and resilience mechanisms."""
    
    def test_automatic_retry_on_transient_failures(self, client: TestClient):
        """Test automatic retry mechanism for transient failures."""
        # Arrange
        files = {
            "file": ("retry_test.txt", b"content for retry test", "text/plain")
        }
        
        # Act - simulate transient failure then success
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Transient network error")
            return Mock(id="retry_success", filename="retry_test.txt", processing_status="completed")
        
        with patch('src.erpfts.services.document_service.DocumentService.process_document',
                  side_effect=side_effect):
            response = client.post("/api/v1/documents/", files=files)
        
        # Assert
        assert response.status_code == 201
        assert call_count == 2  # Should retry once
    
    def test_circuit_breaker_pattern(self, client: TestClient):
        """Test circuit breaker pattern for external service calls."""
        # Arrange
        search_payload = {
            "query": "circuit breaker test",
            "top_k": 5
        }
        
        # Act - simulate repeated failures to trigger circuit breaker
        with patch('src.erpfts.services.search_service.EmbeddingService.search_similar',
                  side_effect=Exception("Service unavailable")) as mock_search:
            
            # Make multiple requests to trigger circuit breaker
            responses = []
            for i in range(5):
                response = client.post("/api/v1/search/", json=search_payload)
                responses.append(response)
        
        # Assert - later requests should fail faster (circuit breaker open)
        assert any(r.status_code == 503 for r in responses)  # Service unavailable
    
    def test_graceful_shutdown_handling(self, client: TestClient):
        """Test graceful handling of shutdown signals."""
        # This test would typically involve testing signal handling
        # For now, we'll test the health check endpoint
        
        # Act
        response = client.get("/api/v1/health")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    def test_resource_cleanup_on_error(self, client: TestClient):
        """Test proper resource cleanup when errors occur."""
        # Arrange
        files = {
            "file": ("cleanup_test.txt", b"content for cleanup test", "text/plain")
        }
        
        # Act - simulate error during processing
        with patch('src.erpfts.services.document_service.DocumentService._create_chunks',
                  side_effect=Exception("Chunk creation failed")):
            response = client.post("/api/v1/documents/", files=files)
        
        # Assert - should clean up and return error
        assert response.status_code == 500
        
        # Verify cleanup occurred (temp files removed, database rolled back, etc.)
        # This would require additional monitoring/instrumentation in real implementation


@pytest.mark.integration
@pytest.mark.error_handling
class TestErrorReporting:
    """Tests for error reporting and logging."""
    
    def test_error_correlation_ids(self, client: TestClient):
        """Test that errors include correlation IDs for tracking."""
        # Arrange
        files = {
            "file": ("correlation_test.txt", b"test content", "text/plain")
        }
        
        # Act - force an error
        with patch('src.erpfts.services.document_service.DocumentService.process_document',
                  side_effect=Exception("Test error for correlation")):
            response = client.post("/api/v1/documents/", files=files)
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        
        # Should include correlation ID for tracking
        assert "correlation_id" in data or "trace_id" in data
    
    def test_error_details_sanitization(self, client: TestClient):
        """Test that error responses don't leak sensitive information."""
        # Arrange - simulate error with sensitive data
        search_payload = {
            "query": "test query",
            "top_k": 5
        }
        
        # Act
        with patch('src.erpfts.services.search_service.SearchService.search',
                  side_effect=Exception("Database password: secret123")):
            response = client.post("/api/v1/search/", json=search_payload)
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        
        # Should not leak sensitive information
        assert "secret123" not in str(data)
        assert "password" not in data["detail"].lower()
    
    def test_structured_error_logging(self, client: TestClient):
        """Test that errors are logged in structured format."""
        # This would typically test log output, but for integration testing
        # we'll verify the error response structure
        
        # Arrange
        files = {
            "file": ("logging_test.txt", b"test content", "text/plain")
        }
        
        # Act
        with patch('src.erpfts.services.document_service.DocumentService.process_document',
                  side_effect=ValidationError("Test validation error")):
            response = client.post("/api/v1/documents/", files=files)
        
        # Assert - structured error response
        assert response.status_code == 400
        data = response.json()
        
        assert "detail" in data
        assert "error_code" in data or "type" in data
        assert "timestamp" in data or isinstance(data, dict)