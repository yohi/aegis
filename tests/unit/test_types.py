"""Tests for core/types.py — shared data types and exceptions."""

from __future__ import annotations

import pytest

from core.types import (
    ReviewRequest,
    ReviewResult,
    ReviewSystemError,
    SecurityBlockedError,
    ShieldFinding,
    ShieldResult,
    SourceInfo,
    SyncError,
    SyncResult,
    AgentTimeoutError,
    TaskDeadlockError,
)


class TestShieldFinding:
    """ShieldFinding is frozen dataclass."""

    def test_create_shield_finding(self) -> None:
        finding = ShieldFinding(
            category="prompt_injection",
            severity="high",
            description="Prompt injection detected",
        )
        assert finding.category == "prompt_injection"
        assert finding.severity == "high"
        assert finding.span_start is None
        assert finding.span_end is None

    def test_shield_finding_is_immutable(self) -> None:
        finding = ShieldFinding(category="pii", severity="medium", description="PII detected")
        with pytest.raises(AttributeError):
            finding.category = "malicious"


class TestShieldResult:
    """ShieldResult is frozen dataclass."""

    def test_create_shield_result_allowed(self) -> None:
        result = ShieldResult(
            allowed=True,
            sanitized_content="safe content",
            findings=[],
            raw_response=None,
        )
        assert result.allowed is True
        assert result.sanitized_content == "safe content"

    def test_create_shield_result_blocked(self) -> None:
        finding = ShieldFinding(category="malicious", severity="critical", description="Malware")
        result = ShieldResult(
            allowed=False,
            sanitized_content="",
            findings=[finding],
            raw_response=None,
        )
        assert result.allowed is False
        assert len(result.findings) == 1


class TestSyncResult:
    """SyncResult tracks sync operations."""

    def test_create_sync_result(self) -> None:
        result = SyncResult(synced_count=5, errors=[])
        assert result.synced_count == 5
        assert result.errors == []


class TestExceptionHierarchy:
    """All custom exceptions derive from ReviewSystemError."""

    def test_security_blocked_is_review_error(self) -> None:
        assert issubclass(SecurityBlockedError, ReviewSystemError)

    def test_sync_error_is_review_error(self) -> None:
        assert issubclass(SyncError, ReviewSystemError)

    def test_agent_timeout_is_review_error(self) -> None:
        assert issubclass(AgentTimeoutError, ReviewSystemError)

    def test_task_deadlock_is_review_error(self) -> None:
        assert issubclass(TaskDeadlockError, ReviewSystemError)

    def test_catch_all_with_base_class(self) -> None:
        with pytest.raises(ReviewSystemError):
            raise SecurityBlockedError("blocked")
