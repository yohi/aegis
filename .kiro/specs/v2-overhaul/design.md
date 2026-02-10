# Design: v2-overhaul

**Version:** 2.0.0 (Draft)
**Date:** 2026-02-10
**Status:** Design Phase
**Base:** specs.md (Rev.16 Gold Release) — v1.0.16 アーキテクチャを刷新

---

## 1. システムアーキテクチャ概要

### 1.1 アーキテクチャ図

```
┌─────────────────────────────────────────────────────────┐
│                    opencode.json                        │
│  { "plugins": { "aegis": { ... } } }                   │
│  └── aegis namespace (§2.5 Configuration)               │
└────────────────┬────────────────────────────────────────┘
                 │ ロード
┌────────────────▼────────────────────────────────────────┐
│              src/index.ts (Plugin Entry)                 │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Plugin Lifecycle                                  │   │
│  │  init() → hooks registration → teardown()        │   │
│  │  (§2.4 REQ-API-002)                              │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─── Hook Layer (§2.4) ────────────────────────────┐   │
│  │ tool.execute.before  ──┐                          │   │
│  │ tool.execute.after   ──┤  Hook Dispatcher         │   │
│  │ session.start/end    ──┤  (src/api/hooks.ts)      │   │
│  │ installation.updated ──┘                          │   │
│  └──────────────┬───────────────────────────────────┘   │
│                 │                                        │
│  ┌──────────────▼───────────────────────────────────┐   │
│  │              Core Pipeline                        │   │
│  │                                                   │   │
│  │  ┌─────────────┐   ┌──────────────┐              │   │
│  │  │ Config       │──▶│ Mode Engine  │              │   │
│  │  │ (§2.5)       │   │ (§2.1)       │              │   │
│  │  └─────────────┘   └──────┬───────┘              │   │
│  │                           │                       │   │
│  │                    ┌──────▼───────┐               │   │
│  │                    │ Skill        │               │   │
│  │                    │ Resolver     │               │   │
│  │                    │ (§2.2)       │               │   │
│  │                    └──────┬───────┘               │   │
│  │                           │                       │   │
│  │  ┌─────────────┐  ┌──────▼───────┐               │   │
│  │  │ Policy      │──│ Security     │               │   │
│  │  │ Engine      │  │ (§2.6)       │               │   │
│  │  │ (§2.6)      │  └──────┬───────┘               │   │
│  │  └─────────────┘         │                       │   │
│  │                    ┌─────▼────────┐               │   │
│  │                    │ Audit Logger │               │   │
│  │                    │ (§2.6)       │               │   │
│  │                    └──────────────┘               │   │
│  └───────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─── Side Systems ─────────────────────────────────┐   │
│  │ Asset Manager (§2.3)  │  Custom Tools (§2.4)     │   │
│  │ src/logic/asset-mgr   │  src/api/tools.ts        │   │
│  └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 1.2 モジュール依存関係

| モジュール | パス | 依存先 | 担当 REQ |
|---|---|---|---|
| **Config** | `src/logic/config.ts` | なし（最初にロード） | REQ-CFG-* |
| **Mode Engine** | `src/logic/mode-engine.ts` | Config | REQ-MODE-* |
| **Skill Resolver** | `src/logic/skill-resolver.ts` | Config, Mode Engine | REQ-SKILL-* |
| **Security** | `src/logic/security.ts` | Config | REQ-SEC-001, 004 |
| **Policy Engine** | `src/policy/engine.ts` | Config, Mode Engine | REQ-SEC-003 |
| **Audit Logger** | `src/audit/logger.ts` | なし | REQ-SEC-002 |
| **Asset Manager** | `src/logic/asset-manager.ts` | Config | REQ-ASSET-* |
| **Hook Dispatcher** | `src/api/hooks.ts` | 全コアモジュール | REQ-API-001, 002 |
| **Tool Registry** | `src/api/tools.ts` | Config | REQ-API-003, 004 |
| **Plugin Entry** | `src/index.ts` | 全モジュール | 統合 |

### 1.3 データフロー（tool.execute.before）

```
Prompt 入力
  → Security.verifyNotInjected(prompt)     // §2.6 REQ-SEC-001
  → Config.load()                          // §2.5 REQ-CFG-001〜003
  → ModeEngine.determine(prompt, config)   // §2.1 REQ-MODE-001〜005
  → PolicyEngine.enforce(mode, tool)       // §2.6 REQ-SEC-003
  → SkillResolver.resolve(mode, config)    // §2.2 REQ-SKILL-001〜005
  → AuditLogger.log(event)                 // §2.6 REQ-SEC-002
  → Prompt にインジェクション + args 正規化
