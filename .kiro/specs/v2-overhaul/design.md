# Design: v2-overhaul

**Version:** 2.0.0-alpha
**Date:** 2026-02-11
**Status:** Draft
**Ref:** `requirements.md` (REQ-MODE/SKILL/ASSET/API/CFG/SEC/TEST)
**Plan:** `.sisyphus/plans/v2-overhaul.md` (TODO #1–#8)

---

## 1. システムアーキテクチャ (System Architecture)

### 1.1 アーキテクチャ概要図

```
┌─────────────────────────────────────────────────────────────────┐
│                    OpenCode Host Runtime                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                     Plugin Loader                         │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │  │
│  │  │ Oh-My-OC    │  │   Aegis v2   │  │  Superpowers    │  │  │
│  │  │ (Context)   │◄─┤  (Control)   ├─►│  (Power)        │  │  │
│  │  └─────────────┘  └──────┬───────┘  └─────────────────┘  │  │
│  └──────────────────────────┼────────────────────────────────┘  │
│                             │                                   │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │                   Aegis v2 Internal                       │  │
│  │                                                           │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │  │
│  │  │  Lifecycle    │  │  Hook        │  │  Tool          │  │  │
│  │  │  Manager      │  │  Dispatcher  │  │  Registry      │  │  │
│  │  └──────┬───────┘  └──────┬───────┘  └────────┬───────┘  │  │
│  │         │                 │                    │          │  │
│  │  ┌──────▼─────────────────▼────────────────────▼───────┐  │  │
│  │  │              Core Engine Layer                       │  │  │
│  │  │  ┌────────────┐ ┌──────────────┐ ┌───────────────┐  │  │  │
│  │  │  │ Mode       │ │ Skill        │ │ Config        │  │  │  │
│  │  │  │ Engine     │ │ Resolver     │ │ Manager       │  │  │  │
│  │  │  └─────┬──────┘ └──────┬───────┘ └───────┬───────┘  │  │  │
│  │  │        │               │                  │          │  │  │
│  │  │  ┌─────▼───────────────▼──────────────────▼───────┐  │  │  │
│  │  │  │           Security Layer                        │  │  │  │
│  │  │  │  ┌──────────┐ ┌───────────┐ ┌───────────────┐  │  │  │  │
│  │  │  │  │ Crypto   │ │ Policy    │ │ Audit         │  │  │  │  │
│  │  │  │  │ Verifier │ │ Engine    │ │ Logger        │  │  │  │  │
│  │  │  │  └──────────┘ └───────────┘ └───────────────┘  │  │  │  │
│  │  │  └────────────────────────────────────────────────┘  │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │                                                           │  │
│  │  ┌──────────────────┐  ┌──────────────────────────────┐   │  │
│  │  │  Asset Manager   │  │  Event Bus (Inter-Plugin)    │   │  │
│  │  │  (Deploy/Version)│  │  (Pub/Sub)                   │   │  │
│  │  └──────────────────┘  └──────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Filesystem / opencode.json                    │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 モジュール依存関係

| モジュール | ファイルパス | 依存先 | 担当 REQ |
|-----------|-------------|--------|---------|
| **Config Manager** | `src/logic/config.ts` | — (ルートモジュール) | REQ-CFG-* |
| **Mode Engine** | `src/logic/mode-engine.ts` | Config Manager | REQ-MODE-* |
| **Skill Resolver** | `src/logic/skill-resolver.ts` | Config Manager, Mode Engine | REQ-SKILL-* |
| **Security Layer** | `src/logic/security.ts` | Config Manager | REQ-SEC-* |
| **Audit Logger** | `src/audit/logger.ts` | Security Layer | REQ-SEC-002 |
| **Policy Engine** | `src/logic/policy-engine.ts` | Config Manager, Mode Engine | REQ-SEC-003 |
| **Asset Manager** | `src/logic/asset-manager.ts` | Config Manager | REQ-ASSET-* |
| **Hook Dispatcher** | `src/api/hooks.ts` | Security Layer | REQ-API-001, REQ-API-002 |
| **Tool Registry** | `src/api/tool-registry.ts` | — | REQ-API-004 |
| **Event Bus** | `src/api/event-bus.ts` | — | REQ-API-003 |
| **Lifecycle Manager** | `src/api/lifecycle.ts` | Hook Dispatcher, Event Bus | REQ-API-002 |
| **Plugin Entry** | `src/index.ts` | All modules | — |

### 1.3 初期化フロー

```
Plugin Load
  │
  ├─1→ ConfigManager.load(opencode.json)     [REQ-CFG-001/002/003]
  │      └─ スキーマ検証 + デフォルトマージ
  │
  ├─2→ SecurityLayer.init(config)             [REQ-SEC-001/004]
  │      └─ 署名鍵生成 + 設定チェックサム計算
  │
  ├─3→ ModeEngine.init(config.modes)          [REQ-MODE-001/002]
  │      └─ ルール登録 + カスタムモード読み込み
  │
  ├─4→ SkillResolver.init(config.skills)      [REQ-SKILL-001/005]
  │      └─ スキルマップ読み込み + キャッシュ初期化
  │
  ├─5→ AssetManager.deploy(rootDir)           [REQ-ASSET-001/002]
  │      └─ バージョン比較 + デプロイ/マージ
  │
  ├─6→ ToolRegistry.register(tools)           [REQ-API-004]
  │      └─ カスタムツール登録
  │
  ├─7→ LifecycleManager.emit("session.start") [REQ-API-002]
  │
  └─8→ HookDispatcher.register(hooks)         [REQ-API-001]
```

---

## 2. 詳細設計 (Detailed Design)

### 2.1 Mode Detection Engine (モード判定エンジン)

**対応要件:** REQ-MODE-001, REQ-MODE-002, REQ-MODE-003, REQ-MODE-004, REQ-MODE-005
**Plan 参照:** `.sisyphus/plans/v2-overhaul.md` TODO #2 (L50–57)

#### 2.1.1 設計方針

v1 のキーワードマッチングを、拡張可能なルールベースエンジンに置換する。
各ルールは独立した `ModeRule` オブジェクトとして定義され、`opencode.json` から
ユーザー定義ルールを追加可能にする。

#### 2.1.2 ルール評価フロー

```
Prompt Input
  │
  ├─1→ ルールリスト取得 (built-in + custom from config)
  │
  ├─2→ 各ルールの evaluate(prompt) を実行
  │      └─ 返り値: { mode: string, score: number, matched: boolean }
  │
  ├─3→ matched=true のルールを score 降順でソート
  │
  ├─4→ 同一 mode の最高スコアを集約
  │
  ├─5→ 階層モード対応: 複合モードの場合は CompositeMode を返す
  │      └─ 例: ["DEBUG", "CODE"] → { primary: "DEBUG", secondary: ["CODE"] }
  │
  └─6→ 最終モード決定 (最高スコア or priority override)
```

#### 2.1.3 ビルトインルール

| ルール名 | 対象モード | マッチ条件 | デフォルト重み |
|---------|----------|-----------|-------------|
| `plan-keywords` | PLAN | `plan`, `strategy`, `architecture`, `計画`, `設計`, `方針` | 100 |
| `debug-keywords` | DEBUG | `debug`, `fix`, `error`, `fail`, `デバッグ`, `修正`, `エラー` | 100 |
| `code-keywords` | CODE | `implement`, `refactor`, `code`, `実装`, `コード`, `リファクタ` | 100 |
| `general-fallback` | GENERAL | 常にマッチ | 0 |

#### 2.1.4 カスタムモード定義 (opencode.json)

```json
{
  "aegis": {
    "modes": {
      "custom": {
        "REVIEW": {
          "rules": [
            { "type": "keyword", "words": ["review", "レビュー", "PR"], "weight": 120 }
          ],
          "parent": "CODE"
        }
      },
      "overrides": {
        "PLAN": {
          "additionalKeywords": ["roadmap", "ロードマップ"],
          "weight": 110
        }
      }
    }
  }
}
```

### 2.2 Skill Resolution (スキル解決)

**対応要件:** REQ-SKILL-001, REQ-SKILL-002, REQ-SKILL-003, REQ-SKILL-004, REQ-SKILL-005
**Plan 参照:** `.sisyphus/plans/v2-overhaul.md` TODO #3 (L59–66)

#### 2.2.1 設計方針

ハードコードされた `SKILL_MAP` を外部設定化し、優先度制御・最大数制限・
レジストリ参照・テレメトリ出力を追加する。

#### 2.2.2 スキル解決フロー

```
Mode (from ModeEngine)
  │
  ├─1→ SkillMap 取得 (config.aegis.skills.map)        [REQ-SKILL-001]
  │      └─ デフォルトマップ + ユーザーオーバーライド
  │
  ├─2→ 候補スキルリスト生成 (mode → skill names)
  │
  ├─3→ 各スキルのソース解決                            [REQ-SKILL-003]
  │      ├─ Local: ファイルシステム検索 (既存ロジック継承)
  │      └─ Registry: (将来) レジストリ参照 (stub)
  │
  ├─4→ キャッシュチェック (TTL + event invalidation)    [REQ-SKILL-005]
  │      └─ Hit → キャッシュから返却
  │      └─ Miss → ディスク検索 → キャッシュ格納
  │
  ├─5→ 優先度ソート + maxSkills 制限                    [REQ-SKILL-002]
  │      └─ skill.priority 降順、上限超過分は切り捨て
  │
  └─6→ テレメトリ出力                                   [REQ-SKILL-004]
         └─ { mode, resolved: [...], source: "local"|"cache", cacheHit: bool }
```

#### 2.2.3 外部設定 (opencode.json)

```json
{
  "aegis": {
    "skills": {
      "map": {
        "PLAN": [
          { "name": "writing-plans", "priority": 10 },
          { "name": "brainstorming", "priority": 5 }
        ],
        "DEBUG": [
          { "name": "systematic-debugging", "priority": 10 },
          { "name": "verification-before-completion", "priority": 8 }
        ],
        "CODE": [
          { "name": "test-driven-development", "priority": 10 },
          { "name": "requesting-code-review", "priority": 5 }
        ],
        "GENERAL": []
      },
      "maxSkills": 5,
      "cache": {
        "ttl": 300000,
        "enabled": true
      }
    }
  }
}
```

### 2.3 Asset System (アセットシステム)

**対応要件:** REQ-ASSET-001, REQ-ASSET-002, REQ-ASSET-003
**Plan 参照:** `.sisyphus/plans/v2-overhaul.md` TODO #5 (L77–84)

#### 2.3.1 設計方針

v1 の Sentinel ベースのデプロイを、バージョン管理・ロールバック・
マージ戦略に対応したシステムに置換する。

#### 2.3.2 バージョン管理

```
assets/commands/
  ├── .aegis-manifest.json    ← NEW: バージョン + チェックサム管理
  ├── .aegis-sentinel
  ├── aegis-refine-plan.md
  └── aegis-doctor.md

.opencode/commands/
  ├── .aegis-manifest.json    ← デプロイ先にもコピー
  ├── .aegis-user-manifest.json  ← NEW: ユーザー修正追跡
  ├── .aegis-sentinel
  ├── aegis-refine-plan.md
  └── aegis-doctor.md
```

#### 2.3.3 マニフェスト形式

```json
{
  "version": "2.0.0",
  "deployedAt": "2026-02-11T13:00:00Z",
  "files": {
    "aegis-refine-plan.md": {
      "hash": "sha256:abc123...",
      "version": "2.0.0"
    },
    "aegis-doctor.md": {
      "hash": "sha256:def456...",
      "version": "2.0.0"
    }
  }
}
```

#### 2.3.4 デプロイ戦略

| シナリオ | 動作 | REQ |
|---------|------|-----|
| 初回デプロイ | 全ファイルコピー + マニフェスト作成 | REQ-ASSET-001 |
| バージョン不一致 | マニフェスト比較 → 差分更新 | REQ-ASSET-002 |
| ユーザー修正あり | 3-way マージ (base ↔ new ↔ user) | REQ-ASSET-003 |
| マージ競合 | `.conflict` ファイル生成 + 警告ログ | REQ-ASSET-003 |
| ロールバック | `rollback(version)` でマニフェスト指定版に復元 | REQ-ASSET-001 |

#### 2.3.5 ロールバック機構

```
.opencode/commands/.aegis-history/
  ├── 1.0.16/                    ← 旧バージョンバックアップ
  │   ├── .aegis-manifest.json
  │   └── *.md
  └── 2.0.0/
      └── ...
```

### 2.4 Plugin API (プラグイン API 拡張)

**対応要件:** REQ-API-001, REQ-API-002, REQ-API-003, REQ-API-004
**Plan 参照:** `.sisyphus/plans/v2-overhaul.md` TODO #6 (L86–93)

#### 2.4.1 Hook ライフサイクル

```
                    Plugin Lifecycle
                    ═══════════════
   ┌─────────────────────────────────────────────────┐
   │                                                 │
   │  session.start ──► tool.execute.before ──►      │
   │                    tool.execute.after  ──►      │
   │                    ... (repeat per tool call)   │
   │                                                 │
   │  session.end ──► plugin.teardown                │
   │                                                 │
   └─────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────┐
   │              Plugin Events                       │
   │                                                 │
   │  plugin.init ──► installation.updated           │
   │                                                 │
   └─────────────────────────────────────────────────┘
```

#### 2.4.2 Hook 一覧

| Hook 名 | タイミング | 引数 | REQ |
|---------|----------|------|-----|
| `plugin.init` | プラグイン初期化時 | `{ config, directory }` | REQ-API-002 |
| `plugin.teardown` | プラグイン終了時 | `{ reason }` | REQ-API-002 |
| `session.start` | セッション開始時 | `{ sessionId, directory }` | REQ-API-002 |
| `session.end` | セッション終了時 | `{ sessionId, stats }` | REQ-API-002 |
| `tool.execute.before` | ツール実行前 | `{ input, output }` (既存) | REQ-API-001 |
| `tool.execute.after` | ツール実行後 | `{ input, result, duration }` | REQ-API-001 |
| `installation.updated` | プラグイン更新時 | `{}` (既存) | — |

#### 2.4.3 プラグイン間通信 (Event Bus)

```typescript
// Oh-My-OpenCode → Aegis への通知例
eventBus.emit("omo:context-changed", { newContext: "..." });

// Aegis → Superpowers への通知例
eventBus.emit("aegis:skills-resolved", { mode: "DEBUG", skills: [...] });
```

#### 2.4.4 カスタムツール登録

```typescript
// Aegis が OpenCode に登録するカスタムツール
const tools = [
  {
    name: "aegis_status",
    description: "現在の Aegis 設定・モード・キャッシュ状態を表示",
    handler: async () => ({ mode, skills, cacheStats })
  },
  {
    name: "aegis_diagnose",
    description: "環境診断 (アセット状態、設定整合性、依存関係)",
    handler: async () => ({ assets, config, dependencies })
  }
];
```

### 2.5 Configuration (設定・コンフィグ)

**対応要件:** REQ-CFG-001, REQ-CFG-002, REQ-CFG-003
**Plan 参照:** `.sisyphus/plans/v2-overhaul.md` TODO #4 (L68–75)

#### 2.5.1 設定スキーマ (opencode.json)

```json
{
  "aegis": {
    "targetTools": ["sisyphus_task", "delegate_task"],
    "modes": {
      "custom": {},
      "overrides": {}
    },
    "skills": {
      "map": {},
      "maxSkills": 5,
      "cache": {
        "ttl": 300000,
        "enabled": true
      }
    },
    "assets": {
      "autoUpdate": true,
      "mergeStrategy": "three-way",
      "historyLimit": 3
    },
    "security": {
      "signatureAlgorithm": "hmac-sha256",
      "auditLog": {
        "enabled": true,
        "level": "info",
        "destination": "stderr"
      },
      "policy": {
        "enabled": false,
        "rules": []
      },
      "configIntegrity": {
        "enabled": true
      }
    },
    "telemetry": {
      "enabled": false,
      "level": "info"
    }
  }
}
```

#### 2.5.2 バリデーション戦略

```
opencode.json 読み込み
  │
  ├─1→ JSON パース
  │      └─ 失敗時: AegisConfigError("Invalid JSON") を throw
  │
  ├─2→ aegis ネームスペース抽出
  │      └─ 未定義時: デフォルト設定全体を使用
  │
  ├─3→ スキーマバリデーション (型チェック + 値範囲)  [REQ-CFG-002]
  │      └─ 各フィールドの型/範囲/必須を検証
  │      └─ 失敗時: フィールドごとの明確なエラーメッセージ
  │
  └─4→ デフォルトマージ (deep merge)                [REQ-CFG-003]
         └─ ユーザー部分設定 + ビルトインデフォルト → 完全設定
```

#### 2.5.3 デフォルトマージ仕様

- **プリミティブ値**: ユーザー値で上書き
- **オブジェクト**: 再帰的にディープマージ
- **配列**: ユーザー値で完全置換 (マージしない)
- **未指定フィールド**: デフォルト値を使用

### 2.6 Security (セキュリティ強化)

**対応要件:** REQ-SEC-001, REQ-SEC-002, REQ-SEC-003, REQ-SEC-004
**Plan 参照:** `.sisyphus/plans/v2-overhaul.md` TODO #7 (L95–102)

#### 2.6.1 暗号署名ベースのインジェクション検証

v1 の `__AEGIS_INJECTED_v1__` マーカー文字列を、HMAC-SHA256 署名に置換する。

```
注入フロー:
  1. セッション開始時にランダムシークレット生成 (session-scoped)
  2. プロンプト注入時:
     signature = HMAC-SHA256(secret, prompt_hash + timestamp)
     injection_header = `__AEGIS_SIG_v2__:${signature}:${timestamp}`
  3. 二重注入チェック時:
     ヘッダー抽出 → 署名検証 → タイムスタンプ有効期限チェック
     → 不正な場合: 監査ログ出力 + 介入続行
```

#### 2.6.2 監査ログ

```typescript
// 監査ログエントリ例
{
  timestamp: "2026-02-11T13:00:00.000Z",
  event: "skill_injection",
  data: {
    mode: "DEBUG",
    skills: ["systematic-debugging", "verification-before-completion"],
    toolTarget: "sisyphus_task",
    bypassAttempted: false,
    signatureValid: true
  }
}
```

| イベント種別 | 記録タイミング | REQ |
|------------|-------------|-----|
| `skill_injection` | スキル注入実行時 | REQ-SEC-002 |
| `mode_detection` | モード判定完了時 | REQ-SEC-002 |
| `bypass_attempt` | バイパス試行検出時 | REQ-SEC-002 |
| `policy_violation` | ポリシー違反検出時 | REQ-SEC-003 |
| `config_tamper` | 設定改ざん検出時 | REQ-SEC-004 |

#### 2.6.3 ポリシーエンジン

モード別のツール利用制限を定義・実施する。

```json
{
  "aegis": {
    "security": {
      "policy": {
        "enabled": true,
        "rules": [
          {
            "mode": "PLAN",
            "deny": ["file_write", "bash_execute", "git_commit"],
            "action": "block",
            "message": "PLAN モードではファイル書き込み/実行系ツールは使用できません"
          }
        ]
      }
    }
  }
}
```

#### 2.6.4 設定ファイル改ざん検知

```
初期化時:
  1. opencode.json の aegis セクションのチェックサム (SHA-256) を計算
  2. メモリに保持

各フック実行時:
  1. 現在の opencode.json を再読み込み
  2. チェックサム再計算 → 保持値と比較
  3. 不一致: 監査ログ出力 + 設定再読み込み or 拒否 (configIntegrity 設定による)
```

### 2.7 Testing (テスト・品質)

**対応要件:** REQ-TEST-001, REQ-TEST-002, REQ-TEST-003
**Plan 参照:** `.sisyphus/plans/v2-overhaul.md` TODO #8 (L104–111)

#### 2.7.1 テスト構造

```
test/
  ├── unit/
  │   ├── mode-engine.test.ts        ← REQ-MODE-* テスト
  │   ├── skill-resolver.test.ts     ← REQ-SKILL-* テスト
  │   ├── config.test.ts             ← REQ-CFG-* テスト
  │   ├── security.test.ts           ← REQ-SEC-001/004 テスト
  │   ├── policy-engine.test.ts      ← REQ-SEC-003 テスト
  │   ├── audit-logger.test.ts       ← REQ-SEC-002 テスト
  │   └── asset-manager.test.ts      ← REQ-ASSET-* テスト
  │
  ├── integration/
  │   ├── plugin-lifecycle.test.ts   ← REQ-API-* テスト
  │   ├── asset-deploy.test.ts       ← REQ-ASSET-* E2E テスト
  │   └── full-pipeline.test.ts      ← 全体統合テスト
  │
  └── fixtures/
      ├── opencode.json              ← テスト用設定
      ├── skills/                    ← モックスキルディレクトリ
      └── assets/                    ← テスト用アセット
```

#### 2.7.2 カバレッジ戦略

| モジュール | 目標カバレッジ | テスト種別 |
|-----------|-------------|----------|
| mode-engine | ≥90% | Unit (パターン網羅) |
| skill-resolver | ≥85% | Unit + Integration |
| config | ≥90% | Unit (バリデーション) |
| security | ≥85% | Unit (暗号検証) |
| policy-engine | ≥90% | Unit (ルール網羅) |
| asset-manager | ≥80% | Unit + Integration |
| plugin lifecycle | ≥75% | Integration |
| **全体** | **≥80%** | — |

#### 2.7.3 CI/CD パイプライン

```yaml
# .github/workflows/ci.yml
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

---

## 3. データモデル (Data Model)

### 3.1 型定義 (`src/types/mode.ts`)

```typescript
/** モード識別子。ビルトイン + ユーザー定義 */
export type BuiltinMode = "PLAN" | "DEBUG" | "CODE" | "GENERAL";
export type AegisMode = BuiltinMode | string;

/** 複合モード (REQ-MODE-003) */
export interface CompositeMode {
  /** 最も高スコアのモード */
  primary: AegisMode;
  /** 同時にマッチした副次モード */
  secondary: AegisMode[];
}

/** モード判定ルール (REQ-MODE-001, REQ-MODE-005) */
export interface ModeRule {
  /** ルール識別名 */
  name: string;
  /** 対象モード */
  mode: AegisMode;
  /** マッチ条件タイプ */
  type: "keyword" | "regex" | "custom";
  /** キーワードリスト (type="keyword" 時) */
  words?: string[];
  /** 正規表現パターン (type="regex" 時) */
  pattern?: string;
  /** カスタム評価関数 (type="custom" 時) */
  evaluate?: (prompt: string) => ModeMatchResult;
  /** 重み (高い方が優先) */
  weight: number;
}

/** ルール評価結果 */
export interface ModeMatchResult {
  mode: AegisMode;
  score: number;
  matched: boolean;
  /** マッチしたキーワード/パターン (デバッグ用) */
  matchedBy?: string;
}

/** モード判定の最終結果 */
export interface ModeResolutionResult {
  /** 決定されたモード (単一 or 複合) */
  resolved: AegisMode | CompositeMode;
  /** 各ルールの評価結果 */
  evaluations: ModeMatchResult[];
  /** 判定にかかった時間 (ms) */
  duration: number;
}

/** カスタムモード定義 (REQ-MODE-002) */
export interface CustomModeDefinition {
  rules: Omit<ModeRule, "name" | "mode">[];
  /** 親モードからルールを継承 */
  parent?: AegisMode;
}
```

### 3.2 型定義 (`src/types/skill.ts`)

```typescript
/** スキルエントリ (REQ-SKILL-001) */
export interface SkillEntry {
  /** スキル名 (ディレクトリパス形式: e.g., "superpowers/writing-plans") */
  name: string;
  /** 優先度 (REQ-SKILL-002) */
  priority: number;
}

/** スキル解決結果 (REQ-SKILL-004) */
export interface SkillResolutionResult {
  /** 解決されたスキルリスト */
  skills: ResolvedSkill[];
  /** テレメトリ情報 */
  telemetry: SkillTelemetry;
}

/** 解決済みスキル */
export interface ResolvedSkill {
  /** スキル名 */
  name: string;
  /** スキルのソース ("local" | "registry") */
  source: "local" | "registry";
  /** 解決元のファイルパス (local の場合) */
  resolvedPath?: string;
}

/** スキルテレメトリ (REQ-SKILL-004) */
export interface SkillTelemetry {
  mode: string;
  resolved: string[];
  source: "local" | "cache";
  cacheHit: boolean;
  duration: number;
}

/** スキルキャッシュエントリ (REQ-SKILL-005) */
export interface SkillCacheEntry {
  skills: ResolvedSkill[];
  cachedAt: number;
  ttl: number;
}
```

### 3.3 型定義 (`src/types/config.ts`)

```typescript
/** Aegis 設定スキーマ全体 (REQ-CFG-001) */
export interface AegisConfig {
  /** 介入対象ツール名 */
  targetTools: string[];

  /** モード設定 */
  modes: {
    custom: Record<string, CustomModeDefinition>;
    overrides: Record<string, ModeOverride>;
  };

  /** スキル設定 */
  skills: {
    map: Record<string, SkillEntry[]>;
    maxSkills: number;
    cache: {
      ttl: number;
      enabled: boolean;
    };
  };

  /** アセット設定 */
  assets: {
    autoUpdate: boolean;
    mergeStrategy: "overwrite" | "three-way" | "skip";
    historyLimit: number;
  };

  /** セキュリティ設定 */
  security: {
    signatureAlgorithm: "hmac-sha256";
    auditLog: AuditLogConfig;
    policy: PolicyConfig;
    configIntegrity: {
      enabled: boolean;
    };
  };

  /** テレメトリ設定 */
  telemetry: {
    enabled: boolean;
    level: "debug" | "info" | "warn" | "error";
  };
}

/** モードオーバーライド (REQ-MODE-005) */
export interface ModeOverride {
  additionalKeywords?: string[];
  weight?: number;
}

/** 監査ログ設定 (REQ-SEC-002) */
export interface AuditLogConfig {
  enabled: boolean;
  level: "debug" | "info" | "warn" | "error";
  destination: "stderr" | "file";
  filePath?: string;
}

/** ポリシー設定 (REQ-SEC-003) */
export interface PolicyConfig {
  enabled: boolean;
  rules: PolicyRule[];
}

/** ポリシールール */
export interface PolicyRule {
  mode: string;
  deny: string[];
  action: "block" | "warn";
  message: string;
}
```

### 3.4 型定義 (`src/types/asset.ts`)

```typescript
/** アセットマニフェスト (REQ-ASSET-001) */
export interface AssetManifest {
  version: string;
  deployedAt: string;
  files: Record<string, AssetFileEntry>;
}

/** アセットファイルエントリ */
export interface AssetFileEntry {
  hash: string;
  version: string;
}

/** デプロイ結果 */
export interface DeployResult {
  action: "created" | "updated" | "merged" | "skipped" | "conflict";
  files: DeployedFile[];
  previousVersion?: string;
  newVersion: string;
}

/** デプロイ済みファイル */
export interface DeployedFile {
  name: string;
  action: "copied" | "merged" | "conflict" | "skipped";
  conflictPath?: string;
}
```

### 3.5 型定義 (`src/types/hooks.ts`)

```typescript
/** フックイベントマップ (REQ-API-001, REQ-API-002) */
export interface AegisHookEventMap {
  "plugin.init": { config: AegisConfig; directory: string };
  "plugin.teardown": { reason: string };
  "session.start": { sessionId: string; directory: string };
  "session.end": { sessionId: string; stats: SessionStats };
  "tool.execute.before": { input: ToolInput; output: ToolOutput };
  "tool.execute.after": { input: ToolInput; result: unknown; duration: number };
  "installation.updated": Record<string, never>;
}

/** セッション統計 */
export interface SessionStats {
  toolCalls: number;
  skillInjections: number;
  policyBlocks: number;
  duration: number;
}

/** ツール入力 */
export interface ToolInput {
  tool: string | { name: string; arguments?: Record<string, unknown> };
}

/** ツール出力 (可変) */
export interface ToolOutput {
  args?: Record<string, unknown>;
}

/** イベントバスメッセージ (REQ-API-003) */
export interface EventBusMessage {
  source: string;
  event: string;
  data: unknown;
  timestamp: number;
}
```

### 3.6 型定義 (`src/types/audit.ts`)

```typescript
/** 監査ログエントリ (REQ-SEC-002) */
export interface AuditLogEntry {
  timestamp: string;
  event: AuditEventType;
  data: AuditEventData;
}

export type AuditEventType =
  | "skill_injection"
  | "mode_detection"
  | "bypass_attempt"
  | "policy_violation"
  | "config_tamper";

export interface AuditEventData {
  mode?: string;
  skills?: string[];
  toolTarget?: string;
  bypassAttempted?: boolean;
  signatureValid?: boolean;
  policyRule?: string;
  message?: string;
}
```

---

## 4. Public API シグネチャ (Public API Signatures)

### 4.1 Plugin Entry (`src/index.ts`)

```typescript
import type { Plugin } from "@opencode-ai/plugin";

/**
 * Aegis v2 プラグインエントリポイント。
 * OpenCode Plugin Loader から呼び出される。
 */
declare const Aegis: Plugin;
export default Aegis;
```

### 4.2 Mode Engine (`src/logic/mode-engine.ts`)

```typescript
import type {
  AegisMode, ModeRule, ModeResolutionResult, CustomModeDefinition
} from "../types/mode";

export class ModeEngine {
  /** ルールリスト + ユーザー定義モードで初期化 */
  constructor(
    builtinRules?: ModeRule[],
    customModes?: Record<string, CustomModeDefinition>
  );

  /** ルールを追加登録 (REQ-MODE-005) */
  addRule(rule: ModeRule): void;

  /** プロンプトからモードを判定 (REQ-MODE-001, REQ-MODE-004) */
  determine(prompt: string): ModeResolutionResult;

  /** 登録済みモード名一覧を取得 */
  getRegisteredModes(): AegisMode[];
}
```

### 4.3 Skill Resolver (`src/logic/skill-resolver.ts`)

```typescript
import type { AegisMode } from "../types/mode";
import type {
  SkillEntry, SkillResolutionResult, ResolvedSkill
} from "../types/skill";

export class SkillResolver {
  constructor(config: {
    map: Record<string, SkillEntry[]>;
    maxSkills: number;
    cache: { ttl: number; enabled: boolean };
  });

  /** モードに対応するスキルを解決 (REQ-SKILL-001, REQ-SKILL-002) */
  resolve(cwd: string, mode: AegisMode): Promise<SkillResolutionResult>;

  /** キャッシュクリア (REQ-SKILL-005) */
  clearCache(): void;

  /** キャッシュ統計を取得 */
  getCacheStats(): { size: number; hits: number; misses: number };
}
```

### 4.4 Config Manager (`src/logic/config.ts`)

```typescript
import type { AegisConfig } from "../types/config";

export class ConfigManager {
  /** opencode.json から設定を読み込み、バリデーション + デフォルトマージ */
  static load(projectConfig: Record<string, unknown>): AegisConfig;

  /** 設定値を検証 (REQ-CFG-002) */
  static validate(config: unknown): asserts config is AegisConfig;

  /** デフォルト設定を取得 */
  static defaults(): AegisConfig;
}
```

### 4.5 Security Layer (`src/logic/security.ts`)

```typescript
export class SecurityLayer {
  constructor(config: AegisConfig["security"]);

  /** 注入署名を生成 (REQ-SEC-001) */
  sign(prompt: string): string;

  /** 署名を検証 (REQ-SEC-001) */
  verify(prompt: string): boolean;

  /** 設定チェックサムを計算・比較 (REQ-SEC-004) */
  checkConfigIntegrity(currentConfig: unknown): boolean;

  /** 設定チェックサムを更新 */
  updateChecksum(config: unknown): void;
}
```

### 4.6 Policy Engine (`src/logic/policy-engine.ts`)

```typescript
import type { PolicyRule } from "../types/config";

export class PolicyEngine {
  constructor(rules: PolicyRule[]);

  /** ツール使用がポリシーに違反するか検査 (REQ-SEC-003) */
  evaluate(mode: string, toolName: string): PolicyEvaluation;
}

export interface PolicyEvaluation {
  allowed: boolean;
  rule?: PolicyRule;
  message?: string;
}
```

### 4.7 Asset Manager (`src/logic/asset-manager.ts`)

```typescript
import type { AssetManifest, DeployResult } from "../types/asset";

export class AssetManager {
  constructor(config: AegisConfig["assets"]);

  /** アセットをデプロイ (REQ-ASSET-001, REQ-ASSET-002, REQ-ASSET-003) */
  deploy(targetRoot: string, force?: boolean): Promise<DeployResult>;

  /** 指定バージョンにロールバック (REQ-ASSET-001) */
  rollback(targetRoot: string, version: string): Promise<DeployResult>;

  /** デプロイ済みマニフェストを取得 */
  getManifest(targetRoot: string): Promise<AssetManifest | null>;

  /** バージョン履歴を取得 */
  getHistory(targetRoot: string): Promise<string[]>;
}
```

### 4.8 Audit Logger (`src/audit/logger.ts`)

```typescript
import type {
  AuditLogEntry, AuditEventType, AuditEventData
} from "../types/audit";

export class AuditLogger {
  constructor(config: AegisConfig["security"]["auditLog"]);

  /** 監査イベントを記録 (REQ-SEC-002) */
  log(event: AuditEventType, data: AuditEventData): void;

  /** ログバッファをフラッシュ */
  flush(): void;
}
```

### 4.9 Hook Dispatcher (`src/api/hooks.ts`)

```typescript
import type { AegisHookEventMap } from "../types/hooks";

export class HookDispatcher {
  /** フックハンドラを登録 */
  on<K extends keyof AegisHookEventMap>(
    event: K,
    handler: (data: AegisHookEventMap[K]) => void | Promise<void>
  ): void;

  /** フックを発火 */
  emit<K extends keyof AegisHookEventMap>(
    event: K,
    data: AegisHookEventMap[K]
  ): Promise<void>;
}
```

### 4.10 Event Bus (`src/api/event-bus.ts`)

```typescript
import type { EventBusMessage } from "../types/hooks";

export class EventBus {
  /** メッセージを送信 (REQ-API-003) */
  emit(event: string, data: unknown): void;

  /** メッセージを購読 */
  on(event: string, handler: (msg: EventBusMessage) => void): void;

  /** 購読解除 */
  off(event: string, handler: (msg: EventBusMessage) => void): void;
}
```

### 4.11 Tool Registry (`src/api/tool-registry.ts`)

```typescript
/** カスタムツール定義 (REQ-API-004) */
export interface ToolDefinition {
  name: string;
  description: string;
  handler: (args: Record<string, unknown>) => Promise<unknown>;
}

export class ToolRegistry {
  /** ツールを登録 */
  register(tool: ToolDefinition): void;

  /** 登録済みツール一覧を取得 */
  getTools(): ToolDefinition[];
}
```

---

## 5. REQ → Design マッピング (Traceability Matrix)

| REQ ID | Design Section | 実装ファイル | テストファイル |
|--------|---------------|-------------|-------------|
| REQ-MODE-001 | 2.1.1, 2.1.2 | `src/logic/mode-engine.ts` | `test/unit/mode-engine.test.ts` |
| REQ-MODE-002 | 2.1.4 | `src/logic/mode-engine.ts` | `test/unit/mode-engine.test.ts` |
| REQ-MODE-003 | 2.1.2 (Step 5) | `src/types/mode.ts` | `test/unit/mode-engine.test.ts` |
| REQ-MODE-004 | 2.1.2 (Step 6) | `src/logic/mode-engine.ts` | `test/unit/mode-engine.test.ts` |
| REQ-MODE-005 | 2.1.3, 2.1.4 | `src/logic/mode-engine.ts` | `test/unit/mode-engine.test.ts` |
| REQ-SKILL-001 | 2.2.2 (Step 1) | `src/logic/skill-resolver.ts` | `test/unit/skill-resolver.test.ts` |
| REQ-SKILL-002 | 2.2.2 (Step 5) | `src/logic/skill-resolver.ts` | `test/unit/skill-resolver.test.ts` |
| REQ-SKILL-003 | 2.2.2 (Step 3) | `src/logic/skill-resolver.ts` | `test/unit/skill-resolver.test.ts` |
| REQ-SKILL-004 | 2.2.2 (Step 6) | `src/logic/skill-resolver.ts` | `test/unit/skill-resolver.test.ts` |
| REQ-SKILL-005 | 2.2.2 (Step 4) | `src/logic/skill-resolver.ts` | `test/unit/skill-resolver.test.ts` |
| REQ-ASSET-001 | 2.3.2, 2.3.4, 2.3.5 | `src/logic/asset-manager.ts` | `test/unit/asset-manager.test.ts` |
| REQ-ASSET-002 | 2.3.4 | `src/logic/asset-manager.ts` | `test/unit/asset-manager.test.ts` |
| REQ-ASSET-003 | 2.3.4 | `src/logic/asset-manager.ts` | `test/integration/asset-deploy.test.ts` |
| REQ-API-001 | 2.4.1, 2.4.2 | `src/api/hooks.ts` | `test/integration/plugin-lifecycle.test.ts` |
| REQ-API-002 | 2.4.1, 2.4.2 | `src/api/lifecycle.ts` | `test/integration/plugin-lifecycle.test.ts` |
| REQ-API-003 | 2.4.3 | `src/api/event-bus.ts` | `test/integration/plugin-lifecycle.test.ts` |
| REQ-API-004 | 2.4.4 | `src/api/tool-registry.ts` | `test/integration/plugin-lifecycle.test.ts` |
| REQ-CFG-001 | 2.5.1 | `src/logic/config.ts` | `test/unit/config.test.ts` |
| REQ-CFG-002 | 2.5.2 | `src/logic/config.ts` | `test/unit/config.test.ts` |
| REQ-CFG-003 | 2.5.3 | `src/logic/config.ts` | `test/unit/config.test.ts` |
| REQ-SEC-001 | 2.6.1 | `src/logic/security.ts` | `test/unit/security.test.ts` |
| REQ-SEC-002 | 2.6.2 | `src/audit/logger.ts` | `test/unit/audit-logger.test.ts` |
| REQ-SEC-003 | 2.6.3 | `src/logic/policy-engine.ts` | `test/unit/policy-engine.test.ts` |
| REQ-SEC-004 | 2.6.4 | `src/logic/security.ts` | `test/unit/security.test.ts` |
| REQ-TEST-001 | 2.7.1, 2.7.2 | — | `test/unit/**` |
| REQ-TEST-002 | 2.7.1 | — | `test/integration/**` |
| REQ-TEST-003 | 2.7.3 | `.github/workflows/ci.yml` | — |

---

## 6. Plan TODO → Design 相互参照

| Plan TODO # | Plan 行 | 内容 | Design Section | 状態 |
|------------|---------|------|---------------|------|
| #1 | L41–48 | タスクリスト初期化 | — (本設計書の作成そのもの) | 本書にて解決 |
| #2 | L50–57 | Mode Detection Engine | 2.1, 3.1, 4.2 | 設計完了 |
| #3 | L59–66 | Skill Resolution | 2.2, 3.2, 4.3 | 設計完了 |
| #4 | L68–75 | Configuration System | 2.5, 3.3, 4.4 | 設計完了 |
| #5 | L77–84 | Asset System | 2.3, 3.4, 4.7 | 設計完了 |
| #6 | L86–93 | Plugin API | 2.4, 3.5, 4.8–4.11 | 設計完了 |
| #7 | L95–102 | Security Features | 2.6, 3.6, 4.5–4.6 | 設計完了 |
| #8 | L104–111 | Testing & CI | 2.7 | 設計完了 |
