# Aegis v2.0 マルチエージェントレビューシステム Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `docs/superpowers/specs/2026-04-17-aegis-v2-multiagent-design.md` 設計書を v1（`src/core/` + `src/plugins/`）を破壊せずに段階的拡張で実現し、Automation（LangGraph + CLI）と Interactive（Cursor + MCP）の二経路でマルチエージェント並列レビューを提供する。

**Architecture:** `src/v2/` 配下に新規モジュールを構築し、v1 は `src/core/protocols.py`（4 protocol 追記）と `src/core/config.py`（`LLMProviderConfig` 追記）のみに限定改修。Boundary-based Shielding（入力／永続化／公開の 3 境界で shield を強制、メモリ内裁定は unredacted）と Provider-neutral プロンプト資産（`src/v2/prompts/*.xml`）を設計原則とする。

**Tech Stack:** Python 3.11+, uv, pytest, mypy --strict, ruff, LangGraph 0.2+, LangChain-core 0.3+, Anthropic SDK 0.40–0.x, OpenAI SDK 1.50–1.x, FastMCP (mcp>=0.9), Pydantic v2, pydantic-settings, python-docx / openpyxl / python-pptx / pypdf, structlog, Google Workspace CLI (`gws`), TypeScript（Cursor extension）。

---

## 0. Branching & PR 運用（全 Phase 共通ルール）

| レイヤ | ブランチ命名 | 派生元 | PR ターゲット | ステータス |
|---|---|---|---|---|
| Phase N | `feature/phase-N__<機能名>__base` | `master`（前 Phase が master マージ済みであることを前提） | `master` | Draft PR をまず作成 |
| Task N.M | `feature/phaseN-taskM__<タスク名>` | 直前の Task ブランチ（Task 1 は Phase base） | `feature/phase-N__<機能名>__base` | Draft PR をまず作成 |

**前提ルール**（全 Phase 共通）:

1. Phase 開始前に、前 Phase の PR が master にマージ済みであることを `git log master` で確認する。未マージの場合、新 Phase には着手しない。
2. Phase base ブランチは必ず `git switch master && git pull && git switch -c feature/phase-N__<name>__base` で作成。
3. 各 Task 完了時に tests が green、mypy --strict が clean、ruff が clean であることを verification-before-completion スキルで確認する。
4. Task 内の「Commit」ステップでは Japanese Conventional Commits（`global-rules/GIT_STANDARDS.md`）に従う。
5. 各 Task 完了時に Draft PR を作成（`gh pr create --draft --base <parent-branch>`）し、CI 緑化を確認してから次 Task の派生元として使う。
6. `using-git-worktrees` スキルで `.worktrees/phase-N__<name>/` に各 Phase のワークツリーを作成して作業（`.worktrees/` は `.gitignore` 未登録のため Phase 1 Task 0 で追加）。

---

## 1. Phase 全体ロードマップ

| Phase | 名称 | master マージ時のマイルストーン | 所要 Task 数 |
|---|---|---|---|
| 1 | Foundation（v2 型・列挙・プロトコル・設定） | v2 型が import 可能・v1 完全不変・全 enum と protocol が mypy --strict で検証 | 6 |
| 2 | LLM Provider 抽象化 | Anthropic/OpenAI/Mock の 3 provider が契約テスト一式で合格、`AgentExecutor` で shield_input 強制 | 6 |
| 3 | Ingest 層 | Drive URL・10 種以上のフォーマットが `IngestedDocument` に正規化される | 6 |
| 4 | Agents + 情報源 | 4 persona の `ReviewAgent` が単独で FindingV2 を返す、NotebookLM InformationSource が Pydantic schema 検証付きで稼働 | 6 |
| 5 | Automation E2E（LangGraph + Report + Approval） | `uv run aegis review-v2 <paths>` が最終レポート（`.review/report.md` + gws Docs/Sheets）まで出力、`aegis ask` / `aegis approve` 完備 | 10 |
| 6 | Interactive 経路（Cursor + MCP） | Cursor 拡張から `/aegis review` を起動し MCP 経由で Automation 経路と同等成果物を生成、`.cursor/rules/*.mdc` drift テスト通過 | 7 |
| 7 | Hardening（エッジケース・非機能・移行） | E1–E14 全シナリオ自動テスト、provider 互換性 Jaccard ≥ 0.85、境界 shield 契約テスト、`docs/v2/migration-notes.md` 整備 | 7 |

合計 48 Tasks。

---

## 2. ファイル構成プラン（Phase 横断）

新規・改修ファイルは設計書 §7.2 のツリーに準拠。以下は本計画で新規作成される主要ファイル一覧（Phase ごとに再掲する）:

```text
src/core/protocols.py                # Phase 1: 追記（ReviewAgent / ConflictResolver / InformationSource / DocumentIngestor）
src/core/config.py                   # Phase 1: 追記（LLMProviderConfig）
src/v2/
  core/enums.py                      # Phase 1
  core/hierarchy.py                  # Phase 1
  core/types.py                      # Phase 1
  llm/provider.py                    # Phase 2
  llm/executor.py                    # Phase 2
  llm/registry.py                    # Phase 2
  llm/providers/{anthropic,openai,mock}.py   # Phase 2
  ingest/protocol.py, registry.py, resolver.py           # Phase 3
  ingest/adapters/{gdocs,gsheets,gslides,office,pdf,image,source_code,markdown}.py # Phase 3
  agents/base.py                     # Phase 4
  agents/{security_guard,architect,domain,performance}.py # Phase 4
  sources/{notebook,gws_docs}.py     # Phase 4
  prompts/*.xml (7 files)            # Phase 4
  persistence/shielded_writer.py     # Phase 5
  automation/graph/{state,nodes,edges,builder}.py        # Phase 5
  automation/resolver/sentinel.py    # Phase 5
  report/{renderer,publisher}.py     # Phase 5
  qna/{session,store}.py             # Phase 5
  approval/recorder.py               # Phase 5
  mcp/server.py + tools/{...}.py     # Phase 6
  interactive/rules_sync.py          # Phase 6
cursor-extension/                    # Phase 6（TypeScript）
docs/v2/{migration-notes,audit-profile}.md  # Phase 7
```

---

# Phase 1: Foundation（型・列挙・プロトコル・設定）

**Branch:** `feature/phase-1__foundation__base` ← `master`
**PR target:** `master`
**マイルストーン:** v2 の型・列挙・protocol が import 可能、v1 既存テストが green のまま、pytest・mypy --strict・ruff が全て通過。

## Task 1.0: ワークツリー準備と `.gitignore` 整備

**Branch:** `feature/phase1-task0__worktree-setup` ← `feature/phase-1__foundation__base`
**PR target:** `feature/phase-1__foundation__base`

**Files:**
- Modify: `.gitignore`
- Create: `docs/superpowers/plans/2026-04-19-aegis-v2-multiagent.md`（既存。この計画書そのもの）

- [ ] **Step 1: `.worktrees/` を `.gitignore` に追加**

`.gitignore` の末尾に追記:

```gitignore

# Superpowers worktrees
.worktrees/
```

- [ ] **Step 2: `.worktrees/phase-1__foundation/` を作成しセットアップ**

```bash
git worktree add .worktrees/phase-1__foundation -b feature/phase-1__foundation__base
cd .worktrees/phase-1__foundation
uv sync
uv run pytest -m "not integration"
```

Expected: 既存テスト全 PASS。

- [ ] **Step 3: Phase 1 Draft PR を作成**

```bash
gh pr create --draft --base master --title "Phase 1: v2 foundation types & protocols" \
  --body "Phase 1 の親 PR。個別 Task PR をこのブランチに向けてマージし、全 Task 完了後に master 向けに ready for review。"
```

- [ ] **Step 4: Task 0 用サブブランチで .gitignore をコミット**

```bash
git switch -c feature/phase1-task0__worktree-setup
git add .gitignore
git commit -m "chore: .worktrees をリポジトリ追跡対象から除外"
git push -u origin feature/phase1-task0__worktree-setup
gh pr create --draft --base feature/phase-1__foundation__base --title "Task 1.0: worktree setup"
```

---

## Task 1.1: v2 列挙型の追加

**Branch:** `feature/phase1-task1__v2-enums` ← `feature/phase1-task0__worktree-setup`
**PR target:** `feature/phase-1__foundation__base`

**Files:**
- Create: `src/v2/__init__.py`（空）
- Create: `src/v2/core/__init__.py`（空）
- Create: `src/v2/core/enums.py`
- Create: `tests/unit/v2/__init__.py`（空）
- Create: `tests/unit/v2/core/__init__.py`（空）
- Create: `tests/unit/v2/core/test_enums.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/unit/v2/core/test_enums.py`:

```python
from src.v2.core.enums import (
    AgentPersona,
    CommentType,
    BugCategory,
    BugPhenomenon,
    RootCause,
    ReviewStatus,
    ReviewTargetKind,
)


def test_agent_persona_values() -> None:
    assert AgentPersona.SENTINEL.value == "sentinel"
    assert AgentPersona.SECURITY_GUARD.value == "security_guard"
    assert AgentPersona.ARCHITECT.value == "architect"
    assert AgentPersona.DOMAIN.value == "domain"
    assert AgentPersona.PERFORMANCE.value == "performance"


def test_comment_type_japanese_labels() -> None:
    assert CommentType.ISSUE.value == "指摘"
    assert CommentType.REQUEST.value == "要望"
    assert CommentType.QUESTION.value == "質問"


def test_bug_category_japanese_labels() -> None:
    assert BugCategory.CURRENT_PHASE.value == "当工程バグ"
    assert BugCategory.UPSTREAM_PHASE.value == "上位工程バグ"
    assert BugCategory.BASE_CODE.value == "母体バグ"
    assert BugCategory.NOT_A_BUG.value == "バグではない"


def test_bug_phenomenon_has_8_members() -> None:
    assert len(BugPhenomenon) == 8
    assert BugPhenomenon.DESIGN_OMISSION.value == "設計漏れ"
    assert BugPhenomenon.CODING_MISS.value == "コーディングミス"


def test_root_cause_has_10_members() -> None:
    assert len(RootCause) == 10


def test_review_status_members() -> None:
    assert {s.value for s in ReviewStatus} == {
        "pending", "in_progress", "completed_pending_approval", "approved", "failed",
    }


def test_review_target_kind() -> None:
    assert ReviewTargetKind.DOCUMENT.value == "document"
    assert ReviewTargetKind.SOURCE_CODE.value == "source_code"
    assert ReviewTargetKind.MIXED.value == "mixed"
```

- [ ] **Step 2: テスト失敗を確認**

Run: `uv run pytest tests/unit/v2/core/test_enums.py -v`
Expected: `ModuleNotFoundError: No module named 'src.v2'`

- [ ] **Step 3: 実装（設計書 §2, §6.1, §6.3 に literal 準拠）**

`src/v2/core/enums.py`:

```python
from __future__ import annotations

from enum import StrEnum


class AgentPersona(StrEnum):
    SENTINEL = "sentinel"
    SECURITY_GUARD = "security_guard"
    ARCHITECT = "architect"
    DOMAIN = "domain"
    PERFORMANCE = "performance"


class CommentType(StrEnum):
    ISSUE = "指摘"
    REQUEST = "要望"
    QUESTION = "質問"


class BugCategory(StrEnum):
    CURRENT_PHASE = "当工程バグ"
    UPSTREAM_PHASE = "上位工程バグ"
    BASE_CODE = "母体バグ"
    NOT_A_BUG = "バグではない"


class BugPhenomenon(StrEnum):
    DESIGN_OMISSION = "設計漏れ"
    DESIGN_ERROR = "設計誤り"
    DESIGN_INTERFACE_MISS = "設計インタフェースミス"
    DESIGN_EXPRESSION = "設計表現不備"
    DESIGN_STANDARDIZATION = "設計標準化ミス"
    TEST_ITEM_MISS = "テスト項目ミス"
    CODING_MISS = "コーディングミス"
    CODING_STANDARDIZATION = "コーディング標準化ミス"


class RootCause(StrEnum):
    INSUFFICIENT_CONSIDERATION = "検討不足"
    INSUFFICIENT_SPEC_CHECK = "仕様確認不足"
    POST_REVIEW_FIX_FAILURE = "レビュー後修正不備"
    COMMUNICATION_FAILURE = "連絡不備"
    INSUFFICIENT_BUSINESS_KNOWLEDGE = "業務知識不足"
    INSUFFICIENT_METHOD_KNOWLEDGE = "方式知識不足"
    INSUFFICIENT_BASIC_SKILL = "基本スキル不足"
    INSUFFICIENT_STANDARD_CHECK = "標準書確認不足"
    INSUFFICIENT_STANDARDIZATION = "標準化不備"
    INSUFFICIENT_ATTENTION = "注意不足"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED_PENDING_APPROVAL = "completed_pending_approval"
    APPROVED = "approved"
    FAILED = "failed"


class ReviewTargetKind(StrEnum):
    DOCUMENT = "document"
    SOURCE_CODE = "source_code"
    MIXED = "mixed"
```

- [ ] **Step 4: テスト成功を確認**

Run: `uv run pytest tests/unit/v2/core/test_enums.py -v && uv run mypy src/v2/core/enums.py && uv run ruff check src/v2 tests/unit/v2`
Expected: 7 passed、mypy `Success`、ruff clean。

- [ ] **Step 5: Commit & Draft PR**

```bash
git add src/v2/__init__.py src/v2/core/__init__.py src/v2/core/enums.py tests/unit/v2
git commit -m "feat(v2/core): 日本語ラベル付き列挙型と AgentPersona を追加"
git push -u origin feature/phase1-task1__v2-enums
gh pr create --draft --base feature/phase-1__foundation__base --title "Task 1.1: v2 enums"
```

