"""Tests for core/types.py — shared data types and exceptions."""

from __future__ import annotations

import pytest

from core.types import (
    ReviewSystemError,
    SecurityBlockedError,
    ShieldFinding,
    ShieldResult,
    SyncError,
    SyncResult,
    SyncReport,
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

    def test_shield_finding_with_valid_spans(self) -> None:
        finding = ShieldFinding(
            category="pii",
            severity="medium",
            description="PII detected",
            span_start=10,
            span_end=20,
        )
        assert finding.span_start == 10
        assert finding.span_end == 20

    def test_shield_finding_rejects_single_span_value(self) -> None:
        with pytest.raises(ValueError, match="Both span_start and span_end must be set"):
            ShieldFinding(category="x", severity="low", description="x", span_start=10)
        with pytest.raises(ValueError, match="Both span_start and span_end must be set"):
            ShieldFinding(category="x", severity="low", description="x", span_end=20)

    def test_shield_finding_rejects_negative_spans(self) -> None:
        with pytest.raises(ValueError, match="Span indices must be non-negative"):
            ShieldFinding(category="x", severity="low", description="x", span_start=-1, span_end=10)

    def test_shield_finding_rejects_invalid_range(self) -> None:
        with pytest.raises(ValueError, match="span_start.*cannot be greater than span_end"):
            ShieldFinding(category="x", severity="low", description="x", span_start=20, span_end=10)

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
        assert result.errors == ()


class TestSyncReport:
    """SyncReport validates consistency."""

    def test_valid_sync_report(self) -> None:
        report = SyncReport(total_files=10, synced_count=7, skipped_count=3)
        assert report.total_files == 10
        assert report.synced_count == 7
        assert report.skipped_count == 3

    def test_rejects_negative_counts(self) -> None:
        with pytest.raises(ValueError, match="must be non-negative"):
            SyncReport(total_files=-1, synced_count=0, skipped_count=0)

    def test_rejects_counts_exceeding_total(self) -> None:
        with pytest.raises(ValueError, match="exceeds total_files"):
            SyncReport(total_files=10, synced_count=8, skipped_count=3)


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
