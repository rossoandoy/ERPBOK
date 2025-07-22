# ERP知識RAGシステム - コーディング規約・Git運用ルール

---
doc_type: "coding_standards"
complexity: "low"
estimated_effort: "20-30 hours"
prerequisites: ["00_ProjectCharter.md", "08_DocumentManagementSystem.md", "09_ImplementationPlan.md"]
implementation_priority: "low"
ai_assistance_level: "full_automation_possible"
version: "1.0.0"
author: "Claude Code"
created_date: "2025-01-21"
status: "approved"
approval_authority: "Development Team"
---

## 📋 コーディング規約・Git運用概要

### 規約の目的
本文書は「ERP知識RAGシステム（ERPFTS）」開発における統一的なコーディング規約、Git ワークフロー、コードレビュー基準を定義する。チーム全体での一貫性あるコード品質、保守性向上、効率的な協業を実現するための実践的ガイドラインを提供する。

### 基本方針
```yaml
コード品質原則:
  可読性: 誰が読んでも理解しやすいコード
  保守性: 変更・拡張が容易なコード構造
  テスタビリティ: テストしやすい設計・実装
  一貫性: チーム全体で統一されたスタイル

開発効率原則:
  自動化: リント・フォーマット・テストの自動化
  標準化: 共通ツール・ライブラリの使用
  ドキュメント化: コード・設計意図の明確化
  継続改善: 規約・プロセスの定期見直し
```

## 🐍 Python コーディング規約

