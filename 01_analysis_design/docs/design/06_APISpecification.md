# ERP知識RAGシステム - API仕様書

---
doc_type: "api_specification"
complexity: "medium"
estimated_effort: "25-35 hours"
prerequisites: ["01_PRD.md", "02_SystemArchitecture.md", "03_FunctionalRequirements.md", "05_DataModelDesign.md"]
implementation_priority: "medium"
ai_assistance_level: "full_automation_possible"
version: "1.0.0"
author: "Claude Code"
created_date: "2025-01-21"
status: "draft"
---

## 📋 API概要

### API設計原則
- **RESTful**: リソース指向、HTTP標準準拠
- **一貫性**: 命名規則、エラー処理の統一
- **バージョニング**: URL パス内でのバージョン管理
- **セキュリティ**: 認証・認可の徹底実装
- **性能**: キャッシュ、ページネーション対応
- **OpenAPI準拠**: 自動ドキュメント生成・検証対応

### 基本情報
```yaml
Base URL: https://api.erpfts.example.com/api/v1
Authentication: Bearer Token (JWT)
Content-Type: application/json
API Version: 1.0
Rate Limiting: 100 req/min/user, 1000 req/min/system
```

## 🔐 認証・セキュリティ

### 認証フロー
```yaml
OAuth 2.0 + JWT:
  1. Authorization Code Grant フロー
  2. JWT Access Token (24時間有効)
  3. Refresh Token (30日有効)
  4. PKCE (Proof Key for Code Exchange) 対応

支援プロバイダー:
  - Google: OAuth 2.0
  - Microsoft: Azure AD
  - GitHub: OAuth Apps
```

### 認証ヘッダー例
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
X-API-Version: 1.0
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

### セキュリティ設定
```yaml
CORS:
  - Allow-Origin: https://erpfts.example.com
  - Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
  - Allow-Headers: Authorization, Content-Type, X-API-Version

Rate Limiting:
  - 100 requests/minute/user (authenticated)
  - 10 requests/minute/IP (anonymous)
  - 1000 requests/minute/system (admin)

Input Validation:
  - JSON Schema validation
  - SQL injection protection
  - XSS protection
  - Request size limits: 10MB
```

## 🔍 Search API

### POST /api/v1/search
セマンティック検索・ハイブリッド検索を実行

#### Request
```json
{
  "query": "ERPプロジェクトでのリスク管理方法は？",
  "search_type": "semantic", // "semantic" | "hybrid" | "keyword"
  "filters": {
    "source_types": ["pmbok", "babok", "blog"],
    "date_range": {
      "start": "2020-01-01",
      "end": "2025-01-21"
    },
    "min_quality_score": 3.5,
    "languages": ["ja", "en"]
  },
  "limit": 10,
  "offset": 0,
  "include_content": true,
  "highlight": true
}
```

#### Response
```json
{
  "success": true,
  "query": "ERPプロジェクトでのリスク管理方法は？",
  "results": [
    {
      "id": "chunk_12345",
      "document_id": "doc_67890",
      "title": "PMBOK Guide - Risk Management",
      "content": "プロジェクトリスクの識別、分析、対応戦略...",
      "highlighted_content": "<mark>プロジェクト</mark><mark>リスク</mark>の識別、分析、対応戦略...",
      "source": {
        "id": "source_001",
        "name": "PMBOK Guide 7th Edition",
        "type": "standard_document",
        "author": "PMI",
        "url": "https://pmi.org/pmbok",
        "published_date": "2021-08-01"
      },
      "scores": {
        "similarity": 0.95,
        "quality": 4.8,
        "relevance": 0.92
      },
      "metadata": {
        "page_number": 123,
        "section": "Risk Management",
        "chunk_index": 5,
        "token_count": 512,
        "language": "ja"
      }
    }
  ],
  "pagination": {
    "total": 47,
    "limit": 10,
    "offset": 0,
    "has_more": true
  },
  "search_metadata": {
    "response_time_ms": 1250,
    "search_strategy": "hybrid",
    "vector_weight": 0.7,
    "keyword_weight": 0.3
  },
  "suggestions": [
    "リスク登録簿",
    "リスク対応計画",
    "ERP導入リスク"
  ]
}
```

