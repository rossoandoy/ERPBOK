# ERP知識RAGシステム - データモデル設計書

---
doc_type: "data_model_design"
complexity: "high"
estimated_effort: "40-60 hours"
prerequisites: ["01_PRD.md", "02_SystemArchitecture.md", "03_FunctionalRequirements.md", "04_NonFunctionalRequirements.md"]
implementation_priority: "high"
ai_assistance_level: "full_automation_possible"
version: "1.0.0"
author: "Claude Code"
created_date: "2025-01-21"
status: "draft"
---

## 📋 データモデル概要

### データベース構成
```
ERP知識RAGシステム データレイヤー
├── メタデータDB (PostgreSQL/SQLite)
│   ├── ソース管理
│   ├── 文書管理
│   ├── ユーザー・権限管理
│   └── システム設定
├── ベクトルDB (Chroma/Supabase Vector)
│   ├── チャンクベクトル
│   ├── 埋め込みメタデータ
│   └── 類似検索インデックス
└── キャッシュDB (Redis/In-Memory)
    ├── 検索結果キャッシュ
    ├── セッション管理
    └── 一時データ
```

### 設計原則
- **正規化**: 第3正規形準拠、必要に応じて非正規化
- **拡張性**: 大量データ対応、パーティショニング考慮
- **整合性**: 参照整合性、制約による品質保証
- **パフォーマンス**: インデックス最適化、クエリ効率化
- **監査**: 変更履歴、アクセスログの保持

## 🗄️ メタデータデータベース設計

### ER図
```
                    ┌─────────────────┐
                    │     Users       │
                    ├─────────────────┤
                    │ id (PK)         │
                    │ email           │
                    │ display_name    │
                    │ role            │
                    │ is_active       │
                    │ last_login      │
                    │ created_at      │
                    │ updated_at      │
                    └─────────────────┘
                             │
                             │ 1:N
                             ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│     Sources     │         │   User_Actions  │         │    Settings     │
├─────────────────┤    ┌────┤─────────────────┤         ├─────────────────┤
│ id (PK)         │    │    │ id (PK)         │         │ id (PK)         │
│ name            │    │    │ user_id (FK)    │         │ key             │
│ source_type     │    │    │ action_type     │         │ value           │
│ base_url        │    │    │ target_id       │         │ description     │
│ rss_feed        │    │    │ metadata        │         │ is_system       │
│ check_interval  │    │    │ created_at      │         │ created_at      │
│ last_checked    │    │    └─────────────────┘         │ updated_at      │
│ is_active       │    │                               └─────────────────┘
│ quality_score   │    │
│ metadata_json   │    │
│ created_at      │    │    ┌─────────────────┐
│ updated_at      │    │    │   Search_Logs   │
└─────────────────┘    │    ├─────────────────┤
         │              │    │ id (PK)         │
         │ 1:N          │    │ user_id (FK)    │
         ▼              │    │ query_text      │
┌─────────────────┐    │    │ result_count    │
│   Documents     │    │    │ response_time   │
├─────────────────┤    │    │ satisfaction    │
│ id (PK)         │    │    │ clicked_sources │
│ source_id (FK)  │────┘    │ created_at      │
│ title           │         └─────────────────┘
│ author          │
│ published_date  │         ┌─────────────────┐
│ last_modified   │         │    Feedback     │
│ file_path       │         ├─────────────────┤
│ content_hash    │         │ id (PK)         │
│ language        │         │ search_log_id(FK)│
│ document_type   │         │ user_id (FK)    │
│ metadata_json   │         │ rating          │
│ quality_score   │         │ comment         │
│ processing_status│        │ useful_sources  │
│ created_at      │         │ improvement_suggestions│
│ updated_at      │         │ created_at      │
└─────────────────┘         └─────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐         ┌─────────────────┐
│     Chunks      │         │   Quality_Scores│
├─────────────────┤         ├─────────────────┤
│ id (PK)         │         │ id (PK)         │
│ document_id (FK)│         │ entity_type     │
│ chunk_index     │         │ entity_id       │
│ content         │         │ score_type      │
│ token_count     │         │ score_value     │
│ page_number     │         │ evaluator       │
│ section_title   │         │ evaluation_date │
│ quality_score   │         │ notes           │
│ metadata_json   │         │ created_at      │
│ embedding_id    │ ────────┤ updated_at      │
│ created_at      │         └─────────────────┘
│ updated_at      │
└─────────────────┘
         │
         │ 1:1
         ▼
┌─────────────────┐
│   Embeddings    │
├─────────────────┤
│ id (PK)         │
│ chunk_id (FK)   │
│ model_name      │
│ model_version   │
│ vector_dimension│
│ embedding_hash  │
│ created_at      │
│ updated_at      │
└─────────────────┘
```