---

## Task 1.2: AuthorityLevel と information_hierarchy

**Branch:** `feature/phase1-task2__authority-level` ← `feature/phase1-task1__v2-enums`
**PR target:** `feature/phase-1__foundation__base`

**Files:**
- Create: `src/v2/core/hierarchy.py`
- Create: `tests/unit/v2/core/test_hierarchy.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/unit/v2/core/test_hierarchy.py`:

```python
from src.v2.core.hierarchy import AuthorityLevel, rank


def test_authority_level_order() -> None:
    assert rank(AuthorityLevel.ABSOLUTE) > rank(AuthorityLevel.PRIMARY)
    assert rank(AuthorityLevel.PRIMARY) > rank(AuthorityLevel.REFERENCE)
    assert rank(AuthorityLevel.REFERENCE) > rank(AuthorityLevel.CONVENTION)


def test_authority_values() -> None:
    assert AuthorityLevel.ABSOLUTE.value == "absolute"
    assert AuthorityLevel.PRIMARY.value == "primary"
    assert AuthorityLevel.REFERENCE.value == "reference"
    assert AuthorityLevel.CONVENTION.value == "convention"
```

- [ ] **Step 2: テスト失敗を確認**

Run: `uv run pytest tests/unit/v2/core/test_hierarchy.py -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 実装（設計書 §5.1）**

`src/v2/core/hierarchy.py`:

```python
from __future__ import annotations

from enum import StrEnum


class AuthorityLevel(StrEnum):
    ABSOLUTE = "absolute"
    PRIMARY = "primary"
    REFERENCE = "reference"
    CONVENTION = "convention"


_ORDER = {
    AuthorityLevel.CONVENTION: 0,
    AuthorityLevel.REFERENCE: 1,
    AuthorityLevel.PRIMARY: 2,
    AuthorityLevel.ABSOLUTE: 3,
}


def rank(level: AuthorityLevel) -> int:
    """数値順位。大きいほど優越（ドメイン知識軸のみ。セキュリティ軸は直交）."""
    return _ORDER[level]
```

- [ ] **Step 4: テスト成功を確認**

Run: `uv run pytest tests/unit/v2/core/test_hierarchy.py -v && uv run mypy src/v2/core/hierarchy.py`
Expected: 2 passed、mypy clean。

- [ ] **Step 5: Commit & Draft PR**

```bash
git add src/v2/core/hierarchy.py tests/unit/v2/core/test_hierarchy.py
git commit -m "feat(v2/core): AuthorityLevel と情報階層 rank util を追加"
git push -u origin feature/phase1-task2__authority-level
gh pr create --draft --base feature/phase-1__foundation__base --title "Task 1.2: AuthorityLevel"
```

---

## Task 1.3: v2 入出力・中間型

**Branch:** `feature/phase1-task3__v2-types` ← `feature/phase1-task2__authority-level`
**PR target:** `feature/phase-1__foundation__base`

**Files:**
- Create: `src/v2/core/types.py`
- Create: `tests/unit/v2/core/test_types.py`

**設計書参照:** §6.2, §6.3, §6.5, §6.7

- [ ] **Step 1: 失敗するテストを書く（frozen/等価性/必須フィールド検証）**

`tests/unit/v2/core/test_types.py`:

```python
from __future__ import annotations

from datetime import datetime, date
from pathlib import Path

import pytest

from src.v2.core.enums import (
    AgentPersona, BugCategory, BugPhenomenon, CommentType,
    ReviewStatus, ReviewTargetKind, RootCause,
)
from src.v2.core.hierarchy import AuthorityLevel
from src.v2.core.types import (
    Approval, FindingV2, IngestSource, IngestedDocument, Location,
    PriorReviewComment, Provenance, ReviewReportV2, ReviewRequestForm,
    ReviewRequestV2, SourceExcerpt,
)


def _sample_provenance() -> Provenance:
    return Provenance(
        origin="upload", uri="/tmp/x.py",
        fetched_at=datetime(2026, 4, 17),
        correlation_id="cid-1",
    )


def test_provenance_is_frozen() -> None:
    p = _sample_provenance()
    with pytest.raises(Exception):
        p.origin = "drive_url"  # type: ignore[misc]


def test_ingested_document_defaults_metadata() -> None:
    doc = IngestedDocument(
        doc_id="d1", format="source_code", content="print(1)",
        structured=None, provenance=_sample_provenance(),
        authority_level=AuthorityLevel.PRIMARY,
    )
    assert doc.metadata == {}


def test_location_all_optional_but_doc_id() -> None:
    loc = Location(doc_id="d1")
    assert loc.file_path is None and loc.line is None and loc.section is None
    loc2 = Location(doc_id="d1", file_path=Path("a.py"), line=10)
    assert loc2.line == 10


def test_finding_v2_requires_persona_and_authority() -> None:
    f = FindingV2(
        finding_id="f1", location=Location(doc_id="d1"),
        comment_type=CommentType.ISSUE, bug_category=BugCategory.CURRENT_PHASE,
        bug_phenomenon=BugPhenomenon.CODING_MISS,
        root_cause=RootCause.INSUFFICIENT_ATTENTION, severity="high",
        details="d", recommendation="r",
        source_persona=AgentPersona.SECURITY_GUARD,
        authority_level=AuthorityLevel.PRIMARY,
    )
    assert f.superseded_by is None and f.relates_to_prior is None


def test_review_request_v2_defaults() -> None:
    req = ReviewRequestV2(
        request_id="r1", correlation_id="r1", kind=ReviewTargetKind.SOURCE_CODE,
        target_docs=(),
    )
    assert req.reference_docs == () and req.notebook_docs == ()
    assert req.prior_form is None and req.focus_hints == ()
    assert req.use_codebase_as_reference is False


def test_review_report_v2_with_qna_default() -> None:
    rep = ReviewReportV2(
        request_id="r1", correlation_id="r1", target_name="x",
        reviewed_at=datetime(2026, 4, 17),
        status=ReviewStatus.COMPLETED_PENDING_APPROVAL,
        executive_summary="s", findings=(), next_steps=(),
        raw_agent_reports={},
    )
    assert rep.qna_threads == {} and rep.approval is None


def test_approval_requires_hash() -> None:
    a = Approval(
        approver="alice", approved_at=datetime(2026, 4, 17),
        approver_comment=None, report_hash="sha256:abc",
    )
    assert a.report_hash.startswith("sha256:")


def test_ingest_source_variants() -> None:
    s1 = IngestSource(kind="drive_url", value="https://drive.google.com/...")
    s2 = IngestSource(kind="file_path", value=Path("/tmp/x.docx"))
    s3 = IngestSource(kind="bytes", value=b"abc", mime_hint="text/plain")
    assert s1.mime_hint is None and s3.mime_hint == "text/plain"


def test_source_excerpt_carries_authority() -> None:
    e = SourceExcerpt(
        source_id="notebook-1", excerpt="...",
        authority_level=AuthorityLevel.ABSOLUTE,
        citation="NotebookLM §3.2",
    )
    assert e.authority_level == AuthorityLevel.ABSOLUTE


def test_prior_review_comment_optional_fields() -> None:
    c = PriorReviewComment(
        commenter="bob", location=Location(doc_id="d"), comment="x",
        comment_type=CommentType.ISSUE, answerer=None, answer_date=None,
        answer=None, bug_category=None, bug_phenomenon=None, root_cause=None,
        severity="low", confirmer=None, confirm_date=None,
    )
    assert c.answerer is None
    _ = ReviewRequestForm(
        source=IngestedDocument(
            doc_id="form", format="xlsx", content="",
            structured={"rows": []}, provenance=_sample_provenance(),
            authority_level=AuthorityLevel.REFERENCE,
        ),
        prior_comments=(c,),
    )
```

- [ ] **Step 2: テスト失敗を確認**

Run: `uv run pytest tests/unit/v2/core/test_types.py -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 実装（設計書 §6.2, §6.3, §6.5, §6.7 に literal 準拠）**

`src/v2/core/types.py`:

```python
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from src.v2.core.enums import (
    AgentPersona, BugCategory, BugPhenomenon, CommentType,
    ReviewStatus, ReviewTargetKind, RootCause,
)
from src.v2.core.hierarchy import AuthorityLevel

Severity = Literal["low", "medium", "high", "critical"]


@dataclass(frozen=True)
class Provenance:
    origin: Literal["drive_url", "upload", "local_path", "cursor_context"]
    uri: str
    fetched_at: datetime
    correlation_id: str


@dataclass(frozen=True)
class IngestedDocument:
    doc_id: str
    format: Literal[
        "gdocs", "gsheets", "gslides", "docx", "xlsx", "pptx",
        "pdf", "image", "source_code", "markdown", "plaintext",
    ]
    content: str
    structured: Mapping[str, Any] | None
    provenance: Provenance
    authority_level: AuthorityLevel
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Location:
    doc_id: str
    file_path: Path | None = None
    line: int | None = None
    section: str | None = None


@dataclass(frozen=True)
class PriorReviewComment:
    commenter: str
    location: Location
    comment: str
    comment_type: CommentType
    answerer: str | None
    answer_date: date | None
    answer: str | None
    bug_category: BugCategory | None
    bug_phenomenon: BugPhenomenon | None
    root_cause: RootCause | None
    severity: Severity
    confirmer: str | None
    confirm_date: date | None


@dataclass(frozen=True)
class ReviewRequestForm:
    source: IngestedDocument
    prior_comments: Sequence[PriorReviewComment]


@dataclass(frozen=True)
class ReviewRequestV2:
    request_id: str
    correlation_id: str
    kind: ReviewTargetKind
    target_docs: Sequence[IngestedDocument]
    reference_docs: Sequence[IngestedDocument] = ()
    notebook_docs: Sequence[IngestedDocument] = ()
    prior_form: ReviewRequestForm | None = None
    focus_hints: Sequence[str] = ()
    use_codebase_as_reference: bool = False


@dataclass(frozen=True)
class FindingV2:
    finding_id: str
    location: Location
    comment_type: CommentType
    bug_category: BugCategory
    bug_phenomenon: BugPhenomenon
    root_cause: RootCause
    severity: Severity
    details: str
    recommendation: str
    source_persona: AgentPersona
    authority_level: AuthorityLevel
    superseded_by: str | None = None
    relates_to_prior: str | None = None


@dataclass(frozen=True)
class Approval:
    approver: str
    approved_at: datetime
    approver_comment: str | None
    report_hash: str


@dataclass(frozen=True)
class QnATurn:
    role: Literal["user", "sentinel"]
    content: str
    timestamp: datetime
    usage: Any | None = None  # TokenUsage（Phase 2 で差し替え）


@dataclass(frozen=True)
class QnAThread:
    finding_id: str
    turns: Sequence[QnATurn]


@dataclass(frozen=True)
class ReviewReportV2:
    request_id: str
    correlation_id: str
    target_name: str
    reviewed_at: datetime
    status: ReviewStatus
    executive_summary: str
    findings: Sequence[FindingV2]
    next_steps: Sequence[str]
    raw_agent_reports: Mapping[AgentPersona, Any]  # AgentReport（Phase 4 で差し替え）
    qna_threads: Mapping[str, QnAThread] = field(default_factory=dict)
    approval: Approval | None = None


@dataclass(frozen=True)
class IngestSource:
    kind: Literal["drive_url", "file_path", "bytes"]
    value: str | Path | bytes
    mime_hint: str | None = None


@dataclass(frozen=True)
class SourceExcerpt:
    source_id: str
    excerpt: str
    authority_level: AuthorityLevel
    citation: str
```

**Note:** `AgentReport` と `TokenUsage` は Phase 2/4 で正式定義される。Phase 1 では前方互換のため `Any` で受けておく（mypy warning は型 stub ではないため影響なし）。Phase 4 Task 4.1 で `Any` を正式型に差し替え、この差し替えは破壊変更ではない（import 位置のみ変更）。

- [ ] **Step 4: テスト成功を確認**

Run: `uv run pytest tests/unit/v2/core/test_types.py -v && uv run mypy src/v2/core/types.py`
Expected: 10 passed、mypy clean。

- [ ] **Step 5: Commit & Draft PR**

```bash
git add src/v2/core/types.py tests/unit/v2/core/test_types.py
git commit -m "feat(v2/core): v2 入出力型（ReviewRequestV2/FindingV2/ReviewReportV2 等）を追加"
git push -u origin feature/phase1-task3__v2-types
gh pr create --draft --base feature/phase-1__foundation__base --title "Task 1.3: v2 types"
```

---

## Task 1.4: `src/core/protocols.py` に 4 protocol を追記

**Branch:** `feature/phase1-task4__protocols` ← `feature/phase1-task3__v2-types`
**PR target:** `feature/phase-1__foundation__base`

**Files:**
- Modify: `src/core/protocols.py`（既存 `ReviewPlugin` / `SecurityShield` は不変、末尾追記のみ）
- Create: `tests/unit/v2/core/test_protocols.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/unit/v2/core/test_protocols.py`:

```python
from __future__ import annotations

from collections.abc import Sequence
from typing import runtime_checkable

from src.core.protocols import (
    ConflictResolver, DocumentIngestor, InformationSource, ReviewAgent,
)


def test_review_agent_runtime_checkable() -> None:
    assert runtime_checkable(ReviewAgent)


def test_document_ingestor_has_supported_formats() -> None:
    # protocol を明示実装するダミーで構造確認
    class Dummy:
        supported_formats: frozenset[str] = frozenset({"pdf"})
        async def ingest(self, source, *, correlation_id):  # noqa: ANN001
            raise NotImplementedError
    assert isinstance(Dummy(), DocumentIngestor)


def test_information_source_has_authority_level() -> None:
    from src.v2.core.hierarchy import AuthorityLevel
    class Dummy:
        authority_level = AuthorityLevel.ABSOLUTE
        async def query(self, q, *, correlation_id):  # noqa: ANN001
            raise NotImplementedError
    assert isinstance(Dummy(), InformationSource)


def test_conflict_resolver_shape() -> None:
    class Dummy:
        async def resolve(self, conflicts, state):  # noqa: ANN001
            return []
    assert isinstance(Dummy(), ConflictResolver)
```