### GET /api/v1/search/suggestions
検索候補・サジェスション取得

#### Request
```http
GET /api/v1/search/suggestions?q=リスク管理&limit=10
```

#### Response
```json
{
  "success": true,
  "query": "リスク管理",
  "suggestions": [
    {
      "text": "リスク管理計画",
      "score": 0.95,
      "category": "concept"
    },
    {
      "text": "リスク登録簿",
      "score": 0.88,
      "category": "document"
    }
  ]
}
```

## 🤖 RAG Answer Generation API

### POST /api/v1/answer
検索結果を基にした自然言語回答生成

#### Request
```json
{
  "question": "ERPプロジェクトでのリスク管理方法を教えて",
  "context_limit": 5,
  "response_format": "detailed", // "brief" | "detailed" | "bullet_points"
  "include_sources": true,
  "language": "ja",
  "temperature": 0.3
}
```

#### Response
```json
{
  "success": true,
  "question": "ERPプロジェクトでのリスク管理方法を教えて",
  "answer": {
    "content": "ERPプロジェクトのリスク管理では、以下の手順が重要です：\n\n1. **リスク識別**: プロジェクト初期段階で...\n2. **リスク分析**: 発生確率と影響度を...\n3. **リスク対応**: 軽減、回避、受容の...",
    "confidence": 0.89,
    "word_count": 245
  },
  "sources": [
    {
      "title": "PMBOK Guide 7版 - Risk Management",
      "author": "PMI",
      "url": "https://pmi.org/pmbok",
      "relevance": 0.95,
      "cited_sections": ["リスク識別プロセス", "リスク分析手法"]
    }
  ],
  "metadata": {
    "generation_time_ms": 3200,
    "tokens_used": 1200,
    "model_version": "gpt-4-turbo"
  }
}
```

## 📄 Document Management API

### GET /api/v1/documents
文書一覧取得

#### Request
```http
GET /api/v1/documents?source_type=pmbok&limit=20&offset=0&sort=created_at&order=desc
```