### テーブル定義

#### Users (ユーザー管理)
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT users_role_check CHECK (role IN ('guest', 'viewer', 'editor', 'admin')),
    INDEX idx_users_email (email),
    INDEX idx_users_role (role),
    INDEX idx_users_active (is_active)
);

-- ユーザー設定例
{
    "ui_preferences": {
        "theme": "light",
        "language": "ja",
        "results_per_page": 10
    },
    "search_preferences": {
        "default_filters": {
            "source_types": ["pmbok", "babok"],
            "min_quality_score": 3.5
        },
        "preferred_response_format": "detailed"
    }
}
```

#### Sources (データソース管理)
```sql
CREATE TABLE sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    base_url TEXT,
    rss_feed TEXT,
    access_config JSONB DEFAULT '{}',
    check_interval INTEGER DEFAULT 3600, -- seconds
    last_checked TIMESTAMP,
    last_success_check TIMESTAMP,
    consecutive_failures INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    quality_weight DECIMAL(3,2) DEFAULT 1.0,
    metadata_json JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT sources_type_check CHECK (source_type IN ('pdf', 'rss', 'web', 'github', 'api')),
    CONSTRAINT sources_quality_weight_check CHECK (quality_weight >= 0 AND quality_weight <= 5.0),
    INDEX idx_sources_type (source_type),
    INDEX idx_sources_active (is_active),
    INDEX idx_sources_check_time (last_checked)
);

-- アクセス設定例
{
    "authentication": {
        "type": "api_key",
        "api_key_header": "X-API-Key"
    },
    "parsing_config": {
        "selectors": {
            "content": ".article-content",
            "title": "h1.title",
            "author": ".author-name"
        }
    },
    "rate_limiting": {
        "requests_per_minute": 10
    }
}
```

#### Documents (文書管理)
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    author VARCHAR(255),
    published_date DATE,
    last_modified TIMESTAMP,
    file_path TEXT,
    content_hash VARCHAR(64) UNIQUE, -- SHA-256
    language VARCHAR(10) DEFAULT 'ja',
    document_type VARCHAR(50) DEFAULT 'article',
    word_count INTEGER,
    page_count INTEGER,
    metadata_json JSONB DEFAULT '{}',
    quality_score DECIMAL(3,2) DEFAULT 0.0,
    processing_status VARCHAR(20) DEFAULT 'pending',
    processing_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT documents_language_check CHECK (language IN ('ja', 'en', 'auto')),
    CONSTRAINT documents_status_check CHECK (processing_status IN 
        ('pending', 'processing', 'completed', 'failed', 'skipped')),
    CONSTRAINT documents_quality_check CHECK (quality_score >= 0 AND quality_score <= 5.0),
    
    INDEX idx_documents_source (source_id),
    INDEX idx_documents_hash (content_hash),
    INDEX idx_documents_type (document_type),
    INDEX idx_documents_quality (quality_score),
    INDEX idx_documents_status (processing_status),
    INDEX idx_documents_published (published_date),
    FULLTEXT INDEX idx_documents_fulltext (title, author)
);

-- メタデータ例
{
    "extraction_info": {
        "method": "PyPDF2",
        "extraction_time": "2025-01-21T10:30:00Z",
        "pages_processed": 245
    },
    "content_analysis": {
        "topics": ["risk_management", "project_planning"],
        "entities": ["PMI", "PMBOK", "PMP"],
        "readability_score": 8.2
    },
    "source_specific": {
        "doi": "10.1000/182",
        "isbn": "978-1-62825-664-2",
        "journal": "Project Management Journal"
    }
}
```

