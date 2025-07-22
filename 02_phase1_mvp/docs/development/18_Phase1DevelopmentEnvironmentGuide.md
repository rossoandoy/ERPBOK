# ERP知識RAGシステム - Phase1 開発環境構築ガイド

---
doc_type: "phase1_development_environment"
complexity: "medium"
estimated_effort: "開発環境統一化の実装"
prerequisites: ["16_Phase1ImplementationPlan.md", "17_Phase1TechnicalSpecification.md", "14_CodingStandardsGitWorkflow.md"]
implementation_priority: "critical"
ai_assistance_level: "full_automation_possible"
version: "1.0.0"
author: "Claude Code"
created_date: "2025-01-21"
status: "approved"
approval_authority: "Development Team"
---

## 📋 Phase1 開発環境構築概要

### 環境構築の目的・範囲
本文書は「ERP知識RAGシステム（ERPFTS）」Phase1 MVP開発に必要な統一開発環境の構築手順を定義する。全開発者が同一環境でプロジェクトを実行可能にし、Week 1の環境構築タスクを効率的に完了することを目的とする。

### Phase1 開発環境の特徴
```yaml
統一性重視:
  - 全開発者での同一Python 3.11環境
  - 依存関係バージョンの完全一致
  - 設定ファイル・ツールチェーンの統一
  - Git workflow・ブランチ戦略の統一

効率性重視:
  - 自動セットアップスクリプト提供
  - 開発ツール統合（VSCode・PyCharm対応）
  - ホットリロード・デバッグ環境
  - テスト・品質チェック自動化

実用性重視:
  - Cross-platform対応（Windows・macOS・Linux）
  - Docker環境・ローカル環境両対応
  - CI/CD パイプライン連携
  - トラブルシューティングガイド完備
```

## 🛠️ 必要システム要件

### ハードウェア要件
```yaml
最小要件:
  CPU: Intel Core i5 / AMD Ryzen 5 以上
  メモリ: 8GB RAM 以上
  ストレージ: 20GB 空き容量以上
  ネットワーク: ブロードバンド接続

推奨要件:
  CPU: Intel Core i7 / AMD Ryzen 7 以上（8コア以上）
  メモリ: 16GB RAM 以上
  ストレージ: SSD 50GB 空き容量以上
  GPU: CUDA対応（埋め込み生成高速化用）

開発環境特化要件:
  - 複数モニター対応（コード・ドキュメント並行作業）
  - USB-C/Thunderbolt（外部デバイス接続）
  - Webカメラ・マイク（チーム会議・ペアプログラミング用）
```

### ソフトウェア要件
```yaml
オペレーティングシステム:
  サポート対象:
    - Windows 10/11 (64bit)
    - macOS 12+ (Intel・Apple Silicon)
    - Ubuntu 20.04+ / Debian 11+
    - CentOS 8+ / RHEL 8+

必須ソフトウェア:
  - Python 3.11.0+ (pyenv経由推奨)
  - Git 2.30+ (最新版推奨)
  - Docker Desktop 4.0+ (コンテナ環境用)
  - Node.js 18+ (フロントエンド開発用)

開発ツール:
  必須:
    - Visual Studio Code 1.85+ または PyCharm Professional 2023.3+
  推奨:
    - Postman / Insomnia (API開発・テスト)
    - DBeaver / pgAdmin (データベース管理)
    - Chrome DevTools (WebUI開発・デバッグ)
```

## 🐍 Python環境セットアップ

### pyenv インストール・設定
```bash
# === macOS (Homebrew) ===
brew install pyenv
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc

# === Linux (Ubuntu/Debian) ===
curl https://pyenv.run | bash
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

# 必要な依存関係インストール（Ubuntu）
sudo apt update
sudo apt install -y make build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
libffi-dev liblzma-dev

# === Windows (Git Bash / WSL2推奨) ===
# WSL2 Ubuntu使用を強く推奨
# Windows直接の場合: https://github.com/pyenv-win/pyenv-win
```

