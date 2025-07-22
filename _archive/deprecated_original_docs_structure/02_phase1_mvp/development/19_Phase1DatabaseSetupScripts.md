# ERP知識RAGシステム - Phase1 データベース設計・初期化スクリプト

---
doc_type: "phase1_database_setup"
complexity: "high"
estimated_effort: "データベース基盤実装"
prerequisites: ["05_DataModelDesign.md", "17_Phase1TechnicalSpecification.md", "18_Phase1DevelopmentEnvironmentGuide.md"]
implementation_priority: "critical"
ai_assistance_level: "full_automation_possible"
version: "1.0.0"
author: "Claude Code"
created_date: "2025-01-21"
status: "approved"
approval_authority: "Backend Engineer"
---

## 📋 Phase1 データベース設計概要

### データベース構成・目的
本文書は「ERP知識RAGシステム（ERPFTS）」Phase1 MVP用のデータベーススキーマ、初期化スクリプト、セットアップ手順を定義する。SQLite（開発・テスト用）とChroma DB（ベクトル検索用）の統合的なデータ基盤を構築し、Week 1の基盤構築タスクを支援する。

### Phase1 データベース方針
```yaml
実用性重視:
  - SQLite: 軽量・高速・ローカル開発最適化
  - Chroma DB: ベクトル検索・永続化・メタデータ管理
  - Redis: セッション・キャッシュ（オプション）

拡張性考慮:
  - PostgreSQL移行準備（SQLAlchemy ORM使用）
  - 大量データ対応インデックス設計
  - パーティショニング準備
  - バックアップ・復旧戦略

整合性保証:
  - 外部キー制約・チェック制約
  - トランザクション管理
  - データ品質バリデーション
  - 重複検出・除去機能
```

## 🗄️ SQLite スキーマ定義・DDL