#### Chunks (チャンク管理)
```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_hash VARCHAR(64),
    token_count INTEGER,
    char_count INTEGER,
    page_number INTEGER,
    section_title VARCHAR(255),
    section_level INTEGER,
    quality_score DECIMAL(3,2) DEFAULT 0.0,
    metadata_json JSONB DEFAULT '{}',
    embedding_id UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(document_id, chunk_index),
    CONSTRAINT chunks_token_count_check CHECK (token_count > 0),
    CONSTRAINT chunks_quality_check CHECK (quality_score >= 0 AND quality_score <= 5.0),
    
    INDEX idx_chunks_document (document_id),
    INDEX idx_chunks_page (page_number),
    INDEX idx_chunks_quality (quality_score),
    INDEX idx_chunks_section (section_title),
    FULLTEXT INDEX idx_chunks_content (content)
);

-- チャンクメタデータ例
{
    "chunking_strategy": {
        "method": "semantic_chunking",
        "overlap_tokens": 50,
        "max_tokens": 512
    },
    "content_type": "paragraph",
    "importance_score": 0.85,
    "contains_tables": false,
    "contains_figures": true,
    "figure_references": ["Figure 5.1", "Table 5.2"]
}
```

#### Embeddings (埋め込みベクトル管理)
```sql
CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chunk_id UUID NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    vector_dimension INTEGER NOT NULL,
    embedding_hash VARCHAR(64),
    model_parameters JSONB DEFAULT '{}',
    generation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(chunk_id, model_name, model_version),
    INDEX idx_embeddings_chunk (chunk_id),
    INDEX idx_embeddings_model (model_name, model_version),
    INDEX idx_embeddings_hash (embedding_hash)
);

-- モデルパラメータ例
{
    "model_config": {
        "max_seq_length": 512,
        "normalize_embeddings": true,
        "pooling_mode": "mean"
    },
    "generation_metadata": {
        "batch_size": 32,
        "processing_time_ms": 1250,
        "gpu_used": true
    }
}
```

#### Search_Logs (検索ログ管理)
```sql
CREATE TABLE search_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id VARCHAR(255),
    query_text TEXT NOT NULL,
    query_type VARCHAR(50) DEFAULT 'semantic',
    filters_applied JSONB DEFAULT '{}',
    result_count INTEGER DEFAULT 0,
    response_time_ms INTEGER,
    clicked_results INTEGER[] DEFAULT '{}',
    satisfaction_rating INTEGER,
    search_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT search_logs_rating_check CHECK (satisfaction_rating >= 1 AND satisfaction_rating <= 5),
    INDEX idx_search_logs_user (user_id),
    INDEX idx_search_logs_session (session_id),
    INDEX idx_search_logs_time (created_at),
    INDEX idx_search_logs_query_type (query_type),
    FULLTEXT INDEX idx_search_logs_query (query_text)
);

-- 検索メタデータ例
{
    "search_strategy": {
        "vector_weight": 0.7,
        "keyword_weight": 0.3,
        "rerank_applied": true
    },
    "results_analysis": {
        "avg_similarity_score": 0.82,
        "source_distribution": {
            "pmbok": 6,
            "babok": 3,
            "blogs": 1
        }
    },
    "user_context": {
        "previous_queries": ["risk management", "project planning"],
        "preferred_sources": ["standard_documents"]
    }
}
```