#### Response
```json
{
  "success": true,
  "documents": [
    {
      "id": "doc_12345",
      "source_id": "source_001",
      "title": "PMBOK Guide - Project Integration Management",
      "author": "PMI",
      "published_date": "2021-08-01",
      "language": "ja",
      "document_type": "standard_document",
      "quality_score": 4.8,
      "processing_status": "completed",
      "chunk_count": 156,
      "word_count": 12450,
      "created_at": "2025-01-21T10:30:00Z",
      "updated_at": "2025-01-21T11:15:00Z"
    }
  ],
  "pagination": {
    "total": 245,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

### GET /api/v1/documents/{document_id}
特定文書詳細取得

#### Response
```json
{
  "success": true,
  "document": {
    "id": "doc_12345",
    "source": {
      "id": "source_001",
      "name": "PMBOK Guide 7th Edition",
      "type": "standard_document"
    },
    "title": "Project Integration Management",
    "author": "PMI",
    "published_date": "2021-08-01",
    "last_modified": "2021-08-01T00:00:00Z",
    "language": "ja",
    "document_type": "standard_document",
    "metadata": {
      "isbn": "978-1-62825-664-2",
      "pages": 245,
      "topics": ["project_management", "integration", "coordination"]
    },
    "quality_score": 4.8,
    "processing_status": "completed",
    "chunks": [
      {
        "id": "chunk_001",
        "chunk_index": 1,
        "content": "プロジェクト統合マネジメントは...",
        "page_number": 56,
        "section_title": "統合マネジメントプロセス",
        "quality_score": 4.6,
        "token_count": 512
      }
    ],
    "statistics": {
      "total_chunks": 156,
      "avg_chunk_quality": 4.5,
      "search_count": 1245,
      "last_accessed": "2025-01-21T09:30:00Z"
    }
  }
}
```

### POST /api/v1/documents
新規文書登録

#### Request
```json
{
  "source_id": "source_001",
  "title": "Custom ERP Implementation Guide",
  "author": "Internal Team",
  "content": "ERPシステム導入に関する包括的ガイド...",
  "document_type": "internal_guide",
  "metadata": {
    "department": "IT",
    "project": "ERP2025",
    "tags": ["implementation", "training", "best_practice"]
  },
  "processing_options": {
    "auto_chunk": true,
    "generate_embeddings": true,
    "quality_check": true
  }
}
```

#### Response
```json
{
  "success": true,
  "document": {
    "id": "doc_67890",
    "title": "Custom ERP Implementation Guide",
    "processing_status": "processing",
    "estimated_completion": "2025-01-21T11:00:00Z"
  },
  "processing_job_id": "job_abc123"
}
```

## 🎯 Source Management API

### GET /api/v1/sources
データソース一覧取得

#### Response
```json
{
  "success": true,
  "sources": [
    {
      "id": "source_001",
      "name": "PMBOK Guide Official",
      "source_type": "pdf",
      "base_url": "https://pmi.org/pmbok/download",
      "is_active": true,
      "check_interval": 86400,
      "last_checked": "2025-01-21T08:00:00Z",
      "last_success_check": "2025-01-21T08:00:00Z",
      "consecutive_failures": 0,
      "quality_weight": 5.0,
      "document_count": 1,
      "status": "healthy"
    }
  ]
}
```

### POST /api/v1/sources
新規ソース登録

#### Request
```json
{
  "name": "PM Blog - Best Practices",
  "source_type": "rss",
  "base_url": "https://pmblog.example.com",
  "rss_feed": "https://pmblog.example.com/feed.xml",
  "check_interval": 3600,
  "access_config": {
    "authentication": {
      "type": "none"
    },
    "parsing_config": {
      "selectors": {
        "content": ".article-content",
        "title": "h1.title",
        "author": ".author-name"
      }
    }
  },
  "quality_weight": 3.5,
  "metadata": {
    "category": "blog",
    "topic": "project_management",
    "language": "ja"
  }
}
```

### PUT /api/v1/sources/{source_id}
ソース情報更新

### DELETE /api/v1/sources/{source_id}
ソース削除

### POST /api/v1/sources/{source_id}/refresh
手動更新実行

#### Response
```json
{
  "success": true,
  "job_id": "refresh_xyz789",
  "estimated_completion": "2025-01-21T11:30:00Z",
  "status": "started"
}
```

## 📊 Analytics & Monitoring API

### GET /api/v1/analytics/dashboard
ダッシュボード統計情報

#### Response
```json
{
  "success": true,
  "dashboard": {
    "overview": {
      "total_documents": 245,
      "total_chunks": 12450,
      "total_searches_today": 89,
      "avg_response_time_ms": 1250,
      "system_health": "healthy"
    },
    "usage_stats": {
      "daily_active_users": 23,
      "weekly_active_users": 67,
      "popular_queries": [
        {"query": "リスク管理", "count": 45},
        {"query": "プロジェクト計画", "count": 38}
      ],
      "search_satisfaction_avg": 4.2
    },
    "quality_metrics": {
      "avg_document_quality": 4.1,
      "low_quality_documents": 12,
      "pending_review": 5,
      "quality_trend": "improving"
    },
    "system_metrics": {
      "cpu_usage_percent": 45,
      "memory_usage_mb": 1024,
      "disk_usage_percent": 67,
      "active_connections": 15
    }
  },
  "last_updated": "2025-01-21T10:45:00Z"
}
```

### GET /api/v1/analytics/search-logs
検索ログ分析

#### Request
```http
GET /api/v1/analytics/search-logs?start_date=2025-01-14&end_date=2025-01-21&limit=50
```

### GET /api/v1/analytics/quality-report
品質分析レポート

#### Response
```json
{
  "success": true,
  "quality_report": {
    "overall_score": 4.1,
    "score_distribution": {
      "5.0": 89,
      "4.0-4.9": 123,
      "3.0-3.9": 45,
      "2.0-2.9": 12,
      "below_2.0": 3
    },
    "improvement_areas": [
      {
        "area": "個人ブログ記事",
        "avg_score": 2.8,
        "document_count": 34,
        "recommendation": "著者権威性の確認が必要"
      }
    ],
    "quality_trends": {
      "last_30_days": 4.1,
      "last_7_days": 4.3,
      "trend": "improving"
    }
  }
}
```

## 🔧 Admin API

### GET /api/v1/admin/system-health
システムヘルスチェック

#### Response
```json
{
  "success": true,
  "health": {
    "overall_status": "healthy",
    "components": {
      "database": {
        "status": "healthy",
        "response_time_ms": 23,
        "connections_active": 5,
        "connections_max": 50
      },
      "vector_store": {
        "status": "healthy",
        "index_size": 12450,
        "memory_usage_mb": 512
      },
      "cache": {
        "status": "healthy",
        "hit_rate": 0.85,
        "memory_usage_mb": 128
      },
      "external_services": {
        "status": "degraded",
        "failing_sources": ["source_123"],
        "last_check": "2025-01-21T10:00:00Z"
      }
    }
  }
}
```

### POST /api/v1/admin/reindex
検索インデックス再構築

#### Request
```json
{
  "target": "all", // "all" | "documents" | "chunks" | "embeddings"
  "force": false,
  "async": true
}
```

### POST /api/v1/admin/quality-check
品質チェック実行

### GET /api/v1/admin/jobs
バックグラウンドジョブ状況

#### Response
```json
{
  "success": true,
  "jobs": [
    {
      "id": "job_123",
      "type": "document_processing",
      "status": "running",
      "progress": 0.65,
      "started_at": "2025-01-21T10:15:00Z",
      "estimated_completion": "2025-01-21T10:45:00Z",
      "metadata": {
        "document_id": "doc_456",
        "total_chunks": 100,
        "processed_chunks": 65
      }
    }
  ]
}
```

## 👤 User Management API

### GET /api/v1/users/profile
現在ユーザーのプロファイル取得

#### Response
```json
{
  "success": true,
  "user": {
    "id": "user_123",
    "email": "consultant@example.com",
    "display_name": "田中太郎",
    "role": "editor",
    "preferences": {
      "ui_language": "ja",
      "results_per_page": 10,
      "search_filters": {
        "default_sources": ["pmbok", "babok"],
        "min_quality_score": 3.5
      }
    },
    "usage_stats": {
      "total_searches": 245,
      "avg_satisfaction": 4.2,
      "favorite_topics": ["risk_management", "project_planning"]
    },
    "last_login": "2025-01-21T09:00:00Z",
    "created_at": "2024-12-01T00:00:00Z"
  }
}
```

### PUT /api/v1/users/profile
ユーザープロファイル更新

#### Request
```json
{
  "display_name": "田中太郎",
  "preferences": {
    "ui_language": "ja",
    "results_per_page": 20,
    "search_filters": {
      "default_sources": ["pmbok", "babok", "blog"],
      "min_quality_score": 4.0
    }
  }
}
```

### POST /api/v1/users/feedback
フィードバック送信

#### Request
```json
{
  "search_id": "search_789",
  "rating": 4,
  "comment": "検索結果は有用でしたが、もう少し具体的な事例があると良い",
  "useful_sources": ["source_001", "source_002"],
  "improvement_suggestions": [
    "実装事例の追加",
    "図表の説明強化"
  ]
}
```

## 🔄 Webhook API

### POST /api/v1/webhooks/github
GitHub webhook (ソース更新通知)

### POST /api/v1/webhooks/rss
RSS更新通知

### GET /api/v1/webhooks/test
Webhook疎通確認

## ❌ エラーレスポンス

### 標準エラーフォーマット
```json
{
  "success": false,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "指定されたクエリは無効です",
    "details": "クエリは1文字以上、1000文字以下である必要があります",
    "timestamp": "2025-01-21T10:30:00Z",
    "request_id": "req_12345"
  },
  "validation_errors": [
    {
      "field": "query",
      "message": "必須フィールドです",
      "code": "REQUIRED"
    }
  ]
}
```

### エラーコード一覧
```yaml
4xx Client Errors:
  400: BAD_REQUEST - 不正なリクエスト
  401: UNAUTHORIZED - 認証が必要
  403: FORBIDDEN - アクセス権限なし
  404: NOT_FOUND - リソースが存在しない
  409: CONFLICT - 重複・競合エラー
  422: UNPROCESSABLE_ENTITY - バリデーションエラー
  429: TOO_MANY_REQUESTS - レート制限超過

