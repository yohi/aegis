# OpenCode Plugin: Aegis - Final Complete Package (Rev.16)

## 1. 実装コード (Implementation)

### `scripts/verify-pack.cjs`

**役割:** 配布物の整合性検証。

```javascript
// scripts/verify-pack.cjs
// [AEGIS FINAL] Gold Release (Rev.16)
// Usage: node scripts/verify-pack.cjs (Standard verification for prepublish)

const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const MAX_BUFFER = 10 * 1024 * 1024; // 10MB
const DUMP_LIMIT = 2000; // 2000 chars dump limit
const PANIC_LOG_FILE = 'aegis-panic.log';

const projectRoot = path.resolve(__dirname, '..');

let stdoutBroken = false;
let stderrBroken = false;

function swallow() {}

function writePanicLog(message) {
  try {
    const timestamp = new Date().toISOString();
    // Rev.16: 環境情報をログに付与
    const envInfo = `[Node:${process.version}/OS:${process.platform}]`;
    const logEntry = `[${timestamp}] ${envInfo} PANIC: ${message}\n`;
    fs.appendFileSync(path.resolve(projectRoot, PANIC_LOG_FILE), logEntry);
  } catch (_) {}
}

function truncateOutput(output) {
  if (!output || output.length <= DUMP_LIMIT * 2) return output;
  const head = output.slice(0, DUMP_LIMIT);
  const tail = output.slice(-DUMP_LIMIT);
  return `${head}\n... [${output.length - DUMP_LIMIT * 2} chars truncated] ...\n${tail}`;
}

function sealStderr() {
  if (stderrBroken) return false;
  stderrBroken = true;
  writePanicLog('stderr stream broken. Switching to silent mode.');
  try { process.stderr.on('error', swallow); } catch (_) {}
  return true;
}

function sealStdout() {
  if (stdoutBroken) return false;
  stdoutBroken = true;
  try { process.stdout.on('error', swallow); } catch (_) {}
  return true;
}

function safeStderr(...args) {
  if (stderrBroken) return;
  try { console.error(...args); } catch (_) { sealStderr(); }
}

function handleStdoutError(err) {
  if (!sealStdout()) return;
  const code = err && err.code;
  if (code === 'EPIPE') {
    safeStderr('[Aegis] WARN: stdout pipe closed (EPIPE); JSON events suppressed.');
  } else {
    const msg = err && err.message ? err.message : String(err);
    safeStderr(`[Aegis] stdout error: ${msg}`);
    writePanicLog(`stdout error detected: ${msg}`);
  }
}

try { process.stderr.once('error', sealStderr); } catch (_) { sealStderr(); }
try { process.stdout.once('error', handleStdoutError); } catch (_) { sealStdout(); }

// --- メイン検証処理 ---

safeStderr('[Aegis] Verifying package payload (Assets & Dist)...');

// 1. npm pack --dry-run
const cmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';
// NOTE: Parsing stdout is fragile across npm versions. Consider --json in future.
const r = spawnSync(cmd, ['pack', '--dry-run'], { 
  cwd: projectRoot,
  encoding: 'utf8', 
  maxBuffer: MAX_BUFFER
});

if (r.error || r.status !== 0) {
  safeStderr('FATAL: npm pack failed.');
  const errInfo = r.error ? `\nError: ${r.error.message}\nStack: ${r.error.stack}` : '';
  writePanicLog(`npm pack failed.${errInfo}\nStdout: ${truncateOutput(r.stdout || '')}\nStderr: ${truncateOutput(r.stderr || '')}`);
  process.exit(1);
}

const output = (r.stdout || '') + (r.stderr || '');

// 2. 必須ファイルの存在確認ロジック (AND条件)
const checks = [
  { pattern: /assets[\\/]+commands[\\/]+\.aegis-sentinel/, label: 'Sentinel File' },
  { pattern: /assets[\\/]+commands[\\/]+aegis-refine-plan\.md/, label: 'Command: Refine Plan' },
  { pattern: /assets[\\/]+commands[\\/]+aegis-doctor\.md/, label: 'Command: Doctor' },
  { pattern: /dist[\\/]+index\.js/, label: 'Build Artifact (dist/index.js)' },
  { pattern: /dist[\\/]+index\.d\.ts/, label: 'Type Definitions' }
];

const failures = checks.filter(c => !c.pattern.test(output));

if (failures.length > 0) {
  safeStderr('FATAL: Package missing required files:');
  failures.forEach(f => safeStderr(` - ${f.label}`));
  safeStderr('Check .npmignore, "files" in package.json, and run "npm run build" before publishing.');
  
  writePanicLog(`Verification failed. Missing files: ${failures.map(f => f.label).join(', ')}`);
  writePanicLog(`npm pack output dump:\n${truncateOutput(output)}`);
  
  process.exit(1);
}

safeStderr('OK: Pack content verified.');

```

