# Aegis v2.0 マルチエージェントレビューシステム 設計書

- **Document ID**: aegis-v2-multiagent-design
- **Version**: 1.0 (initial)
- **Date**: 2026-04-17
- **Status**: Draft（ユーザーレビュー待ち）
- **Scope**: v2.0 マルチエージェントレビュー基盤の設計（実装計画は別ドキュメント）
- **Relation to v1**: `src/core/` および `src/plugins/` を段階的拡張。破壊的変更なし。

---

## 0. 設計目標と運用フロー

### 0.1 主目的（変更判断の基準線）

1. **レビュー時間の極小化** — 人手レビューと同等以上の品質を分単位で提供する
2. **レビュワーの心理的負担の極小化** — 指摘の根拠を問い返せる対話ループ（ステップ10）を主装置とする
3. **人間を凌ぐ精度** — 独立視点のマルチペルソナ並列レビュー（ステップ8）を主装置とする

上記 3 点は設計上「非機能要件」として扱い、後述の検証戦略（§7.5）で指標化する。

### 0.2 運用フロー（User Journey: 11 ステップ）

```
 1. レビュー対象の分類入力 (DOCUMENT / SOURCE_CODE / MIXED)
 2. レビュー依頼票のアップロード (任意)         ┐
 3. レビュー対象ドキュメント／コードのアップロード │
 4. (DOCUMENT時のみ) コードベースを参考に扱うか    ├─ ingest 層が全て正規化
 5. 関連ドキュメントのアップロード (REFERENCE)     │   (Drive URL / ファイル up 両対応)
 6. NotebookLM のアップロード (ABSOLUTE TRUTH)    ┘
 7. 補足事項 / focus_hints の入力
            │
            ▼
 8. マルチエージェント並列レビュー
    (Sentinel + SecurityGuard + Architect + Domain + Performance)
            │
            ▼
 9. レポート生成 (.review/report.md + Google Docs / Sheets)
            │
            ▼
10. Q&A ループ (依頼者が finding 単位で根拠を追問、shield 適用)
            │
            ▼
11. 人間による最終承認 (LLM は自動承認しない)
```

各ステップに対応する責任コンポーネント（モジュール）は §7.2 のディレクトリ構成で明示する。

---

## 1. アーキテクチャ概観

### 1.1 ハイブリッド 2 経路構成

```
                 ┌── 共有資産 (Single Source of Truth) ───────────────┐
                 │ prompts/*.xml  report/renderer  information_hierarchy │
                 │ enums / types (FindingV2, PriorReviewComment, ...)    │
                 │ ingest 層 (Drive URL / 各種ファイル → 正規化)         │
                 │ MCP tools (NotebookLM / gws / Model Armor /           │
                 │            AST scan / status / artifact / QnA)        │
                 │ LLM Provider 抽象化 (Anthropic / OpenAI / Mock)       │
                 └──┬──────────────────────────────────────┬─────────────┘
                    │                                      │
┌───────────────────┴────────────────┐    ┌────────────────┴──────────────────┐
│ Interactive 経路 (Cursor 完結)      │    │ Automation 経路 (CI / 定期実行)   │
│                                     │    │                                   │
│  Cursor Agent = Sentinel            │    │  LangGraph StateGraph             │
│   ├ Cursor sub-agents × 4 persona   │    │   ├ 4 persona nodes (並列)        │
│   │   Rules (.cursor/rules/*.mdc)    │    │   ├ Conflict Resolver            │
│   │   を persona ごとにロード        │    │   └ Report Publisher             │
│   └ MCP サーバ経由でツール呼出       │    │  LLMProvider 経由で LLM 呼出     │
│  モデル: Cursor 経由 Claude Opus 4.7 │    │   thinking: adaptive              │
│   クレジット: Cursor サブスクリプション │    │   effort: xhigh                  │
│                                     │    │   cache_control: ephemeral        │
│  起動: IDE 内 `/aegis review`       │    │  起動: `uv run aegis review-v2`   │
└─────────────────────────────────────┘    └───────────────────────────────────┘

外部依存:
  NotebookLM (ABSOLUTE TRUTH)   Model Armor (shield)
  Google Drive / Docs / Sheets (gws CLI, correlation_id 必須)
  LLM Provider (Anthropic / OpenAI 等)
```

### 1.2 アーキテクチャ原則

- **Protocol-first / Microkernel**: `src/core/protocols.py` は追記のみ（`ReviewPlugin` / `SecurityShield` は不変）。新プロトコル `ReviewAgent` / `ConflictResolver` / `InformationSource` / `DocumentIngestor` / `LLMProvider` を追加
- **Composition over Inheritance**: 各ノード／エージェントは protocol 実装をコンポーズ。深い継承を避ける
- **Everything auditable**: LangGraph 各ノード境界、Cursor sub-agent 終了時、MCP ツール呼出し時に `.review/artifacts/` へ atomic write
- **SecurityShield は必須経路**: `AgentExecutor` を介さない LLM 呼出しを作らない。Cursor 経路でも MCP 側で shield 適用
- **Provider-neutral**: LLM 固有パラメータ（Anthropic の `thinking`、OpenAI の `reasoning_effort` 等）はアダプタ内に封じ込め、エージェント／レポート側からは見えない
- **Devcontainer 限定実行**: Python バックエンドは devcontainer 外から起動しない（Cursor プラグインからも devcontainer に接続）

### 1.3 観測可能性

- `structlog` で以下を必ず記録：`request_id`, `correlation_id`, `actor`（persona または "system"）, `previous_state`, `next_state`
- 記録ポイント：ingest 完了、各ノード entry/exit、LLM 呼出し（provider / model / usage / cache hit / thinking tokens）、shield 検知、conflict 発生・裁定、Q&A 交換、gws 呼出し成否、承認イベント

---

## 2. サブエージェント（ペルソナ）定義

v1 の `AgentRole` enum（`TECH_LEAD` / `LINTING` / `SECURITY` / `VERIFIER`）は互換性のため温存。v2 用に新規 enum を追加する。

```python
class AgentPersona(StrEnum):
    SENTINEL        = "sentinel"          # Orchestrator
    SECURITY_GUARD  = "security_guard"
    ARCHITECT       = "architect"
    DOMAIN          = "domain"
    PERFORMANCE     = "performance"
```