### 基本スタイル
```python
"""
Python コーディング規約 - 基本スタイル
ベース: PEP 8 + Black formatter + 追加ルール
"""

# ===== インポート規約 =====
# 1. 標準ライブラリ
import asyncio
import datetime
import logging
from typing import Dict, List, Optional, Union

# 2. サードパーティライブラリ
import fastapi
import sqlalchemy
from pydantic import BaseModel, Field

# 3. プロジェクト内モジュール
from erpfts.core.config import settings
from erpfts.models.document import Document
from erpfts.services.search import SearchService


# ===== 命名規約 =====
class DocumentSearchService:
    """クラス名: PascalCase (大文字始まりのキャメルケース)"""
    
    def __init__(self, search_engine: SearchEngine):
        """
        コンストラクタ
        
        Args:
            search_engine: 検索エンジンインスタンス
        """
        self._search_engine = search_engine  # プライベート: アンダースコア
        self.max_results = 50  # パブリック: snake_case
        
    async def search_documents(
        self, 
        query: str, 
        *, 
        limit: int = 10,
        quality_threshold: float = 3.0
    ) -> List[Document]:
        """
        文書検索実行
        
        Args:
            query: 検索クエリ
            limit: 結果件数上限（keyword-only引数）
            quality_threshold: 品質スコア閾値
            
        Returns:
            検索結果文書リスト
            
        Raises:
            SearchError: 検索処理エラー時
        """
        # 関数名: snake_case
        if not query.strip():
            raise ValueError("Search query cannot be empty")
            
        # 定数: UPPER_SNAKE_CASE
        MAX_QUERY_LENGTH = 500
        if len(query) > MAX_QUERY_LENGTH:
            query = query[:MAX_QUERY_LENGTH]
            
        results = await self._search_engine.search(
            query=query,
            limit=limit,
            filters={"quality_score": {"$gte": quality_threshold}}
        )
        
        return [Document.from_dict(result) for result in results]


# ===== 型ヒント規約 =====
from typing import Any, Dict, List, Optional, Protocol, TypeVar, Union

# 型エイリアス定義
SearchResult = Dict[str, Any]
DocumentID = str
QualityScore = float

# プロトコル定義（インターフェース）
class SearchableEngine(Protocol):
    """検索エンジンプロトコル"""
    
    async def search(
        self, 
        query: str, 
        *, 
        limit: int = 10
    ) -> List[SearchResult]:
        """検索実行"""
        ...

# 型変数定義
T = TypeVar('T', bound='BaseModel')

class SearchResponse(BaseModel):
    """
    検索レスポンスモデル
    
    Attributes:
        results: 検索結果リスト
        total_count: 総件数
        response_time: レスポンス時間（秒）
    """
    results: List[Document]
    total_count: int = Field(..., description="検索結果総件数")
    response_time: float = Field(..., ge=0, description="レスポンス時間（秒）")
    
    @classmethod
    def create_empty(cls) -> "SearchResponse":
        """空の検索レスポンス生成"""
        return cls(
            results=[],
            total_count=0,
            response_time=0.0
        )


# ===== エラーハンドリング規約 =====
class ERPFTSError(Exception):
    """ERPFTS 基底例外クラス"""
    
    def __init__(self, message: str, *, error_code: str = None):
        super().__init__(message)
        self.error_code = error_code
        self.timestamp = datetime.datetime.now()

class SearchError(ERPFTSError):
    """検索関連エラー"""
    pass

class DataQualityError(ERPFTSError):
    """データ品質関連エラー"""
    pass

async def safe_search_execution(
    search_func: Callable,
    query: str,
    *,
    max_retries: int = 3
) -> SearchResponse:
    """
    安全な検索実行（リトライ機能付き）
    
    Args:
        search_func: 検索関数
        query: 検索クエリ
        max_retries: 最大リトライ回数
        
    Returns:
        検索結果
        
    Raises:
        SearchError: リトライ上限到達時
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            return await search_func(query)
        except SearchError as e:
            last_error = e
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)  # 指数バックオフ
                continue
            break
        except Exception as e:
            # 予期しないエラーは即座に再発生
            raise SearchError(f"Unexpected search error: {str(e)}") from e
    
    raise SearchError(f"Search failed after {max_retries} retries") from last_error


# ===== ログ規約 =====
import logging
import structlog

# 構造化ログ設定
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

class SearchService:
    """検索サービス - ログ使用例"""
    
    async def search(self, query: str) -> SearchResponse:
        """検索実行（ログ出力例）"""
        # 処理開始ログ
        logger.info(
            "search_started",
            query=query,
            user_id=self.current_user_id,
            session_id=self.session_id
        )
        
        try:
            start_time = time.time()
            results = await self._execute_search(query)
            response_time = time.time() - start_time
            
            # 成功ログ
            logger.info(
                "search_completed",
                query=query,
                result_count=len(results),
                response_time=response_time,
                user_id=self.current_user_id
            )
            
            return SearchResponse(
                results=results,
                total_count=len(results),
                response_time=response_time
            )
            
        except SearchError as e:
            # エラーログ
            logger.error(
                "search_failed",
                query=query,
                error_code=e.error_code,
                error_message=str(e),
                user_id=self.current_user_id,
                exc_info=True
            )
            raise
        
        except Exception as e:
            # 予期しないエラーログ
            logger.critical(
                "search_unexpected_error",
                query=query,
                error_type=type(e).__name__,
                error_message=str(e),
                user_id=self.current_user_id,
                exc_info=True
            )
            raise SearchError("Internal search error") from e
```