### メインテーブル作成 DDL
```sql
-- ===============================================
-- Phase1 MVP Database Schema (SQLite)
-- Generated: 2025-01-21
-- Purpose: ERP Knowledge RAG System Phase1
-- ===============================================

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 1000000;
PRAGMA temp_store = memory;

-- ===============================================
-- 1. Users Table (ユーザー管理)
-- ===============================================
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    email TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('guest', 'viewer', 'editor', 'admin')),
    is_active BOOLEAN DEFAULT 1,
    last_login TIMESTAMP,
    preferences TEXT DEFAULT '{}' CHECK (json_valid(preferences)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);
CREATE INDEX IF NOT EXISTS idx_users_active ON users (is_active);
CREATE INDEX IF NOT EXISTS idx_users_last_login ON users (last_login);

-- ===============================================
-- 2. Sources Table (データソース管理)
-- ===============================================
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    name TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('pdf', 'rss', 'web', 'github', 'api', 'manual')),
    base_url TEXT,
    rss_feed TEXT,
    access_config TEXT DEFAULT '{}' CHECK (json_valid(access_config)),
    check_interval INTEGER DEFAULT 3600 CHECK (check_interval > 0),
    last_checked TIMESTAMP,
    last_success_check TIMESTAMP,
    consecutive_failures INTEGER DEFAULT 0 CHECK (consecutive_failures >= 0),
    is_active BOOLEAN DEFAULT 1,
    quality_weight REAL DEFAULT 1.0 CHECK (quality_weight >= 0 AND quality_weight <= 5.0),
    metadata_json TEXT DEFAULT '{}' CHECK (json_valid(metadata_json)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sources indexes
CREATE INDEX IF NOT EXISTS idx_sources_type ON sources (source_type);
CREATE INDEX IF NOT EXISTS idx_sources_active ON sources (is_active);
CREATE INDEX IF NOT EXISTS idx_sources_last_checked ON sources (last_checked);
CREATE INDEX IF NOT EXISTS idx_sources_failures ON sources (consecutive_failures);
CREATE INDEX IF NOT EXISTS idx_sources_quality ON sources (quality_weight);

-- ===============================================
-- 3. Documents Table (文書管理)
-- ===============================================
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    author TEXT,
    published_date DATE,
    last_modified TIMESTAMP,
    file_path TEXT,
    content_hash TEXT UNIQUE, -- SHA-256 hash
    language TEXT DEFAULT 'ja' CHECK (language IN ('ja', 'en', 'auto')),
    document_type TEXT DEFAULT 'article',
    word_count INTEGER CHECK (word_count >= 0),
    page_count INTEGER CHECK (page_count >= 0),
    metadata_json TEXT DEFAULT '{}' CHECK (json_valid(metadata_json)),
    quality_score REAL DEFAULT 0.0 CHECK (quality_score >= 0 AND quality_score <= 5.0),
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'skipped')),
    processing_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Documents indexes
CREATE INDEX IF NOT EXISTS idx_documents_source ON documents (source_id);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents (content_hash);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents (document_type);
CREATE INDEX IF NOT EXISTS idx_documents_quality ON documents (quality_score);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (processing_status);
CREATE INDEX IF NOT EXISTS idx_documents_published ON documents (published_date);
CREATE INDEX IF NOT EXISTS idx_documents_language ON documents (language);
CREATE INDEX IF NOT EXISTS idx_documents_updated ON documents (updated_at);

-- Full-text search index for documents
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    title, author, content=documents, content_rowid=rowid
);

-- ===============================================
-- 4. Chunks Table (チャンク管理)
-- ===============================================
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL,
    content_hash TEXT, -- SHA-256 of content for deduplication
    token_count INTEGER CHECK (token_count > 0),
    char_count INTEGER CHECK (char_count > 0),
    page_number INTEGER CHECK (page_number > 0),
    section_title TEXT,
    section_level INTEGER CHECK (section_level >= 0),
    quality_score REAL DEFAULT 0.0 CHECK (quality_score >= 0 AND quality_score <= 5.0),
    metadata_json TEXT DEFAULT '{}' CHECK (json_valid(metadata_json)),
    embedding_id TEXT, -- Reference to vector database
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(document_id, chunk_index)
);

-- Chunks indexes  
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_page ON chunks (page_number);
CREATE INDEX IF NOT EXISTS idx_chunks_quality ON chunks (quality_score);
CREATE INDEX IF NOT EXISTS idx_chunks_section ON chunks (section_title);
CREATE INDEX IF NOT EXISTS idx_chunks_hash ON chunks (content_hash);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks (embedding_id);
CREATE INDEX IF NOT EXISTS idx_chunks_tokens ON chunks (token_count);

-- Full-text search index for chunks
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    content, section_title, content=chunks, content_rowid=rowid
);

-- ===============================================
-- 5. Embeddings Table (埋め込みベクトル管理)
-- ===============================================
CREATE TABLE IF NOT EXISTS embeddings (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    chunk_id TEXT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    vector_dimension INTEGER NOT NULL CHECK (vector_dimension > 0),
    embedding_hash TEXT, -- For deduplication
    model_parameters TEXT DEFAULT '{}' CHECK (json_valid(model_parameters)),
    generation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(chunk_id, model_name, model_version)
);

-- Embeddings indexes
CREATE INDEX IF NOT EXISTS idx_embeddings_chunk ON embeddings (chunk_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings (model_name, model_version);
CREATE INDEX IF NOT EXISTS idx_embeddings_hash ON embeddings (embedding_hash);
CREATE INDEX IF NOT EXISTS idx_embeddings_dimension ON embeddings (vector_dimension);

-- ===============================================
-- 6. Search_Logs Table (検索ログ管理)
-- ===============================================
CREATE TABLE IF NOT EXISTS search_logs (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    session_id TEXT,
    query_text TEXT NOT NULL,
    query_type TEXT DEFAULT 'semantic' CHECK (query_type IN ('semantic', 'keyword', 'hybrid')),
    filters_applied TEXT DEFAULT '{}' CHECK (json_valid(filters_applied)),
    result_count INTEGER DEFAULT 0 CHECK (result_count >= 0),
    response_time_ms INTEGER CHECK (response_time_ms >= 0),
    clicked_results TEXT DEFAULT '[]' CHECK (json_valid(clicked_results)), -- JSON array of chunk IDs
    satisfaction_rating INTEGER CHECK (satisfaction_rating >= 1 AND satisfaction_rating <= 5),
    search_metadata TEXT DEFAULT '{}' CHECK (json_valid(search_metadata)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Search_logs indexes
CREATE INDEX IF NOT EXISTS idx_search_logs_user ON search_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_search_logs_session ON search_logs (session_id);
CREATE INDEX IF NOT EXISTS idx_search_logs_time ON search_logs (created_at);
CREATE INDEX IF NOT EXISTS idx_search_logs_query_type ON search_logs (query_type);
CREATE INDEX IF NOT EXISTS idx_search_logs_rating ON search_logs (satisfaction_rating);

-- Full-text search for query analysis
CREATE VIRTUAL TABLE IF NOT EXISTS search_logs_fts USING fts5(
    query_text, content=search_logs, content_rowid=rowid
);

-- ===============================================
-- 7. Quality_Scores Table (品質評価管理)
-- ===============================================
CREATE TABLE IF NOT EXISTS quality_scores (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    entity_type TEXT NOT NULL CHECK (entity_type IN ('source', 'document', 'chunk')),
    entity_id TEXT NOT NULL,
    score_type TEXT NOT NULL, -- authority_score, accuracy_score, timeliness_score, etc.
    score_value REAL NOT NULL CHECK (score_value >= 0),
    max_possible_score REAL DEFAULT 5.0 CHECK (max_possible_score > 0),
    evaluator TEXT, -- human, auto, ai
    evaluation_method TEXT,
    evaluation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    metadata TEXT DEFAULT '{}' CHECK (json_valid(metadata)),
    is_current BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Quality_scores indexes
CREATE INDEX IF NOT EXISTS idx_quality_entity ON quality_scores (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_quality_type ON quality_scores (score_type);
CREATE INDEX IF NOT EXISTS idx_quality_current ON quality_scores (is_current);
CREATE INDEX IF NOT EXISTS idx_quality_date ON quality_scores (evaluation_date);
CREATE INDEX IF NOT EXISTS idx_quality_value ON quality_scores (score_value);

-- ===============================================
-- 8. Settings Table (システム設定管理)
-- ===============================================
CREATE TABLE IF NOT EXISTS settings (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    key TEXT UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    is_system BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Settings indexes
CREATE INDEX IF NOT EXISTS idx_settings_key ON settings (key);
CREATE INDEX IF NOT EXISTS idx_settings_system ON settings (is_system);

-- ===============================================
-- Triggers for updated_at timestamps
-- ===============================================
CREATE TRIGGER IF NOT EXISTS users_updated_at
    AFTER UPDATE ON users
    FOR EACH ROW
    BEGIN
        UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS sources_updated_at
    AFTER UPDATE ON sources
    FOR EACH ROW
    BEGIN
        UPDATE sources SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS documents_updated_at
    AFTER UPDATE ON documents
    FOR EACH ROW
    BEGIN
        UPDATE documents SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS chunks_updated_at
    AFTER UPDATE ON chunks
    FOR EACH ROW
    BEGIN
        UPDATE chunks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS embeddings_updated_at
    AFTER UPDATE ON embeddings
    FOR EACH ROW
    BEGIN
        UPDATE embeddings SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS settings_updated_at
    AFTER UPDATE ON settings
    FOR EACH ROW
    BEGIN
        UPDATE settings SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- ===============================================
-- FTS Triggers for maintaining full-text search
-- ===============================================
CREATE TRIGGER IF NOT EXISTS documents_fts_insert
    AFTER INSERT ON documents
    BEGIN
        INSERT INTO documents_fts(rowid, title, author) VALUES (NEW.rowid, NEW.title, NEW.author);
    END;

CREATE TRIGGER IF NOT EXISTS documents_fts_delete
    AFTER DELETE ON documents
    BEGIN
        DELETE FROM documents_fts WHERE rowid = OLD.rowid;
    END;

CREATE TRIGGER IF NOT EXISTS documents_fts_update
    AFTER UPDATE ON documents
    BEGIN
        DELETE FROM documents_fts WHERE rowid = OLD.rowid;
        INSERT INTO documents_fts(rowid, title, author) VALUES (NEW.rowid, NEW.title, NEW.author);
    END;

CREATE TRIGGER IF NOT EXISTS chunks_fts_insert
    AFTER INSERT ON chunks
    BEGIN
        INSERT INTO chunks_fts(rowid, content, section_title) VALUES (NEW.rowid, NEW.content, NEW.section_title);
    END;

CREATE TRIGGER IF NOT EXISTS chunks_fts_delete
    AFTER DELETE ON chunks
    BEGIN
        DELETE FROM chunks_fts WHERE rowid = OLD.rowid;
    END;

CREATE TRIGGER IF NOT EXISTS chunks_fts_update
    AFTER UPDATE ON chunks
    BEGIN
        DELETE FROM chunks_fts WHERE rowid = OLD.rowid;
        INSERT INTO chunks_fts(rowid, content, section_title) VALUES (NEW.rowid, NEW.content, NEW.section_title);
    END;
```