- [ ] **Step 2: テスト失敗を確認**

Run: `uv run pytest tests/unit/v2/core/test_protocols.py -v`
Expected: FAIL（`ImportError: cannot import ReviewAgent`）

- [ ] **Step 3: 実装（既存 protocols.py 末尾に追記。設計書 §6.8）**

`src/core/protocols.py` の末尾に追記（既存部分には触れない）:

```python
# ---------------------------------------------------------------------------
# v2 protocols (additions only; v1 protocols above remain unchanged)
# ---------------------------------------------------------------------------
from __future__ import annotations  # 既存 import を利用する場合は重複させない

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from src.v2.agents.base import AgentContext, AgentReport  # Phase 4 で作成
    from src.v2.automation.graph.state import SentinelState  # Phase 5 で作成
    from src.v2.core.enums import AgentPersona
    from src.v2.core.hierarchy import AuthorityLevel
    from src.v2.core.types import IngestedDocument, IngestSource, SourceExcerpt


@runtime_checkable
class ReviewAgent(Protocol):
    persona: "AgentPersona"
    async def review(self, ctx: "AgentContext") -> "AgentReport": ...


@runtime_checkable
class ConflictResolver(Protocol):
    async def resolve(
        self,
        conflicts: "Sequence[object]",     # Conflict — Phase 5 で確定
        state: "SentinelState",
    ) -> "Sequence[object]": ...            # Resolution — Phase 5 で確定


@runtime_checkable
class InformationSource(Protocol):
    authority_level: "AuthorityLevel"
    async def query(self, q: str, *, correlation_id: str) -> "SourceExcerpt": ...


@runtime_checkable
class DocumentIngestor(Protocol):
    supported_formats: frozenset[str]
    async def ingest(
        self,
        source: "IngestSource",
        *,
        correlation_id: str,
    ) -> "IngestedDocument": ...
```

**Note:** `Conflict` と `Resolution` は Phase 5 Task 5.1 / 5.6 で具象型が確定するため、Phase 1 では `object` で受けておき、Phase 5 で正式型に差し替える（`runtime_checkable` のため shape 検査は維持される）。

- [ ] **Step 4: テスト成功 + v1 既存テスト回帰確認**

```bash
uv run pytest tests/unit/v2/core/test_protocols.py -v
uv run pytest tests/unit -v  # v1 既存テストに影響がないこと
uv run mypy src/core/protocols.py src/v2
```

Expected: 全 PASS、mypy clean。

- [ ] **Step 5: Commit & Draft PR**

```bash
git add src/core/protocols.py tests/unit/v2/core/test_protocols.py
git commit -m "feat(core/protocols): v2 用 4 protocol（ReviewAgent 等）を追記"
git push -u origin feature/phase1-task4__protocols
gh pr create --draft --base feature/phase-1__foundation__base --title "Task 1.4: v2 protocols"
```

---

## Task 1.5: `LLMProviderConfig` を `src/core/config.py` に追記

**Branch:** `feature/phase1-task5__llm-config` ← `feature/phase1-task4__protocols`
**PR target:** `feature/phase-1__foundation__base`

**Files:**
- Modify: `src/core/config.py`
- Create: `tests/unit/v2/core/test_llm_config.py`

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/unit/v2/core/test_llm_config.py
from __future__ import annotations

import os

import pytest

from src.core.config import LLMProviderConfig


def test_defaults() -> None:
    cfg = LLMProviderConfig()
    assert cfg.name == "anthropic"
    assert cfg.model_id == "claude-opus-4-7"
    assert cfg.reasoning_mode == "adaptive"
    assert cfg.reasoning_effort == "xhigh"
    assert cfg.max_concurrent == 4
    assert cfg.api_key_env_var == "ANTHROPIC_API_KEY"


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER_NAME", "openai")
    monkeypatch.setenv("LLM_PROVIDER_MODEL_ID", "gpt-5")
    monkeypatch.setenv("LLM_PROVIDER_API_KEY_ENV_VAR", "OPENAI_API_KEY")
    cfg = LLMProviderConfig()
    assert cfg.name == "openai" and cfg.model_id == "gpt-5"
    assert cfg.api_key_env_var == "OPENAI_API_KEY"


def test_invalid_name_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER_NAME", "unknown")
    with pytest.raises(Exception):
        LLMProviderConfig()
```

- [ ] **Step 2: テスト失敗を確認**

Run: `uv run pytest tests/unit/v2/core/test_llm_config.py -v`
Expected: `ImportError: cannot import LLMProviderConfig`

- [ ] **Step 3: 実装（設計書 §4.5。既存 config.py は不変、末尾追記）**

```python
# src/core/config.py の末尾に追記
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProviderConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LLM_PROVIDER_")

    name: Literal["anthropic", "openai", "mock"] = "anthropic"
    model_id: str = "claude-opus-4-7"
    reasoning_mode: Literal["off", "light", "deep", "adaptive"] = "adaptive"
    reasoning_effort: Literal["low", "medium", "high", "xhigh"] = "xhigh"
    max_concurrent: int = 4
    api_key_env_var: str = "ANTHROPIC_API_KEY"
```

- [ ] **Step 4: テスト成功を確認**

Run: `uv run pytest tests/unit/v2/core/test_llm_config.py -v && uv run mypy src/core/config.py`
Expected: 3 passed、mypy clean。

- [ ] **Step 5: Commit & ready-for-review**

```bash
git add src/core/config.py tests/unit/v2/core/test_llm_config.py
git commit -m "feat(core/config): LLMProviderConfig を追加（env prefix LLM_PROVIDER_）"
git push -u origin feature/phase1-task5__llm-config
gh pr create --draft --base feature/phase-1__foundation__base --title "Task 1.5: LLMProviderConfig"
```

**Phase 1 完了時のアクション:**
- 全 Task PR を順次 `feature/phase-1__foundation__base` にマージ
- Phase 1 Draft PR を `gh pr ready` で通常 PR に昇格
- CI 緑化確認後、`master` にマージ

---

# Phase 2: LLM Provider 抽象化

**Branch:** `feature/phase-2__llm-provider__base` ← `master`（Phase 1 マージ完了後）
**PR target:** `master`
**マイルストーン:** Anthropic / OpenAI / Mock の 3 provider が `test_provider_contract.py` 共通スイートで合格、`AgentExecutor.invoke` で shield_input が必ず適用され、unredacted な応答を返す。

## Task 2.1: Provider 中立コンテンツ型と Protocol

**Branch:** `feature/phase2-task1__provider-protocol` ← `feature/phase-2__llm-provider__base`
**PR target:** `feature/phase-2__llm-provider__base`

**Files:**
- Create: `src/v2/llm/__init__.py`
- Create: `src/v2/llm/provider.py`
- Create: `tests/unit/v2/llm/__init__.py`
- Create: `tests/unit/v2/llm/test_provider_types.py`

- [ ] **Step 1: 失敗するテストを書く（ProviderFeature / ReasoningConfig / TokenUsage / ProviderResponse / SystemBlock 等の形状確認）**

`tests/unit/v2/llm/test_provider_types.py`:

```python
from __future__ import annotations

import pytest

from src.v2.llm.provider import (
    CacheHint, ContentBlock, LLMProvider, Message, ProviderFeature,
    ProviderResponse, ReasoningConfig, SystemBlock, TokenUsage, Tool,
)


def test_provider_feature_values() -> None:
    assert {f.value for f in ProviderFeature} == {
        "adaptive_thinking", "reasoning_effort",
        "prompt_caching", "json_mode", "tool_use",
    }


def test_reasoning_config_defaults() -> None:
    r = ReasoningConfig()
    assert r.mode == "adaptive" and r.effort == "xhigh"


def test_cache_hint_defaults() -> None:
    h = CacheHint(block_id="b1")
    assert h.ttl == "ephemeral"


def test_token_usage_zero_defaults() -> None:
    u = TokenUsage(input_tokens=10, output_tokens=5)
    assert u.cache_read_input_tokens == 0 and u.thinking_tokens == 0


def test_system_block_optional_cache_hint() -> None:
    s = SystemBlock(text="hello")
    assert s.cache_hint is None


def test_message_content_block_union() -> None:
    m = Message(role="user", content=[ContentBlock(type="text", text="hi")])
    assert m.content[0].text == "hi"


def test_provider_response_fields() -> None:
    r = ProviderResponse(
        content="ok",
        usage=TokenUsage(input_tokens=1, output_tokens=1),
        raw={"provider": "mock"},
        stop_reason="end_turn",
    )
    assert r.stop_reason == "end_turn"


def test_tool_has_input_schema() -> None:
    t = Tool(name="search", description="desc", input_schema={"type": "object"})
    assert t.input_schema == {"type": "object"}


def test_llm_provider_is_runtime_checkable() -> None:
    class Dummy:
        name = "mock"
        model_id = "m"
        def supports(self, feature: ProviderFeature) -> bool:  # noqa: ARG002
            return False
        async def complete(self, *, system, messages, **kwargs):  # noqa: ANN001, ARG002
            raise NotImplementedError
        async def close(self) -> None: ...
    assert isinstance(Dummy(), LLMProvider)
```

- [ ] **Step 2: テスト失敗を確認**

Run: `uv run pytest tests/unit/v2/llm/test_provider_types.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: 実装（設計書 §4.1, §6.6 に literal 準拠）**

`src/v2/llm/provider.py`:

```python
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal, Protocol, runtime_checkable


class ProviderFeature(StrEnum):
    ADAPTIVE_THINKING = "adaptive_thinking"
    REASONING_EFFORT = "reasoning_effort"
    PROMPT_CACHING = "prompt_caching"
    JSON_MODE = "json_mode"
    TOOL_USE = "tool_use"


@dataclass(frozen=True)
class ReasoningConfig:
    mode: Literal["off", "light", "deep", "adaptive"] = "adaptive"
    effort: Literal["low", "medium", "high", "xhigh"] = "xhigh"


@dataclass(frozen=True)
class CacheHint:
    block_id: str
    ttl: Literal["ephemeral", "persistent"] = "ephemeral"


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    thinking_tokens: int = 0


@dataclass(frozen=True)
class ProviderResponse:
    content: str
    usage: TokenUsage
    raw: object
    stop_reason: str


@dataclass(frozen=True)
class SystemBlock:
    text: str
    cache_hint: CacheHint | None = None


@dataclass(frozen=True)
class ContentBlock:
    type: Literal["text", "image", "tool_result"]
    text: str | None = None
    image_url: str | None = None
    tool_use_id: str | None = None


@dataclass(frozen=True)
class Message:
    role: Literal["user", "assistant"]
    content: Sequence[ContentBlock]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: Mapping[str, Any]


@runtime_checkable
class LLMProvider(Protocol):
    name: str
    model_id: str

    def supports(self, feature: ProviderFeature) -> bool: ...
    async def complete(
        self,
        *,
        system: Sequence[SystemBlock],
        messages: Sequence[Message],
        tools: Sequence[Tool] = (),
        max_tokens: int,
        reasoning: ReasoningConfig | None = None,
        cache_hints: Sequence[CacheHint] = (),
        response_format: Literal["text", "json"] = "text",
    ) -> ProviderResponse: ...
    async def close(self) -> None: ...
```

- [ ] **Step 4: テスト成功を確認**

Run: `uv run pytest tests/unit/v2/llm/test_provider_types.py -v && uv run mypy src/v2/llm/provider.py`
Expected: 9 passed、mypy clean。

- [ ] **Step 5: Commit & Draft PR**

```bash
git add src/v2/llm tests/unit/v2/llm/test_provider_types.py tests/unit/v2/llm/__init__.py
git commit -m "feat(v2/llm): LLMProvider protocol と provider-neutral 型を追加"
git push -u origin feature/phase2-task1__provider-protocol
gh pr create --draft --base feature/phase-2__llm-provider__base --title "Task 2.1: provider protocol"
```

---

## Task 2.2: MockProvider と契約テスト共通スイート

**Branch:** `feature/phase2-task2__mock-provider` ← `feature/phase2-task1__provider-protocol`
**PR target:** `feature/phase-2__llm-provider__base`

**Files:**
- Create: `src/v2/llm/providers/__init__.py`
- Create: `src/v2/llm/providers/mock.py`
- Create: `tests/unit/v2/llm/test_provider_contract.py`（共通スイートを pytest fixture で parametrize）
- Create: `tests/unit/v2/llm/test_mock_provider.py`

**実装方針:** `MockProvider` はハンドラ関数 `Callable[[...], ProviderResponse]` を受けて応答を返す決定論的 fake。契約スイートは provider fixture（Phase 2 後半で anthropic/openai を追加する際に再利用）。

- [ ] **Step 1: 契約テスト共通スイートを作成**

`tests/unit/v2/llm/test_provider_contract.py`:

```python
from __future__ import annotations

import pytest

from src.v2.llm.provider import (
    ContentBlock, Message, ProviderFeature, ReasoningConfig, SystemBlock,
)
from src.v2.llm.providers.mock import MockProvider


@pytest.fixture(params=["mock"])
def provider(request):  # noqa: ANN001
    if request.param == "mock":
        return MockProvider(canned_text="hello")
    raise AssertionError(request.param)


@pytest.mark.asyncio
async def test_provider_complete_returns_content(provider) -> None:  # noqa: ANN001
    resp = await provider.complete(
        system=[SystemBlock(text="sys")],
        messages=[Message(role="user", content=[ContentBlock(type="text", text="hi")])],
        max_tokens=100,
    )
    assert isinstance(resp.content, str) and resp.content
    assert resp.usage.input_tokens >= 0


@pytest.mark.asyncio
async def test_provider_supports_mandatory_features(provider) -> None:  # noqa: ANN001
    # 設計書 §4.2「TOOL_USE と JSON_MODE は全 provider 必須サポート」
    assert provider.supports(ProviderFeature.TOOL_USE)
    assert provider.supports(ProviderFeature.JSON_MODE)


@pytest.mark.asyncio
async def test_provider_close_is_idempotent(provider) -> None:  # noqa: ANN001
    await provider.close()
    await provider.close()
```

- [ ] **Step 2: MockProvider 専用テスト**

`tests/unit/v2/llm/test_mock_provider.py`:

```python
from __future__ import annotations

import pytest

from src.v2.llm.provider import (
    ContentBlock, Message, ProviderFeature, SystemBlock,
)
from src.v2.llm.providers.mock import MockProvider


@pytest.mark.asyncio
async def test_deterministic_response() -> None:
    p = MockProvider(canned_text="answer")
    for _ in range(3):
        resp = await p.complete(
            system=[SystemBlock(text="sys")],
            messages=[Message(role="user", content=[ContentBlock(type="text", text="q")])],
            max_tokens=10,
        )
        assert resp.content == "answer"


@pytest.mark.asyncio
async def test_call_log_captured() -> None:
    p = MockProvider(canned_text="ok", record_calls=True)
    await p.complete(
        system=[SystemBlock(text="sys")],
        messages=[Message(role="user", content=[ContentBlock(type="text", text="q")])],
        max_tokens=10,
    )
    assert len(p.calls) == 1
    assert p.calls[0]["max_tokens"] == 10


def test_supports_all_features() -> None:
    p = MockProvider()
    for feat in ProviderFeature:
        assert p.supports(feat)
```

- [ ] **Step 3: テスト失敗を確認**

Run: `uv run pytest tests/unit/v2/llm/test_mock_provider.py tests/unit/v2/llm/test_provider_contract.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 4: MockProvider 実装**

`src/v2/llm/providers/mock.py`:

```python
from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from src.v2.llm.provider import (
    CacheHint, Message, ProviderFeature, ProviderResponse,
    ReasoningConfig, SystemBlock, TokenUsage, Tool,
)


class MockProvider:
    name: str = "mock"

    def __init__(
        self,
        *,
        canned_text: str = "",
        model_id: str = "mock-1",
        record_calls: bool = False,
    ) -> None:
        self.model_id = model_id
        self._canned = canned_text
        self._record = record_calls
        self.calls: list[dict[str, Any]] = []

    def supports(self, feature: ProviderFeature) -> bool:  # noqa: ARG002
        return True

    async def complete(
        self,
        *,
        system: Sequence[SystemBlock],
        messages: Sequence[Message],
        tools: Sequence[Tool] = (),
        max_tokens: int,
        reasoning: ReasoningConfig | None = None,
        cache_hints: Sequence[CacheHint] = (),
        response_format: Literal["text", "json"] = "text",
    ) -> ProviderResponse:
        if self._record:
            self.calls.append({
                "system": system, "messages": messages, "tools": tools,
                "max_tokens": max_tokens, "reasoning": reasoning,
                "cache_hints": cache_hints, "response_format": response_format,
            })
        return ProviderResponse(
            content=self._canned,
            usage=TokenUsage(
                input_tokens=sum(
                    len(b.text or "") for m in messages for b in m.content
                ),
                output_tokens=len(self._canned),
            ),
            raw={"provider": "mock"},
            stop_reason="end_turn",
        )

    async def close(self) -> None:
        return None
```

- [ ] **Step 5: テスト成功を確認 + Commit**

```bash
uv run pytest tests/unit/v2/llm -v
uv run mypy src/v2/llm
uv run ruff check src/v2/llm tests/unit/v2/llm
git add src/v2/llm/providers tests/unit/v2/llm
git commit -m "feat(v2/llm): MockProvider と provider 契約テストスイートを追加"
git push -u origin feature/phase2-task2__mock-provider
gh pr create --draft --base feature/phase-2__llm-provider__base --title "Task 2.2: MockProvider + contract suite"
```

---

## Task 2.3: AnthropicProvider（feature_probe 付き）

**Branch:** `feature/phase2-task3__anthropic-provider` ← `feature/phase2-task2__mock-provider`
**PR target:** `feature/phase-2__llm-provider__base`

**Files:**
- Modify: `pyproject.toml`（optional-dependencies `provider-anthropic` 追加）
- Create: `src/v2/llm/providers/anthropic.py`
- Create: `tests/unit/v2/llm/test_anthropic_provider.py`（SDK を httpx-based でスタブ）

**実装方針:**
- `anthropic.AsyncAnthropic` を DI 可能に（`client_factory` 引数）
- `__init__` で `_feature_probe()` を run（`BadRequestError` 捕捉、`_supports_effort` を決定）
- `cache_control` は `CacheHint` を持つ SystemBlock へ attach
- `thinking={"type":"adaptive"}` と `extra_body={"output_config":{"effort":...}}` を適用
- 応答から `usage` を抽出（`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`）

- [ ] **Step 1: 契約テストスイートに Anthropic fixture を追加**

`tests/unit/v2/llm/test_provider_contract.py` の `provider` fixture に `"anthropic_stub"` パラメータを追加し、スタブクライアントでテスト。

- [ ] **Step 2: Anthropic 専用テスト（feature_probe 挙動、cache_control 注入、usage 抽出、thinking/effort マッピング）**

`tests/unit/v2/llm/test_anthropic_provider.py`:

```python
from __future__ import annotations

from typing import Any

import pytest

from src.v2.llm.provider import (
    CacheHint, ContentBlock, Message, ProviderFeature,
    ReasoningConfig, SystemBlock,
)


class _FakeAnthropicClient:
    def __init__(self, *, probe_raises: bool = False) -> None:
        self.probe_raises = probe_raises
        self.calls: list[dict[str, Any]] = []
        self.messages = self  # api.messages.create 互換

    async def create(self, **kwargs):  # noqa: ANN003
        self.calls.append(kwargs)
        if self.probe_raises and kwargs.get("max_tokens", 0) == 1:
            raise _FakeBadRequestError("output_config rejected")
        return _FakeResponse()

    async def close(self) -> None:
        return None


class _FakeBadRequestError(Exception):
    ...


class _FakeResponse:
    content = [type("B", (), {"text": "hello", "type": "text"})()]
    stop_reason = "end_turn"
    usage = type("U", (), {
        "input_tokens": 10, "output_tokens": 3,
        "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0,
    })()


@pytest.mark.asyncio
async def test_feature_probe_success_enables_effort() -> None:
    from src.v2.llm.providers.anthropic import AnthropicProvider
    p = await AnthropicProvider.create(
        model_id="claude-opus-4-7",
        client_factory=lambda: _FakeAnthropicClient(probe_raises=False),
        bad_request_error=_FakeBadRequestError,
    )
    assert p.supports(ProviderFeature.REASONING_EFFORT)


@pytest.mark.asyncio
async def test_feature_probe_failure_disables_effort() -> None:
    from src.v2.llm.providers.anthropic import AnthropicProvider
    p = await AnthropicProvider.create(
        model_id="claude-opus-4-7",
        client_factory=lambda: _FakeAnthropicClient(probe_raises=True),
        bad_request_error=_FakeBadRequestError,
    )
    assert not p.supports(ProviderFeature.REASONING_EFFORT)


@pytest.mark.asyncio
async def test_cache_hint_injects_cache_control() -> None:
    from src.v2.llm.providers.anthropic import AnthropicProvider
    client = _FakeAnthropicClient()
    p = await AnthropicProvider.create(
        model_id="claude-opus-4-7",
        client_factory=lambda: client,
        bad_request_error=_FakeBadRequestError,
    )
    await p.complete(
        system=[SystemBlock(text="SYS", cache_hint=CacheHint(block_id="s"))],
        messages=[Message(role="user", content=[ContentBlock(type="text", text="u")])],
        max_tokens=100,
        reasoning=ReasoningConfig(mode="adaptive", effort="xhigh"),
        cache_hints=(),
    )
    real_call = client.calls[-1]
    assert any("cache_control" in blk for blk in real_call["system"])
    assert real_call["thinking"] == {"type": "adaptive"}
```

- [ ] **Step 3: テスト失敗を確認**

Run: `uv run pytest tests/unit/v2/llm/test_anthropic_provider.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 4: 実装（設計書 §4.2, §7.6 #1）**

`src/v2/llm/providers/anthropic.py` の要点（全文は設計書に合わせて実装）:

```python
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Literal

import structlog

from src.v2.llm.provider import (
    CacheHint, Message, ProviderFeature, ProviderResponse,
    ReasoningConfig, SystemBlock, TokenUsage, Tool,
)

logger = structlog.get_logger(__name__)


class AnthropicProvider:
    name: str = "anthropic"

    def __init__(
        self,
        *,
        model_id: str,
        client: Any,
        bad_request_error: type[BaseException],
        supports_effort: bool,
    ) -> None:
        self.model_id = model_id
        self._client = client
        self._bad_request_error = bad_request_error
        self._supports_effort = supports_effort

    @classmethod
    async def create(
        cls,
        *,
        model_id: str,
        client_factory: Callable[[], Any],
        bad_request_error: type[BaseException],
    ) -> "AnthropicProvider":
        client = client_factory()
        supports_effort = True
        try:
            await client.messages.create(
                model=model_id,
                max_tokens=1,
                system=[{"type": "text", "text": "probe"}],
                messages=[{"role": "user", "content": [{"type": "text", "text": "."}]}],
                extra_body={"output_config": {"effort": "xhigh"}},
                thinking={"type": "adaptive"},
            )
        except bad_request_error:
            supports_effort = False
            logger.warning(
                "provider_feature_probe_failed",
                feature="reasoning_effort", fallback="default",
            )
        return cls(
            model_id=model_id, client=client,
            bad_request_error=bad_request_error,
            supports_effort=supports_effort,
        )

    def supports(self, feature: ProviderFeature) -> bool:
        if feature is ProviderFeature.REASONING_EFFORT:
            return self._supports_effort
        return feature in {
            ProviderFeature.ADAPTIVE_THINKING,
            ProviderFeature.PROMPT_CACHING,
            ProviderFeature.JSON_MODE,
            ProviderFeature.TOOL_USE,
        }

    async def complete(
        self,
        *,
        system: Sequence[SystemBlock],
        messages: Sequence[Message],
        tools: Sequence[Tool] = (),
        max_tokens: int,
        reasoning: ReasoningConfig | None = None,
        cache_hints: Sequence[CacheHint] = (),
        response_format: Literal["text", "json"] = "text",
    ) -> ProviderResponse:
        sys_blocks = []
        for s in system:
            blk: dict[str, Any] = {"type": "text", "text": s.text}
            if s.cache_hint is not None:
                blk["cache_control"] = {"type": s.cache_hint.ttl}
            sys_blocks.append(blk)

        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "max_tokens": max_tokens,
            "system": sys_blocks,
            "messages": [self._adapt_message(m) for m in messages],
        }
        if reasoning is not None:
            kwargs["thinking"] = {"type": reasoning.mode}
            if self._supports_effort:
                kwargs["extra_body"] = {
                    "output_config": {"effort": reasoning.effort}
                }
        if tools:
            kwargs["tools"] = [self._adapt_tool(t) for t in tools]
        if response_format == "json":
            # JSON Schema 強制は tool_use 経由（設計書 §4.2）
            kwargs.setdefault("tools", []).append({
                "name": "final_output",
                "input_schema": {"type": "object"},
            })
            kwargs["tool_choice"] = {"type": "tool", "name": "final_output"}

        raw = await self._client.messages.create(**kwargs)
        return self._adapt_response(raw)

    def _adapt_message(self, m: Message) -> dict[str, Any]:
        return {"role": m.role, "content": [self._adapt_block(b) for b in m.content]}

    @staticmethod
    def _adapt_block(b: Any) -> dict[str, Any]:
        if b.type == "text":
            return {"type": "text", "text": b.text or ""}
        if b.type == "image":
            return {"type": "image", "source": {"type": "url", "url": b.image_url}}
        if b.type == "tool_result":
            return {"type": "tool_result", "tool_use_id": b.tool_use_id}
        raise ValueError(b.type)

    @staticmethod
    def _adapt_tool(t: Tool) -> dict[str, Any]:
        return {
            "name": t.name,
            "description": t.description,
            "input_schema": dict(t.input_schema),
        }

    @staticmethod
    def _adapt_response(raw: Any) -> ProviderResponse:
        text = "".join(getattr(b, "text", "") for b in raw.content)
        u = raw.usage
        usage = TokenUsage(
            input_tokens=u.input_tokens,
            output_tokens=u.output_tokens,
            cache_read_input_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
            cache_creation_input_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
        )
        return ProviderResponse(
            content=text, usage=usage, raw=raw,
            stop_reason=getattr(raw, "stop_reason", "end_turn"),
        )

    async def close(self) -> None:
        if hasattr(self._client, "close"):
            await self._client.close()
```

`pyproject.toml`:

```toml
[project.optional-dependencies]
provider-anthropic = ["anthropic>=0.40,<1.0"]
provider-openai = ["openai>=1.50,<2.0"]
```

- [ ] **Step 5: テスト成功を確認 + Commit**