### テストコード規約
```python
"""
テストコード規約・ベストプラクティス
フレームワーク: pytest + pytest-asyncio
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator

from erpfts.services.search import SearchService
from erpfts.models.document import Document


# ===== テストフィクスチャ =====
@pytest.fixture
async def search_service() -> AsyncGenerator[SearchService, None]:
    """検索サービステストフィクスチャ"""
    # セットアップ
    mock_engine = AsyncMock()
    service = SearchService(search_engine=mock_engine)
    
    # テスト実行
    yield service
    
    # クリーンアップ
    await service.cleanup()

@pytest.fixture
def sample_documents() -> List[Document]:
    """サンプル文書フィクスチャ"""
    return [
        Document(
            id="doc_001",
            title="プロジェクト管理の基礎",
            content="プロジェクト管理の基本的な概念...",
            quality_score=4.2
        ),
        Document(
            id="doc_002", 
            title="リスク管理手法",
            content="リスク管理の実践的アプローチ...",
            quality_score=4.5
        )
    ]


# ===== テストクラス・関数 =====
class TestSearchService:
    """検索サービステストクラス"""
    
    @pytest.mark.asyncio
    async def test_search_success(
        self, 
        search_service: SearchService,
        sample_documents: List[Document]
    ):
        """正常検索テスト"""
        # Arrange
        query = "プロジェクト管理"
        expected_results = sample_documents[:1]
        
        search_service._search_engine.search.return_value = [
            doc.dict() for doc in expected_results
        ]
        
        # Act
        response = await search_service.search_documents(query)
        
        # Assert
        assert len(response) == 1
        assert response[0].title == "プロジェクト管理の基礎"
        search_service._search_engine.search.assert_called_once_with(
            query=query,
            limit=10,
            filters={"quality_score": {"$gte": 3.0}}
        )
    
    @pytest.mark.asyncio
    async def test_search_empty_query(self, search_service: SearchService):
        """空クエリエラーテスト"""
        # Act & Assert
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            await search_service.search_documents("")
    
    @pytest.mark.asyncio
    async def test_search_engine_error(self, search_service: SearchService):
        """検索エンジンエラーテスト"""
        # Arrange
        search_service._search_engine.search.side_effect = SearchError(
            "Engine connection failed",
            error_code="ENGINE_ERROR"
        )
        
        # Act & Assert
        with pytest.raises(SearchError) as exc_info:
            await search_service.search_documents("test query")
        
        assert exc_info.value.error_code == "ENGINE_ERROR"
    
    @pytest.mark.parametrize("query,limit,expected_calls", [
        ("test", 5, 1),
        ("project management", 20, 1),
        ("risk", 1, 1),
    ])
    @pytest.mark.asyncio
    async def test_search_parameterized(
        self,
        search_service: SearchService,
        query: str,
        limit: int,
        expected_calls: int
    ):
        """パラメータ化テスト"""
        # Arrange
        search_service._search_engine.search.return_value = []
        
        # Act
        await search_service.search_documents(query, limit=limit)
        
        # Assert
        assert search_service._search_engine.search.call_count == expected_calls


# ===== モック・パッチ規約 =====
class TestDataIngestion:
    """データ取り込みテスト - モック使用例"""
    
    @patch('erpfts.services.ingestion.ChromaDBClient')
    @patch('erpfts.services.ingestion.EmbeddingModel')
    @pytest.mark.asyncio
    async def test_document_ingestion_with_mocks(
        self,
        mock_embedding_model,
        mock_chroma_client
    ):
        """外部依存をモックしたテスト"""
        # Arrange
        mock_embeddings = [[0.1, 0.2, 0.3] * 100]  # 300次元ベクトル
        mock_embedding_model.return_value.encode.return_value = mock_embeddings
        
        mock_collection = MagicMock()
        mock_chroma_client.return_value.get_collection.return_value = mock_collection
        
        from erpfts.services.ingestion import DocumentIngestionService
        service = DocumentIngestionService()
        
        # Act
        result = await service.ingest_document("test document content")
        
        # Assert
        assert result.success is True
        mock_embedding_model.return_value.encode.assert_called_once()
        mock_collection.add.assert_called_once()


# ===== テストデータ管理 =====
@pytest.fixture(scope="session")
def test_database():
    """テスト用データベースセットアップ"""
    # テスト用SQLiteデータベース作成
    test_db_url = "sqlite:///test_erpfts.db"
    
    # テーブル作成・初期データ投入
    setup_test_database(test_db_url)
    
    yield test_db_url
    
    # テスト後クリーンアップ
    cleanup_test_database(test_db_url)

def setup_test_database(db_url: str):
    """テストデータベース初期化"""
    # スキーマ作成
    # テストデータ投入
    pass

def cleanup_test_database(db_url: str):
    """テストデータベースクリーンアップ"""
    # ファイル削除等
    pass
```

## 🌐 JavaScript/TypeScript 規約

