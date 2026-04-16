"""Shared data types and exception hierarchy for the review system."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence


# --- Exceptions ---


class ReviewSystemError(Exception):
    """Base error. All custom exceptions derive from this."""


class SecurityBlockedError(ReviewSystemError):
    """Model Armor blocked the content."""


class SyncError(ReviewSystemError):
    """Google Drive / NotebookLM sync error."""


class AgentTimeoutError(ReviewSystemError):
    """Sub-agent timed out."""


class TaskDeadlockError(ReviewSystemError):
    """Circular dependency detected between sub-agents."""


# --- Data Types ---


@dataclass(frozen=True)
class ShieldFinding:
    """Details of a detected threat."""

    category: str
    severity: str
    description: str
    span_start: int | None = None
    span_end: int | None = None


@dataclass(frozen=True)
class ShieldResult:
    """Shield processing result."""

    allowed: bool
    sanitized_content: str
    findings: Sequence[ShieldFinding] = field(default_factory=tuple)
    raw_response: Any | None = None


@dataclass(frozen=True)
class SourceInfo:
    """Information about a source in NotebookLM."""

    source_id: str
    name: str
    drive_file_id: str


@dataclass(frozen=True)
class SyncResult:
    """Sync operation result."""

    synced_count: int
    errors: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class SyncReport:
    """Full sync report for a repository."""

    total_files: int
    synced_count: int
    skipped_count: int
    errors: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class Finding:
    """A single review finding."""

    file_path: Path
    line: int
    severity: str
    message: str
    rule_id: str | None = None


@dataclass(frozen=True)
class ReviewRequest:
    """Input to a review pipeline."""

    request_id: str
    repo_path: Path
    target_files: Sequence[Path] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReviewResult:
    """Output from a review pipeline."""

    request_id: str
    status: str
    findings: Sequence[Finding] = field(default_factory=tuple)
    summary: str = ""
    error_details: str | None = None

    def with_redacted_summary(self) -> ReviewResult:
        """Return a copy with redacted summary."""
        return dataclasses.replace(self, summary="[REDACTED]")


