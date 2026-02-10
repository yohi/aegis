# Requirements: v2-overhaul

# Project Initialization Profile for cc-sdd

## 1. Project Overview (for /kiro:spec-init)

Run the following command to initialize the project:

> OpenCode プラグイン「Aegis」の v2.0 フルリニューアル。モード判定エンジン・スキル解決・アセットデプロイ・セキュリティモデルの全面再設計に加え、Vitest によるテスト基盤と CI/CD パイプラインを導入する。v1 との後方互換性は不要（Breaking Change 許容）。

## 2. Requirements Draft (for requirements.md)

以下の要件定義は **EARS (Easy Approach to Requirements Syntax)** に基づいています。

### 2.1 Mode Detection Engine (モード判定エンジン)

* **REQ-MODE-001**: The system **shall** provide a pluggable mode detection engine that replaces the current keyword-matching approach with an extensible rule-based architecture.
* **REQ-MODE-002**: The system **shall** support user-defined custom modes beyond the built-in PLAN/DEBUG/CODE/GENERAL, configurable via `opencode.json`.
* **REQ-MODE-003**: The system **shall** redesign the mode taxonomy to allow hierarchical or composite modes (e.g., a prompt matching both DEBUG and CODE).
* **REQ-MODE-004**: When multiple modes match a given prompt, the system **shall** resolve conflicts using a configurable priority mechanism (e.g., weight-based scoring or explicit precedence order).
* **REQ-MODE-005**: The system **shall** allow users to extend the built-in keyword dictionaries and matching rules without modifying source code.

### 2.2 Skill Resolution (スキル解決)

* **REQ-SKILL-001**: The system **shall** externalize the `SKILL_MAP` (mode-to-skill mapping) into a user-configurable format (JSON/YAML in `opencode.json` or dedicated config file), removing hard-coded mappings.
* **REQ-SKILL-002**: The system **shall** support skill priority control, allowing users to assign priority weights to skills and enforce a maximum skill count per invocation.
* **REQ-SKILL-003**: The system **shall** expand skill source discovery beyond the local filesystem to support registry-based or remote skill references (future-proofing).
* **REQ-SKILL-004**: The system **shall** emit structured logs or telemetry of skill resolution results (which skills were resolved, from where, cache hit/miss) for observability.
* **REQ-SKILL-005**: The system **shall** maintain the in-memory cache with TTL support and invalidation on `installation.updated` events.

### 2.3 Asset System (アセットシステム)

* **REQ-ASSET-001**: The system **shall** implement versioned asset deployment, tracking deployed asset versions and supporting rollback to previous versions.
* **REQ-ASSET-002**: The system **shall** detect version mismatches between bundled assets and deployed assets, and automatically update when a newer version is available.
* **REQ-ASSET-003**: The system **shall** preserve user modifications to deployed assets by implementing a merge or diff strategy rather than blind overwrite.

### 2.4 Plugin API (プラグイン API 拡張)

* **REQ-API-001**: The system **shall** support additional hook points beyond `tool.execute.before`, including `tool.execute.after` for post-execution processing.
* **REQ-API-002**: The system **shall** provide lifecycle hooks for session start/end, plugin initialization, and plugin teardown events.
* **REQ-API-003**: The system **shall** expose an inter-plugin communication mechanism (event bus or shared context) for coordination with peer plugins (oh-my-opencode, superpowers).
* **REQ-API-004**: The system **shall** support custom tool provision, allowing Aegis to register its own tools (e.g., `aegis_status`, `aegis_diagnose`) into the OpenCode tool palette.

### 2.5 Configuration (設定・コンフィグ)

* **REQ-CFG-001**: The system **shall** define a comprehensive, typed configuration schema for all Aegis settings within `opencode.json`, using a single `aegis` namespace.
* **REQ-CFG-002**: The system **shall** validate all configuration values at plugin initialization and emit clear error messages for invalid entries.
* **REQ-CFG-003**: The system **shall** implement a default-merge strategy where user-provided partial config is deeply merged with built-in defaults, preventing the need to specify every option.

### 2.6 Security (セキュリティ強化)

* **REQ-SEC-001**: The system **shall** strengthen injection bypass prevention by replacing the simple string marker with a cryptographic signature or hash-based verification mechanism.
* **REQ-SEC-002**: The system **shall** emit structured audit logs for all interventions (skill injections, mode detections, bypass attempts), including timestamp, mode, skills injected, and tool target.
* **REQ-SEC-003**: The system **shall** implement a policy engine that enforces mode-specific restrictions on tool usage (e.g., PLAN mode disallows file write tools).
* **REQ-SEC-004**: The system **shall** detect configuration file tampering by computing and verifying checksums of critical config entries at runtime.

### 2.7 Testing & Quality (テスト・品質)

* **REQ-TEST-001**: The system **shall** include unit tests for all logic modules (mode-selector, skill-resolver, safety, installer, config-validator) with ≥80% code coverage target.
* **REQ-TEST-002**: The system **shall** include integration tests that verify the full plugin lifecycle (initialization → hook interception → skill injection → output verification).
* **REQ-TEST-003**: The system **shall** include a CI/CD pipeline (GitHub Actions) that runs lint, type-check, unit tests, integration tests, and pack verification on every PR and release.

### Technical Constraints

* The system **must** be built using **TypeScript (5.x+)** with **ESM** module format, bundled by **tsup**.
* The system **must** target **Node.js 24+** (LTS) as the minimum runtime.
* All test execution and linting **must** occur within the **Devcontainer** environment.
* The system **must** use **Vitest** as the test framework.
* Breaking changes from v1.0.x **are** permitted. No backward compatibility requirement.
* Host-side execution of tests and lint is **prohibited**; these run exclusively in Devcontainer.

## 3. Environment Setup (Devcontainer)

Create `.devcontainer/devcontainer.json` with the following configuration:

```json
{
  "name": "aegis-v2-dev",
  "image": "mcr.microsoft.com/devcontainers/typescript-node:24",
  "customizations": {
    "vscode": {
      "extensions": [
        "dbaeumer.vscode-eslint",
        "esbenp.prettier-vscode",
        "vitest.explorer"
      ],
      "settings": {
        "editor.formatOnSave": true,
        "editor.defaultFormatter": "esbenp.prettier-vscode"
      }
    }
  },
  "postCreateCommand": "npm install",
  "remoteUser": "node"
}
```

## 4. Testing Strategy

* **Unit Tests**: Vitest を使用し、各ロジックモジュール (`mode-selector`, `skill-resolver`, `safety`, `installer`, `config`) を個別にテスト。
* **Integration Tests**: プラグインのフルライフサイクル（初期化 → フック介入 → スキル注入 → 出力検証）をテスト。
* **CI/CD**: GitHub Actions で lint → type-check → test → build → verify-pack を自動実行。
* **Command**: `npx vitest run` (Devcontainer 内で実行)。
* **Coverage Target**: ≥80% line coverage。

```yaml
# .github/workflows/ci.yml (概要)
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    container:
      image: node:24
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm run test -- --coverage
      - run: npm run build
      - run: npm run verify-pack
```
