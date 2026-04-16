# Aegis Autonomous Review System — Specification

## 1. System Overview
Aegis is an autonomous, multi-agent LLM code review system powered by NotebookLM Enterprise and Google Cloud Model Armor. It uses a plugin-based microkernel architecture with a Protocol-first design, ensuring that each module is independently testable and isolated from concrete dependencies.

## 2. Core Architecture
- **Protocol-First**: Core logic (`src/core`) only depends on abstract protocols (`src/core/protocols.py`), completely decoupled from concrete plugin implementations.
- **Security Middleware**: Integrates Google Cloud Model Armor to shield all interactions. It prevents prompt injection and PII leaks on input (`shield_input`), and redacts sensitive data from LLM responses on output (`shield_output`).
- **Asynchronous Execution**: Deeply utilizes Python's `asyncio`. Blocking I/O is offloaded via `asyncio.to_thread`, and parallel tasks (like file shielding) are robustly managed with `asyncio.TaskGroup` and semaphores.

## 3. Sync Pipeline (NotebookLM + Google Drive + gwscli)
- Creates a Single Source of Truth (SSOT) by synchronizing the local codebase to NotebookLM.
- **DriveClient**: Uploads source code to Google Drive and links those files into the target NotebookLM.
- **ReportWriter**: Asynchronously shells out to `gwscli` to write human-readable review reports to Google Docs and operational metrics to Google Sheets.
- Pre-filtering mechanisms ensure that oversized or binary files are skipped efficiently.

## 4. Cursor Rules Engine (.mdc)
- Dynamically generates Cursor `.mdc` rule files from YAML templates (`src/plugins/rules/templates/`).
- Enforces progressive disclosure by applying rules only to relevant files (via strict glob matching).
- Maintains high standards by converting structured, positively-framed YAML definitions into context-aware IDE guardrails.

## 5. Sub-Agent Orchestration
- **Communication Protocol**: Agents communicate exclusively through atomic file operations (the Write-then-Rename pattern) within a dedicated `.review/tasks` workspace, preventing race conditions.
- **Task Messages**: Tasks are represented as Markdown files with structured YAML frontmatter (`task_id`, `sender`, `receiver`, `status`, etc.).
- **Identifiers & Concurrency**: Task file names use a robust combination of dates and UUIDs (e.g., `TASK-YYYYMMDD-<uuid>-<sender>-to-<receiver>.md`). This simplifies concurrent operations and avoids ID collisions without relying on complex file locks.

## 6. Defensive Engineering & Validation
- **Exception Hierarchy**: All errors inherit from a base `ReviewSystemError` to allow for consistent error boundaries and logging.
- **Strict Data Types**: Heavily utilizes `pydantic` settings for configuration and fully immutable `dataclasses` (with `Sequence` and `__post_init__` checks) for internal data structures.
- **Built-in Defenses**: Includes path traversal checks on file operations and strict argument validation to prevent flag injection in subprocess calls.