### `scripts/check-assets.cjs`

```javascript
// scripts/check-assets.cjs
const fs = require('fs');
const path = require('path');

const dir = path.resolve(__dirname, '..', 'assets', 'commands');
const sentinel = path.join(dir, '.aegis-sentinel');
const CORE_COMMANDS = ['aegis-refine-plan.md', 'aegis-doctor.md'];

console.log('[Aegis] Verifying local assets...');

try {
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) {
    throw new Error(`Assets directory missing or not a directory: ${dir}`);
  }

  if (!fs.existsSync(sentinel) || !fs.statSync(sentinel).isFile()) {
    throw new Error(`Sentinel missing or not a file: ${sentinel}`);
  }

  const missingCommands = CORE_COMMANDS.filter(f => {
    try { return !fs.statSync(path.join(dir, f)).isFile(); } catch (e) { return true; }
  });

  if (missingCommands.length > 0) {
    throw new Error(`Missing core commands: ${missingCommands.join(', ')} in ${dir}`);
  }

  console.log('OK: Local assets verified');
} catch (e) {
  console.error(`FATAL: ${e.message}`);
  process.exit(1);
}

```

### `src/logic/mode-selector.ts`

```typescript
export type AegisMode = "PLAN" | "DEBUG" | "CODE" | "GENERAL";

export function determineMode(prompt: string): AegisMode {
  const p = prompt.toLowerCase();
  
  const hasWord = (word: string) => new RegExp(`\\b${word}\\b`, 'i').test(p);
  const hasKeyword = (keywords: string[]) => keywords.some(k => p.includes(k));

  if (hasWord("plan") || hasWord("strategy") || hasWord("architecture") || hasKeyword(["計画", "設計", "方針"])) {
    return "PLAN";
  }
  if (hasWord("debug") || hasWord("fix") || hasWord("error") || hasWord("fail") || hasKeyword(["デバッグ", "修正", "エラー", "失敗"])) {
    return "DEBUG";
  }
  if (hasWord("implement") || hasWord("refactor") || hasWord("code") || hasKeyword(["実装", "コード", "リファクタ"])) {
    return "CODE";
  }
  return "GENERAL";
}

```

### `src/logic/skill-resolver.ts`

```typescript
import * as fs from "fs/promises";
import * as path from "path";
import * as os from "os";
import type { AegisMode } from "./mode-selector";

export interface Skill {
  name: string;
}

const SKILL_MAP: Record<AegisMode, string[]> = {
  PLAN: ["writing-plans", "brainstorming"],
  DEBUG: ["systematic-debugging", "verification-before-completion"],
  CODE: ["test-driven-development", "requesting-code-review"],
  GENERAL: []
};

async function getSkillSearchPaths(cwd: string): Promise<string[]> {
  const candidates = [
    path.join(cwd, ".opencode"),
    path.join(cwd, ".claude"),
    path.join(os.homedir(), ".config", "opencode"),
    path.join(os.homedir(), ".claude"),
  ];
  
  const paths: string[] = [];
  for (const root of candidates) {
    paths.push(path.join(root, "skills"));
    paths.push(path.join(root, "skill"));
  }
  return paths;
}

async function findSkillName(searchPaths: string[], baseName: string): Promise<string | null> {
  const candidates = [
    `superpowers/${baseName}`, // 優先: 名前空間付き
    baseName                   // 次点: フラット
  ];

  for (const root of searchPaths) {
    for (const subPath of candidates) {
      const skillFile = path.join(root, subPath, "SKILL.md");
      try {
        // 不要な読み込み(Frontmatter解析)を排除し、存在確認のみで高速化。
        // ファイルが存在すれば、そのディレクトリ構造(subPath)をロードIDとして採用する。
        await fs.access(skillFile);
        return subPath;
      } catch {}
    }
  }
  return null;
}

const RESOLVE_CACHE = new Map<string, Skill[]>();

export function clearCache() {
  RESOLVE_CACHE.clear();
}

export async function resolveSkills(cwd: string, mode: AegisMode): Promise<Skill[]> {
  const cacheKey = `${cwd}:${mode}`;
  if (RESOLVE_CACHE.has(cacheKey)) {
    return RESOLVE_CACHE.get(cacheKey)!;
  }

  const candidates = SKILL_MAP[mode] || [];
  const searchPaths = await getSkillSearchPaths(cwd);

  const results = await Promise.all(candidates.map(async (baseName) => {
    const foundName = await findSkillName(searchPaths, baseName);
    return foundName ? { name: foundName } : null;
  }));

  const validSkills = results.filter((s): s is Skill => s !== null);
  RESOLVE_CACHE.set(cacheKey, validSkills);
  
  return validSkills;
}

```

