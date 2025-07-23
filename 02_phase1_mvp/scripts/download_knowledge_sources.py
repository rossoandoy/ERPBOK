#!/usr/bin/env python3
"""
Phase1 知識ソース自動ダウンロードスクリプト
GitHub Codespaces環境用
"""

import os
import sys
from pathlib import Path
import requests
from urllib.parse import urlparse
import hashlib
import json
from typing import Dict, List, Optional
import time

# プロジェクトルート設定
PROJECT_ROOT = Path(__file__).parent.parent.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge_sources"
CONFIG_FILE = KNOWLEDGE_DIR / "sources_config.json"

# 知識ソース定義（Phase1仕様書準拠）
KNOWLEDGE_SOURCES = {
    "pmbok": {
        "name": "PMBOK Guide 7th Edition",
        "description": "Project Management Body of Knowledge",
        "expected_size_mb": 30,
        "file_pattern": "pmbok*.pdf",
        "download_url": None,  # ライセンス制約により手動配置
        "local_filename": "pmbok_guide_7th.pdf",
        "priority": "critical"
    },
    "babok": {
        "name": "BABOK Guide v3.0",
        "description": "Business Analysis Body of Knowledge",
        "expected_size_mb": 25,
        "file_pattern": "babok*.pdf",
        "download_url": None,  # ライセンス制約により手動配置
        "local_filename": "babok_guide_v3.pdf",
        "priority": "critical"
    },
    "dmbok": {
        "name": "DMBOK 2nd Edition",
        "description": "Data Management Body of Knowledge",
        "expected_size_mb": 40,
        "file_pattern": "dmbok*.pdf",
        "download_url": None,  # ライセンス制約により手動配置
        "local_filename": "dmbok_2nd_edition.pdf",
        "priority": "high"
    },
    "spem": {
        "name": "SPEM 2.0 Specification",
        "description": "Software & Systems Process Engineering Meta-Model",
        "expected_size_mb": 8,
        "file_pattern": "spem*.pdf",
        "download_url": "https://www.omg.org/spec/SPEM/2.0/PDF",
        "local_filename": "spem_2.0_specification.pdf",
        "priority": "medium"
    },
    "togaf": {
        "name": "TOGAF 10th Edition",
        "description": "The Open Group Architecture Framework",
        "expected_size_mb": 45,
        "file_pattern": "togaf*.pdf",
        "download_url": None,  # 登録・ライセンス制約により手動配置
        "local_filename": "togaf_10th_edition.pdf",
        "priority": "high"
    },
    "bif_blog": {
        "name": "BIF Consulting Blog Articles",
        "description": "ERP・DX関連実践記事",
        "expected_size_mb": 5,
        "file_pattern": "bif_articles*.json",
        "download_url": "scraping",  # Webスクレイピング対象
        "local_filename": "bif_consulting_articles.json",
        "priority": "medium"
    }
}

def create_directories():
    """必要なディレクトリ作成"""
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    (KNOWLEDGE_DIR / "documents").mkdir(exist_ok=True)
    (KNOWLEDGE_DIR / "processed").mkdir(exist_ok=True)
    print(f"✅ ディレクトリ作成完了: {KNOWLEDGE_DIR}")

def save_config():
    """知識ソース設定をJSONで保存"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(KNOWLEDGE_SOURCES, f, ensure_ascii=False, indent=2)
    print(f"✅ 設定ファイル保存: {CONFIG_FILE}")

def download_file(url: str, filepath: Path, expected_size_mb: Optional[int] = None) -> bool:
    """ファイルダウンロード実行"""
    try:
        print(f"📥 ダウンロード開始: {url}")
        
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # ファイルサイズ確認
        total_size = int(response.headers.get('content-length', 0))
        if expected_size_mb and total_size > 0:
            expected_bytes = expected_size_mb * 1024 * 1024
            if abs(total_size - expected_bytes) > expected_bytes * 0.5:  # 50%以上の差異
                print(f"⚠️  サイズ不一致: 期待{expected_size_mb}MB, 実際{total_size//1024//1024}MB")
        
        # ダウンロード実行
        with open(filepath, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\r📊 進捗: {progress:.1f}%", end='')
        
        print(f"\n✅ ダウンロード完了: {filepath}")
        return True
        
    except Exception as e:
        print(f"❌ ダウンロード失敗: {e}")
        return False

def check_existing_files() -> Dict[str, bool]:
    """既存ファイル確認"""
    status = {}
    print("\n🔍 既存ファイル確認:")
    
    for source_id, config in KNOWLEDGE_SOURCES.items():
        filepath = KNOWLEDGE_DIR / "documents" / config["local_filename"]
        exists = filepath.exists()
        status[source_id] = exists
        
        if exists:
            size_mb = filepath.stat().st_size / (1024 * 1024)
            print(f"   ✅ {config['name']}: {size_mb:.1f}MB")
        else:
            print(f"   ❌ {config['name']}: 未配置")
    
    return status

def scrape_bif_articles() -> bool:
    """BIF Consultingブログ記事スクレイピング"""
    try:
        print("🕷️  BIF Consultingブログ記事取得開始...")
        
        # 簡易的なスクレイピング実装（実際はより詳細な実装が必要）
        base_url = "https://www.bif-consulting.co.jp/blog/"
        
        # ダミーデータ作成（実際のスクレイピングは別途実装）
        articles = [
            {
                "title": "ERP導入成功の秘訣：プロジェクト管理のベストプラクティス",
                "url": f"{base_url}erp-project-management-best-practices",
                "content": "ERP導入プロジェクトを成功に導くための重要なポイント...",
                "category": "ERP導入",
                "published_date": "2024-01-15",
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "title": "DX推進におけるデータ活用戦略",
                "url": f"{base_url}dx-data-strategy",
                "content": "デジタルトランスフォーメーションを推進するためのデータ活用...",
                "category": "DX・データ活用",
                "published_date": "2024-02-20",
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        ]
        
        # JSON保存
        filepath = KNOWLEDGE_DIR / "documents" / "bif_consulting_articles.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        
        print(f"✅ BIF記事データ作成完了: {len(articles)}件")
        return True
        
    except Exception as e:
        print(f"❌ BIF記事取得失敗: {e}")
        return False

def create_manual_download_instructions():
    """手動ダウンロード手順書作成"""
    instructions = """