### 基本スタイル
```typescript
/**
 * TypeScript/JavaScript コーディング規約
 * ベース: ESLint + Prettier + TypeScript strict mode
 */

// ===== インポート規約 =====
// 1. Node.js標準モジュール
import { promises as fs } from 'fs';
import path from 'path';

// 2. サードパーティライブラリ
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { z } from 'zod';

// 3. プロジェクト内モジュール
import { SearchService } from '../services/SearchService';
import type { Document, SearchResult } from '../types/document';
import { API_ENDPOINTS } from '../config/constants';

// ===== 型定義規約 =====
// インターフェース: PascalCase
interface SearchRequest {
  readonly query: string;
  readonly limit?: number;
  readonly filters?: SearchFilters;
}

// 型エイリアス: PascalCase
type DocumentId = string;
type QualityScore = number;

// 列挙型: PascalCase
enum SearchResultType {
  SEMANTIC = 'semantic',
  KEYWORD = 'keyword',
  HYBRID = 'hybrid',
}

// ユニオン型
type SearchStatus = 'idle' | 'loading' | 'success' | 'error';

// 型ガード
function isValidDocument(obj: unknown): obj is Document {
  return typeof obj === 'object' && 
         obj !== null && 
         'id' in obj && 
         'title' in obj;
}

// ===== 関数・クラス規約 =====
class DocumentSearchService {
  private readonly apiClient: axios.AxiosInstance;
  private readonly maxRetries = 3;
  
  constructor(
    private readonly baseUrl: string,
    private readonly apiKey: string
  ) {
    this.apiClient = axios.create({
      baseURL: baseUrl,
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      timeout: 10000,
    });
  }
  
  /**
   * 文書検索実行
   * @param request - 検索リクエスト
   * @returns 検索結果
   * @throws {SearchError} 検索エラー時
   */
  async searchDocuments(request: SearchRequest): Promise<SearchResult> {
    this.validateRequest(request);
    
    try {
      const response = await this.apiClient.post<SearchResult>(
        API_ENDPOINTS.SEARCH,
        request
      );
      
      return this.validateResponse(response.data);
    } catch (error) {
      throw new SearchError(
        `Search failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        { originalError: error }
      );
    }
  }
  
  private validateRequest(request: SearchRequest): void {
    if (!request.query?.trim()) {
      throw new ValidationError('Search query is required');
    }
    
    if (request.limit !== undefined && request.limit <= 0) {
      throw new ValidationError('Limit must be positive');
    }
  }
  
  private validateResponse(data: unknown): SearchResult {
    // Zodスキーマバリデーション
    return SearchResultSchema.parse(data);
  }
}

// ===== React Hooks規約 =====
/**
 * 検索フック
 * @param initialQuery - 初期検索クエリ
 * @returns 検索状態・実行関数
 */
function useDocumentSearch(initialQuery = ''): {
  query: string;
  results: Document[];
  status: SearchStatus;
  error: string | null;
  search: (query: string) => Promise<void>;
  setQuery: (query: string) => void;
} {
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<Document[]>([]);
  const [status, setStatus] = useState<SearchStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  
  const searchService = useMemo(
    () => new DocumentSearchService(
      process.env.REACT_APP_API_URL!,
      process.env.REACT_APP_API_KEY!
    ),
    []
  );
  
  const search = useCallback(async (searchQuery: string): Promise<void> => {
    if (!searchQuery.trim()) {
      setError('Search query cannot be empty');
      return;
    }
    
    setStatus('loading');
    setError(null);
    
    try {
      const result = await searchService.searchDocuments({
        query: searchQuery,
        limit: 20,
      });
      
      setResults(result.documents);
      setStatus('success');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Search failed';
      setError(errorMessage);
      setStatus('error');
    }
  }, [searchService]);
  
  return {
    query,
    results,
    status,
    error,
    search,
    setQuery,
  };
}

// ===== バリデーション規約 =====
import { z } from 'zod';

// Zodスキーマ定義
const DocumentSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  content: z.string(),
  qualityScore: z.number().min(0).max(5),
  publishedDate: z.string().datetime().optional(),
  tags: z.array(z.string()).default([]),
});

const SearchResultSchema = z.object({
  documents: z.array(DocumentSchema),
  totalCount: z.number().int().min(0),
  responseTime: z.number().min(0),
  query: z.string(),
});

// 型推論
type Document = z.infer<typeof DocumentSchema>;
type SearchResult = z.infer<typeof SearchResultSchema>;