#### Quality_Scores (品質評価管理)
```sql
CREATE TABLE quality_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(20) NOT NULL,
    entity_id UUID NOT NULL,
    score_type VARCHAR(50) NOT NULL,
    score_value DECIMAL(5,3) NOT NULL,
    max_possible_score DECIMAL(5,3) DEFAULT 5.000,
    evaluator VARCHAR(100),
    evaluation_method VARCHAR(50),
    evaluation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    metadata JSONB DEFAULT '{}',
    is_current BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT quality_entity_type_check CHECK (entity_type IN ('source', 'document', 'chunk')),
    CONSTRAINT quality_score_positive CHECK (score_value >= 0),
    INDEX idx_quality_entity (entity_type, entity_id),
    INDEX idx_quality_type (score_type),
    INDEX idx_quality_current (is_current),
    INDEX idx_quality_date (evaluation_date)
);

-- 品質スコア種別
-- authority_score: 権威性スコア (0-5)
-- accuracy_score: 正確性スコア (0-5)
-- timeliness_score: 時宜性スコア (0-5)
-- completeness_score: 網羅性スコア (0-5)
-- utility_score: 利用性スコア (0-5)
-- overall_score: 総合スコア (0-5)
```

## 🔍 ベクトルデータベース設計

### Chroma DB 設計
```python
# Chromaコレクション設計
CHROMA_COLLECTIONS = {
    "erp_knowledge": {
        "embedding_function": "multilingual-e5-large",
        "metadata_schema": {
            "document_id": "string",
            "chunk_id": "string",
            "source_type": "string",
            "document_type": "string", 
            "language": "string",
            "quality_score": "float",
            "published_date": "string",
            "section_title": "string",
            "page_number": "int",
            "token_count": "int"
        },
        "distance_metric": "cosine"
    }
}

# ChromaDB設定例
import chromadb
from chromadb.config import Settings

# 永続化設定
client = chromadb.PersistentClient(
    path="./chroma_db",
    settings=Settings(
        anonymized_telemetry=False,
        is_persistent=True
    )
)

# コレクション作成
collection = client.create_collection(
    name="erp_knowledge",
    metadata={"description": "ERP knowledge base embeddings"},
    embedding_function=multilingual_e5_large_embedding_function
)
```

### ベクトル検索最適化
```python
# 検索インデックス設定
VECTOR_INDEX_CONFIG = {
    "index_type": "HNSW",  # Hierarchical Navigable Small World
    "parameters": {
        "M": 16,           # 各ノードの接続数
        "ef_construction": 200,  # 構築時の探索幅
        "ef_search": 100,  # 検索時の探索幅
        "max_elements": 1000000  # 最大要素数
    },
    "distance_metric": "cosine"
}

# 階層化インデックス設計
HIERARCHICAL_INDEX = {
    "levels": [
        {
            "name": "document_level",
            "chunk_size": 2000,
            "overlap": 200,
            "aggregation": "mean_pooling"
        },
        {
            "name": "section_level", 
            "chunk_size": 800,
            "overlap": 100,
            "aggregation": "attention_weighted"
        },
        {
            "name": "paragraph_level",
            "chunk_size": 400,
            "overlap": 50,
            "aggregation": "none"
        }
    ]
}
```

## 💾 キャッシュDB設計 (Redis)

### Redis データ構造
```python
# キャッシュキー設計
CACHE_KEYS = {
    "search_results": "search:{query_hash}",
    "user_session": "session:{session_id}",
    "document_cache": "doc:{document_id}",
    "embedding_cache": "embed:{content_hash}",
    "quality_cache": "quality:{entity_type}:{entity_id}",
    "popular_queries": "popular_queries:{date}",
    "system_stats": "stats:{metric_name}:{timestamp}"
}

# TTL設定
TTL_CONFIG = {
    "search_results": 3600,      # 1時間
    "user_session": 86400,       # 24時間
    "document_cache": 7200,      # 2時間
    "embedding_cache": 604800,   # 1週間
    "quality_cache": 3600,       # 1時間
    "popular_queries": 86400,    # 24時間
    "system_stats": 300          # 5分
}

# Redis クラスター設計（将来拡張用）
REDIS_CLUSTER_CONFIG = {
    "nodes": [
        {"host": "redis-1", "port": 6379, "role": "master"},
        {"host": "redis-2", "port": 6379, "role": "replica"},
        {"host": "redis-3", "port": 6379, "role": "master"}
    ],
    "sharding_strategy": "consistent_hashing",
    "replication_factor": 1
}
```

## 📊 データパイプライン設計

