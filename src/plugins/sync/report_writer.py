"""Write review results to Google Workspace via gwscli."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from src.core.types import ReviewResult

logger = logging.getLogger(__name__)


class ReportWriter:
    """Write review results to Google Workspace via gwscli."""

    def _validate_arg(self, arg: str) -> str:
        """Validate argument to prevent flag injection."""
        if arg.startswith("-"):
            raise ValueError(f"Invalid argument (potential flag injection): {arg}")
        return arg

    async def write_docs_report(self, result: ReviewResult, template_id: str) -> str:
        """Output review report to Google Docs. Return doc_id."""
        self._validate_arg(result.request_id)
        self._validate_arg(template_id)

        report_content = self._format_report(result)
        stdout = await self._run_gwscli(
            "docs",
            "create",
            "--title",
            f"Review Report: {result.request_id}",
            "--content",
            report_content,
        )
        doc_id = json.loads(stdout).get("id", "")
        logger.info("Report written to Google Docs", doc_id=doc_id)
        return doc_id

    async def append_metrics_sheet(self, result: ReviewResult, sheet_id: str) -> None:
        """Append metrics row to Google Sheets."""
        self._validate_arg(sheet_id)
        row_data = json.dumps(
            {
                "request_id": result.request_id,
                "status": result.status,
                "finding_count": len(result.findings),
            }
        )
        await self._run_gwscli(
            "sheets",
            "append",
            "--spreadsheet-id",
            sheet_id,
            "--data",
            row_data,
        )
        logger.info("Metrics appended to sheet", sheet_id=sheet_id)

    def _format_report(self, result: ReviewResult) -> str:
        """Format ReviewResult as a human-readable report."""
        lines = [
            f"# Review Report: {result.request_id}",
            f"Status: {result.status}",
            f"Findings: {len(result.findings)}",
            "",
            "## Summary",
            result.summary or "(No summary)",
            "",
            "## Findings",
        ]
        for finding in result.findings:
            lines.append(
                f"- [{finding.severity}] {finding.file_path}:{finding.line} — {finding.message}"
            )
        return "\n".join(lines)

    async def _run_gwscli(self, *args: str) -> str:
        """Run gwscli command asynchronously."""
        # Note: Static analysis requires literal string here for security (Bandit B603)
        proc = await asyncio.create_subprocess_exec(
            "gwscli",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"gwscli failed (exit {proc.returncode}): {stderr.decode()}")
        return stdout.decode()