// バリデーション関数
function validateDocument(data: unknown): Document {
  return DocumentSchema.parse(data);
}

// ===== エラーハンドリング規約 =====
abstract class ERPFTSError extends Error {
  abstract readonly code: string;
  
  constructor(
    message: string,
    public readonly metadata: Record<string, unknown> = {}
  ) {
    super(message);
    this.name = this.constructor.name;
  }
}

class SearchError extends ERPFTSError {
  readonly code = 'SEARCH_ERROR';
}

class ValidationError extends ERPFTSError {
  readonly code = 'VALIDATION_ERROR';
}

class NetworkError extends ERPFTSError {
  readonly code = 'NETWORK_ERROR';
}

// エラーハンドリング関数
function handleApiError(error: unknown): never {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 429) {
      throw new NetworkError('Rate limit exceeded', {
        retryAfter: error.response.headers['retry-after'],
      });
    }
    
    if (error.response?.status >= 500) {
      throw new NetworkError('Server error', {
        status: error.response.status,
        statusText: error.response.statusText,
      });
    }
    
    throw new SearchError(
      error.response?.data?.message || 'API request failed',
      { status: error.response?.status }
    );
  }
  
  if (error instanceof Error) {
    throw new SearchError(error.message, { originalError: error });
  }
  
  throw new SearchError('Unknown error occurred');
}
```

## 📝 ドキュメント規約

### コメント・JSDoc規約
```python
"""
ドキュメント規約 - Python docstring
Google Style docstring形式を採用
"""

