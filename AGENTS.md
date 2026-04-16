# Aegis

Autonomous multi-agent LLM code review system.

## Toolchain & Context
- **Runtime**: Python 3.11+ via DevContainer.
- **Package Manager**: `uv`. Use `uv sync` for setup.
- **Important**: If `uv run` fails with build errors, use `uv run --no-project --with <deps>` to bypass package isolation.

## Key Commands
- **Test**: `PYTHONPATH=src uv run pytest` (Primary validation)
- **Lint**: `uv run ruff check src/ tests/` (Use `--fix` for auto-formatting)
- **Type Check**: `uv run mypy src/` (Requires `types-PyYAML`, `pydantic-settings`)

## Domain Concepts
- **SecurityShield**: Interface for input/output sanitization.
- **ReviewResult**: Structured output containing findings and summary.
- **Orchestrator**: Core component coordinating the pipeline.

## Guidelines
- **Logic**: Favor composition and protocols over inheritance. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
- **Security**: Always log blocked inputs as `logger.error`. See [docs/SECURITY.md](docs/SECURITY.md).
- **Verification**: Never claim success without running tests. Evidence-based completion only.
