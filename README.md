<<<<<<< HEAD
# 🛡️ Aegis 
**Autonomous Multi-Agent LLM Review Architecture**

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg?style=flat-square&logo=python)
![Architecture](https://img.shields.io/badge/Architecture-Microkernel-success.svg?style=flat-square)
![Security](https://img.shields.io/badge/Security-Model_Armor-red.svg?style=flat-square&logo=googlecloud)
![AI](https://img.shields.io/badge/AI-Gemini_3.1_Pro_%7C_Claude_4.6-purple.svg?style=flat-square)

> **属人的なコードレビューの終焉。** > 設計の不整合から潜在的な脆弱性まで、マルチエージェントが自律的に検知・修正・報告する次世代の開発ワークフロー。

## 📖 Overview

**Aegis（イージス）** は、ソフトウェア開発におけるコードおよびドキュメントのレビュープロセスを極限まで自律化する、実運用指向の統合アーキテクチャです。

複数の独立したリポジトリに点在する設計仕様を **NotebookLM Enterprise** へと自動集約して単一の信頼できる情報源（SSOT）を構築。Cursor IDEのファイルベース通信プロトコルを介して複数のLLMサブエージェントをオーケストレーションし、人間は最終的な「承認（Approve）」のみを行う **Human-in-the-loop** モデルを実現します。

### ✨ Key Capabilities
- 🧠 **Context-Aware Inference**: Gemini 3.1 ProのDeepThinkを活用した、ドメインロジックとコード間の深い意味的レビュー。
- 🤖 **Agentic Orchestration**: Cursor IDE上で稼働する特化型サブエージェント群による、自律的なコード修正と検証ループ。
- 🛡️ **Zero-Trust Guardrails**: Google Cloud Model Armorを組み込んだ、プロンプトインジェクションとデータ漏洩を防ぐ堅牢な防壁。
- ⚙️ **Isolated Execution**: Devcontainerによる、完全に隔離された安全なテスト・静的解析環境の強制。

**Architecture Pattern**: プラグインベース・マイクロカーネルアーキテクチャ（Protocol-first design）
=======
# LLM Review System

Autonomous, multi-agent LLM code review system powered by NotebookLM Enterprise and Google Cloud Model Armor.

## Architecture

Plugin-based microkernel architecture with Protocol-first design.
All plugins implement `core/protocols.py` Protocols — no concrete class dependencies.

## Quick Start

1. Open in DevContainer (VS Code / Cursor)
2. Environment is auto-configured via `post-create.sh`
3. Run: `pip install -e ".[dev]"`

## Development

```bash
# Run tests
pytest

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## License

See [LICENSE](LICENSE).
>>>>>>> feat/01-project-foundation
