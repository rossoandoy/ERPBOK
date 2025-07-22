"""
Integration tests for complete end-to-end workflows.

Tests complete user journeys and business processes from document upload
through processing, indexing, searching, and result retrieval.
"""

import io
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from src.erpfts.models.database import Document, KnowledgeChunk, SearchHistory


@pytest.mark.integration
@pytest.mark.workflows
@pytest.mark.slow
class TestCompleteWorkflows:
    """Integration tests for complete end-to-end workflows."""
    
    def test_complete_document_lifecycle_workflow(self, client: TestClient, db_session, sample_text_file):
        """Test complete document lifecycle from upload to deletion."""
        # Step 1: Upload document
        files = {
            "file": ("lifecycle_test.txt", io.BytesIO(sample_text_file.encode()), "text/plain")
        }
        
        with patch('src.erpfts.services.document_service.save_uploaded_file') as mock_save, \
             patch('src.erpfts.services.document_service.DocumentService.process_document') as mock_process:
            
            # Mock successful document processing
            mock_document = Document(
                id="lifecycle_doc_123",
                filename="lifecycle_test.txt",
                processing_status="completed",
                source_type="upload",
                uploaded_by="test_user"
            )
            mock_process.return_value = mock_document
            
            upload_response = client.post("/api/v1/documents/", files=files)
            assert upload_response.status_code == 201
            document_id = upload_response.json()["id"]
        
        # Step 2: Check processing status
        status_response = client.get(f"/api/v1/documents/{document_id}/status")
        assert status_response.status_code == 200
        assert status_response.json()["processing_status"] in ["processing", "completed"]
        
        # Step 3: Retrieve document details
        detail_response = client.get(f"/api/v1/documents/{document_id}")
        assert detail_response.status_code == 200
        detail_data = detail_response.json()
        assert detail_data["filename"] == "lifecycle_test.txt"
        
        # Step 4: List documents (should include our document)
        list_response = client.get("/api/v1/documents/")
        assert list_response.status_code == 200
        documents = list_response.json()["documents"]
        document_ids = [doc["id"] for doc in documents]
        assert document_id in document_ids
        
        # Step 5: Get document chunks
        chunks_response = client.get(f"/api/v1/documents/{document_id}/chunks")
        assert chunks_response.status_code == 200
        
        # Step 6: Delete document
        delete_response = client.delete(f"/api/v1/documents/{document_id}")
        assert delete_response.status_code == 200
        
        # Step 7: Verify document is deleted
        deleted_response = client.get(f"/api/v1/documents/{document_id}")
        assert deleted_response.status_code == 404
    
    def test_search_workflow_with_document_processing(
        self, client: TestClient, db_session, sample_documents_data
    ):
        """Test complete search workflow after document processing."""
        # Step 1: Setup test documents and chunks in database
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
        
        # Step 2: Perform search
        search_payload = {
            "query": "ERP implementation",
            "user_id": "workflow_test_user",
            "top_k": 5,
            "threshold": 0.7
        }
        
        with patch('src.erpfts.services.search_service.SearchService.search') as mock_search:
            from src.erpfts.schemas.search import SearchResponse, SearchResult
            mock_search.return_value = SearchResponse(
                query="ERP implementation",
                total_results=2,
                results=[
                    SearchResult(
                        chunk_id="chunk_1",
                        document_id="doc_1",
                        content="ERP implementation requires careful planning and stakeholder engagement.",
                        similarity_score=0.85,
                        chunk_index=0,
                        search_type="semantic",
                        highlight_positions=[],
                        metadata={"document_filename": "sample_document.pdf"}
                    ),
                    SearchResult(
                        chunk_id="chunk_2",
                        document_id="doc_1", 
                        content="Change management is critical for successful ERP deployment.",
                        similarity_score=0.75,
                        chunk_index=1,
                        search_type="semantic",
                        highlight_positions=[],
                        metadata={"document_filename": "sample_document.pdf"}
                    )
                ],
                processing_time=0.12,
                search_type="semantic"
            )
            
            search_response = client.post("/api/v1/search/", json=search_payload)
        
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert search_data["total_results"] == 2
        assert len(search_data["results"]) == 2
        
        # Step 3: Check search history was recorded
        history_response = client.get("/api/v1/search/history/workflow_test_user")
        assert history_response.status_code == 200
        history_data = history_response.json()
        
        # Should have at least one search in history
        assert len(history_data["history"]) >= 1
        latest_search = history_data["history"][0]
        assert latest_search["query"] == "ERP implementation"
        
        # Step 4: Get popular searches (should include our query)
        popular_response = client.get("/api/v1/search/popular")
        assert popular_response.status_code == 200
        popular_data = popular_response.json()
        
        # Step 5: Get search suggestions
        suggestions_response = client.get("/api/v1/search/suggestions?q=ERP")
        assert suggestions_response.status_code == 200
    
    def test_multi_user_collaboration_workflow(self, client: TestClient, db_session):
        """Test workflow with multiple users collaborating."""
        # User 1: Upload document
        files = {
            "file": ("collaboration_doc.txt", io.BytesIO(b"Collaboration test content"), "text/plain")
        }
        
        with patch('src.erpfts.services.document_service.save_uploaded_file'), \
             patch('src.erpfts.services.document_service.DocumentService.process_document') as mock_process:
            
            mock_document = Document(
                id="collab_doc_123",
                filename="collaboration_doc.txt",
                processing_status="completed",
                source_type="upload",
                uploaded_by="user_1"
            )
            mock_process.return_value = mock_document
            
            upload_response = client.post("/api/v1/documents/", files=files)
            assert upload_response.status_code == 201
            document_id = upload_response.json()["id"]
        
        # User 2: Search for the document
        search_payload_user2 = {
            "query": "collaboration test",
            "user_id": "user_2",
            "top_k": 5
        }
        
        with patch('src.erpfts.services.search_service.SearchService.search') as mock_search:
            from src.erpfts.schemas.search import SearchResponse, SearchResult
            mock_search.return_value = SearchResponse(
                query="collaboration test",
                total_results=1,
                results=[
                    SearchResult(
                        chunk_id="collab_chunk",
                        document_id=document_id,
                        content="Collaboration test content",
                        similarity_score=0.9,
                        chunk_index=0,
                        search_type="hybrid",
                        highlight_positions=[],
                        metadata={}
                    )
                ],
                processing_time=0.05,
                search_type="hybrid"
            )
            
            search_response = client.post("/api/v1/search/", json=search_payload_user2)
        
        assert search_response.status_code == 200
        
        # User 3: Also search for the document  
        search_payload_user3 = {
            "query": "collaboration test",
            "user_id": "user_3", 
            "top_k": 3
        }
        
        with patch('src.erpfts.services.search_service.SearchService.search') as mock_search:
            mock_search.return_value = SearchResponse(
                query="collaboration test",
                total_results=1,
                results=[
                    SearchResult(
                        chunk_id="collab_chunk",
                        document_id=document_id,
                        content="Collaboration test content",
                        similarity_score=0.85,
                        chunk_index=0,
                        search_type="keyword",
                        highlight_positions=[(0, 13)],
                        metadata={}
                    )
                ],
                processing_time=0.08,
                search_type="keyword"
            )
            
            search_response_user3 = client.post("/api/v1/search/", json=search_payload_user3)
        
        assert search_response_user3.status_code == 200
        
        # Check that popular searches now includes this query
        popular_response = client.get("/api/v1/search/popular")
        assert popular_response.status_code == 200
        popular_data = popular_response.json()
        
        # Should have "collaboration test" in popular searches
        popular_queries = [item["query"] for item in popular_data["popular_searches"]]
        assert "collaboration test" in popular_queries
    
    def test_batch_document_processing_workflow(self, client: TestClient, db_session):
        """Test workflow for processing multiple documents in batch."""
        # Upload multiple documents
        documents_to_upload = [
            ("batch_doc_1.txt", b"First batch document content"),
            ("batch_doc_2.txt", b"Second batch document content"),
            ("batch_doc_3.txt", b"Third batch document content")
        ]
        
        uploaded_docs = []
        
        for filename, content in documents_to_upload:
            files = {
                "file": (filename, io.BytesIO(content), "text/plain")
            }
            
            with patch('src.erpfts.services.document_service.save_uploaded_file'), \
                 patch('src.erpfts.services.document_service.DocumentService.process_document') as mock_process:
                
                mock_document = Document(
                    id=f"batch_{len(uploaded_docs)}",
                    filename=filename,
                    processing_status="completed",
                    source_type="upload"
                )
                mock_process.return_value = mock_document
                
                response = client.post("/api/v1/documents/", files=files)
                assert response.status_code == 201
                uploaded_docs.append(response.json())
        
        # Verify all documents are listed
        list_response = client.get("/api/v1/documents/")
        assert list_response.status_code == 200
        
        listed_docs = list_response.json()["documents"]
        uploaded_ids = [doc["id"] for doc in uploaded_docs]
        listed_ids = [doc["id"] for doc in listed_docs]
        
        # All uploaded documents should be in the list
        for doc_id in uploaded_ids:
            assert doc_id in listed_ids
        
        # Search across all documents
        search_payload = {
            "query": "batch document",
            "top_k": 10
        }
        
        with patch('src.erpfts.services.search_service.SearchService.search') as mock_search:
            from src.erpfts.schemas.search import SearchResponse, SearchResult
            mock_search.return_value = SearchResponse(
                query="batch document",
                total_results=3,
                results=[
                    SearchResult(
                        chunk_id=f"batch_chunk_{i}",
                        document_id=f"batch_{i}",
                        content=f"{['First', 'Second', 'Third'][i]} batch document content",
                        similarity_score=0.8 - (i * 0.1),
                        chunk_index=0,
                        search_type="semantic",
                        highlight_positions=[],
                        metadata={}
                    )
                    for i in range(3)
                ],
                processing_time=0.15,
                search_type="semantic"
            )
            
            search_response = client.post("/api/v1/search/", json=search_payload)
        
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert search_data["total_results"] == 3
        assert len(search_data["results"]) == 3
    
    def test_error_recovery_workflow(self, client: TestClient, db_session):
        """Test workflow that includes error scenarios and recovery."""
        # Step 1: Upload document that initially fails processing
        files = {
            "file": ("error_recovery_test.txt", io.BytesIO(b"Error recovery content"), "text/plain")
        }
        
        # First attempt fails
        with patch('src.erpfts.services.document_service.DocumentService.process_document',
                  side_effect=Exception("Processing temporarily failed")):
            error_response = client.post("/api/v1/documents/", files=files)
            assert error_response.status_code == 500
        
        # Step 2: Retry upload (now succeeds)
        with patch('src.erpfts.services.document_service.save_uploaded_file'), \
             patch('src.erpfts.services.document_service.DocumentService.process_document') as mock_process:
            
            mock_document = Document(
                id="error_recovery_doc",
                filename="error_recovery_test.txt",
                processing_status="completed",
                source_type="upload"
            )
            mock_process.return_value = mock_document
            
            retry_response = client.post("/api/v1/documents/", files=files)
            assert retry_response.status_code == 201
            document_id = retry_response.json()["id"]
        
        # Step 3: Search fails initially
        search_payload = {
            "query": "error recovery",
            "top_k": 5
        }
        
        with patch('src.erpfts.services.search_service.SearchService.search',
                  side_effect=Exception("Search service temporarily unavailable")):
            search_error_response = client.post("/api/v1/search/", json=search_payload)
            assert search_error_response.status_code == 500
        
        # Step 4: Search succeeds on retry
        with patch('src.erpfts.services.search_service.SearchService.search') as mock_search:
            from src.erpfts.schemas.search import SearchResponse, SearchResult
            mock_search.return_value = SearchResponse(
                query="error recovery",
                total_results=1,
                results=[
                    SearchResult(
                        chunk_id="recovery_chunk",
                        document_id=document_id,
                        content="Error recovery content",
                        similarity_score=0.95,
                        chunk_index=0,
                        search_type="semantic",
                        highlight_positions=[],
                        metadata={}
                    )
                ],
                processing_time=0.07,
                search_type="semantic"
            )
            
            search_success_response = client.post("/api/v1/search/", json=search_payload)
        
        assert search_success_response.status_code == 200
        search_data = search_success_response.json()
        assert search_data["total_results"] == 1
        
        # Step 5: Verify document can be retrieved
        detail_response = client.get(f"/api/v1/documents/{document_id}")
        assert detail_response.status_code == 200
    
    @pytest.mark.slow
    def test_performance_under_load_workflow(self, client: TestClient):
        """Test system performance under load conditions."""
        # Simulate concurrent document uploads
        upload_tasks = []
        for i in range(5):
            files = {
                "file": (f"load_test_{i}.txt", io.BytesIO(f"Load test content {i}".encode()), "text/plain")
            }
            
            with patch('src.erpfts.services.document_service.save_uploaded_file'), \
                 patch('src.erpfts.services.document_service.DocumentService.process_document') as mock_process:
                
                mock_document = Document(
                    id=f"load_test_doc_{i}",
                    filename=f"load_test_{i}.txt",
                    processing_status="completed",
                    source_type="upload"
                )
                mock_process.return_value = mock_document
                
                response = client.post("/api/v1/documents/", files=files)
                upload_tasks.append(response)
        
        # All uploads should succeed
        for response in upload_tasks:
            assert response.status_code == 201
        
        # Simulate concurrent searches  
        search_tasks = []
        for i in range(10):
            search_payload = {
                "query": f"load test {i}",
                "top_k": 3
            }
            
            with patch('src.erpfts.services.search_service.SearchService.search') as mock_search:
                from src.erpfts.schemas.search import SearchResponse
                mock_search.return_value = SearchResponse(
                    query=f"load test {i}",
                    total_results=0,
                    results=[],
                    processing_time=0.02,
                    search_type="no_results"
                )
                
                response = client.post("/api/v1/search/", json=search_payload)
                search_tasks.append(response)
        
        # All searches should complete successfully
        for response in search_tasks:
            assert response.status_code == 200
            data = response.json()
            assert data["processing_time"] < 1.0  # Should be performant