"""Write review results to Google Workspace via gws."""

from __future__ import annotations

import asyncio
import json

import structlog

from core.types import ReviewResult

logger = structlog.get_logger()


class ReportWriter:
    """Write review results to Google Workspace via gws."""

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
        stdout = await self._run_gws(
            "docs",
            "create",
            "--title",
            f"Review Report: {result.request_id}",
            "--content",
            report_content,
            "--template-id",
            template_id,
            correlation_id=result.request_id,
        )

        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError as exc:
            # Sanitize output before logging to prevent leaking sensitive data
            sanitized = stdout[:100] + "..." if len(stdout) > 100 else stdout
            logger.error("Failed to parse gws output", output_summary=sanitized, error=str(exc), correlation_id=result.request_id)
            raise RuntimeError(f"Invalid JSON from gws: {exc}") from exc

        doc_id = parsed.get("id")
        if not doc_id:
            sanitized = stdout[:100] + "..." if len(stdout) > 100 else stdout
            logger.error("gws output missing 'id'", output_summary=sanitized, correlation_id=result.request_id)
            raise ValueError("gws create failed: output missing 'id'")

        logger.info("Report written to Google Docs", doc_id=doc_id, correlation_id=result.request_id)
        return str(doc_id)

    async def append_metrics_sheet(self, result: ReviewResult, sheet_id: str) -> None:
        """Append metrics row to Google Sheets."""
        self._validate_arg(sheet_id)
        self._validate_arg(result.request_id)
        row_data = json.dumps(
            {
                "request_id": result.request_id,
                "status": result.status,
                "finding_count": len(result.findings),
            }
        )
        await self._run_gws(
            "sheets",
            "append",
            "--spreadsheet-id",
            sheet_id,
            "--data",
            row_data,
            correlation_id=result.request_id,
        )
        logger.info("Metrics appended to sheet", sheet_id=sheet_id, correlation_id=result.request_id)

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

    async def _run_gws(self, *args: str, correlation_id: str, timeout: float = 30.0) -> str:
        """Run gws command asynchronously with mandatory correlation_id and timeout handling."""
        try:
            # Note: Static analysis requires literal string here for security
            proc = await asyncio.create_subprocess_exec("gws", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)  # nosec B603 # nosemgrep # noqa: E501
        except FileNotFoundError as exc:
            logger.error("gws not found", error=str(exc), correlation_id=correlation_id)
            raise RuntimeError("gws is not installed or not in PATH") from exc

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError:
            proc.kill()
            await proc.communicate()  # Clean up process
            logger.error(
                "gws timed out",
                timeout=timeout,
                correlation_id=correlation_id,
            )
            raise TimeoutError(f"gws timed out after {timeout}s") from None

        if proc.returncode != 0:
            logger.error(
                "gws failed",
                exit_code=proc.returncode,
                correlation_id=correlation_id,
            )
            raise RuntimeError(f"gws failed (exit {proc.returncode})")

        return stdout.decode()