```

---

## 2. 詳細設計

### 2.1 Mode Detection Engine

**対応要件**: REQ-MODE-001, REQ-MODE-002, REQ-MODE-003, REQ-MODE-004, REQ-MODE-005
**Plan 参照**: `.sisyphus/plans/v2-overhaul.md` TODO #2 (v2-mode-1)

#### 2.1.1 設計方針

v1 はハードコードされたキーワードマッチング（`mode-selector.ts`）だったが、v2 では **ルールベースエンジン** に移行する。各ルールは独立した `ModeRule` オブジェクトとして定義され、設定から動的にロードできる。

#### 2.1.2 ルール構造

```typescript
// src/types/mode.ts

/** 組み込みモード + ユーザー定義モードをサポート（REQ-MODE-002） */
export type BuiltinMode = "PLAN" | "DEBUG" | "CODE" | "GENERAL";
export type AegisMode = BuiltinMode | string; // ユーザー定義モードは任意文字列

/** ルール定義（REQ-MODE-001, REQ-MODE-005） */
export interface ModeRule {
  /** ルール識別子 */
  readonly id: string;
  /** 対象モード */
  readonly mode: AegisMode;
  /** マッチング用キーワード（正規表現文字列も可） */
  readonly keywords: readonly string[];
  /** 優先度スコア（高い方が優先。REQ-MODE-004） */
  readonly priority: number;
  /** true の場合、正規表現としてキーワードを評価 */
  readonly isRegex?: boolean;
}

/** モード判定結果（複合モード対応。REQ-MODE-003） */
export interface ModeResult {
  /** 最終決定モード */
  readonly primary: AegisMode;
  /** スコア付きの全マッチ結果 */
  readonly matches: readonly ModeMatch[];
}

export interface ModeMatch {
  readonly mode: AegisMode;
  readonly score: number;
  readonly matchedRules: readonly string[]; // rule ID のリスト
}
```

#### 2.1.3 エンジン API

```typescript
// src/logic/mode-engine.ts

import type { ModeRule, ModeResult, AegisMode } from "../types/mode";
import type { AegisConfig } from "../types/config";

/** 組み込みルール定義（v1 互換キーワード） */
export const BUILTIN_RULES: readonly ModeRule[];

/**
 * ルールベースのモード判定エンジン。
 * 組み込みルール + ユーザー定義ルールを統合し、優先度で解決する。
 *
 * @param prompt - 解析対象のプロンプト文字列
 * @param config - Aegis 設定（カスタムモード・ルールを含む）
 * @returns ModeResult - 全マッチ結果と最終決定モード
 *
 * REQ-MODE-001: ルールベースアーキテクチャ
 * REQ-MODE-002: カスタムモード対応
 * REQ-MODE-003: 複合モード（matches に全候補が含まれる）
 * REQ-MODE-004: priority による優先度解決
 * REQ-MODE-005: ユーザー定義ルールは config 経由でロード
 */
export function determineMode(prompt: string, config: AegisConfig): ModeResult;
```

#### 2.1.4 優先度解決アルゴリズム（REQ-MODE-004）

1. 全ルール（builtin + user）を `prompt` に対して評価
2. マッチしたルールをモード別にグルーピング
3. 各モードのスコア = `Σ(rule.priority)` （マッチしたルールの priority 合計）
4. 最高スコアのモードを `primary` として返却
5. 同点の場合はユーザー定義ルールを優先、さらに同点ならルール ID の辞書順

---

### 2.2 Skill Resolution

**対応要件**: REQ-SKILL-001, REQ-SKILL-002, REQ-SKILL-003, REQ-SKILL-004, REQ-SKILL-005
**Plan 参照**: `.sisyphus/plans/v2-overhaul.md` TODO #3 (v2-skill-1)

#### 2.2.1 設計方針

v1 のハードコード `SKILL_MAP` を廃止し、設定ファイル（`opencode.json` の `aegis.skills` セクション）からマッピングをロードする。レジストリベースのリモートスキル参照にも対応する拡張点を持つ。

#### 2.2.2 型定義

```typescript
// src/types/skill.ts

/** スキルソース種別（REQ-SKILL-003） */
export type SkillSource = "local" | "registry";