## 🐍 データベース初期化スクリプト

### SQLite セットアップスクリプト
```python
#!/usr/bin/env python3
"""
Phase1 SQLite Database Setup Script
Purpose: Initialize SQLite database with complete schema and sample data
Usage: python scripts/init_sqlite_database.py
"""

import sqlite3
import logging
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "erpfts.db"
SCHEMA_PATH = PROJECT_ROOT / "scripts" / "schema.sql"

class SQLiteSetup:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
    
    def connect(self):
        """データベース接続"""
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row
        
        # Enable foreign keys and optimize settings
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL") 
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.conn.execute("PRAGMA cache_size = 1000000")
        
        logger.info(f"Connected to SQLite database: {self.db_path}")
    
    def execute_schema(self, schema_content: str):
        """スキーマ実行"""
        try:
            # Split schema into individual statements
            statements = [stmt.strip() for stmt in schema_content.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement:
                    self.conn.execute(statement)
            
            self.conn.commit()
            logger.info("Schema executed successfully")
            
        except sqlite3.Error as e:
            logger.error(f"Schema execution failed: {e}")
            raise
    
    def insert_initial_data(self):
        """初期データ挿入"""
        logger.info("Inserting initial data...")
        
        # Insert system settings
        settings_data = [
            ("system_version", "1.0.0", "System version", True),
            ("default_language", "ja", "Default language for new documents", True),
            ("max_chunk_size", "512", "Maximum tokens per chunk", True),
            ("embedding_model", "multilingual-e5-large", "Default embedding model", True),
            ("search_timeout", "30", "Search timeout in seconds", True),
            ("min_quality_score", "3.0", "Minimum quality score for indexing", True)
        ]
        
        for key, value, desc, is_system in settings_data:
            self.conn.execute("""
                INSERT OR IGNORE INTO settings (key, value, description, is_system)
                VALUES (?, ?, ?, ?)
            """, (key, value, desc, is_system))
        
        # Insert default admin user
        admin_user_id = self.generate_id()
        self.conn.execute("""
            INSERT OR IGNORE INTO users (id, email, display_name, role, preferences)
            VALUES (?, ?, ?, ?, ?)
        """, (
            admin_user_id,
            "admin@erpfts.local",
            "System Administrator", 
            "admin",
            json.dumps({
                "ui_preferences": {"theme": "light", "language": "ja"},
                "search_preferences": {"min_quality_score": 3.0}
            })
        ))
        
        # Insert sample data sources
        sources_data = [
            {
                "name": "PMBOK Guide", 
                "source_type": "pdf",
                "metadata": {"category": "project_management", "authority": "PMI"}
            },
            {
                "name": "BABOK Guide",
                "source_type": "pdf", 
                "metadata": {"category": "business_analysis", "authority": "IIBA"}
            },
            {
                "name": "Project Management Blog",
                "source_type": "rss",
                "rss_feed": "https://example.com/pm-blog/feed",
                "metadata": {"category": "blog", "update_frequency": "daily"}
            }
        ]
        
        for source_data in sources_data:
            source_id = self.generate_id()
            self.conn.execute("""
                INSERT OR IGNORE INTO sources (
                    id, name, source_type, rss_feed, metadata_json, quality_weight
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                source_id,
                source_data["name"],
                source_data["source_type"],
                source_data.get("rss_feed"),
                json.dumps(source_data["metadata"]),
                4.5  # High quality for standard guides
            ))
        
        self.conn.commit()
        logger.info("Initial data inserted successfully")
    
    def create_indexes(self):
        """追加インデックス作成"""
        logger.info("Creating additional indexes...")
        
        additional_indexes = [
            # Performance optimization indexes
            "CREATE INDEX IF NOT EXISTS idx_documents_quality_status ON documents (quality_score, processing_status)",
            "CREATE INDEX IF NOT EXISTS idx_chunks_quality_tokens ON chunks (quality_score, token_count)",
            "CREATE INDEX IF NOT EXISTS idx_search_logs_time_user ON search_logs (created_at, user_id)",
            
            # Composite indexes for common queries
            "CREATE INDEX IF NOT EXISTS idx_documents_source_status ON documents (source_id, processing_status)",
            "CREATE INDEX IF NOT EXISTS idx_chunks_document_quality ON chunks (document_id, quality_score DESC)",
        ]
        
        for index_sql in additional_indexes:
            try:
                self.conn.execute(index_sql)
            except sqlite3.Error as e:
                logger.warning(f"Index creation warning: {e}")
        
        self.conn.commit()
        logger.info("Additional indexes created")
    
    def verify_schema(self):
        """スキーマ検証"""
        logger.info("Verifying database schema...")
        
        # Check that all expected tables exist
        expected_tables = [
            'users', 'sources', 'documents', 'chunks', 'embeddings',
            'search_logs', 'quality_scores', 'settings'
        ]
        
        cursor = self.conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = set(expected_tables) - set(existing_tables)
        if missing_tables:
            logger.error(f"Missing tables: {missing_tables}")
            raise ValueError(f"Schema verification failed: missing tables {missing_tables}")
        
        # Check foreign key constraints
        cursor = self.conn.execute("PRAGMA foreign_key_check")
        fk_violations = cursor.fetchall()
        if fk_violations:
            logger.error(f"Foreign key violations: {fk_violations}")
            raise ValueError("Schema verification failed: foreign key violations")
        
        logger.info("Schema verification passed")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """データベース統計取得"""
        stats = {}
        
        # Table counts
        for table in ['users', 'sources', 'documents', 'chunks', 'embeddings', 'search_logs']:
            cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table}")
            stats[f"{table}_count"] = cursor.fetchone()[0]
        
        # Database file size
        stats["database_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
        
        # Schema version
        cursor = self.conn.execute("SELECT value FROM settings WHERE key = 'system_version'")
        result = cursor.fetchone()
        stats["schema_version"] = result[0] if result else "unknown"
        
        return stats
    
    @staticmethod
    def generate_id() -> str:
        """UUID代替のID生成"""
        import secrets
        return secrets.token_hex(16)

def load_schema_from_file(schema_path: Path) -> str:
    """スキーマファイル読み込み"""
    if not schema_path.exists():
        logger.error(f"Schema file not found: {schema_path}")
        # Return inline schema if file doesn't exist
        return """
        -- Basic schema would be here
        -- This is a fallback if schema.sql doesn't exist
        """
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    """メイン実行関数"""
    logger.info("🗄️  Phase1 SQLite Database Setup Starting...")
    
    try:
        # Load schema
        if SCHEMA_PATH.exists():
            schema_content = load_schema_from_file(SCHEMA_PATH)
        else:
            # Use inline schema (from the DDL section above)
            logger.warning("Using inline schema")
            schema_content = """
            -- The complete DDL from above would be placed here
            -- For brevity, using placeholder
            PRAGMA foreign_keys = ON;
            """
        
        # Initialize database
        with SQLiteSetup() as db:
            db.execute_schema(schema_content)
            db.insert_initial_data()
            db.create_indexes()
            db.verify_schema()
            
            # Display statistics
            stats = db.get_database_stats()
            logger.info("Database setup completed successfully!")
            logger.info(f"Database statistics: {json.dumps(stats, indent=2)}")
            
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        raise

if __name__ == "__main__":
    main()
```