### ETLパイプライン
```python
# データ処理パイプライン設計
class DataPipeline:
    def __init__(self):
        self.stages = [
            ExtractionStage(),
            TransformationStage(), 
            QualityAssuranceStage(),
            EmbeddingGenerationStage(),
            LoadingStage(),
            IndexingStage()
        ]
    
    async def process_document(self, document_path):
        """文書処理パイプライン実行"""
        context = ProcessingContext(document_path)
        
        for stage in self.stages:
            try:
                context = await stage.process(context)
                await self._log_stage_completion(stage, context)
            except Exception as e:
                await self._handle_stage_error(stage, context, e)
                break
        
        return context

# 段階別処理定義
class TransformationStage:
    async def process(self, context):
        # 1. テキスト前処理
        clean_text = self.clean_text(context.raw_text)
        
        # 2. チャンク分割
        chunks = self.smart_chunking(clean_text)
        
        # 3. メタデータ抽出
        metadata = self.extract_metadata(context)
        
        # 4. 品質評価
        quality_score = self.evaluate_quality(chunks, metadata)
        
        context.processed_chunks = chunks
        context.metadata = metadata
        context.quality_score = quality_score
        
        return context
```

### データ整合性管理
```python
# データ整合性チェック
class DataConsistencyChecker:
    async def run_consistency_checks(self):
        """データ整合性の包括チェック"""
        checks = [
            self.check_orphaned_chunks(),
            self.check_missing_embeddings(),
            self.check_quality_score_ranges(),
            self.check_reference_integrity(),
            self.check_duplicate_content()
        ]
        
        results = await asyncio.gather(*checks)
        return self.generate_consistency_report(results)
    
    async def check_orphaned_chunks(self):
        """孤立チャンクの検出"""
        query = """
        SELECT c.id, c.document_id
        FROM chunks c
        LEFT JOIN documents d ON c.document_id = d.id
        WHERE d.id IS NULL
        """
        return await self.db.fetch_all(query)
    
    async def check_missing_embeddings(self):
        """埋め込みベクトル未生成チャンクの検出"""
        query = """
        SELECT c.id, c.document_id
        FROM chunks c
        LEFT JOIN embeddings e ON c.id = e.chunk_id
        WHERE e.id IS NULL 
        AND c.quality_score >= 3.0
        """
        return await self.db.fetch_all(query)
```

## 🔄 データバックアップ・復旧設計

### バックアップ戦略
```yaml
バックアップ方式:
  フルバックアップ:
    - 頻度: 毎日1回（深夜3:00）
    - 対象: 全データベース + ベクトルDB
    - 保持期間: 30日
    - 方式: pg_dump + chroma export
  
  増分バックアップ:
    - 頻度: 6時間毎
    - 対象: 変更されたテーブルのみ
    - 保持期間: 7日
    - 方式: WAL (Write-Ahead Logging)
  
  トランザクションログバックアップ:
    - 頻度: 15分毎
    - 対象: トランザクションログ
    - 保持期間: 24時間
    - 方式: 継続的ログシップング

ベクトルDBバックアップ:
  - Chromaデータディレクトリの圧縮バックアップ
  - インデックス再構築用の設定ファイル
  - メタデータとベクトルデータの整合性検証
```

### 災害復旧計画
```python
class DisasterRecoveryPlan:
    def __init__(self):
        self.recovery_procedures = [
            self.assess_damage,
            self.restore_metadata_db,
            self.restore_vector_db,
            self.rebuild_indexes,
            self.validate_consistency,
            self.resume_services
        ]
    
    async def execute_recovery(self, incident_type):
        """災害復旧手順の実行"""
        recovery_log = RecoveryLog(incident_type)
        
        for procedure in self.recovery_procedures:
            start_time = time.time()
            try:
                result = await procedure(recovery_log)
                elapsed = time.time() - start_time
                recovery_log.log_success(procedure.__name__, elapsed)
            except Exception as e:
                recovery_log.log_failure(procedure.__name__, str(e))
                await self.notify_recovery_failure(procedure, e)
                break
        
        return recovery_log

# RTO/RPO 目標値
RECOVERY_OBJECTIVES = {
    "RTO": {  # Recovery Time Objective
        "critical_failure": "2 hours",
        "partial_failure": "30 minutes", 
        "data_corruption": "4 hours"
    },
    "RPO": {  # Recovery Point Objective  
        "critical_data": "15 minutes",
        "search_logs": "1 hour",
        "cache_data": "24 hours"
    }
}
```