| ペルソナ | 責務 | 主要入力 | 主要ツール | プロンプト | 出力 |
|---|---|---|---|---|---|
| `SENTINEL` | 並列起動・調停・最終レポート生成・Q&A 応答 | ReviewRequestV2 / 全 agent reports / Q&A 質問 | LangGraph state, `LLMProvider` | `prompts/sentinel.xml`（要件内システムプロンプトを literal 配置） | `OrchestratorDecision`, `ReviewReportV2`, Q&A 応答 |
| `SECURITY_GUARD` | 機密情報ハードコード／パストラバーサル／shield 逸脱検出 | target_files, `ShieldResult` | `ModelArmorMiddleware`, secrets regex | `prompts/security_guard.xml` | `list[FindingV2]` |
| `ARCHITECT` | 継承の深さ／composition 準拠／ARCHITECTURE・SPEC・AGENTS 整合 | target_files AST, 設計文書群 | `LLMProvider`, `ast` | `prompts/architect.xml` | `list[FindingV2]` |
| `DOMAIN` | ビジネスロジックと **NotebookLM（絶対正）** の整合検証 | target_files, NotebookLM 抜粋 | `InformationSource`（NotebookLM） | `prompts/domain.xml`（情報階層 literal 埋込） | `list[FindingV2]` |
| `PERFORMANCE` | async ブロッキング／N+1／同期 I/O 検出 | target_files AST | `LLMProvider`, AST パターン | `prompts/performance.xml` | `list[FindingV2]` |

### 2.1 `ReviewTargetKind` によるペルソナ重み付け

```python
class ReviewTargetKind(StrEnum):
    DOCUMENT    = "document"
    SOURCE_CODE = "source_code"
    MIXED       = "mixed"
```

| Target Kind | 主軸ペルソナ（必須） | 補助ペルソナ |
|---|---|---|
| `DOCUMENT` | DOMAIN, ARCHITECT | SECURITY_GUARD, PERFORMANCE |
| `SOURCE_CODE` | SECURITY_GUARD, PERFORMANCE, ARCHITECT | DOMAIN |
| `MIXED` | 全ペルソナ均等 | — |

`DOCUMENT` レビュー時のみ `ReviewRequestV2.use_codebase_as_reference: bool` が有効。True のときコードベースは `AuthorityLevel.REFERENCE`（絶対正ではない）で `IngestedDocument` 化される。

### 2.2 共通仕様

- すべて `ReviewAgent` protocol を実装（§6 参照）
- `AgentExecutor` 経由で LLM を呼出す（shield 強制、provider 抽象、監査ログ）
- タイムアウト既定 120s。超過時は `AgentTimeoutError`（v1 既存）
- 1 ペルソナの失敗では全体停止せず、`state.failures` に積み、Sentinel が欠損を明示してレポート生成

---

## 3. LangGraph ワークフロー（Automation 経路）

### 3.1 State 定義

```python
# src/v2/automation/graph/state.py
class SentinelState(TypedDict):
    request: ReviewRequestV2                     # §6.2 で定義（v1 ReviewRequest とは別型）
    correlation_id: str                          # gws 全呼出しで必須、request_id と 1:1
    ingested: Sequence[IngestedDocument]         # ingest 層が正規化した全入力
    prior_form: ReviewRequestForm | None         # レビュー依頼票（任意）
    notebook_context: NotebookContext            # DOMAIN 用・絶対正データ
    focus_hints: Sequence[str]                   # 利用者が指定した注目領域
    agent_reports: dict[AgentPersona, AgentReport]
    conflicts: list[Conflict]
    resolutions: list[Resolution]
    final_report: ReviewReportV2 | None
    failures: list[AgentFailure]
```

参照型の所在：
- `ReviewRequestV2`, `IngestedDocument`, `ReviewRequestForm`, `Conflict`, `Resolution` → §6.2 / §6.3 / §5.2 で定義
- `NotebookContext` → `src/v2/sources/notebook.py`（`InformationSource` 由来の抜粋束）
- `AgentReport`, `AgentFailure` → `src/v2/agents/base.py`（後述）


### 3.2 ノード構成

```
START
  ▼
(1) prepare_context            ingest 全入力、prior_form 正規化、NotebookLM
                               フェッチ、shield_input、correlation_id 確定
  ▼
(2) fan_out_agents             Send API で target_kind に応じたペルソナを並列起動
  ├► (2a) security_guard      ┐
  ├► (2b) architect           │ ReviewAgent.review() を呼ぶ共通実装
  ├► (2c) domain              │ 1 エージェントの例外は failures に積む（継続）
  └► (2d) performance         ┘
  ▼
(3) detect_conflicts           同一箇所の severity 乖離 / DOMAIN 矛盾 /
                               security override conflict を抽出
  ▼
(4) resolve_conflicts          SentinelResolver が <information_hierarchy>
                               literal 埋込で Provider 経由裁定
  ▼
(5) compose_report             ReviewReportV2 を構造化、shield_output 全文適用
  ▼
(6) persist_and_publish        .review/report.md + gws Docs/Sheets
                               correlation_id 強制、失敗時 stderr サマリー記録
  ▼
END → status: completed_pending_approval
```

### 3.3 チェックポイントと再実行

- `SqliteSaver` を `.review/checkpoints.sqlite` に配置
- `aegis review-v2 --resume <request_id>` で失敗ノード以降のみ再実行
- 各ノード終了時に `.review/artifacts/<node>.json` を `TaskDispatcher._sync_atomic_write`（v1 流用）で永続化

### 3.4 並列実行の制約

- `fan_out_agents` は LangGraph `Send` API（`add_conditional_edges`）で実装
- 共有ステートは read-only slice のみ渡す。ミューテーションは reducer 経由に強制
- LLM 同時呼出しは `LLM_PROVIDER_MAX_CONCURRENT` 既定 4（env）
- shield セマフォは v1 `core.Orchestrator._shield_semaphore` をそのまま継承

---

## 4. LLM Provider 抽象化

### 4.1 プロトコル