## 🔍 Chroma DB セットアップスクリプト

### Vector Database 初期化
```python
#!/usr/bin/env python3
"""
Phase1 Chroma Vector Database Setup Script
Purpose: Initialize Chroma DB for semantic search with proper configuration
Usage: python scripts/init_chromadb.py
"""

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_PATH = DATA_DIR / "chroma_db"

class ChromaDBSetup:
    def __init__(self, persist_directory: Path = CHROMA_PATH):
        self.persist_directory = persist_directory
        self.client: Optional[chromadb.PersistentClient] = None
        self.collection: Optional[chromadb.Collection] = None
        
    def initialize_client(self):
        """Chroma クライアント初期化"""
        # Create directory if it doesn't exist
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize persistent client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                is_persistent=True,
                persist_directory=str(self.persist_directory)
            )
        )
        
        logger.info(f"Chroma client initialized: {self.persist_directory}")
        
    def create_collection(self, collection_name: str = "erp_knowledge") -> chromadb.Collection:
        """メインコレクション作成"""
        if not self.client:
            raise ValueError("Client not initialized")
        
        # Check if collection already exists
        try:
            existing_collection = self.client.get_collection(collection_name)
            logger.info(f"Collection '{collection_name}' already exists")
            return existing_collection
        except ValueError:
            # Collection doesn't exist, create new one
            pass
        
        # Configure embedding function for multilingual-e5-large
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="intfloat/multilingual-e5-large",
            device="cpu"  # Change to "cuda" if GPU available
        )
        
        # Create collection with metadata
        collection = self.client.create_collection(
            name=collection_name,
            embedding_function=embedding_function,
            metadata={
                "description": "ERP Knowledge Base - Phase1 MVP",
                "version": "1.0.0", 
                "embedding_model": "multilingual-e5-large",
                "created_for": "phase1_mvp",
                "distance_metric": "cosine",
                "max_chunk_size": 512,
                "overlap_size": 50
            }
        )
        
        logger.info(f"Collection '{collection_name}' created successfully")
        return collection
        
    def setup_indexes(self):
        """インデックス設定・最適化"""
        if not self.collection:
            logger.warning("No collection available for index setup")
            return
            
        # Chroma handles indexing automatically
        # Configuration is done at collection creation time
        logger.info("Chroma DB uses automatic indexing - no manual setup required")
        
    def insert_sample_data(self):
        """サンプルデータ挿入"""
        if not self.collection:
            logger.warning("No collection available for sample data")
            return
            
        logger.info("Inserting sample data...")
        
        # Sample knowledge chunks for testing
        sample_documents = [
            {
                "id": "sample_001",
                "content": "プロジェクト管理とは、プロジェクトの目標を達成するために、知識、スキル、ツール、技法を適用する活動です。",
                "metadata": {
                    "source_type": "pmbok",
                    "document_type": "guide",
                    "section": "introduction",
                    "page_number": 1,
                    "quality_score": 4.8,
                    "language": "ja",
                    "chunk_index": 0
                }
            },
            {
                "id": "sample_002", 
                "content": "ビジネス分析とは、組織の変化を促進するために、ニーズを定義し、ステークホルダーに価値を提供するソリューションを推奨する実践です。",
                "metadata": {
                    "source_type": "babok",
                    "document_type": "guide", 
                    "section": "introduction",
                    "page_number": 1,
                    "quality_score": 4.7,
                    "language": "ja",
                    "chunk_index": 0
                }
            },
            {
                "id": "sample_003",
                "content": "リスク管理プロセスには、リスクの識別、分析、対応計画、監視・コントロールが含まれます。",
                "metadata": {
                    "source_type": "pmbok",
                    "document_type": "guide",
                    "section": "risk_management", 
                    "page_number": 145,
                    "quality_score": 4.6,
                    "language": "ja",
                    "chunk_index": 1
                }
            }
        ]
        
        # Extract data for batch insertion
        ids = [doc["id"] for doc in sample_documents]
        documents = [doc["content"] for doc in sample_documents]
        metadatas = [doc["metadata"] for doc in sample_documents]
        
        # Insert into collection
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
        logger.info(f"Inserted {len(sample_documents)} sample documents")
        
    def test_search_functionality(self):
        """検索機能テスト"""
        if not self.collection:
            logger.warning("No collection available for search test")
            return
            
        logger.info("Testing search functionality...")
        
        # Test query
        test_query = "プロジェクト管理の手法"
        
        try:
            results = self.collection.query(
                query_texts=[test_query],
                n_results=3,
                include=["documents", "metadatas", "distances"]
            )
            
            logger.info(f"Search test successful!")
            logger.info(f"Query: '{test_query}'")
            logger.info(f"Results: {len(results['documents'][0])} documents found")
            
            # Display results
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0], 
                results['distances'][0]
            )):
                logger.info(f"  Result {i+1}:")
                logger.info(f"    Content: {doc[:100]}...")
                logger.info(f"    Source: {metadata.get('source_type', 'unknown')}")
                logger.info(f"    Distance: {distance:.4f}")
                
        except Exception as e:
            logger.error(f"Search test failed: {e}")
            raise
            
    def get_collection_stats(self) -> Dict[str, Any]:
        """コレクション統計取得"""
        if not self.collection:
            return {"error": "No collection available"}
            
        try:
            count = self.collection.count()
            metadata = self.collection.metadata
            
            return {
                "collection_name": self.collection.name,
                "document_count": count,
                "embedding_model": metadata.get("embedding_model", "unknown"),
                "version": metadata.get("version", "unknown"),
                "description": metadata.get("description", ""),
                "distance_metric": metadata.get("distance_metric", "cosine")
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}
            
    def verify_setup(self):
        """セットアップ検証"""
        logger.info("Verifying Chroma DB setup...")
        
        # Check client connection
        if not self.client:
            raise ValueError("Client not initialized")
            
        # Check collection exists and is accessible
        if not self.collection:
            raise ValueError("Collection not created")
            
        # Check we can perform basic operations
        try:
            count = self.collection.count()
            logger.info(f"Collection contains {count} documents")
        except Exception as e:
            raise ValueError(f"Collection operations failed: {e}")
            
        # Test search if documents exist
        if count > 0:
            self.test_search_functionality()
            
        logger.info("Chroma DB verification passed")

def main():
    """メイン実行関数"""
    logger.info("🔍 Phase1 Chroma Vector Database Setup Starting...")
    
    try:
        setup = ChromaDBSetup()
        
        # Initialize and setup
        setup.initialize_client()
        setup.collection = setup.create_collection()
        setup.setup_indexes()
        setup.insert_sample_data()
        setup.verify_setup()
        
        # Display statistics
        stats = setup.get_collection_stats()
        logger.info("Chroma DB setup completed successfully!")
        logger.info(f"Collection statistics: {json.dumps(stats, indent=2)}")
        
        return setup
        
    except Exception as e:
        logger.error(f"Chroma DB setup failed: {e}")
        raise

if __name__ == "__main__":
    main()
```