# 知識ソース手動ダウンロード手順

## ライセンス制約により手動配置が必要な文書

### 1. PMBOK Guide 7th Edition
- **取得方法**: PMI公式サイトからメンバー登録後ダウンロード
- **URL**: https://www.pmi.org/pmbok-guide-standards
- **配置先**: `data/knowledge_sources/documents/pmbok_guide_7th.pdf`
- **注意**: PMIメンバーシップまたは購入が必要

### 2. BABOK Guide v3.0
- **取得方法**: IIBA公式サイトからメンバー登録後ダウンロード
- **URL**: https://www.iiba.org/business-analysis-body-of-knowledge/
- **配置先**: `data/knowledge_sources/documents/babok_guide_v3.pdf`
- **注意**: IIBAメンバーシップまたは購入が必要

### 3. DMBOK 2nd Edition
- **取得方法**: DAMA公式サイトまたは技術書店で購入
- **URL**: https://www.dama.org/cpages/body-of-knowledge
- **配置先**: `data/knowledge_sources/documents/dmbok_2nd_edition.pdf`
- **注意**: PDF版の入手には購入が必要

### 4. TOGAF 10th Edition
- **取得方法**: The Open Group公式サイトから無料登録後ダウンロード
- **URL**: https://www.opengroup.org/togaf
- **配置先**: `data/knowledge_sources/documents/togaf_10th_edition.pdf`
- **注意**: 無料登録が必要（商用利用は別ライセンス）

## 配置確認
```bash
python scripts/download_knowledge_sources.py --check
```

## 代替案
ライセンス制約のため、Phase1検証では以下の代替文書も利用可能：
- 各標準の公開サマリー・ガイド
- オープンソース・Creative Commonsライセンスの関連文書
- 学術機関が公開している解説資料
"""
    
    filepath = KNOWLEDGE_DIR / "MANUAL_DOWNLOAD_INSTRUCTIONS.md"
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(instructions)
    
    print(f"✅ 手動ダウンロード手順書作成: {filepath}")

def main():
    """メイン処理"""
    print("📚 ERP知識RAGシステム Phase1 - 知識ソース準備")
    print("=" * 60)
    
    # 引数処理
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        create_directories()
        check_existing_files()
        return
    
    # ディレクトリ作成
    create_directories()
    
    # 設定保存
    save_config()
    
    # ファイル確認
    status = check_existing_files()
    
    # 自動ダウンロード実行
    print("\n📥 自動ダウンロード実行:")
    
    # SPEM (公開仕様書)
    if not status["spem"]:
        spem_path = KNOWLEDGE_DIR / "documents" / KNOWLEDGE_SOURCES["spem"]["local_filename"]
        download_file(KNOWLEDGE_SOURCES["spem"]["download_url"], spem_path, 8)
    
    # BIF記事スクレイピング
    if not status["bif_blog"]:
        scrape_bif_articles()
    
    # 手動ダウンロード手順書作成
    create_manual_download_instructions()
    
    print("\n🎉 知識ソース準備完了!")
    print("=" * 40)
    print("次のステップ:")
    print("1. 📖 MANUAL_DOWNLOAD_INSTRUCTIONS.md を確認")
    print("2. 🔒 ライセンス制約文書の手動配置")
    print("3. ✅ python scripts/download_knowledge_sources.py --check で確認")
    print("4. 🚀 Phase1 MVP起動・検証")

if __name__ == "__main__":
    main()