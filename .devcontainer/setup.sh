#!/bin/bash
# GitHub Codespaces環境自動セットアップスクリプト

set -e

echo "🚀 ERP知識RAGシステム Phase1 - Codespaces環境セットアップ開始"
echo "=================================================================="

# Python環境確認
python_version=$(python --version)
echo "✅ Python確認: $python_version"

# pipアップグレード
echo "📦 pip・setuptools アップグレード..."
pip install --upgrade pip setuptools wheel

# メイン依存関係インストール
echo "📚 依存関係インストール..."
if [ -f "02_phase1_mvp/requirements.txt" ]; then
    pip install -r 02_phase1_mvp/requirements.txt
elif [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "⚠️  requirements.txtが見つかりません。手動でインストールが必要です。"
fi

# spaCy言語モデルダウンロード
echo "🌐 spaCy言語モデルダウンロード..."
python -m spacy download ja_core_news_sm || echo "⚠️  日本語モデルダウンロード失敗"
python -m spacy download en_core_web_sm || echo "⚠️  英語モデルダウンロード失敗"

# データディレクトリ作成
echo "📁 データディレクトリ準備..."
mkdir -p data/chroma_db
mkdir -p data/documents
mkdir -p logs

# 環境設定ファイル作成
echo "⚙️  環境設定ファイル作成..."
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# ERP知識RAGシステム Phase1 - 環境設定

# データベース設定
DATABASE_URL=sqlite:///data/erpfts.db
CHROMA_DB_PATH=data/chroma_db

# API設定
API_HOST=0.0.0.0
API_PORT=8000
STREAMLIT_PORT=8501

# ログ設定
LOG_LEVEL=INFO
LOG_FILE=logs/erpfts.log

# セキュリティ設定
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 開発設定
DEBUG=true
DEVELOPMENT=true
EOF
    echo "📝 .env作成完了"
fi

# Git設定（Codespacesでは自動設定されるが確認）
echo "🔗 Git設定確認..."
git config --get user.name || echo "Git user.name未設定"
git config --get user.email || echo "Git user.email未設定"

# pre-commit設定（オプション）
echo "🔧 品質チェックツール設定..."
if command -v pre-commit &> /dev/null; then
    pre-commit install || echo "⚠️  pre-commit設定スキップ"
fi

# データベース初期化用スクリプト準備
echo "🗄️  データベース初期化準備..."
cat > scripts/init_codespace_db.py << 'EOF'
#!/usr/bin/env python3
"""Codespaces用データベース初期化スクリプト"""

import sqlite3
import os
from pathlib import Path

def init_sqlite_db():
    """SQLite データベース初期化"""
    db_path = Path("data/erpfts.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 基本テーブル作成
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT,
            content TEXT,
            chunk_index INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents (id)
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"✅ SQLite データベース初期化完了: {db_path}")

if __name__ == "__main__":
    init_sqlite_db()
EOF

chmod +x scripts/init_codespace_db.py

# ChromaDB初期化
echo "🔍 ChromaDB初期化..."
python -c "
import chromadb
from pathlib import Path

chroma_path = Path('data/chroma_db')
chroma_path.mkdir(parents=True, exist_ok=True)

try:
    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_or_create_collection('erp_knowledge')
    print(f'✅ ChromaDB初期化完了: {chroma_path}')
    print(f'コレクション数: {len(client.list_collections())}')
except Exception as e:
    print(f'⚠️  ChromaDB初期化エラー: {e}')
"

# 環境診断
echo "🔍 環境診断実行..."
python -c "
import sys
print(f'Python: {sys.version}')

packages = ['fastapi', 'streamlit', 'chromadb', 'sqlalchemy']
for pkg in packages:
    try:
        module = __import__(pkg)
        version = getattr(module, '__version__', 'unknown')
        print(f'✅ {pkg}: {version}')
    except ImportError:
        print(f'❌ {pkg}: Not installed')
"

echo ""
echo "🎉 Codespaces環境セットアップ完了!"
echo "======================================="
echo "次のステップ:"
echo "1. 🏃 FastAPI起動: cd 02_phase1_mvp && python -m uvicorn src.erpfts.api.main:app --reload --host 0.0.0.0 --port 8000"
echo "2. 🌐 Streamlit起動: streamlit run src/erpfts/ui/main.py --server.port 8501"
echo "3. 🧪 テスト実行: pytest tests/ -v"
echo "4. 📊 ブラウザアクセス: ポート転送でAPI(8000)・UI(8501)確認"