```python
# src/v2/llm/provider.py
class ProviderFeature(StrEnum):
    ADAPTIVE_THINKING  = "adaptive_thinking"
    REASONING_EFFORT   = "reasoning_effort"
    PROMPT_CACHING     = "prompt_caching"
    JSON_MODE          = "json_mode"
    TOOL_USE           = "tool_use"

@dataclass(frozen=True)
class ReasoningConfig:
    mode:   Literal["off", "light", "deep", "adaptive"] = "adaptive"
    effort: Literal["low", "medium", "high", "xhigh"]   = "xhigh"

@dataclass(frozen=True)
class CacheHint:
    block_id: str
    ttl: Literal["ephemeral", "persistent"] = "ephemeral"

@dataclass(frozen=True)
class TokenUsage:
    input_tokens:  int
    output_tokens: int
    cache_read_input_tokens:  int = 0
    cache_creation_input_tokens: int = 0
    thinking_tokens: int = 0

@dataclass(frozen=True)
class ProviderResponse:
    content:     str
    usage:       TokenUsage
    raw:         object          # デバッグ用
    stop_reason: str

@runtime_checkable
class LLMProvider(Protocol):
    name:     str                # "anthropic" | "openai" | "mock"
    model_id: str

    def supports(self, feature: ProviderFeature) -> bool: ...
    async def complete(
        self,
        *,
        system:          Sequence[SystemBlock],
        messages:        Sequence[Message],
        tools:           Sequence[Tool] = (),
        max_tokens:      int,
        reasoning:       ReasoningConfig | None = None,
        cache_hints:     Sequence[CacheHint] = (),
        response_format: Literal["text", "json"] = "text",
    ) -> ProviderResponse: ...
    async def close(self) -> None: ...
```

### 4.2 アダプタ実装マッピング

| 機能 | AnthropicProvider | OpenAIProvider | 未サポート時の扱い |
|---|---|---|---|
| 基本呼出し | `messages.create` (claude-opus-4-7) | `responses.create` / `chat.completions` | — |
| `ReasoningConfig.mode=adaptive` | `thinking={"type":"adaptive"}` | `reasoning={"effort":...}` にマップ | `supports()=False`、呼出しは成功、`structlog.info("provider_feature_unavailable", ...)` |
| `ReasoningConfig.effort=xhigh` | `extra_body={"output_config":{"effort":"xhigh"}}` | `reasoning_effort="high"` にマップ | 既定値で続行 |
| `CacheHint` | `cache_control: {"type":"ephemeral"}` を当該 block に付与 | OpenAI 自動キャッシュに委譲（no-op） | 無視。`usage.cache_*=0` |
| `response_format="json"` | tool_use で JSON schema 強制 | `response_format={"type":"json_object"}` | アダプタ内で JSON パース検証 |
| Retry | `anthropic.RateLimitError` 等 | `openai.RateLimitError` 等 | `RetryConfig` 共通（§7.3） |

**最低要件**: `TOOL_USE` と `JSON_MODE` は全 provider 必須サポート（Sentinel の JSON 裁定出力に依存）。未サポートの provider はレジストリ登録時に `ValueError`。

### 4.3 `AgentExecutor`

```python
# src/v2/llm/executor.py
class AgentExecutor:
    def __init__(self, provider: LLMProvider, shield: SecurityShield) -> None:
        self.provider = provider
        self.shield   = shield

    async def invoke(
        self,
        *,
        persona: AgentPersona,
        system_blocks: Sequence[SystemBlock],    # cache_hint 付き
        user_content:  Sequence[ContentBlock],
        reasoning:     ReasoningConfig | None = None,
        response_format: Literal["text","json"] = "text",
        max_tokens: int = 8_000,
    ) -> AgentResponse:
        # 1) shield_input を user_content 全文に適用
        # 2) provider.complete(...)  ← provider 固有詳細は隠蔽
        # 3) shield_output を応答本文に適用
        # 4) structlog: provider=self.provider.name, model=..., usage, cache hit,
        #               thinking_tokens, feature_fallbacks=[...]
```

Anthropic 固有パラメータ（`thinking`、`output_config.effort`、`cache_control`）は **アダプタ内でのみ** 扱う。エージェント実装・レポート・プロンプト資産からは見えない。

### 4.4 プロンプト資産（Provider-Neutral）

- `src/v2/prompts/*.xml` が **Single Source of Truth**
- `<thinking>` や `cache_control` といった provider 固有タグは埋め込まない。アダプタ側で注入
- Interactive 経路では `src/v2/interactive/rules_sync.py` が `.cursor/rules/*.mdc` を自動生成（drift を CI テストで検知）

### 4.5 設定

```python
# src/core/config.py に追加
class LLMProviderConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LLM_PROVIDER_")
    name:             Literal["anthropic", "openai", "mock"] = "anthropic"
    model_id:         str   = "claude-opus-4-7"
    reasoning_mode:   Literal["off","light","deep","adaptive"] = "adaptive"
    reasoning_effort: Literal["low","medium","high","xhigh"]   = "xhigh"
    max_concurrent:   int   = 4
    api_key_env_var:  str   = "ANTHROPIC_API_KEY"   # OpenAI 時は "OPENAI_API_KEY"
```

切替例（OpenAI）: `.env` に `LLM_PROVIDER_NAME=openai`, `LLM_PROVIDER_MODEL_ID=gpt-5`, `LLM_PROVIDER_API_KEY_ENV_VAR=OPENAI_API_KEY`。

---

## 5. 情報階層と衝突調停

### 5.1 情報源の権威レベル

```python
# src/v2/core/hierarchy.py
class AuthorityLevel(StrEnum):
    ABSOLUTE   = "absolute"     # NotebookLM — 他と矛盾したら必ず勝つ
    PRIMARY    = "primary"      # Target code / Target docs
    REFERENCE  = "reference"    # Google Docs / PDF / 他関連文書
    CONVENTION = "convention"   # エージェントの事前知識
```

| レベル | ソース | 実体 |
|---|---|---|
| ABSOLUTE | NotebookLM | `InformationSource`（NotebookLM アダプタ） |
| PRIMARY | 対象 | `ReviewRequestV2.target_docs`（SOURCE_CODE / DOCUMENT / MIXED いずれも） |
| REFERENCE | 関連ドキュメント | ingest された `IngestedDocument`（`ARCHITECTURE.md`, 関連 PDF 等） |
| CONVENTION | LLM 事前知識 | 明示情報が無い場合のみ |