### `src/logic/safety.ts`

```typescript
import type { AegisMode } from "./mode-selector";

export async function enforceWorktreeSafety(cwd: string, mode: AegisMode, $: any): Promise<void> {
  if (mode === "DEBUG" || mode === "CODE") {
    try {
      const status = await $`git -C ${cwd} status --porcelain`.text();
      if (status.trim().length > 0) {
        console.warn("[Aegis] WARN: Working directory is not clean. Proceed with caution.");
      }
    } catch (e) {
      // git管理外などの場合は無視
    }
  }
}

```

### `src/logic/installer.ts`

```typescript
import * as fs from "fs/promises";
import * as path from "path";
import { fileURLToPath } from "url";

async function findAssetsDir(): Promise<string> {
  const currentDir = path.dirname(fileURLToPath(import.meta.url));
  let searchDir = currentDir;
  for (let i = 0; i < 5; i++) {
    const candidate = path.join(searchDir, "assets", "commands");
    try {
      await fs.access(candidate);
      return candidate;
    } catch {
      const parent = path.dirname(searchDir);
      if (parent === searchDir) break;
      searchDir = parent;
    }
  }
  throw new Error("Assets directory (assets/commands) not found in package.");
}

async function isDeployed(targetCmdDir: string): Promise<boolean> {
  try {
    await fs.access(path.join(targetCmdDir, ".aegis-sentinel"));
    await fs.access(path.join(targetCmdDir, "aegis-refine-plan.md"));
    await fs.access(path.join(targetCmdDir, "aegis-doctor.md"));
    return true;
  } catch {
    return false;
  }
}

export async function deployCommands(targetRoot: string, force: boolean = false): Promise<void> {
  try {
    const targetCmdDir = path.join(targetRoot, ".opencode", "commands");
    
    // force=false の場合は既存チェックを行い、存在すればスキップ（上書きしない）
    if (!force && await isDeployed(targetCmdDir)) {
      return; 
    }

    const assetsDir = await findAssetsDir();
    await fs.mkdir(targetCmdDir, { recursive: true });

    const files = await fs.readdir(assetsDir);
    for (const file of files) {
      if (file.endsWith(".md") || file === ".aegis-sentinel") {
        // force=true の場合は常に上書きコピー（ただし完全同期・削除は行わない）
        await fs.copyFile(path.join(assetsDir, file), path.join(targetCmdDir, file));
      }
    }

    if (!force) {
      console.info("[Aegis] Installed helper commands to .opencode/commands.");
      console.info("[Aegis] NOTE: Please add '.opencode/commands/' to your .gitignore to avoid repository pollution.");
    }

  } catch (error) {
    console.warn(`[Aegis] Failed to deploy commands: ${(error as any).message}`);
  }
}

```

### `src/index.ts`