## ⚙️ データベース管理ユーティリティ

### SQLAlchemy ORM モデル定義
```python
#!/usr/bin/env python3
"""
SQLAlchemy ORM Models for ERP Knowledge RAG System Phase1
Purpose: Define database models using SQLAlchemy 2.0 for async operations
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, Date,
    ForeignKey, Index, CheckConstraint, UniqueConstraint, text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.sqlite import TEXT
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, Dict, Any
import json
import secrets

Base = declarative_base()

def generate_id() -> str:
    """Generate UUID-like ID"""
    return secrets.token_hex(16)

class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

class JSONMixin:
    """Mixin for JSON field validation"""
    
    @validates('preferences', 'metadata_json', 'access_config', 'model_parameters', 'search_metadata')
    def validate_json(self, key, value):
        if value and isinstance(value, str):
            try:
                json.loads(value)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON in {key}")
        return value

class User(Base, TimestampMixin, JSONMixin):
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True, default=generate_id)
    email = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default='viewer')
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    preferences = Column(TEXT, default='{}')
    
    # Relationships
    search_logs = relationship("SearchLog", back_populates="user")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(role.in_(['guest', 'viewer', 'editor', 'admin']), name='users_role_check'),
        Index('idx_users_email', 'email'),
        Index('idx_users_role', 'role'),
        Index('idx_users_active', 'is_active'),
    )

class Source(Base, TimestampMixin, JSONMixin):
    __tablename__ = 'sources'
    
    id = Column(String, primary_key=True, default=generate_id)
    name = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)
    base_url = Column(TEXT)
    rss_feed = Column(TEXT)
    access_config = Column(TEXT, default='{}')
    check_interval = Column(Integer, default=3600)
    last_checked = Column(DateTime)
    last_success_check = Column(DateTime)
    consecutive_failures = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    quality_weight = Column(Float, default=1.0)
    metadata_json = Column(TEXT, default='{}')
    
    # Relationships
    documents = relationship("Document", back_populates="source", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(source_type.in_(['pdf', 'rss', 'web', 'github', 'api', 'manual']), name='sources_type_check'),
        CheckConstraint(quality_weight >= 0, name='sources_quality_positive'),
        CheckConstraint(quality_weight <= 5.0, name='sources_quality_max'),
        CheckConstraint(consecutive_failures >= 0, name='sources_failures_positive'),
        Index('idx_sources_type', 'source_type'),
        Index('idx_sources_active', 'is_active'),
        Index('idx_sources_last_checked', 'last_checked'),
    )

class Document(Base, TimestampMixin, JSONMixin):
    __tablename__ = 'documents'
    
    id = Column(String, primary_key=True, default=generate_id)
    source_id = Column(String, ForeignKey('sources.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(500), nullable=False)
    author = Column(String(255))
    published_date = Column(Date)
    last_modified = Column(DateTime)
    file_path = Column(TEXT)
    content_hash = Column(String(64), unique=True)  # SHA-256
    language = Column(String(10), default='ja')
    document_type = Column(String(50), default='article')
    word_count = Column(Integer)
    page_count = Column(Integer)
    metadata_json = Column(TEXT, default='{}')
    quality_score = Column(Float, default=0.0)
    processing_status = Column(String(20), default='pending')
    processing_error = Column(TEXT)
    
    # Relationships
    source = relationship("Source", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(language.in_(['ja', 'en', 'auto']), name='documents_language_check'),
        CheckConstraint(processing_status.in_(['pending', 'processing', 'completed', 'failed', 'skipped']), 
                       name='documents_status_check'),
        CheckConstraint(quality_score >= 0, name='documents_quality_positive'),
        CheckConstraint(quality_score <= 5.0, name='documents_quality_max'),
        CheckConstraint(word_count >= 0, name='documents_word_count_positive'),
        CheckConstraint(page_count >= 0, name='documents_page_count_positive'),
        Index('idx_documents_source', 'source_id'),
        Index('idx_documents_hash', 'content_hash'),
        Index('idx_documents_type', 'document_type'),
        Index('idx_documents_quality', 'quality_score'),
        Index('idx_documents_status', 'processing_status'),
    )

class Chunk(Base, TimestampMixin, JSONMixin):
    __tablename__ = 'chunks'
    
    id = Column(String, primary_key=True, default=generate_id)
    document_id = Column(String, ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(TEXT, nullable=False)
    content_hash = Column(String(64))
    token_count = Column(Integer)
    char_count = Column(Integer)
    page_number = Column(Integer)
    section_title = Column(String(255))
    section_level = Column(Integer)
    quality_score = Column(Float, default=0.0)
    metadata_json = Column(TEXT, default='{}')
    embedding_id = Column(String)  # Reference to vector DB
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    embeddings = relationship("Embedding", back_populates="chunk", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('document_id', 'chunk_index', name='uq_document_chunk_index'),
        CheckConstraint(token_count > 0, name='chunks_token_count_positive'),
        CheckConstraint(char_count > 0, name='chunks_char_count_positive'),
        CheckConstraint(quality_score >= 0, name='chunks_quality_positive'),
        CheckConstraint(quality_score <= 5.0, name='chunks_quality_max'),
        CheckConstraint(section_level >= 0, name='chunks_section_level_positive'),
        CheckConstraint(page_number > 0, name='chunks_page_number_positive'),
        Index('idx_chunks_document', 'document_id'),
        Index('idx_chunks_page', 'page_number'),
        Index('idx_chunks_quality', 'quality_score'),
        Index('idx_chunks_embedding', 'embedding_id'),
    )

class Embedding(Base, TimestampMixin, JSONMixin):
    __tablename__ = 'embeddings'
    
    id = Column(String, primary_key=True, default=generate_id)
    chunk_id = Column(String, ForeignKey('chunks.id', ondelete='CASCADE'), nullable=False)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    vector_dimension = Column(Integer, nullable=False)
    embedding_hash = Column(String(64))
    model_parameters = Column(TEXT, default='{}')
    generation_time = Column(DateTime, default=func.now())
    
    # Relationships
    chunk = relationship("Chunk", back_populates="embeddings")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('chunk_id', 'model_name', 'model_version', name='uq_chunk_model_version'),
        CheckConstraint(vector_dimension > 0, name='embeddings_dimension_positive'),
        Index('idx_embeddings_chunk', 'chunk_id'),
        Index('idx_embeddings_model', 'model_name', 'model_version'),
        Index('idx_embeddings_hash', 'embedding_hash'),
    )

class SearchLog(Base, JSONMixin):
    __tablename__ = 'search_logs'
    
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, ForeignKey('users.id', ondelete='SET NULL'))
    session_id = Column(String(255))
    query_text = Column(TEXT, nullable=False)
    query_type = Column(String(50), default='semantic')
    filters_applied = Column(TEXT, default='{}')
    result_count = Column(Integer, default=0)
    response_time_ms = Column(Integer)
    clicked_results = Column(TEXT, default='[]')  # JSON array
    satisfaction_rating = Column(Integer)
    search_metadata = Column(TEXT, default='{}')
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="search_logs")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(query_type.in_(['semantic', 'keyword', 'hybrid']), name='search_logs_query_type_check'),
        CheckConstraint(result_count >= 0, name='search_logs_result_count_positive'),
        CheckConstraint(response_time_ms >= 0, name='search_logs_response_time_positive'),
        CheckConstraint(satisfaction_rating >= 1, name='search_logs_rating_min'),
        CheckConstraint(satisfaction_rating <= 5, name='search_logs_rating_max'),
        Index('idx_search_logs_user', 'user_id'),
        Index('idx_search_logs_session', 'session_id'),
        Index('idx_search_logs_time', 'created_at'),
    )

class QualityScore(Base):
    __tablename__ = 'quality_scores'
    
    id = Column(String, primary_key=True, default=generate_id)
    entity_type = Column(String(20), nullable=False)
    entity_id = Column(String, nullable=False)
    score_type = Column(String(50), nullable=False)
    score_value = Column(Float, nullable=False)
    max_possible_score = Column(Float, default=5.0)
    evaluator = Column(String(100))
    evaluation_method = Column(String(50))
    evaluation_date = Column(DateTime, default=func.now())
    notes = Column(TEXT)
    metadata = Column(TEXT, default='{}')
    is_current = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint(entity_type.in_(['source', 'document', 'chunk']), name='quality_entity_type_check'),
        CheckConstraint(score_value >= 0, name='quality_score_positive'),
        CheckConstraint(max_possible_score > 0, name='quality_max_score_positive'),
        Index('idx_quality_entity', 'entity_type', 'entity_id'),
        Index('idx_quality_type', 'score_type'),
        Index('idx_quality_current', 'is_current'),
    )

class Setting(Base, TimestampMixin):
    __tablename__ = 'settings'
    
    id = Column(String, primary_key=True, default=generate_id)
    key = Column(String, unique=True, nullable=False)
    value = Column(TEXT)
    description = Column(TEXT)
    is_system = Column(Boolean, default=False)
    
    # Constraints
    __table_args__ = (
        Index('idx_settings_key', 'key'),
        Index('idx_settings_system', 'is_system'),
    )
```