export interface Skill {
  /** スキルのロードID（パス or レジストリ識別子） */
  readonly name: string;
  /** スキルソース */
  readonly source: SkillSource;
  /** 優先度（高い方が優先。REQ-SKILL-002） */
  readonly priority: number;
}

/** モードごとのスキルマッピング設定（REQ-SKILL-001） */
export interface SkillMapping {
  readonly mode: string;
  readonly skills: readonly SkillEntry[];
}

export interface SkillEntry {
  /** スキル名またはパス */
  readonly name: string;
  /** 優先度（デフォルト: 0） */
  readonly priority?: number;
  /** ソース種別（デフォルト: "local"） */
  readonly source?: SkillSource;
}

/** スキル解決結果のテレメトリ（REQ-SKILL-004） */
export interface SkillResolutionLog {
  readonly timestamp: string;
  readonly mode: string;
  readonly candidates: readonly string[];
  readonly resolved: readonly string[];
  readonly cacheHit: boolean;
  readonly sources: Record<string, SkillSource>;
}
```

#### 2.2.3 リゾルバ API

```typescript
// src/logic/skill-resolver.ts

import type { Skill, SkillResolutionLog } from "../types/skill";
import type { AegisMode } from "../types/mode";
import type { AegisConfig } from "../types/config";

/**
 * スキルの解決。設定からマッピングを読み込み、ファイルシステムで存在確認後に返却。
 *
 * @param cwd - プロジェクトルートパス
 * @param mode - 判定されたモード
 * @param config - Aegis 設定
 * @returns 解決されたスキルのリスト（priority 降順、maxSkills 上限適用済み）
 *
 * REQ-SKILL-001: 外部設定マッピング
 * REQ-SKILL-002: 優先度制御 + maxSkills 上限
 * REQ-SKILL-003: source による分岐（local / registry）
 * REQ-SKILL-004: resolutionLog を emit
 * REQ-SKILL-005: TTL キャッシュ + installation.updated 無効化
 */
export function resolveSkills(
  cwd: string,
  mode: AegisMode,
  config: AegisConfig,
): Promise<Skill[]>;

/** キャッシュクリア（installation.updated 時に呼出。REQ-SKILL-005） */
export function clearCache(): void;

/** 直近の解決ログを取得（REQ-SKILL-004） */
export function getLastResolutionLog(): SkillResolutionLog | null;
```

#### 2.2.4 キャッシュ戦略（REQ-SKILL-005）

- **キー**: `${cwd}:${mode}`
- **TTL**: 設定の `aegis.skills.cacheTtlMs`（デフォルト: 300000ms = 5分）
- **無効化トリガー**: `installation.updated` イベント → `clearCache()` 呼出
- **実装**: `Map<string, { skills: Skill[]; expiresAt: number }>` + `Date.now()` 比較

---

### 2.3 Asset System

**対応要件**: REQ-ASSET-001, REQ-ASSET-002, REQ-ASSET-003
**Plan 参照**: `.sisyphus/plans/v2-overhaul.md` TODO #5 (v2-asset-1)

#### 2.3.1 設計方針

v1 は単純なファイルコピー（`installer.ts`）でバージョン管理もマージ戦略もなかった。v2 ではバージョンマニフェストとハッシュベースの差分検知を導入する。

#### 2.3.2 バージョンマニフェスト

```typescript
// src/types/asset.ts

/** アセットマニフェスト（.aegis-manifest.json として保存） */
export interface AssetManifest {
  /** Aegis バージョン（デプロイ元） */
  readonly aegisVersion: string;
  /** デプロイ日時 */
  readonly deployedAt: string;
  /** 各ファイルのハッシュ */
  readonly files: Record<string, AssetFileEntry>;
}

export interface AssetFileEntry {
  /** デプロイ時のファイルハッシュ（SHA-256） */
  readonly deployedHash: string;
  /** バンドル版のファイルハッシュ */
  readonly bundledHash: string;
}

/** マージ戦略（REQ-ASSET-003） */
export type MergeStrategy = "skip" | "overwrite" | "backup";
```

#### 2.3.3 Asset Manager API

```typescript
// src/logic/asset-manager.ts

import type { AssetManifest, MergeStrategy } from "../types/asset";
import type { AegisConfig } from "../types/config";