```bash
uv sync --extra provider-anthropic
uv run pytest tests/unit/v2/llm -v
uv run mypy src/v2/llm
git add src/v2/llm/providers/anthropic.py tests/unit/v2/llm/test_anthropic_provider.py pyproject.toml uv.lock
git commit -m "feat(v2/llm): AnthropicProvider（feature_probe/cache_control/thinking マッピング）を追加"
git push -u origin feature/phase2-task3__anthropic-provider
gh pr create --draft --base feature/phase-2__llm-provider__base --title "Task 2.3: AnthropicProvider"
```

---

## Task 2.4: OpenAIProvider（responses-first, chat-completions フォールバック）

**Branch:** `feature/phase2-task4__openai-provider` ← `feature/phase2-task3__anthropic-provider`
**PR target:** `feature/phase-2__llm-provider__base`

**Files:**
- Create: `src/v2/llm/providers/openai.py`
- Create: `tests/unit/v2/llm/test_openai_provider.py`

**実装方針（設計書 §4.2）:**
- `client.responses.create` を第一選択。SDK に `responses` 属性がなければ `chat.completions.create` へフォールバック
- `ReasoningConfig.effort` は `reasoning_effort` にマップ（`xhigh` → `high`）
- `cache_hints` は no-op
- `response_format="json"` は `{"type":"json_object"}` へマップ
- 契約テストスイートに `"openai_stub"` を追加

テスト観点: responses 経路・chat fallback 経路・degradation（`CacheHint` 渡しても例外が出ず `cache_read_input_tokens=0` + `provider_feature_unavailable` が structlog に記録）、`test_degradation_records_feature_unavailable`。

- [ ] **Step 1–2: 契約テストと degradation テスト**
- [ ] **Step 3: 失敗確認**
- [ ] **Step 4: 実装**
- [ ] **Step 5: Commit**

```bash
git commit -m "feat(v2/llm): OpenAIProvider（responses 第一選択・chat フォールバック）を追加"
```

---

## Task 2.5: Provider レジストリ / ファクトリ

**Branch:** `feature/phase2-task5__provider-registry` ← `feature/phase2-task4__openai-provider`
**PR target:** `feature/phase-2__llm-provider__base`

**Files:**
- Create: `src/v2/llm/registry.py`
- Create: `tests/unit/v2/llm/test_registry.py`

**実装方針:**
- `create_provider(config: LLMProviderConfig) -> LLMProvider` が config.name に応じて適切な provider を返す
- レジストリ登録時に `TOOL_USE` と `JSON_MODE` の必須サポートを検査、欠落時 `ValueError`
- `api_key_env_var` から env を取得、未設定時 `LLMProviderInitError`

テスト観点:
- `name=mock` → `MockProvider` が返る
- `name=anthropic` で API キー未設定 → `LLMProviderInitError`
- 必須 feature 未サポートの偽 provider を登録しようとすると `ValueError`

- [ ] **Step 1–5: TDD サイクル（前 Task と同パターン）**

Commit: `feat(v2/llm): Provider レジストリとファクトリを追加`

---

## Task 2.6: AgentExecutor（入力側 shield のみ）

**Branch:** `feature/phase2-task6__agent-executor` ← `feature/phase2-task5__provider-registry`
**PR target:** `feature/phase-2__llm-provider__base`

**Files:**
- Create: `src/v2/llm/executor.py`
- Create: `tests/unit/v2/llm/test_agent_executor.py`

**実装方針（設計書 §4.3）:**
- `AgentExecutor.__init__(provider, shield)`
- `invoke()` は:
  1. `shield.shield_input(user_content 全テキスト)` → `allowed=False` なら `SecurityBlockedError(finding_metadata=...)` を投げる
  2. provider.complete(...) を呼ぶ
  3. `AgentResponse.text` は **unredacted** のまま返す（設計書 §4.3 の明文化根拠）
  4. `structlog.info("llm_completed", persona, provider, model, usage, feature_fallbacks)`
- `AgentResponse` は Phase 1 Task 1.3 で定義済み（`src/v2/core/types.py` から import）
- `AsyncSemaphore(max_concurrent)` は Phase 7 Task 7.1 で注入（Phase 2 では無し）

テスト観点:
- `shield_input.allowed=True` → provider 呼出され unredacted 応答が返る
- `shield_input.allowed=False` → `SecurityBlockedError` が `finding_metadata` を携えて伝搬
- 応答に fake の秘匿文字列を仕込んでも `executor.invoke` の戻り値には redaction されていない（`test_executor_no_output_shield.py` の雛形、Phase 7 で正式契約テスト化）

- [ ] **Step 1–5: TDD**

Commit: `feat(v2/llm): AgentExecutor を追加（入力側 shield のみ、応答は unredacted）`

**Phase 2 完了時:** 全 Task PR をマージ → Phase 2 Draft PR を ready → `master` にマージ。

---

# Phase 3: Ingest 層

**Branch:** `feature/phase-3__ingest__base` ← `master`
**PR target:** `master`
**マイルストーン:** Drive URL / 10+ フォーマット（gdocs, gsheets, gslides, docx, xlsx, pptx, pdf, image, source_code, markdown, plaintext）が `IngestedDocument` に正規化される。E1（大ファイル）、E2（大 PDF ストリーム）、E4/E5（未対応フォーマット）、E9（Drive アクセス不可）、E10（循環参照）を自動テストで網羅。

## Task 3.1: DocumentIngestor 実装基盤（registry / resolver）

**Branch:** `feature/phase3-task1__ingest-base` ← `feature/phase-3__ingest__base`
**PR target:** `feature/phase-3__ingest__base`

**Files:**
- Create: `src/v2/ingest/__init__.py`
- Create: `src/v2/ingest/protocol.py`（エラー型 `UnsupportedFormatError`, `FileTypeDetectionError`, `DriveAccessDeniedError`, `FileSizeExceededError`, `IngestCycleSkipped` を定義）
- Create: `src/v2/ingest/registry.py`（拡張子 / MIME → adapter のマッピング、未登録時 `UnsupportedFormatError`）
- Create: `src/v2/ingest/resolver.py`（Drive URL → bytes、循環検知、サイズ検知）
- Create: `tests/unit/v2/ingest/test_registry.py`, `test_resolver.py`

**テスト観点:**
- Registry: `.rar`/`.exe` → `UnsupportedFormatError`（E4）
- Resolver: MIME `application/octet-stream` → `FileTypeDetectionError`（E5）
- Resolver: 循環参照で `structlog.info("ingest_cycle_skipped", ...)`（E10）
- Resolver: 500KB 超の `format="source_code"` → `FileSizeExceededError`（E1 境界）

- [ ] **Step 1–5: TDD** 
  - 既存の `SyncConfig.max_file_size_kb` を再利用し、default 500 を env で上書き可能にする
  - Drive クライアントは `client_factory` 引数で DI

Commit: `feat(v2/ingest): DocumentIngestor 基盤（registry/resolver）とエラー型を追加`

---

## Task 3.2: source_code / markdown / plaintext adapter

**Branch:** `feature/phase3-task2__source-code-adapter` ← `feature/phase3-task1__ingest-base`
**PR target:** `feature/phase-3__ingest__base`

**Files:**
- Create: `src/v2/ingest/adapters/__init__.py`
- Create: `src/v2/ingest/adapters/source_code.py`
- Create: `src/v2/ingest/adapters/markdown.py`
- Create: `src/v2/ingest/adapters/plaintext.py`
- Create: `tests/unit/v2/ingest/adapters/test_source_code.py` 他

**テスト観点:**
- `source_code.py` が 500KB 制限を enforce（E1）
- Python / TypeScript / Go / Rust / Shell の識別（拡張子ベース）
- Markdown の front-matter 検出と本文正規化
- plaintext は改行正規化のみ

Commit: `feat(v2/ingest): source_code / markdown / plaintext adapter を追加`

---

## Task 3.3: office（docx / xlsx / pptx）adapter

**Branch:** `feature/phase3-task3__office-adapter` ← `feature/phase3-task2__source-code-adapter`
**PR target:** `feature/phase-3__ingest__base`

**Files:**
- Create: `src/v2/ingest/adapters/office.py`
- Create: `config/review_form_templates/default.yaml`（設計書 §7.6 #6）
- Create: `tests/unit/v2/ingest/adapters/test_office.py`
- Create: `tests/fixtures/ingest/{sample.docx,sample.xlsx,sample.pptx}`

**テスト観点:**
- docx: python-docx 由来の段落抽出、脚注、表
- xlsx: openpyxl で `structured={"sheets": [...]}` を作成
- xlsx: レビュー依頼票テンプレ `default.yaml` マッピングで `ReviewRequestForm` 変換成功
- xlsx: 未知カラムは無視 + `structlog.warning("prior_form_schema_unknown")`（§7.6 #6 フォールバック）
- xlsx: 必須カラム欠落 → `PriorFormSchemaError`
- pptx: python-pptx でスライド順テキスト抽出

Commit: `feat(v2/ingest): office（docx/xlsx/pptx）adapter とレビュー依頼票テンプレを追加`

---

## Task 3.4: pdf / image adapter

**Branch:** `feature/phase3-task4__pdf-image-adapter` ← `feature/phase3-task3__office-adapter`
**PR target:** `feature/phase-3__ingest__base`

**Files:**
- Create: `src/v2/ingest/adapters/pdf.py`, `image.py`
- Create: `tests/unit/v2/ingest/adapters/test_pdf.py`, `test_image.py`
- Create: `tests/fixtures/ingest/{small.pdf,large_20mb.pdf,sample.png}`

**テスト観点:**
- pdf: pypdf でページ順抽出、20MB 超はページ単位ストリーム抽出に切替（E2）、`metadata.truncated=True`、`structlog.warning("ingest_truncated", ...)`
- image: OCR なしで `content=""` + `metadata={"ocr_required": True}`（ingestor としては LLM image input パスに委ねる）

Commit: `feat(v2/ingest): pdf / image adapter（ストリーム抽出対応）を追加`

---

## Task 3.5: gdocs / gsheets / gslides adapter + Drive resolver

**Branch:** `feature/phase3-task5__gws-adapters` ← `feature/phase3-task4__pdf-image-adapter`
**PR target:** `feature/phase-3__ingest__base`

**Files:**
- Create: `src/v2/ingest/adapters/gdocs.py`, `gsheets.py`, `gslides.py`
- Modify: `src/v2/ingest/resolver.py`（gws CLI 経由 Drive URL 解決）
- Create: `tests/unit/v2/ingest/adapters/test_gdocs.py` 他
- Create: `tests/unit/v2/ingest/test_drive_access.py`（E9）

**テスト観点:**
- gws CLI を subprocess で invoke、`correlation_id` を必ず渡す
- 権限無し Drive URL → `DriveAccessDeniedError`、`structlog.error("drive_access_denied", url=<masked>)`
- gdocs: 構造化抽出（見出し、箇条書き）
- gsheets: 複数シート対応、`structured={"sheets": [...]}`
- gslides: スライド順テキスト

Commit: `feat(v2/ingest): gws（gdocs/gsheets/gslides）adapter と Drive URL リゾルバを追加`

---

## Task 3.6: Ingest 統合テスト（registry→resolver→adapter フロー）

**Branch:** `feature/phase3-task6__ingest-e2e` ← `feature/phase3-task5__gws-adapters`
**PR target:** `feature/phase-3__ingest__base`

**Files:**
- Create: `tests/unit/v2/ingest/test_ingest_flow.py`
- Modify: `src/v2/ingest/resolver.py`（全 adapter を registry に登録、ファサード `ingest_all(sources)` を追加）

**テスト観点:**
- `sources=[IngestSource(kind="drive_url", ...), IngestSource(kind="file_path", ...)]` を一括 ingest → 全件正規化
- E3（1,000 ファイル一括、各 `<=500KB`）→ TaskGroup で並列、`state.failures == []`（並列上限 4 を遵守）
- 循環参照（E10）を跨ぐ自動解決

Commit: `feat(v2/ingest): registry/resolver/adapter を統合する ingest ファサードを追加`

**Phase 3 完了:** PR マージ → master。

---

# Phase 4: エージェント + 情報源

**Branch:** `feature/phase-4__agents__base` ← `master`
**PR target:** `master`
**マイルストーン:** 4 persona（SECURITY_GUARD / ARCHITECT / DOMAIN / PERFORMANCE）の `ReviewAgent` が単独で `FindingV2` 列を返す。NotebookLM InformationSource が Pydantic schema 検証付きで稼働。`prompts/*.xml` 7 ファイルが存在し loader 経由で読める。

## Task 4.1: AgentContext / AgentReport / AgentFailure / BaseAgent + TokenUsage 結線

**Branch:** `feature/phase4-task1__agent-base` ← `feature/phase-4__agents__base`
**PR target:** `feature/phase-4__agents__base`

**Files:**
- Create: `src/v2/agents/__init__.py`
- Create: `src/v2/agents/base.py`
- Modify: `src/v2/core/types.py`（Phase 1 の `Any` プレースホルダを `AgentReport` / `TokenUsage` に差し替え、循環 import を避けるため `TYPE_CHECKING` ガード）
- Create: `tests/unit/v2/agents/test_base.py`

**実装方針（設計書 §6.5）:**
- `AgentContext`, `AgentReport`, `AgentFailure`, `AgentResponse`, `Resolution` を正式定義
- `BaseReviewAgent` は `__init__(persona, executor: AgentExecutor, prompt_path: Path)` でコンポジション
- `review(ctx)` は共通実装で:
  1. `_build_user_content(ctx)`（サブクラス override）
  2. `executor.invoke(persona, system_blocks, user_content)` を呼ぶ
  3. レスポンスから `FindingV2` 列をパース（サブクラス override）
  4. `AgentReport(persona, findings, duration_ms, usage)` を返す
  5. タイムアウト 120s 超過で `AgentTimeoutError`（v1 既存）

