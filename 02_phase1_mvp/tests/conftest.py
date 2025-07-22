"""
Pytest configuration and fixtures for ERPFTS Phase1 MVP tests.

Provides common test fixtures, database setup, and testing utilities
following TDD best practices.
"""

import os
import tempfile
from pathlib import Path
from typing import Generator, Dict, Any
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Set test environment before importing modules
os.environ["ERPFTS_DEBUG"] = "true"
os.environ["ERPFTS_LOG_LEVEL"] = "DEBUG"

from src.erpfts.core.config import settings
from src.erpfts.models.database import Base
from src.erpfts.db.session import get_db_session
from src.erpfts.api.main import app


@pytest.fixture(scope="session")
def temp_db_path() -> Generator[str, None, None]:
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture(scope="session")
def test_engine(temp_db_path: str):
    """Create a test database engine."""
    database_url = f"sqlite:///{temp_db_path}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        echo=False  # Set to True for SQL debugging
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    return engine


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a database session for each test."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> TestClient:
    """Create a test client with dependency overrides."""
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def temp_storage_dir() -> Generator[Path, None, None]:
    """Create temporary storage directory for file tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_path = Path(temp_dir)
        
        # Create subdirectories
        (storage_path / "uploads").mkdir()
        (storage_path / "cache").mkdir()
        (storage_path / "chroma").mkdir()
        
        yield storage_path


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for testing."""
    mock_service = Mock()
    
    # Mock successful embedding generation
    mock_service.generate_embeddings.return_value = [
        [0.1, 0.2, 0.3, 0.4] * 256  # 1024-dim vector
    ]
    
    # Mock successful chunk processing
    mock_service.process_chunks.return_value = 5
    
    # Mock similarity search
    mock_service.search_similar.return_value = [
        {
            "id": "chunk_1",
            "content": "Sample search result",
            "metadata": {"document_id": "doc_1", "chunk_index": 0},
            "similarity": 0.85,
            "distance": 0.15
        }
    ]
    
    return mock_service


@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for testing."""
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Hello, World!) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000060 00000 n 
0000000120 00000 n 
0000000200 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
290
%%EOF"""
    
    return pdf_content


@pytest.fixture
def sample_text_file():
    """Create a sample text file for testing."""
    return "This is a sample text file for testing document processing."


@pytest.fixture
def sample_documents_data() -> Dict[str, Any]:
    """Sample document data for testing."""
    return {
        "documents": [
            {
                "id": "doc_1",
                "filename": "sample_document.pdf",
                "content": "This document contains information about ERP implementation best practices. It covers project management, change management, and technical considerations.",
                "language": "english",
                "source_type": "upload"
            },
            {
                "id": "doc_2", 
                "filename": "technical_guide.txt",
                "content": "Technical implementation guide for RAG systems. Covers vector databases, embedding models, and search algorithms.",
                "language": "english",
                "source_type": "upload"
            },
            {
                "id": "doc_3",
                "filename": "japanese_content.txt", 
                "content": "これは日本語のサンプル文書です。ERPシステムの導入に関する情報が含まれています。",
                "language": "japanese",
                "source_type": "upload"
            }
        ],
        "chunks": [
            {
                "id": "chunk_1",
                "document_id": "doc_1",
                "content": "ERP implementation requires careful planning and stakeholder engagement.",
                "chunk_index": 0,
                "start_position": 0,
                "end_position": 71
            },
            {
                "id": "chunk_2", 
                "document_id": "doc_1",
                "content": "Change management is critical for successful ERP deployment.",
                "chunk_index": 1,
                "start_position": 72,
                "end_position": 130
            },
            {
                "id": "chunk_3",
                "document_id": "doc_2",
                "content": "Vector databases enable semantic search capabilities.",
                "chunk_index": 0,
                "start_position": 0,
                "end_position": 50
            }
        ]
    }


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, temp_storage_dir):
    """Setup test environment variables and paths."""
    # Override settings for testing
    monkeypatch.setenv("ERPFTS_STORAGE_ROOT", str(temp_storage_dir))
    monkeypatch.setenv("ERPFTS_CHROMA_PERSIST_DIRECTORY", str(temp_storage_dir / "chroma"))
    monkeypatch.setenv("ERPFTS_DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("ERPFTS_DEBUG", "true")
    
    # Create required directories
    (temp_storage_dir / "uploads").mkdir(exist_ok=True)
    (temp_storage_dir / "cache").mkdir(exist_ok=True)
    (temp_storage_dir / "logs").mkdir(exist_ok=True)


@pytest.fixture
def mock_chromadb_client():
    """Mock ChromaDB client for testing."""
    mock_client = Mock()
    mock_collection = Mock()
    
    # Mock collection operations
    mock_collection.count.return_value = 10
    mock_collection.add.return_value = None
    mock_collection.query.return_value = {
        "ids": [["chunk_1", "chunk_2"]],
        "distances": [[0.15, 0.25]], 
        "documents": [["Sample content 1", "Sample content 2"]],
        "metadatas": [[{"document_id": "doc_1"}, {"document_id": "doc_2"}]]
    }
    mock_collection.delete.return_value = None
    
    mock_client.get_or_create_collection.return_value = mock_collection
    mock_client.PersistentClient.return_value = mock_client
    
    return mock_client


# Test markers for TDD phases
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "tdd: mark test as part of TDD workflow"
    )
    config.addinivalue_line(
        "markers", "red: mark test in RED phase (should fail initially)"
    )
    config.addinivalue_line(
        "markers", "green: mark test in GREEN phase (minimal implementation)"
    )
    config.addinivalue_line(
        "markers", "refactor: mark test in REFACTOR phase (quality improvement)"
    )


# Test data cleanup
@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Clean up test data after each test."""
    yield
    # Add any cleanup logic here if needed