/**
 * アセットのデプロイ（バージョン追跡付き）。
 *
 * 処理フロー:
 * 1. バンドルアセットのハッシュ計算
 * 2. 既存マニフェストの読み込み
 * 3. ファイルごとのミスマッチ検出（REQ-ASSET-002）
 * 4. ユーザー変更検出: deployedHash != 現在のファイルハッシュ
 * 5. マージ戦略適用（REQ-ASSET-003）:
 *    - skip: ユーザー変更がある場合はスキップ
 *    - overwrite: 強制上書き
 *    - backup: .bak を作成してから上書き
 * 6. マニフェスト更新（REQ-ASSET-001）
 */
export function deployAssets(
  targetRoot: string,
  config: AegisConfig,
): Promise<void>;

/**
 * 指定バージョンへのロールバック（REQ-ASSET-001）。
 * .aegis-manifest.json.bak から復元。
 */
export function rollbackAssets(targetRoot: string): Promise<void>;

/**
 * バンドル版とデプロイ版のバージョンミスマッチを検出（REQ-ASSET-002）。
 */
export function detectMismatch(
  targetRoot: string,
): Promise<{ file: string; expected: string; actual: string }[]>;
```

---

### 2.4 Plugin API

**対応要件**: REQ-API-001, REQ-API-002, REQ-API-003, REQ-API-004
**Plan 参照**: `.sisyphus/plans/v2-overhaul.md` TODO #6 (v2-api-1)

#### 2.4.1 フック拡張（REQ-API-001, REQ-API-002）

v1 は `tool.execute.before` と `installation.updated` のみ。v2 で追加するフック:

| フック名 | タイミング | 用途 |
|---|---|---|
| `tool.execute.after` | ツール実行後 | 結果の監査・ログ記録 (REQ-API-001) |
| `session.start` | セッション開始時 | 環境診断・設定リロード (REQ-API-002) |
| `session.end` | セッション終了時 | テレメトリ送信・クリーンアップ (REQ-API-002) |
| `plugin.init` | プラグイン初期化時 | 設定検証・アセットデプロイ (REQ-API-002) |
| `plugin.teardown` | プラグイン終了時 | リソース解放 (REQ-API-002) |

#### 2.4.2 Hook Dispatcher 型定義

```typescript
// src/api/hooks.ts

import type { AegisConfig } from "../types/config";

/** フックイベント定義 */
export interface HookEvents {
  "tool.execute.before": (input: ToolInput, output: ToolOutput) => Promise<void>;
  "tool.execute.after": (input: ToolInput, result: ToolResult) => Promise<void>;
  "session.start": (ctx: SessionContext) => Promise<void>;
  "session.end": (ctx: SessionContext) => Promise<void>;
  "plugin.init": (config: AegisConfig) => Promise<void>;
  "plugin.teardown": () => Promise<void>;
  "installation.updated": () => Promise<void>;
}

export interface ToolInput {
  readonly tool: string | { name: string; arguments?: Record<string, unknown> };
}

export interface ToolOutput {
  args: Record<string, unknown>;
}

export interface ToolResult {
  readonly success: boolean;
  readonly output?: unknown;
}

export interface SessionContext {
  readonly sessionId: string;
  readonly startedAt: string;
}
```

#### 2.4.3 プラグイン間通信（REQ-API-003）

```typescript
// src/api/event-bus.ts

/** プラグイン間イベントバス */
export interface EventBus {
  /** イベント発火 */
  emit(event: string, payload: unknown): void;
  /** イベント購読 */
  on(event: string, handler: (payload: unknown) => void): void;
  /** 購読解除 */
  off(event: string, handler: (payload: unknown) => void): void;
}

/**
 * SharedContext: プラグイン間で共有されるコンテキスト。
 * oh-my-opencode や superpowers との連携に使用。
 */
export interface SharedPluginContext {
  readonly eventBus: EventBus;
  readonly sharedState: Map<string, unknown>;
}
```

#### 2.4.4 カスタムツール登録（REQ-API-004）

```typescript
// src/api/tools.ts

/** Aegis 独自ツール定義 */
export interface AegisTool {
  readonly name: string;
  readonly description: string;
  execute(args: Record<string, unknown>): Promise<unknown>;
}

/**
 * Aegis が提供するカスタムツール:
 * - aegis_status: 現在のモード・スキル・設定状態を返却
 * - aegis_diagnose: 環境診断（aegis-doctor 相当の機能をツールとして提供）
 */
export function createBuiltinTools(config: AegisConfig): AegisTool[];