### 5.2 Conflict 検出（`detect_conflicts` ノード）

以下のいずれかで `Conflict` を生成：

1. 同一 `(file_path, line)` の Finding が 2 ペルソナ以上から出て、`severity` が 2 段階以上乖離
2. `DOMAIN` の Finding と他ペルソナの Finding が同一箇所で相互矛盾
3. `SECURITY_GUARD` が `high` / `critical` をつけた箇所に、他ペルソナが不整合な `recommendation` を提示

```python
@dataclass(frozen=True)
class Conflict:
    conflict_id:      str
    location:         Location
    findings:         Sequence[FindingV2]
    conflict_type:    Literal["severity_divergence", "domain_contradiction",
                               "security_override_conflict"]
    involved_personas: frozenset[AgentPersona]
```

### 5.3 `ConflictResolver`（Sentinel による裁定）

- `ConflictResolver` protocol の具象 `SentinelResolver`
- システムプロンプトに `<information_hierarchy>` と `<core_directives>` を literal 埋込
- Provider 経由で JSON 応答を強制：

```json
{
  "decision": "uphold | override | merge | escalate",
  "winning_persona": "DOMAIN | SECURITY_GUARD | ARCHITECT | PERFORMANCE",
  "rationale": "NotebookLM §3.2 が...",
  "authority_level_applied": "ABSOLUTE | PRIMARY | REFERENCE | CONVENTION",
  "merged_finding": { ... }
}
```

- `escalate`（Claude が判断できない）は `next_steps` に「ユーザー確認必要」として残す
- `winning_persona == DOMAIN` かつ `authority_level_applied == ABSOLUTE` の場合、他ペルソナの反対意見は `superseded_by` メタで残しつつ非表示化（監査には全文保持）
- 裁定結果は `.review/conflicts/<conflict_id>.json` に atomic write
- `structlog.info("conflict_resolved", conflict_id, decision, winning_persona, authority_level_applied, request_id, correlation_id, actor="sentinel")`

---

## 6. 型拡張とレポートフォーマット

v1 の `src/core/types.py` は **一切変更しない**。新規型はすべて `src/v2/core/` 配下に配置する。

### 6.1 日本語分類 enum

```python
# src/v2/core/enums.py
class CommentType(StrEnum):
    ISSUE    = "指摘"
    REQUEST  = "要望"
    QUESTION = "質問"

class BugCategory(StrEnum):
    CURRENT_PHASE  = "当工程バグ"
    UPSTREAM_PHASE = "上位工程バグ"
    BASE_CODE      = "母体バグ"
    NOT_A_BUG      = "バグではない"

class BugPhenomenon(StrEnum):
    DESIGN_OMISSION        = "設計漏れ"
    DESIGN_ERROR           = "設計誤り"
    DESIGN_INTERFACE_MISS  = "設計インタフェースミス"
    DESIGN_EXPRESSION      = "設計表現不備"
    DESIGN_STANDARDIZATION = "設計標準化ミス"
    TEST_ITEM_MISS         = "テスト項目ミス"
    CODING_MISS            = "コーディングミス"
    CODING_STANDARDIZATION = "コーディング標準化ミス"

class RootCause(StrEnum):
    INSUFFICIENT_CONSIDERATION     = "検討不足"
    INSUFFICIENT_SPEC_CHECK        = "仕様確認不足"
    POST_REVIEW_FIX_FAILURE        = "レビュー後修正不備"
    COMMUNICATION_FAILURE          = "連絡不備"
    INSUFFICIENT_BUSINESS_KNOWLEDGE= "業務知識不足"
    INSUFFICIENT_METHOD_KNOWLEDGE  = "方式知識不足"
    INSUFFICIENT_BASIC_SKILL       = "基本スキル不足"
    INSUFFICIENT_STANDARD_CHECK    = "標準書確認不足"
    INSUFFICIENT_STANDARDIZATION   = "標準化不備"
    INSUFFICIENT_ATTENTION         = "注意不足"
```

### 6.2 入力型

```python
# src/v2/core/types.py
@dataclass(frozen=True)
class Provenance:
    origin:          Literal["drive_url", "upload", "local_path", "cursor_context"]
    uri:             str
    fetched_at:      datetime
    correlation_id:  str

@dataclass(frozen=True)
class IngestedDocument:
    doc_id:     str
    format:     Literal["gdocs","gsheets","gslides","docx","xlsx","pptx",
                        "pdf","image","source_code","markdown","plaintext"]
    content:    str                      # テキスト正規化済み
    structured: Mapping[str, Any] | None # テーブル／シート構造等
    provenance: Provenance
    authority_level: AuthorityLevel
    metadata:   Mapping[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class PriorReviewComment:
    commenter:       str
    location:        Location
    comment:         str
    comment_type:    CommentType
    answerer:        str | None
    answer_date:     date | None
    answer:          str | None
    bug_category:    BugCategory | None
    bug_phenomenon:  BugPhenomenon | None
    root_cause:      RootCause | None
    severity:        Severity
    confirmer:       str | None
    confirm_date:    date | None

@dataclass(frozen=True)
class ReviewRequestForm:
    source:         IngestedDocument
    prior_comments: Sequence[PriorReviewComment]

@dataclass(frozen=True)
class ReviewRequestV2:                        # v1 ReviewRequest (src/core/types.py) とは別型
    request_id:    str
    correlation_id: str
    kind:          ReviewTargetKind
    target_docs:   Sequence[IngestedDocument]       # 主対象（AuthorityLevel.PRIMARY）
    reference_docs:Sequence[IngestedDocument] = ()  # REFERENCE
    notebook_docs: Sequence[IngestedDocument] = ()  # ABSOLUTE
    prior_form:    ReviewRequestForm | None   = None
    focus_hints:   Sequence[str]              = ()
    use_codebase_as_reference: bool           = False
```

v1 `ReviewRequest`（`src/core/types.py`）は不変で残し、v2 経路では `ReviewRequestV2` を用いる。`prepare_context` ノード内で v1 `core.Orchestrator` を呼び出す際は、`target_docs` のうち `format="source_code"` のものから v1 `ReviewRequest` を構築してアダプトする。


