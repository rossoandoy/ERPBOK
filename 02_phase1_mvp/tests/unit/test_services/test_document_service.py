"""
Unit tests for DocumentService following TDD practices.

Tests document processing, validation, and text extraction functionality.
"""

import io
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from src.erpfts.services.document_service import DocumentService
from src.erpfts.core.exceptions import DocumentProcessingError, ValidationError
from src.erpfts.models.database import Document, KnowledgeChunk


@pytest.mark.unit
@pytest.mark.tdd
class TestDocumentService:
    """Test suite for DocumentService with TDD approach."""
    
    @pytest.fixture
    def document_service(self, db_session):
        """Create DocumentService instance for testing."""
        return DocumentService(db=db_session)
    
    @pytest.mark.red
    async def test_process_document_with_valid_pdf_returns_document_object(
        self, document_service, sample_pdf_file
    ):
        """
        RED: Test that processing a valid PDF returns a Document object.
        
        This test should initially fail as the full implementation
        doesn't exist yet.
        """
        # Arrange
        pdf_file = io.BytesIO(sample_pdf_file)
        filename = "test_document.pdf"
        user_id = "user_123"
        
        # Act
        result = await document_service.process_document(
            pdf_file, filename, user_id
        )
        
        # Assert
        assert result is not None
        assert isinstance(result, Document)
        assert result.filename == filename
        assert result.processing_status == "completed"
        assert result.uploaded_by == user_id
        assert result.source_type == "upload"
    
    @pytest.mark.red
    async def test_process_document_with_unsupported_format_raises_validation_error(
        self, document_service
    ):
        """
        RED: Test that unsupported file formats raise ValidationError.
        """
        # Arrange
        invalid_file = io.BytesIO(b"invalid content")
        filename = "test_file.xyz"
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await document_service.process_document(invalid_file, filename)
        
        assert "not supported" in str(exc_info.value).lower()
    
    @pytest.mark.red
    async def test_process_document_with_oversized_file_raises_validation_error(
        self, document_service, monkeypatch
    ):
        """
        RED: Test that files exceeding size limit raise ValidationError.
        """
        # Arrange - set small file size limit for testing
        monkeypatch.setattr("src.erpfts.services.document_service.settings.max_file_size_mb", 0.001)
        
        large_file = io.BytesIO(b"x" * 2048)  # 2KB file
        filename = "large_file.txt"
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await document_service.process_document(large_file, filename)
        
        assert "exceeds limit" in str(exc_info.value)
    
    @pytest.mark.green
    def test_validate_file_with_valid_pdf_returns_file_info(self, document_service):
        """
        GREEN: Test file validation with valid PDF file.
        
        Minimal implementation to make the test pass.
        """
        # Arrange
        pdf_content = b"%PDF-1.4\nSample PDF content"
        pdf_file = io.BytesIO(pdf_content)
        filename = "test.pdf"
        
        # Act
        result = document_service._validate_file(pdf_file, filename)
        
        # Assert
        assert result["content_type"] == "application/pdf"
        assert result["size"] > 0
        assert result["filename"] == filename
    
    @pytest.mark.green 
    def test_validate_file_with_invalid_extension_raises_error(self, document_service):
        """
        GREEN: Test file validation with invalid extension.
        """
        # Arrange
        invalid_file = io.BytesIO(b"invalid content")
        filename = "test.invalid"
        
        # Act & Assert
        with pytest.raises(ValidationError):
            document_service._validate_file(invalid_file, filename)
    
    @pytest.mark.refactor
    @patch('src.erpfts.services.document_service.PdfReader')
    async def test_extract_pdf_text_returns_cleaned_content(
        self, mock_pdf_reader, document_service, temp_storage_dir
    ):
        """
        REFACTOR: Test PDF text extraction with proper mocking.
        
        This test focuses on the quality of the text extraction.
        """
        # Arrange
        mock_reader = Mock()
        mock_page = Mock()
        mock_page.extract_text.return_value = "Sample PDF text content"
        mock_reader.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader
        
        test_file = temp_storage_dir / "test.pdf"
        test_file.write_bytes(b"fake pdf content")
        
        # Act
        result = await document_service._extract_pdf_text(test_file)
        
        # Assert
        assert result == "Sample PDF text content"
        mock_pdf_reader.assert_called_once()
    
    @pytest.mark.refactor
    async def test_extract_plain_text_with_utf8_encoding(
        self, document_service, temp_storage_dir
    ):
        """
        REFACTOR: Test plain text extraction with proper encoding handling.
        """
        # Arrange
        test_content = "This is a test document with UTF-8 content: こんにちは"
        test_file = temp_storage_dir / "test.txt"
        test_file.write_text(test_content, encoding="utf-8")
        
        # Act
        result = await document_service._extract_plain_text(test_file)
        
        # Assert
        assert result == test_content
    
    @pytest.mark.refactor
    async def test_extract_plain_text_with_encoding_fallback(
        self, document_service, temp_storage_dir
    ):
        """
        REFACTOR: Test encoding fallback for non-UTF-8 files.
        """
        # Arrange
        test_content = "This is a latin1 encoded file"
        test_file = temp_storage_dir / "test_latin1.txt"
        test_file.write_bytes(test_content.encode('latin1'))
        
        # Act
        result = await document_service._extract_plain_text(test_file)
        
        # Assert
        assert result == test_content
    
    @pytest.mark.refactor
    async def test_create_chunks_generates_proper_chunks(
        self, document_service, db_session
    ):
        """
        REFACTOR: Test chunk creation with proper database integration.
        """
        # Arrange
        document = Document(
            id="doc_test_1",
            filename="test.txt",
            processing_status="processing",
            source_type="upload"
        )
        db_session.add(document)
        db_session.flush()
        
        text_content = "This is a test document. " * 100  # Long text
        
        # Act
        await document_service._create_chunks(document, text_content)
        
        # Assert - Check chunks were created
        chunks = db_session.query(KnowledgeChunk).filter(
            KnowledgeChunk.document_id == document.id
        ).all()
        
        assert len(chunks) > 0
        assert all(chunk.document_id == document.id for chunk in chunks)
        assert all(chunk.content for chunk in chunks)  # All chunks have content
        assert all(chunk.chunk_index == idx for idx, chunk in enumerate(chunks))
    
    @pytest.mark.integration
    def test_get_document_by_id_returns_correct_document(
        self, document_service, db_session
    ):
        """
        Integration test for document retrieval.
        """
        # Arrange
        test_document = Document(
            id="doc_test_2",
            filename="test_retrieve.pdf",
            processing_status="completed",
            source_type="upload"
        )
        db_session.add(test_document)
        db_session.commit()
        
        # Act
        result = document_service.get_document("doc_test_2")
        
        # Assert
        assert result is not None
        assert result.id == "doc_test_2"
        assert result.filename == "test_retrieve.pdf"
    
    @pytest.mark.integration
    def test_get_document_nonexistent_returns_none(self, document_service):
        """
        Integration test for non-existent document retrieval.
        """
        # Act
        result = document_service.get_document("nonexistent_id")
        
        # Assert
        assert result is None
    
    @pytest.mark.integration
    def test_list_documents_with_filters(self, document_service, db_session):
        """
        Integration test for document listing with filters.
        """
        # Arrange - Create test documents
        docs = [
            Document(
                id="doc_list_1",
                filename="doc1.pdf", 
                processing_status="completed",
                source_type="upload",
                uploaded_by="user1"
            ),
            Document(
                id="doc_list_2",
                filename="doc2.txt",
                processing_status="processing", 
                source_type="upload",
                uploaded_by="user2"
            ),
            Document(
                id="doc_list_3",
                filename="doc3.pdf",
                processing_status="completed",
                source_type="upload", 
                uploaded_by="user1"
            )
        ]
        
        for doc in docs:
            db_session.add(doc)
        db_session.commit()
        
        # Act - Test user filter
        user1_docs = document_service.list_documents(user_id="user1")
        
        # Assert
        assert len(user1_docs) == 2
        assert all(doc.uploaded_by == "user1" for doc in user1_docs)
        
        # Act - Test status filter
        completed_docs = document_service.list_documents(status="completed")
        
        # Assert
        assert len(completed_docs) == 2
        assert all(doc.processing_status == "completed" for doc in completed_docs)
    
    @pytest.mark.integration
    def test_delete_document_removes_document_and_chunks(
        self, document_service, db_session
    ):
        """
        Integration test for document deletion with cascading chunk removal.
        """
        # Arrange
        document = Document(
            id="doc_delete_test",
            filename="delete_test.pdf",
            processing_status="completed",
            source_type="upload"
        )
        db_session.add(document)
        db_session.flush()
        
        # Add some chunks
        chunks = [
            KnowledgeChunk(
                id=f"chunk_{i}",
                document_id=document.id,
                content=f"Chunk {i} content",
                chunk_index=i
            )
            for i in range(3)
        ]
        
        for chunk in chunks:
            db_session.add(chunk)
        db_session.commit()
        
        # Act
        result = document_service.delete_document("doc_delete_test")
        
        # Assert
        assert result is True
        
        # Verify document is deleted
        deleted_doc = document_service.get_document("doc_delete_test")
        assert deleted_doc is None
        
        # Verify chunks are deleted
        remaining_chunks = db_session.query(KnowledgeChunk).filter(
            KnowledgeChunk.document_id == "doc_delete_test"
        ).all()
        assert len(remaining_chunks) == 0
    
    @pytest.mark.slow
    @pytest.mark.integration
    async def test_full_document_processing_workflow(
        self, document_service, sample_text_file, temp_storage_dir
    ):
        """
        Slow integration test for complete document processing workflow.
        
        This test covers the entire process from file upload to chunk creation.
        """
        # Arrange
        text_file = io.BytesIO(sample_text_file.encode('utf-8'))
        filename = "integration_test.txt"
        user_id = "integration_user"
        
        # Act
        with patch('src.erpfts.services.document_service.save_uploaded_file') as mock_save:
            mock_save.return_value = temp_storage_dir / filename
            (temp_storage_dir / filename).write_text(sample_text_file)
            
            result = await document_service.process_document(
                text_file, filename, user_id
            )
        
        # Assert - Document created
        assert result is not None
        assert result.filename == filename
        assert result.processing_status == "completed"
        assert result.uploaded_by == user_id
        
        # Assert - Chunks created
        chunks = document_service.db.query(KnowledgeChunk).filter(
            KnowledgeChunk.document_id == result.id
        ).all()
        assert len(chunks) > 0