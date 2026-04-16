"""Write review results to Google Workspace via gwscli."""

from __future__ import annotations

import asyncio
import json

import structlog

from core.types import ReviewResult

logger = structlog.get_logger()


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
            "--template-id",
            template_id,
        )

        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse gwscli output", output=stdout, error=str(exc))
            raise RuntimeError(f"Invalid JSON from gwscli: {exc}") from exc

        doc_id = parsed.get("id")
        if not doc_id:
            logger.error("gwscli output missing 'id'", output=stdout)
            raise ValueError("gwscli create failed: output missing 'id'")

        logger.info("Report written to Google Docs", doc_id=doc_id)
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

    async def _run_gwscli(self, *args: str, timeout: float = 30.0) -> str:
        """Run gwscli command asynchronously with timeout and robust error handling."""
        try:
            # Note: Static analysis requires literal string here for security
            proc = await asyncio.create_subprocess_exec("gwscli", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)  # nosec B603 # nosemgrep # noqa: E501
        except FileNotFoundError as exc:
            logger.error("gwscli not found", error=str(exc))
            raise RuntimeError("gwscli is not installed or not in PATH") from exc

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError:
            proc.kill()
            stdout, stderr = await proc.communicate()
            logger.error(
                "gwscli timed out",
                timeout=timeout,
                stdout=stdout.decode(),
                stderr=stderr.decode(),
            )
            raise TimeoutError(f"gwscli timed out after {timeout}s") from None

        if proc.returncode != 0:
            err_msg = stderr.decode()
            logger.error("gwscli failed", exit_code=proc.returncode, stderr=err_msg)
            raise RuntimeError(f"gwscli failed (exit {proc.returncode}): {err_msg}")

        return stdout.decode()