### Python 3.11 インストール・仮想環境作成
```bash
# Python 3.11 最新版インストール
pyenv install 3.11.7
pyenv global 3.11.7

# インストール確認
python --version  # Python 3.11.7 が出力されることを確認
pip --version

# プロジェクト用仮想環境作成
cd /path/to/ERPFTS
python -m venv venv

# 仮想環境アクティベート
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 仮想環境内でのPython確認
which python  # 仮想環境内のpythonパスが表示されることを確認
pip install --upgrade pip setuptools wheel
```

## 📦 プロジェクト依存関係セットアップ

### requirements.txt 定義
```python
# === Core Dependencies ===
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
streamlit==1.28.1
pydantic==2.5.0

# Database & ORM
sqlalchemy==2.0.23
alembic==1.12.1
databases[aiosqlite]==0.8.0
psycopg2-binary==2.9.9  # PostgreSQL support

# Vector Database
chromadb==0.4.15
sentence-transformers==2.2.2

# Text Processing & NLP
spacy==3.7.2
langdetect==1.0.9
tiktoken==0.5.1
PyPDF2==3.0.1
pdfplumber==0.9.0
beautifulsoup4==4.12.2
feedparser==6.0.10
python-docx==0.8.11

# ML & AI
torch==2.1.0
transformers==4.35.0
numpy==1.24.3
scikit-learn==1.3.0

# Async & Concurrency
asyncio-mqtt==0.13.0
aiofiles==23.2.1
httpx==0.25.0

# Development & Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==23.11.0
flake8==6.1.0
mypy==1.7.0
pre-commit==3.6.0
pytest-benchmark==4.0.0

# Monitoring & Logging
loguru==0.7.2
prometheus-client==0.19.0

# Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Utilities
python-dotenv==1.0.0
click==8.1.7
rich==13.7.0
typer==0.9.0
```

### 開発用追加依存関係
```python
# === Development Only Dependencies ===
# requirements-dev.txt
jupyter==1.0.0
ipython==8.17.2
notebook==7.0.6

# Code Quality
bandit==1.7.5  # Security analysis
safety==2.3.5  # Vulnerability check
pylint==3.0.2
isort==5.12.0

# Documentation
mkdocs==1.5.3
mkdocs-material==9.4.7
sphinx==7.2.6

# Database Tools
sqlite-utils==3.35.2

# Performance Profiling
line-profiler==4.1.1
memory-profiler==0.61.0

# API Testing
httpx==0.25.0
requests==2.31.0
```

### 依存関係インストール自動化
```bash
#!/bin/bash
# setup_dependencies.sh - 依存関係自動インストールスクリプト

set -e  # エラー時即座に終了

echo "🔧 ERP知識RAGシステム Phase1 依存関係セットアップ開始"
echo "========================================================"

# 仮想環境確認
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "❌ 仮想環境がアクティベートされていません"
    echo "実行してください: source venv/bin/activate"
    exit 1
fi

echo "✅ 仮想環境確認: $VIRTUAL_ENV"

# pip アップグレード
echo "📦 pip・setuptools アップグレード..."
pip install --upgrade pip setuptools wheel

# メイン依存関係インストール
echo "📚 メイン依存関係インストール..."
pip install -r requirements.txt

# 開発用依存関係インストール
echo "🛠️  開発用依存関係インストール..."
pip install -r requirements-dev.txt

# spaCy 言語モデルダウンロード
echo "🌐 spaCy言語モデルダウンロード..."
python -m spacy download ja_core_news_sm
python -m spacy download en_core_web_sm

# pre-commit フックインストール
echo "🔗 pre-commit フックセットアップ..."
pre-commit install

# 依存関係確認
echo "🔍 依存関係確認..."
pip list | grep -E "(fastapi|streamlit|chromadb|spacy|transformers)"

echo "✅ 依存関係セットアップ完了!"
echo "======================================="
echo "次のステップ: データベースセットアップ"
```

