# Tasks

## Mode Detection Engine

* [ ] v2-mode-1: ルールベース・モード判定エンジンの実装 (Scope: `src/logic/mode-engine.ts`, `src/types/mode.ts`)
  - Acceptance: `determineMode` がカスタムルール・複合モード・優先度解決を処理する。REQ-MODE-001〜005 を満たす。
  - Tests: `test/unit/mode-engine.test.ts`
  - Ref: design.md §2.1, plan TODO #2

## Skill Resolution

* [ ] v2-skill-1: 外部設定ベースのスキル解決エンジンの実装 (Scope: `src/logic/skill-resolver.ts`, `src/types/skill.ts`)
  - Acceptance: SKILL_MAP を外部設定から読み込み、優先度・上限制御・TTL キャッシュが機能する。REQ-SKILL-001〜005 を満たす。
  - Tests: `test/unit/skill-resolver.test.ts`
  - Ref: design.md §2.2, plan TODO #3

## Configuration

* [ ] v2-config-1: 型付きコンフィグスキーマとバリデーションの実装 (Scope: `src/logic/config.ts`, `src/schemas/config-schema.ts`)
  - Acceptance: `opencode.json` の `aegis` 名前空間から設定をロード・検証し、デフォルトマージが機能する。REQ-CFG-001〜003 を満たす。
  - Tests: `test/unit/config.test.ts`
  - Ref: design.md §2.5, plan TODO #4

## Asset System

* [ ] v2-asset-1: バージョン管理付きアセットデプロイの実装 (Scope: `src/logic/asset-manager.ts`, `scripts/deploy.ts`)
  - Acceptance: アセットのバージョン追跡、ミスマッチ検出、ロールバック、ユーザー変更のマージ保護が機能する。REQ-ASSET-001〜003 を満たす。
  - Tests: `test/integration/asset-deploy.test.ts`
  - Ref: design.md §2.3, plan TODO #5

## Plugin API

* [ ] v2-pluginapi-1: フック拡張・ライフサイクル・ツール登録の実装 (Scope: `src/index.ts`, `src/api/hooks.ts`, `src/api/tools.ts`)
  - Acceptance: `tool.execute.after`、セッションライフサイクルフック、カスタムツール登録（`aegis_status`, `aegis_diagnose`）が機能する。REQ-API-001〜004 を満たす。
  - Tests: `test/integration/plugin-lifecycle.test.ts`
  - Ref: design.md §2.4, plan TODO #6

## Security

* [ ] v2-security-1: 暗号署名・監査ログ・ポリシーエンジンの実装 (Scope: `src/logic/security.ts`, `src/audit/logger.ts`, `src/policy/engine.ts`)
  - Acceptance: インジェクションバイパスが暗号署名で検証され、構造化監査ログが出力され、モード別ツール制限ポリシーが適用される。REQ-SEC-001〜004 を満たす。
  - Tests: `test/unit/security.test.ts`
  - Ref: design.md §2.6, plan TODO #7

## Testing & CI

* [ ] v2-testing-1: Vitest テスト基盤・CI/CD パイプラインの構築 (Scope: `vitest.config.ts`, `.github/workflows/ci.yml`, `.devcontainer/devcontainer.json`)
  - Acceptance: Vitest で全ユニット/統合テストが実行可能、GitHub Actions で lint → typecheck → test → build → verify-pack が自動実行される。REQ-TEST-001〜003 を満たす。
  - Ref: design.md §2.7, plan TODO #8
