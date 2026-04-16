"""Task message types and enums for sub-agent communication."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRole(StrEnum):
    TECH_LEAD = "techlead"
    LINTING = "linting"
    SECURITY = "security"
    VERIFIER = "verifier"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class TaskMessage:
    """Immutable task message for file-based inter-agent communication."""

    task_id: str
    sender: AgentRole
    receiver: AgentRole
    status: TaskStatus
    priority: Priority
    created_at: datetime
    objective: str
    target_files: list[Path] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    response: str | None = None