```typescript
import type { Plugin } from "@opencode-ai/plugin";
import { deployCommands } from "./logic/installer";
import { enforceWorktreeSafety } from "./logic/safety";
import { resolveSkills, clearCache } from "./logic/skill-resolver";
import { determineMode } from "./logic/mode-selector";

const TARGET_TOOLS = ["sisyphus_task", "delegate_task"]; 
const INJECTION_MARKER = "__AEGIS_INJECTED_v1__";

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); 
}

const MARKER_RE = new RegExp(`(?:^|\\r?\\n)\\s*${escapeRegExp(INJECTION_MARKER)}\\s*(?:\\r?\\n|$)`);

const Aegis: Plugin = async (ctx) => {
  const { directory, worktree, $ } = ctx;
  const rootDir = worktree || directory;
  
  const configTargets = (Array.isArray(ctx.project?.targetTools) && ctx.project.targetTools.every(t => typeof t === "string"))
    ? ctx.project.targetTools as string[] 
    : TARGET_TOOLS;

  await deployCommands(rootDir, false).catch(() => {});

  return {
    "installation.updated": async () => {
      // Rev.14: キャッシュをクリアして再スキャンを強制
      clearCache();
      await deployCommands(rootDir, true);
    },

    "tool.execute.before": async (input: any, output: any) => {
      const toolName = typeof input.tool === "string" ? input.tool : input.tool?.name;
      
      if (!toolName || !configTargets.includes(toolName)) return;

      const inputArgs = typeof input.tool === "string" 
        ? undefined 
        : (input.tool?.arguments as any);
      const args = output.args ?? inputArgs ?? {};
      
      if (typeof args.prompt !== "string" || args.prompt.length === 0) return;

      const prompt = args.prompt.startsWith("\uFEFF") ? args.prompt.slice(1) : args.prompt;
      if (prompt.trim().length === 0) return;

      if (prompt.startsWith(INJECTION_MARKER)) return;
      if (MARKER_RE.test(prompt)) return;

      const mode = determineMode(prompt);
      
      await enforceWorktreeSafety(rootDir, mode, $).catch(e => console.warn(e.message));

      const skills = await resolveSkills(rootDir, mode);
      if (skills.length === 0) return;

      const skillList = skills.map(s => `"${s.name}"`).join("\n- ");

      const injection = INJECTION_MARKER + "\n" +
`=== AEGIS PROTOCOL: ${mode} ===
REQUIRED SKILLS:
- ${skillList}

INSTRUCTION: 
Ensure these skills are loaded for the delegate task.
==================================`;
      
      args.prompt = `${injection.trim()}\n\n${prompt.trim()}`;
      
      const skillNames = skills.map(s => s.name);
      
      let finalSkills = Array.isArray(args.load_skills) ? args.load_skills : [];
      
      if (Array.isArray(args.skills)) {
        finalSkills = [...finalSkills, ...args.skills];
        delete args.skills;
      }
      
      const merged = [...new Set([...finalSkills, ...skillNames])];
      args.load_skills = merged.filter((s): s is string => typeof s === "string");
      
      output.args = args;
    },
  };
};

export default Aegis;

```

### `package.json`

```json
{
  "name": "opencode-plugin-aegis",
  "version": "1.0.16",
  "type": "module",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "files": [
    "dist",
    "assets"
  ],
  "scripts": {
    "build": "tsup src/index.ts --format esm --clean --dts",
    "prepublishOnly": "npm run build && npm run check-assets && npm run verify-pack",
    "check-assets": "node scripts/check-assets.cjs",
    "verify-pack": "node scripts/verify-pack.cjs"
  },
  "dependencies": {},
  "devDependencies": {
    "tsup": "^8.0.0",
    "typescript": "^5.0.0",
    "@types/node": "^20.0.0",
    "@opencode-ai/plugin": ">=1.0.0"
  },
  "peerDependencies": {
    "oh-my-opencode": "*",
    "superpowers": "*"
  },
  "peerDependenciesMeta": {
    "oh-my-opencode": { "optional": true },
    "superpowers": { "optional": true }
  }
}

```

## 2. アセット (Assets)

以下のファイルを `assets/commands/` 配下に配置します。

### `assets/commands/.aegis-sentinel`

```text
AEGIS-ACTIVATED

```

### `assets/commands/aegis-refine-plan.md`

```markdown
---
description: Refines a project plan using strict validation rules.
---

# Aegis Plan Refinement

You are an expert architect tasked with refining a project plan.
Validate the plan against the following criteria:
1. Feasibility (Technical & Resource)
2. Clarity of deliverables (SMART criteria)
3. Risk assessment (Mitigation strategies)

## Output Format

Please output the refined plan in the following Markdown format:

```markdown
# Refined Project Plan

## 1. Executive Summary
(Brief overview of changes and validation results)

## 2. Refined Steps
(Detailed steps with clear deliverables)

## 3. Risk Analysis
- [High/Medium/Low] Risk: Mitigation strategy
```
```

### `assets/commands/aegis-doctor.md`

