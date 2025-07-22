"""
Integration tests for document-related API endpoints.

Tests document upload, processing, retrieval, and management endpoints
with complete workflows and error scenarios.
"""

import io
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.erpfts.models.database import Document, KnowledgeChunk
from tests.conftest import sample_pdf_file, sample_text_file


@pytest.mark.integration
@pytest.mark.api
class TestDocumentEndpoints:
    """Integration tests for document API endpoints."""
    
    def test_upload_document_success(self, client: TestClient, sample_pdf_file):
        """Test successful document upload via API."""
        # Arrange
        files = {
            "file": ("test.pdf", io.BytesIO(sample_pdf_file), "application/pdf")
        }
        
        # Act
        with patch('src.erpfts.services.document_service.save_uploaded_file'):
            response = client.post("/api/v1/documents/", files=files)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        
        assert "id" in data
        assert data["filename"] == "test.pdf"
        assert data["processing_status"] in ["processing", "completed"]
        assert "upload_timestamp" in data
    
    def test_upload_document_invalid_format(self, client: TestClient):
        """Test document upload with invalid file format."""
        # Arrange
        invalid_content = b"This is not a valid document"
        files = {
            "file": ("test.invalid", io.BytesIO(invalid_content), "application/octet-stream")
        }
        
        # Act
        response = client.post("/api/v1/documents/", files=files)
        
        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "not supported" in data["detail"].lower()
    
    def test_upload_document_oversized_file(self, client: TestClient):
        """Test document upload with file size exceeding limit."""
        # Arrange - create a large file
        large_content = b"x" * (10 * 1024 * 1024)  # 10MB file
        files = {
            "file": ("large.txt", io.BytesIO(large_content), "text/plain")
        }
        
        # Act
        with patch('src.erpfts.core.config.settings.max_file_size_mb', 5):  # Set 5MB limit
            response = client.post("/api/v1/documents/", files=files)
        
        # Assert
        assert response.status_code == 413
        data = response.json()
        assert "exceeds limit" in data["detail"]
    
    def test_upload_document_no_file_provided(self, client: TestClient):
        """Test document upload without file."""
        # Act
        response = client.post("/api/v1/documents/")
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_get_document_by_id_success(self, client: TestClient, db_session):
        """Test retrieving document by ID."""
        # Arrange
        document = Document(
            id="test_doc_123",
            filename="test_retrieve.pdf",
            processing_status="completed",
            source_type="upload",
            uploaded_by="user_123"
        )
        db_session.add(document)
        db_session.commit()
        
        # Act
        response = client.get("/api/v1/documents/test_doc_123")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == "test_doc_123"
        assert data["filename"] == "test_retrieve.pdf"
        assert data["processing_status"] == "completed"
    
    def test_get_document_not_found(self, client: TestClient):
        """Test retrieving non-existent document."""
        # Act
        response = client.get("/api/v1/documents/nonexistent_id")
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_list_documents_success(self, client: TestClient, db_session):
        """Test listing documents with pagination."""
        # Arrange - Create test documents
        documents = [
            Document(
                id=f"doc_list_{i}",
                filename=f"doc_{i}.pdf",
                processing_status="completed",
                source_type="upload",
                uploaded_by="user_123"
            )
            for i in range(5)
        ]
        
        for doc in documents:
            db_session.add(doc)
        db_session.commit()
        
        # Act
        response = client.get("/api/v1/documents/?limit=3")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert "documents" in data
        assert len(data["documents"]) <= 3
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
    
    def test_list_documents_with_filters(self, client: TestClient, db_session):
        """Test listing documents with status filter."""
        # Arrange
        completed_doc = Document(
            id="completed_doc",
            filename="completed.pdf",
            processing_status="completed",
            source_type="upload"
        )
        processing_doc = Document(
            id="processing_doc",
            filename="processing.pdf",
            processing_status="processing",
            source_type="upload"
        )
        
        db_session.add(completed_doc)
        db_session.add(processing_doc)
        db_session.commit()
        
        # Act
        response = client.get("/api/v1/documents/?status=completed")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        completed_docs = [doc for doc in data["documents"] 
                         if doc["processing_status"] == "completed"]
        assert len(completed_docs) >= 1
    
    def test_delete_document_success(self, client: TestClient, db_session):
        """Test successful document deletion."""
        # Arrange
        document = Document(
            id="delete_test_doc",
            filename="to_delete.pdf",
            processing_status="completed",
            source_type="upload"
        )
        db_session.add(document)
        db_session.commit()
        
        # Act
        response = client.delete("/api/v1/documents/delete_test_doc")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deleted" in data["message"].lower()
    
    def test_delete_document_not_found(self, client: TestClient):
        """Test deleting non-existent document."""
        # Act
        response = client.delete("/api/v1/documents/nonexistent_delete")
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_get_document_processing_status(self, client: TestClient, db_session):
        """Test retrieving document processing status."""
        # Arrange
        document = Document(
            id="status_test_doc",
            filename="status_test.pdf",
            processing_status="processing",
            source_type="upload"
        )
        db_session.add(document)
        db_session.commit()
        
        # Act
        response = client.get("/api/v1/documents/status_test_doc/status")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["document_id"] == "status_test_doc"
        assert data["processing_status"] == "processing"
        assert "last_updated" in data
    
    @pytest.mark.slow
    def test_document_upload_and_processing_workflow(
        self, client: TestClient, db_session, sample_text_file
    ):
        """Test complete document upload and processing workflow."""
        # Arrange
        files = {
            "file": ("workflow_test.txt", io.BytesIO(sample_text_file.encode()), "text/plain")
        }
        
        # Act 1: Upload document
        with patch('src.erpfts.services.document_service.save_uploaded_file'), \
             patch('src.erpfts.services.document_service.DocumentService.process_document') as mock_process:
            
            # Mock successful processing
            mock_document = Document(
                id="workflow_test_id",
                filename="workflow_test.txt",
                processing_status="completed",
                source_type="upload"
            )
            mock_process.return_value = mock_document
            
            upload_response = client.post("/api/v1/documents/", files=files)
        
        # Assert upload
        assert upload_response.status_code == 201
        upload_data = upload_response.json()
        document_id = upload_data["id"]
        
        # Act 2: Check processing status
        status_response = client.get(f"/api/v1/documents/{document_id}/status")
        
        # Assert status
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["processing_status"] in ["processing", "completed"]
        
        # Act 3: Retrieve document details
        detail_response = client.get(f"/api/v1/documents/{document_id}")
        
        # Assert details
        assert detail_response.status_code == 200
        detail_data = detail_response.json()
        assert detail_data["filename"] == "workflow_test.txt"
    
    def test_document_chunks_endpoint(self, client: TestClient, db_session):
        """Test retrieving document chunks."""
        # Arrange
        document = Document(
            id="chunks_test_doc",
            filename="chunks_test.txt",
            processing_status="completed",
            source_type="upload"
        )
        db_session.add(document)
        db_session.flush()
        
        # Add chunks
        chunks = [
            KnowledgeChunk(
                id=f"chunk_{i}",
                document_id=document.id,
                content=f"Chunk {i} content for testing",
                chunk_index=i,
                start_position=i * 50,
                end_position=(i + 1) * 50 - 1
            )
            for i in range(3)
        ]
        
        for chunk in chunks:
            db_session.add(chunk)
        db_session.commit()
        
        # Act
        response = client.get(f"/api/v1/documents/{document.id}/chunks")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert "chunks" in data
        assert len(data["chunks"]) == 3
        assert "total_chunks" in data
        
        # Verify chunk data
        for i, chunk_data in enumerate(data["chunks"]):
            assert chunk_data["chunk_index"] == i
            assert f"Chunk {i} content" in chunk_data["content"]
    
    def test_document_error_handling_network_issues(self, client: TestClient):
        """Test API error handling for network/timeout issues."""
        # Arrange
        files = {
            "file": ("timeout_test.pdf", io.BytesIO(b"test content"), "application/pdf")
        }
        
        # Act - simulate timeout during processing
        with patch('src.erpfts.services.document_service.DocumentService.process_document',
                  side_effect=TimeoutError("Processing timeout")):
            response = client.post("/api/v1/documents/", files=files)
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "timeout" in data["detail"].lower()
    
    def test_document_concurrent_upload_handling(self, client: TestClient):
        """Test handling of concurrent document uploads."""
        # Arrange
        files1 = {
            "file": ("concurrent1.txt", io.BytesIO(b"Content 1"), "text/plain")
        }
        files2 = {
            "file": ("concurrent2.txt", io.BytesIO(b"Content 2"), "text/plain")
        }
        
        # Act - simulate concurrent uploads
        with patch('src.erpfts.services.document_service.save_uploaded_file'):
            response1 = client.post("/api/v1/documents/", files=files1)
            response2 = client.post("/api/v1/documents/", files=files2)
        
        # Assert
        assert response1.status_code == 201
        assert response2.status_code == 201
        
        # Verify different document IDs
        data1 = response1.json()
        data2 = response2.json()
        assert data1["id"] != data2["id"]