5xx Server Errors:
  500: INTERNAL_SERVER_ERROR - サーバー内部エラー
  502: BAD_GATEWAY - 外部サービスエラー
  503: SERVICE_UNAVAILABLE - サービス一時停止
  504: GATEWAY_TIMEOUT - タイムアウト

カスタムエラーコード:
  SEARCH_ENGINE_ERROR - 検索エンジンエラー
  EMBEDDING_GENERATION_FAILED - 埋め込み生成失敗
  QUALITY_CHECK_FAILED - 品質チェック失敗
  SOURCE_CONNECTION_FAILED - ソース接続失敗
```

## 📝 実装例・SDKサンプル

### Python SDK例
```python
import requests
from typing import List, Dict, Optional

class ERPFTSClient:
    def __init__(self, api_key: str, base_url: str = "https://api.erpfts.example.com/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def search(self, query: str, **kwargs) -> Dict:
        """セマンティック検索実行"""
        payload = {"query": query, **kwargs}
        response = self.session.post(f"{self.base_url}/search", json=payload)
        response.raise_for_status()
        return response.json()
    
    def generate_answer(self, question: str, **kwargs) -> Dict:
        """RAG回答生成"""
        payload = {"question": question, **kwargs}
        response = self.session.post(f"{self.base_url}/answer", json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_documents(self, limit: int = 20, **filters) -> Dict:
        """文書一覧取得"""
        params = {"limit": limit, **filters}
        response = self.session.get(f"{self.base_url}/documents", params=params)
        response.raise_for_status()
        return response.json()

# 使用例
client = ERPFTSClient("your-api-key")

# 検索実行
results = client.search(
    query="ERPプロジェクトのリスク管理",
    limit=10,
    filters={"min_quality_score": 4.0}
)

# 回答生成
answer = client.generate_answer(
    question="リスク管理の具体的手順を教えて",
    response_format="detailed"
)
```

### JavaScript/TypeScript SDK例
```javascript
class ERPFTSClient {
    constructor(apiKey, baseURL = 'https://api.erpfts.example.com/api/v1') {
        this.apiKey = apiKey;
        this.baseURL = baseURL;
    }

    async search(query, options = {}) {
        const response = await fetch(`${this.baseURL}/search`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query, ...options })
        });
        
        if (!response.ok) {
            throw new Error(`Search failed: ${response.statusText}`);
        }
        
        return await response.json();
    }

    async generateAnswer(question, options = {}) {
        const response = await fetch(`${this.baseURL}/answer`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question, ...options })
        });
        
        return await response.json();
    }
}

