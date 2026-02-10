# Aegis v2 Overhaul Plan

## TL;DR
> **Quick Summary**: Aegis v2 へのフルリニューアル。モード判定、スキル解決、アセット管理、API、設定、セキュリティ、テスト基盤の全領域を刷新する。
> **Deliverables**:
> - v2 仕様準拠のソースコード一式
> - Vitest によるテストコード
> - GitHub Actions CI/CD パイプライン
> **Estimated Effort**: Large
> **Critical Path**: Config/Mode/Skill (Core) -> Asset/API/Security (Feature) -> Test/CI (Quality)

---

## Context
v1.0.16 からのメジャーアップデート。後方互換性を捨て、アーキテクチャを刷新する。
SDD (Spec-Driven Development) に完全準拠し、`requirements.md`, `design.md` に基づいて実装する。

## Work Objectives
1. **Mode Engine**: ルールベース、カスタムモード、優先度制御
2. **Skill Resolution**: 外部設定、優先度、レジストリ対応
3. **Asset System**: バージョン管理、ロールバック
4. **Plugin API**: フック拡張、ライフサイクル、ツール登録
5. **Configuration**: スキーマ定義、バリデーション
6. **Security**: インジェクション防止、監査ログ、ポリシー
7. **Quality**: Vitest, CI/CD

---

## Verification Strategy
- **Framework**: Vitest (Unit/Integration)
- **CI**: GitHub Actions
- **Agent-Executed QA**:
  - `npm run test` (Unit/Integration)
  - `npm run verify-pack` (Build artifact check)
  - `npm run lint` (Static analysis)

---

## TODOs

- [ ] 1. **Initialize Task List**
  - **What**: Update `.kiro/specs/v2-overhaul/tasks.md` with the detailed task list below.
  - **Why**: The current `tasks.md` is too generic.
  - **Agent**: `quick`
  - **Verification**: `cat .kiro/specs/v2-overhaul/tasks.md` matches expected content.
  - **Acceptance Criteria**:
    - [ ] `tasks.md` updated with v2-* tasks.
    - [ ] `sdd_sync_kiro` executed to reflect changes in root `tasks.md`. *(NOTE: SDD フレームワーク組込みツール。手動実行: `sdd_sync_kiro` コマンドを呼び出し、`.kiro/specs/**/tasks.md` → `specs/tasks.md` への同期を実行する)*

- [ ] 2. **Implement Mode Detection Engine (v2-mode-1)**
  - **What**: Implement `src/logic/mode-engine.ts`, `src/types/mode.ts`.
  - **Ref**: `requirements.md` (REQ-MODE-*), `design.md` (2.1 Mode Detection)
  - **Tests**: `test/unit/mode-engine.test.ts`
  - **Agent**: `visual-engineering` (TypeScript logic)
  - **Acceptance Criteria**:
    - [ ] `determineMode` function handles custom rules.
    - [ ] Tests pass for complex prompt patterns.

- [ ] 3. **Implement Skill Resolution (v2-skill-1)**
  - **What**: Implement `src/logic/skill-resolver.ts`, `src/types/skill.ts`.
  - **Ref**: `requirements.md` (REQ-SKILL-*), `design.md` (2.2 Skill Resolution)
  - **Tests**: `test/unit/skill-resolver.test.ts`
  - **Agent**: `visual-engineering`
  - **Acceptance Criteria**:
    - [ ] Skills resolved from config map.
    - [ ] Priority and limits enforced.

- [ ] 4. **Implement Configuration System (v2-config-1)**
  - **What**: Implement `src/logic/config.ts`, `src/schemas/config.json`.
  - **Ref**: `requirements.md` (REQ-CFG-*), `design.md` (2.5 Configuration)
  - **Tests**: `test/unit/config.test.ts`
  - **Agent**: `visual-engineering`
  - **Acceptance Criteria**:
    - [ ] Config loads from `opencode.json`.
    - [ ] Validation errors reported clearly.

- [ ] 5. **Implement Asset System (v2-asset-1)**
  - **What**: Implement `scripts/verify-pack.cjs`, `scripts/deploy.ts`.
  - **Ref**: `requirements.md` (REQ-ASSET-*), `design.md` (2.3 Asset System)
  - **Tests**: `test/integration/asset-deploy.test.ts`
  - **Agent**: `visual-engineering`
  - **Acceptance Criteria**:
    - [ ] Assets deployed with version tracking.
    - [ ] Rollback works on failure.

- [ ] 6. **Implement Plugin API (v2-api-1)**
  - **What**: Implement `src/index.ts`, `src/api/hooks.ts`.
  - **Ref**: `requirements.md` (REQ-API-*), `design.md` (2.4 Plugin API)
  - **Tests**: `test/integration/plugin-lifecycle.test.ts`
  - **Agent**: `visual-engineering`
  - **Acceptance Criteria**:
    - [ ] New hooks (`execute.after`) fire correctly.
    - [ ] Custom tools registered.

- [ ] 7. **Implement Security Features (v2-sec-1)**
  - **What**: Implement `src/logic/security.ts`, `src/audit/logger.ts`.
  - **Ref**: `requirements.md` (REQ-SEC-*), `design.md` (2.6 Security)
  - **Tests**: `test/unit/security.test.ts`
  - **Agent**: `visual-engineering`
  - **Acceptance Criteria**:
    - [ ] Injection bypass verified cryptographically.
    - [ ] Audit logs generated.

- [ ] 8. **Setup Testing & CI (v2-test-1)**
  - **What**: Setup `vitest`, `.github/workflows/ci.yml`.
  - **Ref**: `requirements.md` (REQ-TEST-*), `design.md` (2.7 Testing)
  - **Verification**: CI passes on GitHub.
  - **Agent**: `visual-engineering`
  - **Acceptance Criteria**:
    - [ ] Vitest runs successfully in local & CI.
    - [ ] Lint/Build checks pass.