### 6.3 出力型

```python
@dataclass(frozen=True)
class Location:
    doc_id:    str
    file_path: Path | None = None
    line:      int  | None = None
    section:   str  | None = None

@dataclass(frozen=True)
class FindingV2:
    finding_id:       str
    location:         Location
    comment_type:     CommentType
    bug_category:     BugCategory
    bug_phenomenon:   BugPhenomenon
    root_cause:       RootCause
    severity:         Severity            # v1 Literal 流用
    details:          str                 # 複数行可
    recommendation:   str
    source_persona:   AgentPersona
    authority_level:  AuthorityLevel
    superseded_by:    str | None = None   # 調停敗者の場合、勝者 finding_id
    relates_to_prior: str | None = None   # PriorReviewComment との関連

class ReviewStatus(StrEnum):               # v1 Literal を拡張
    PENDING                    = "pending"
    IN_PROGRESS                = "in_progress"
    COMPLETED_PENDING_APPROVAL = "completed_pending_approval"
    APPROVED                   = "approved"
    FAILED                     = "failed"

@dataclass(frozen=True)
class ReviewReportV2:
    request_id:        str
    correlation_id:    str
    target_name:       str
    reviewed_at:       datetime
    status:            ReviewStatus
    executive_summary: str
    findings:          Sequence[FindingV2]
    next_steps:        Sequence[str]
    raw_agent_reports: Mapping[AgentPersona, AgentReport]   # 監査用
    qna_threads:       Mapping[str, QnAThread] = field(default_factory=dict)
    approval:          Approval | None = None

@dataclass(frozen=True)
class Approval:
    approver:         str
    approved_at:      datetime
    approver_comment: str | None
    report_hash:      str
```

### 6.4 Markdown レンダラ

- 要件の `<report_format>` を **literal に遵守**。見出し・箇条書き順序・日本語ラベルを一字一句維持
- AI 的前置き（「Here is the report...」等）は禁止。テンプレートは f-string で固定、LLM 生成部分は `executive_summary` / 各 finding の `details` と `recommendation` のみ
- Sentinel の LLM 呼出しで `executive_summary` と findings の散文説明を生成 → renderer がテンプレートに差し込み
- 出力先：
  1. `.review/report.md`（一次成果物）
  2. Google Docs（`gws docs create --correlation-id=<id>`）
  3. Google Sheets（findings をフラット化、`gws sheets append`）
- 承認ステータスに応じて `[未承認]` / `[承認済み]` フッターを付与

### 6.5 エージェント基盤型（`src/v2/agents/base.py`）

```python
@dataclass(frozen=True)
class AgentContext:
    persona:         AgentPersona
    request:         ReviewRequestV2
    correlation_id:  str
    ingested:        Sequence[IngestedDocument]
    notebook_context: NotebookContext
    prior_comments:  Sequence[PriorReviewComment]
    focus_hints:     Sequence[str]

@dataclass(frozen=True)
class AgentReport:
    persona:   AgentPersona
    findings:  Sequence[FindingV2]
    duration_ms: int
    usage:     TokenUsage | None

@dataclass(frozen=True)
class AgentFailure:
    persona: AgentPersona
    error:   str       # 例外クラス名 + メッセージ（スタックは structlog へ）

@dataclass(frozen=True)
class AgentResponse:
    text:   str
    json:   Mapping[str, Any] | None    # response_format="json" 時のみ
    usage:  TokenUsage

@dataclass(frozen=True)
class Resolution:
    conflict_id:             str
    decision:                Literal["uphold","override","merge","escalate"]
    winning_persona:         AgentPersona | None
    rationale:               str
    authority_level_applied: AuthorityLevel
    merged_finding:          FindingV2 | None

@dataclass(frozen=True)
class QnAThread:
    finding_id: str
    turns:      Sequence[QnATurn]

@dataclass(frozen=True)
class QnATurn:
    role:      Literal["user","sentinel"]
    content:   str
    timestamp: datetime
    usage:     TokenUsage | None
```

### 6.6 Provider 中立コンテンツ型（`src/v2/llm/provider.py`）

```python
@dataclass(frozen=True)
class SystemBlock:
    text:       str
    cache_hint: CacheHint | None = None

@dataclass(frozen=True)
class ContentBlock:
    type: Literal["text", "image", "tool_result"]
    text: str | None = None
    image_url: str | None = None
    tool_use_id: str | None = None

@dataclass(frozen=True)
class Message:
    role:    Literal["user", "assistant"]
    content: Sequence[ContentBlock]

@dataclass(frozen=True)
class Tool:
    name:        str
    description: str
    input_schema: Mapping[str, Any]    # JSON Schema
```

上記は provider-neutral。各アダプタが対応 SDK の型に変換する。

### 6.7 Ingest 補助型

```python
@dataclass(frozen=True)
class IngestSource:
    kind: Literal["drive_url","file_path","bytes"]
    value: str | Path | bytes
    mime_hint: str | None = None

@dataclass(frozen=True)
class SourceExcerpt:
    source_id:      str
    excerpt:        str
    authority_level: AuthorityLevel
    citation:       str        # 例: "NotebookLM §3.2"
```

### 6.8 プロトコル追加

`src/core/protocols.py` に以下を追記（既存は不変）：

```python
@runtime_checkable
class ReviewAgent(Protocol):
    persona: AgentPersona
    async def review(self, ctx: AgentContext) -> AgentReport: ...

@runtime_checkable
class ConflictResolver(Protocol):
    async def resolve(self, conflicts: Sequence[Conflict],
                      state: SentinelState) -> Sequence[Resolution]: ...

@runtime_checkable
class InformationSource(Protocol):
    authority_level: AuthorityLevel
    async def query(self, q: str, *, correlation_id: str) -> SourceExcerpt: ...

@runtime_checkable
class DocumentIngestor(Protocol):
    supported_formats: frozenset[str]
    async def ingest(self, source: IngestSource, *, correlation_id: str)
        -> IngestedDocument: ...
```

---

## 7. システム統合（Cursor / 移行 / 検証）

### 7.1 Cursor プラグイン「Skill Orchestra」I/F