### データベース操作ヘルパー関数
```python
#!/usr/bin/env python3
"""
Database Helper Functions for Phase1
Purpose: Common database operations and utilities
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update, delete, func, text
from typing import List, Dict, Any, Optional, AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from .models import Base, User, Source, Document, Chunk, Embedding, SearchLog, QualityScore, Setting

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Async session context manager"""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def create_tables(self):
        """Create all tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("All tables created successfully")
    
    async def drop_tables(self):
        """Drop all tables (use with caution!)"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("All tables dropped")
    
    async def get_table_stats(self) -> Dict[str, int]:
        """Get row counts for all tables"""
        stats = {}
        async with self.get_session() as session:
            for table_name in ['users', 'sources', 'documents', 'chunks', 'embeddings', 'search_logs']:
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                stats[table_name] = result.scalar()
        return stats
    
    # User operations
    async def create_user(self, email: str, display_name: str, role: str = 'viewer') -> User:
        """Create new user"""
        async with self.get_session() as session:
            user = User(email=email, display_name=display_name, role=role)
            session.add(user)
            await session.flush()
            await session.refresh(user)
            return user
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        async with self.get_session() as session:
            result = await session.execute(
                select(User).where(User.email == email)
            )
            return result.scalar_one_or_none()
    
    # Source operations
    async def create_source(self, name: str, source_type: str, **kwargs) -> Source:
        """Create new source"""
        async with self.get_session() as session:
            source = Source(name=name, source_type=source_type, **kwargs)
            session.add(source)
            await session.flush()
            await session.refresh(source)
            return source
    
    async def get_active_sources(self) -> List[Source]:
        """Get all active sources"""
        async with self.get_session() as session:
            result = await session.execute(
                select(Source).where(Source.is_active == True)
            )
            return result.scalars().all()
    
    # Document operations
    async def create_document(self, source_id: str, title: str, **kwargs) -> Document:
        """Create new document"""
        async with self.get_session() as session:
            document = Document(source_id=source_id, title=title, **kwargs)
            session.add(document)
            await session.flush()
            await session.refresh(document)
            return document
    
    async def get_documents_by_status(self, status: str) -> List[Document]:
        """Get documents by processing status"""
        async with self.get_session() as session:
            result = await session.execute(
                select(Document)
                .where(Document.processing_status == status)
                .options(selectinload(Document.source))
            )
            return result.scalars().all()
    
    # Chunk operations
    async def create_chunk(self, document_id: str, chunk_index: int, content: str, **kwargs) -> Chunk:
        """Create new chunk"""
        async with self.get_session() as session:
            chunk = Chunk(
                document_id=document_id,
                chunk_index=chunk_index,
                content=content,
                **kwargs
            )
            session.add(chunk)
            await session.flush()
            await session.refresh(chunk)
            return chunk
    
    async def get_chunks_for_embedding(self, min_quality: float = 3.0) -> List[Chunk]:
        """Get chunks that need embedding generation"""
        async with self.get_session() as session:
            result = await session.execute(
                select(Chunk)
                .where(
                    Chunk.embedding_id.is_(None),
                    Chunk.quality_score >= min_quality
                )
                .options(selectinload(Chunk.document))
            )
            return result.scalars().all()
    
    # Search log operations
    async def log_search(self, query_text: str, user_id: Optional[str] = None, **kwargs) -> SearchLog:
        """Log search query"""
        async with self.get_session() as session:
            search_log = SearchLog(
                query_text=query_text,
                user_id=user_id,
                **kwargs
            )
            session.add(search_log)
            await session.flush()
            await session.refresh(search_log)
            return search_log
    
    # Settings operations
    async def get_setting(self, key: str) -> Optional[str]:
        """Get setting value by key"""
        async with self.get_session() as session:
            result = await session.execute(
                select(Setting.value).where(Setting.key == key)
            )
            return result.scalar_one_or_none()
    
    async def set_setting(self, key: str, value: str, description: str = None) -> Setting:
        """Set setting value"""
        async with self.get_session() as session:
            # Try to update existing setting
            result = await session.execute(
                select(Setting).where(Setting.key == key)
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                setting.value = value
                if description:
                    setting.description = description
            else:
                setting = Setting(key=key, value=value, description=description)
                session.add(setting)
            
            await session.flush()
            await session.refresh(setting)
            return setting

# Global database manager instance
db_manager: Optional[DatabaseManager] = None

def get_database_manager() -> DatabaseManager:
    """Get global database manager instance"""
    global db_manager
    if db_manager is None:
        raise ValueError("Database manager not initialized")
    return db_manager

def initialize_database_manager(database_url: str):
    """Initialize global database manager"""
    global db_manager
    db_manager = DatabaseManager(database_url)
    logger.info(f"Database manager initialized with URL: {database_url}")
```