class DocumentProcessor:
    """
    文書処理クラス
    
    PDF、HTML、テキストファイルの処理を行い、
    チャンク分割・品質評価・埋め込み生成を実行する。
    
    Attributes:
        chunk_size: チャンクサイズ（トークン数）
        chunk_overlap: チャンク重複サイズ
        quality_threshold: 品質スコア閾値
        
    Example:
        >>> processor = DocumentProcessor(chunk_size=512)
        >>> result = await processor.process_document("sample.pdf")
        >>> print(f"処理完了: {result.chunk_count}チャンク生成")
    """
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        quality_threshold: float = 3.0
    ):
        """
        文書処理器初期化
        
        Args:
            chunk_size: チャンクサイズ（デフォルト: 512トークン）
            chunk_overlap: チャンク間重複サイズ（デフォルト: 50トークン）
            quality_threshold: 品質評価閾値（デフォルト: 3.0）
            
        Raises:
            ValueError: パラメータが無効な場合
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
            
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.quality_threshold = quality_threshold
    
    async def process_document(
        self,
        file_path: str,
        *,
        extract_metadata: bool = True,
        generate_embeddings: bool = True
    ) -> ProcessingResult:
        """
        文書処理実行
        
        指定されたファイルを読み込み、テキスト抽出・チャンク分割・
        品質評価・埋め込み生成を実行する。
        
        Args:
            file_path: 処理対象ファイルパス
            extract_metadata: メタデータ抽出実行フラグ
            generate_embeddings: 埋め込み生成実行フラグ
            
        Returns:
            ProcessingResult: 処理結果オブジェクト
                - chunks: 生成されたチャンクリスト
                - metadata: 抽出されたメタデータ
                - quality_scores: 品質評価結果
                - embeddings: 生成された埋め込み（生成時のみ）
                
        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ProcessingError: 文書処理エラー時
            
        Example:
            >>> result = await processor.process_document(
            ...     "document.pdf",
            ...     extract_metadata=True,
            ...     generate_embeddings=True
            ... )
            >>> print(f"チャンク数: {len(result.chunks)}")
            >>> print(f"平均品質: {result.average_quality_score}")
        """
        # 実装省略
        pass
        
    def _extract_text_from_pdf(self, file_path: str) -> str:
        """
        PDFからテキスト抽出
        
        Args:
            file_path: PDFファイルパス
            
        Returns:
            抽出されたテキスト
            
        Note:
            PyPDF2を使用してテキスト抽出を実行。
            OCR機能は含まない（将来拡張予定）。
        """
        # 実装省略
        pass


# TypeScript JSDoc規約
/**
 * 検索サービスクラス
 * 
 * ERP知識ベースに対するセマンティック検索・キーワード検索を提供。
 * レスポンス時間最適化・結果品質向上のための機能を含む。
 * 
 * @example
 * ```typescript
 * const service = new SearchService(config);
 * const results = await service.search({
 *   query: "プロジェクト管理",
 *   limit: 10
 * });
 * console.log(`${results.totalCount}件の結果`);
 * ```
 */
class SearchService {
  /**
   * 検索サービス初期化
   * 
   * @param config - サービス設定
   * @param config.apiUrl - API ベースURL
   * @param config.apiKey - 認証APIキー
   * @param config.timeout - リクエストタイムアウト（ミリ秒）
   * @throws {ConfigurationError} 設定が無効な場合
   */
  constructor(config: SearchConfig) {
    // 実装省略
  }
  
  /**
   * 文書検索実行
   * 
   * 指定されたクエリに対してセマンティック検索を実行し、
   * 関連度順にソートされた結果を返す。
   * 
   * @param request - 検索リクエスト
   * @param request.query - 検索クエリ（必須）
   * @param request.limit - 結果件数上限（デフォルト: 10）
   * @param request.filters - 検索フィルタ
   * @returns 検索結果プロミス
   * @throws {ValidationError} リクエストが無効な場合
   * @throws {SearchError} 検索処理エラー時
   * 
   * @example
   * ```typescript
   * const result = await service.search({
   *   query: "リスク管理手法",
   *   limit: 20,
   *   filters: { qualityScore: { min: 4.0 } }
   * });
   * ```
   */
  async search(request: SearchRequest): Promise<SearchResult> {
    // 実装省略
  }
}
```

## 🔀 Git ワークフロー

### ブランチ戦略
```yaml
Git Flow モデル採用:

メインブランチ:
  main (master):
    - 本番環境デプロイ用
    - タグ付けによるバージョン管理
    - 直接コミット禁止（PR必須）
    
  develop:
    - 開発統合ブランチ
    - フィーチャーブランチの統合先
    - 安定版のみマージ

サポートブランチ:
  feature/{機能名}:
    - 新機能開発用
    - develop から分岐
    - develop へマージ
    - 例: feature/semantic-search-improvement
    
  bugfix/{バグ名}:
    - バグ修正用  
    - develop から分岐
    - develop へマージ
    - 例: bugfix/search-timeout-issue
    
  hotfix/{修正名}:
    - 緊急修正用
    - main から分岐
    - main と develop へマージ
    - 例: hotfix/security-vulnerability-fix
    
  release/{バージョン}:
    - リリース準備用
    - develop から分岐
    - main と develop へマージ
    - 例: release/v1.2.0
```

### ブランチ命名規約
```bash
# ブランチ命名パターン
# {type}/{scope}-{description}

# 機能開発
feature/search-performance-optimization
feature/user-authentication-oauth
feature/document-quality-scoring

# バグ修正  
bugfix/search-result-pagination
bugfix/memory-leak-document-processing
bugfix/api-rate-limiting-error

# 緊急修正
hotfix/security-xss-vulnerability
hotfix/database-connection-timeout
hotfix/critical-search-failure

# リリース
release/v1.0.0
release/v1.1.0-beta

# 実験・調査
experiment/new-embedding-model
experiment/hybrid-search-algorithm
spike/performance-investigation
```

### コミット規約
```bash
# Conventional Commits 形式採用
# {type}({scope}): {description}
# 
# {body}
# 
# {footer}

# 基本的なコミット例
feat(search): セマンティック検索機能を追加

ユーザーが自然言語でクエリを入力すると、
関連する文書をベクトル類似度で検索する機能を実装。

- multilingual-e5-largeモデルを使用
- ChromaDBとの連携実装  
- レスポンス時間3秒以内を達成

Closes #123

# その他のコミット例
fix(api): 検索APIのタイムアウトエラーを修正

refactor(database): データベース接続処理をリファクタリング

docs(readme): インストール手順を更新

test(search): 検索機能のユニットテストを追加

style(format): コードフォーマットを統一（Black適用）

perf(search): 検索インデックス最適化で30%高速化

chore(deps): 依存ライブラリを最新版に更新

# type種別
feat:     新機能追加
fix:      バグ修正
docs:     ドキュメント更新
style:    コードスタイル変更（機能変更なし）
refactor: リファクタリング
perf:     性能改善
test:     テスト追加・修正
chore:    ビルド・設定変更
```

### Pull Request 規約
```markdown
# プルリクエストテンプレート

## 📋 変更概要
<!-- 変更内容を簡潔に説明 -->

## 🎯 関連Issue
<!-- 関連するIssue番号を記載 -->
Closes #123
Related to #456

## 📝 変更詳細
<!-- 具体的な変更内容を箇条書きで -->
- [ ] 新機能A を実装
- [ ] バグB を修正
- [ ] パフォーマンス改善C を適用
- [ ] テストD を追加

## 🧪 テスト
<!-- テスト実行結果・確認事項 -->
- [ ] ユニットテスト追加・実行
- [ ] 統合テスト実行
- [ ] 手動テスト実行
- [ ] パフォーマンステスト実行

### テスト結果
```bash
$ pytest tests/
======================== 25 passed in 3.45s ========================

$ pytest tests/integration/
======================== 8 passed in 12.34s ========================
```

## 📊 パフォーマンス影響
<!-- パフォーマンスへの影響がある場合 -->
- レスポンス時間: 3.2s → 2.1s（34%改善）
- メモリ使用量: 512MB → 380MB（26%削減）

## 🔒 セキュリティ考慮
<!-- セキュリティ関連の変更がある場合 -->
- [ ] 入力値検証強化
- [ ] 認証・認可確認
- [ ] 機密情報漏洩チェック

## 📖 ドキュメント更新
<!-- ドキュメント更新の必要性 -->
- [ ] API仕様書更新
- [ ] ユーザーマニュアル更新
- [ ] 運用手順書更新

## ⚠️ 注意事項
<!-- 特別な注意事項・デプロイ時の考慮点 -->
- データベースマイグレーション必要
- 環境変数 `NEW_CONFIG_VALUE` の設定必要
- キャッシュクリアが必要

## 📸 スクリーンショット
<!-- UI変更がある場合のスクリーンショット -->

## ✅ チェックリスト
- [ ] コードレビュー要求項目確認
- [ ] テストカバレッジ80%以上
- [ ] ドキュメント更新完了
- [ ] CI/CDパイプライン通過
- [ ] セキュリティチェック完了
```

## 🔍 コードレビュー規約

### レビュー観点
```yaml
必須確認項目:

機能・ロジック:
  □ 要件通りの機能実装
  □ エッジケース・エラーハンドリング
  □ パフォーマンス影響確認
  □ セキュリティ脆弱性チェック

コード品質:
  □ 可読性・保守性
  □ 命名規約準拠
  □ 重複コード排除
  □ 適切な設計パターン使用

テスト:
  □ テストケース充実度
  □ テストカバレッジ基準達成
  □ テストの可読性・保守性

ドキュメント:
  □ コメント・docstring充実
  □ API仕様更新
  □ README・手順書更新
```

### レビューコメント例
```markdown
# 良いコメント例

## 提案・改善案
```python
# 現在のコード
if len(results) > 0:
    return results[0]
return None

# 提案: より簡潔で意図が明確
return results[0] if results else None
```

## 質問・確認
`timeout` の値が30秒に設定されていますが、
これは本番環境での実測値に基づいていますか？
外部APIの応答時間によってはもう少し長くても良いかもしれません。

## セキュリティ指摘
```python
# 現在のコード（問題あり）
query = f"SELECT * FROM documents WHERE title = '{user_input}'"

# 修正提案: SQLインジェクション対策
query = "SELECT * FROM documents WHERE title = %s"
cursor.execute(query, (user_input,))
```

## パフォーマンス指摘
この処理は文書数が増加すると O(n²) になりそうです。
インデックスの使用やアルゴリズムの見直しを検討してください。

## ナイスコード！
エラーハンドリングが丁寧で、ログも充実していて素晴らしいです！
特に retry ロジックが実装されているのが良いですね。
```

## 🛠️ 開発環境・ツール設定

### Python開発環境
```python
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
line_length = 88

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[tool.pytest.ini_options]
minversion = "6.0"
addopts = "-ra -q --strict-markers --cov=erpfts --cov-report=term-missing --cov-report=html"
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]

[tool.coverage.run]
source = ["erpfts"]
omit = [
    "*/tests/*",
    "*/test_*",
    "*/__pycache__/*",
    "*/migrations/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if self.debug:",
    "if settings.DEBUG",
    "raise AssertionError",
    "raise NotImplementedError",
    "if 0:",
    "if __name__ == .__main__.:",
]
```

### JavaScript/TypeScript環境
```json
// .eslintrc.json
{
  "extends": [
    "eslint:recommended",
    "@typescript-eslint/recommended",
    "@typescript-eslint/recommended-requiring-type-checking",
    "prettier"
  ],
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "ecmaVersion": 2022,
    "sourceType": "module",
    "project": "./tsconfig.json"
  },
  "plugins": ["@typescript-eslint"],
  "rules": {
    "@typescript-eslint/no-unused-vars": "error",
    "@typescript-eslint/explicit-function-return-type": "warn",
    "@typescript-eslint/no-explicit-any": "warn",
    "@typescript-eslint/prefer-const": "error",
    "prefer-const": "off",
    "no-var": "error"
  },
  "env": {
    "browser": true,
    "node": true,
    "es2022": true
  }
}

// .prettierrc
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 80,
  "tabWidth": 2,
  "useTabs": false
}

// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM"],
    "module": "ESNext",
    "moduleResolution": "node",
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noImplicitOverride": true,
    "exactOptionalPropertyTypes": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

### VS Code設定
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.sortImports.args": ["--profile", "black"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "files.associations": {
    "*.py": "python"
  },
  "[python]": {
    "editor.rulers": [88],
    "editor.tabSize": 4
  },
  "[typescript]": {
    "editor.rulers": [80],
    "editor.tabSize": 2,
    "editor.formatOnSave": true
  },
  "[json]": {
    "editor.tabSize": 2
  }
}

// .vscode/extensions.json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "ms-python.isort",
    "ms-python.mypy-type-checker",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint"
  ]
}
```

## 🤖 Implementation Notes for AI

### Critical Implementation Paths
1. **コード品質自動化**: Linter・Formatter・テストの CI/CD 統合
2. **Git ワークフロー**: ブランチ戦略・コミット規約・PR テンプレート実装
3. **レビュープロセス**: コードレビューチェックリスト・自動品質チェック
4. **開発環境**: 統一された開発環境・ツール設定の標準化

### Key Dependencies
- **Python**: Black, isort, mypy, pytest, flake8
- **JavaScript/TypeScript**: ESLint, Prettier, TypeScript strict mode
- **Git**: Conventional Commits, Git Flow, PR templates
- **IDE**: VS Code統一設定、必須拡張機能

### Testing Strategy
- **自動化テスト**: 単体・統合・E2Eテストの包括的実装
- **品質ゲート**: コードカバレッジ・静的解析・セキュリティチェック
- **CI/CD統合**: プルリクエスト時の自動品質チェック
- **レビュー検証**: コードレビューガイドラインの実効性確認

### Common Pitfalls
- **規約の形骸化**: チーム内での規約遵守・継続的な見直し不足
- **ツール設定の不統一**: 開発者間でのフォーマッタ・リンタ設定差異
- **コミット粒度**: 大きすぎる・小さすぎるコミットによるレビュー効率低下
- **ドキュメント更新**: コード変更時のドキュメント更新漏れ

### 実装優先順位
1. **Phase 1**: 基本コーディング規約・Git ワークフロー確立
2. **Phase 2**: 自動化ツール・CI/CD パイプライン構築
3. **Phase 3**: 高度な品質保証・継続的改善プロセス

---

**Version**: 1.0.0 | **Last Updated**: 2025-01-21 | **Next Review**: 2025-02-21