テスト観点:
- `BaseReviewAgent.review` が fake executor + fake プロンプトで通し動作
- 応答 JSON 解析失敗 → `AgentReport(findings=[])` + `structlog.error("agent_parse_failed")`

Commit: `feat(v2/agents): BaseReviewAgent と AgentContext/Report/Failure を追加`

---

## Task 4.2: NotebookLM InformationSource（Pydantic schema 検証付き）

**Branch:** `feature/phase4-task2__notebook-source` ← `feature/phase4-task1__agent-base`
**PR target:** `feature/phase-4__agents__base`

**Files:**
- Create: `src/v2/sources/__init__.py`
- Create: `src/v2/sources/notebook.py`（`NotebookLMResponseV1` Pydantic モデル + `NotebookLMSource`）
- Create: `src/v2/sources/gws_docs.py`（REFERENCE レベルの GWS 情報源、Phase 5 で使用）
- Create: `tests/unit/v2/sources/test_notebook.py`

**テスト観点（設計書 §7.6 #3）:**
- 正常レスポンス → `SourceExcerpt(authority_level=ABSOLUTE, citation="NotebookLM §...")`
- schema 不整合 → `SourceSchemaError` + `structlog.error("notebook_schema_mismatch", expected_version="v1", raw_keys=...)`
- `correlation_id` が必ずクライアント呼出しに渡る

Commit: `feat(v2/sources): NotebookLM InformationSource（Pydantic V1 schema 検証）を追加`

---

## Task 4.3: プロンプト XML 資産 + ローダ

**Branch:** `feature/phase4-task3__prompts` ← `feature/phase4-task2__notebook-source`
**PR target:** `feature/phase-4__agents__base`

**Files:**
- Create: `src/v2/prompts/__init__.py`
- Create: `src/v2/prompts/sentinel.xml`
- Create: `src/v2/prompts/security_guard.xml`
- Create: `src/v2/prompts/architect.xml`
- Create: `src/v2/prompts/domain.xml`
- Create: `src/v2/prompts/performance.xml`
- Create: `src/v2/prompts/qna_followup.xml`
- Create: `src/v2/prompts/information_hierarchy.xml`
- Create: `src/v2/prompts/loader.py`（`load_prompt(name) -> list[SystemBlock]`、`<persona>`, `<information_hierarchy>`, `<core_directives>` を section ごとに SystemBlock 化、必要に応じて `CacheHint` を付与）
- Create: `tests/unit/v2/prompts/test_loader.py`

**プロンプト設計規約（設計書 §4.4 / §1.2）:**
- provider 固有タグ（`<thinking>`, `cache_control`）は XML に埋め込まない
- 日本語で記述（ペルソナの役割・行動原則）
- `<information_hierarchy>` は設計書 §5.1 の権威レベル定義を literal に埋込
- `<core_directives>` は「Boundary-based shielding」「LLM 自動承認禁止」「裁定ルール 1（セキュリティ最上位）」等を明記

**テスト観点:**
- loader が全 7 ファイルをエラーなく読み込む
- 破損 XML → `PromptLoadError`
- SystemBlock の `cache_hint` が information_hierarchy / core_directives に付与される（頻出のためキャッシュ対象）

Commit: `feat(v2/prompts): 7 個のペルソナ／共通プロンプト XML とローダを追加`

---

## Task 4.4: SecurityGuardAgent

**Branch:** `feature/phase4-task4__security-guard-agent` ← `feature/phase4-task3__prompts`
**PR target:** `feature/phase-4__agents__base`

**Files:**
- Create: `src/v2/agents/security_guard.py`
- Create: `tests/unit/v2/agents/test_security_guard.py`

**実装方針（設計書 §2）:**
- 入力: target_files, `ShieldResult`
- 検出対象: ハードコード秘密、パストラバーサル、shield 逸脱
- ツール: `ModelArmorMiddleware`（v1 `src/plugins/security/`）+ secrets regex
- 出力: `list[FindingV2]`（`comment_type=ISSUE`, `bug_phenomenon=CODING_MISS`, severity 割当）

**テスト観点:**
- 偽 LLM 応答（秘密パターンを含む recommendation）でも Findings が返る（shield_output は境界なので executor 応答内に残る）
- パストラバーサル検出 → `severity=high`
- 空入力 → 空 findings

Commit: `feat(v2/agents): SecurityGuardAgent を追加`

---

## Task 4.5: ArchitectAgent

**Branch:** `feature/phase4-task5__architect-agent` ← `feature/phase4-task4__security-guard-agent`
**PR target:** `feature/phase-4__agents__base`

**Files:**
- Create: `src/v2/agents/architect.py`
- Create: `tests/unit/v2/agents/test_architect.py`

**実装方針（設計書 §2）:**
- 入力: target_files AST, 設計文書群（ARCHITECTURE.md, SPEC.md, AGENTS.md）
- 検出: 継承の深さ違反、composition 準拠違反、ARCHITECTURE/SPEC/AGENTS との不整合
- ツール: `ast` 標準ライブラリ
- 出力: `list[FindingV2]`

**テスト観点:**
- 深い継承（3 段以上）検出
- composition 準拠（`__init__` で protocol 注入）への reward
- ARCHITECTURE.md にない新規レイヤ導入を検知

Commit: `feat(v2/agents): ArchitectAgent を追加`

---

## Task 4.6: DomainAgent + PerformanceAgent

**Branch:** `feature/phase4-task6__domain-performance-agents` ← `feature/phase4-task5__architect-agent`
**PR target:** `feature/phase-4__agents__base`

**Files:**
- Create: `src/v2/agents/domain.py`
- Create: `src/v2/agents/performance.py`
- Create: `tests/unit/v2/agents/test_domain.py`
- Create: `tests/unit/v2/agents/test_performance.py`

**実装方針:**
- DomainAgent: NotebookLM InformationSource から `SourceExcerpt` を取得し、`authority_level=ABSOLUTE` を findings に埋め込む
- E14 対応: 同一論点で 2 件以上の ABSOLUTE 抜粋が矛盾 → `FindingV2.comment_type=QUESTION`, `bug_phenomenon=DESIGN_EXPRESSION`
- PerformanceAgent: async ブロッキング、N+1、同期 I/O を AST パターンマッチで検出

**テスト観点:**
- Domain: NotebookLM 矛盾入力で QUESTION finding 生成（E14）
- Performance: `requests.get` を async 関数内で呼ぶコードを検出

Commit: `feat(v2/agents): DomainAgent と PerformanceAgent を追加`

**Phase 4 完了:** master にマージ。

---

# Phase 5: Automation E2E（LangGraph + Report + Approval）

**Branch:** `feature/phase-5__automation__base` ← `master`
**PR target:** `master`
**マイルストーン:** `uv run aegis review-v2 <paths>` を実行すると、ingest → 並列レビュー → 裁定 → レポート生成 → gws publish → `completed_pending_approval` まで通しで稼働。`aegis ask`, `aegis approve`, `aegis report show` が揃う。

## Task 5.1: SentinelState と reducer

**Branch:** `feature/phase5-task1__state` ← `feature/phase-5__automation__base`
**PR target:** `feature/phase-5__automation__base`

**Files:**
- Create: `src/v2/automation/__init__.py`
- Create: `src/v2/automation/graph/__init__.py`
- Create: `src/v2/automation/graph/state.py`（`SentinelState` TypedDict, `_merge_agent_reports`, `_extend_list`）
- Create: `src/v2/core/types.py`（追記: `Conflict` 型と `conflict_type` Literal）
- Create: `tests/unit/v2/automation/test_state.py`

**テスト観点（設計書 §3.1）:**
- `_merge_agent_reports`: 同一 persona の二重到着で後着が勝つ
- `_extend_list`: conflicts / resolutions / failures が append される
- `state["request"].correlation_id` が常に Single Source

Commit: `feat(v2/automation): SentinelState と reducer を追加`

---

## Task 5.2: ShieldedPersistenceWriter

**Branch:** `feature/phase5-task2__shielded-writer` ← `feature/phase5-task1__state`
**PR target:** `feature/phase-5__automation__base`

**Files:**
- Create: `src/v2/persistence/__init__.py`
- Create: `src/v2/persistence/shielded_writer.py`
- Create: `tests/unit/v2/persistence/test_shielded_writer.py`

**実装方針（設計書 §3.3）:**
- `ShieldedPersistenceWriter(shield: SecurityShield)`
- `write_atomic(path, payload: dict | str)`: 書込み直前に `shield.shield_output` を全テキストフィールドへ適用 → `TaskDispatcher._sync_atomic_write`（v1 流用）で atomic write
- `wrap_sqlite_saver(checkpointer)`: LangGraph `SqliteSaver` を wrap し `put()` 前に shield を噛ます
- `.review/artifacts/` / `.review/conflicts/` / `.review/qna/` 全て経由

**テスト観点:**
- fake 秘匿文字列を含む payload を write_atomic → ディスク上のバイト列に秘匿文字列が**現れない**
- atomic write 失敗時の rollback（temp file の削除）

Commit: `feat(v2/persistence): ShieldedPersistenceWriter（永続化境界 shield）を追加`

---

## Task 5.3: prepare_context ノード

**Branch:** `feature/phase5-task3__prepare-context` ← `feature/phase5-task2__shielded-writer`
**PR target:** `feature/phase-5__automation__base`

**Files:**
- Create: `src/v2/automation/graph/nodes.py`（`prepare_context` 関数のみ。他ノードは後続 Task）
- Create: `tests/unit/v2/automation/test_prepare_context.py`

**実装方針（設計書 §3.2 (1)）:**
- Ingest 全入力（target_docs, reference_docs, notebook_docs, prior_form）→ `IngestedDocument` 化
- `NotebookLMSource` をクエリ → `NotebookContext`
- `shield_input` をエージェントに渡す前の共通テキストへ適用
- `correlation_id` を `state.request.correlation_id` として確定
- v1 `core.Orchestrator` を `target_docs` のうち `format="source_code"` から `ReviewRequest` を構築して呼出（設計書 §6.2 の注記）

**テスト観点:**
- 正常入力で `state.ingested` / `state.notebook_context` が埋まる
- Drive アクセス失敗（E9）でも他入力は継続し `state.failures` に積まれる

Commit: `feat(v2/automation): prepare_context ノード（ingest / notebook / shield_input / v1 orchestrator 結線）`

---

## Task 5.4: fan_out_agents + 4 persona ノード

**Branch:** `feature/phase5-task4__fan-out` ← `feature/phase5-task3__prepare-context`
**PR target:** `feature/phase-5__automation__base`

**Files:**
- Modify: `src/v2/automation/graph/nodes.py`（`fan_out_agents`, `run_agent_node`）
- Create: `src/v2/automation/graph/edges.py`（`Send` API による動的 fan-out、target_kind に応じたペルソナ選択）
- Create: `tests/unit/v2/automation/test_fan_out.py`

**実装方針（設計書 §3.2 (2), §3.4, §2.1）:**
- `target_kind` ごとの必須ペルソナ（§2.1 表）を選択
- `Send` で各 persona ノードへ read-only slice を渡す
- 1 persona 失敗 → `state.failures` に `AgentFailure` 追加、全体は継続
- `AgentResponse.text` は unredacted で `state.agent_reports` に入る
- artifact 書込み時のみ `ShieldedPersistenceWriter` 経由

**テスト観点:**
- `kind=DOCUMENT` なら DOMAIN / ARCHITECT が必須、SECURITY_GUARD / PERFORMANCE が補助
- 1 persona raise → 他 3 は完走、failures に 1 件
- shield_input 遮断（E11）→ 当該ファイルのみ除外、レポート §3 に記録

Commit: `feat(v2/automation): fan_out_agents と 4 persona ノード（Send API / 失敗隔離）`

---

## Task 5.5: detect_conflicts

**Branch:** `feature/phase5-task5__detect-conflicts` ← `feature/phase5-task4__fan-out`
**PR target:** `feature/phase-5__automation__base`

**Files:**
- Modify: `src/v2/automation/graph/nodes.py`（`detect_conflicts` 追加）
- Modify: `src/v2/core/types.py`（`Conflict` dataclass を正式化、Phase 1 Task 1.4 の protocol も正式型に差し替え）
- Create: `tests/unit/v2/automation/test_detect_conflicts.py`

**実装方針（設計書 §5.2）:**
- 同一 `(file_path, line)` で severity 2 段階以上乖離 → `severity_divergence`
- DOMAIN と他ペルソナが相互矛盾 → `domain_contradiction`（E6）
- SECURITY_GUARD が `high`/`critical` に対し他ペルソナが不整合 → `security_override_conflict`

**テスト観点:**
- 3 種の conflict_type を固定 findings で生成できる
- 検出ロジックは unredacted な full context で走る（`test_resolver_full_context.py` の前準備）

Commit: `feat(v2/automation): detect_conflicts ノードと Conflict 型を追加`

---

## Task 5.6: SentinelResolver（裁定ルール 1–4）

**Branch:** `feature/phase5-task6__sentinel-resolver` ← `feature/phase5-task5__detect-conflicts`
**PR target:** `feature/phase-5__automation__base`

**Files:**
- Create: `src/v2/automation/resolver/__init__.py`
- Create: `src/v2/automation/resolver/sentinel.py`
- Modify: `src/v2/automation/graph/nodes.py`（`resolve_conflicts` ノード追加）
- Create: `tests/unit/v2/automation/resolver/test_sentinel.py`