## 🗄️ データベース環境セットアップ

### SQLite セットアップ（開発・テスト用）
```python
# scripts/setup_sqlite.py
"""SQLite データベース初期セットアップスクリプト"""

import sqlite3
import os
from pathlib import Path
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# プロジェクトルート取得
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "erpfts.db"

def setup_sqlite_database():
    """SQLite データベース初期セットアップ"""
    print("🗄️  SQLite データベースセットアップ開始...")
    
    # データディレクトリ作成
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # データベース接続・テーブル作成
    engine = create_engine(f"sqlite:///{DB_PATH}")
    
    # DDL実行（05_DataModelDesign.mdからの基本スキーマ）
    ddl_commands = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'viewer',
            is_active BOOLEAN DEFAULT 1,
            last_login TIMESTAMP,
            preferences TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            source_type TEXT NOT NULL,
            base_url TEXT,
            rss_feed TEXT,
            access_config TEXT DEFAULT '{}',
            check_interval INTEGER DEFAULT 3600,
            last_checked TIMESTAMP,
            last_success_check TIMESTAMP,
            consecutive_failures INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            quality_weight REAL DEFAULT 1.0,
            metadata_json TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            title TEXT NOT NULL,
            author TEXT,
            published_date DATE,
            last_modified TIMESTAMP,
            file_path TEXT,
            content_hash TEXT UNIQUE,
            language TEXT DEFAULT 'ja',
            document_type TEXT DEFAULT 'article',
            word_count INTEGER,
            page_count INTEGER,
            metadata_json TEXT DEFAULT '{}',
            quality_score REAL DEFAULT 0.0,
            processing_status TEXT DEFAULT 'pending',
            processing_error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES sources (id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            content_hash TEXT,
            token_count INTEGER,
            char_count INTEGER,
            page_number INTEGER,
            section_title TEXT,
            section_level INTEGER,
            quality_score REAL DEFAULT 0.0,
            metadata_json TEXT DEFAULT '{}',
            embedding_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents (id),
            UNIQUE(document_id, chunk_index)
        )
        """
    ]
    
    with engine.connect() as conn:
        for ddl in ddl_commands:
            conn.execute(text(ddl))
        conn.commit()
    
    print(f"✅ SQLite データベース作成完了: {DB_PATH}")
    return str(DB_PATH)

if __name__ == "__main__":
    setup_sqlite_database()
```

### Chroma DB セットアップ
```python
# scripts/setup_chromadb.py
"""Chroma Vector Database セットアップスクリプト"""

import chromadb
from chromadb.config import Settings
from pathlib import Path
import logging

# プロジェクトルート・設定
PROJECT_ROOT = Path(__file__).parent.parent
CHROMA_PATH = PROJECT_ROOT / "data" / "chroma_db"

def setup_chromadb():
    """Chroma DB 初期セットアップ"""
    print("🔍 Chroma Vector Database セットアップ開始...")
    
    # Chromaデータディレクトリ作成
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    
    # Chroma クライアント初期化
    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=Settings(
            anonymized_telemetry=False,
            is_persistent=True
        )
    )
    
    # コレクション作成（存在確認）
    try:
        collection = client.get_collection("erp_knowledge")
        print("✅ 既存コレクション 'erp_knowledge' 発見")
    except ValueError:
        # コレクション新規作成
        collection = client.create_collection(
            name="erp_knowledge",
            metadata={
                "description": "ERP Knowledge Base Embeddings - Phase1 MVP",
                "version": "1.0.0",
                "created_for": "phase1_mvp"
            }
        )
        print("✅ 新規コレクション 'erp_knowledge' 作成完了")
    
    # 基本情報表示
    print(f"📊 Chroma DB 情報:")
    print(f"   パス: {CHROMA_PATH}")
    print(f"   コレクション数: {len(client.list_collections())}")
    print(f"   'erp_knowledge' チャンク数: {collection.count()}")
    
    return client, collection

if __name__ == "__main__":
    setup_chromadb()
```