## 📈 パフォーマンス最適化

### インデックス戦略
```sql
-- 複合インデックス設計
CREATE INDEX CONCURRENTLY idx_documents_search_optimized 
ON documents (source_id, processing_status, quality_score DESC)
WHERE processing_status = 'completed' AND quality_score >= 3.0;

CREATE INDEX CONCURRENTLY idx_chunks_vector_ready
ON chunks (document_id, quality_score DESC, token_count)
WHERE embedding_id IS NOT NULL;

CREATE INDEX CONCURRENTLY idx_search_logs_analytics
ON search_logs (created_at, user_id, query_type)
WHERE satisfaction_rating IS NOT NULL;

-- 部分インデックス（条件付きインデックス）
CREATE INDEX CONCURRENTLY idx_sources_active_monitoring
ON sources (last_checked, consecutive_failures)
WHERE is_active = true;

-- GINインデックス（JSONB用）
CREATE INDEX CONCURRENTLY idx_documents_metadata_gin
ON documents USING GIN (metadata_json);

CREATE INDEX CONCURRENTLY idx_chunks_metadata_gin  
ON chunks USING GIN (metadata_json);
```

### パーティショニング戦略
```sql
-- 時系列パーティショニング（検索ログ）
CREATE TABLE search_logs_partitioned (
    LIKE search_logs INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- 月次パーティション作成
CREATE TABLE search_logs_2025_01 PARTITION OF search_logs_partitioned
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE search_logs_2025_02 PARTITION OF search_logs_partitioned  
FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- ハッシュパーティショニング（チャンク）
CREATE TABLE chunks_partitioned (
    LIKE chunks INCLUDING ALL
) PARTITION BY HASH (document_id);

-- 4つのハッシュパーティション
CREATE TABLE chunks_part0 PARTITION OF chunks_partitioned
FOR VALUES WITH (modulus 4, remainder 0);

CREATE TABLE chunks_part1 PARTITION OF chunks_partitioned
FOR VALUES WITH (modulus 4, remainder 1);
```

## 🤖 Implementation Notes for AI

### Critical Implementation Paths
1. **データベーススキーマ作成**: PostgreSQL/SQLite DDL実行、制約・インデックス設定
2. **ベクトルDB初期化**: Chroma/Supabase Vector セットアップ、コレクション作成
3. **データマイグレーション**: 段階的スキーマ変更、データ移行スクリプト
4. **整合性確保**: 外部キー制約、チェック制約、トリガー実装

### Key Dependencies
- **データベース**: PostgreSQL 13+, SQLite 3.35+, Chroma DB
- **ORM**: SQLAlchemy 2.0, Alembic (マイグレーション)
- **ベクトルDB**: chromadb, sentence-transformers
- **キャッシュ**: Redis 7+, aioredis

### Testing Strategy
- **スキーマテスト**: DDL実行、制約違反テスト
- **データ整合性テスト**: 参照整合性、品質制約テスト  
- **パフォーマンステスト**: インデックス効果、クエリ最適化
- **バックアップテスト**: 復旧手順、整合性検証

### Common Pitfalls
- **文字エンコーディング**: UTF-8設定、日本語文字化け対策
- **インデックスサイズ**: 大量データ時のインデックス肥大化
- **N+1問題**: ORM使用時の効率的なクエリ設計
- **ベクトル次元**: 埋め込みモデル変更時の互換性

### 実装優先順位
1. **Phase 1**: 基本スキーマ、主要テーブル作成
2. **Phase 2**: インデックス最適化、ベクトルDB連携
3. **Phase 3**: パーティショニング、バックアップ自動化

---

**Version**: 1.0.0 | **Last Updated**: 2025-01-21 | **Next Review**: 2025-02-21