## 🤖 Implementation Notes for AI

### Critical Setup Sequence
1. **Week 1 Day 3**: SQLite スキーマ作成、基本テーブル構築
2. **Week 1 Day 4**: Chroma DB セットアップ、コレクション作成
3. **Week 1 Day 5**: SQLAlchemy ORM統合、データベース操作関数

### Database Architecture
- **SQLite**: 軽量・高速、ローカル開発・テスト最適化
- **Chroma DB**: ベクトル検索専用、multilingual-e5-large対応
- **Redis**: セッション・キャッシュ（オプション）
- **PostgreSQL**: 本番環境移行準備（SQLAlchemy使用）

### Quality Gates
- **スキーマ整合性**: 外部キー制約・チェック制約100%
- **パフォーマンス**: インデックス効果・クエリ最適化確認
- **データ品質**: 重複検出・整合性チェック機能
- **バックアップ**: 復旧手順・整合性検証

### Common Pitfalls
- **SQLite制限**: 同時書き込み・大量データ処理注意
- **Chroma DB設定**: 永続化パス・埋め込みモデル整合性
- **文字エンコーディング**: UTF-8設定・日本語対応確認
- **外部キー**: CASCADE設定・参照整合性維持

---

**Version**: 1.0.0 | **Last Updated**: 2025-01-21 | **Next Review**: Weekly Development Review