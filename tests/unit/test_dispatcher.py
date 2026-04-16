"""Tests for plugins/agents/dispatcher.py."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from plugins.agents.protocol import AgentRole, Priority, TaskMessage, TaskStatus


class TestTaskDispatcher:
    """Test task file generation and atomic writing."""

    @pytest.fixture
    def workspace(self, tmp_path: Path) -> Path:
        return tmp_path

    @pytest.mark.asyncio
    async def test_dispatch_creates_task_file(self, workspace: Path) -> None:
        from plugins.agents.dispatcher import TaskDispatcher

        dispatcher = TaskDispatcher(workspace)
        msg = TaskMessage(
            task_id="TASK-20260416-001",
            sender=AgentRole.TECH_LEAD,
            receiver=AgentRole.LINTING,
            status=TaskStatus.PENDING,
            priority=Priority.HIGH,
            created_at=datetime(2026, 4, 16, 2, 40, 0, tzinfo=timezone.utc),
            objective="Analyze files",
            target_files=[Path("src/core/orchestrator.py")],
            constraints=["Use ruff"],
            depends_on=[],
        )
        path = await dispatcher.dispatch(msg)
        assert path.exists()
        assert path.suffix == ".md"
        assert "techlead" in path.name
        assert "linting" in path.name

    @pytest.mark.asyncio
    async def test_dispatch_file_contains_frontmatter(self, workspace: Path) -> None:
        from plugins.agents.dispatcher import TaskDispatcher

        dispatcher = TaskDispatcher(workspace)
        msg = TaskMessage(
            task_id="TASK-20260416-001",
            sender=AgentRole.TECH_LEAD,
            receiver=AgentRole.LINTING,
            status=TaskStatus.PENDING,
            priority=Priority.HIGH,
            created_at=datetime(2026, 4, 16, 2, 40, 0, tzinfo=timezone.utc),
            objective="Analyze files",
            target_files=[],
            constraints=[],
            depends_on=[],
        )
        path = await dispatcher.dispatch(msg)
        content = path.read_text()
        assert "task_id:" in content
        assert "TASK-20260416-001" in content
        assert 'status: "pending"' in content

    @pytest.mark.asyncio
    async def test_no_tmp_files_after_dispatch(self, workspace: Path) -> None:
        from plugins.agents.dispatcher import TaskDispatcher

        dispatcher = TaskDispatcher(workspace)
        msg = TaskMessage(
            task_id="TASK-20260416-001",
            sender=AgentRole.TECH_LEAD,
            receiver=AgentRole.SECURITY,
            status=TaskStatus.PENDING,
            priority=Priority.MEDIUM,
            created_at=datetime(2026, 4, 16, 2, 40, 0, tzinfo=timezone.utc),
            objective="Security scan",
            target_files=[],
            constraints=[],
            depends_on=[],
        )
        await dispatcher.dispatch(msg)
        task_dir = workspace / ".review" / "tasks"
        tmp_files = list(task_dir.glob("*.tmp"))
        assert len(tmp_files) == 0

    @pytest.mark.asyncio
    async def test_sequential_ids_increment(self, workspace: Path) -> None:
        from plugins.agents.dispatcher import TaskDispatcher

        dispatcher = TaskDispatcher(workspace)
        for i in range(3):
            msg = TaskMessage(
                task_id=f"TASK-20260416-{i+1:03d}",
                sender=AgentRole.TECH_LEAD,
                receiver=AgentRole.LINTING,
                status=TaskStatus.PENDING,
                priority=Priority.HIGH,
                created_at=datetime(2026, 4, 16, 2, 40, 0, tzinfo=timezone.utc),
                objective=f"Task {i+1}",
                target_files=[],
                constraints=[],
                depends_on=[],
            )
            await dispatcher.dispatch(msg)

        task_dir = workspace / ".review" / "tasks"
        md_files = sorted(task_dir.glob("*.md"))
        assert len(md_files) == 3
