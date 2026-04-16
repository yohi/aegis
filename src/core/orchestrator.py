"""Review pipeline orchestrator."""

from __future__ import annotations

import asyncio
from asyncio import Semaphore
from pathlib import Path

import structlog

from .protocols import SecurityShield
from .types import (
    ReviewRequest,
    ReviewResult,
    SecurityBlockedError,
    SyncError,
)

logger = structlog.get_logger()


class Orchestrator:
    """Coordinates the full review pipeline."""


    def __init__(self, shield: SecurityShield, repo_path: Path) -> None:
        self._io_semaphore = Semaphore(10)
        self.shield = shield
        self.repo_path = repo_path

    async def _read_file(self, file: Path) -> tuple[Path, str]:
        """Read a file asynchronously without blocking the event loop."""
        async with self._io_semaphore:
            try:
                content = await asyncio.to_thread(file.read_text, encoding="utf-8")
            except (UnicodeDecodeError, OSError) as exc:
                raise SyncError(
                    f"Cannot read {file}: {exc}"
                ) from exc
        return file, content

    async def _shield_file(self, file: Path, content: str) -> None:
        """Shield a single file input and raise error if blocked."""
        result = await self.shield.shield_input(content)
        if not result.allowed:
            raise SecurityBlockedError(
                f"Input blocked for {file.name}: {[f.category for f in result.findings]}"
            )

    async def run_review(self, request: ReviewRequest) -> ReviewResult:
        """Execute the full review pipeline."""
        sanitized_files = []
        repo_root = request.repo_path.resolve()
        for f in request.target_files:
            # Resolve path against request.repo_path and verify it's a descendant
            resolved_path = (repo_root / f).resolve()
            if repo_root not in resolved_path.parents and resolved_path != repo_root:
                logger.error("security_path_traversal_attempt_detected", path=str(f))
                raise SecurityBlockedError(f"Path traversal attempt detected: {f}")
            sanitized_files.append(resolved_path)

        file_contents = await asyncio.gather(*(self._read_file(f) for f in sanitized_files))

        # Parallelize security shielding for all files using TaskGroup for robust cancellation
        try:
            async with asyncio.TaskGroup() as tg:
                for file, content in file_contents:
                    tg.create_task(self._shield_file(file, content))
        except ExceptionGroup as eg:
            # Re-raise the first SecurityBlockedError or other ReviewError to maintain API consistency
            # If multiple files are blocked, TaskGroup collects all, but we only need to report the first failure.
            for exc in eg.exceptions:
                if isinstance(exc, SecurityBlockedError):
                    raise exc
            raise  # Fallback for unexpected exceptions

        review_output = ReviewResult(
            request_id=request.request_id,
            status="completed",
            findings=(),
            summary="Review completed successfully.",
        )

        output_result = await self.shield.shield_output(review_output.summary)
        if not output_result.allowed:
            review_output = review_output.with_redacted_summary()
        else:
            review_output = review_output.with_summary(output_result.sanitized_content)

        return review_output
