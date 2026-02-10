# Tasks

## Core Layer (基盤)

* [ ] v2-config-1: 設定スキーマ定義・バリデーション・デフォルトマージ実装 (Scope: `src/logic/config.ts`, `src/types/config.ts`)
  - 受入条件: `AegisConfig` スキーマに準拠した設定読み込み、型チェック + 値範囲バリデーション、ディープマージ動作確認
  - REF: REQ-CFG-001, REQ-CFG-002, REQ-CFG-003 / design.md §2.5

* [ ] v2-mode-1: ルールベースモード判定エンジン実装 (Scope: `src/logic/mode-engine.ts`, `src/types/mode.ts`)
  - 受入条件: `ModeEngine.determine()` がビルトイン + カスタムルールで動作、複合モード対応、優先度解決
  - REF: REQ-MODE-001, REQ-MODE-002, REQ-MODE-003, REQ-MODE-004, REQ-MODE-005 / design.md §2.1

* [ ] v2-skill-1: スキル解決の外部設定化・優先度・キャッシュ・テレメトリ実装 (Scope: `src/logic/skill-resolver.ts`, `src/types/skill.ts`)
  - 受入条件: 外部設定からスキルマップ読み込み、優先度ソート + maxSkills 制限、TTL キャッシュ、テレメトリ出力
  - REF: REQ-SKILL-001, REQ-SKILL-002, REQ-SKILL-003, REQ-SKILL-004, REQ-SKILL-005 / design.md §2.2

## Feature Layer (機能)

* [ ] v2-asset-1: バージョン管理付きアセットデプロイ・ロールバック・マージ戦略実装 (Scope: `src/logic/asset-manager.ts`, `src/types/asset.ts`)
  - 受入条件: マニフェストベースのバージョン追跡、3-way マージによるユーザー修正保持、ロールバック動作
  - REF: REQ-ASSET-001, REQ-ASSET-002, REQ-ASSET-003 / design.md §2.3

* [ ] v2-pluginapi-1: フック拡張・ライフサイクル・ツール登録・イベントバス実装 (Scope: `src/api/hooks.ts`, `src/api/lifecycle.ts`, `src/api/tool-registry.ts`, `src/api/event-bus.ts`, `src/types/hooks.ts`)
  - 受入条件: `tool.execute.after` フック動作、セッション/プラグインライフサイクルフック発火、カスタムツール登録、プラグイン間通信
  - REF: REQ-API-001, REQ-API-002, REQ-API-003, REQ-API-004 / design.md §2.4

* [ ] v2-security-1: 暗号署名・監査ログ・ポリシーエンジン・改ざん検知実装 (Scope: `src/logic/security.ts`, `src/logic/policy-engine.ts`, `src/audit/logger.ts`, `src/types/audit.ts`)
  - 受入条件: HMAC-SHA256 署名による二重注入防止、構造化監査ログ出力、モード別ツール制限ポリシー、設定チェックサム検証
  - REF: REQ-SEC-001, REQ-SEC-002, REQ-SEC-003, REQ-SEC-004 / design.md §2.6

## Quality Layer (品質)

* [ ] v2-testing-1: Vitest テスト基盤・ユニットテスト・統合テスト実装 (Scope: `test/**`, `vitest.config.ts`)
  - 受入条件: 全ロジックモジュールのユニットテスト (≥80% coverage)、プラグインライフサイクル統合テスト
  - REF: REQ-TEST-001, REQ-TEST-002 / design.md §2.7

* [ ] v2-ci-1: GitHub Actions CI/CD パイプライン構築 (Scope: `.github/workflows/ci.yml`)
  - 受入条件: lint → typecheck → test (coverage) → build → verify-pack の自動実行、PR/push トリガー
  - REF: REQ-TEST-003 / design.md §2.7.3

## Integration (統合)

* [ ] v2-entry-1: プラグインエントリポイント統合 (Scope: `src/index.ts`)
  - 受入条件: 全モジュールを統合した初期化フロー、v2 フック登録、package.json 更新
  - REF: design.md §1.3
