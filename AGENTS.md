# Aegis

Autonomous multi-agent LLM code review system.

## ⚠️ Critical Rules (MUST)
- **Environment**: You MUST use **DevContainer** for all development and test execution.
- **Verification**: You MUST NOT claim success or fix completion without running tests. Evidence-based validation is mandatory.
- **Security**: You MUST log blocked inputs as `logger.error` to ensure audit visibility. If a specific task requires suppressing this (e.g., for noise reduction during bulk debugging), you MUST ask the user for confirmation first. See [docs/SECURITY.md](docs/SECURITY.md).

## 🛠️ Standard Procedures (SHOULD)
- **Package Manager**: Use `uv`. Run `uv sync` for environment setup.
- **Toolchain**: Prefer `uv run --no-project --with <deps>` if standard `uv run` fails due to package isolation issues.
- **Linting**: Run `uv run ruff check src/ tests/` and use `--fix` for auto-formatting.
- **Architecture**: Favor composition and protocols over inheritance. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 💡 Preferred Conventions (MAY)
- **Domain Language**: Use terms like `SecurityShield`, `ReviewResult`, and `Orchestrator` to align with the codebase.
- **Type Checking**: Run `uv run mypy src/` to verify type safety (requires `types-PyYAML`).