```markdown
---
description: Diagnoses the current environment and project state.
---

# Aegis Doctor

Analyze the current workspace for:
- Uncommitted changes (git status)
- Missing dependencies (package.json vs node_modules)
- Potential configuration conflicts (.env, config files)
- Directory structure anomalies

## Output Format

Report findings in the following JSON format for machine readability:

```json
{
  "status": "healthy|warning|critical",
  "issues": [
    {
      "severity": "info|warn|error",
      "category": "git|deps|config",
      "message": "Description of the issue",
      "suggestion": "How to fix it"
    }
  ],
  "env": {
    "node": "version",
    "platform": "os"
  }
}
```



---

## 3. ドキュメント (DESIGN.md)

`DESIGN.md` の「3. セキュリティモデルと既知の制約」セクションです。
**変更点 (P2):** Permission 設定に関する注釈を追加し、ワイルドカード非対応環境への配慮を記述。

````markdown
# OpenCode Plugin: Aegis - Design & Specification

**Version:** 1.0.16 (Gold Release - Rev.16)
**Date:** 2024-05-24
**Status:** Released

## 1. 概要 (Overview)

**Aegis** は、OpenCode プラグインエコシステムにおいて、npm パッケージの整合性を検証し、その実行コンテキストを安全かつ強力に拡張するための統合セキュリティ・プラットフォームです。

### 1.1. Installation & Setup

`opencode.json` に以下を追加して有効化します。
また、Peer Dependencies として `oh-my-opencode` および `superpowers` の導入を推奨します。

```json
{
  "plugins": {
    "aegis": {
      "package": "opencode-plugin-aegis"
    }
  }
}
```

## 2. アーキテクチャと設計哲学

### 2.1. The Trinity: Context, Power, and Safety (三位一体)

Aegis は、以下の2つのプラグインと併用されることで、システムの真価を発揮する「三種の神器」の一つとして設計されています。

* **Oh-My-OpenCode (Context/Defense):** ツール実行環境とタスクランナーを提供。
* **Superpowers (Power/Offense):** 高度なエンジニアリングスキルを提供。
* **Aegis (Safety/Control):** 上記2つを仲介し、コンテキストに応じた適切なスキル注入と、配布物の完全性検証を行う。

### 2.2. Robust & Dynamic Skill Resolution (Rev.16)

Aegis は、ディレクトリ構造に基づいた「相対パス」をロードIDとして使用します。
パフォーマンス確保のため、解決結果はキャッシュされますが、`installation.updated` イベント（プラグイン更新や設定変更）発生時にキャッシュはクリアされ、再スキャンが行われます。これにより、動的な変更への追随と高速な動作を両立しています。

### 2.3. Target Tool Configuration

Aegis はデフォルトで `sisyphus_task` および `delegate_task` を介入対象とします。
この対象は `opencode.json` の `targetTools` プロパティでカスタマイズ可能です。

```json
{
  "targetTools": ["sisyphus_task", "delegate_task", "my_custom_task"]
}
```

## 3. セキュリティモデルと既知の制約 (Security & Limitations)

### 3.1. Security Boundary & Permissions

Aegis のフック介入は補助的なものであり、完全なセキュリティ境界を保証するものではありません。
厳格なツールの利用制限が必要な場合は、OpenCode 標準の **`permission` 設定**（`opencode.json`）を使用してください。

**例 (Superpowers対応設定):**

```json
{
  "permission": {
    "skill": {
      "superpowers/*": "allow",
      "brainstorming": "allow",
      "*": "ask"
    }
  }
}
```

*注: 環境によってはワイルドカード（`*`）が期待通りに機能しない場合があります。その場合は、`"superpowers/brainstorming": "allow"` のように完全一致で指定してください。*

**Injection Bypass:**
プロンプトの先頭に `__AEGIS_INJECTED_v1__` マーカーが含まれる場合、Aegis は二重注入防止のために介入をスキップします。
ユーザーが意図的にこのマーカーを付与することで、Aegis の介入を回避（Opt-out）することが可能です。これはデバッグや高度な制御のための仕様です。

### 3.2. Repository Hygiene & Safety

Aegis は初回起動時に、補助コマンド（`aegis-doctor` 等）を `.opencode/commands/` に配置します。
以下の点に注意してください。

1. **ファイルの上書き:** プラグイン更新時（`installation.updated`）やデプロイ時には、同名ファイルが警告なく上書きされます。このディレクトリ内のファイルを手動で変更しないでください。
2. **Git Ignore:** リポジトリの汚染を防ぐため、`.gitignore` に以下を追加することを強く推奨します。

```text
.opencode/commands/
aegis-panic.log
```

### 3.3. Argument Normalization (One-Way)

Aegis は互換性維持のため、`skills` 引数が存在する場合、それを `load_skills` に統合し、元の `skills` 引数を削除します（片方向正規化）。
````