/**
 * OpenCode のツールパレットにツールを登録。
 * Plugin API の tool registration mechanism を使用。
 */
export function registerTools(
  tools: AegisTool[],
  registry: ToolRegistry,
): void;
```

---

### 2.5 Configuration

**対応要件**: REQ-CFG-001, REQ-CFG-002, REQ-CFG-003
**Plan 参照**: `.sisyphus/plans/v2-overhaul.md` TODO #4 (v2-config-1)

#### 2.5.1 設定スキーマ（REQ-CFG-001）

```typescript
// src/types/config.ts

/** Aegis v2 設定スキーマ（opencode.json の "aegis" 名前空間） */
export interface AegisConfig {
  /** 介入対象のツール名リスト */
  readonly targetTools: readonly string[];

  /** モード判定エンジン設定 */
  readonly modes: {
    /** ユーザー定義モード */
    readonly custom: readonly ModeRule[];
    /** 組み込みルールを無効化する場合は true */
    readonly disableBuiltins: boolean;
  };

  /** スキル解決設定 */
  readonly skills: {
    /** モード→スキルのマッピング */
    readonly mappings: readonly SkillMapping[];
    /** 1回のインジェクションで注入するスキルの最大数 */
    readonly maxSkills: number;
    /** キャッシュ TTL（ミリ秒） */
    readonly cacheTtlMs: number;
  };

  /** アセットシステム設定 */
  readonly assets: {
    /** マージ戦略 */
    readonly mergeStrategy: MergeStrategy;
    /** 自動更新を有効にする */
    readonly autoUpdate: boolean;
  };

  /** セキュリティ設定 */
  readonly security: {
    /** 監査ログを有効にする */
    readonly auditLog: boolean;
    /** ポリシーエンジンを有効にする */
    readonly policyEnabled: boolean;
    /** モード別ツール制限ポリシー */
    readonly policies: readonly PolicyRule[];
  };
}
```

#### 2.5.2 デフォルト値定義

```typescript
// src/logic/config.ts

/** デフォルト設定（REQ-CFG-003: 部分指定時のマージ元） */
export const DEFAULT_CONFIG: AegisConfig = {
  targetTools: ["sisyphus_task", "delegate_task"],
  modes: {
    custom: [],
    disableBuiltins: false,
  },
  skills: {
    mappings: [],
    maxSkills: 5,
    cacheTtlMs: 300_000,
  },
  assets: {
    mergeStrategy: "skip",
    autoUpdate: true,
  },
  security: {
    auditLog: false,
    policyEnabled: false,
    policies: [],
  },
};
```

#### 2.5.3 バリデーション（REQ-CFG-002）

```typescript
// src/logic/config.ts

export interface ConfigValidationError {
  readonly path: string;
  readonly message: string;
  readonly value: unknown;
}

/**
 * 設定のロードとバリデーション。
 *
 * 1. opencode.json から ctx.project.aegis を取得
 * 2. DEFAULT_CONFIG とディープマージ（REQ-CFG-003）
 * 3. 型・値の検証（REQ-CFG-002）
 * 4. エラーがあれば ConfigValidationError[] を返却
 *
 * @param rawConfig - opencode.json から取得した生の設定オブジェクト
 * @returns [config, errors] タプル
 */
export function loadConfig(
  rawConfig: unknown,
): [AegisConfig, ConfigValidationError[]];

/**
 * ディープマージ: ユーザー提供の部分設定を defaults にマージ。
 * 配列はユーザー値で完全置換（append ではない）。
 */
export function deepMerge<T extends Record<string, unknown>>(
  defaults: T,
  overrides: Partial<T>,
): T;
```

---

### 2.6 Security

**対応要件**: REQ-SEC-001, REQ-SEC-002, REQ-SEC-003, REQ-SEC-004
**Plan 参照**: `.sisyphus/plans/v2-overhaul.md` TODO #7 (v2-sec-1)

#### 2.6.1 暗号署名によるインジェクション検証（REQ-SEC-001）

v1 の `__AEGIS_INJECTED_v1__` 文字列マーカーを廃止し、HMAC-SHA256 署名に置き換える。

```typescript
// src/logic/security.ts

/**
 * インジェクションマーカーの生成。
 * セッション固有のシークレットから HMAC-SHA256 を計算し、
 * プロンプト先頭に埋め込む。
 *
 * @param prompt - 注入対象のプロンプト
 * @param sessionSecret - セッション開始時に生成されるランダムシークレット
 * @returns 署名付きマーカー文字列
 */