## ⚙️ 開発ツール設定

### Visual Studio Code 設定
```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=88"],
    "python.sortImports.args": ["--profile", "black"],
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.pytestArgs": ["tests/"],
    
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/venv": true,
        "**/.pytest_cache": true,
        "**/node_modules": true
    },
    
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    
    "files.associations": {
        "*.md": "markdown"
    }
}
```

```json
// .vscode/launch.json - デバッグ設定
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI Server",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/venv/bin/uvicorn",
            "args": [
                "erpfts.api.main:app",
                "--reload",
                "--host", "0.0.0.0",
                "--port", "8000"
            ],
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            },
            "console": "integratedTerminal"
        },
        {
            "name": "Streamlit App",
            "type": "python", 
            "request": "launch",
            "program": "${workspaceFolder}/venv/bin/streamlit",
            "args": [
                "run",
                "erpfts/ui/streamlit_app.py",
                "--server.port", "8501"
            ],
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            },
            "console": "integratedTerminal"
        },
        {
            "name": "Run Tests",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/venv/bin/pytest",
            "args": ["tests/", "-v", "--cov=erpfts"],
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            },
            "console": "integratedTerminal"
        }
    ]
}
```

### PyCharm 設定
```yaml
# PyCharm設定エクスポート手順:
プロジェクト設定:
  1. File → Settings → Project → Python Interpreter
     - 仮想環境パス設定: ./venv/bin/python
  
  2. File → Settings → Editor → Code Style → Python
     - Line length: 88
     - Continuation indent: 4
  
  3. File → Settings → Tools → External Tools
     - Black formatter 追加
     - flake8 linter 追加
     - pytest runner 追加

実行設定:
  FastAPI Server:
    - Script path: venv/bin/uvicorn
    - Parameters: erpfts.api.main:app --reload --host 0.0.0.0 --port 8000
    - Working directory: プロジェクトルート
  
  Streamlit App:
    - Script path: venv/bin/streamlit  
    - Parameters: run erpfts/ui/streamlit_app.py --server.port 8501
    - Working directory: プロジェクトルート
```

## 🔧 Git・品質管理設定

### Git 設定・リポジトリ初期化
```bash
# Git初期設定（未設定の場合）
git config --global user.name "Your Name"
git config --global user.email "your.email@company.com"
git config --global init.defaultBranch main

# リポジトリ初期化
cd /path/to/ERPFTS
git init
git remote add origin <repository-url>

# .gitignore設定
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Database
*.db
*.sqlite3
data/erpfts.db

# Chroma DB
data/chroma_db/

# Logs
*.log
logs/

# Environment variables
.env
.env.local

# Testing
.pytest_cache/
.coverage
htmlcov/

# Documentation
docs/_build/

# Temporary files
*.tmp
*.temp
EOF
```

### pre-commit 設定
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3
        args: [--line-length=88]

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203,W503]

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: [--profile=black]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
        args: [--ignore-missing-imports]
```

## 🐋 Docker環境（オプション）

### Docker Compose設定
```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"  # FastAPI
      - "8501:8501"  # Streamlit
    volumes:
      - .:/app
      - ./data:/app/data
    environment:
      - PYTHONPATH=/app
      - DATABASE_URL=sqlite:///app/data/erpfts.db
      - CHROMA_DB_PATH=/app/data/chroma_db
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: erpfts
      POSTGRES_USER: erpfts_user
      POSTGRES_PASSWORD: erpfts_pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  redis_data:
  postgres_data:
```

### Dockerfile
```dockerfile
FROM python:3.11-slim

# システムパッケージ更新・必要パッケージインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリ設定
WORKDIR /app

# Python依存関係インストール
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-dev.txt

# spaCy言語モデルダウンロード
RUN python -m spacy download ja_core_news_sm
RUN python -m spacy download en_core_web_sm

# アプリケーションコピー
COPY . .