**役割分担**:
- **Cursor 側（TypeScript, `cursor-extension/` 新規）**: UI のみ。LLM 呼出しは Cursor Agent に委譲
- **Python バックエンド（devcontainer 内）**: `src/cli/main.py` に `review-v2` サブコマンドを追加し、MCP サーバ（`src/v2/mcp/server.py`）を起動

**通信**:
- プラグインは devcontainer 内 Python を起動: `uv run aegis review-v2 --mode=interactive`
- 起動後、Cursor と MCP サーバが stdio で接続。プラグインは MCP 経由で backend ツールを呼ぶ
- 進捗購読：`.review/status.json` を Cursor プラグインが `chokidar` で watch
- 最終成果物：`.review/report.md` を Cursor のエディタタブで自動 open

**Cursor プラグイン UI 要素**（MVP）:
- レビュー対象投入：ファイル選択 / Google Drive 共有 URL 入力 / 現在開いているファイルのインライン指定
- 対象分類トグル：DOCUMENT / SOURCE_CODE / MIXED
- 「コードベースを参考資料に含める」チェックボックス（DOCUMENT 時のみ活性）
- 関連文書 / NotebookLM / レビュー依頼票の個別投入スロット
- 補足事項入力欄（→ `focus_hints`）
- 進捗表示（各ペルソナの状態、現在ノード）
- レポート表示パネル
- 各 finding 横の「このコメントについて質問する」ボタン（→ `/aegis ask`）
- レポート末尾の「承認」ボタン（→ `/aegis approve`）

**`.review/status.json` スキーマ**:

```json
{
  "request_id": "uuid",
  "correlation_id": "uuid",
  "phase": "ingest|prepare|fan_out|resolve|compose|publish|completed_pending_approval|qna|approved|failed",
  "agent_progress": {
    "SECURITY_GUARD": {"status": "in_progress|completed|failed", "started_at": "..."},
    "ARCHITECT":  {...},
    "DOMAIN":     {...},
    "PERFORMANCE":{...}
  },
  "updated_at": "ISO8601",
  "error": null
}
```

**CLI コマンド**:

| コマンド | 機能 |
|---|---|
| `aegis review-v2 --target <paths> [--kind document|source_code|mixed]` | 新規レビュー開始 |
| `aegis review-v2 --resume <request_id>` | チェックポイントから再開（Automation） |
| `aegis review-v2 --dry-run` | LLM 呼出しなし。graph 構造のみ検証 |
| `aegis review-v2 --mode interactive|automation|auto` | 経路選択（既定 auto） |
| `aegis ask <request_id> <finding_id> --question "..."` | Q&A 追問 |
| `aegis approve <request_id> --approver <name> [--comment "..."]` | 最終承認 |
| `aegis report show <request_id>` | 過去レポート表示 |

**運用モード選択ロジック（`--mode auto`）**:
- `CI=true` 検出 → `automation`
- それ以外 → `interactive` を推奨表示（Cursor 内の MCP セッションが無ければフェイルセーフで `automation` に切替）

### 7.2 ディレクトリ構成（最終形）

```
src/
├── core/                         # v1: 不変
│   ├── protocols.py              # ← ReviewAgent / ConflictResolver /
│   │                             #    InformationSource / DocumentIngestor を追記
│   ├── orchestrator.py           # v1: 不変（v2 の prepare_context から呼出）
│   ├── types.py                  # v1: 不変
│   └── config.py                 # ← LLMProviderConfig を追記
├── plugins/                      # v1: 不変
│   ├── agents/                   # ファイルベース通信は監査用途で残置
│   ├── security/                 # ModelArmorMiddleware 流用
│   ├── sync/                     # report_writer.py を correlation_id 対応
│   └── rules/
└── v2/                           # 新規（v2 専用）
    ├── core/
    │   ├── enums.py              # AgentPersona / CommentType / BugCategory / ...
    │   ├── hierarchy.py          # AuthorityLevel, information_hierarchy util
    │   └── types.py              # FindingV2, ReviewReportV2, IngestedDocument, ...
    ├── prompts/                  # 共有（両経路が参照）
    │   ├── sentinel.xml
    │   ├── security_guard.xml
    │   ├── architect.xml
    │   ├── domain.xml
    │   ├── performance.xml
    │   ├── qna_followup.xml
    │   └── information_hierarchy.xml
    ├── ingest/                   # 多形式入力（共有）
    │   ├── protocol.py
    │   ├── registry.py
    │   ├── resolver.py           # Drive URL → ファイル（gws + correlation_id）
    │   └── adapters/
    │       ├── gdocs.py
    │       ├── gsheets.py
    │       ├── gslides.py
    │       ├── office.py
    │       ├── pdf.py
    │       ├── image.py
    │       └── source_code.py
    ├── llm/                      # Provider 抽象（共有、実利用は Automation）
    │   ├── provider.py
    │   ├── executor.py
    │   ├── registry.py
    │   └── providers/
    │       ├── anthropic.py
    │       ├── openai.py
    │       └── mock.py
    ├── agents/                   # 共有（ReviewAgent 実装）
    │   ├── base.py
    │   ├── security_guard.py
    │   ├── architect.py
    │   ├── domain.py
    │   └── performance.py
    ├── automation/               # Automation 経路 専用
    │   ├── graph/
    │   │   ├── state.py
    │   │   ├── nodes.py
    │   │   ├── edges.py
    │   │   └── builder.py
    │   └── resolver/
    │       └── sentinel.py
    ├── interactive/              # Interactive 経路 専用
    │   └── rules_sync.py         # prompts/*.xml → .cursor/rules/*.mdc 生成
    ├── mcp/                      # MCP サーバ（両経路共通のツール層）
    │   ├── server.py             # FastMCP ベース
    │   └── tools/
    │       ├── notebook_query.py
    │       ├── gws_publish.py
    │       ├── shield_input.py
    │       ├── shield_output.py
    │       ├── ast_scan.py
    │       ├── artifact_write.py
    │       ├── status_publish.py
    │       ├── ingest_resolve.py
    │       ├── ask_about_finding.py
    │       └── submit_finding.py
    ├── qna/                      # Q&A ループ（共有）
    │   ├── session.py
    │   └── store.py
    ├── report/                   # 共有
    │   ├── renderer.py
    │   └── publisher.py
    ├── sources/                  # 共有
    │   ├── notebook.py
    │   └── gws_docs.py
    └── approval/
        └── recorder.py           # Approval 記録（human-only 遷移）

.cursor/
└── rules/                        # interactive/rules_sync.py が生成（手編集禁止）
    ├── aegis-sentinel.mdc
    ├── aegis-security-guard.mdc
    ├── aegis-architect.mdc
    ├── aegis-domain.mdc
    └── aegis-performance.mdc

cursor-extension/                 # Cursor 拡張（TypeScript、UI のみ）
├── package.json
└── src/
    ├── extension.ts              # /aegis review / ask / approve コマンド登録
    ├── mcpBridge.ts              # devcontainer 内 MCP サーバ起動 & 接続
    ├── uploadPanel.ts            # 多形式入力 UI
    └── statusWatcher.ts          # .review/status.json 購読

.review/                          # 実行時ランタイム（gitignore）
├── artifacts/                    # ノード／エージェント境界スナップショット
├── conflicts/                    # Resolver の裁定
├── qna/<finding_id>/             # Q&A 会話ログ
├── checkpoints.sqlite            # Automation のみ
├── status.json
├── report.md
└── approved.json                 # 承認記録
```