export function createInjectionMarker(
  prompt: string,
  sessionSecret: string,
): string;

/**
 * インジェクション済みかどうかを暗号的に検証。
 * 文字列の単純一致ではなく、HMAC 検証で判定する。
 */
export function verifyInjectionMarker(
  prompt: string,
  sessionSecret: string,
): boolean;

/**
 * セッションシークレットの生成（crypto.randomBytes ベース）。
 * セッション開始時に1回だけ呼ばれる。
 */
export function generateSessionSecret(): string;
```

#### 2.6.2 構造化監査ログ（REQ-SEC-002）

```typescript
// src/audit/logger.ts

/** 監査イベント種別 */
export type AuditEventType =
  | "mode_detected"
  | "skills_injected"
  | "bypass_attempt"
  | "policy_enforced"
  | "config_tamper_detected";

export interface AuditEvent {
  readonly timestamp: string;
  readonly type: AuditEventType;
  readonly mode: string;
  readonly toolTarget: string;
  readonly skillsInjected: readonly string[];
  readonly details: Record<string, unknown>;
}

/**
 * 監査ロガー。構造化 JSON 形式でイベントを記録する。
 * 出力先は stderr（デフォルト）または設定で指定されたファイル。
 */
export interface AuditLogger {
  log(event: AuditEvent): void;
  flush(): Promise<void>;
}

export function createAuditLogger(config: AegisConfig): AuditLogger;
```

#### 2.6.3 ポリシーエンジン（REQ-SEC-003）

```typescript
// src/policy/engine.ts

/** ポリシールール定義 */
export interface PolicyRule {
  /** 対象モード（"*" で全モード） */
  readonly mode: string;
  /** 許可/拒否するツール名パターン */
  readonly tools: readonly string[];
  /** allow or deny */
  readonly action: "allow" | "deny";
}

export interface PolicyViolation {
  readonly rule: PolicyRule;
  readonly tool: string;
  readonly mode: string;
  readonly message: string;
}

/**
 * ポリシーの適用判定。
 * deny ルールが優先（deny > allow）。
 *
 * @returns null なら許可、PolicyViolation なら拒否
 */
export function enforcePolicy(
  mode: string,
  tool: string,
  policies: readonly PolicyRule[],
): PolicyViolation | null;
```

#### 2.6.4 設定ファイル改竄検出（REQ-SEC-004）

```typescript
// src/logic/security.ts

/**
 * 設定のチェックサム計算と検証。
 * 初回ロード時にチェックサムを保存し、以降の参照時に比較する。
 */
export function computeConfigChecksum(config: AegisConfig): string;

export function verifyConfigIntegrity(
  config: AegisConfig,
  expectedChecksum: string,
): boolean;
```

---

### 2.7 Testing

**対応要件**: REQ-TEST-001, REQ-TEST-002, REQ-TEST-003
**Plan 参照**: `.sisyphus/plans/v2-overhaul.md` TODO #8 (v2-test-1)

#### 2.7.1 テスト構造

```
test/
├── unit/
│   ├── mode-engine.test.ts      # REQ-MODE-* (§2.1)
│   ├── skill-resolver.test.ts   # REQ-SKILL-* (§2.2)
│   ├── config.test.ts           # REQ-CFG-* (§2.5)
│   ├── security.test.ts         # REQ-SEC-001, 004 (§2.6)
│   ├── policy-engine.test.ts    # REQ-SEC-003 (§2.6)
│   └── audit-logger.test.ts     # REQ-SEC-002 (§2.6)
├── integration/
│   ├── plugin-lifecycle.test.ts # REQ-API-* (§2.4), REQ-TEST-002
│   └── asset-deploy.test.ts     # REQ-ASSET-* (§2.3)
└── fixtures/
    ├── opencode-valid.json      # テスト用設定ファイル
    ├── opencode-invalid.json    # バリデーションエラー用
    └── assets/                  # テスト用アセット