// 使用例
const client = new ERPFTSClient('your-api-key');

const results = await client.search('ERPプロジェクトのリスク管理', {
    limit: 10,
    filters: { min_quality_score: 4.0 }
});

const answer = await client.generateAnswer('リスク管理の具体的手順を教えて');
```

## 🤖 Implementation Notes for AI

### Critical Implementation Paths
1. **FastAPI フレームワーク**: async/await対応、高性能API実装
2. **JWT認証**: 認証ミドルウェア、トークン検証・更新
3. **バリデーション**: Pydantic models、リクエスト検証
4. **エラーハンドリング**: 統一エラーレスポンス、ロギング

### Key Dependencies
- **FastAPI**: 高性能非同期Webフレームワーク
- **Pydantic**: データバリデーション・シリアライゼーション
- **SQLAlchemy**: ORM、データベースアクセス
- **Authlib**: OAuth 2.0 + JWT実装
- **httpx**: 非同期HTTP客户端（外部API連携用）

### Testing Strategy
- **単体テスト**: 各エンドポイントの独立テスト
- **統合テスト**: データベース込みのE2Eテスト
- **負荷テスト**: locust による API性能テスト
- **セキュリティテスト**: 認証・認可・入力検証

### Common Pitfalls
- **非同期処理**: async/awaitの適切な使用
- **認証スコープ**: 細かい権限制御の実装
- **レート制限**: Redis等を使った分散レート制限
- **エラー情報**: セキュリティを考慮した適切なエラー情報開示

### 実装優先順位
1. **Phase 1**: 基本検索API、文書管理API
2. **Phase 2**: RAG生成API、分析API、管理API
3. **Phase 3**: Webhook、高度な分析機能

---

**Version**: 1.0.0 | **Last Updated**: 2025-01-21 | **Next Review**: 2025-02-21