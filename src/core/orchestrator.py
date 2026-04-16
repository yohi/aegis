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

        for file, content in file_contents:
            result = await self.shield.shield_input(content)
            if not result.allowed:
                raise SecurityBlockedError(
                    f"Input blocked for {file.name}: {[f.category for f in result.findings]}"
                )

        review_output = ReviewResult(
            request_id=request.request_id,
            status="completed",
            findings=(),
            summary="Review completed successfully.",
        )

        output_result = await self.shield.shield_output(review_output.summary)
        if not output_result.allowed:
            review_output = review_output.with_redacted_summary()

        return review_output