```

#### 2.7.2 カバレッジ戦略（REQ-TEST-001）

| モジュール | カバレッジ目標 | テスト種別 |
|---|---|---|
| mode-engine | ≥90% | Unit: 全ルールパターン、複合モード、優先度解決 |
| skill-resolver | ≥85% | Unit: 設定マッピング、キャッシュ、TTL |
| config | ≥90% | Unit: マージ、バリデーション、エッジケース |
| security | ≥85% | Unit: HMAC 検証、チェックサム |
| policy-engine | ≥90% | Unit: allow/deny 判定、ワイルドカード |
| audit-logger | ≥80% | Unit: イベント記録、フラッシュ |
| asset-manager | ≥80% | Integration: デプロイ、ロールバック、マージ |
| plugin lifecycle | ≥80% | Integration: 全フックの発火順序 |
| **全体** | **≥80%** | REQ-TEST-001 |

#### 2.7.3 CI/CD パイプライン（REQ-TEST-003）

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
      - run: npx vitest run --coverage
      - run: npm run build
      - run: npm run verify-pack
```

#### 2.7.4 Vitest 設定

```typescript
// vitest.config.ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["test/**/*.test.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 75,
        statements: 80,
      },
    },
  },
});
```

---

## 3. データモデル（統合型定義）

以下は §2 で個別に記述した型を統合した一覧。実装時は各 `src/types/*.ts` に分割配置する。

| 型名 | ファイル | 定義セクション |
|---|---|---|
| `AegisMode`, `BuiltinMode` | `src/types/mode.ts` | §2.1.2 |
| `ModeRule`, `ModeResult`, `ModeMatch` | `src/types/mode.ts` | §2.1.2 |
| `Skill`, `SkillSource`, `SkillMapping`, `SkillEntry` | `src/types/skill.ts` | §2.2.2 |
| `SkillResolutionLog` | `src/types/skill.ts` | §2.2.2 |
| `AssetManifest`, `AssetFileEntry`, `MergeStrategy` | `src/types/asset.ts` | §2.3.2 |
| `AegisConfig` | `src/types/config.ts` | §2.5.1 |
| `ConfigValidationError` | `src/types/config.ts` | §2.5.3 |
| `HookEvents`, `ToolInput`, `ToolOutput`, `ToolResult`, `SessionContext` | `src/api/hooks.ts` | §2.4.2 |
| `EventBus`, `SharedPluginContext` | `src/api/event-bus.ts` | §2.4.3 |
| `AegisTool` | `src/api/tools.ts` | §2.4.4 |
| `AuditEvent`, `AuditEventType`, `AuditLogger` | `src/audit/logger.ts` | §2.6.2 |
| `PolicyRule`, `PolicyViolation` | `src/policy/engine.ts` | §2.6.3 |

---

## 4. 公開 API シグネチャ一覧

### 4.1 Core Logic

| 関数 | モジュール | REQ |
|---|---|---|
| `determineMode(prompt, config)` → `ModeResult` | mode-engine | MODE-001〜005 |
| `resolveSkills(cwd, mode, config)` → `Promise<Skill[]>` | skill-resolver | SKILL-001〜005 |
| `clearCache()` → `void` | skill-resolver | SKILL-005 |
| `getLastResolutionLog()` → `SkillResolutionLog \| null` | skill-resolver | SKILL-004 |
| `loadConfig(rawConfig)` → `[AegisConfig, ConfigValidationError[]]` | config | CFG-001〜003 |
| `deepMerge(defaults, overrides)` → `T` | config | CFG-003 |

### 4.2 Asset

| 関数 | モジュール | REQ |
|---|---|---|
| `deployAssets(targetRoot, config)` → `Promise<void>` | asset-manager | ASSET-001〜003 |
| `rollbackAssets(targetRoot)` → `Promise<void>` | asset-manager | ASSET-001 |
| `detectMismatch(targetRoot)` → `Promise<Mismatch[]>` | asset-manager | ASSET-002 |

### 4.3 Security

| 関数 | モジュール | REQ |
|---|---|---|
| `createInjectionMarker(prompt, secret)` → `string` | security | SEC-001 |
| `verifyInjectionMarker(prompt, secret)` → `boolean` | security | SEC-001 |
| `generateSessionSecret()` → `string` | security | SEC-001 |
| `computeConfigChecksum(config)` → `string` | security | SEC-004 |
| `verifyConfigIntegrity(config, checksum)` → `boolean` | security | SEC-004 |
| `enforcePolicy(mode, tool, policies)` → `PolicyViolation \| null` | policy-engine | SEC-003 |
| `createAuditLogger(config)` → `AuditLogger` | audit-logger | SEC-002 |

### 4.4 Plugin API

