# GitHub Codespaces 環境構築ガイド

## 🚀 Codespaces 起動手順

### 1. Codespace作成
1. GitHubリポジトリページで `Code` ボタンクリック
2. `Codespaces` タブ選択
3. `Create codespace on main` クリック

### 2. 自動セットアップ完了待ち
- `.devcontainer/setup.sh` が自動実行されます
- 依存関係インストール、データベース初期化が完了します
- 約5-10分でセットアップ完了

### 3. アプリケーション起動

#### FastAPI サーバー起動
```bash
cd 02_phase1_mvp
python -m uvicorn src.erpfts.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### Streamlit UI起動
```bash
streamlit run src/erpfts/ui/main.py --server.port 8501
```

### 4. ブラウザアクセス
- FastAPI: `https://<codespace-name>-8000.app.github.dev`
- Streamlit: `https://<codespace-name>-8501.app.github.dev`
- ポート転送は自動で設定されます

## 🔧 開発環境

### 利用可能な拡張機能
- Python
- Black Formatter
- Flake8
- MyPy
- Jupyter
- GitHub Copilot

### データ永続化
- `/workspaces/ERPFTS/data` にデータベース・ChromaDBが保存
- Codespacesのボリュームマウントで永続化

### テスト実行
```bash
pytest tests/ -v --cov=erpfts
```

## 📊 利用可能リソース
- **CPU**: 2-core (無料プラン)
- **メモリ**: 4GB RAM
- **ストレージ**: 32GB
- **利用時間**: 月60時間無料

## 🛠️ トラブルシューティング

### ポート転送確認
```bash
# 起動中サービス確認
ps aux | grep -E "(uvicorn|streamlit)"

# ポート使用状況確認
netstat -tlnp | grep -E ":8000|:8501"
```

### 依存関係再インストール
```bash
pip install -r 02_phase1_mvp/requirements.txt --force-reinstall
```

### データベース再初期化
```bash
rm -rf data/erpfts.db data/chroma_db
python scripts/init_codespace_db.py
```