### 7.3 v1 との共存・移行方針

| 要素 | v1 | v2 | 方針 |
|---|---|---|---|
| `AgentRole` enum | TECH_LEAD/LINTING/SECURITY/VERIFIER | — | 温存（既存 dispatcher.py のため） |
| `AgentPersona` enum | — | SENTINEL/SECURITY_GUARD/ARCHITECT/DOMAIN/PERFORMANCE | 新規。両 enum を受容する `AgentIdentity` union を追加 |
| `core.Orchestrator` | Model Armor + 並列シールド | 同じ | v2 の `prepare_context` から再利用 |
| `TaskDispatcher` | 全通信 | 監査 artifact 書込みのみ | atomic write を流用 |
| `ModelArmorMiddleware` | shield_input/output | 同じ | `AgentExecutor` が DI で受け取り、全 LLM 呼出しに強制適用 |
| `RetryConfig` | google API エラー | + LLM provider エラー | `retryable_exceptions` に `anthropic.RateLimitError` / `anthropic.APITimeoutError` / `openai.RateLimitError` 等を追加 |
| `report_writer.py` | gws 呼出し | 同じ | `correlation_id` を必須引数化（型で強制） |
| CLI | `llm-review` | + `aegis` | `[project.scripts]` に `aegis = "cli.main:app"` を追加、旧 `llm-review` はエイリアス温存 |
| `src/core/protocols.py` | `ReviewPlugin` / `SecurityShield` | 既存不変、4 protocol 追記 | 後方互換完全維持 |
| `src/core/types.py` | 既存型群 | 一切変更しない | v2 新規型は `src/v2/core/types.py` へ |

**依存関係追加**（`pyproject.toml`）:
- 必須: `langgraph>=0.2`, `langchain-core>=0.3`, `python-docx`, `openpyxl`, `python-pptx`, `pypdf`, `mcp>=0.9`（FastMCP）
- Optional extras:
  - `provider-anthropic`: `anthropic>=0.40`
  - `provider-openai`: `openai>=1.50`
- 既定で `provider-anthropic` を dev extra に含める

### 7.4 Q&A ループ（ステップ10）の実装詳細

**目的**: レビュー依頼者の心理的負担軽減。finding の根拠を即座に問い返せる。

```
Report 生成後
  │
  │ ユーザーが finding_id を指定して質問
  ▼
MCP tool: ask_about_finding(finding_id, question, correlation_id)
  │
  ▼
QnASession が以下を Sentinel(Provider 経由) に渡す:
  - 対象 finding の全メタデータ
  - 元コード／ドキュメント該当箇所
  - NotebookLM 絶対正抜粋（DOMAIN 由来 finding の場合）
  - この finding の過去 Q&A スレッド
  - <information_hierarchy> と <core_directives>
  │
  ▼
応答を .review/qna/<finding_id>/<NNN>.md に atomic write
shield_output を必ず適用
structlog: qna_exchange (finding_id, turn, usage, ...)
```

- プロンプト `src/v2/prompts/qna_followup.xml` は「レビュー指摘の根拠を人間に納得させる」ことに特化
- Cursor UI：各 finding 横にボタン。Automation 経路では CLI `aegis ask` で対話
- Q&A ログは `ReviewReportV2.qna_threads` に最終取込み、承認時に固定化

### 7.5 検証戦略

**品質ゲート**（全てパスで成功報告）:

```bash
uv sync
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest -m "not integration"
```

**テスト方針**:

| レイヤ | 対象 | 方針 |
|---|---|---|
| Unit | `v2/core/*`, `hierarchy`, `report/renderer` | pure function、LLM 呼出しなし |
| Unit | 各 `v2/agents/*` | `AgentExecutor` をフェイク provider に差替 |
| Unit | `v2/llm/provider` 契約 | `test_provider_contract.py` で Anthropic/OpenAI/Mock 共通スイートを適用 |
| Unit | Feature matrix | `provider.supports(...)` の実装状況一致 |
| Unit | Degradation | OpenAI で `CacheHint` 渡しても例外が出ず `cache_read_input_tokens=0`、`provider_feature_unavailable` が記録 |
| Unit | `automation/graph/builder` | dry-run で StateGraph 構築が例外なく終わる |
| Unit | `automation/resolver/sentinel` | 固定 Conflict → mock response で裁定ルール検証 |
| Unit | `ingest/adapters/*` | 各フォーマットのサンプルファイルでの正規化テスト |
| Unit | `qna/session` | turn 積み重ね、shield 強制、atomic write |
| Unit | `approval/recorder` | LLM 経由で `APPROVED` 遷移を試みるテストが失敗することを確認 |
| Unit | **Drift テスト** | `prompts/*.xml` と `.cursor/rules/*.mdc` の同期を保証 |
| Unit | **契約テスト** | MCP ツールが両経路から呼ばれても同じ `FindingV2` / `ReviewReportV2` を返す |
| Integration (`@integration`) | LLM Provider / NotebookLM / gws | CI では skip、devcontainer でのみ実行 |
| E2E | `aegis review-v2 --dry-run` | 小リポジトリで graph 全ノード通過、`.review/` 成果物検証 |
| Security | secrets 偽装応答、パストラバーサル入力 | 必ず `SecurityBlockedError` または `[REDACTED]` に落ちる |