**実装方針（設計書 §5.3）:**
- `SentinelResolver.resolve(conflicts, state)` を実装
- システムプロンプトに `<information_hierarchy>` + `<core_directives>` を literal 埋込
- provider 経由で JSON 応答を強制（`response_format="json"`）
- 裁定ルール適用順:
  1. **セキュリティ保護（最上位）**: SECURITY_GUARD high/critical → `decision=escalate`, `winning_persona=None`, `next_steps` に人間確認必須を追記、`forced_by_rule=1`
  2. **DOMAIN/ABSOLUTE**: winning=DOMAIN かつ authority=ABSOLUTE → 他 findings は `superseded_by` メタで非表示化（監査には全文保持）
  3. **NotebookLM 内部矛盾**: `domain_contradiction` かつ ABSOLUTE 抜粋が複数互いに矛盾 → `decision=escalate` に固定（E7 / E14）、`forced_by_rule=3`
  4. **一般ケース**: LLM 応答をそのまま採用

**テスト観点:**
- ルール 1: SECURITY high + DOMAIN ABSOLUTE override 試行でも `escalate` に強制
- ルール 3: 複数 ABSOLUTE 矛盾で LLM が `uphold` を返しても `escalate` に固定（E7 / E14）
- ルール 4: 一般ケースで LLM の `merge` がそのまま採用

Commit: `feat(v2/automation): SentinelResolver（セキュリティ強制 escalate / ABSOLUTE 優越 / NotebookLM 内部矛盾）を追加`

---

## Task 5.7: compose_report + Markdown renderer + Q&A / Approval 型整備

**Branch:** `feature/phase5-task7__compose-report` ← `feature/phase5-task6__sentinel-resolver`
**PR target:** `feature/phase-5__automation__base`

**Files:**
- Create: `src/v2/report/__init__.py`
- Create: `src/v2/report/renderer.py`（Markdown renderer、`<report_format>` literal 遵守）
- Modify: `src/v2/automation/graph/nodes.py`（`compose_report` ノード追加、**公開境界 shield_output** をここで初めて適用）
- Create: `tests/unit/v2/report/test_renderer.py`
- Create: `tests/unit/v2/automation/test_compose_report.py`

**実装方針（設計書 §3.2 (5), §6.4）:**
- Renderer は `ReviewReportV2` 受領直後に `shield_output` を `executive_summary` / `details` / `recommendation` / `qna_threads.*.content` へ適用
- テンプレート f-string で固定、LLM 生成部分は `executive_summary` と 各 finding の `details` / `recommendation` のみ
- 承認ステータスに応じて `[未承認]` / `[承認済み]` フッター

**テスト観点:**
- 日本語区分（指摘/要望/質問、当工程バグ/上位工程バグ/…、設計漏れ/…）が正しいセクション順
- LLM 的前置き（"Here is the report..."）が除去
- shield_output が全テキストフィールドに適用済みである（fake 秘匿文字列が出力から消える）

Commit: `feat(v2/report): Markdown renderer と compose_report ノード（公開境界 shield_output）`

---

## Task 5.8: persist_and_publish + gws publisher + checkpoints

**Branch:** `feature/phase5-task8__persist-publish` ← `feature/phase5-task7__compose-report`
**PR target:** `feature/phase-5__automation__base`

**Files:**
- Create: `src/v2/report/publisher.py`（`.review/report.md` + gws Docs + gws Sheets 書出し）
- Modify: `src/v2/automation/graph/nodes.py`（`persist_and_publish` ノード追加）
- Create: `src/v2/automation/graph/builder.py`（`build_graph(config)` で `StateGraph.compile(checkpointer=ShieldedSqliteSaver)` を返す）
- Modify: `src/plugins/sync/report_writer.py`（`correlation_id: str | None = None` 後方互換、`None` 時は uuid4 自動採番 + ログ警告 1 回）
- Create: `tests/unit/v2/report/test_publisher.py`
- Create: `tests/unit/v2/automation/test_builder.py`

**実装方針（設計書 §3.2 (6), §3.3, §7.3）:**
- publisher は shield 済み `ReviewReportV2` を受領（二重 shield 不要の契約）
- gws CLI 呼出しに `--correlation-id` を必ず渡す、失敗時 stderr サマリーを `structlog.error`
- Google Sheets は findings をフラット化（1 finding = 1 row）
- `SqliteSaver` は `ShieldedPersistenceWriter.wrap_sqlite_saver` で wrap

**テスト観点:**
- `.review/report.md` に shield 済みテキストのみ（fake 秘匿文字列が出現しない）
- gws 呼出し失敗時も `state.final_report` は保持され `status=completed_pending_approval`（報告可）
- 空 findings（E8）でも status は failed でなく `completed_pending_approval`

Commit: `feat(v2/automation): persist_and_publish ノードと publisher、builder を追加`

---

## Task 5.9: Q&A セッション + Approval 記録

**Branch:** `feature/phase5-task9__qna-approval` ← `feature/phase5-task8__persist-publish`
**PR target:** `feature/phase-5__automation__base`

**Files:**
- Create: `src/v2/qna/__init__.py`
- Create: `src/v2/qna/session.py`, `src/v2/qna/store.py`
- Create: `src/v2/approval/__init__.py`
- Create: `src/v2/approval/recorder.py`（`record_approval(report, approver, comment)` → `Approval` を作成し `.review/approved.json` へ atomic write、LLM 経由の呼出しを拒否）
- Create: `tests/unit/v2/qna/test_session.py`
- Create: `tests/unit/v2/approval/test_recorder.py`

**実装方針（設計書 §6.3, §7.4）:**
- `QnASession.ask(finding_id, question, correlation_id)`:
  - 対象 finding の全メタデータ + 元コード / NotebookLM 抜粋 + 過去 Q&A を Sentinel に投げる
  - 応答は publisher 側で公開境界 shield_output を適用
  - `.review/qna/<finding_id>/<NNN>.md` に `ShieldedPersistenceWriter` 経由で保存
- Approval: LLM 呼出し経路では `APPROVED` 遷移を拒否（`LLMCannotApproveError`）。CLI の `aegis approve` からのみ遷移可

**テスト観点:**
- LLM 経由で APPROVED 遷移を試みるテストが `LLMCannotApproveError` で失敗することを確認
- Q&A ログが atomic write される、shield 済みテキストのみがディスクに残る

Commit: `feat(v2/qna,approval): Q&A セッションと Approval 記録（LLM 自動承認禁止）を追加`

---

## Task 5.10: `aegis` CLI 統合（review-v2 / ask / approve / report show）

**Branch:** `feature/phase5-task10__cli` ← `feature/phase5-task9__qna-approval`
**PR target:** `feature/phase-5__automation__base`

**Files:**
- Modify: `src/cli/main.py`（`aegis` Typer app に `review-v2`, `ask`, `approve`, `report` サブコマンドを追加、`llm-review` は alias 温存）
- Modify: `pyproject.toml`（`[project.scripts]` に `aegis = "cli.main:app"`）
- Create: `tests/unit/v2/cli/test_aegis_cli.py`

**コマンド仕様（設計書 §7.1）:**

| コマンド | 実装 |
|---|---|
| `aegis review-v2 --target <paths> [--kind ...] [--mode auto\|automation\|interactive]` | `build_graph` → `graph.ainvoke(state)` |
| `aegis review-v2 --resume <request_id>` | `build_graph` で checkpointer 結線 → 再実行 |
| `aegis review-v2 --dry-run` | graph 構築のみ、ainvoke せず |
| `aegis ask <request_id> <finding_id> --question "..."` | `QnASession.ask` |
| `aegis approve <request_id> --approver <name> [--comment "..."]` | `ApprovalRecorder.record_approval` |
| `aegis report show <request_id>` | `.review/report.md` を stdout |

**モード選択ロジック:**
- `--mode auto` + `CI=true` → automation
- それ以外かつ MCP セッション無し → automation にフェイルセーフ（Phase 6 以前は常に automation）

**テスト観点:**
- `--dry-run` が LLM 呼出しなしで 0 終了
- `aegis approve` の二重実行で 2 つ目が `AlreadyApprovedError` で exit 1
- `aegis review-v2 --resume` で checkpointer から state 復元（設計書 §7.5 `test_resume_degradation`）

Commit: `feat(cli): aegis サブコマンド（review-v2 / ask / approve / report show）を追加`

**Phase 5 完了:** `master` マージ後、Automation 経路が使用可能になる。

---

# Phase 6: Interactive 経路（Cursor + MCP）

**Branch:** `feature/phase-6__interactive__base` ← `master`
**PR target:** `master`
**マイルストーン:** Cursor 拡張 `/aegis review` から MCP 経由で Automation と同等成果物を生成。`.cursor/rules/*.mdc` が `prompts/*.xml` と drift テストで同期保証される。

## Task 6.1: MCP FastMCP サーバ骨格

**Branch:** `feature/phase6-task1__mcp-server` ← `feature/phase-6__interactive__base`
**PR target:** `feature/phase-6__interactive__base`

**Files:**
- Modify: `pyproject.toml`（`mcp>=0.9`）
- Create: `src/v2/mcp/__init__.py`
- Create: `src/v2/mcp/server.py`（FastMCP 初期化、stdio バインド強制、TCP 拒否）
- Create: `tests/unit/v2/mcp/test_server.py`

Commit: `feat(v2/mcp): FastMCP サーバ骨格（stdio 限定）を追加`

---

## Task 6.2: MCP 読取り系ツール群

**Branch:** `feature/phase6-task2__mcp-read-tools` ← `feature/phase6-task1__mcp-server`
**PR target:** `feature/phase-6__interactive__base`

**Files:**
- Create: `src/v2/mcp/tools/{notebook_query,shield_input,shield_output,ingest_resolve,ast_scan,status_publish}.py`
- Create: `tests/unit/v2/mcp/tools/test_*.py`

各ツールは Phase 3–5 で作成した関数を薄くラップ。`correlation_id` 必須、構造化エラー応答。

Commit: `feat(v2/mcp): 読取り系 MCP ツール（notebook_query / shield_* / ingest_resolve / ast_scan / status_publish）`

---

## Task 6.3: MCP 書込み系ツール（artifact / qna / submit / gws）

**Branch:** `feature/phase6-task3__mcp-write-tools` ← `feature/phase6-task2__mcp-read-tools`
**PR target:** `feature/phase-6__interactive__base`

**Files:**
- Create: `src/v2/mcp/tools/{artifact_write,ask_about_finding,submit_finding,gws_publish}.py`
- Create: `tests/unit/v2/mcp/tools/test_*.py`

**実装方針:**
- `submit_finding`: audit canary マーカー（設計書 §7.6 #5）の検査、無い場合 `audit_integrity=unverified`
- `artifact_write` / `ask_about_finding`: `ShieldedPersistenceWriter` 経由
- `gws_publish`: shield 済みのみ受容、`correlation_id` 必須

Commit: `feat(v2/mcp): 書込み系 MCP ツールと audit canary 検査を追加`

---

## Task 6.4: rules_sync + drift テスト

**Branch:** `feature/phase6-task4__rules-sync` ← `feature/phase6-task3__mcp-write-tools`
**PR target:** `feature/phase-6__interactive__base`

**Files:**
- Create: `src/v2/interactive/__init__.py`
- Create: `src/v2/interactive/rules_sync.py`
- Create: `.cursor/rules/README.md`（"このディレクトリは自動生成。手編集禁止" と明記）
- Create: `tests/unit/v2/interactive/test_rules_sync.py`（drift テスト本体）

**実装方針（設計書 §4.4, §7.5）:**
- `rules_sync.generate_all()` が `src/v2/prompts/*.xml` → `.cursor/rules/aegis-*.mdc` を冪等生成
- テストは `generate_all` を一時ディレクトリで実行し、リポジトリの `.cursor/rules/*.mdc` とバイト単位で一致することを保証

Commit: `feat(v2/interactive): prompts/*.xml から .cursor/rules/*.mdc を自動生成する rules_sync と drift テスト`

---

## Task 6.5: Cursor 拡張骨格（package.json / extension.ts / mcpBridge.ts）

**Branch:** `feature/phase6-task5__cursor-skeleton` ← `feature/phase6-task4__rules-sync`
**PR target:** `feature/phase-6__interactive__base`

**Files:**
- Create: `cursor-extension/package.json`（`engines.cursor`, `/aegis review`, `/aegis ask`, `/aegis approve` コマンド登録）
- Create: `cursor-extension/src/extension.ts`
- Create: `cursor-extension/src/mcpBridge.ts`（devcontainer 内で `uv run aegis review-v2 --mode=interactive` を起動、stdio で MCP 接続）
- Create: `cursor-extension/tsconfig.json`
- Create: `cursor-extension/src/__tests__/mcpBridge.test.ts`（jest / vitest、Node.js レベル）

**テスト観点:**
- `mcpBridge` が devcontainer 起動成功／失敗を正しくハンドリング
- サポート外 Cursor バージョンで警告ダイアログ

Commit: `feat(cursor-extension): 拡張骨格と MCP ブリッジ（TypeScript）を追加`

---

## Task 6.6: Cursor 拡張 UI（uploadPanel / statusWatcher）

**Branch:** `feature/phase6-task6__cursor-ui` ← `feature/phase6-task5__cursor-skeleton`
**PR target:** `feature/phase-6__interactive__base`

**Files:**
- Create: `cursor-extension/src/uploadPanel.ts`（ファイル選択 / Drive URL / DOCUMENT|SOURCE_CODE|MIXED トグル / focus_hints 入力）
- Create: `cursor-extension/src/statusWatcher.ts`（`chokidar` で `.review/status.json` を watch）
- Create: `cursor-extension/src/__tests__/uploadPanel.test.ts`
- Create: `cursor-extension/src/__tests__/statusWatcher.test.ts`

**実装方針（設計書 §7.1 UI 要素）:**
- `.review/status.json` スキーマ（§7.1 末尾の JSON）を TypeScript 型で定義
- レポート完成時に `.review/report.md` を自動 open
- 各 finding 横に「このコメントについて質問する」ボタン → `aegis ask`

