# ERP知識RAGシステム - フェーズベース・ドキュメント体系

## 📁 ドキュメント構造概要

このプロジェクトでは、フェーズベースのドキュメント管理体系を採用しています。各フェーズが独立したドキュメント体系を持ち、明確な分離と追跡性を確保しています。

```bash
docs/
├── 00_project_foundation/     # プロジェクト基盤（全フェーズ共通）
├── 01_analysis_design/        # 分析・設計フェーズ
├── 02_phase1_mvp/            # Phase1 MVP開発
├── 03_phase2_enhancement/     # Phase2 機能拡張（準備中）
├── 04_phase3_advanced/        # Phase3 高度機能（準備中）
├── 05_operations/             # 運用・保守
└── 99_archive/               # アーカイブ・廃止文書
```

## 🎯 フェーズ別ドキュメント

### 📋 00_project_foundation/ - プロジェクト基盤
全フェーズ共通の基盤ドキュメント

- **charter/** - プロジェクト憲章・戦略
  - `00_ProjectCharter.md` - プロジェクト憲章・基本方針
- **architecture/** - システム全体アーキテクチャ  
  - `02_SystemArchitecture.md` - システム全体アーキテクチャ設計
- **management/** - プロジェクト管理基盤
  - `00_DocumentManagementGuideline.md` - フェーズベース管理ガイドライン
  - `01_PhaseTransitionProcedures.md` - フェーズ移行時の管理手順
  - `07_ProjectManagementPlan.md` - プロジェクト管理計画
  - `08_DocumentManagementSystem.md` - ドキュメント管理システム
  - `10_ChangeManagementRules.md` - 変更管理ルール
- **standards/** - 品質・セキュリティ基準
  - `11_SecurityDesign.md` - セキュリティ設計・対策
  - `14_CodingStandardsGitWorkflow.md` - コーディング規約・Git運用

### 📊 01_analysis_design/ - 分析・設計フェーズ
要件分析・システム設計の成果物

- **requirements/** - 要件定義
  - `01_PRD.md` - プロダクト要件定義書
  - `03_FunctionalRequirements.md` - 機能要件仕様書
  - `04_NonFunctionalRequirements.md` - 非機能要件仕様書
- **design/** - システム設計
  - `05_DataModelDesign.md` - データモデル設計
  - `06_APISpecification.md` - API仕様書
- **planning/** - 実装計画
  - `09_ImplementationPlan.md` - 実装計画・フェーズ管理

### 🚀 02_phase1_mvp/ - Phase1 MVP開発
Phase1 MVP開発の完全な成果物

- **planning/** - フェーズ計画
  - `16_Phase1ImplementationPlan.md` - Phase1詳細実装計画（6週間）
- **technical/** - 技術仕様
  - `17_Phase1TechnicalSpecification.md` - Phase1技術仕様・実装詳細
- **development/** - 開発ガイド
  - `18_Phase1DevelopmentEnvironmentGuide.md` - 開発環境構築ガイド
  - `19_Phase1DatabaseSetupScripts.md` - データベース設定・初期化
- **testing/** - テスト関連
  - `20_Phase1TestPlan.md` - Phase1テスト計画・テストケース
- **deployment/** - デプロイ関連
  - `21_Phase1DeploymentPlan.md` - Phase1デプロイメント計画

### 🔧 05_operations/ - 運用・保守
本番運用・保守の継続的ドキュメント

- **procedures/** - 運用手順
  - `12_TestSpecification.md` - テスト仕様書
  - `13_KnowledgeManagementOperations.md` - 知識管理運用手順

## 🗺️ ドキュメント読み順・学習パス

### 🔰 プロジェクト新参加者向け
1. `00_project_foundation/charter/00_ProjectCharter.md` - プロジェクト概要理解
2. `00_project_foundation/architecture/02_SystemArchitecture.md` - システム全体像把握
3. `01_analysis_design/requirements/01_PRD.md` - プロダクト要件理解
4. `02_phase1_mvp/planning/16_Phase1ImplementationPlan.md` - 現在フェーズ状況

### 🛠️ 開発者向け
1. `02_phase1_mvp/technical/17_Phase1TechnicalSpecification.md` - 技術仕様詳細
2. `02_phase1_mvp/development/18_Phase1DevelopmentEnvironmentGuide.md` - 環境構築
3. `00_project_foundation/standards/14_CodingStandardsGitWorkflow.md` - 開発規約
4. `02_phase1_mvp/testing/20_Phase1TestPlan.md` - テスト要件

### 🚀 デプロイ・運用担当者向け
1. `02_phase1_mvp/deployment/21_Phase1DeploymentPlan.md` - デプロイ戦略
2. `05_operations/procedures/13_KnowledgeManagementOperations.md` - 運用手順
3. `00_project_foundation/standards/11_SecurityDesign.md` - セキュリティ要件

### 📊 プロジェクト管理者向け
1. `00_project_foundation/management/00_DocumentManagementGuideline.md` - 管理方針
2. `00_project_foundation/management/01_PhaseTransitionProcedures.md` - フェーズ移行手順
3. `02_phase1_mvp/planning/16_Phase1ImplementationPlan.md` - 進捗・品質管理

## 📋 Phase1 MVP 完了状況

### ✅ 完了済みドキュメント
- [x] Phase1実装計画（6週間詳細スケジュール）
- [x] Phase1技術仕様（実装詳細・コード例）
- [x] 開発環境構築ガイド（自動化スクリプト含む）
- [x] データベース設計・セットアップスクリプト
- [x] Phase1テスト計画・テストケース
- [x] Phase1デプロイメント計画（Blue-Green戦略）

### 🔄 現在のフェーズ
**Phase1 MVP開発** - ドキュメント準備完了、実装開始準備完了

### 📅 次のマイルストーン
- Phase1実装開始（Week 1: 基盤環境構築）
- Phase2計画ドキュメント作成開始
- 運用体制移行準備

## 🔍 検索・ナビゲーション

### フェーズ別検索
- Phase1関連: `docs/02_phase1_mvp/`
- 基盤・共通: `docs/00_project_foundation/`
- 要件・設計: `docs/01_analysis_design/`
- 運用関連: `docs/05_operations/`

### カテゴリ別検索
- 計画系: `planning/`, `management/`
- 技術系: `technical/`, `development/`
- 品質系: `testing/`, `standards/`
- 運用系: `deployment/`, `operations/`

### メタデータ検索
各ドキュメントのフロントマターで検索可能：
- `doc_type`: ドキュメント種別
- `complexity`: 複雑度レベル
- `prerequisites`: 前提ドキュメント
- `implementation_priority`: 実装優先度

## 🤖 ドキュメント管理

### 更新・メンテナンス
- **責任者**: 各フェーズリーダー + プロジェクトマネージャー
- **更新頻度**: 週次レビュー + 必要時随時
- **品質管理**: フェーズゲート時の包括確認

### バージョン管理
- **Phase完了時**: vX.0.0 タグ付与
- **マイナー更新**: vX.Y.0
- **パッチ更新**: vX.Y.Z

### 問い合わせ・サポート
- ドキュメント関連問題: プロジェクトマネージャー
- 技術的質問: 各フェーズテックリード  
- 管理・プロセス質問: プロジェクト管理チーム

---

**Last Updated**: 2025-01-21 | **Structure Version**: 2.0.0