# ポート公開
EXPOSE 8000 8501

# デフォルトコマンド
CMD ["uvicorn", "erpfts.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

## 🚀 環境構築自動化スクリプト

### 統合セットアップスクリプト
```bash
#!/bin/bash
# setup_development_environment.sh - Phase1開発環境自動構築

set -e

echo "🚀 ERP知識RAGシステム Phase1 開発環境構築開始"
echo "=================================================="

# OS検出
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"  
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
else
    echo "❌ サポートされていないOS: $OSTYPE"
    exit 1
fi

echo "🖥️  検出OS: $OS"

# Python 3.11 確認
python_version=$(python --version 2>&1 | cut -d' ' -f2)
if [[ ! "$python_version" =~ ^3\.11\. ]]; then
    echo "❌ Python 3.11が必要です。現在: $python_version"
    echo "pyenvを使用してPython 3.11をインストールしてください"
    exit 1
fi

echo "✅ Python確認: $python_version"

# 仮想環境作成・アクティベート
if [ ! -d "venv" ]; then
    echo "📦 仮想環境作成..."
    python -m venv venv
fi

echo "🔌 仮想環境アクティベート..."
source venv/bin/activate

# 依存関係インストール
echo "📚 依存関係インストール..."
./scripts/setup_dependencies.sh

# データベースセットアップ
echo "🗄️  データベースセットアップ..."
python scripts/setup_sqlite.py
python scripts/setup_chromadb.py

# Git設定確認・pre-commit setup
if [ -d ".git" ]; then
    echo "🔗 Git hooks設定..."
    pre-commit install
else
    echo "⚠️  Git未初期化。後でgit initを実行してください"
fi

# 設定ファイル作成
echo "⚙️  設定ファイル作成..."
if [ ! -f ".env" ]; then
    cp .env.template .env
    echo "📝 .env作成完了。必要に応じて設定を変更してください"
fi

# 健全性チェック
echo "🔍 環境構築確認..."
python -c "
import sys
import fastapi
import streamlit
import chromadb
print(f'✅ Python: {sys.version}')
print(f'✅ FastAPI: {fastapi.__version__}')
print(f'✅ Streamlit: {streamlit.__version__}')
print(f'✅ ChromaDB: {chromadb.__version__}')
"

echo ""
echo "🎉 Phase1開発環境構築完了!"
echo "================================="
echo "次のステップ:"
echo "1. 🔌 仮想環境アクティベート: source venv/bin/activate"
echo "2. 🏃 FastAPI起動: uvicorn erpfts.api.main:app --reload"
echo "3. 🌐 Streamlit起動: streamlit run erpfts/ui/streamlit_app.py"
echo "4. 🧪 テスト実行: pytest tests/"
```

## 🔧 トラブルシューティング

### よくある問題・解決方法
```yaml
Python関連:
  問題: "python: command not found"
  解決: 
    - pyenv正常インストール確認
    - .bashrc/.zshrc設定確認・再読み込み
    - pyenv global 3.11.7 実行

  問題: "仮想環境アクティベート失敗"
  解決:
    - venv削除・再作成: rm -rf venv && python -m venv venv
    - Pythonパス確認: which python
    - 権限確認: chmod +x venv/bin/activate

依存関係:
  問題: "パッケージインストール失敗"
  解決:
    - pip最新化: pip install --upgrade pip
    - キャッシュクリア: pip cache purge
    - システムライブラリ確認（Linux）

  問題: "spaCy言語モデルダウンロード失敗"
  解決:
    - 直接ダウンロード: python -m spacy download ja_core_news_sm --user
    - プロキシ設定確認
    - 手動インストール: pip install ja_core_news_sm@https://...

データベース:
  問題: "SQLite database is locked"
  解決:
    - プロセス終了: pkill -f erpfts
    - DB再作成: rm data/erpfts.db && python scripts/setup_sqlite.py

  問題: "Chroma permission denied"
  解決:
    - 権限確認: chmod -R 755 data/chroma_db/
    - パス確認: ls -la data/

VS Code:
  問題: "Python interpreter not found"
  解決:
    - Ctrl+Shift+P → "Python: Select Interpreter"
    - ./venv/bin/python選択
    - .vscode/settings.json確認

  問題: "拡張機能エラー"
  解決:
    - Python拡張機能再インストール
    - Pylance拡張機能追加インストール
    - VSCode再起動
```

### 環境診断スクリプト
```python
#!/usr/bin/env python3
# scripts/diagnose_environment.py
"""開発環境診断スクリプト"""

import sys
import subprocess
import platform
import os
from pathlib import Path

def run_diagnostics():
    """包括的環境診断"""
    print("🔍 ERP知識RAGシステム 開発環境診断")
    print("=" * 50)
    
    # 基本環境情報
    print("🖥️  システム情報:")
    print(f"   OS: {platform.system()} {platform.release()}")
    print(f"   Python: {sys.version}")
    print(f"   プラットフォーム: {platform.platform()}")
    
    # 仮想環境確認
    venv_active = os.environ.get('VIRTUAL_ENV')
    if venv_active:
        print(f"✅ 仮想環境: {venv_active}")
    else:
        print("❌ 仮想環境未アクティベート")
        return False
    
    # 必須パッケージ確認
    required_packages = [
        'fastapi', 'streamlit', 'chromadb', 'spacy', 
        'transformers', 'sqlalchemy'
    ]
    
    print("\n📦 パッケージ確認:")
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package}")
            missing_packages.append(package)
    
    # データベースファイル確認
    print("\n🗄️  データベース確認:")
    db_files = [
        'data/erpfts.db',
        'data/chroma_db'
    ]
    
    for db_file in db_files:
        if Path(db_file).exists():
            print(f"   ✅ {db_file}")
        else:
            print(f"   ❌ {db_file}")
    
    # Git設定確認
    print("\n🔗 Git設定確認:")
    try:
        git_name = subprocess.check_output(['git', 'config', 'user.name']).decode().strip()
        git_email = subprocess.check_output(['git', 'config', 'user.email']).decode().strip()
        print(f"   ✅ Name: {git_name}")
        print(f"   ✅ Email: {git_email}")
    except:
        print("   ❌ Git設定未完了")
    
    # 診断結果
    if not missing_packages:
        print("\n🎉 環境診断正常完了!")
        return True
    else:
        print(f"\n❌ 不足パッケージ: {', '.join(missing_packages)}")
        print("requirements.txtから再インストールしてください")
        return False

if __name__ == "__main__":
    run_diagnostics()
```

## 🤖 Implementation Notes for AI

### Critical Setup Sequence
1. **Week 1 Day 1-2**: Python環境統一、仮想環境作成、依存関係インストール
2. **Week 1 Day 3-4**: データベースセットアップ、開発ツール設定
3. **Week 1 Day 5-7**: Git workflow確立、CI/CD基盤構築

### Environment Validation
- **Python 3.11**: 必須バージョン確認、pyenv使用推奨
- **Dependencies**: 完全バージョン固定、requirements.txt厳密管理
- **Database**: SQLite + Chroma DB 正常動作確認
- **Tools**: VS Code/PyCharm統一設定、デバッグ環境準備

### Common Pitfalls
- **Python Path**: 仮想環境パス設定、PYTHONPATH環境変数
- **Package Conflicts**: バージョン競合回避、clean install実行
- **Database Permissions**: ファイル権限、ディレクトリアクセス
- **Cross-platform**: Windows・macOS・Linux環境差異対応

### Quality Gates
- **環境統一度**: 全開発者での同一動作確認100%
- **セットアップ時間**: 30分以内での環境構築完了
- **依存関係安定性**: pip install成功率100%
- **ツール統合**: IDE・デバッガ・テスト完全動作

---

**Version**: 1.0.0 | **Last Updated**: 2025-01-21 | **Next Review**: Weekly Development Review