# 🚀 GitHub Codespaces クイックスタートガイド

## Phase1 MVP検証 - ローカルストレージ不要！

### 🎯 概要
- **目的**: ERP知識RAGシステム Phase1をクラウド環境で検証
- **ストレージ使用量**: ローカル 0GB（全てクラウド）
- **セットアップ時間**: 約10分
- **利用枠**: GitHub無料プラン月60時間

### 📋 事前準備
- GitHubアカウント（既存）
- ブラウザ（Chrome/Edge/Safari推奨）
- インターネット接続

### 🚀 起動手順

#### Step 1: Codespace作成
1. **GitHubリポジトリページにアクセス**
   ```
   https://github.com/[username]/ERPFTS
   ```

2. **Codespace起動**
   - 緑色の `Code` ボタンをクリック
   - `Codespaces` タブを選択
   - `Create codespace on main` をクリック

3. **自動セットアップ待機**
   - 初回起動：約8-10分
   - 依存関係インストール、環境構築が自動実行
   - ターミナルで進捗確認可能

#### Step 2: 知識ベース準備
```bash
# 知識ソース準備スクリプト実行
cd 02_phase1_mvp
python scripts/download_knowledge_sources.py

# 配置確認
python scripts/download_knowledge_sources.py --check
```

#### Step 3: データベース初期化
```bash
# SQLite & ChromaDB初期化
python scripts/init_codespace_db.py

# 初期データ確認
ls -la data/
```

#### Step 4: アプリケーション起動

**Terminal 1: FastAPI サーバー**
```bash
cd 02_phase1_mvp
python -m uvicorn src.erpfts.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2: Streamlit UI**
```bash
streamlit run src/erpfts/ui/main.py --server.port 8501
```

#### Step 5: ブラウザアクセス
- **FastAPI Swagger**: `https://[codespace-name]-8000.app.github.dev/docs`
- **Streamlit UI**: `https://[codespace-name]-8501.app.github.dev`
- ポート転送通知が自動表示されます

### 🧪 動作確認手順

#### 基本機能テスト
```bash
# 単体テスト実行
pytest tests/ -v

# API疎通確認
curl https://[codespace-name]-8000.app.github.dev/health

# ChromaDB接続確認
python -c "
import chromadb
client = chromadb.PersistentClient(path='data/chroma_db')
print(f'Collections: {len(client.list_collections())}')
"
```

#### 知識検索テスト（Streamlit UI）
1. ブラウザでStreamlit UIにアクセス
2. 「プロジェクト管理」で検索実行
3. PMBOK関連結果が表示されることを確認
4. 「データガバナンス」で検索実行
5. DMBOK関連結果が表示されることを確認

### 📊 リソース利用状況

#### GitHub Codespaces無料枠
- **計算能力**: 2-core CPU, 4GB RAM
- **ストレージ**: 32GB
- **利用時間**: 月60時間
- **同時起動**: 最大2 Codespace

#### 概算利用時間
- **初回セットアップ**: 0.5時間
- **Phase1検証**: 2-4時間
- **開発・テスト**: 10-20時間
- **余裕**: 35-47時間

### 🔧 トラブルシューティング

#### よくある問題

**1. セットアップ失敗**
```bash
# 依存関係再インストール
pip install -r 02_phase1_mvp/requirements.txt --force-reinstall

# スクリプト再実行
bash .devcontainer/setup.sh
```

**2. ポート接続エラー**
```bash
# プロセス確認
ps aux | grep -E "(uvicorn|streamlit)"

# ポート強制終了
pkill -f "uvicorn|streamlit"

# 再起動
python -m uvicorn src.erpfts.api.main:app --reload --host 0.0.0.0 --port 8000
```

**3. データベースエラー**
```bash
# データベース再初期化
rm -rf data/*.db data/chroma_db
python scripts/init_codespace_db.py
```

#### 高度なトラブルシューティング
```bash
# 環境診断スクリプト実行
python .devcontainer/diagnose_environment.py

# ログ確認
tail -f logs/erpfts.log

# システムリソース確認
htop
df -h
```

### 🎯 検証成功基準

#### Phase1 MVP検証完了チェックリスト
- [ ] Codespace正常起動・環境構築完了
- [ ] FastAPI サーバー起動・Swagger UI表示
- [ ] Streamlit UI起動・ホーム画面表示
- [ ] ChromaDB接続・コレクション作成確認
- [ ] 知識検索機能動作確認
- [ ] PDF文書アップロード・処理確認
- [ ] 基本API エンドポイント疎通確認
- [ ] 単体テスト全件合格

#### パフォーマンス確認
- [ ] 検索レスポンス時間 < 3秒
- [ ] 文書処理時間 < 30秒/文書
- [ ] メモリ使用量 < 3GB
- [ ] CPU使用率 < 80%

### 📋 次のステップ

#### Phase1完了後
1. **ChromaDBクラウド移行**
   - Chroma Cloud アカウント作成
   - データ移行スクリプト実行
   - リモートMCP設定更新

2. **本格運用準備**
   - Docker環境構築
   - CI/CD パイプライン設定
   - 監視・ログ体制構築

3. **Phase2計画**
   - 高度検索機能実装
   - マルチLLM統合
   - スケーラビリティ向上

### 💡 Tips

#### 効率的な開発
- **複数ターミナル**: Ctrl+Shift+` で新ターミナル
- **ポート管理**: PORTS タブで転送状況確認
- **ファイル同期**: 変更は自動保存・Git同期
- **拡張機能**: Python、GitHub Copilot活用

#### コスト最適化
- **停止**: 使用後は Codespace 停止（時間節約）
- **削除**: 検証完了後は削除（ストレージ節約）
- **プリビルド**: 頻繁利用時はプリビルド設定

---

## 🎉 Phase1 MVP on GitHub Codespaces 準備完了！

**ローカルストレージ使用量: 0GB**  
**クラウド検証環境: Ready**  
**次のアクション: GitHub リポジトリから Codespace 起動**