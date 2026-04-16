"""Task message types and enums for sub-agent communication."""

from __future__ import annotations

from collections.abc import Sequence
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
    completed_at: datetime | None = None
    target_files: Sequence[Path] = field(default_factory=tuple)
    constraints: Sequence[str] = field(default_factory=tuple)
    depends_on: Sequence[str] = field(default_factory=tuple)
    response: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_files", tuple(self.target_files))
        object.__setattr__(self, "constraints", tuple(self.constraints))
        object.__setattr__(self, "depends_on", tuple(self.depends_on))