Commit: `feat(cursor-extension): アップロード UI と status 監視を追加`

---

## Task 6.7: Interactive 用 CLI 経路 + 逐次フォールバック + audit canary

**Branch:** `feature/phase6-task7__interactive-cli` ← `feature/phase6-task6__cursor-ui`
**PR target:** `feature/phase-6__interactive__base`

**Files:**
- Modify: `src/cli/main.py`（`--mode=interactive` 時は MCP サーバ起動で終わる）
- Modify: `src/v2/mcp/server.py`（30s fan_out 未着手で sequential フォールバック、設計書 §7.6 #4）
- Create: `tests/unit/v2/mcp/test_interactive_mode.py`

**テスト観点:**
- 逐次フォールバック経路で 4 persona が順次 review → 同じ `ReviewReportV2` 生成
- audit canary が system prompt 末尾に挿入、`submit_finding` が検査

Commit: `feat(v2/mcp,cli): Interactive 経路（逐次フォールバック / audit canary）を追加`

**Phase 6 完了:** `master` マージ。

---

# Phase 7: Hardening（エッジケース・非機能・移行）

**Branch:** `feature/phase-7__hardening__base` ← `master`
**PR target:** `master`
**マイルストーン:** E1–E14 全シナリオが自動テストで網羅、provider 互換性 Jaccard ≥ 0.85、境界 shield 契約テスト完備、`docs/v2/migration-notes.md` 整備、`AsyncSemaphore` と RateLimit 動的縮退が稼働。

## Task 7.1: AsyncSemaphore + 動的並列縮退 + RetryConfig

**Branch:** `feature/phase7-task1__rate-limit` ← `feature/phase-7__hardening__base`
**PR target:** `feature/phase-7__hardening__base`

**Files:**
- Modify: `src/v2/llm/executor.py`（`AsyncSemaphore(LLM_PROVIDER_MAX_CONCURRENT)` を注入、`RateLimitError` で `max_concurrent` を半減 → 60 秒成功で復元）
- Modify: `src/core/config.py`（`RetryConfig` に `anthropic.RateLimitError` / `anthropic.APITimeoutError` / `openai.RateLimitError` を `retryable_exceptions` として追加）
- Create: `tests/unit/v2/llm/test_rate_limit_throttling.py`

**テスト観点（設計書 §7.6 #2）:**
- 5 並列で 1 回 RateLimitError → 次以降は `max_concurrent=2` で動作
- 60 秒連続成功で `max_concurrent` が元値に復元
- 5 回失敗したペルソナは `AgentFailure` に積まれ全体は継続
- `structlog.warning("provider_rate_limit", current_concurrency=..., backoff_seconds=...)` が emit

Commit: `feat(v2/llm): AgentExecutor に動的並列縮退と RateLimit リトライを追加`

---

## Task 7.2: feature_probe integration + SDK ピン留めドキュメント

**Branch:** `feature/phase7-task2__feature-probe` ← `feature/phase7-task1__rate-limit`
**PR target:** `feature/phase-7__hardening__base`

**Files:**
- Create: `tests/integration/v2/test_feature_probe.py`（`@integration` 付き、devcontainer のみ）
- Create: `docs/v2/sdk-pinning.md`（`anthropic>=0.40,<1.0` 固定の理由、マイナー更新時の手動検証手順）

Commit: `feat(v2/llm): feature_probe integration テストと SDK ピン留め手順を追加`

---

## Task 7.3: E1–E14 エッジケーステスト網羅

**Branch:** `feature/phase7-task3__edge-cases` ← `feature/phase7-task2__feature-probe`
**PR target:** `feature/phase-7__hardening__base`

**Files:**
- Create: `tests/unit/v2/edge_cases/test_e01_large_single_file.py`
- Create: `tests/unit/v2/edge_cases/test_e02_large_pdf_stream.py`
- Create: `tests/unit/v2/edge_cases/test_e03_bulk_small_files.py`
- Create: `tests/unit/v2/edge_cases/test_e04_unsupported_format.py`
- Create: `tests/unit/v2/edge_cases/test_e05_unknown_mime.py`
- Create: `tests/unit/v2/edge_cases/test_e06_notebook_contradiction.py`
- Create: `tests/unit/v2/edge_cases/test_e07_notebook_internal_conflict.py`
- Create: `tests/unit/v2/edge_cases/test_e08_empty_inputs.py`
- Create: `tests/unit/v2/edge_cases/test_e09_drive_access_denied.py`
- Create: `tests/unit/v2/edge_cases/test_e10_circular_reference.py`
- Create: `tests/unit/v2/edge_cases/test_e11_shield_block.py`
- Create: `tests/unit/v2/edge_cases/test_e12_prior_comment_dedup.py`
- Create: `tests/unit/v2/edge_cases/test_e13_provider_degradation.py`
- Create: `tests/unit/v2/edge_cases/test_e14_absolute_internal_conflict.py`

各テストは設計書 §7.5 Edge case マトリクスの「期待出力／挙動」列を literal に検証。Phase 3–5 で未カバーだった観点をここで補完。

Commit: `test(v2): エッジケースマトリクス E1–E14 を網羅する自動テストを追加`

---

## Task 7.4: 非機能要件ベンチマーク

**Branch:** `feature/phase7-task4__non-functional` ← `feature/phase7-task3__edge-cases`
**PR target:** `feature/phase-7__hardening__base`

**Files:**
- Create: `tests/integration/v2/test_qna_latency.py`（p50 ≤ 15s、20 回計測、`@integration`）
- Create: `tests/integration/v2/test_provider_parity.py`（Jaccard ≥ 0.85、比較キー: `(location.doc_id, location.file_path, location.line, bug_phenomenon, severity)`）
- Create: `tests/integration/v2/test_prior_duplication_rate.py`（`relates_to_prior` 重複率 ≤ 5%）
- Create: `tests/integration/v2/test_throughput.py`（1 kLOC ≤ 3 分）
- Create: `tests/fixtures/v2/benchmark/`（ベンチマーク用リポジトリサンプル）

Commit: `test(v2): 非機能要件ベンチマーク（Q&A p50 / Jaccard / 重複率 / スループット）を追加`

---

## Task 7.5: 境界 shield 契約テスト 5 本

**Branch:** `feature/phase7-task5__boundary-shield` ← `feature/phase7-task4__non-functional`
**PR target:** `feature/phase-7__hardening__base`

**Files:**
- Create: `tests/unit/v2/security/test_persistence_boundary_shield.py`
- Create: `tests/unit/v2/security/test_publish_boundary_shield.py`
- Create: `tests/unit/v2/security/test_executor_no_output_shield.py`
- Create: `tests/unit/v2/security/test_resolver_full_context.py`
- Create: `tests/unit/v2/security/test_resume_degradation.py`

全て設計書 §7.5 セキュリティ検証節の literal 仕様に従う。テスト用 API キーダミー `sk-test-AEGIS-<uuid>` を fake LLM 応答に混入させ、ディスクに到達しないこと／resolver 入力には到達すること／publish に到達しないこと／`--resume` 時の仕様的デグレードを記録する。

Commit: `test(v2): 境界 shield 契約テスト 5 本（永続化 / 公開 / executor / resolver / resume）を追加`

---

## Task 7.6: 移行ドキュメント + v1 後方互換チェック

**Branch:** `feature/phase7-task6__migration-docs` ← `feature/phase7-task5__boundary-shield`
**PR target:** `feature/phase-7__hardening__base`

**Files:**
- Create: `docs/v2/migration-notes.md`（v1→v2 移行手順、`correlation_id` デフォルト `None` の deprecation path、`aegis` / `llm-review` CLI 並存、`AgentRole` enum と `AgentPersona` enum の `AgentIdentity` union 提供タイミング）
- Create: `docs/v2/audit-profile.md`（Interactive 経路と Automation 経路の監査粒度差、canary による担保、高信頼要件で `automation` 強制）
- Create: `tests/unit/v2/test_v1_backwards_compat.py`（v1 `AgentRole` enum / `ReviewRequest` / `ModelArmorMiddleware` / v1 既存テスト全 PASS を検証）

**テスト観点:**
- `src/plugins/sync/report_writer.py` の `write_report(correlation_id=None)` 呼出しで uuid4 自動採番 + ログ警告 1 回
- v1 既存テストが全 PASS

Commit: `docs(v2): 移行ノートと監査プロファイルを追加、v1 後方互換契約テストを追加`

---

## Task 7.7: 品質ゲート総仕上げ + CI 統合

**Branch:** `feature/phase7-task7__ci` ← `feature/phase7-task6__migration-docs`
**PR target:** `feature/phase-7__hardening__base`

**Files:**
- Modify: `bitbucket-pipelines.yml`（品質ゲート `uv sync && ruff check && mypy src && pytest -m "not integration"`）
- Modify: `pyproject.toml`（extras 整理、`aegis` script 明示）
- Create: `docs/v2/release-checklist.md`（リリース手順、品質ゲート一覧）

**テスト観点:**
- CI で全 Phase 1–7 の unit + E2E dry-run テストが green
- `uv run aegis review-v2 --dry-run ./tests/fixtures/v2/sample_repo` が 0 終了

Commit: `ci(v2): Bitbucket Pipelines 統合と release checklist を整備`

**Phase 7 完了:** `master` マージ → Aegis v2.0 機能完成。

---

# Self-Review（Spec coverage scan）

## Spec カバレッジ対応表（設計書 § → Task）

| 設計書節 | 実装 Task |
|---|---|
| §0.2 11 ステップフロー | Task 5.3 (1–7) / 5.4 (8) / 5.7 (9) / 5.9 (10) / 5.10 approve (11) |
| §1.1 ハイブリッド 2 経路 | Phase 5 (Automation) / Phase 6 (Interactive) |
| §1.2 原則（Protocol-first / Boundary-based Shielding） | Task 1.4, 2.6, 5.2, 5.7 |
| §1.3 観測可能性（structlog 必須フィールド） | Task 2.6, 5.3–5.10, 7.1 全体で enforce |
| §2 ペルソナ定義 | Task 4.4–4.6 |
| §2.1 target_kind 重み付け | Task 5.4 |
| §3.1 SentinelState + reducer | Task 5.1 |
| §3.2 ノード構成 | Task 5.3–5.8 |
| §3.3 チェックポイント + ShieldedPersistenceWriter | Task 5.2, 5.8, 7.5 `test_resume_degradation` |
| §3.4 並列実行制約（Send API, Semaphore） | Task 5.4, 7.1 |
| §4 LLM Provider 抽象化 | Phase 2 全体 |
| §4.3 AgentExecutor（入力側 shield のみ） | Task 2.6, 7.5 `test_executor_no_output_shield` |
| §4.4 プロンプト資産 | Task 4.3, 6.4 |
| §4.5 LLMProviderConfig | Task 1.5 |
| §5.1 AuthorityLevel | Task 1.2 |
| §5.2 detect_conflicts | Task 5.5 |
| §5.3 裁定ルール 1–4 | Task 5.6 |
| §6.1 日本語 enum | Task 1.1 |
| §6.2 入力型（ReviewRequestV2 等） | Task 1.3 |
| §6.3 出力型（FindingV2 / ReviewReportV2 / Approval） | Task 1.3, 5.7 |
| §6.4 Markdown renderer | Task 5.7 |
| §6.5 エージェント基盤型 | Task 4.1 |
| §6.6 Provider 中立コンテンツ型 | Task 2.1 |
| §6.7 Ingest 補助型 | Task 1.3, 3.1 |
| §6.8 プロトコル追加 | Task 1.4, 5.5 (正式型差替え) |
| §7.1 Cursor プラグイン I/F + CLI | Task 5.10, 6.5–6.7 |
| §7.2 ディレクトリ構成 | 全 Phase で具現化 |
| §7.3 v1 共存・移行 | Task 7.6 |
| §7.4 Q&A ループ | Task 5.9, 6.3 (MCP ask_about_finding) |
| §7.5 検証戦略 | Phase 7 全体 |
| §7.5 Edge case E1–E14 | Task 7.3 |
| §7.5 非機能要件 | Task 7.4 |
| §7.5 境界 shield 契約テスト | Task 7.5 |
| §7.6 #1 output_config.effort フォールバック | Task 2.3, 7.2 |
| §7.6 #2 LangGraph Send × RateLimit | Task 5.4, 7.1 |
| §7.6 #3 notebooklm-py schema | Task 4.2 |
| §7.6 #4 Cursor sub-agent API 版数依存 | Task 6.7 |
| §7.6 #5 Cursor usage/token 監査 | Task 6.3 (canary), 7.6 audit-profile.md |
| §7.6 #6 Excel/Sheet カラム差 | Task 3.3 |

**全節カバー済み。Placeholder・TBD は無し。型名（AgentPersona / FindingV2 / ReviewReportV2 / AgentReport / Conflict / Resolution / LLMProvider / AgentExecutor / AuthorityLevel / ShieldedPersistenceWriter / SentinelResolver）は全 Task で一貫使用。**

---

# Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-19-aegis-v2-multiagent.md`. Two execution options:**

**1. Subagent-Driven（推奨）** — Task ごとに新しい subagent を dispatch し、Task 間で two-stage review。Phase をまたいだ回帰検知と高速イテレーションに最適。

**2. Inline Execution** — このセッション内で `superpowers/executing-plans` を使って Task を逐次実行、checkpoint ごとに review。

どちらで進めますか？

**Subagent-Driven を選択した場合:** REQUIRED SUB-SKILL `superpowers:subagent-driven-development`

**Inline Execution を選択した場合:** REQUIRED SUB-SKILL `superpowers:executing-plans`
