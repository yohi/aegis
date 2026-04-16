"""Tests for plugins/agents/protocol.py — task message types."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest


class TestTaskMessage:
    """Test TaskMessage dataclass."""

    def test_create_task_message(self) -> None:
        from plugins.agents.protocol import (
            AgentRole,
            Priority,
            TaskMessage,
            TaskStatus,
        )

        msg = TaskMessage(
            task_id="TASK-20260416-001",
            sender=AgentRole.TECH_LEAD,
            receiver=AgentRole.LINTING,
            status=TaskStatus.PENDING,
            priority=Priority.HIGH,
            created_at=datetime(2026, 4, 16, 2, 40, 0, tzinfo=timezone.utc),
            objective="Analyze files for linting violations",
            target_files=[Path("src/core/orchestrator.py")],
            constraints=["Use ruff for Python linting"],
            depends_on=[],
        )
        assert msg.task_id == "TASK-20260416-001"
        assert msg.sender == AgentRole.TECH_LEAD
        assert msg.response is None

    def test_task_message_is_immutable(self) -> None:
        from plugins.agents.protocol import (
            AgentRole,
            Priority,
            TaskMessage,
            TaskStatus,
        )

        msg = TaskMessage(
            task_id="TASK-20260416-001",
            sender=AgentRole.TECH_LEAD,
            receiver=AgentRole.LINTING,
            status=TaskStatus.PENDING,
            priority=Priority.HIGH,
            created_at=datetime.now(tz=timezone.utc),
            objective="Test",
            target_files=[],
            constraints=[],
            depends_on=[],
        )
        with pytest.raises(AttributeError):
            msg.task_id = "changed"  # type: ignore[misc]


class TestAgentRole:
    """Test AgentRole enum values."""

    def test_agent_roles_exist(self) -> None:
        from plugins.agents.protocol import AgentRole

        assert AgentRole.TECH_LEAD == "techlead"
        assert AgentRole.LINTING == "linting"
        assert AgentRole.SECURITY == "security"
        assert AgentRole.VERIFIER == "verifier"


class TestTaskStatus:
    """Test TaskStatus enum values."""

    def test_statuses_exist(self) -> None:
        from plugins.agents.protocol import TaskStatus

        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.IN_PROGRESS == "in_progress"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
