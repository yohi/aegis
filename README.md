# 🛡️ Aegis (イージス)

**自律型マルチエージェント LLM レビューアーキテクチャ**

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg?style=flat-square&logo=python)
![Architecture](https://img.shields.io/badge/Architecture-Microkernel-success.svg?style=flat-square)
![Security](https://img.shields.io/badge/Security-Model_Armor-red.svg?style=flat-square&logo=googlecloud)
![AI](https://img.shields.io/badge/AI-Gemini_3.1_Pro_%7C_Claude_4.6-purple.svg?style=flat-square)

> **属人的なコードレビューの終焉。**  
> 設計の不整合から潜在的な脆弱性まで、マルチエージェントが自律的に検知・修正・報告する次世代の開発ワークフロー。

## 📖 概要 (Overview)

**Aegis（イージス）** は、ソフトウェア開発におけるコードおよびドキュメントのレビュープロセスを極限まで自律化する、実運用指向の統合アーキテクチャです。

複数の独立したリポジトリに点在する設計仕様を **NotebookLM Enterprise** へと自動集約して単一の信頼できる情報源（SSOT: Single Source of Truth）を構築します。また、Cursor IDEのファイルベース通信プロトコルを介して複数のLLMサブエージェントを連携（オーケストレーション）し、人間は最終的な「承認（Approve）」のみを行う **Human-in-the-loop** モデルを実現します。

## ✨ 主な機能 (Key Capabilities)

- 🧠 **コンテキストを理解した推論 (Context-Aware Inference)**  
  Gemini 3.1 Pro の DeepThink などを活用し、ドメインロジックとコード実装間の深い意味的レビューを実行します。
- 🤖 **エージェント・オーケストレーション (Agentic Orchestration)**  
  Cursor IDE 上で稼働する特化型サブエージェント群による、自律的なコード修正と検証ループを構築。エージェント間の通信は、競合を防ぐ堅牢なファイルベース通信（Write-then-Renameパターン）で行われます。
- 🛡️ **ゼロトラスト・ガードレール (Zero-Trust Guardrails)**  
  Google Cloud Model Armor をミドルウェアとして組み込み、プロンプトインジェクションの防止とPII（個人情報）などのデータ漏洩を防ぐ強固な防壁を提供します。
- ⚙️ **隔離された実行環境 (Isolated Execution)**  
  Devcontainer（開発コンテナ）を利用し、完全に隔離された安全なテスト・静的解析環境の利用を強制します。

## 🏗 アーキテクチャ (Architecture)

Aegisは **プロトコル・ファースト設計によるプラグインベースのマイクロカーネルアーキテクチャ** を採用しています。コアロジック（`src/core`）は抽象化されたプロトコル（`src/core/protocols.py`）にのみ依存し、具象クラスや各種プラグイン実装から完全に切り離されています。

### パイプラインとコンポーネント
- **同期パイプライン (Sync Pipeline)**: Google DriveAPI経由でローカルコードベースをアップロードし、NotebookLMに連携することでSSOTを構築します。また、`gwscli`を用いた人間可読なレビューレポートの自動生成（Google Docs/Sheets）も行います。
- **Cursor Rules Engine**: 構造化されたYAML定義（`src/plugins/rules/templates/`）から、Cursor向けのコンテキスト対応ガードレールである `.mdc` ルールファイルを動的に生成します。
- **非同期実行 (Asynchronous Execution)**: `asyncio` を極限まで活用。I/Oバウンドな処理は別スレッドにオフロードし、並行タスクは `asyncio.TaskGroup` 等で安全かつ高速に管理されます。

> より詳細なシステム仕様、通信プロトコル、セキュリティ設計については、**[SPEC.md](SPEC.md)** および **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** を参照してください。

## ⚙️ 環境設定 (Configuration)

本システムは環境変数（または `.env` ファイル）による設定をサポートしています。主要な設定項目は以下の通りです：

| 環境変数 | 説明 | デフォルト値 |
| --- | --- | --- |
| `LLM_REVIEW_SYNC_NOTEBOOK_ID` | 同期先となる NotebookLM の ID | (必須) |
| `LLM_REVIEW_SYNC_DRIVE_FOLDER_ID` | コードベースをアップロードする Google Drive のフォルダ ID | (必須) |
| `LLM_SECURITY_GCP_PROJECT_ID` | Model Armor 等を利用する GCP プロジェクト ID | (必須) |
| `LLM_SECURITY_LOCATION` | GCP リソースのロケーション | `us-central1` |
| `LLM_SECURITY_MODEL_ARMOR_TEMPLATE_ID` | 適用する Model Armor テンプレート ID | `default-shield` |

## 🚀 クイックスタート (Quick Start)

1. **DevContainer で開く** (VS Code または Cursor を推奨)
2. コンテナ起動時に `post-create.sh` が実行され、環境が自動的にセットアップされます。
3. 依存関係の変更時や、自動セットアップがスキップされた場合は、手動で以下のコマンドを実行してください：
   ```bash
   pip install -e ".[dev]"
   ```

### For Humans (推奨)

> [!TIP]
> **人間は設定を打ち間違えることがあります。** このプロジェクトのインストールと設定は、AIエージェント（Claude Code / Gemini CLI / Cursor 等）に丸投げすることを強く推奨します。

### AIエージェントによるインストール

以下のプロンプトをコピーしてエージェントに渡してください：

```text
Install and configure Aegis by following the instructions here:
https://github.com/yohi/aegis/blob/master/README.md
```

<details>
<summary><b>For Agents (AIエージェント向け手順)</b></summary>

あなたがターミナル操作可能なAIエージェントであるなら、以下の手順でインストールとセットアップを自律的に遂行してください：

1.  **[ ] 依存関係の解決:**
    *   `pip` を使用して、開発用依存関係をインストールしてください。
    *   `pip install -e ".[dev]"`
2.  **[ ] 環境設定:**
    *   必要な環境変数（`LLM_REVIEW_SYNC_NOTEBOOK_ID`, `LLM_SECURITY_GCP_PROJECT_ID` など）をヒアリングまたは構成から推測し、`.env` ファイルを作成して設定してください。
3.  **[ ] 動作確認:**
    *   テストを実行して、環境が正しく構築されているか確認してください。
    *   `pytest`
4.  **[ ] 静的解析と型チェック:**
    *   Linterおよび型チェックが通過することを確認してください。
    *   `ruff check src/ tests/`
    *   `mypy src/`
5.  **[ ] エージェントへの指示の追加 (Personal/Global):**
    *   `AGENTS.md` や `docs/ARCHITECTURE.md` の内容を、あなたのエージェントの**グローバル設定**（`~/.gemini/GEMINI.md`, `~/.clauderules`, または Cursor の `Rules for AI`）に追加・反映させてください。
    *   **注記**: チーム共有のプロジェクトルート（`.cursorrules` 等）に追記すると、他のメンバーのエージェントの挙動にも影響するため、個人のグローバル設定に配置することを強く推奨します。
</details>

## 💻 開発ガイド (Development)

本プロジェクトは **Python 3.11以上** をターゲットとしています。各種ツールによる厳格な品質管理を行っています。

```bash
# テストの実行 (pytest, pytest-asyncio)
# 外部GCPサービスに依存するテストは `integration` マーカーで分離されています
pytest

# リンターによる静的解析 (Ruff)
ruff check src/ tests/

# 型チェック (mypy)
mypy src/
```

### ロギングと監査 (Logging & Auditing)
構造化ロギングには `structlog` を使用しています。状態遷移（例: `pending` -> `in_progress`）は重要な監査イベントとして記録し、ログには必ず `request_id` や `actor` （実行主体）を含めるルールとなっています。

## 📄 ライセンス (License)

詳細は [LICENSE](LICENSE) ファイルをご参照ください。