**非機能要件テスト**（主目的の指標化）:

| 指標 | 閾値 | 測定方法 |
|---|---|---|
| Q&A ラウンドトリップ p50 レイテンシ | ≤ 15s | Integration テストで 20 回計測 |
| 過去指摘との重複率 | ≤ 5% | `prior_form` 付きベンチマークで `relates_to_prior` 重複検出 |
| Provider 切替後の finding 数同等性 | ±10% 以内 | 同一入力で Anthropic / OpenAI 実行し finding 集合の Jaccard ≥ 0.85 |
| レビュー全体スループット | 対象 1 kLOC あたり ≤ 3 分 | E2E ベンチマーク |

**観測可能性**:
- `structlog` 必須フィールド：`request_id`, `correlation_id`, `actor`, `previous_state`, `next_state`
- LLM 呼出し時：`provider`, `model`, `usage.input/output/cache_read/cache_write/thinking`, `feature_fallbacks`
- gws 呼出し時：`correlation_id`, stderr サマリー（失敗時）

**セキュリティ検証**:
- `AgentExecutor` を介さない LLM 呼出し経路が存在しないことを契約テストで保証
- MCP サーバは stdio バインドのみ。TCP 公開は registry レベルで拒否
- API キーはロガーで自動マスキング（`structlog` processor）

### 7.6 オープン課題

1. Claude Opus 4.7 の `output_config.effort` パラメータは、公式 SDK が正式対応前の場合 `extra_body` 送信を要検証（SDK 版数依存）
2. LangGraph `Send` API を使った fan-out 並列は v0.2 系で stable だが、devcontainer 並列度上限と LLM provider rate limit の相互作用は実測で調整
3. NotebookLM Python クライアント（`notebooklm-py`）のクエリ応答 schema は公式未確定のため、`InformationSource` 実装は薄いアダプタに留め、変更時影響を最小化
4. Cursor の sub-agent API 仕様（並列起動・引数受け渡し）は Cursor 版数依存。`.cursor/rules/*.mdc` のフロントマター（`applyTo` / `spawn_as` 等）は版数確認後に確定
5. Cursor 経由の LLM 呼出しは usage/token がプログラム的には限定的にしか取得できない。Automation 経路と Interactive 経路の監査粒度差を運用手順書に明記する必要あり
6. 画像／スキャン PDF の OCR は MCP ツール経由で Vision モデルを呼ぶ予定だが、Vision モデルの provider 抽象化（Anthropic Vision / OpenAI Vision / Gemini Vision 等）は本設計書ではスコープ外（将来拡張）
7. レビュー依頼票の Excel/Sheet フォーマットは組織ごとにカラム配置が異なる可能性があるため、`adapters/office.py` 内に設定可能な **カラムマッピング YAML** を用意する方針とする（詳細は実装計画）

---

## 付録 A: 要件との対応表

| 要件項目（元要件） | 反映先 |
|---|---|
| Target LLM: claude-opus-4-7 | §4.5 `LLMProviderConfig.model_id` 既定値 |
| thinking: adaptive | §4.1 `ReasoningConfig.mode="adaptive"` / §4.2 Anthropic アダプタ |
| effort: xhigh | §4.1 `ReasoningConfig.effort="xhigh"` / §4.2 アダプタでマップ |
| Devcontainer 必須 | §1.2 原則、§7.1 プラグイン経路制約 |
| uv / ruff / mypy | §7.5 品質ゲート |
| gws に correlation_id 必須 | §6.2 `Provenance.correlation_id`、§7.2 report_writer 型強制 |
| structlog 状態遷移 | §1.3、§3 各ノード記録、§7.5 テスト |
| SecurityShield 強制 | §1.2 原則、§4.3 `AgentExecutor`、§7.5 契約テスト |
| Composition over Inheritance | §1.2 原則、§6.5 protocol 追記のみ |
| Multi-Agent Personas | §2 ペルソナ定義 |
| Information Hierarchy | §5 権威レベルと Resolver |
| Report Format 日本語区分 | §6.1 enum、§6.4 renderer literal 遵守 |
| Next Steps 明示 | §6.3 `ReviewReportV2.next_steps`、§5.3 escalate 処理 |
| 11 ステップ運用フロー | §0.2、§7.1 CLI、§7.4 Q&A |
| マルチ形式ドキュメント | §7.2 `src/v2/ingest/` |
| Drive URL / ファイルアップロード | §7.2 `ingest/resolver.py`、§7.1 Cursor UI |
| NotebookLM 絶対正 | §5.1 `AuthorityLevel.ABSOLUTE`、§2 DOMAIN |
| レビュー依頼票 | §6.2 `PriorReviewComment` / `ReviewRequestForm` |
| 重点箇所指定 | §6.2 `ReviewRequestV2.focus_hints` |
| Q&A ループ | §7.4、§6.3 `ReviewReportV2.qna_threads` |
| 人間最終承認 | §6.3 `ReviewStatus.APPROVED`、§7.2 `approval/recorder.py` |
| Provider 柔軟切替 | §4 全体、§7.5 契約テスト |

## 付録 B: 用語定義

- **Aegis Sentinel**: Orchestrator ペルソナ。複数ペルソナの調停と最終レポート生成を担う
- **correlation_id**: gws CLI およびクロスシステム呼出しのトレーシング ID。`request_id` と 1:1 対応
- **ABSOLUTE TRUTH**: NotebookLM 由来の情報。他と矛盾したら必ず勝つ
- **PRIMARY**: レビュー対象そのもの（コード／ドキュメント）
- **REFERENCE**: 関連文書（参考情報、絶対正ではない）
- **CONVENTION**: LLM の事前知識（明示情報が無いときのみ採用）
- **Skill Orchestra**: 本システムの Cursor プラグイン名
- **Drift テスト**: `prompts/*.xml` と `.cursor/rules/*.mdc` の同期を CI で保証するテスト