| 関数 | モジュール | REQ |
|---|---|---|
| `createBuiltinTools(config)` → `AegisTool[]` | tools | API-004 |
| `registerTools(tools, registry)` → `void` | tools | API-004 |

---

## 5. REQ-* トレーサビリティマトリクス

| REQ ID | 設計セクション | 実装ファイル | テストファイル | tasks.md タスクID |
|---|---|---|---|---|
| REQ-MODE-001 | §2.1 | `src/logic/mode-engine.ts` | `test/unit/mode-engine.test.ts` | v2-mode-1 |
| REQ-MODE-002 | §2.1 | `src/logic/mode-engine.ts`, `src/types/mode.ts` | `test/unit/mode-engine.test.ts` | v2-mode-1 |
| REQ-MODE-003 | §2.1 | `src/logic/mode-engine.ts` | `test/unit/mode-engine.test.ts` | v2-mode-1 |
| REQ-MODE-004 | §2.1 | `src/logic/mode-engine.ts` | `test/unit/mode-engine.test.ts` | v2-mode-1 |
| REQ-MODE-005 | §2.1 | `src/logic/mode-engine.ts` | `test/unit/mode-engine.test.ts` | v2-mode-1 |
| REQ-SKILL-001 | §2.2 | `src/logic/skill-resolver.ts` | `test/unit/skill-resolver.test.ts` | v2-skill-1 |
| REQ-SKILL-002 | §2.2 | `src/logic/skill-resolver.ts` | `test/unit/skill-resolver.test.ts` | v2-skill-1 |
| REQ-SKILL-003 | §2.2 | `src/logic/skill-resolver.ts` | `test/unit/skill-resolver.test.ts` | v2-skill-1 |
| REQ-SKILL-004 | §2.2 | `src/logic/skill-resolver.ts` | `test/unit/skill-resolver.test.ts` | v2-skill-1 |
| REQ-SKILL-005 | §2.2 | `src/logic/skill-resolver.ts` | `test/unit/skill-resolver.test.ts` | v2-skill-1 |
| REQ-ASSET-001 | §2.3 | `src/logic/asset-manager.ts` | `test/integration/asset-deploy.test.ts` | v2-asset-1 |
| REQ-ASSET-002 | §2.3 | `src/logic/asset-manager.ts` | `test/integration/asset-deploy.test.ts` | v2-asset-1 |
| REQ-ASSET-003 | §2.3 | `src/logic/asset-manager.ts` | `test/integration/asset-deploy.test.ts` | v2-asset-1 |
| REQ-API-001 | §2.4 | `src/api/hooks.ts` | `test/integration/plugin-lifecycle.test.ts` | v2-pluginapi-1 |
| REQ-API-002 | §2.4 | `src/api/hooks.ts` | `test/integration/plugin-lifecycle.test.ts` | v2-pluginapi-1 |
| REQ-API-003 | §2.4 | `src/api/event-bus.ts` | `test/integration/plugin-lifecycle.test.ts` | v2-pluginapi-1 |
| REQ-API-004 | §2.4 | `src/api/tools.ts` | `test/integration/plugin-lifecycle.test.ts` | v2-pluginapi-1 |
| REQ-CFG-001 | §2.5 | `src/logic/config.ts`, `src/types/config.ts` | `test/unit/config.test.ts` | v2-config-1 |
| REQ-CFG-002 | §2.5 | `src/logic/config.ts` | `test/unit/config.test.ts` | v2-config-1 |
| REQ-CFG-003 | §2.5 | `src/logic/config.ts` | `test/unit/config.test.ts` | v2-config-1 |
| REQ-SEC-001 | §2.6 | `src/logic/security.ts` | `test/unit/security.test.ts` | v2-security-1 |
| REQ-SEC-002 | §2.6 | `src/audit/logger.ts` | `test/unit/audit-logger.test.ts` | v2-security-1 |
| REQ-SEC-003 | §2.6 | `src/policy/engine.ts` | `test/unit/policy-engine.test.ts` | v2-security-1 |
| REQ-SEC-004 | §2.6 | `src/logic/security.ts` | `test/unit/security.test.ts` | v2-security-1 |
| REQ-TEST-001 | §2.7 | `vitest.config.ts` | 全テストファイル | v2-testing-1 |
| REQ-TEST-002 | §2.7 | — | `test/integration/plugin-lifecycle.test.ts` | v2-testing-1 |
| REQ-TEST-003 | §2.7 | `.github/workflows/ci.yml` | — | v2-testing-1 |
