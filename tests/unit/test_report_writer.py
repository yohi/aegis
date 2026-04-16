"""Tests for plugins/sync/report_writer.py."""

from __future__ import annotations

import pytest

from core.types import ReviewResult
from plugins.sync.report_writer import ReportWriter


class TestReportWriter:
    """Test ReportWriter formatting and validation."""

    def test_validate_arg(self) -> None:
        writer = ReportWriter()
        assert writer._validate_arg("valid") == "valid"
        with pytest.raises(ValueError, match="Invalid argument"):
            writer._validate_arg("--invalid")

    def test_format_report(self) -> None:
        writer = ReportWriter()
        result = ReviewResult(
            request_id="req-001",
            status="completed",
            findings=[],
            summary="Test summary",
        )
        report = writer._format_report(result)
        assert "req-001" in report
        assert "Status: completed" in report
        assert "Test summary" in report
        assert "Findings: 0" in report
