"""Tests for plugins/agents/watcher.py."""

from __future__ import annotations

from pathlib import Path

import pytest


class TestTaskWatcher:
    """Test task completion watching."""

    @pytest.fixture
    def task_dir(self, tmp_path: Path) -> Path:
        d = tmp_path / ".review" / "tasks"
        d.mkdir(parents=True)
        return d

    def _write_task_file(self, task_dir: Path, task_id: str, status: str) -> None:
        content = f"""---
task_id: "{task_id}"
sender: "linting"
receiver: "techlead"
status: "{status}"
priority: "high"
created_at: "2026-04-16T02:40:00Z"
completed_at: null
depends_on: []
---

## Response
Test findings here.
"""
        (task_dir / f"{task_id}-linting-to-techlead.md").write_text(content)

    @pytest.mark.asyncio
    async def test_collect_completed_results(self, task_dir: Path) -> None:
        from plugins.agents.watcher import TaskWatcher

        self._write_task_file(task_dir, "TASK-20260416-001", "completed")

        watcher = TaskWatcher(task_dir, poll_interval=0.1)
        results = await watcher.collect_results(["TASK-20260416-001"])
        assert "TASK-20260416-001" in results

    @pytest.mark.asyncio
    async def test_timeout_when_task_not_completed(self, task_dir: Path) -> None:
        from plugins.agents.watcher import TaskWatcher
        from core.types import AgentTimeoutError

        self._write_task_file(task_dir, "TASK-20260416-001", "pending")

        watcher = TaskWatcher(task_dir, poll_interval=0.05)
        with pytest.raises(AgentTimeoutError):
            await watcher.wait_for_completion(
                ["TASK-20260416-001"], timeout=0.1
            )

    @pytest.mark.asyncio
    async def test_parse_with_html_comments_and_completed_at(self, task_dir: Path) -> None:
        from plugins.agents.watcher import TaskWatcher
        from datetime import datetime

        task_id = "TASK-COMPLEX-001"
        completed_at_str = "2026-04-17T10:00:00+00:00"
        content = f"""---
task_id: "{task_id}"
sender: "security"
receiver: "techlead"
status: "completed"
priority: "medium"
created_at: "2026-04-17T09:00:00+00:00"
completed_at: "{completed_at_str}"
depends_on: []
---

## Objective
Test complex parsing

## Target Files
- `src/main.py`

## Constraints
- No external APIs

## Response
<!-- some comment -->
<!-- another comment -->
Actual result content.
"""
        (task_dir / f"{task_id}.md").write_text(content)

        watcher = TaskWatcher(task_dir)
        results = await watcher.collect_results([task_id])
        msg = results[task_id]

        assert msg.response == "Actual result content."
        assert msg.completed_at == datetime.fromisoformat(completed_at_str)
        assert msg.objective == "Test complex parsing"
        assert Path("src/main.py") in msg.target_files
        assert "No external APIs" in msg.constraints

    @pytest.mark.asyncio
    async def test_skip_invalid_enum_values(self, task_dir: Path) -> None:
        from plugins.agents.watcher import TaskWatcher

        task_id = "TASK-INVALID-ENUM"
        content = f"""---
task_id: "{task_id}"
sender: "invalid-role"
receiver: "techlead"
status: "completed"
priority: "medium"
created_at: "2026-04-17T09:00:00+00:00"
---
## Response
Body
"""
        (task_dir / f"{task_id}.md").write_text(content)

        watcher = TaskWatcher(task_dir)
        results = await watcher.collect_results([task_id])
        assert task_id not in results
